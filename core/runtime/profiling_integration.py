"""
Performance Profiling Runtime Integration

Provides hardened wrappers for profiling storage operations with retry logic,
health checks, and failure isolation to ensure profiling never breaks tests.

This module wraps profiling storage backends (PostgreSQL, InfluxDB) with:
- Automatic retry for transient database failures
- Health checks for storage backend availability
- Graceful degradation when storage is unavailable
- Rate limiting for high-volume metric collection

Usage:
    from core.runtime.profiling_integration import (
        HardenedProfilingStorage,
        with_profiling_storage_retry
    )
    
    # Wrap storage backend with retry
    storage = HardenedProfilingStorage(original_storage)
    
    # Or use decorator for individual operations
    @with_profiling_storage_retry
    def write_metrics(events):
        storage.write_events(events)
"""

from typing import List, Callable, Any, Optional
from functools import wraps
import time

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


# Import runtime functions lazily to avoid circular imports
def _get_runtime_functions():
    """Lazy import of runtime functions to avoid circular imports"""
    from core.runtime.retry import retry_with_backoff
    from core.runtime.rate_limit import with_rate_limit
    from core.runtime.health import register_health_check, check_health as _check_health
    return retry_with_backoff, with_rate_limit, register_health_check, _check_health


def with_profiling_storage_retry(func: Callable) -> Callable:
    """
    Decorator to add automatic retry logic for profiling storage operations.
    
    Uses the "quick" retry policy (3 attempts, 500ms backoff) to avoid
    blocking test execution while still providing resilience to transient failures.
    
    Args:
        func: Storage operation function to wrap
        
    Returns:
        Wrapped function with retry logic
        
    Example:
        @with_profiling_storage_retry
        def save_events(storage, events):
            storage.write_events(events)
    """
    retry_with_backoff, _, _, _ = _get_runtime_functions()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get retry policy config
            from core.runtime.config import get_retry_policy_by_name
            policy = get_retry_policy_by_name("quick")
            return retry_with_backoff(func, policy)(*args, **kwargs)
        except Exception as e:
            # Profiling failures should NEVER break tests
            logger.warning(
                f"Profiling storage operation failed after retries: {func.__name__}",
                extra={
                    "error": str(e),
                    "function": func.__name__,
                    "operation": "profiling_storage"
                }
            )
            return None
    
    return wrapper


