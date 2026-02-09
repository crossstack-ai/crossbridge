"""
Remote Sidecar API Service

Provides HTTP API for remote sidecar observers to receive events from test executions
running on different machines.

Architecture:
- Observer mode: Runs this API server to receive events
- Client mode: Sends events to remote observer

Supports all frameworks via unified event format.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator
import uvicorn

from core.logging import get_logger, LogCategory
from core.sidecar.observer import SidecarObserver, Event
from core.sidecar.sampler import Sampler

# Import all available parsers
from core.intelligence.robot_log_parser import RobotLogParser
from core.intelligence.java_step_parser import JavaStepDefinitionParser
from core.intelligence.cypress_results_parser import CypressResultsParser
from core.intelligence.playwright_trace_parser import PlaywrightTraceParser
from core.intelligence.behave_selenium_parsers import BehaveResultsParser, SeleniumLogParser

# Import execution intelligence components
from core.execution.intelligence.analyzer import ExecutionAnalyzer
from core.execution.intelligence.models import FailureType

# Import AI components
from core.ai.license import LicenseValidator, get_cost_estimate, format_cost_summary
from core.ai.providers import OpenAIProvider, AnthropicProvider, OllamaProvider
from core.ai.models import AIMessage, ModelConfig, AIExecutionContext, TokenUsage

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


# ============================================================================
# API Models
# ============================================================================

class EventPayload(BaseModel):
    """Event data from remote client"""
    event_type: str
    data: Dict[str, Any]
    timestamp: Optional[Union[float, str]] = Field(default_factory=lambda: datetime.utcnow().timestamp())
    execution_id: Optional[str] = None
    test_id: Optional[str] = None
    run_id: Optional[str] = None
    framework: Optional[str] = None
    environment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('timestamp')
    @classmethod
    def parse_timestamp(cls, v):
        """Convert ISO string timestamp to float if needed"""
        if isinstance(v, str):
            # Parse ISO format timestamp to float
            try:
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                return dt.timestamp()
            except Exception:
                raise ValueError(f"Invalid timestamp format: {v}")
        return v


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    mode: str
    uptime_seconds: float
    queue_size: int
    events_processed: int
    events_dropped: int


class BatchEventsPayload(BaseModel):
    """Batch of events for efficient transmission"""
    events: list[EventPayload]
    batch_id: Optional[str] = None
    compression: Optional[str] = None  # 'gzip', 'zstd'


# ============================================================================
# Sidecar API Server
# ============================================================================

class SidecarAPIServer:
    """
    Remote Sidecar API Server
    
    Runs in observer mode to receive events from remote test executions.
    """
    
    def __init__(
        self,
        observer: Optional[SidecarObserver] = None,
        host: str = "0.0.0.0",
        port: int = 8765
    ):
        """
        Initialize sidecar API server
        
        Args:
            observer: SidecarObserver instance (optional, will create if not provided)
            host: Host to bind to
            port: Port to listen on
        """
        if observer is None:
            sampler = Sampler(default_rate=1.0)  # Sample everything in remote sidecar
            observer = SidecarObserver(sampler=sampler)
        self.observer = observer
        self.host = host
        self.port = port
        self.start_time = datetime.utcnow()
        
        # Start observer to process events
        if not self.observer._running:
            self.observer.start()
            logger.info("Observer started for event processing")
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="CrossBridge Sidecar API",
            description="Remote observer API for distributed test monitoring",
            version="1.0.0"
        )
        
        # Add validation error handler for debugging
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            logger.error(f"Validation error: {exc.errors()}")
            logger.error(f"Request body: {await request.body()}")
            return JSONResponse(
                status_code=422,
                content={"detail": exc.errors(), "body": str(await request.body())}
            )
        
        # Register routes
        self._setup_routes()
        self._setup_log_storage_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health():
            """Health check endpoint"""
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            stats = self.observer.get_stats()
            
            return HealthResponse(
                status="healthy",
                version="1.0.0",
                mode="observer",
                uptime_seconds=uptime,
                queue_size=stats.get('queue_size', 0),
                events_processed=stats.get('events_processed', 0),
                events_dropped=stats.get('events_dropped', 0)
            )
        
        @self.app.get("/ready")
        async def readiness():
            """
            Readiness check endpoint (Kubernetes-compatible)
            Returns 200 if service is ready to accept traffic, 503 otherwise
            """
            stats = self.observer.get_stats()
            queue_size = stats.get('queue_size', 0)
            queue_capacity = stats.get('queue_capacity', 5000)
            
            # Not ready if queue is >90% full
            if queue_size / queue_capacity > 0.9:
                raise HTTPException(
                    status_code=503,
                    detail=f"Queue nearly full: {queue_size}/{queue_capacity}"
                )
            
            return {
                "status": "ready",
                "queue_utilization": f"{queue_size}/{queue_capacity}",
                "queue_percent": round((queue_size / queue_capacity) * 100, 2)
            }
        
        @self.app.post("/events")
        async def receive_event(payload: EventPayload, background_tasks: BackgroundTasks):
            """
            Receive a single event from remote client
            
            This is the primary endpoint for event ingestion.
            """
            try:
                # Convert to internal Event format
                event = Event(
                    event_type=payload.event_type,
                    data=payload.data,
                    timestamp=payload.timestamp or datetime.utcnow().timestamp(),
                    execution_id=payload.execution_id,
                    test_id=payload.test_id,
                    run_id=payload.run_id
                )
                
                # Add framework metadata if provided
                if payload.framework:
                    event.data['framework'] = payload.framework
                if payload.environment:
                    event.data['environment'] = payload.environment
                if payload.metadata:
                    event.data['metadata'] = payload.metadata
                
                # Log event received with detailed information
                log_details = {
                    'event_type': payload.event_type,
                    'framework': payload.framework,
                    'test_id': payload.test_id
                }
                
                # Add event-specific details for better visibility
                log_message_parts = [f"Event: {payload.event_type}"]
                
                if payload.event_type == 'test_start':
                    test_name = payload.data.get('test_name', 'Unknown')
                    tags = payload.data.get('tags', [])
                    log_message_parts.append(f"test='{test_name}'")
                    if tags:
                        log_message_parts.append(f"tags={tags}")
                    log_details['test_name'] = test_name
                    if tags:
                        log_details['tags'] = tags
                
                elif payload.event_type == 'test_end':
                    test_name = payload.data.get('test_name', 'Unknown')
                    status = payload.data.get('status', 'Unknown')
                    elapsed = payload.data.get('elapsed_time', 0)
                    message = payload.data.get('message', '')
                    log_message_parts.append(f"test='{test_name}'")
                    log_message_parts.append(f"status={status}")
                    log_message_parts.append(f"elapsed={elapsed:.2f}s")
                    log_details['test_name'] = test_name
                    log_details['status'] = status
                    log_details['elapsed_time'] = elapsed
                    if message:
                        log_details['message'] = message[:100]  # Limit message length
                
                elif payload.event_type == 'suite_start':
                    suite_name = payload.data.get('suite_name', 'Unknown')
                    suite_id = payload.data.get('suite_id', '')
                    source = payload.data.get('source', '')
                    log_message_parts.append(f"suite='{suite_name}'")
                    if suite_id:
                        log_message_parts.append(f"id={suite_id}")
                    log_details['suite_name'] = suite_name
                    log_details['suite_id'] = suite_id
                    if source:
                        log_details['source'] = source
                
                elif payload.event_type == 'suite_end':
                    suite_name = payload.data.get('suite_name', 'Unknown')
                    status = payload.data.get('status', 'Unknown')
                    elapsed = payload.data.get('elapsed_time', 0)
                    stats = payload.data.get('statistics', {})
                    log_message_parts.append(f"suite='{suite_name}'")
                    log_message_parts.append(f"status={status}")
                    log_message_parts.append(f"elapsed={elapsed:.2f}s")
                    if stats:
                        total = stats.get('total', 0)
                        passed = stats.get('passed', 0)
                        failed = stats.get('failed', 0)
                        log_message_parts.append(f"tests={total} (passed={passed}, failed={failed})")
                        log_details['statistics'] = stats
                    log_details['suite_name'] = suite_name
                    log_details['status'] = status
                
                elif payload.event_type == 'execution_complete':
                    message = payload.data.get('message', '')
                    log_message_parts.append(f"message='{message}'")
                    log_details['message'] = message
                
                log_message = " | ".join(log_message_parts)
                logger.info(log_message, extra=log_details)
                
                # Observe event (non-blocking)
                self.observer.observe_event(
                    event_type=payload.event_type,
                    data=event.data,
                    execution_id=payload.execution_id,
                    test_id=payload.test_id,
                    run_id=payload.run_id
                )
                
                return {"status": "accepted", "event_id": payload.test_id}
                
            except Exception as e:
                logger.error(f"Failed to process event: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/events/batch")
        async def receive_batch(payload: BatchEventsPayload, background_tasks: BackgroundTasks):
            """
            Receive batch of events for efficient transmission
            
            Reduces HTTP overhead for high-volume scenarios.
            """
            try:
                accepted_count = 0
                failed_count = 0
                
                for event_payload in payload.events:
                    try:
                        # Observe event (non-blocking)
                        self.observer.observe_event(
                            event_type=event_payload.event_type,
                            data=event_payload.data,
                            execution_id=event_payload.execution_id,
                            test_id=event_payload.test_id,
                            run_id=event_payload.run_id
                        )
                        accepted_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to process event in batch: {e}")
                        failed_count += 1
                
                return {
                    "status": "processed",
                    "batch_id": payload.batch_id,
                    "accepted": accepted_count,
                    "failed": failed_count,
                    "total": len(payload.events)
                }
                
            except Exception as e:
                logger.error(f"Failed to process batch: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/stats")
        async def get_stats():
            """Get observer statistics"""
            return self.observer.get_stats()
        
        @self.app.get("/config")
        async def get_config():
            """Get current configuration"""
            # Get list of available adapters
            adapters_dir = Path(__file__).parent.parent / "adapters"
            available_frameworks = []
            if adapters_dir.exists():
                available_frameworks = [
                    d.name for d in adapters_dir.iterdir() 
                    if d.is_dir() and not d.name.startswith('_') and not d.name == 'common'
                ]
            
            return {
                "host": self.host,
                "port": self.port,
                "max_queue_size": self.observer._max_queue_size,
                "frameworks_supported": sorted(available_frameworks),
                "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
                "features": {
                    "adapter_download": True,
                    "universal_wrapper": True,
                    "batch_events": True,
                    "enhanced_logging": True,
                    "log_parsing": True,
                    "parseable_frameworks": ["robot", "cypress", "playwright", "behave", "java"]
                }
            }
        
        @self.app.post("/shutdown")
        async def shutdown():
            """Graceful shutdown"""
            logger.info("Shutdown requested via API")
            return {"status": "shutting_down"}
        
        @self.app.get("/adapters")
        async def list_adapters():
            """
            List available framework adapters
            
            Returns metadata about all supported framework adapters
            """
            try:
                adapters_dir = Path(__file__).parent.parent / "adapters"
                available_adapters = []
                
                if adapters_dir.exists():
                    for adapter_path in adapters_dir.iterdir():
                        if adapter_path.is_dir() and not adapter_path.name.startswith('_'):
                            # Get adapter metadata
                            readme_path = adapter_path / "README.md"
                            description = ""
                            if readme_path.exists():
                                try:
                                    with open(readme_path, 'r') as f:
                                        first_line = f.readline().strip()
                                        description = first_line.lstrip('#').strip()
                                except:
                                    pass
                            
                            available_adapters.append({
                                "name": adapter_path.name,
                                "path": str(adapter_path),
                                "description": description or f"{adapter_path.name.title()} adapter",
                                "download_url": f"/adapters/{adapter_path.name}"
                            })
                
                return {
                    "adapters": available_adapters,
                    "total": len(available_adapters)
                }
            except Exception as e:
                logger.error(f"Failed to list adapters: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/adapters/{framework}")
        async def download_adapter(framework: str):
            """
            Download framework adapter as tar.gz
            
            The universal wrapper (crossbridge-run) uses this endpoint to download
            adapters dynamically at runtime, enabling zero-touch integration.
            
            Args:
                framework: Framework name (robot, pytest, jest, mocha, etc.)
            
            Returns:
                Tar.gz archive containing the adapter code
            """
            import tarfile
            import tempfile
            import shutil
            from fastapi.responses import FileResponse
            
            try:
                # Validate framework name
                adapters_dir = Path(__file__).parent.parent / "adapters"
                adapter_path = adapters_dir / framework
                
                if not adapter_path.exists() or not adapter_path.is_dir():
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Adapter '{framework}' not found. Available: {[d.name for d in adapters_dir.iterdir() if d.is_dir() and not d.name.startswith('_')]}"
                    )
                
                # Create temporary tar.gz file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp_file:
                    tar_path = tmp_file.name
                
                # Create tar archive
                with tarfile.open(tar_path, "w:gz") as tar:
                    # Add all files from adapter directory
                    for item in adapter_path.rglob("*"):
                        if item.is_file() and not item.name.endswith('.pyc'):
                            arcname = item.relative_to(adapter_path.parent)
                            tar.add(item, arcname=arcname)
                
                logger.info(f"Serving adapter: {framework} ({adapter_path})")
                
                # Return file response that auto-deletes after sending
                return FileResponse(
                    path=tar_path,
                    media_type="application/gzip",
                    filename=f"{framework}-adapter.tar.gz",
                    background=BackgroundTasks().add_task(lambda: Path(tar_path).unlink(missing_ok=True))
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to serve adapter {framework}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # ============================================================================
        # Log Parsing Endpoints
        # ============================================================================
        
        @self.app.post("/parse/{framework}")
        async def parse_test_results(framework: str, request: Request):
            """
            Generic test results parser for all supported frameworks
            
            Supported frameworks:
            - robot: Robot Framework output.xml
            - cypress: Cypress JSON results
            - playwright: Playwright trace files
            - behave: Behave JSON results
            - java: Java step definitions
            
            Upload test results/logs and get detailed analysis including:
            - Test statistics (passed/failed/total)
            - Failed tests with error messages
            - Performance analysis
            - Framework-specific insights
            
            Examples:
                # Robot Framework
                curl -X POST http://localhost:8765/parse/robot \\
                     -H "Content-Type: application/xml" \\
                     --data-binary @output.xml
                
                # Cypress
                curl -X POST http://localhost:8765/parse/cypress \\
                     -H "Content-Type: application/json" \\
                     --data-binary @cypress-results.json
                
                # Playwright
                curl -X POST http://localhost:8765/parse/playwright \\
                     -H "Content-Type: application/json" \\
                     --data-binary @trace.json
                
                # Behave
                curl -X POST http://localhost:8765/parse/behave \\
                     -H "Content-Type: application/json" \\
                     --data-binary @behave-results.json
            """
            try:
                # Get content from request body
                content = await request.body()
                
                if not content:
                    raise HTTPException(status_code=400, detail="No content provided")
                
                # Route to appropriate parser based on framework
                if framework == "robot":
                    return await self._parse_robot_log(content)
                elif framework == "cypress":
                    return await self._parse_cypress_results(content)
                elif framework == "playwright":
                    return await self._parse_playwright_trace(content)
                elif framework == "behave":
                    return await self._parse_behave_results(content)
                elif framework == "java":
                    return await self._parse_java_steps(content)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported framework: {framework}. "
                               f"Supported: robot, cypress, playwright, behave, java"
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to parse {framework} results: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _parse_robot_log(self, content: bytes) -> dict:
        """Parse Robot Framework output.xml"""
        parser = RobotLogParser()
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xml', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            suite = parser.parse(tmp_path)
            stats = parser.get_statistics()
            failed_tests = parser.get_failed_tests()
            failed_keywords = parser.get_failed_keywords()
            slowest_tests = parser.get_slowest_tests(count=10)
            slowest_keywords = parser.get_slowest_keywords(count=10)
            
            return {
                "framework": "robot",
                "suite": {
                    "name": suite.name,
                    "source": suite.source,
                    "status": suite.status.value,
                    "total_tests": suite.total_tests,
                    "passed_tests": suite.passed_tests,
                    "failed_tests": suite.failed_tests,
                    "elapsed_ms": suite.elapsed_ms
                },
                "statistics": stats,
                "failed_tests": [
                    {
                        "name": test.name,
                        "suite": test.suite,
                        "status": test.status.value,
                        "elapsed_ms": test.elapsed_ms,
                        "error_message": test.error_message or self._extract_keyword_errors(test),
                        "tags": test.tags
                    }
                    for test in failed_tests
                ],
                "failed_keywords": [
                    {
                        "name": kw.name,
                        "library": kw.library,
                        "error": kw.error_message,
                        "messages": kw.messages[:5]
                    }
                    for kw in failed_keywords[:20]
                ],
                "slowest_tests": [
                    {
                        "name": test.name,
                        "suite": test.suite,
                        "elapsed_ms": test.elapsed_ms,
                        "status": test.status.value
                    }
                    for test in slowest_tests
                ],
                "slowest_keywords": [
                    {
                        "name": kw.name,
                        "library": kw.library,
                        "elapsed_ms": kw.elapsed_ms
                    }
                    for kw in slowest_keywords
                ]
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def _extract_keyword_errors(self, test) -> str:
        """Extract error messages from failed keywords in a test"""
        errors = []
        keyword_count = len(test.keywords) if hasattr(test, 'keywords') else 0
        failed_kw_count = 0
        
        logger.debug(f"Extracting errors from test with {keyword_count} keywords")
        
        for kw in test.keywords:
            if kw.status.value == "FAIL":
                failed_kw_count += 1
                if kw.error_message:
                    errors.append(f"{kw.name}: {kw.error_message}")
                    logger.debug(f"Found error in keyword {kw.name}: {kw.error_message[:100]}")
                elif kw.messages:
                    errors.append(f"{kw.name}: {'; '.join(kw.messages[:3])}")
                    logger.debug(f"Found messages in keyword {kw.name}: {kw.messages[:3]}")
                else:
                    logger.debug(f"Failed keyword {kw.name} has no error_message or messages")
        
        logger.debug(f"Total keywords: {keyword_count}, failed: {failed_kw_count}, errors extracted: {len(errors)}")
        
        result = " | ".join(errors[:5]) if errors else ""
        if not result and failed_kw_count > 0:
            logger.warning(f"Test has {failed_kw_count} failed keywords but no error messages extracted")
        return result
    
    async def _parse_cypress_results(self, content: bytes) -> dict:
        """Parse Cypress JSON results"""
        import json
        
        data = json.loads(content)
        parser = CypressResultsParser()
        results = parser.parse(data)
        
        return {
            "framework": "cypress",
            "statistics": {
                "total": results.get("total_tests", 0),
                "passed": results.get("passed", 0),
                "failed": results.get("failed", 0),
                "skipped": results.get("skipped", 0),
                "pass_rate": results.get("pass_rate", 0.0)
            },
            "failed_tests": results.get("failed_tests", []),
            "duration_ms": results.get("duration_ms", 0),
            "insights": results.get("insights", {})
        }
    
    async def _parse_playwright_trace(self, content: bytes) -> dict:
        """Parse Playwright trace files"""
        import json
        
        data = json.loads(content)
        parser = PlaywrightTraceParser()
        results = parser.parse(data)
        
        return {
            "framework": "playwright",
            "statistics": results.get("statistics", {}),
            "actions": results.get("actions", []),
            "network_calls": results.get("network_calls", []),
            "console_messages": results.get("console_messages", []),
            "errors": results.get("errors", []),
            "performance": results.get("performance", {})
        }
    
    async def _parse_behave_results(self, content: bytes) -> dict:
        """Parse Behave JSON results"""
        import json
        
        data = json.loads(content)
        parser = BehaveResultsParser()
        results = parser.parse(data)
        
        return {
            "framework": "behave",
            "statistics": {
                "total_features": results.get("total_features", 0),
                "total_scenarios": results.get("total_scenarios", 0),
                "passed_scenarios": results.get("passed_scenarios", 0),
                "failed_scenarios": results.get("failed_scenarios", 0),
                "pass_rate": results.get("pass_rate", 0.0)
            },
            "failed_scenarios": results.get("failed_scenarios_list", []),
            "duration_ms": results.get("duration_ms", 0)
        }
    
    async def _parse_java_steps(self, content: bytes) -> dict:
        """Parse Java step definitions"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.java', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            parser = JavaStepDefinitionParser()
            steps = parser.parse_file(tmp_path)
            bindings = parser.get_step_bindings_map()
            
            return {
                "framework": "java",
                "total_steps": len(steps),
                "step_types": {
                    "Given": len(bindings.get("Given", [])),
                    "When": len(bindings.get("When", [])),
                    "Then": len(bindings.get("Then", []))
                },
                "steps": [
                    {
                        "type": step.step_type,
                        "pattern": step.pattern,
                        "method": step.method_name,
                        "file": Path(step.file_path).name,
                        "line": step.line_number
                    }
                    for step in steps
                ]
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def _setup_log_storage_routes(self):
        """Setup log storage and intelligence analysis routes"""
        # ============================================================================
        # Log Storage & Retrieval Endpoints
        # ============================================================================
        
        # In-memory storage for parsed logs (limited to prevent memory issues)
        self._log_storage: Dict[str, dict] = {}
        self._max_stored_logs = 100  # Limit to 100 logs
        
        # Initialize execution intelligence analyzer (works without AI by default)
        self._analyzer = ExecutionAnalyzer(enable_ai=False)
        
        @self.app.post("/logs/{log_id}")
        async def store_parsed_log(log_id: str, request: Request):
            """
            Store parsed log results for later retrieval via API
            
            This allows crossbridge-log to upload results and provide API access.
            Limited to 10MB per log and 100 total logs to prevent memory issues.
            """
            try:
                # Check size limit
                content = await request.body()
                if len(content) > 10 * 1024 * 1024:  # 10MB
                    raise HTTPException(
                        status_code=413,
                        detail="Log too large. Maximum size: 10MB"
                    )
                
                # Check storage limit
                if len(self._log_storage) >= self._max_stored_logs:
                    # Remove oldest log
                    oldest_id = next(iter(self._log_storage))
                    del self._log_storage[oldest_id]
                    logger.warning(f"Storage limit reached. Removed oldest log: {oldest_id}")
                
                # Parse and store
                data = json.loads(content)
                self._log_storage[log_id] = {
                    "id": log_id,
                    "data": data,
                    "stored_at": datetime.utcnow().isoformat(),
                    "framework": data.get("framework", "unknown")
                }
                
                logger.info(f"Stored log {log_id} ({len(content)} bytes)")
                
                return {
                    "id": log_id,
                    "status": "stored",
                    "size_bytes": len(content),
                    "framework": data.get("framework", "unknown")
                }
                
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON")
            except Exception as e:
                logger.error(f"Failed to store log {log_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/logs/{log_id}")
        async def get_parsed_log(log_id: str):
            """
            Retrieve full parsed log by ID
            
            Returns the complete parsed log data.
            """
            if log_id not in self._log_storage:
                raise HTTPException(status_code=404, detail=f"Log {log_id} not found")
            
            return self._log_storage[log_id]
        
        @self.app.get("/logs/{log_id}/summary")
        async def get_log_summary(log_id: str):
            """
            Get summary of parsed log (statistics only)
            
            Returns lightweight summary without full test details.
            """
            if log_id not in self._log_storage:
                raise HTTPException(status_code=404, detail=f"Log {log_id} not found")
            
            log_data = self._log_storage[log_id]["data"]
            framework = log_data.get("framework", "unknown")
            
            # Extract summary based on framework
            if framework == "robot":
                return {
                    "id": log_id,
                    "framework": framework,
                    "stored_at": self._log_storage[log_id]["stored_at"],
                    "suite": log_data.get("suite", {}).get("name"),
                    "statistics": {
                        "total": log_data.get("suite", {}).get("total_tests", 0),
                        "passed": log_data.get("suite", {}).get("passed_tests", 0),
                        "failed": log_data.get("suite", {}).get("failed_tests", 0),
                        "duration_ms": log_data.get("suite", {}).get("elapsed_ms", 0)
                    }
                }
            elif framework == "cypress":
                return {
                    "id": log_id,
                    "framework": framework,
                    "stored_at": self._log_storage[log_id]["stored_at"],
                    "statistics": log_data.get("statistics", {})
                }
            elif framework == "java":
                return {
                    "id": log_id,
                    "framework": framework,
                    "stored_at": self._log_storage[log_id]["stored_at"],
                    "total_steps": log_data.get("total_steps", 0),
                    "step_types": log_data.get("step_types", {})
                }
            else:
                return {
                    "id": log_id,
                    "framework": framework,
                    "stored_at": self._log_storage[log_id]["stored_at"],
                    "data": log_data
                }
        
        @self.app.get("/logs/{log_id}/failures")
        async def get_log_failures(log_id: str):
            """
            Get only failed tests/keywords from log
            
            Returns failure information for quick issue identification.
            """
            if log_id not in self._log_storage:
                raise HTTPException(status_code=404, detail=f"Log {log_id} not found")
            
            log_data = self._log_storage[log_id]["data"]
            framework = log_data.get("framework", "unknown")
            
            if framework == "robot":
                return {
                    "id": log_id,
                    "framework": framework,
                    "failed_keywords": log_data.get("failed_keywords", []),
                    "failed_count": len(log_data.get("failed_keywords", []))
                }
            elif framework == "cypress":
                return {
                    "id": log_id,
                    "framework": framework,
                    "failures": log_data.get("failures", []),
                    "failed_count": len(log_data.get("failures", []))
                }
            else:
                return {
                    "id": log_id,
                    "framework": framework,
                    "message": "No failure information available for this framework"
                }
        
        @self.app.get("/logs")
        async def list_stored_logs():
            """
            List all stored logs
            
            Returns metadata for all stored logs.
            """
            return {
                "total": len(self._log_storage),
                "max_capacity": self._max_stored_logs,
                "logs": [
                    {
                        "id": log_id,
                        "framework": log_info.get("framework"),
                        "stored_at": log_info.get("stored_at")
                    }
                    for log_id, log_info in self._log_storage.items()
                ]
            }
        
        @self.app.delete("/logs/{log_id}")
        async def delete_log(log_id: str):
            """
            Delete stored log by ID
            
            Removes log from storage to free memory.
            """
            if log_id not in self._log_storage:
                raise HTTPException(status_code=404, detail=f"Log {log_id} not found")
            
            del self._log_storage[log_id]
            logger.info(f"Deleted log {log_id}")
            
            return {"status": "deleted", "id": log_id}
        
        @self.app.get("/ai-provider-info")
        async def get_ai_provider_info():
            """
            Get cached AI provider information for display purposes.
            
            Returns provider type, model name, and cost estimates.
            Used by CLI to show dynamic AI banners based on actual configuration.
            
            Response:
            {
                "provider": "openai|anthropic|selfhosted|none",
                "model": "gpt-3.5-turbo|claude-3-sonnet|deepseek-coder:6.7b|null",
                "endpoint": "http://..." (for self-hosted only),
                "cost_per_1k_tokens": 0.002 or 0.0 (for self-hosted),
                "typical_run_cost": "~$0.01-$0.10" or "No cost",
                "requires_license": true/false
            }
            """
            try:
                # Detect cached provider
                provider = self._detect_ai_provider()
                
                if not provider:
                    return {
                        "provider": "none",
                        "model": None,
                        "cost_per_1k_tokens": 0.0,
                        "typical_run_cost": "N/A - No AI configured",
                        "requires_license": False
                    }
                
                # Get provider-specific details
                result = {"provider": provider}
                
                if provider == "selfhosted":
                    # Get self-hosted config
                    config = self._get_selfhosted_ai_config()
                    if config:
                        result["model"] = config.get("model_name", "unknown")
                        result["endpoint"] = config.get("endpoint_url", "unknown")
                        result["cost_per_1k_tokens"] = 0.0
                        result["typical_run_cost"] = "No cost (self-hosted)"
                        result["requires_license"] = False
                    else:
                        result["model"] = "unknown"
                        result["cost_per_1k_tokens"] = 0.0
                        result["typical_run_cost"] = "No cost (self-hosted)"
                        result["requires_license"] = False
                
                elif provider == "openai":
                    result["model"] = "gpt-3.5-turbo"  # Default model
                    result["cost_per_1k_tokens"] = 0.002
                    result["typical_run_cost"] = "~$0.01-$0.10 per run"
                    result["requires_license"] = True
                
                elif provider == "anthropic":
                    result["model"] = "claude-3-sonnet"  # Default model
                    result["cost_per_1k_tokens"] = 0.003
                    result["typical_run_cost"] = "~$0.015-$0.15 per run"
                    result["requires_license"] = True
                
                else:
                    # Unknown provider
                    result["model"] = "unknown"
                    result["cost_per_1k_tokens"] = 0.0
                    result["typical_run_cost"] = "Unknown"
                    result["requires_license"] = True
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to get AI provider info: {e}", exc_info=True)
                return {
                    "provider": "error",
                    "model": None,
                    "error": str(e),
                    "cost_per_1k_tokens": 0.0,
                    "typical_run_cost": "Unknown",
                    "requires_license": False
                }
        
        @self.app.post("/analyze")
        async def analyze_logs(request: Request):
            """
            Analyze parsed logs with execution intelligence
            
            Automatically applies:
            - Failure classification (PRODUCT_DEFECT, AUTOMATION_DEFECT, ENVIRONMENT_ISSUE, etc.)
            - Signal extraction (timeout, assertion, locator errors)
            - Code reference resolution (for automation defects)
            
            Works deterministically without AI. Returns enriched log data.
            
            Request body:
            {
                "data": <parsed_log_data>,
                "framework": "robot|cypress|pytest|etc",
                "workspace_root": "/path/to/project" (optional)
            }
            
            Response:
            {
                "analyzed": true,
                "data": <original_data>,
                "intelligence_summary": {
                    "classifications": {"PRODUCT_DEFECT": 2, "AUTOMATION_DEFECT": 1},
                    "signals": {"timeout": 1, "assertion_failure": 2},
                    "recommendations": ["Check API endpoint availability", ...]
                },
                "enriched_tests": [<tests_with_classification>]
            }
            """
            try:
                body = await request.json()
                data = body.get("data", {})
                framework = body.get("framework", "unknown")
                workspace_root = body.get("workspace_root")
                
                # AI parameters
                enable_ai = body.get("enable_ai", False)
                ai_provider = body.get("ai_provider")
                ai_model = body.get("ai_model")
                
                # Auto-detect AI provider from cached credentials if not specified
                if enable_ai and not ai_provider:
                    logger.info("AI enabled but no provider specified - attempting auto-detection")
                    ai_provider = self._detect_configured_ai_provider()
                    if ai_provider:
                        logger.info(f"Auto-detected AI provider: {ai_provider}")
                    else:
                        logger.warning("Failed to auto-detect AI provider - falling back to openai")
                        ai_provider = "openai"  # fallback
                
                if not ai_model:
                    ai_model = "gpt-3.5-turbo"  # default model
                
                # AI tracking variables
                ai_token_usage = None
                ai_cost = 0.0
                
                # Update analyzer workspace if provided
                if workspace_root:
                    self._analyzer.workspace_root = workspace_root
                    self._analyzer.resolver.workspace_root = workspace_root
                
                # Validate AI license if AI is enabled (skip for self-hosted)
                if enable_ai:
                    logger.info(f"AI validation check - provider: {ai_provider}")
                    if ai_provider.lower() == "selfhosted":
                        logger.info("Self-hosted AI detected - skipping license validation")
                    else:
                        validator = LicenseValidator()
                        is_valid, message, license = validator.validate_license(ai_provider, "log_analysis")
                        if not is_valid:
                            logger.error(f"License validation failed for {ai_provider}: {message}")
                            raise HTTPException(status_code=403, detail=f"AI License validation failed: {message}")
                
                # Extract failed tests for analysis
                failed_tests = self._extract_failed_tests(data, framework)
                
                logger.info(f"Extracted {len(failed_tests)} failed tests for analysis")
                if failed_tests:
                    # Log first test for debugging
                    first_test = failed_tests[0]
                    error_msg = first_test.get('error_message', 'NO ERROR')
                    logger.info(f"First test name: {first_test.get('name')}")
                    logger.info(f"First test keys: {list(first_test.keys())}")
                    logger.info(f"First test error_message: {error_msg[:200] if error_msg else 'EMPTY'}")
                    logger.info(f"First test full: {str(first_test)[:500]}")
                    
                    # Check what raw_log is being built
                    raw_log_test = self._build_raw_log(first_test, framework)
                    logger.info(f"Built raw_log length: {len(raw_log_test)}")
                    logger.info(f"Built raw_log content: {repr(raw_log_test[:500])}")
                
                if not failed_tests:
                    # No failures to analyze
                    return {
                        "analyzed": True,
                        "data": data,
                        "intelligence_summary": {
                            "classifications": {},
                            "signals": {},
                            "recommendations": ["All tests passed - no analysis needed"]
                        }
                    }
                
                # Analyze each failed test
                classifications = {}
                signals_summary = {}
                enriched_tests = []
                recommendations = set()
                top_failures = []  # For detailed failure display
                
                # Initialize AI provider if enabled
                ai_provider_instance = None
                total_prompt_tokens = 0
                total_completion_tokens = 0
                
                if enable_ai:
                    try:
                        if ai_provider.lower() == "selfhosted":
                            # Get self-hosted AI config from cached credentials
                            config = self._get_selfhosted_ai_config()
                            if config:
                                endpoint_url = config['endpoint_url']
                                model_name = config['model_name'] or ai_model
                                
                                logger.info(f"Self-hosted AI configured: {endpoint_url} with model {model_name}")
                                
                                # Initialize Ollama provider (works with Ollama, LM Studio, etc.)
                                ai_provider_instance = OllamaProvider({
                                    "base_url": endpoint_url,
                                    "model": model_name
                                })
                                
                                # Override ai_model with configured model
                                ai_model = model_name
                                logger.info(f"Self-hosted AI provider initialized: {endpoint_url} with model {model_name}")
                            else:
                                logger.error("Self-hosted AI provider selected but no configuration found")
                                enable_ai = False
                        elif ai_provider.lower() == "openai":
                            ai_provider_instance = OpenAIProvider({"api_key": license.customer_id})  # Using customer_id as API key for demo
                        elif ai_provider.lower() == "anthropic":
                            ai_provider_instance = AnthropicProvider({"api_key": license.customer_id})
                        else:
                            raise ValueError(f"Unsupported AI provider: {ai_provider}")
                        
                        if ai_provider_instance:
                            logger.info(f"AI provider initialized: {ai_provider} with model {ai_model}")
                    except Exception as e:
                        logger.error(f"Failed to initialize AI provider: {e}")
                        enable_ai = False  # Disable AI on initialization failure
                
                for test in failed_tests:
                    test_name = test.get("name", "unknown")
                    error_msg = test.get("error_message") or test.get("error", "")
                    
                    # Build raw log for analyzer
                    raw_log = self._build_raw_log(test, framework)
                    
                    logger.debug(f"Analyzing test {test_name}, raw_log length: {len(raw_log)}, preview: {raw_log[:200]}")
                    
                    # Analyze (with optional AI enhancement)
                    try:
                        result = self._analyzer.analyze(
                            raw_log=raw_log,
                            test_name=test_name,
                            framework=framework,
                            context={"framework": framework}
                        )
                        
                        # AI-enhanced analysis if enabled
                        if enable_ai and ai_provider_instance and result.classification:
                            try:
                                # Create AI prompt for enhanced analysis
                                prompt = f"""Analyze this test failure and provide insights:
                                
Test Name: {test_name}
Error: {error_msg[:500]}
Current Classification: {result.classification.failure_type.value}
Confidence: {result.classification.confidence}

Provide:
1. Root cause analysis
2. Specific fix recommendations
3. Similar failure patterns to watch for

Keep response concise (max 200 words)."""
                                
                                # Call AI provider
                                ai_response = ai_provider_instance.complete(
                                    messages=[AIMessage(role="user", content=prompt)],
                                    model_config=ModelConfig(model=ai_model, max_tokens=300, temperature=0.3),
                                    context=AIExecutionContext(execution_id=f"log_analysis_{test_name[:20]}")
                                )
                                
                                # Track token usage
                                if ai_response.token_usage:
                                    total_prompt_tokens += ai_response.token_usage.prompt_tokens
                                    total_completion_tokens += ai_response.token_usage.completion_tokens
                                    ai_cost += ai_response.cost
                                
                                # Add AI insights to classification
                                result.classification.reason = f"{result.classification.reason}\n\nAI Insights: {ai_response.content[:300]}"
                                recommendations.add(ai_response.content[:200])
                                
                            except Exception as ai_err:
                                logger.warning(f"AI analysis failed for {test_name}: {ai_err}")
                        
                        # Log signals for debugging
                        logger.info(f"Analysis result for {test_name[:50]}: signals={len(result.signals)}, classification={result.classification.failure_type.value if result.classification else 'None'}")
                        if result.signals:
                            logger.info(f"Signals extracted: {[s.signal_type.value for s in result.signals]}")
                        
                        # Check if classification is valid
                        if not result.classification:
                            logger.warning(f"No classification for test {test_name} - raw_log preview: {raw_log[:200]}")
                            enriched_tests.append(test)
                            continue
                        
                        # Count classifications
                        failure_type = result.classification.failure_type.value
                        classifications[failure_type] = classifications.get(failure_type, 0) + 1
                        
                        # Count signals
                        for signal in result.signals:
                            signal_type = signal.signal_type.value
                            signals_summary[signal_type] = signals_summary.get(signal_type, 0) + 1
                        
                        # Add recommendations
                        if result.classification.failure_type == FailureType.PRODUCT_DEFECT:
                            recommendations.add("Review application code for bugs")
                        elif result.classification.failure_type == FailureType.AUTOMATION_DEFECT:
                            recommendations.add("Update test automation code/locators")
                        elif result.classification.failure_type == FailureType.ENVIRONMENT_ISSUE:
                            recommendations.add("Check infrastructure and network connectivity")
                        elif result.classification.failure_type == FailureType.CONFIGURATION_ISSUE:
                            recommendations.add("Verify test configuration and dependencies")
                        
                        # Add to top failures (limit to 5 most important)
                        if len(top_failures) < 5:
                            # Get actual error message from test or signals
                            actual_error = error_msg if error_msg else (result.signals[0].message if result.signals else "Unknown error")
                            
                            failure_detail = {
                                "test_name": test_name[:80],  # Truncate long names
                                "failure_type": failure_type,
                                "confidence": result.classification.confidence,
                                "reason": actual_error[:200],  # Show actual error message
                                "code_reference": f"{result.classification.code_reference.file}:{result.classification.code_reference.line}" if result.classification.code_reference else None,
                                "stacktrace": result.signals[0].stacktrace if result.signals and result.signals[0].stacktrace else None
                            }
                            top_failures.append(failure_detail)
                        
                        # Enrich test with classification
                        enriched_test = {
                            **test,
                            "classification": {
                                "type": failure_type,
                                "confidence": result.classification.confidence,
                                "reason": result.classification.reason,
                                "code_reference": {
                                    "file": result.classification.code_reference.file,
                                    "line": result.classification.code_reference.line,
                                    "snippet": result.classification.code_reference.snippet
                                } if result.classification.code_reference else None
                            },
                            "signals": [
                                {
                                    "type": s.signal_type.value,
                                    "confidence": s.confidence,
                                    "message": s.message
                                }
                                for s in result.signals
                            ]
                        }
                        enriched_tests.append(enriched_test)
                        
                    except Exception as e:
                        logger.warning(f"Failed to analyze test {test_name}: {e}")
                        enriched_tests.append(test)
                
                # Track AI usage in license
                if enable_ai and (total_prompt_tokens + total_completion_tokens) > 0:
                    validator = LicenseValidator()
                    total_tokens = total_prompt_tokens + total_completion_tokens
                    validator.track_usage(total_tokens, ai_cost)
                    
                    # Create AI usage summary
                    ai_token_usage = {
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_tokens,
                        "cost": ai_cost,
                        "provider": ai_provider,
                        "model": ai_model
                    }
                
                response = {
                    "analyzed": True,
                    "data": data,
                    "intelligence_summary": {
                        "classifications": classifications,
                        "signals": signals_summary,
                        "recommendations": list(recommendations),
                        "top_failures": top_failures  # Add detailed failure information
                    },
                    "enriched_tests": enriched_tests
                }
                
                # Add AI usage info if AI was used
                if ai_token_usage:
                    response["ai_usage"] = ai_token_usage
                
                return response
                
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    def _detect_configured_ai_provider(self) -> Optional[str]:
        """
        Detect which AI provider is configured in cached credentials.
        
        Returns:
            Provider name (selfhosted, openai, anthropic) or None
        """
        try:
            from core.repo.test_credentials import _get_test_creds_manager
            
            manager = _get_test_creds_manager()
            if not manager:
                logger.info("No credential manager available - cryptography may not be installed")
                return None
            
            # Check for cached AI credentials
            logger.info(f"Loading credentials from: {manager.credentials_file if hasattr(manager, 'credentials_file') else 'unknown'}")
            manager._load_credentials()
            
            logger.info(f"Found {len(manager._credentials)} total credentials")
            for key, cred in manager._credentials.items():
                logger.debug(f"Checking credential: provider={cred.provider}, repo={cred.repo}")
                if cred.repo == "_ai_cache_":
                    # Return the configured provider
                    logger.info(f"✅ Detected cached AI provider: {cred.provider}")
                    return cred.provider
            
            logger.info("No AI credentials found in cache (repo='_ai_cache_')")
            return None
        except Exception as e:
            logger.error(f"Failed to detect AI provider from cache: {e}", exc_info=True)
            return None
    
    def _get_selfhosted_ai_config(self) -> Optional[dict]:
        """
        Get self-hosted AI configuration from cached credentials.
        
        Returns:
            Dict with endpoint_url, model_name, api_key or None
        """
        try:
            from core.repo.test_credentials import get_selfhosted_ai_config
            
            config = get_selfhosted_ai_config()
            return config
        except Exception as e:
            logger.warning(f"Failed to get self-hosted AI config: {e}")
            return None
    
    def _extract_failed_tests(self, data: dict, framework: str) -> List[dict]:
        """Extract failed tests from parsed log data"""
        failed = []
        
        if framework == "robot":
            # Robot Framework - use failed_tests array
            if "failed_tests" in data and data["failed_tests"]:
                failed = data["failed_tests"]
            elif "suite" in data and "tests" in data["suite"]:
                failed = [t for t in data["suite"]["tests"] if t.get("status") == "FAIL"]
            elif "slowest_tests" in data:
                # Fall back to slowest_tests list and filter for failures
                failed = [t for t in data["slowest_tests"] if t.get("status") == "FAIL"]
        
        elif framework == "cypress":
            # Cypress
            if "failures" in data:
                failed = data["failures"]
            elif "tests" in data:
                failed = [t for t in data["tests"] if t.get("state") == "failed"]
        
        elif framework == "pytest":
            # Pytest
            if "failures" in data:
                failed = data["failures"]
        
        else:
            # Generic - look for tests with failure status
            if "tests" in data:
                failed = [
                    t for t in data["tests"]
                    if t.get("status") in ["FAIL", "failed", "FAILED", "error", "ERROR"]
                ]
        
        return failed
    
    def _build_raw_log(self, test: dict, framework: str) -> str:
        """Build raw log string from test data for analyzer"""
        lines = []
        
        # Test name
        name = test.get("name", "unknown_test")
        lines.append(f"Test: {name}")
        
        # Error message
        error = test.get("error_message") or test.get("error") or test.get("message", "")
        if error:
            lines.append(f"Error: {error}")
        
        # Stack trace
        stack_trace = test.get("stack_trace") or test.get("stacktrace", "")
        if stack_trace:
            lines.append(f"Stack trace:\n{stack_trace}")
        
        # Messages (Robot Framework)
        if "messages" in test:
            for msg in test["messages"]:
                lines.append(f"Message: {msg}")
        
        return "\n".join(lines)
    
        @self.app.post("/analyze/with-app-logs")
        async def analyze_with_correlation(request: Request):
            """
            Analyze test failures with application log correlation
            
            Provides enhanced insights by correlating test failures with application logs.
            Uses multiple correlation strategies: trace_id, timestamp, service, execution_id.
            
            Request body:
            {
                "data": <parsed_test_log_data>,
                "app_logs": <application_logs_file_path or log_entries>,
                "framework": "robot|cypress|pytest|etc",
                "workspace_root": "/path/to/project" (optional),
                "correlation_config": {
                    "timestamp_window": 5,  # seconds
                    "strategies": ["trace_id", "execution_id", "timestamp", "service"]
                }
            }
            
            Response:
            {
                "analyzed": true,
                "data": <original_data>,
                "intelligence_summary": { ... },
                "enriched_tests": [ ... ],
                "correlation_summary": {
                    "total_correlated": 10,
                    "correlation_methods": {"timestamp": 8, "trace_id": 2},
                    "avg_confidence": 0.75
                },
                "correlated_app_errors": [
                    {
                        "test_name": "...",
                        "app_logs": [<related app errors>],
                        "correlation_method": "timestamp",
                        "confidence": 0.7
                    }
                ]
            }
            """
            try:
                from core.execution.intelligence.log_adapters import get_registry
                from core.execution.intelligence.log_adapters.correlation import LogCorrelator
                from core.execution.intelligence.log_adapters.sampling import LogSampler, SamplingConfig
                
                body = await request.json()
                data = body.get("data", {})
                app_logs_input = body.get("app_logs")
                framework = body.get("framework", "unknown")
                workspace_root = body.get("workspace_root")
                correlation_config = body.get("correlation_config", {})
                
                # Update analyzer workspace if provided
                if workspace_root:
                    self._analyzer.workspace_root = workspace_root
                    self._analyzer.resolver.workspace_root = workspace_root
                
                # Extract failed tests
                failed_tests = self._extract_failed_tests(data, framework)
                
                if not failed_tests:
                    return {
                        "analyzed": True,
                        "data": data,
                        "intelligence_summary": {
                            "classifications": {},
                            "signals": {},
                            "recommendations": ["All tests passed - no analysis needed"]
                        },
                        "correlation_summary": {
                            "total_correlated": 0,
                            "message": "No failed tests to correlate"
                        }
                    }
                
                # Parse application logs
                app_logs = []
                if app_logs_input:
                    if isinstance(app_logs_input, str):
                        # File path provided - parse it
                        registry = get_registry()
                        adapter = registry.get_adapter(app_logs_input)
                        
                        if adapter:
                            logger.info(f"Parsing application logs from {app_logs_input}")
                            with open(app_logs_input, 'r') as f:
                                for line in f:
                                    parsed = adapter.parse(line.strip())
                                    if parsed:
                                        app_logs.append(parsed)
                            
                            # Apply sampling to reduce volume (keep all errors/warnings)
                            sampler_config = SamplingConfig(
                                debug_rate=0.01,
                                info_rate=0.01,
                                warn_rate=0.1,
                                error_rate=1.0,
                                fatal_rate=1.0
                            )
                            sampler = LogSampler(sampler_config)
                            sampled_logs = []
                            for log in app_logs:
                                if sampler.should_sample(log.get('level', 'INFO'), log):
                                    sampled_logs.append(log)
                            app_logs = sampled_logs
                            
                            logger.info(f"Parsed {len(app_logs)} application logs (after sampling)")
                        else:
                            logger.warning(f"No adapter found for {app_logs_input}")
                    elif isinstance(app_logs_input, list):
                        # Direct log entries provided
                        app_logs = app_logs_input
                
                # Initialize correlator with config
                timestamp_window = correlation_config.get('timestamp_window', 5)
                correlator = LogCorrelator(timestamp_window_seconds=timestamp_window)
                
                # Perform standard analysis first
                classifications = {}
                signals_summary = {}
                enriched_tests = []
                recommendations = set()
                top_failures = []
                
                # Correlation tracking
                correlation_summary = {
                    "total_correlated": 0,
                    "correlation_methods": {},
                    "avg_confidence": 0.0
                }
                correlated_app_errors = []
                total_confidence = 0.0
                
                for test in failed_tests:
                    test_name = test.get("name", "unknown")
                    error_msg = test.get("error_message") or test.get("error", "")
                    
                    # Build raw log for analyzer
                    raw_log = self._build_raw_log(test, framework)
                    
                    # Analyze (deterministic)
                    result = self._analyzer.analyze(
                        raw_log=raw_log,
                        test_name=test_name,
                        framework=framework,
                        context={"framework": framework}
                    )
                    
                    if not result.classification:
                        enriched_tests.append(test)
                        continue
                    
                    # Count classifications and signals
                    failure_type = result.classification.failure_type.value
                    classifications[failure_type] = classifications.get(failure_type, 0) + 1
                    
                    for signal in result.signals:
                        signal_type = signal.signal_type.value
                        signals_summary[signal_type] = signals_summary.get(signal_type, 0) + 1
                    
                    # Add recommendations
                    if result.classification.failure_type == FailureType.PRODUCT_DEFECT:
                        recommendations.add("Review application code for bugs")
                    elif result.classification.failure_type == FailureType.AUTOMATION_DEFECT:
                        recommendations.add("Update test automation code/locators")
                    elif result.classification.failure_type == FailureType.ENVIRONMENT_ISSUE:
                        recommendations.add("Check infrastructure and network connectivity")
                    
                    # Correlate with application logs if available
                    correlated_logs_for_test = []
                    correlation_method = "none"
                    correlation_confidence = 0.0
                    
                    if app_logs:
                        # Create execution event from test
                        from core.execution.intelligence.models import ExecutionEvent
                        test_event = ExecutionEvent(
                            level="ERROR",
                            message=error_msg or test_name,
                            timestamp=test.get("start_time") or test.get("timestamp"),
                            metadata={
                                "test_name": test_name,
                                "trace_id": test.get("trace_id"),
                                "execution_id": test.get("execution_id"),
                                "service": test.get("service") or test.get("suite")
                            }
                        )
                        
                        # Correlate
                        correlation_result = correlator.correlate(test_event, app_logs)
                        
                        if correlation_result.correlated_logs:
                            correlation_summary["total_correlated"] += 1
                            method = correlation_result.correlation_method
                            correlation_summary["correlation_methods"][method] = \
                                correlation_summary["correlation_methods"].get(method, 0) + 1
                            
                            total_confidence += correlation_result.correlation_confidence
                            correlated_logs_for_test = correlation_result.correlated_logs
                            correlation_method = method
                            correlation_confidence = correlation_result.correlation_confidence
                            
                            # Add to correlated app errors (limit to errors/warnings)
                            error_logs = [
                                log for log in correlation_result.correlated_logs
                                if log.get('level') in ['ERROR', 'FATAL', 'WARN', 'WARNING']
                            ]
                            
                            if error_logs:
                                correlated_app_errors.append({
                                    "test_name": test_name[:80],
                                    "app_logs": error_logs[:5],  # Top 5 errors
                                    "correlation_method": method,
                                    "confidence": correlation_confidence
                                })
                                
                                # Enhance recommendations based on app logs
                                for log in error_logs:
                                    if 'timeout' in log.get('message', '').lower():
                                        recommendations.add("Increase timeout configurations in application")
                                    elif 'database' in log.get('message', '').lower():
                                        recommendations.add("Check database connectivity and query performance")
                                    elif 'memory' in log.get('message', '').lower():
                                        recommendations.add("Monitor application memory usage")
                    
                    # Build top failures with correlation info
                    if len(top_failures) < 5:
                        actual_error = error_msg if error_msg else (result.signals[0].message if result.signals else "Unknown error")
                        
                        failure_detail = {
                            "test_name": test_name[:80],
                            "failure_type": failure_type,
                            "confidence": result.classification.confidence,
                            "reason": actual_error[:200],
                            "correlated_app_errors": len(correlated_logs_for_test),
                            "correlation_method": correlation_method if correlation_method != "none" else None,
                            "correlation_confidence": correlation_confidence if correlation_confidence > 0 else None
                        }
                        top_failures.append(failure_detail)
                    
                    # Enrich test with classification and correlation
                    enriched_test = {
                        **test,
                        "classification": {
                            "type": failure_type,
                            "confidence": result.classification.confidence,
                            "reason": result.classification.reason
                        },
                        "signals": [
                            {
                                "type": s.signal_type.value,
                                "confidence": s.confidence,
                                "message": s.message[:200]
                            } for s in result.signals
                        ],
                        "correlated_app_logs": len(correlated_logs_for_test),
                        "correlation_method": correlation_method if correlation_method != "none" else None
                    }
                    enriched_tests.append(enriched_test)
                
                # Calculate average confidence
                if correlation_summary["total_correlated"] > 0:
                    correlation_summary["avg_confidence"] = total_confidence / correlation_summary["total_correlated"]
                
                return {
                    "analyzed": True,
                    "data": data,
                    "intelligence_summary": {
                        "classifications": classifications,
                        "signals": signals_summary,
                        "recommendations": list(recommendations)
                    },
                    "top_failures": top_failures,
                    "enriched_tests": enriched_tests,
                    "correlation_summary": correlation_summary,
                    "correlated_app_errors": correlated_app_errors[:10]  # Top 10
                }
                
            except Exception as e:
                logger.error(f"Correlation analysis failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Correlation analysis failed: {str(e)}")
    
    async def start(self):
        """Start the API server"""
        logger.info(f"Starting Sidecar API server on {self.host}:{self.port}")
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run(self):
        """Run the server (blocking)"""
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


# ============================================================================
# Client Helpers
# ============================================================================

@dataclass
class RemoteSidecarConfig:
    """Configuration for remote sidecar client"""
    host: str
    port: int = 8765
    protocol: str = "http"
    batch_size: int = 50
    batch_timeout_ms: int = 1000
    retry_attempts: int = 3
    timeout_seconds: int = 5
    
    @property
    def base_url(self) -> str:
        """Get base URL for API"""
        return f"{self.protocol}://{self.host}:{self.port}"
