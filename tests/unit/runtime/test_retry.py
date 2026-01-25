"""
Unit Tests for Retry Logic

Comprehensive tests for retry policies and exponential backoff.
"""

import pytest
import time
from unittest.mock import Mock, patch, call

from core.runtime.retry import (
    RetryPolicy,
    RetryStats,
    RetryableError,
    NetworkError,
    RateLimitError,
    ServerError,
    NonRetryableError,
    AuthenticationError,
    ValidationError,
    calculate_delay,
    should_retry,
    retry_with_backoff,
    retryable,
    convert_http_error_to_retry,
    AGGRESSIVE_RETRY,
    CONSERVATIVE_RETRY,
    QUICK_RETRY
)


class TestRetryPolicy:
    """Tests for RetryPolicy configuration."""
    
    def test_default_policy(self):
        """Test default retry policy."""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 0.5
        assert policy.max_delay == 5.0
        assert policy.exponential_base == 2.0
        assert policy.jitter is True
    
    def test_custom_policy(self):
        """Test custom retry policy."""
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=3.0,
            jitter=False
        )
        
        assert policy.max_attempts == 5
        assert policy.base_delay == 1.0
        assert policy.max_delay == 10.0
        assert policy.exponential_base == 3.0
        assert policy.jitter is False
    
    def test_invalid_max_attempts(self):
        """Test policy with invalid max attempts."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            RetryPolicy(max_attempts=0)
        
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            RetryPolicy(max_attempts=-1)
    
    def test_invalid_base_delay(self):
        """Test policy with invalid base delay."""
        with pytest.raises(ValueError, match="base_delay must be >= 0"):
            RetryPolicy(base_delay=-0.5)
    
    def test_invalid_max_delay(self):
        """Test policy with invalid max delay."""
        with pytest.raises(ValueError, match="max_delay.*must be >= base_delay"):
            RetryPolicy(base_delay=5.0, max_delay=1.0)
    
    def test_invalid_exponential_base(self):
        """Test policy with invalid exponential base."""
        with pytest.raises(ValueError, match="exponential_base must be >= 1"):
            RetryPolicy(exponential_base=0.5)


class TestRetryStats:
    """Tests for RetryStats tracking."""
    
    def test_initialization(self):
        """Test stats initialization."""
        stats = RetryStats()
        
        assert stats.total_attempts == 0
        assert stats.successful_attempt is None
        assert stats.total_delay == 0.0
        assert len(stats.exceptions) == 0
    
    def test_record_attempt(self):
        """Test recording attempts."""
        stats = RetryStats()
        
        # Record failed attempt
        error = ValueError("test error")
        stats.record_attempt(1, error)
        
        assert stats.total_attempts == 1
        assert len(stats.exceptions) == 1
        assert stats.exceptions[0] == error
        
        # Record successful attempt
        stats.record_attempt(2)
        
        assert stats.total_attempts == 2
        assert stats.successful_attempt == 2
    
    def test_record_delay(self):
        """Test recording delays."""
        stats = RetryStats()
        
        stats.record_delay(0.5)
        stats.record_delay(1.0)
        stats.record_delay(2.0)
        
        assert stats.total_delay == 3.5
    
    def test_to_dict(self):
        """Test stats serialization."""
        stats = RetryStats()
        stats.record_attempt(1, ValueError("error1"))
        stats.record_attempt(2, TypeError("error2"))
        stats.record_delay(1.5)
        stats.record_attempt(3)
        
        data = stats.to_dict()
        
        assert data['total_attempts'] == 3
        assert data['successful_attempt'] == 3
        assert data['total_delay_seconds'] == 1.5
        assert data['failed_attempts'] == 2
        assert data['exception_types'] == ['ValueError', 'TypeError']


class TestCalculateDelay:
    """Tests for delay calculation."""
    
    def test_exponential_backoff_base2(self):
        """Test exponential backoff with base 2."""
        # base_delay * (2 ^ (attempt - 1))
        assert calculate_delay(1, 1.0, 10.0, 2.0, jitter=False) == 1.0   # 1.0 * 2^0
        assert calculate_delay(2, 1.0, 10.0, 2.0, jitter=False) == 2.0   # 1.0 * 2^1
        assert calculate_delay(3, 1.0, 10.0, 2.0, jitter=False) == 4.0   # 1.0 * 2^2
        assert calculate_delay(4, 1.0, 10.0, 2.0, jitter=False) == 8.0   # 1.0 * 2^3
    
    def test_exponential_backoff_base3(self):
        """Test exponential backoff with base 3."""
        assert calculate_delay(1, 1.0, 100.0, 3.0, jitter=False) == 1.0   # 1.0 * 3^0
        assert calculate_delay(2, 1.0, 100.0, 3.0, jitter=False) == 3.0   # 1.0 * 3^1
        assert calculate_delay(3, 1.0, 100.0, 3.0, jitter=False) == 9.0   # 1.0 * 3^2
    
    def test_max_delay_cap(self):
        """Test delay capped at max_delay."""
        delay = calculate_delay(10, 1.0, 5.0, 2.0, jitter=False)
        assert delay == 5.0  # Would be 512.0 without cap
    
    def test_jitter_adds_randomness(self):
        """Test jitter adds randomness."""
        delays = [
            calculate_delay(3, 1.0, 10.0, 2.0, jitter=True)
            for _ in range(10)
        ]
        
        # Should have some variation
        assert len(set(delays)) > 1, "Jitter should add randomness"
        
        # All should be within jitter range (2.0 to 6.0 for 4.0 * [0.5, 1.5])
        for delay in delays:
            assert 2.0 <= delay <= 6.0
    
    def test_no_jitter_is_deterministic(self):
        """Test without jitter is deterministic."""
        delays = [
            calculate_delay(3, 1.0, 10.0, 2.0, jitter=False)
            for _ in range(10)
        ]
        
        # All should be identical
        assert len(set(delays)) == 1
        assert delays[0] == 4.0


class TestShouldRetry:
    """Tests for retry decision logic."""
    
    def test_retry_retryable_errors(self):
        """Test retrying retryable errors."""
        policy = RetryPolicy()
        
        assert should_retry(RetryableError(), policy) is True
        assert should_retry(NetworkError(), policy) is True
        assert should_retry(RateLimitError(), policy) is True
        assert should_retry(ServerError(), policy) is True
        assert should_retry(TimeoutError(), policy) is True
        assert should_retry(ConnectionError(), policy) is True
    
    def test_no_retry_non_retryable_errors(self):
        """Test not retrying non-retryable errors."""
        policy = RetryPolicy()
        
        assert should_retry(NonRetryableError(), policy) is False
        assert should_retry(AuthenticationError(), policy) is False
        assert should_retry(ValidationError(), policy) is False
        assert should_retry(ValueError(), policy) is False
        assert should_retry(TypeError(), policy) is False
        assert should_retry(KeyError(), policy) is False
    
    def test_unknown_exception_not_retried(self):
        """Test unknown exceptions are not retried by default."""
        policy = RetryPolicy()
        
        class CustomError(Exception):
            pass
        
        assert should_retry(CustomError(), policy) is False


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""
    
    def test_success_on_first_try(self):
        """Test success on first attempt (no retry)."""
        mock_func = Mock(return_value="success")
        
        result = retry_with_backoff(mock_func, RetryPolicy(max_attempts=3))
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_success_after_retries(self):
        """Test success after some retries."""
        mock_func = Mock(side_effect=[
            NetworkError("timeout"),
            NetworkError("timeout"),
            "success"
        ])
        
        result = retry_with_backoff(
            mock_func, 
            RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False)
        )
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_failure_after_max_attempts(self):
        """Test failure after exhausting retries."""
        mock_func = Mock(side_effect=NetworkError("persistent error"))
        
        with pytest.raises(NetworkError, match="persistent error"):
            retry_with_backoff(
                mock_func,
                RetryPolicy(max_attempts=3, base_delay=0.01)
            )
        
        assert mock_func.call_count == 3
    
    def test_non_retryable_error_no_retry(self):
        """Test non-retryable error fails immediately."""
        mock_func = Mock(side_effect=ValidationError("bad input"))
        
        with pytest.raises(ValidationError, match="bad input"):
            retry_with_backoff(
                mock_func,
                RetryPolicy(max_attempts=3, base_delay=0.01)
            )
        
        assert mock_func.call_count == 1  # No retries
    
    def test_exponential_backoff_timing(self):
        """Test exponential backoff delays."""
        mock_func = Mock(side_effect=[
            NetworkError(),
            NetworkError(),
            "success"
        ])
        
        start_time = time.time()
        
        retry_with_backoff(
            mock_func,
            RetryPolicy(max_attempts=3, base_delay=0.1, jitter=False)
        )
        
        elapsed = time.time() - start_time
        
        # Expected delays: 0.1s (attempt 1) + 0.2s (attempt 2) = 0.3s minimum
        assert elapsed >= 0.3, f"Expected >= 0.3s, got {elapsed}s"
    
    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        mock_func = Mock(side_effect=[
            NetworkError("error1"),
            NetworkError("error2"),
            "success"
        ])
        
        callback_calls = []
        
        def on_retry(attempt, exception, delay):
            callback_calls.append((attempt, type(exception).__name__, delay))
        
        retry_with_backoff(
            mock_func,
            RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False),
            on_retry=on_retry
        )
        
        assert len(callback_calls) == 2  # 2 retries
        assert callback_calls[0][0] == 1  # First retry after attempt 1
        assert callback_calls[0][1] == "NetworkError"
        assert callback_calls[1][0] == 2  # Second retry after attempt 2
    
    def test_callback_exception_does_not_break_retry(self):
        """Test callback exception doesn't break retry logic."""
        mock_func = Mock(side_effect=[
            NetworkError(),
            "success"
        ])
        
        def bad_callback(attempt, exception, delay):
            raise ValueError("callback error")
        
        # Should still succeed despite callback failure
        result = retry_with_backoff(
            mock_func,
            RetryPolicy(max_attempts=3, base_delay=0.01),
            on_retry=bad_callback
        )
        
        assert result == "success"