class HardenedProfilingStorage:
    """
    Hardened wrapper for profiling storage backends.
    
    Wraps any storage backend (Local, PostgreSQL, InfluxDB) with:
    - Automatic retry on transient failures
    - Health checks for backend availability
    - Graceful degradation when backend is unavailable
    - Non-blocking operation to never impact test execution
    
    The wrapper ensures that profiling infrastructure problems never
    cause test failures or delays.
    
    Attributes:
        storage: Underlying storage backend to wrap
        health_check_name: Name for health check registration
        max_consecutive_failures: Number of failures before marking unhealthy
        
    Example:
        from core.profiling.storage import PostgreSQLStorageBackend
        from core.runtime.profiling_integration import HardenedProfilingStorage
        
        original_storage = PostgreSQLStorageBackend(config)
        hardened_storage = HardenedProfilingStorage(original_storage)
        
        # Operations now have automatic retry and health checks
        hardened_storage.write_events(events)
    """
    
    def __init__(
        self,
        storage: Any,
        health_check_name: str = "profiling_storage",
        max_consecutive_failures: int = 5
    ):
        """
        Initialize hardened storage wrapper.
        
        Args:
            storage: Storage backend to wrap (must implement StorageBackend interface)
            health_check_name: Name for health check registration
            max_consecutive_failures: Number of consecutive failures before marking unhealthy
        """
        self._storage = storage
        self._health_check_name = health_check_name
        self._max_consecutive_failures = max_consecutive_failures
        self._consecutive_failures = 0
        self._is_healthy = True
        
        # Register health check
        self._register_health_check()
        
        logger.info(
            f"Initialized hardened profiling storage: {storage.__class__.__name__}",
            extra={
                "storage_type": storage.__class__.__name__,
                "health_check": health_check_name,
                "max_failures": max_consecutive_failures
            }
        )
    
    def _register_health_check(self) -> None:
        """Register health check for this storage backend"""
        _, _, register_health_check, _ = _get_runtime_functions()
        
        def health_check() -> bool:
            """Check if storage backend is healthy"""
            try:
                # Try to initialize or test connection
                if hasattr(self._storage, 'test_connection'):
                    return self._storage.test_connection()
                elif hasattr(self._storage, 'initialize'):
                    return self._storage.initialize()
                else:
                    # No test method, assume healthy
                    return self._is_healthy
            except Exception as e:
                logger.debug(
                    f"Storage health check failed: {self._health_check_name}",
                    extra={"error": str(e)}
                )
                return False
        
        register_health_check(
            health_check,
            name=self._health_check_name
        )
    
    def _handle_failure(self, operation: str, error: Exception) -> None:
        """Handle operation failure and update health status"""
        self._consecutive_failures += 1
        
        logger.warning(
            f"Profiling storage operation failed: {operation}",
            extra={
                "operation": operation,
                "error": str(error),
                "consecutive_failures": self._consecutive_failures,
                "storage_type": self._storage.__class__.__name__
            }
        )
        
        if self._consecutive_failures >= self._max_consecutive_failures:
            self._is_healthy = False
            logger.error(
                f"Profiling storage marked unhealthy after {self._consecutive_failures} failures",
                extra={
                    "storage_type": self._storage.__class__.__name__,
                    "health_check": self._health_check_name
                }
            )
    
    def _handle_success(self, operation: str) -> None:
        """Handle successful operation"""
        if self._consecutive_failures > 0:
            logger.info(
                f"Profiling storage recovered: {operation}",
                extra={
                    "operation": operation,
                    "previous_failures": self._consecutive_failures,
                    "storage_type": self._storage.__class__.__name__
                }
            )
        
        self._consecutive_failures = 0
        self._is_healthy = True
    
    def initialize(self) -> bool:
        """Initialize storage backend with retry"""
        from core.runtime.config import get_retry_policy_by_name
        from core.runtime.retry import retry_with_backoff
        
        try:
            policy = get_retry_policy_by_name("quick")
            result = retry_with_backoff(self._storage.initialize, policy)()
            self._handle_success("initialize")
            return result
        except Exception as e:
            self._handle_failure("initialize", e)
            return False
    
    def write_events(self, events: List[Any]) -> bool:
        """
        Write events to storage with retry and rate limiting.
        
        Args:
            events: List of PerformanceEvent objects to write
            
        Returns:
            True if successful, False otherwise
        """
        from core.runtime.config import get_retry_policy_by_name, get_rate_limit_for_operation
        from core.runtime.retry import retry_with_backoff
        from core.runtime.rate_limit import check_rate_limit
        
        if not self._is_healthy:
            logger.debug(
                "Skipping profiling storage write - backend unhealthy",
                extra={
                    "event_count": len(events),
                    "storage_type": self._storage.__class__.__name__
                }
            )
            return False
        
        # Check rate limit
        try:
            check_rate_limit("default")
        except Exception:
            logger.warning("Rate limit exceeded for profiling storage")
            return False
        
        try:
            policy = get_retry_policy_by_name("quick")
            result = retry_with_backoff(self._storage.write_events, policy)(events)
            
            self._handle_success("write_events")
            
            logger.debug(
                f"Wrote {len(events)} profiling events to storage",
                extra={
                    "event_count": len(events),
                    "storage_type": self._storage.__class__.__name__
                }
            )
            
            return result
            
        except Exception as e:
            self._handle_failure("write_events", e)
            return False
    
    def flush(self) -> bool:
        """Flush buffered events with retry"""
        from core.runtime.config import get_retry_policy_by_name
        from core.runtime.retry import retry_with_backoff
        
        try:
            policy = get_retry_policy_by_name("quick")
            result = retry_with_backoff(self._storage.flush, policy)()
            self._handle_success("flush")
            return result
        except Exception as e:
            self._handle_failure("flush", e)
            return False
    
    def shutdown(self) -> None:
        """Clean shutdown of storage backend"""
        try:
            self._storage.shutdown()
            logger.info(
                "Profiling storage shutdown complete",
                extra={"storage_type": self._storage.__class__.__name__}
            )
        except Exception as e:
            logger.warning(
                "Error during profiling storage shutdown",
                extra={
                    "error": str(e),
                    "storage_type": self._storage.__class__.__name__
                }
            )


