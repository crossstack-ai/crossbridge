"""
Test Execution Profiler

Profiles test execution lifecycle, driver commands, HTTP requests, and assertions.
Consolidates legacy profiling functionality with config-driven approach.
"""

import time
from typing import Dict, Any, Optional
from core.profiling.timing import TimingProfiler
from core.profiling.base import ProfilerConfig, ProfileRecord
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class TestExecutionProfiler(TimingProfiler):
    """
    Profiler for test execution lifecycle and commands.
    
    Captures:
    - Test lifecycle (start, setup, teardown, end)
    - Driver commands (Selenium, Playwright, Cypress)
    - HTTP requests
    - Assertions (optional)
    
    Replaces legacy MetricsCollector and PerformanceEvent system.
    """
    
    def __init__(self, config: ProfilerConfig):
        """Initialize test execution profiler"""
        super().__init__(config)
        self._test_start_times: Dict[str, float] = {}
        self._test_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            f"TestExecutionProfiler initialized: "
            f"lifecycle={config.capture_test_lifecycle}, "
            f"commands={config.capture_commands}, "
            f"http={config.capture_http}"
        )
    
    def start_test(self, test_id: str, test_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Mark test start.
        
        Args:
            test_id: Unique test identifier
            test_name: Human-readable test name
            metadata: Additional test metadata (framework, file, etc.)
        """
        if not self.config.enabled or not self.config.capture_test_lifecycle:
            return
        
        self._test_start_times[test_id] = time.monotonic()
        self._test_metadata[test_id] = metadata or {}
        
        self.start(f"test.{test_id}.lifecycle", metadata={"event": "start", "test_name": test_name, **(metadata or {})})
    
    def end_test(self, test_id: str, status: str, error: Optional[str] = None):
        """
        Mark test end and emit full test duration.
        
        Args:
            test_id: Unique test identifier
            status: Test status (passed, failed, skipped)
            error: Error message if failed
        """
        if not self.config.enabled or not self.config.capture_test_lifecycle:
            return
        
        metadata = {
            "event": "end",
            "status": status,
            **({"error": error} if error else {}),
            **self._test_metadata.get(test_id, {})
        }
        
        self.stop(f"test.{test_id}.lifecycle", metadata=metadata)
        
        # Cleanup
        self._test_start_times.pop(test_id, None)
        self._test_metadata.pop(test_id, None)
    
    def record_command(
        self,
        test_id: str,
        command: str,
        duration_ms: float,
        framework: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record driver command execution.
        
        Args:
            test_id: Test identifier
            command: Command name (e.g., "click", "sendKeys", "navigate")
            duration_ms: Command duration in milliseconds
            framework: Framework name (selenium, playwright, cypress)
            metadata: Additional metadata (selector, url, etc.)
        """
        if not self.config.enabled or not self.config.capture_commands:
            return
        
        # Check if this command exceeds threshold
        if duration_ms < self.config.slow_call_ms:
            return
        
        record = ProfileRecord(
            name=f"command.{framework}.{command}",
            duration_ms=duration_ms,
            timestamp=time.time(),
            metadata={
                "test_id": test_id,
                "framework": framework,
                "type": "command",
                **(metadata or {})
            }
        )
        
        self.emit(record)
    
    def record_http(
        self,
        test_id: str,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record HTTP request.
        
        Args:
            test_id: Test identifier
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            metadata: Additional metadata (headers, body size, etc.)
        """
        if not self.config.enabled or not self.config.capture_http:
            return
        
        # Check if this request exceeds threshold
        if duration_ms < self.config.slow_call_ms:
            return
        
        record = ProfileRecord(
            name=f"http.{method}",
            duration_ms=duration_ms,
            timestamp=time.time(),
            metadata={
                "test_id": test_id,
                "method": method,
                "url": url,
                "status_code": status_code,
                "type": "http",
                **(metadata or {})
            }
        )
        
        self.emit(record)
    
    def record_assertion(
        self,
        test_id: str,
        assertion_type: str,
        passed: bool,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record assertion (optional, can be noisy).
        
        Args:
            test_id: Test identifier
            assertion_type: Type of assertion
            passed: Whether assertion passed
            duration_ms: Assertion duration
            metadata: Additional metadata
        """
        if not self.config.enabled or not self.config.capture_assertions:
            return
        
        record = ProfileRecord(
            name=f"assertion.{assertion_type}",
            duration_ms=duration_ms,
            timestamp=time.time(),
            metadata={
                "test_id": test_id,
                "passed": passed,
                "type": "assertion",
                **(metadata or {})
            }
        )
        
        self.emit(record)
