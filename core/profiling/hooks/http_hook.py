"""
HTTP Requests Performance Profiling

Intercepts HTTP calls to measure response time and detect slow APIs.
"""

import logging
import time
from typing import Optional
import requests
from requests import Session

from core.profiling.models import PerformanceEvent, EventType
from core.profiling.collector import MetricsCollector

logger = logging.getLogger(__name__)


class ProfilingSession(Session):
    """
    Requests Session wrapper that captures HTTP performance.
    
    Usage:
        from core.profiling.hooks.http_hook import ProfilingSession
        
        session = ProfilingSession(test_id="test_api_login")
        response = session.get("https://api.example.com/login")
    """
    
    def __init__(self, test_id: str, collector: Optional[MetricsCollector] = None):
        super().__init__()
        self._test_id = test_id
        self._collector = collector or MetricsCollector.get_instance()
    
    def request(self, method, url, *args, **kwargs):
        """Override request method to capture timing"""
        start = time.monotonic()
        response = None
        exception_occurred = False
        
        try:
            response = super().request(method, url, *args, **kwargs)
            return response
        except Exception as e:
            exception_occurred = True
            raise
        finally:
            end = time.monotonic()
            duration_ms = (end - start) * 1000
            
            # Emit profiling event
            if self._collector.current_run_id:
                event = PerformanceEvent.create(
                    run_id=self._collector.current_run_id,
                    test_id=self._test_id,
                    event_type=EventType.HTTP_REQUEST,
                    framework="requests",
                    duration_ms=duration_ms,
                    endpoint=url,
                    method=method.upper(),
                    status_code=response.status_code if response else 0,
                    failed=exception_occurred,
                )
                self._collector.collect(event)


def profile_requests_session(test_id: str) -> ProfilingSession:
    """
    Factory function to create a profiling requests session.
    
    Args:
        test_id: Test identifier for event correlation
    
    Returns:
        ProfilingSession instance
    """
    return ProfilingSession(test_id)


# Monkey-patch helper (optional - for automatic profiling)
_original_request = requests.request
_profiling_enabled = False


def enable_requests_profiling(test_id: str) -> None:
    """
    Enable automatic profiling of all requests calls.
    
    Warning: This uses monkey-patching and should be used carefully.
    """
    global _profiling_enabled
    
    if _profiling_enabled:
        return
    
    collector = MetricsCollector.get_instance()
    
    def profiled_request(method, url, **kwargs):
        start = time.monotonic()
        response = None
        exception_occurred = False
        
        try:
            response = _original_request(method, url, **kwargs)
            return response
        except Exception as e:
            exception_occurred = True
            raise
        finally:
            end = time.monotonic()
            duration_ms = (end - start) * 1000
            
            if collector.current_run_id:
                event = PerformanceEvent.create(
                    run_id=collector.current_run_id,
                    test_id=test_id,
                    event_type=EventType.HTTP_REQUEST,
                    framework="requests",
                    duration_ms=duration_ms,
                    endpoint=url,
                    method=method.upper(),
                    status_code=response.status_code if response else 0,
                    failed=exception_occurred,
                )
                collector.collect(event)
    
    requests.request = profiled_request
    _profiling_enabled = True


def disable_requests_profiling() -> None:
    """Disable automatic profiling of requests"""
    global _profiling_enabled
    
    if not _profiling_enabled:
        return
    
    requests.request = _original_request
    _profiling_enabled = False
