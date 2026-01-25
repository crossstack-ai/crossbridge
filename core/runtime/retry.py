"""
Advanced Retry Logic with Exponential Backoff

Intelligent retry handling for transient failures with jitter to prevent thundering herd.

Features:
- Exponential backoff with jitter
- Configurable retry policies
- Selective retry (only transient errors)
- Retry budget enforcement
- Detailed retry metrics
- YAML configuration support

Usage:
    result = retry_with_backoff(
        lambda: api_call(),
        RetryPolicy(max_attempts=4, base_delay=0.5)
    )
"""

from dataclasses import dataclass, field
from typing import Callable, TypeVar, Optional, List, Type
import time
import random
from functools import wraps

from core.logging import get_logger, LogCategory
from .config import get_retry_policy_by_name, load_runtime_config

logger = get_logger(__name__, category=LogCategory.GENERAL)

T = TypeVar('T')


class RetryableError(Exception):
    """Base class for errors that should be retried."""
    pass


class NetworkError(RetryableError):
    """Network-related errors (timeouts, connection failures)."""
    pass


class RateLimitError(RetryableError):
    """Rate limit errors (429, quota exceeded)."""
    pass


class ServerError(RetryableError):
    """Server errors (5xx)."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should NOT be retried."""
    pass


class AuthenticationError(NonRetryableError):
    """Authentication failures (401, 403)."""
    pass


class ValidationError(NonRetryableError):
    """Validation errors (400, 422)."""
    pass


@dataclass
class RetryPolicy:
    """
    Retry policy configuration.
    
    Attributes:
        max_attempts: Maximum retry attempts (including initial try)
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff (default: 2)
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Exception types to retry
        non_retryable_exceptions: Exception types to never retry
    """
    
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 5.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (
        RetryableError,
        TimeoutError,
        ConnectionError,
    )
    non_retryable_exceptions: tuple = (
        NonRetryableError,
        ValueError,
        TypeError,
        KeyError,
    )
    
    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.base_delay < 0:
            raise ValueError(f"base_delay must be >= 0, got {self.base_delay}")
        if self.max_delay < self.base_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be >= base_delay ({self.base_delay})"
            )
        if self.exponential_base < 1:
            raise ValueError(
                f"exponential_base must be >= 1, got {self.exponential_base}"
            )


@dataclass
class RetryStats:
    """Statistics for a retry operation."""
    
    total_attempts: int = 0
    successful_attempt: Optional[int] = None
    total_delay: float = 0.0
    exceptions: List[Exception] = field(default_factory=list)
    
    def record_attempt(self, attempt: int, exception: Optional[Exception] = None):
        """Record an attempt."""
        self.total_attempts = attempt
        if exception:
            self.exceptions.append(exception)
        else:
            self.successful_attempt = attempt
    
    def record_delay(self, delay: float):
        """Record delay time."""
        self.total_delay += delay
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            'total_attempts': self.total_attempts,
            'successful_attempt': self.successful_attempt,
            'total_delay_seconds': round(self.total_delay, 3),
            'failed_attempts': len(self.exceptions),
            'exception_types': [type(e).__name__ for e in self.exceptions]
        }


def calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool
) -> float:
    """
    Calculate delay for retry attempt.
    
    Args:
        attempt: Current attempt number (1-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Exponential backoff base
        jitter: Whether to add random jitter
        
    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = base_delay * (exponential_base ** (attempt - 1))
    
    # Cap at max_delay
    delay = min(delay, max_delay)
    
    # Add jitter: multiply by random factor between 0.5 and 1.5
    if jitter:
        delay *= random.uniform(0.5, 1.5)
    
    return delay


def should_retry(
    exception: Exception,
    policy: RetryPolicy
) -> bool:
    """
    Determine if exception should be retried.
    
    Args:
        exception: The exception that occurred
        policy: Retry policy
        
    Returns:
        True if should retry, False otherwise
    """
    # Never retry non-retryable exceptions
    if isinstance(exception, policy.non_retryable_exceptions):
        return False
    
    # Always retry retryable exceptions
    if isinstance(exception, policy.retryable_exceptions):
        return True
    
    # Default: do not retry unknown exceptions
    return False


def retry_with_backoff(
    func: Callable[[], T],
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
) -> T:
    """
    Execute function with retry logic and exponential backoff.
    
    Args:
        func: Function to execute (should be idempotent)
        policy: Retry policy (default: RetryPolicy())
        on_retry: Optional callback(attempt, exception, delay) called before retry
        
    Returns:
        Result from successful function execution
        
    Raises:
        Last exception if all retries exhausted
        
    Example:
        result = retry_with_backoff(
            lambda: embedding_provider.embed(texts),
            RetryPolicy(max_attempts=4, base_delay=0.5)
        )
    """
    if policy is None:
        policy = RetryPolicy()
    
    stats = RetryStats()
    attempt = 0
    last_exception = None
    
    while True:
        attempt += 1
        
        try:
            result = func()
            stats.record_attempt(attempt)
            
            if attempt > 1:
                logger.info(
                    f"Retry succeeded on attempt {attempt}/{policy.max_attempts}",
                    extra={'retry_stats': stats.to_dict()}
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            stats.record_attempt(attempt, e)
            
            # Check if we should retry
            if attempt >= policy.max_attempts:
                logger.error(
                    f"All retry attempts exhausted ({policy.max_attempts})",
                    extra={'retry_stats': stats.to_dict()},
                    exc_info=True
                )
                raise
            
            if not should_retry(e, policy):
                logger.warning(
                    f"Non-retryable error: {type(e).__name__}: {e}",
                    extra={'attempt': attempt}
                )
                raise
            
            # Calculate delay
            delay = calculate_delay(
                attempt,
                policy.base_delay,
                policy.max_delay,
                policy.exponential_base,
                policy.jitter
            )
            stats.record_delay(delay)
            
            logger.warning(
                f"Retry attempt {attempt}/{policy.max_attempts} after "
                f"{delay:.2f}s delay. Error: {type(e).__name__}: {e}",
                extra={'retry_stats': stats.to_dict()}
            )
            
            # Call retry callback
            if on_retry:
                try:
                    on_retry(attempt, e, delay)
                except Exception as callback_error:
                    logger.error(
                        f"Error in retry callback: {callback_error}",
                        exc_info=True
                    )
            
            # Wait before retry
            time.sleep(delay)


def retryable(
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
):
    """
    Decorator to make a function retryable.
    
    Args:
        policy: Retry policy (default: RetryPolicy())
        on_retry: Optional callback(attempt, exception, delay)
        
    Example:
        @retryable(RetryPolicy(max_attempts=5))
        def fetch_data():
            return api.get("/data")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return retry_with_backoff(
                lambda: func(*args, **kwargs),
                policy=policy,
                on_retry=on_retry
            )
        return wrapper
    return decorator


# Predefined policies for common scenarios
AGGRESSIVE_RETRY = RetryPolicy(
    max_attempts=5,
    base_delay=0.2,
    max_delay=10.0
)

CONSERVATIVE_RETRY = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    max_delay=5.0
)

QUICK_RETRY = RetryPolicy(
    max_attempts=2,
    base_delay=0.1,
    max_delay=1.0
)


def convert_http_error_to_retry(exception: Exception) -> Exception:
    """
    Convert HTTP status codes to appropriate retry exceptions.
    
    Args:
        exception: Original exception
        
    Returns:
        Converted exception (RetryableError or NonRetryableError)
    """
    # Check for common HTTP status codes in exception message
    error_msg = str(exception).lower()
    
    if '429' in error_msg or 'rate limit' in error_msg:
        return RateLimitError(f"Rate limit: {exception}")
    
    if any(code in error_msg for code in ['500', '502', '503', '504']):
        return ServerError(f"Server error: {exception}")
    
    if 'timeout' in error_msg or 'timed out' in error_msg:
        return NetworkError(f"Timeout: {exception}")
    
    if any(code in error_msg for code in ['401', '403']):
        return AuthenticationError(f"Auth error: {exception}")
    
    if any(code in error_msg for code in ['400', '422']):
        return ValidationError(f"Validation error: {exception}")
    
    # Return original if can't classify
    return exception
