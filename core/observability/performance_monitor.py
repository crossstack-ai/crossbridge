"""
Performance Monitoring for Sidecar Observer

Tracks performance overhead of the observer to ensure it stays below 5%.
Provides real-time metrics and alerts when overhead exceeds thresholds.
"""

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
from contextlib import contextmanager

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a monitored operation."""
    
    operation_name: str
    total_calls: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    
    # Sliding window for recent operations
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Overhead tracking
    test_duration_ms: float = 0.0  # Time test would take without observer
    observer_overhead_ms: float = 0.0  # Time added by observer
    
    @property
    def avg_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration_ms / self.total_calls
    
    @property
    def p95_duration_ms(self) -> float:
        """Calculate 95th percentile duration."""
        if not self.recent_durations:
            return 0.0
        sorted_durations = sorted(self.recent_durations)
        index = int(len(sorted_durations) * 0.95)
        return sorted_durations[index] if index < len(sorted_durations) else sorted_durations[-1]
    
    @property
    def p99_duration_ms(self) -> float:
        """Calculate 99th percentile duration."""
        if not self.recent_durations:
            return 0.0
        sorted_durations = sorted(self.recent_durations)
        index = int(len(sorted_durations) * 0.99)
        return sorted_durations[index] if index < len(sorted_durations) else sorted_durations[-1]
    
    @property
    def overhead_percentage(self) -> float:
        """Calculate overhead as percentage of test duration."""
        if self.test_duration_ms == 0:
            return 0.0
        return (self.observer_overhead_ms / self.test_duration_ms) * 100


class PerformanceMonitor:
    """
    Monitors performance overhead of sidecar observer.
    
    Tracks timing of observer operations and calculates overhead
    relative to actual test execution time.
    
    Usage:
        monitor = PerformanceMonitor()
        
        with monitor.measure("test_observer"):
            # Observer operations
            pass
    """
    
    def __init__(self, overhead_threshold_percent: float = 5.0):
        """
        Initialize performance monitor.
        
        Args:
            overhead_threshold_percent: Alert threshold for overhead (default: 5%)
        """
        self.overhead_threshold = overhead_threshold_percent
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.RLock()
        
        # Global counters
        self._total_tests_observed = 0
        self._threshold_violations = 0
        
        logger.info(
            "Performance monitor initialized",
            extra={"overhead_threshold": f"{overhead_threshold_percent}%"}
        )
    
    @contextmanager
    def measure(self, operation_name: str):
        """
        Context manager to measure operation duration.
        
        Args:
            operation_name: Name of the operation being measured
            
        Usage:
            with monitor.measure("observe_test_start"):
                # Code to measure
                pass
        """
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self._record_measurement(operation_name, duration_ms)
    
    def _record_measurement(self, operation_name: str, duration_ms: float):
        """Record a performance measurement."""
        with self._lock:
            if operation_name not in self._metrics:
                self._metrics[operation_name] = PerformanceMetrics(operation_name=operation_name)
            
            metrics = self._metrics[operation_name]
            metrics.total_calls += 1
            metrics.total_duration_ms += duration_ms
            metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
            metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)
            metrics.recent_durations.append(duration_ms)
            
            # Log if duration is excessive
            if duration_ms > 100:  # More than 100ms
                logger.warning(
                    f"Slow observer operation: {operation_name}",
                    extra={"duration_ms": duration_ms}
                )
    
    def record_test_execution(
        self,
        test_name: str,
        test_duration_ms: float,
        observer_overhead_ms: float
    ):
        """
        Record overhead for a complete test execution.
        
        Args:
            test_name: Name of test
            test_duration_ms: Total test execution time
            observer_overhead_ms: Time spent in observer
        """
        with self._lock:
            self._total_tests_observed += 1
            
            # Calculate overhead percentage
            if test_duration_ms > 0:
                overhead_pct = (observer_overhead_ms / test_duration_ms) * 100
                
                # Check threshold
                if overhead_pct > self.overhead_threshold:
                    self._threshold_violations += 1
                    logger.warning(
                        f"Observer overhead exceeded threshold for test: {test_name}",
                        extra={
                            "overhead_percent": f"{overhead_pct:.2f}%",
                            "threshold": f"{self.overhead_threshold}%",
                            "test_duration_ms": test_duration_ms,
                            "observer_overhead_ms": observer_overhead_ms
                        }
                    )
                
                # Store in metrics
                if test_name not in self._metrics:
                    self._metrics[test_name] = PerformanceMetrics(operation_name=test_name)
                
                metrics = self._metrics[test_name]
                metrics.test_duration_ms = test_duration_ms
                metrics.observer_overhead_ms = observer_overhead_ms
    
    def get_metrics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Args:
            operation_name: Specific operation (None for all)
            
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            if operation_name:
                metrics = self._metrics.get(operation_name)
                if not metrics:
                    return {}
                
                return {
                    "operation": metrics.operation_name,
                    "total_calls": metrics.total_calls,
                    "avg_duration_ms": metrics.avg_duration_ms,
                    "min_duration_ms": metrics.min_duration_ms,
                    "max_duration_ms": metrics.max_duration_ms,
                    "p95_duration_ms": metrics.p95_duration_ms,
                    "p99_duration_ms": metrics.p99_duration_ms,
                    "overhead_percent": metrics.overhead_percentage
                }
            
            # Return all metrics
            return {
                "global": {
                    "total_tests_observed": self._total_tests_observed,
                    "threshold_violations": self._threshold_violations,
                    "violation_rate": (
                        self._threshold_violations / self._total_tests_observed * 100
                        if self._total_tests_observed > 0 else 0
                    )
                },
                "operations": {
                    name: {
                        "total_calls": m.total_calls,
                        "avg_duration_ms": m.avg_duration_ms,
                        "p95_duration_ms": m.p95_duration_ms,
                        "p99_duration_ms": m.p99_duration_ms
                    }
                    for name, m in self._metrics.items()
                }
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status based on performance metrics.
        
        Returns:
            Health status with warnings if overhead too high
        """
        with self._lock:
            violation_rate = (
                self._threshold_violations / self._total_tests_observed * 100
                if self._total_tests_observed > 0 else 0
            )
            
            is_healthy = violation_rate < 10  # Less than 10% of tests exceed threshold
            
            status = {
                "healthy": is_healthy,
                "tests_observed": self._total_tests_observed,
                "threshold_violations": self._threshold_violations,
                "violation_rate": f"{violation_rate:.2f}%",
                "overhead_threshold": f"{self.overhead_threshold}%"
            }
            
            if not is_healthy:
                status["warning"] = (
                    f"Observer overhead exceeding {self.overhead_threshold}% "
                    f"threshold in {violation_rate:.1f}% of tests"
                )
            
            return status
    
    def reset_metrics(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._total_tests_observed = 0
            self._threshold_violations = 0
            logger.info("Performance metrics reset")


class SamplingStrategy:
    """
    Configurable sampling strategy for observer operations.
    
    Allows reducing overhead by sampling only a percentage of tests
    when overhead is too high.
    """
    
    def __init__(self, sample_rate: float = 1.0):
        """
        Initialize sampling strategy.
        
        Args:
            sample_rate: Fraction of tests to observe (0.0 to 1.0)
                        1.0 = observe all tests (100%)
                        0.1 = observe 10% of tests
                        0.01 = observe 1% of tests
        """
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")
        
        self._sample_rate = sample_rate
        self._counter = 0
        self._lock = threading.Lock()
        
        logger.info(
            "Sampling strategy initialized",
            extra={"sample_rate": f"{sample_rate * 100}%"}
        )
    
    @property
    def sample_rate(self) -> float:
        """Get current sample rate."""
        return self._sample_rate
    
    @sample_rate.setter
    def sample_rate(self, value: float):
        """Set sample rate."""
        if not 0.0 <= value <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")
        
        with self._lock:
            old_rate = self._sample_rate
            self._sample_rate = value
            
            logger.info(
                "Sample rate changed",
                extra={
                    "old_rate": f"{old_rate * 100}%",
                    "new_rate": f"{value * 100}%"
                }
            )
    
    def should_observe(self) -> bool:
        """
        Determine if current test should be observed.
        
        Returns:
            True if test should be observed, False otherwise
        """
        if self._sample_rate >= 1.0:
            return True
        
        if self._sample_rate <= 0.0:
            return False
        
        with self._lock:
            self._counter += 1
            
            # Simple deterministic sampling
            # Observe every Nth test where N = 1/sample_rate
            interval = int(1.0 / self._sample_rate)
            return (self._counter % interval) == 0
    
    def adjust_for_overhead(self, current_overhead_percent: float, target_overhead_percent: float = 5.0):
        """
        Automatically adjust sample rate based on measured overhead.
        
        Args:
            current_overhead_percent: Measured overhead percentage
            target_overhead_percent: Target overhead (default: 5%)
        """
        if current_overhead_percent <= target_overhead_percent:
            # Overhead acceptable, can increase sampling
            new_rate = min(1.0, self._sample_rate * 1.1)
        else:
            # Overhead too high, reduce sampling
            ratio = target_overhead_percent / current_overhead_percent
            new_rate = self._sample_rate * ratio * 0.9  # Be conservative
            new_rate = max(0.01, new_rate)  # At least 1%
        
        if new_rate != self._sample_rate:
            self.sample_rate = new_rate
            logger.info(
                "Sample rate auto-adjusted for overhead",
                extra={
                    "current_overhead": f"{current_overhead_percent:.2f}%",
                    "target_overhead": f"{target_overhead_percent}%",
                    "new_sample_rate": f"{new_rate * 100:.1f}%"
                }
            )


# Global instances
performance_monitor = PerformanceMonitor()
sampling_strategy = SamplingStrategy()
