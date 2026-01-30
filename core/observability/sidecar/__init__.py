"""
Sidecar Observer Core Infrastructure

Fail-safe, resilient observer pattern for test execution monitoring.

Design Principles:
- Fail-open: Never block test execution
- Bounded resources: Limited queues, memory, CPU
- Sampling-first: Configurable sampling rates
- Structured logging: JSON-only with correlation IDs
- Observable: Metrics, health endpoints
- Debuggable: Rich context in errors
"""

import logging
import time
import threading
import queue
import psutil
import os
from typing import Dict, Any, Optional, Callable
from datetime import datetime, UTC
from functools import wraps
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class SidecarConfig:
    """Sidecar observer configuration."""
    
    # Feature flags
    enabled: bool = True
    
    # Queue limits
    max_queue_size: int = 5000
    max_event_age_seconds: int = 300  # 5 minutes
    
    # Resource budgets
    max_cpu_percent: float = 5.0  # 5% CPU
    max_memory_mb: float = 100.0  # 100MB RAM
    
    # Sampling rates
    sampling_rates: Dict[str, float] = field(default_factory=lambda: {
        'events': 0.1,      # 10% of events
        'logs': 0.05,       # 5% of logs
        'profiling': 0.01,  # 1% of profiling data
        'metrics': 1.0      # 100% of metrics
    })
    
    # Processing
    batch_size: int = 100
    flush_interval_seconds: float = 5.0
    
    # Observability
    enable_metrics: bool = True
    enable_health_endpoint: bool = True
    metrics_port: int = 9090


# ============================================================================
# Fail-Open Execution
# ============================================================================

class SidecarMetrics:
    """Thread-safe metrics collector."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
    
    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter metric."""
        with self._lock:
            self._counters[metric_name] = self._counters.get(metric_name, 0) + value
    
    def set_gauge(self, metric_name: str, value: float):
        """Set a gauge metric."""
        with self._lock:
            self._gauges[metric_name] = value
    
    def record_histogram(self, metric_name: str, value: float):
        """Record a histogram value."""
        with self._lock:
            if metric_name not in self._histograms:
                self._histograms[metric_name] = []
            self._histograms[metric_name].append(value)
            
            # Keep only recent values (last 1000)
            if len(self._histograms[metric_name]) > 1000:
                self._histograms[metric_name] = self._histograms[metric_name][-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            return {
                'counters': self._counters.copy(),
                'gauges': self._gauges.copy(),
                'histograms': {
                    name: {
                        'count': len(values),
                        'avg': sum(values) / len(values) if values else 0,
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0
                    }
                    for name, values in self._histograms.items()
                }
            }


# Global metrics instance
_metrics = SidecarMetrics()


def get_metrics() -> SidecarMetrics:
    """Get global metrics instance."""
    return _metrics


def safe_observe(operation_name: str = "unknown"):
    """
    Decorator for fail-open execution.
    
    Wraps functions to ensure exceptions never propagate to caller.
    All errors are logged and metrics are incremented.
    
    Args:
        operation_name: Name of operation for logging/metrics
    
    Usage:
        @safe_observe("event_processing")
        def process_event(event):
            # Implementation
            pass
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                start_time = time.time()
                result = fn(*args, **kwargs)
                
                # Record success metrics
                duration_ms = (time.time() - start_time) * 1000
                _metrics.increment(f"sidecar.{operation_name}.success")
                _metrics.record_histogram(f"sidecar.{operation_name}.duration_ms", duration_ms)
                
                return result
                
            except Exception as e:
                # Increment error counter
                _metrics.increment(f"sidecar.{operation_name}.errors")
                _metrics.increment("sidecar.errors.total")
                
                # Structured error logging
                logger.warning(
                    "sidecar_error",
                    extra={
                        'operation': operation_name,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'function': fn.__name__,
                        'timestamp': datetime.now(UTC).isoformat()
                    }
                )
                
                # Return None or default value (fail-open)
                return None
        
        return wrapper
    return decorator


# ============================================================================
# Bounded Queue with Load Shedding
# ============================================================================

class BoundedEventQueue:
    """
    Thread-safe bounded queue with load shedding.
    
    Drops events when queue is full instead of blocking.
    Emits metrics on every drop.
    """
    
    def __init__(self, max_size: int = 5000):
        """
        Initialize bounded queue.
        
        Args:
            max_size: Maximum queue size
        """
        self._queue = queue.Queue(maxsize=max_size)
        self._max_size = max_size
        self._dropped_events = 0
        self._total_events = 0
    
    def put(self, event: Dict[str, Any]) -> bool:
        """
        Try to add event to queue.
        
        Args:
            event: Event dictionary
            
        Returns:
            True if added, False if dropped
        """
        self._total_events += 1
        
        # Check queue size
        if self._queue.qsize() >= self._max_size:
            # Load shedding: Drop event
            self._dropped_events += 1
            _metrics.increment("sidecar.events_dropped")
            
            logger.debug(
                "sidecar_event_dropped",
                extra={
                    'reason': 'queue_full',
                    'queue_size': self._queue.qsize(),
                    'max_size': self._max_size,
                    'total_dropped': self._dropped_events
                }
            )
            
            return False
        
        try:
            # Non-blocking put
            self._queue.put_nowait(event)
            _metrics.increment("sidecar.events_queued")
            return True
            
        except queue.Full:
            # Should not happen due to size check, but handle anyway
            self._dropped_events += 1
            _metrics.increment("sidecar.events_dropped")
            return False
    
    def get(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Get event from queue with timeout.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            Event dict or None if timeout
        """
        try:
            event = self._queue.get(timeout=timeout)
            _metrics.increment("sidecar.events_processed")
            return event
        except queue.Empty:
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def is_full(self) -> bool:
        """Check if queue is full."""
        return self._queue.qsize() >= self._max_size
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            'current_size': self._queue.qsize(),
            'max_size': self._max_size,
            'total_events': self._total_events,
            'dropped_events': self._dropped_events,
            'drop_rate': self._dropped_events / max(self._total_events, 1),
            'utilization': self._queue.qsize() / self._max_size
        }


