"""
Runtime Integration for Flaky Detection

Wraps flaky detection database operations with retry logic and health checks.
"""

from typing import List, Optional
from functools import wraps

from core.logging import get_logger, LogCategory
from core.runtime import (
    with_database_retry,
    register_database_health_check,
    retry_with_backoff,
    load_runtime_config,
)

logger = get_logger(__name__, category=LogCategory.TESTING)


def with_flaky_db_retry(func):
    """
    Decorator to add retry logic to flaky detection database operations.
    
    Automatically retries on connection errors, deadlocks, and transient failures.
    Uses 'quick' retry policy suitable for database operations.
    
    Example:
        @with_flaky_db_retry
        def save_flaky_result(self, result):
            self.session.add(result)
            self.session.commit()
    """
    return with_database_retry(func, retry_policy_name="quick", operation_name=f"flaky_db_{func.__name__}")


def register_flaky_db_health_check(connection_check_function, name: str = "flaky_detection_db"):
    """
    Register health check for flaky detection database.
    
    Args:
        connection_check_function: Function that returns True if DB is healthy
        name: Health check name (default: "flaky_detection_db")
        
    Example:
        def check_flaky_db():
            try:
                session.execute("SELECT 1 FROM test_executions LIMIT 1")
                return True
            except:
                return False
        
        register_flaky_db_health_check(check_flaky_db)
    """
    config = load_runtime_config()
    
    if not config.health_checks.enabled:
        logger.info(f"Health checks disabled, skipping registration for {name}")
        return
    
    register_database_health_check(connection_check_function, name)
    logger.info(
        f"Registered flaky detection database health check: {name}",
        extra={"health_check": name}
    )


class HardenedFlakyDetector:
    """
    Wrapper around flaky detector with production hardening.
    
    Features:
    - Database retry on transient failures
    - Health check monitoring
    - Structured logging
    """
    
    def __init__(self, detector, enable_retry: bool = True, enable_health_checks: bool = True):
        """
        Initialize hardened flaky detector.
        
        Args:
            detector: Underlying flaky detector (FlakyDetector or MultiFrameworkDetector)
            enable_retry: Enable retry logic for database operations
            enable_health_checks: Enable health check registration
        """
        self.detector = detector
        
        # Load runtime config
        config = load_runtime_config()
        
        self.enable_retry = enable_retry and config.retry.enabled
        self.enable_health_checks = enable_health_checks and config.health_checks.enabled
        
        logger.info(
            f"Initialized hardened flaky detector",
            extra={
                "detector_type": detector.__class__.__name__,
                "retry_enabled": self.enable_retry,
                "health_checks_enabled": self.enable_health_checks,
            }
        )
    
    def detect(self, test_id: str, executions: List, framework: Optional[str] = None):
        """
        Detect flaky tests with retry logic.
        
        Args:
            test_id: Test identifier
            executions: List of test execution records
            framework: Test framework (optional)
            
        Returns:
            FlakyTestResult
        """
        if self.enable_retry:
            @with_flaky_db_retry
            def _detect():
                return self.detector.detect(test_id, executions, framework)
            
            try:
                result = _detect()
                logger.info(
                    f"Flaky detection successful for {test_id}",
                    extra={
                        "test_id": test_id,
                        "classification": result.classification if hasattr(result, 'classification') else None,
                        "framework": framework,
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Flaky detection failed after retries: {test_id}",
                    extra={
                        "test_id": test_id,
                        "error": str(e),
                        "framework": framework,
                    }
                )
                raise
        else:
            return self.detector.detect(test_id, executions, framework)
    
    def __getattr__(self, name: str):
        """Forward attribute access to underlying detector."""
        return getattr(self.detector, name)


def harden_flaky_detector(detector):
    """
    Wrap a flaky detector with production hardening.
    
    Args:
        detector: Flaky detector to wrap (FlakyDetector or MultiFrameworkDetector)
        
    Returns:
        HardenedFlakyDetector instance
        
    Example:
        from core.flaky_detection import MultiFrameworkDetector
        from core.runtime.flaky_integration import harden_flaky_detector
        
        detector = MultiFrameworkDetector()
        hardened = harden_flaky_detector(detector)
        result = hardened.detect(test_id="test_login", executions=records)
    """
    return HardenedFlakyDetector(detector)
