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
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from core.logging import get_logger, LogCategory
from core.sidecar.observer import SidecarObserver, Event
from core.sidecar.sampler import Sampler

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


# ============================================================================
# API Models
# ============================================================================

class EventPayload(BaseModel):
    """Event data from remote client"""
    event_type: str
    data: Dict[str, Any]
    timestamp: Optional[float] = Field(default_factory=lambda: datetime.utcnow().timestamp())
    execution_id: Optional[str] = None
    test_id: Optional[str] = None
    run_id: Optional[str] = None
    framework: Optional[str] = None
    environment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


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
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="CrossBridge Sidecar API",
            description="Remote observer API for distributed test monitoring",
            version="1.0.0"
        )
        
        # Register routes
        self._setup_routes()
    
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
                
                # Queue event for processing (async)
                background_tasks.add_task(self.observer.record_event, event)
                
                return {"status": "accepted", "event_id": event.test_id}
                
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
                        event = Event(
                            event_type=event_payload.event_type,
                            data=event_payload.data,
                            timestamp=event_payload.timestamp or datetime.utcnow().timestamp(),
                            execution_id=event_payload.execution_id,
                            test_id=event_payload.test_id,
                            run_id=event_payload.run_id
                        )
                        
                        background_tasks.add_task(self.observer.record_event, event)
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
            return {
                "host": self.host,
                "port": self.port,
                "max_queue_size": self.observer._max_queue_size,
                "frameworks_supported": ["robot", "pytest", "testng", "cucumber", "cypress", "playwright"],
                "uptime": (datetime.utcnow() - self.start_time).total_seconds()
            }
        
        @self.app.post("/shutdown")
        async def shutdown():
            """Graceful shutdown"""
            logger.info("Shutdown requested via API")
            return {"status": "shutting_down"}
    
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
