"""
Error Handling and Retry Infrastructure for Log Adapters

Provides common error handling, retry logic, and resilience patterns
for log ingestion operations.
"""

import logging
import time
from typing import Callable, Any, Optional, Type
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 0.1  # seconds
    max_delay: float = 5.0      # seconds
    exponential_base: float = 2.0
    retry_on_exceptions: tuple = (Exception,)


class LogAdapterError(Exception):
    """Base exception for log adapter errors."""
    pass


class LogParsingError(LogAdapterError):
    """Error during log parsing."""
    pass


class LogStorageError(LogAdapterError):
    """Error during log storage."""
    pass


class LogCorrelationError(LogAdapterError):
    """Error during log correlation."""
    pass


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to functions.
    
    Args:
        config: Retry configuration (uses defaults if None)
    
    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        def store_logs(logs):
            # Implementation
            pass
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = config.initial_delay
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                
                except config.retry_on_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts: {e}",
                            exc_info=True
                        )
                        raise
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{config.max_attempts}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * config.exponential_base, config.max_delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def with_error_handling(
    error_type: Type[LogAdapterError] = LogAdapterError,
    default_return: Any = None,
    log_error: bool = True
):
    """
    Decorator to add error handling to functions.
    
    Args:
        error_type: Exception type to raise
        default_return: Value to return on error
        log_error: Whether to log the error
    
    Usage:
        @with_error_handling(error_type=LogParsingError, default_return=None)
        def parse_log(line):
            # Implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                if log_error:
                    logger.error(
                        f"Error in {func.__name__}: {e}",
                        exc_info=True
                    )
                
                # Return default value for graceful degradation
                if default_return is not None or error_type is None:
                    return default_return
                
                # Re-raise as adapter-specific error
                raise error_type(f"Error in {func.__name__}: {e}") from e
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for protecting downstream systems.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if system recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes to close circuit from half-open
            timeout: Seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            LogAdapterError: If circuit is open
        """
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise LogAdapterError(
                    f"Circuit breaker is OPEN. "
                    f"Will retry after {self.timeout}s from last failure."
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == 'HALF_OPEN':
            self.success_count += 1
            
            if self.success_count >= self.success_threshold:
                self.state = 'CLOSED'
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker CLOSED after successful recovery")
        
        elif self.state == 'CLOSED':
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == 'HALF_OPEN':
            self.state = 'OPEN'
            self.success_count = 0
            logger.warning("Circuit breaker OPEN after failure in HALF_OPEN state")
        
        elif self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )


class RateLimiter:
    """
    Token bucket rate limiter for controlling ingestion rate.
    """
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize rate limiter.
        
        Args:
            rate: Tokens per second
            capacity: Maximum token bucket size
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens.
        
        Args:
            tokens: Number of tokens to acquire
        
        Returns:
            True if tokens acquired, False otherwise
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def _refill(self):
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on rate
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now


# Global circuit breaker instances (can be configured per adapter)
_circuit_breakers = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.
    
    Args:
        name: Circuit breaker identifier
        **kwargs: CircuitBreaker constructor arguments
    
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(**kwargs)
    
    return _circuit_breakers[name]