class TestRetryableDecorator:
    """Tests for @retryable decorator."""
    
    def test_decorator_success(self):
        """Test decorator with successful function."""
        call_count = [0]
        
        @retryable(RetryPolicy(max_attempts=3, base_delay=0.01))
        def fetch_data():
            call_count[0] += 1
            return "data"
        
        result = fetch_data()
        
        assert result == "data"
        assert call_count[0] == 1
    
    def test_decorator_with_retries(self):
        """Test decorator with retries."""
        call_count = [0]
        
        @retryable(RetryPolicy(max_attempts=3, base_delay=0.01))
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise NetworkError("network issue")
            return "success"
        
        result = flaky_function()
        
        assert result == "success"
        assert call_count[0] == 3
    
    def test_decorator_with_args(self):
        """Test decorator with function arguments."""
        @retryable(RetryPolicy(max_attempts=2, base_delay=0.01))
        def add(a, b):
            return a + b
        
        result = add(2, 3)
        assert result == 5
    
    def test_decorator_with_kwargs(self):
        """Test decorator with keyword arguments."""
        @retryable(RetryPolicy(max_attempts=2, base_delay=0.01))
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        result = greet("Alice", greeting="Hi")
        assert result == "Hi, Alice!"


class TestPredefinedPolicies:
    """Tests for predefined retry policies."""
    
    def test_aggressive_retry(self):
        """Test AGGRESSIVE_RETRY policy."""
        assert AGGRESSIVE_RETRY.max_attempts == 5
        assert AGGRESSIVE_RETRY.base_delay == 0.2
        assert AGGRESSIVE_RETRY.max_delay == 10.0
    
    def test_conservative_retry(self):
        """Test CONSERVATIVE_RETRY policy."""
        assert CONSERVATIVE_RETRY.max_attempts == 3
        assert CONSERVATIVE_RETRY.base_delay == 1.0
        assert CONSERVATIVE_RETRY.max_delay == 5.0
    
    def test_quick_retry(self):
        """Test QUICK_RETRY policy."""
        assert QUICK_RETRY.max_attempts == 2
        assert QUICK_RETRY.base_delay == 0.1
        assert QUICK_RETRY.max_delay == 1.0