# ============================================================================
# Sampling
# ============================================================================

class EventSampler:
    """
    Configurable event sampler.
    
    Implements sampling-first design: check before processing.
    """
    
    def __init__(self, sampling_rates: Dict[str, float]):
        """
        Initialize sampler.
        
        Args:
            sampling_rates: Sampling rates by event type (0.0 to 1.0)
        """
        self.sampling_rates = sampling_rates
        self._sample_counts = {event_type: 0 for event_type in sampling_rates}
        self._total_counts = {event_type: 0 for event_type in sampling_rates}
    
    def should_sample(self, event_type: str) -> bool:
        """
        Determine if event should be sampled.
        
        Args:
            event_type: Type of event ('events', 'logs', 'profiling', etc.)
            
        Returns:
            True if event should be sampled
        """
        self._total_counts[event_type] = self._total_counts.get(event_type, 0) + 1
        
        # Get sampling rate (default to 1.0 if not configured)
        rate = self.sampling_rates.get(event_type, 1.0)
        
        # Always sample if rate is 1.0
        if rate >= 1.0:
            self._sample_counts[event_type] = self._sample_counts.get(event_type, 0) + 1
            return True
        
        # Never sample if rate is 0.0
        if rate <= 0.0:
            _metrics.increment("sidecar.events_sampled_out")
            return False
        
        # Deterministic sampling based on count
        should_sample = (self._total_counts[event_type] % int(1.0 / rate)) == 0
        
        if should_sample:
            self._sample_counts[event_type] = self._sample_counts.get(event_type, 0) + 1
        else:
            _metrics.increment("sidecar.events_sampled_out")
        
        return should_sample
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sampling statistics."""
        return {
            event_type: {
                'total': self._total_counts.get(event_type, 0),
                'sampled': self._sample_counts.get(event_type, 0),
                'rate': self.sampling_rates.get(event_type, 1.0),
                'actual_rate': (
                    self._sample_counts.get(event_type, 0) / 
                    max(self._total_counts.get(event_type, 1), 1)
                )
            }
            for event_type in self.sampling_rates
        }


# ============================================================================
# Resource Budget Guards
# ============================================================================

class ResourceMonitor:
    """
    Monitor CPU and memory usage.
    
    Enforces resource budgets to prevent sidecar from impacting tests.
    """
    
    def __init__(self, max_cpu_percent: float = 5.0, max_memory_mb: float = 100.0):
        """
        Initialize resource monitor.
        
        Args:
            max_cpu_percent: Maximum CPU usage percentage
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_mb = max_memory_mb
        self._process = psutil.Process(os.getpid())
        self._profiling_enabled = True
    
    def check_resources(self) -> Dict[str, Any]:
        """
        Check current resource usage.
        
        Returns:
            Resource usage stats
        """
        try:
            cpu_percent = self._process.cpu_percent(interval=0.1)
            memory_mb = self._process.memory_info().rss / (1024 * 1024)
            
            # Update metrics
            _metrics.set_gauge("sidecar.cpu_usage", cpu_percent)
            _metrics.set_gauge("sidecar.memory_usage", memory_mb)
            
            # Check if over budget
            cpu_over_budget = cpu_percent > self.max_cpu_percent
            memory_over_budget = memory_mb > self.max_memory_mb
            
            if cpu_over_budget and self._profiling_enabled:
                logger.warning(
                    "sidecar_cpu_budget_exceeded",
                    extra={
                        'current': cpu_percent,
                        'budget': self.max_cpu_percent,
                        'action': 'disabling_profiling'
                    }
                )
                self.disable_profiling()
            
            if memory_over_budget:
                logger.warning(
                    "sidecar_memory_budget_exceeded",
                    extra={
                        'current_mb': memory_mb,
                        'budget_mb': self.max_memory_mb
                    }
                )
            
            return {
                'cpu_percent': cpu_percent,
                'memory_mb': memory_mb,
                'cpu_over_budget': cpu_over_budget,
                'memory_over_budget': memory_over_budget,
                'profiling_enabled': self._profiling_enabled
            }
            
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
            return {}
    
    def disable_profiling(self):
        """Disable profiling to reduce resource usage."""
        self._profiling_enabled = False
        _metrics.increment("sidecar.profiling_disabled")
    
    def enable_profiling(self):
        """Re-enable profiling."""
        self._profiling_enabled = True
        _metrics.increment("sidecar.profiling_enabled")
    
    def is_profiling_enabled(self) -> bool:
        """Check if profiling is currently enabled."""
        return self._profiling_enabled


