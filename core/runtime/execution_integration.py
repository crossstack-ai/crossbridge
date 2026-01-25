"""
Test Execution Runtime Integration

Provides hardened wrappers for test execution operations with retry logic,
health checks, and failure isolation.

This module wraps test execution operations with:
- Automatic retry for transient adapter/infrastructure failures
- Health checks for adapter availability
- Timeout management and graceful degradation
- Structured logging for execution observability

Usage:
    from core.runtime.execution_integration import (
        HardenedTestExecutor,
        with_execution_retry
    )
    
    # Wrap executor with retry
    executor = HardenedTestExecutor(original_executor)
    
    # Or use decorator for individual operations
    @with_execution_retry
    def run_test(adapter, test_name):
        return adapter.run_test(test_name)
"""

from typing import List, Callable, Any, Optional, Dict
from functools import wraps
import time

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.EXECUTION)


# Import runtime functions lazily to avoid circular imports
def _get_runtime_functions():
    """Lazy import of runtime functions to avoid circular imports"""
    from core.runtime.retry import retry_with_backoff
    from core.runtime.health import register_health_check, check_health as _check_health
    from core.runtime.config import get_retry_policy_by_name
    return retry_with_backoff, register_health_check, _check_health, get_retry_policy_by_name


def with_execution_retry(func: Callable) -> Callable:
    """
    Decorator to add automatic retry logic for test execution operations.
    
    Uses the "quick" retry policy (3 attempts, 500ms backoff) to handle
    transient adapter failures while avoiding excessive delays.
    
    Args:
        func: Execution operation function to wrap
        
    Returns:
        Wrapped function with retry logic
        
    Example:
        @with_execution_retry
        def execute_test(executor, test_name):
            return executor.execute_single(test_name)
    """
    retry_with_backoff, _, _, get_retry_policy_by_name = _get_runtime_functions()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            policy = get_retry_policy_by_name("quick")
            return retry_with_backoff(func, policy)(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Test execution operation failed after retries: {func.__name__}",
                extra={
                    "error": str(e),
                    "function": func.__name__,
                    "operation": "test_execution"
                }
            )
            raise
    
    return wrapper