class TestConvertHttpError:
    """Tests for HTTP error conversion."""
    
    def test_convert_rate_limit_error(self):
        """Test converting 429 to RateLimitError."""
        error = Exception("HTTP 429: Rate limit exceeded")
        converted = convert_http_error_to_retry(error)
        
        assert isinstance(converted, RateLimitError)
    
    def test_convert_server_errors(self):
        """Test converting 5xx to ServerError."""
        for code in ['500', '502', '503', '504']:
            error = Exception(f"HTTP {code}: Server error")
            converted = convert_http_error_to_retry(error)
            
            assert isinstance(converted, ServerError)
    
    def test_convert_timeout_error(self):
        """Test converting timeout to NetworkError."""
        error = Exception("Request timed out")
        converted = convert_http_error_to_retry(error)
        
        assert isinstance(converted, NetworkError)
    
    def test_convert_auth_errors(self):
        """Test converting 401/403 to AuthenticationError."""
        for code in ['401', '403']:
            error = Exception(f"HTTP {code}: Unauthorized")
            converted = convert_http_error_to_retry(error)
            
            assert isinstance(converted, AuthenticationError)
    
    def test_convert_validation_errors(self):
        """Test converting 400/422 to ValidationError."""
        for code in ['400', '422']:
            error = Exception(f"HTTP {code}: Bad request")
            converted = convert_http_error_to_retry(error)
            
            assert isinstance(converted, ValidationError)
    
    def test_unrecognized_error_passthrough(self):
        """Test unrecognized errors pass through unchanged."""
        error = Exception("Unknown error")
        converted = convert_http_error_to_retry(error)
        
        assert converted is error