# ============================================================================
# Global Instances
# ============================================================================

# Global configuration
_config = SidecarConfig()

# Global event queue
_event_queue = BoundedEventQueue(max_size=_config.max_queue_size)

# Global sampler
_sampler = EventSampler(_config.sampling_rates)

# Global resource monitor
_resource_monitor = ResourceMonitor(
    max_cpu_percent=_config.max_cpu_percent,
    max_memory_mb=_config.max_memory_mb
)


def get_config() -> SidecarConfig:
    """Get global sidecar configuration."""
    return _config


def get_event_queue() -> BoundedEventQueue:
    """Get global event queue."""
    return _event_queue


def get_sampler() -> EventSampler:
    """Get global event sampler."""
    return _sampler


def get_resource_monitor() -> ResourceMonitor:
    """Get global resource monitor."""
    return _resource_monitor


def update_config(new_config: Dict[str, Any]):
    """
    Update sidecar configuration at runtime.
    
    Args:
        new_config: New configuration values
    """
    global _config, _sampler
    
    for key, value in new_config.items():
        if hasattr(_config, key):
            setattr(_config, key, value)
    
    # Update sampler if rates changed
    if 'sampling_rates' in new_config:
        _sampler = EventSampler(new_config['sampling_rates'])
    
    logger.info(
        "sidecar_config_updated",
        extra={'config': new_config}
    )
