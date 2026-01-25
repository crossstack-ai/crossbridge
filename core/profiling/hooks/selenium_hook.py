"""
Selenium WebDriver Performance Profiling Wrapper

Wraps WebDriver commands to capture execution time and detect slow operations.
"""

import time
from typing import Any, Callable

from core.profiling.models import PerformanceEvent, EventType
from core.profiling.collector import MetricsCollector
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class ProfilingWebDriver:
    """
    WebDriver wrapper that captures command performance.
    
    Usage:
        from selenium import webdriver
        from core.profiling.hooks.selenium_hook import ProfilingWebDriver
        
        driver = webdriver.Chrome()
        profiled_driver = ProfilingWebDriver(driver, test_id="test_login")
    """
    
    def __init__(self, driver: Any, test_id: str, collector: MetricsCollector = None):
        self._driver = driver
        self._test_id = test_id
        self._collector = collector or MetricsCollector.get_instance()
        
        # Commands to profile
        self._profiled_commands = {
            "get", "find_element", "find_elements", "click", "send_keys",
            "execute_script", "switch_to", "refresh", "back", "forward",
            "implicitly_wait", "set_page_load_timeout",
        }
    
    def __getattr__(self, name: str) -> Any:
        """Intercept attribute access to wrap methods"""
        original = getattr(self._driver, name)
        
        # Only profile known commands
        if name in self._profiled_commands and callable(original):
            return self._wrap_method(name, original)
        
        return original
    
    def _wrap_method(self, command: str, method: Callable) -> Callable:
        """Wrap a WebDriver method to capture timing"""
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            exception_occurred = False
            
            try:
                result = method(*args, **kwargs)
                return result
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
                        event_type=EventType.DRIVER_COMMAND,
                        framework="selenium",
                        duration_ms=duration_ms,
                        command=command,
                        failed=exception_occurred,
                    )
                    self._collector.collect(event)
        
        return wrapper
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        if hasattr(self._driver, "__exit__"):
            return self._driver.__exit__(exc_type, exc_val, exc_tb)


def profile_webdriver(driver: Any, test_id: str) -> ProfilingWebDriver:
    """
    Factory function to create a profiling WebDriver wrapper.
    
    Args:
        driver: Original WebDriver instance
        test_id: Test identifier for event correlation
    
    Returns:
        ProfilingWebDriver wrapper
    """
    return ProfilingWebDriver(driver, test_id)
