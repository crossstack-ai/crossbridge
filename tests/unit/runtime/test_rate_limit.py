"""
Unit Tests for Rate Limiting

Comprehensive tests for TokenBucket and RateLimiter.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from core.runtime.rate_limit import (
    RateLimit,
    TokenBucket,
    RateLimiter,
    RateLimitExceeded,
    check_rate_limit,
    get_rate_limiter
)


class TestRateLimit:
    """Tests for RateLimit dataclass."""
    
    def test_valid_rate_limit(self):
        """Test valid rate limit creation."""
        rate_limit = RateLimit(key="user123", limit=60, window_seconds=60)
        
        assert rate_limit.key == "user123"
        assert rate_limit.limit == 60
        assert rate_limit.window_seconds == 60
    
    def test_invalid_limit(self):
        """Test rate limit with invalid limit."""
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            RateLimit(key="user123", limit=0, window_seconds=60)
        
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            RateLimit(key="user123", limit=-10, window_seconds=60)
    
    def test_invalid_window(self):
        """Test rate limit with invalid window."""
        with pytest.raises(ValueError, match="Window seconds must be positive"):
            RateLimit(key="user123", limit=60, window_seconds=0)
        
        with pytest.raises(ValueError, match="Window seconds must be positive"):
            RateLimit(key="user123", limit=60, window_seconds=-5)


class TestTokenBucket:
    """Tests for TokenBucket algorithm."""
    
    def test_initialization(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        assert bucket.capacity == 10
        assert bucket.tokens == 10.0
        assert bucket.refill_rate == 1.0
        assert bucket.get_available_tokens() == 10.0
    
    def test_invalid_capacity(self):
        """Test bucket with invalid capacity."""
        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucket(capacity=0, refill_rate=1.0)
        
        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucket(capacity=-5, refill_rate=1.0)
    
    def test_invalid_refill_rate(self):
        """Test bucket with invalid refill rate."""
        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucket(capacity=10, refill_rate=0.0)
        
        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucket(capacity=10, refill_rate=-1.0)
    
    def test_allow_within_capacity(self):
        """Test allowing requests within capacity."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Should allow 5 requests
        for i in range(5):
            assert bucket.allow() is True, f"Request {i+1} should be allowed"
        
        # 6th request should be denied
        assert bucket.allow() is False, "6th request should be denied"
    
    def test_allow_multiple_tokens(self):
        """Test consuming multiple tokens at once."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Consume 5 tokens
        assert bucket.allow(tokens=5) is True
        assert 4.9 <= bucket.get_available_tokens() <= 5.1  # Allow small refill
        
        # Consume another 5 tokens
        assert bucket.allow(tokens=5) is True
        available = bucket.get_available_tokens()
        assert available < 0.1  # Nearly empty (allow small refill)
        
        # Should be denied now
        assert bucket.allow(tokens=1) is False
    
    def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec
        
        # Consume all tokens
        for _ in range(10):
            assert bucket.allow() is True
        
        assert bucket.allow() is False
        
        # Wait 0.5 seconds (should refill 5 tokens)
        time.sleep(0.5)
        
        # Should allow approximately 5 requests
        allowed = sum(1 for _ in range(10) if bucket.allow())
        assert 4 <= allowed <= 6, f"Expected ~5 tokens, got {allowed}"
    
    def test_refill_does_not_exceed_capacity(self):
        """Test that refill doesn't exceed capacity."""
        bucket = TokenBucket(capacity=5, refill_rate=10.0)
        
        # Wait for refill (already at capacity)
        time.sleep(1.0)
        
        # Should still only allow 5 requests
        for i in range(5):
            assert bucket.allow() is True, f"Request {i+1} should be allowed"
        
        assert bucket.allow() is False, "Should not exceed capacity"
    
    def test_reset(self):
        """Test bucket reset."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Consume all tokens
        for _ in range(5):
            bucket.allow()
        
        available = bucket.get_available_tokens()
        assert available < 0.1  # Nearly empty (allow small refill)
        
        # Reset
        bucket.reset()
        
        assert bucket.get_available_tokens() == 5.0
        
        # Should allow 5 requests again
        for i in range(5):
            assert bucket.allow() is True
    
    def test_thread_safety(self):
        """Test thread-safe token consumption."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        allowed_count = [0]
        denied_count = [0]
        
        def consume():
            for _ in range(20):
                if bucket.allow():
                    allowed_count[0] += 1
                else:
                    denied_count[0] += 1
        
        threads = [threading.Thread(target=consume) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        total_attempts = allowed_count[0] + denied_count[0]
        assert total_attempts == 200  # 10 threads * 20 attempts
        assert allowed_count[0] <= 100, "Should not exceed capacity"


class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()
        
        assert len(limiter.buckets) == 0
        assert limiter.cleanup_threshold == 1000
    
    def test_check_first_request(self):
        """Test first request creates bucket."""
        limiter = RateLimiter()
        
        assert limiter.check("user123", capacity=60, window_seconds=60) is True
        assert "user123" in limiter.buckets
    
    def test_check_within_limit(self):
        """Test requests within rate limit."""
        limiter = RateLimiter()
        
        # Allow 10 requests per second
        for i in range(10):
            assert limiter.check("user123", capacity=10, window_seconds=1) is True
    
    def test_check_exceeds_limit(self):
        """Test requests exceeding rate limit."""
        limiter = RateLimiter()
        
        # Allow 5 requests per second
        for i in range(5):
            assert limiter.check("user123", capacity=5, window_seconds=1) is True
        
        # 6th request should be denied
        assert limiter.check("user123", capacity=5, window_seconds=1) is False
    
    def test_different_keys(self):
        """Test rate limiting with different keys."""
        limiter = RateLimiter()
        
        # Each user has their own limit
        for i in range(5):
            assert limiter.check("user1", capacity=5, window_seconds=1) is True
            assert limiter.check("user2", capacity=5, window_seconds=1) is True
        
        # Both users should be at limit
        assert limiter.check("user1", capacity=5, window_seconds=1) is False
        assert limiter.check("user2", capacity=5, window_seconds=1) is False
    
    def test_get_remaining(self):
        """Test getting remaining tokens."""
        limiter = RateLimiter()
        
        # Before any requests
        remaining = limiter.get_remaining("user123", capacity=10, window_seconds=1)
        assert remaining == 10.0
        
        # After 3 requests
        for _ in range(3):
            limiter.check("user123", capacity=10, window_seconds=1)
        
        remaining = limiter.get_remaining("user123", capacity=10, window_seconds=1)
        assert 6.0 <= remaining <= 8.0  # Allow for refill during execution
    
    def test_reset_key(self):
        """Test resetting rate limit for specific key."""
        limiter = RateLimiter()
        
        # Consume all tokens
        for _ in range(5):
            limiter.check("user123", capacity=5, window_seconds=1)
        
        assert limiter.check("user123", capacity=5, window_seconds=1) is False
        
        # Reset
        limiter.reset("user123")
        
        # Should allow requests again
        assert limiter.check("user123", capacity=5, window_seconds=1) is True
    
    def test_reset_all(self):
        """Test resetting all rate limits."""
        limiter = RateLimiter()
        
        # Consume tokens for multiple users
        for _ in range(5):
            limiter.check("user1", capacity=5, window_seconds=1)
            limiter.check("user2", capacity=5, window_seconds=1)
        
        # Reset all
        limiter.reset_all()
        
        # Both users should be able to make requests
        assert limiter.check("user1", capacity=5, window_seconds=1) is True
        assert limiter.check("user2", capacity=5, window_seconds=1) is True
    
    def test_cleanup_inactive_buckets(self):
        """Test automatic cleanup of inactive buckets."""
        limiter = RateLimiter(cleanup_threshold=10)
        
        # Create many buckets (all with same capacity)
        for i in range(15):
            limiter.check(f"user{i}", capacity=10, window_seconds=1)
        
        # Wait for buckets to refill to full capacity (so they're considered inactive)
        time.sleep(1.5)
        
        # Trigger cleanup by exceeding threshold
        limiter.check("user_new", capacity=10, window_seconds=1)
        
        # Some buckets should be cleaned up (should be <= 11: 10 threshold + 1 new)
        assert len(limiter.buckets) <= 11, f"Expected <= 11 buckets after cleanup, got {len(limiter.buckets)}"
    
    def test_get_stats(self):
        """Test getting rate limiter statistics."""
        limiter = RateLimiter()
        
        # Create some buckets
        limiter.check("user1", capacity=10, window_seconds=1)
        limiter.check("user2", capacity=20, window_seconds=2)
        
        stats = limiter.get_stats()
        
        assert stats['total_buckets'] == 2
        assert 'buckets' in stats
        assert 'user1' in stats['buckets'] or 'user2' in stats['buckets']
    
    def test_multi_token_consumption(self):
        """Test consuming multiple tokens per request."""
        limiter = RateLimiter()
        
        # Allow 10 tokens, consume 5 per request
        assert limiter.check("user123", capacity=10, window_seconds=1, tokens=5) is True
        assert limiter.check("user123", capacity=10, window_seconds=1, tokens=5) is True
        assert limiter.check("user123", capacity=10, window_seconds=1, tokens=5) is False


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""
    
    def test_exception_creation(self):
        """Test exception creation."""
        exc = RateLimitExceeded("user123", 60, 60)
        
        assert exc.key == "user123"
        assert exc.limit == 60
        assert exc.window == 60
        assert "user123" in str(exc)
        assert "60 requests per 60s" in str(exc)


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_get_rate_limiter_singleton(self):
        """Test global rate limiter singleton."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        assert limiter1 is limiter2
    
    def test_check_rate_limit_allowed(self):
        """Test convenience function when allowed."""
        limiter = get_rate_limiter()
        limiter.reset_all()
        
        result = check_rate_limit("test_user", capacity=5, window_seconds=1)
        assert result is True
    
    def test_check_rate_limit_exceeded_raises(self):
        """Test convenience function raises on exceeded."""
        limiter = get_rate_limiter()
        limiter.reset_all()
        
        # Consume all tokens
        for _ in range(5):
            check_rate_limit("test_user2", capacity=5, window_seconds=1)
        
        # Should raise
        with pytest.raises(RateLimitExceeded) as exc_info:
            check_rate_limit("test_user2", capacity=5, window_seconds=1)
        
        assert exc_info.value.key == "test_user2"
        assert exc_info.value.limit == 5
    
    def test_check_rate_limit_exceeded_no_raise(self):
        """Test convenience function returns False without raising."""
        limiter = get_rate_limiter()
        limiter.reset_all()
        
        # Consume all tokens
        for _ in range(5):
            check_rate_limit("test_user3", capacity=5, window_seconds=1, raise_on_exceeded=False)
        
        # Should return False
        result = check_rate_limit("test_user3", capacity=5, window_seconds=1, raise_on_exceeded=False)
        assert result is False


class TestRateLimitingScenarios:
    """Real-world rate limiting scenarios."""
    
    def test_api_rate_limiting(self):
        """Test typical API rate limiting (60 req/min)."""
        limiter = RateLimiter()
        user_id = "api_user"
        
        # Allow 60 requests per minute
        allowed = 0
        denied = 0
        
        for _ in range(70):
            if limiter.check(user_id, capacity=60, window_seconds=60):
                allowed += 1
            else:
                denied += 1
        
        assert allowed == 60, f"Expected 60 allowed, got {allowed}"
        assert denied == 10, f"Expected 10 denied, got {denied}"
    
    def test_burst_handling(self):
        """Test handling burst traffic."""
        limiter = RateLimiter()
        
        # Allow 100 requests per second (burst capacity)
        for i in range(100):
            assert limiter.check("burst_user", capacity=100, window_seconds=1) is True
        
        # 101st should be denied
        assert limiter.check("burst_user", capacity=100, window_seconds=1) is False
    
    def test_gradual_refill(self):
        """Test gradual token refill."""
        limiter = RateLimiter()
        
        # Consume all tokens
        for _ in range(10):
            limiter.check("refill_user", capacity=10, window_seconds=1)
        
        # Should be denied
        assert limiter.check("refill_user", capacity=10, window_seconds=1) is False
        
        # Wait 0.5 seconds (should refill ~5 tokens at 10/sec)
        time.sleep(0.5)
        
        # Should allow some requests
        allowed = sum(
            1 for _ in range(10) 
            if limiter.check("refill_user", capacity=10, window_seconds=1)
        )
        assert 3 <= allowed <= 7, f"Expected ~5 tokens, got {allowed}"
    
    def test_multi_tenant_fairness(self):
        """Test fairness across multiple tenants."""
        limiter = RateLimiter()
        
        users = [f"user{i}" for i in range(10)]
        
        # Each user should get their fair share
        for user in users:
            for _ in range(5):
                assert limiter.check(user, capacity=5, window_seconds=1) is True
            
            # 6th request should be denied
            assert limiter.check(user, capacity=5, window_seconds=1) is False
    
    def test_different_rate_limits_per_tier(self):
        """Test different rate limits for different user tiers."""
        limiter = RateLimiter()
        
        # Free tier: 10 req/min
        free_user = "free_user"
        for _ in range(10):
            assert limiter.check(free_user, capacity=10, window_seconds=60) is True
        assert limiter.check(free_user, capacity=10, window_seconds=60) is False
        
        # Premium tier: 100 req/min
        premium_user = "premium_user"
        for _ in range(100):
            assert limiter.check(premium_user, capacity=100, window_seconds=60) is True
        assert limiter.check(premium_user, capacity=100, window_seconds=60) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
