"""
Runtime Integration for Database Operations

Wraps database operations with retry logic and health checks.
"""

from typing import Any, Callable, Optional, TypeVar
from functools import wraps

from core.logging import get_logger, LogCategory
from core.runtime import (
    retry_with_backoff,
    get_health_registry,
    SimpleHealthCheck,
    NetworkError,
    ServerError,
    load_runtime_config,
)

logger = get_logger(__name__, category=LogCategory.PERSISTENCE)

T = TypeVar('T')


def with_database_retry(
    func: Optional[Callable] = None,
    *,
    retry_policy_name: str = "quick",
    operation_name: Optional[str] = None,
):
    """
    Decorator to add retry logic to database operations.
    
    Args:
        func: Function to wrap (set automatically when used as decorator)
        retry_policy_name: Retry policy (quick by default for DB ops)
        operation_name: Name of operation for logging
        
    Example:
        @with_database_retry(retry_policy_name="quick")
        def get_test_results(test_id: str):
            return db.query("SELECT * FROM tests WHERE id = ?", test_id)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            config = load_runtime_config()
            
            if not config.retry.enabled:
                # Retry disabled, call directly
                return f(*args, **kwargs)
            
            op_name = operation_name or f.__name__
            
            def _call():
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    # Convert database errors to retryable errors
                    error_str = str(e).lower()
                    
                    # Connection errors
                    if any(x in error_str for x in [
                        "connection", "timeout", "timed out",
                        "cannot connect", "connection refused",
                        "connection reset", "broken pipe"
                    ]):
                        raise NetworkError(f"Database connection error: {e}")
                    
                    # Transient errors
                    if any(x in error_str for x in [
                        "deadlock", "lock timeout", "lock wait timeout",
                        "serialization failure", "could not serialize",
                        "database is locked"
                    ]):
                        raise ServerError(f"Database lock/deadlock: {e}")
                    
                    # Server errors
                    if any(x in error_str for x in [
                        "server error", "internal error",
                        "out of memory", "too many connections"
                    ]):
                        raise ServerError(f"Database server error: {e}")
                    
                    # Re-raise non-retryable errors
                    raise
            
            try:
                result = retry_with_backoff(
                    _call,
                    policy_name=retry_policy_name,
                )
                logger.info(
                    f"Database operation successful: {op_name}",
                    extra={"operation": op_name}
                )
                return result
            except Exception as e:
                logger.error(
                    f"Database operation failed after retries: {op_name}",
                    extra={
                        "operation": op_name,
                        "error": str(e),
                    }
                )
                raise
        
        return wrapper
    
    if func is None:
        # Called with arguments: @with_database_retry(retry_policy_name="quick")
        return decorator
    else:
        # Called without arguments: @with_database_retry
        return decorator(func)


def register_database_health_check(
    check_function: Callable[[], bool],
    name: str = "database",
) -> None:
    """
    Register a database health check.
    
    Args:
        check_function: Function that returns True if database is healthy
        name: Health check name
        
    Example:
        def check_db_connection():
            try:
                db.execute("SELECT 1")
                return True
            except Exception as e:
                logger.debug(f"Database health check failed: {e}")
                return False
        
        register_database_health_check(check_db_connection, "postgresql")
    """
    config = load_runtime_config()
    
    if not config.health_checks.enabled:
        logger.info(f"Health checks disabled, skipping registration for {name}")
        return
    
    registry = get_health_registry()
    
    health_check = SimpleHealthCheck(
        check=check_function,
        name=name,
    )
    
    registry.register(name, health_check)
    logger.info(
        f"Registered database health check: {name}",
        extra={"health_check": name}
    )


class HardenedDatabaseConnection:
    """
    Wrapper around database connection with production hardening.
    
    Features:
    - Automatic retry on transient failures
    - Health check registration
    - Structured logging
    """
    
    def __init__(
        self,
        connection: Any,
        retry_policy_name: str = "quick",
        enable_retry: bool = True,
        enable_health_checks: bool = True,
    ):
        """
        Initialize hardened database connection.
        
        Args:
            connection: Underlying database connection
            retry_policy_name: Retry policy name
            enable_retry: Enable retry logic
            enable_health_checks: Enable health check registration
        """
        self.connection = connection
        self.retry_policy_name = retry_policy_name
        
        # Load runtime config
        config = load_runtime_config()
        
        self.enable_retry = enable_retry and config.retry.enabled
        self.enable_health_checks = enable_health_checks and config.health_checks.enabled
        
        # Register health check
        if self.enable_health_checks:
            def _check():
                try:
                    # Try to execute simple query
                    cursor = self.connection.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    return True
                except Exception as e:
                    logger.debug(f"Database cursor health check failed: {e}")
                    return False
            
            register_database_health_check(_check, "database_connection")
    
    def execute(self, query: str, *args, **kwargs) -> Any:
        """
        Execute query with retry logic.
        
        Args:
            query: SQL query
            *args: Query arguments
            **kwargs: Query keyword arguments
            
        Returns:
            Query result
        """
        @with_database_retry(retry_policy_name=self.retry_policy_name, operation_name="execute")
        def _execute():
            cursor = self.connection.cursor()
            cursor.execute(query, *args, **kwargs)
            return cursor
        
        if self.enable_retry:
            return _execute()
        else:
            cursor = self.connection.cursor()
            cursor.execute(query, *args, **kwargs)
            return cursor
    
    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to underlying connection."""
        return getattr(self.connection, name)


def harden_database_connection(
    connection: Any,
    retry_policy_name: str = "quick",
) -> HardenedDatabaseConnection:
    """
    Wrap a database connection with production hardening.
    
    Args:
        connection: Database connection to wrap
        retry_policy_name: Retry policy name
        
    Returns:
        HardenedDatabaseConnection instance
        
    Example:
        >>> import psycopg2
        >>> conn = psycopg2.connect("postgresql://localhost/db")
        >>> hardened = harden_database_connection(conn)
        >>> cursor = hardened.execute("SELECT * FROM tests")
    """
    return HardenedDatabaseConnection(
        connection=connection,
        retry_policy_name=retry_policy_name,
    )
