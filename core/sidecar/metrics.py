"""
Metrics Collector for Sidecar Runtime

Provides Prometheus-compatible metrics:
- Counter (monotonic increasing)
- Gauge (can go up/down)
- Histogram (distribution of values)
- Summary (percentiles)
"""

import time
import threading
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


@dataclass
class MetricValue:
    """Single metric value with timestamp"""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class Counter:
    """Monotonic counter metric"""
    
    def __init__(self, name: str, help_text: str = ""):
        self.name = name
        self.help_text = help_text
        self._value = 0.0
        self._lock = threading.Lock()
    
    def increment(self, amount: float = 1.0) -> None:
        """Increment counter"""
        with self._lock:
            self._value += amount
    
    def get(self) -> float:
        """Get current value"""
        with self._lock:
            return self._value
    
    def reset(self) -> None:
        """Reset counter"""
        with self._lock:
            self._value = 0.0


class Gauge:
    """Gauge metric (can go up or down)"""
    
    def __init__(self, name: str, help_text: str = ""):
        self.name = name
        self.help_text = help_text
        self._value = 0.0
        self._lock = threading.Lock()
    
    def set(self, value: float) -> None:
        """Set gauge value"""
        with self._lock:
            self._value = value
    
    def increment(self, amount: float = 1.0) -> None:
        """Increment gauge"""
        with self._lock:
            self._value += amount
    
    def decrement(self, amount: float = 1.0) -> None:
        """Decrement gauge"""
        with self._lock:
            self._value -= amount
    
    def get(self) -> float:
        """Get current value"""
        with self._lock:
            return self._value


class Histogram:
    """Histogram metric for tracking distributions"""
    
    def __init__(self, name: str, help_text: str = "", buckets: Optional[List[float]] = None):
        self.name = name
        self.help_text = help_text
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._observations: List[float] = []
        self._sum = 0.0
        self._count = 0
        self._lock = threading.Lock()
    
    def observe(self, value: float) -> None:
        """Record an observation"""
        with self._lock:
            self._observations.append(value)
            self._sum += value
            self._count += 1
            
            # Keep only last 10000 observations to prevent memory growth
            if len(self._observations) > 10000:
                self._observations.pop(0)
    
    def get_summary(self) -> Dict:
        """Get histogram summary"""
        with self._lock:
            if not self._observations:
                return {
                    'count': 0,
                    'sum': 0.0,
                    'avg': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'buckets': {},
                }
            
            sorted_obs = sorted(self._observations)
            bucket_counts = {}
            
            for bucket in self.buckets:
                bucket_counts[bucket] = sum(1 for v in sorted_obs if v <= bucket)
            
            return {
                'count': self._count,
                'sum': self._sum,
                'avg': self._sum / self._count if self._count > 0 else 0.0,
                'min': min(sorted_obs),
                'max': max(sorted_obs),
                'p50': sorted_obs[len(sorted_obs) // 2],
                'p95': sorted_obs[int(len(sorted_obs) * 0.95)],
                'p99': sorted_obs[int(len(sorted_obs) * 0.99)],
                'buckets': bucket_counts,
            }


class MetricsCollector:
    """
    Metrics collector with Prometheus-compatible output
    
    Thread-safe and low overhead.
    """
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.RLock()
        
        # Initialize core sidecar metrics
        self._init_core_metrics()
    
    def _init_core_metrics(self) -> None:
        """Initialize core sidecar metrics"""
        # Counters
        self.register_counter('sidecar_events_total', 'Total events observed')
        self.register_counter('sidecar_events_dropped_total', 'Total events dropped due to sampling or queue overflow')
        self.register_counter('sidecar_errors_total', 'Total errors in sidecar')
        
        # Gauges
        self.register_gauge('sidecar_queue_size', 'Current queue size')
        self.register_gauge('sidecar_cpu_usage', 'CPU usage percentage')
        self.register_gauge('sidecar_memory_usage_mb', 'Memory usage in MB')
        self.register_gauge('sidecar_thread_count', 'Number of threads')
        
        # Histograms
        self.register_histogram('sidecar_processing_latency_ms', 'Event processing latency in milliseconds')
    
    def register_counter(self, name: str, help_text: str = "") -> Counter:
        """Register or get a counter"""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, help_text)
            return self._counters[name]
    
    def register_gauge(self, name: str, help_text: str = "") -> Gauge:
        """Register or get a gauge"""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, help_text)
            return self._gauges[name]
    
    def register_histogram(self, name: str, help_text: str = "", buckets: Optional[List[float]] = None) -> Histogram:
        """Register or get a histogram"""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, help_text, buckets)
            return self._histograms[name]
    
    def increment(self, name: str, amount: float = 1.0) -> None:
        """Increment a counter"""
        counter = self.register_counter(name)
        counter.increment(amount)
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value"""
        gauge = self.register_gauge(name)
        gauge.set(value)
    
    def observe(self, name: str, value: float) -> None:
        """Record a histogram observation"""
        histogram = self.register_histogram(name)
        histogram.observe(value)
    
    def get_metrics(self) -> Dict[str, any]:
        """Get all metrics as a dictionary"""
        with self._lock:
            metrics = {}
            
            # Counters
            for name, counter in self._counters.items():
                metrics[name] = {
                    'type': 'counter',
                    'value': counter.get(),
                    'help': counter.help_text,
                }
            
            # Gauges
            for name, gauge in self._gauges.items():
                metrics[name] = {
                    'type': 'gauge',
                    'value': gauge.get(),
                    'help': gauge.help_text,
                }
            
            # Histograms
            for name, histogram in self._histograms.items():
                metrics[name] = {
                    'type': 'histogram',
                    'value': histogram.get_summary(),
                    'help': histogram.help_text,
                }
            
            return metrics
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format
        
        Returns:
            Prometheus-formatted metrics string
        """
        with self._lock:
            lines = []
            
            # Counters
            for name, counter in self._counters.items():
                if counter.help_text:
                    lines.append(f"# HELP {name} {counter.help_text}")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {counter.get()}")
            
            # Gauges
            for name, gauge in self._gauges.items():
                if gauge.help_text:
                    lines.append(f"# HELP {name} {gauge.help_text}")
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {gauge.get()}")
            
            # Histograms
            for name, histogram in self._histograms.items():
                if histogram.help_text:
                    lines.append(f"# HELP {name} {histogram.help_text}")
                lines.append(f"# TYPE {name} histogram")
                
                summary = histogram.get_summary()
                
                # Buckets
                for bucket, count in summary.get('buckets', {}).items():
                    lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {summary["count"]}')
                
                # Sum and count
                lines.append(f"{name}_sum {summary['sum']}")
                lines.append(f"{name}_count {summary['count']}")
            
            return '\n'.join(lines) + '\n'
    
    def reset_all(self) -> None:
        """Reset all metrics"""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()
            # Gauges don't reset
            # Histograms keep history
