"""
Failure Isolation for Sidecar Observer

Ensures observer failures don't crash the test execution.
Provides isolated execution contexts with fallback mechanisms.
"""

import sys
import traceback
import threading
from typing import Callable, Any, Optional, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.OBSERVER)

T = TypeVar('T')


@dataclass
class FailureRecord:
    """Record of an isolated failure."""
    
    timestamp: datetime
    operation: str
    exception_type: str
    exception_message: str
    traceback: str
    recovered: bool


class IsolatedExecutor(Generic[T]):
    """
    Execute operations in isolated context with failure handling.
    
    Prevents observer failures from propagating to test execution.
    """
    
    def __init__(
        self,
        operation_name: str,
        default_value: Optional[T] = None,
        log_failures: bool = True,
        raise_on_failure: bool = False
    ):
        """
        Initialize isolated executor.
        
        Args:
            operation_name: Name of operation being isolated
            default_value: Value to return on failure
            log_failures: Whether to log failures
            raise_on_failure: Whether to re-raise exceptions (for testing)
        """
        self.operation_name = operation_name
        self.default_value = default_value
        self.log_failures = log_failures
        self.raise_on_failure = raise_on_failure
        
        self._failures: list[FailureRecord] = []
        self._lock = threading.Lock()
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """
        Execute function in isolated context.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result or default_value on failure
        """
        try:
            return func(*args, **kwargs)
        
        except Exception as e:
            # Record failure
            failure = FailureRecord(
                timestamp=datetime.now(),
                operation=self.operation_name,
                exception_type=type(e).__name__,
                exception_message=str(e),
                traceback=traceback.format_exc(),
                recovered=True
            )
            
            with self._lock:
                self._failures.append(failure)
            
            if self.log_failures:
                logger.error(
                    f"Observer operation failed (isolated): {self.operation_name}",
                    extra={
                        "exception_type": failure.exception_type,
                        "exception_message": failure.exception_message,
                        "recovered": True
                    },
                    exc_info=True
                )
            
            if self.raise_on_failure:
                raise
            
            return self.default_value
    
    @contextmanager
    def isolated_context(self):
        """
        Context manager for isolated execution.
        
        Usage:
            executor = IsolatedExecutor("my_operation")
            with executor.isolated_context():
                # Code that might fail
                pass
        """
        try:
            yield
        except Exception as e:
            # Record failure
            failure = FailureRecord(
                timestamp=datetime.now(),
                operation=self.operation_name,
                exception_type=type(e).__name__,
                exception_message=str(e),
                traceback=traceback.format_exc(),
                recovered=True
            )
            
            with self._lock:
                self._failures.append(failure)
            
            if self.log_failures:
                logger.error(
                    f"Observer operation failed (isolated): {self.operation_name}",
                    extra={
                        "exception_type": failure.exception_type,
                        "exception_message": failure.exception_message
                    },
                    exc_info=True
                )
            
            if self.raise_on_failure:
                raise
    
    def get_failures(self) -> list[FailureRecord]:
        """Get list of recorded failures."""
        with self._lock:
            return self._failures.copy()
    
    def clear_failures(self):
        """Clear failure history."""
        with self._lock:
            self._failures.clear()


class ObserverFailureHandler:
    """
    Global handler for observer failures.
    
    Centralizes failure tracking and provides health metrics.
    """
    
    def __init__(self, max_failures_per_minute: int = 10):
        """
        Initialize failure handler.
        
        Args:
            max_failures_per_minute: Alert threshold for failure rate
        """
        self.max_failures_per_minute = max_failures_per_minute
        self._executors: dict[str, IsolatedExecutor] = {}
        self._lock = threading.RLock()
        
        logger.info(
            "Observer failure handler initialized",
            extra={"max_failures_per_minute": max_failures_per_minute}
        )
    
    def get_executor(
        self,
        operation_name: str,
        default_value: Any = None,
        log_failures: bool = True
    ) -> IsolatedExecutor:
        """
        Get or create isolated executor for operation.
        
        Args:
            operation_name: Name of operation
            default_value: Default return value on failure
            log_failures: Whether to log failures
            
        Returns:
            IsolatedExecutor instance
        """
        with self._lock:
            if operation_name not in self._executors:
                self._executors[operation_name] = IsolatedExecutor(
                    operation_name=operation_name,
                    default_value=default_value,
                    log_failures=log_failures
                )
            return self._executors[operation_name]
    
    def get_all_failures(self) -> list[FailureRecord]:
        """Get all recorded failures across all executors."""
        with self._lock:
            failures = []
            for executor in self._executors.values():
                failures.extend(executor.get_failures())
            return sorted(failures, key=lambda f: f.timestamp, reverse=True)
    
    def get_recent_failures(self, minutes: int = 1) -> list[FailureRecord]:
        """Get failures from last N minutes."""
        cutoff = datetime.now()
        cutoff = cutoff.replace(
            second=cutoff.second,
            microsecond=cutoff.microsecond
        )
        
        from datetime import timedelta
        cutoff = cutoff - timedelta(minutes=minutes)
        
        all_failures = self.get_all_failures()
        return [f for f in all_failures if f.timestamp >= cutoff]
    
    def get_health_status(self) -> dict[str, Any]:
        """
        Get health status based on failure rate.
        
        Returns:
            Health status dictionary
        """
        recent_failures = self.get_recent_failures(minutes=1)
        failure_count = len(recent_failures)
        
        is_healthy = failure_count < self.max_failures_per_minute
        
        status = {
            "healthy": is_healthy,
            "failures_last_minute": failure_count,
            "threshold": self.max_failures_per_minute,
            "total_operations": len(self._executors)
        }
        
        if not is_healthy:
            status["warning"] = (
                f"Observer failure rate ({failure_count}/min) exceeds "
                f"threshold ({self.max_failures_per_minute}/min)"
            )
            
            # Include most common failure types
            failure_types = {}
            for failure in recent_failures:
                failure_types[failure.exception_type] = (
                    failure_types.get(failure.exception_type, 0) + 1
                )
            
            status["top_failures"] = sorted(
                failure_types.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        
        return status
    
    def clear_all_failures(self):
        """Clear all failure records."""
        with self._lock:
            for executor in self._executors.values():
                executor.clear_failures()
            logger.info("All observer failure records cleared")


def safe_observer_call(
    operation_name: str,
    func: Callable[..., T],
    *args,
    default_value: Optional[T] = None,
    **kwargs
) -> Optional[T]:
    """
    Convenience function to execute observer operation safely.
    
    Args:
        operation_name: Name of operation
        func: Function to execute
        *args: Positional arguments
        default_value: Value to return on failure
        **kwargs: Keyword arguments
        
    Returns:
        Function result or default_value on failure
        
    Usage:
        result = safe_observer_call(
            "record_test_start",
            observer.on_test_start,
            test_name="my_test"
        )
    """
    executor = failure_handler.get_executor(operation_name, default_value)
    return executor.execute(func, *args, **kwargs)


@contextmanager
def isolated_observer_operation(operation_name: str):
    """
    Context manager for isolated observer operations.
    
    Args:
        operation_name: Name of operation
        
    Usage:
        with isolated_observer_operation("observe_screenshot"):
            # Observer code that might fail
            observer.record_screenshot(screenshot)
    """
    executor = failure_handler.get_executor(operation_name)
    with executor.isolated_context():
        yield


# Global failure handler
failure_handler = ObserverFailureHandler()