class TestRetryScenarios:
    """Real-world retry scenarios."""
    
    def test_api_timeout_retry(self):
        """Test retrying API timeouts."""
        call_count = [0]
        
        def api_call():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TimeoutError("Connection timeout")
            return {"data": "success"}
        
        result = retry_with_backoff(
            api_call,
            RetryPolicy(max_attempts=3, base_delay=0.01)
        )
        
        assert result == {"data": "success"}
        assert call_count[0] == 3
    
    def test_rate_limit_with_backoff(self):
        """Test handling rate limits with backoff."""
        call_count = [0]
        
        def rate_limited_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise RateLimitError("Rate limit exceeded")
            return "success"
        
        result = retry_with_backoff(
            rate_limited_call,
            RetryPolicy(max_attempts=3, base_delay=0.01)
        )
        
        assert result == "success"
    
    def test_intermittent_network_failures(self):
        """Test handling intermittent network failures."""
        failures = [
            NetworkError("Connection refused"),
            NetworkError("DNS lookup failed"),
            None  # Success
        ]
        
        call_count = [0]
        
        def network_call():
            error = failures[call_count[0]]
            call_count[0] += 1
            if error:
                raise error
            return "data"
        
        result = retry_with_backoff(
            network_call,
            RetryPolicy(max_attempts=3, base_delay=0.01)
        )
        
        assert result == "data"
        assert call_count[0] == 3
    
    def test_auth_error_no_retry(self):
        """Test authentication errors are not retried."""
        call_count = [0]
        
        def authenticated_call():
            call_count[0] += 1
            raise AuthenticationError("Invalid token")
        
        with pytest.raises(AuthenticationError):
            retry_with_backoff(
                authenticated_call,
                RetryPolicy(max_attempts=3, base_delay=0.01)
            )
        
        assert call_count[0] == 1  # No retries
    
    def test_max_delay_prevents_long_waits(self):
        """Test max_delay prevents excessively long waits."""
        mock_func = Mock(side_effect=[
            NetworkError(),
            NetworkError(),
            NetworkError(),
            "success"
        ])
        
        start_time = time.time()
        
        retry_with_backoff(
            mock_func,
            RetryPolicy(
                max_attempts=4,
                base_delay=0.1,
                max_delay=0.5,  # Cap at 0.5s
                jitter=False
            )
        )
        
        elapsed = time.time() - start_time
        
        # Should be ~1.5s (3 retries * 0.5s max delay each)
        # Not 0.1 + 0.2 + 0.4 = 0.7s without cap, but since we cap at 0.5
        # it's 0.1 + 0.2 + 0.5 = 0.8s minimum
        assert elapsed < 1.5, f"Expected < 1.5s, got {elapsed}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
