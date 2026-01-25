"""
Rate Limiting Implementation

Token bucket algorithm for fair, predictable rate limiting per user/org/key.

Features:
- Per-key rate limiting (user_id, org_id, api_key)
- Token bucket algorithm with smooth refill
- Thread-safe operations
- Memory-efficient (can be Redis-backed later)
- YAML configuration support

Usage:
    rate_limiter = RateLimiter()
    
    if not rate_limiter.check(user_id="user123", capacity=60, window_seconds=60):
        raise Exception("Rate limit exceeded: 60 requests per minute")
"""

from dataclasses import dataclass
from time import time
from typing import Dict, Optional
import threading

from core.logging import get_logger, LogCategory
from .config import get_rate_limit_for_operation, load_runtime_config

logger = get_logger(__name__, category=LogCategory.GENERAL)


@dataclass
class RateLimit:
    """Rate limit configuration for a specific key."""
    
    key: str              # user_id / org_id / api_key
    limit: int            # max requests
    window_seconds: int   # rolling window in seconds
    
    def __post_init__(self):
        if self.limit <= 0:
            raise ValueError(f"Rate limit must be positive, got {self.limit}")
        if self.window_seconds <= 0:
            raise ValueError(f"Window seconds must be positive, got {self.window_seconds}")


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    
    Tokens refill continuously at a constant rate.
    Each request consumes one token.
    
    Attributes:
        capacity: Maximum tokens in the bucket
        tokens: Current available tokens
        refill_rate: Tokens added per second
        last_refill: Timestamp of last refill
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum tokens (burst limit)
            refill_rate: Tokens per second (e.g., 1.0 = 1 token/sec)
        """
        if capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {capacity}")
        if refill_rate <= 0:
            raise ValueError(f"Refill rate must be positive, got {refill_rate}")
        
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time()
        self._lock = threading.Lock()
    
    def allow(self, tokens: int = 1) -> bool:
        """
        Check if request is allowed and consume tokens.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            True if request allowed, False if rate limit exceeded
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now
    
    def get_available_tokens(self) -> float:
        """Get current available tokens (for monitoring)."""
        with self._lock:
            self._refill()
            return self.tokens
    
    def reset(self):
        """Reset bucket to full capacity."""
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_refill = time()


class RateLimiter:
    """
    Manages rate limiting across multiple keys.
    
    Features:
    - Per-key token buckets
    - Automatic bucket creation
    - Thread-safe operations
    - Memory cleanup for inactive keys
    
    Usage:
        limiter = RateLimiter()
        
        # Check rate limit: 60 requests per 60 seconds
        if limiter.check(key="user123", capacity=60, window_seconds=60):
            # Process request
            pass
        else:
            # Reject request
            raise RateLimitExceeded()
    """
    
    def __init__(self, cleanup_threshold: int = 1000):
        """
        Initialize rate limiter.
        
        Args:
            cleanup_threshold: Max buckets before cleanup (default: 1000)
        """
        self.buckets: Dict[str, TokenBucket] = {}
        self.cleanup_threshold = cleanup_threshold
        self._lock = threading.Lock()
    
    def check(
        self, 
        key: str, 
        capacity: int, 
        window_seconds: int,
        tokens: int = 1
    ) -> bool:
        """
        Check if request is allowed for given key.
        
        Args:
            key: Unique identifier (user_id, org_id, api_key)
            capacity: Max requests allowed
            window_seconds: Time window in seconds
            tokens: Tokens to consume (default: 1)
            
        Returns:
            True if allowed, False if rate limit exceeded
            
        Example:
            # Allow 30 requests per minute per user
            if limiter.check("user123", capacity=30, window_seconds=60):
                process_request()
        """
        refill_rate = capacity / window_seconds
        
        with self._lock:
            # Get or create bucket
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(capacity, refill_rate)
                
                # Cleanup old buckets if threshold exceeded
                if len(self.buckets) > self.cleanup_threshold:
                    self._cleanup_inactive_buckets()
            
            bucket = self.buckets[key]
        
        return bucket.allow(tokens)
    
    def get_remaining(
        self, 
        key: str, 
        capacity: int, 
        window_seconds: int
    ) -> Optional[float]:
        """
        Get remaining tokens for a key.
        
        Args:
            key: Rate limit key
            capacity: Max capacity
            window_seconds: Time window
            
        Returns:
            Available tokens, or None if bucket doesn't exist
        """
        with self._lock:
            if key not in self.buckets:
                return float(capacity)
            
            return self.buckets[key].get_available_tokens()
    
    def reset(self, key: str):
        """Reset rate limit for a specific key."""
        with self._lock:
            if key in self.buckets:
                self.buckets[key].reset()
    
    def reset_all(self):
        """Reset all rate limits."""
        with self._lock:
            for bucket in self.buckets.values():
                bucket.reset()
    
    def _cleanup_inactive_buckets(self):
        """Remove buckets that are at full capacity (inactive)."""
        keys_to_remove = [
            key for key, bucket in self.buckets.items()
            if bucket.get_available_tokens() >= bucket.capacity
        ]
        
        for key in keys_to_remove[:len(keys_to_remove) // 2]:  # Remove half
            del self.buckets[key]
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        with self._lock:
            return {
                'total_buckets': len(self.buckets),
                'buckets': {
                    key: {
                        'capacity': bucket.capacity,
                        'available': bucket.get_available_tokens(),
                        'refill_rate': bucket.refill_rate
                    }
                    for key, bucket in list(self.buckets.items())[:10]  # Limit output
                }
            }


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, key: str, limit: int, window: int):
        self.key = key
        self.limit = limit
        self.window = window
        super().__init__(
            f"Rate limit exceeded for '{key}': {limit} requests per {window}s"
        )


# Global rate limiter instance (can be replaced with Redis-backed version)
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    
    return _global_rate_limiter


def check_rate_limit(
    key: str,
    capacity: int,
    window_seconds: int,
    raise_on_exceeded: bool = True
) -> bool:
    """
    Convenience function for rate limit checking.
    
    Args:
        key: Rate limit key
        capacity: Max requests
        window_seconds: Time window
        raise_on_exceeded: Raise exception if exceeded (default: True)
        
    Returns:
        True if allowed, False if exceeded (when raise_on_exceeded=False)
        
    Raises:
        RateLimitExceeded: If rate limit exceeded and raise_on_exceeded=True
    """
    limiter = get_rate_limiter()
    allowed = limiter.check(key, capacity, window_seconds)
    
    if not allowed and raise_on_exceeded:
        raise RateLimitExceeded(key, capacity, window_seconds)
    
    return allowed