class ProfilingHealthMonitor:
    """
    Monitor profiling infrastructure health.
    
    Provides aggregated health status for all profiling components:
    - Storage backend health
    - Collector service health
    - Event queue health
    
    Example:
        monitor = ProfilingHealthMonitor()
        
        if monitor.is_healthy():
            print("Profiling infrastructure healthy")
        else:
            print(f"Profiling issues: {monitor.get_issues()}")
    """
    
    def __init__(self):
        self._health_checks = []
        logger.info("Initialized profiling health monitor")
    
    def register_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """
        Register a health check function.
        
        Args:
            name: Name for this health check
            check_func: Function that returns True if healthy
        """
        self._health_checks.append((name, check_func))
        logger.debug(f"Registered profiling health check: {name}")
    
    def is_healthy(self) -> bool:
        """
        Check if all profiling components are healthy.
        
        Returns:
            True if all health checks pass
        """
        for name, check_func in self._health_checks:
            try:
                if not check_func():
                    logger.warning(f"Profiling health check failed: {name}")
                    return False
            except Exception as e:
                logger.warning(
                    f"Profiling health check error: {name}",
                    extra={"error": str(e)}
                )
                return False
        
        return True
    
    def get_issues(self) -> List[str]:
        """
        Get list of failing health checks.
        
        Returns:
            List of health check names that are failing
        """
        issues = []
        
        for name, check_func in self._health_checks:
            try:
                if not check_func():
                    issues.append(name)
            except Exception as e:
                issues.append(f"{name} (error: {str(e)})")
        
        return issues
    
    def get_status_report(self) -> dict:
        """
        Get detailed status report for all health checks.
        
        Returns:
            Dictionary with health check results
        """
        report = {
            "healthy": True,
            "checks": []
        }
        
        for name, check_func in self._health_checks:
            try:
                is_healthy = check_func()
                report["checks"].append({
                    "name": name,
                    "healthy": is_healthy,
                    "error": None
                })
                
                if not is_healthy:
                    report["healthy"] = False
                    
            except Exception as e:
                report["checks"].append({
                    "name": name,
                    "healthy": False,
                    "error": str(e)
                })
                report["healthy"] = False
        
        return report


# Convenience functions for common operations
def create_hardened_storage(storage: Any) -> HardenedProfilingStorage:
    """
    Create a hardened storage wrapper for the given backend.
    
    Args:
        storage: Storage backend to wrap
        
    Returns:
        HardenedProfilingStorage instance
        
    Example:
        from core.profiling.storage import StorageFactory
        from core.runtime.profiling_integration import create_hardened_storage
        
        config = ProfileConfig(...)
        raw_storage = StorageFactory.create(config)
        hardened = create_hardened_storage(raw_storage)
    """
    return HardenedProfilingStorage(storage)


def check_profiling_health() -> bool:
    """
    Quick check if profiling infrastructure is healthy.
    
    Returns:
        True if profiling storage health check passes
    """
    _, _, _, check_health = _get_runtime_functions()
    
    try:
        result = check_health()
        
        # Check for profiling-specific health checks
        if "profiling_storage" in result:
            return result["profiling_storage"]["healthy"]
        
        # If no specific check, assume healthy
        return True
        
    except Exception as e:
        logger.warning(
            "Error checking profiling health",
            extra={"error": str(e)}
        )
        return False