class HardenedTestExecutor:
    """
    Hardened wrapper for test executor.
    
    Wraps TestExecutor with:
    - Automatic retry on transient adapter failures
    - Health checks for adapter availability
    - Timeout management with graceful degradation
    - Structured logging for execution visibility
    
    The wrapper ensures that infrastructure problems don't prevent
    test execution when possible, and provides clear visibility.
    
    Attributes:
        executor: Underlying test executor to wrap
        health_check_name: Name for health check registration
        max_timeout: Maximum timeout for test execution
        
    Example:
        from core.execution.executor import TestExecutor
        from core.runtime.execution_integration import HardenedTestExecutor
        
        original_executor = TestExecutor()
        hardened_executor = HardenedTestExecutor(original_executor)
        
        # Operations now have automatic retry
        results = hardened_executor.execute_tests(test_list)
    """
    
    def __init__(
        self,
        executor: Any,
        health_check_name: str = "test_executor",
        max_timeout: int = 3600
    ):
        """
        Initialize hardened test executor wrapper.
        
        Args:
            executor: Test executor to wrap (TestExecutor instance)
            health_check_name: Name for health check registration
            max_timeout: Maximum timeout in seconds for test execution
        """
        self._executor = executor
        self._health_check_name = health_check_name
        self._max_timeout = max_timeout
        self._is_healthy = True
        self._adapter_health: Dict[str, bool] = {}
        
        # Register health check
        self._register_health_check()
        
        logger.info(
            f"Initialized hardened test executor: {executor.__class__.__name__}",
            extra={
                "executor_type": executor.__class__.__name__,
                "health_check": health_check_name,
                "max_timeout": max_timeout
            }
        )
    
    def _register_health_check(self) -> None:
        """Register health check for test executor"""
        _, register_health_check, _, _ = _get_runtime_functions()
        
        def health_check() -> bool:
            """Check if test executor is healthy"""
            try:
                # Check executor has required components
                if hasattr(self._executor, 'adapter_registry'):
                    return True
                return self._is_healthy
            except Exception as e:
                logger.debug(
                    f"Test executor health check failed: {self._health_check_name}",
                    extra={"error": str(e)}
                )
                return False
        
        register_health_check(
            health_check,
            name=self._health_check_name
        )
    
    def _check_adapter_health(self, adapter_name: str) -> bool:
        """
        Check if a specific adapter is healthy.
        
        Args:
            adapter_name: Name of the adapter to check
            
        Returns:
            True if adapter is healthy or health status unknown
        """
        if adapter_name in self._adapter_health:
            is_healthy = self._adapter_health[adapter_name]
            
            if not is_healthy:
                logger.warning(
                    f"Adapter marked unhealthy: {adapter_name}",
                    extra={"adapter": adapter_name}
                )
            
            return is_healthy
        
        # Unknown adapter, assume healthy
        return True
    
    def _mark_adapter_health(self, adapter_name: str, is_healthy: bool) -> None:
        """
        Update adapter health status.
        
        Args:
            adapter_name: Name of the adapter
            is_healthy: Whether adapter is healthy
        """
        previous_status = self._adapter_health.get(adapter_name, True)
        self._adapter_health[adapter_name] = is_healthy
        
        if previous_status != is_healthy:
            logger.info(
                f"Adapter health status changed: {adapter_name}",
                extra={
                    "adapter": adapter_name,
                    "previous": previous_status,
                    "current": is_healthy
                }
            )
    
    def execute_tests(
        self,
        tests: List[str],
        framework: Optional[str] = None,
        parallel: bool = False,
        timeout: Optional[int] = None
    ) -> List[Any]:
        """
        Execute multiple tests with retry.
        
        Args:
            tests: List of test identifiers
            framework: Framework to use (pytest, robot, etc.)
            parallel: Whether to run tests in parallel
            timeout: Timeout in seconds (capped at max_timeout)
            
        Returns:
            List of test execution results
        """
        retry_with_backoff, _, _, get_retry_policy_by_name = _get_runtime_functions()
        actual_timeout = min(timeout or self._max_timeout, self._max_timeout)
        
        try:
            logger.info(
                f"Executing {len(tests)} tests",
                extra={
                    "test_count": len(tests),
                    "framework": framework,
                    "parallel": parallel,
                    "timeout": actual_timeout
                }
            )
            
            start_time = time.time()
            
            policy = get_retry_policy_by_name("quick")
            results = retry_with_backoff(
                lambda: self._executor.execute_tests(
                    tests=tests,
                    framework=framework,
                    parallel=parallel,
                    timeout=actual_timeout
                ),
                policy
            )()
            
            elapsed = time.time() - start_time
            
            # Count results by status
            status_counts = {}
            for result in results:
                status = getattr(result, 'status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            logger.info(
                f"Test execution completed: {len(results)} results",
                extra={
                    "test_count": len(tests),
                    "result_count": len(results),
                    "elapsed_seconds": round(elapsed, 2),
                    "status_counts": status_counts,
                    "framework": framework
                }
            )
            
            return results
            
        except TimeoutError as e:
            logger.error(
                f"Test execution timeout after {actual_timeout}s",
                extra={
                    "test_count": len(tests),
                    "timeout": actual_timeout,
                    "framework": framework
                }
            )
            raise
            
        except Exception as e:
            logger.error(
                "Test execution failed",
                extra={
                    "test_count": len(tests),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "framework": framework
                }
            )
            
            # Mark adapter as potentially unhealthy
            if framework:
                self._mark_adapter_health(framework, False)
            
            raise
    
    def execute_single(
        self,
        test: str,
        framework: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Execute a single test with retry.
        
        Args:
            test: Test identifier
            framework: Framework to use
            timeout: Timeout in seconds
            
        Returns:
            Test execution result
        """
        retry_with_backoff, _, _, get_retry_policy_by_name = _get_runtime_functions()
        actual_timeout = min(timeout or 300, self._max_timeout)
        
        try:
            logger.debug(
                f"Executing single test: {test}",
                extra={
                    "test": test,
                    "framework": framework,
                    "timeout": actual_timeout
                }
            )
            
            policy = get_retry_policy_by_name("quick")
            result = retry_with_backoff(
                lambda: self._executor.execute_single(
                    test=test,
                    framework=framework,
                    timeout=actual_timeout
                ),
                policy
            )()
            
            logger.debug(
                f"Test execution completed: {test}",
                extra={
                    "test": test,
                    "status": getattr(result, 'status', 'unknown'),
                    "framework": framework
                }
            )
            
            # Mark adapter as healthy on success
            if framework:
                self._mark_adapter_health(framework, True)
            
            return result
            
        except Exception as e:
            logger.error(
                f"Single test execution failed: {test}",
                extra={
                    "test": test,
                    "error": str(e),
                    "framework": framework
                }
            )
            
            # Mark adapter as potentially unhealthy
            if framework:
                self._mark_adapter_health(framework, False)
            
            raise
    
    def get_adapter_health_status(self) -> Dict[str, bool]:
        """
        Get health status for all known adapters.
        
        Returns:
            Dictionary mapping adapter names to health status
        """
        return self._adapter_health.copy()
    
    def reset_adapter_health(self, adapter_name: Optional[str] = None) -> None:
        """
        Reset health status for adapters.
        
        Args:
            adapter_name: Specific adapter to reset, or None for all
        """
        if adapter_name:
            if adapter_name in self._adapter_health:
                logger.info(f"Resetting adapter health: {adapter_name}")
                del self._adapter_health[adapter_name]
        else:
            logger.info("Resetting all adapter health status")
            self._adapter_health.clear()
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to underlying executor"""
        return getattr(self._executor, name)


class AdapterHealthMonitor:
    """
    Monitor test adapter health.
    
    Tracks adapter availability and performance to detect issues.
    
    Example:
        monitor = AdapterHealthMonitor()
        monitor.register_adapter('pytest', pytest_adapter)
        
        if monitor.is_adapter_healthy('pytest'):
            # Use adapter
            pass
    """
    
    def __init__(self):
        self._adapters: Dict[str, Any] = {}
        self._health_status: Dict[str, bool] = {}
        self._failure_counts: Dict[str, int] = {}
        
        logger.info("Initialized adapter health monitor")
    
    def register_adapter(self, name: str, adapter: Any) -> None:
        """
        Register an adapter for health monitoring.
        
        Args:
            name: Adapter name
            adapter: Adapter instance
        """
        self._adapters[name] = adapter
        self._health_status[name] = True
        self._failure_counts[name] = 0
        
        logger.info(f"Registered adapter for monitoring: {name}")
    
    def is_adapter_healthy(self, name: str) -> bool:
        """
        Check if an adapter is healthy.
        
        Args:
            name: Adapter name
            
        Returns:
            True if adapter is healthy
        """
        return self._health_status.get(name, True)
    
    def record_failure(self, name: str) -> None:
        """
        Record an adapter failure.
        
        Args:
            name: Adapter name
        """
        if name in self._failure_counts:
            self._failure_counts[name] += 1
            
            # Mark unhealthy after 3 failures
            if self._failure_counts[name] >= 3:
                self._health_status[name] = False
                logger.warning(
                    f"Adapter marked unhealthy after {self._failure_counts[name]} failures: {name}"
                )
    
    def record_success(self, name: str) -> None:
        """
        Record an adapter success.
        
        Args:
            name: Adapter name
        """
        if name in self._failure_counts:
            # Reset failure count on success
            if self._failure_counts[name] > 0:
                logger.info(f"Adapter recovered: {name}")
            
            self._failure_counts[name] = 0
            self._health_status[name] = True
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Get health status report for all adapters.
        
        Returns:
            Dictionary with adapter health information
        """
        report = {
            "healthy_adapters": [],
            "unhealthy_adapters": [],
            "total_adapters": len(self._adapters)
        }
        
        for name in self._adapters:
            status = {
                "name": name,
                "healthy": self._health_status.get(name, True),
                "failure_count": self._failure_counts.get(name, 0)
            }
            
            if status["healthy"]:
                report["healthy_adapters"].append(status)
            else:
                report["unhealthy_adapters"].append(status)
        
        return report


# Convenience functions
def create_hardened_executor(executor: Any) -> HardenedTestExecutor:
    """
    Create a hardened test executor wrapper.
    
    Args:
        executor: Test executor to wrap
        
    Returns:
        HardenedTestExecutor instance
        
    Example:
        from core.execution.executor import TestExecutor
        from core.runtime.execution_integration import create_hardened_executor
        
        executor = TestExecutor()
        hardened = create_hardened_executor(executor)
    """
    return HardenedTestExecutor(executor)


def check_execution_health() -> bool:
    """
    Quick check if test execution infrastructure is healthy.
    
    Returns:
        True if test executor health check passes
    """
    _, _, check_health, _ = _get_runtime_functions()
    
    try:
        result = check_health()
        
        # Check for execution-specific health checks
        if "test_executor" in result:
            return result["test_executor"]["healthy"]
        
        # If no specific check, assume healthy
        return True
        
    except Exception as e:
        logger.warning(
            "Error checking test executor health",
            extra={"error": str(e)}
        )
        return False
