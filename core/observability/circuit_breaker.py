"""
Circuit Breaker Pattern for Observer Resilience

Implements circuit breaker to protect the sidecar observer from cascading failures.
If the observer repeatedly fails, it automatically opens the circuit and stops
attempting operations until recovery is detected.

Based on Michael Nygard's "Release It!" pattern.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, Dict
import threading
from collections import deque

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure detected, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    # Failure threshold to open circuit
    failure_threshold: int = 5
    
    # Success threshold to close circuit from half-open
    success_threshold: int = 2
    
    # Time to wait before attempting recovery (seconds)
    timeout: float = 60.0
    
    # Window size for tracking failures (seconds)
    window_size: float = 120.0
    
    # Exceptions that trigger circuit breaker
    monitored_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""
    
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Calls rejected due to open circuit
    
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    
    circuit_opened_count: int = 0
    circuit_closed_count: int = 0
    
    current_state: CircuitState = CircuitState.CLOSED
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.successful_calls + self.failed_calls
        if total == 0:
            return 1.0
        return self.successful_calls / total


class CircuitBreakerError(Exception):
    """Exception raised when circuit is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting observer operations.
    
    Automatically opens circuit after threshold failures,
    preventing cascading failures in the sidecar observer.
    
    Usage:
        breaker = CircuitBreaker(name="test-observer")
        
        @breaker.protected
        def observe_test():
            # This operation is now protected
            pass
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker
            config: Configuration (uses defaults if None)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None
        
        # Thread-safe operation
        self._lock = threading.RLock()
        
        # Sliding window for failures
        self._failure_window: deque = deque()
        
        # Metrics
        self.metrics = CircuitBreakerMetrics()
        
        logger.info(
            f"Circuit breaker '{name}' initialized",
            extra={
                "failure_threshold": self.config.failure_threshold,
                "timeout": self.config.timeout
            }
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._update_state()
            return self._state
    
    def _update_state(self):
        """Update circuit state based on current conditions."""
        now = datetime.utcnow()
        
        # Clean old failures from window
        cutoff = now - timedelta(seconds=self.config.window_size)
        while self._failure_window and self._failure_window[0] < cutoff:
            self._failure_window.popleft()
        
        # State transitions
        if self._state == CircuitState.OPEN:
            # Check if timeout expired -> move to half-open
            if self._opened_at and (now - self._opened_at).total_seconds() >= self.config.timeout:
                self._transition_to_half_open()
        
        elif self._state == CircuitState.HALF_OPEN:
            # Check if enough successes -> close circuit
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
            
            # Check if any failure -> reopen circuit
            elif self._failure_count > 0:
                self._transition_to_open()
        
        elif self._state == CircuitState.CLOSED:
            # Check if too many failures in window -> open circuit
            if len(self._failure_window) >= self.config.failure_threshold:
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        if self._state != CircuitState.OPEN:
            self._state = CircuitState.OPEN
            self._opened_at = datetime.utcnow()
            self.metrics.circuit_opened_count += 1
            
            logger.warning(
                f"Circuit breaker '{self.name}' OPENED",
                extra={
                    "failure_count": len(self._failure_window),
                    "threshold": self.config.failure_threshold,
                    "timeout": self.config.timeout
                }
            )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0
        
        logger.info(
            f"Circuit breaker '{self.name}' HALF_OPEN (testing recovery)",
            extra={"success_threshold": self.config.success_threshold}
        )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_window.clear()
        self.metrics.circuit_closed_count += 1
        
        logger.info(f"Circuit breaker '{self.name}' CLOSED (recovered)")
    
    def _record_success(self):
        """Record successful operation."""
        with self._lock:
            self.metrics.total_calls += 1
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = datetime.utcnow()
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
            
            self._update_state()
    
    def _record_failure(self):
        """Record failed operation."""
        with self._lock:
            now = datetime.utcnow()
            
            self.metrics.total_calls += 1
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = now
            
            # Add to sliding window
            self._failure_window.append(now)
            
            if self._state == CircuitState.HALF_OPEN:
                self._failure_count += 1
            
            self._update_state()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of function call
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function raises an exception
        """
        with self._lock:
            self._update_state()
            
            # Reject if circuit is open
            if self._state == CircuitState.OPEN:
                self.metrics.rejected_calls += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Will retry after {self.config.timeout}s"
                )
        
        # Attempt execution
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
            
        except self.config.monitored_exceptions as e:
            self._record_failure()
            logger.debug(
                f"Circuit breaker '{self.name}' recorded failure",
                extra={"exception": str(e), "state": self._state.value}
            )
            raise
    
    def protected(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with circuit breaker.
        
        Usage:
            @breaker.protected
            def my_function():
                pass
        """
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self._transition_to_closed()
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        with self._lock:
            self._update_state()
            self.metrics.current_state = self._state
            
            return {
                "name": self.name,
                "state": self._state.value,
                "total_calls": self.metrics.total_calls,
                "successful_calls": self.metrics.successful_calls,
                "failed_calls": self.metrics.failed_calls,
                "rejected_calls": self.metrics.rejected_calls,
                "success_rate": self.metrics.success_rate(),
                "circuit_opened_count": self.metrics.circuit_opened_count,
                "circuit_closed_count": self.metrics.circuit_closed_count,
                "failures_in_window": len(self._failure_window),
                "last_failure": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "last_success": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
            }


class CircuitBreakerRegistry:
    """
    Global registry for managing multiple circuit breakers.
    
    Allows centralized monitoring and management of all circuit breakers
    in the sidecar observer.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: Dict[str, CircuitBreaker] = {}
        return cls._instance
    
    def register(self, breaker: CircuitBreaker):
        """Register a circuit breaker."""
        self._breakers[breaker.name] = breaker
        logger.info(f"Registered circuit breaker: {breaker.name}")
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all registered circuit breakers."""
        return {
            name: breaker.get_metrics()
            for name, breaker in self._breakers.items()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of all circuit breakers.
        
        Returns:
            Health status with counts of breakers in each state
        """
        states = {
            "closed": 0,
            "open": 0,
            "half_open": 0
        }
        
        for breaker in self._breakers.values():
            state = breaker.state.value
            states[state] = states.get(state, 0) + 1
        
        is_healthy = states["open"] == 0
        
        return {
            "healthy": is_healthy,
            "total_breakers": len(self._breakers),
            "states": states,
            "breakers": {
                name: breaker.state.value
                for name, breaker in self._breakers.items()
            }
        }
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("Reset all circuit breakers")


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()
