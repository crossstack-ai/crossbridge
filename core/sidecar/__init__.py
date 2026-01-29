"""
CrossBridge Debuggable Sidecar Runtime

A resilient, low-overhead, configurable sidecar observer that:
- Samples events with configurable rates
- Collects lightweight profiling data
- Emits structured logs and metrics
- Provides health monitoring
- Never blocks or crashes the main process

Design Principles:
- Fail-open: Sidecar failure never affects main process
- Low overhead: <5% CPU, minimal memory footprint
- Sampling-first: Everything is sampled
- Runtime configurable: No rebuilds required
- Debuggable by default: Logs + metrics + traces
"""

from .observer import SidecarObserver, Event
from .sampler import Sampler, AdaptiveSampler, SignalType
from .profiler import LightweightProfiler, DeepProfiler
from .metrics import MetricsCollector, Counter, Gauge, Histogram
from .health import SidecarHealth, HealthStatus
from .config import SidecarConfig
from .runtime import SidecarRuntime

__all__ = [
    # Main runtime
    'SidecarRuntime',
    
    # Core components
    'SidecarObserver',
    'Sampler',
    'AdaptiveSampler',
    'LightweightProfiler',
    'DeepProfiler',
    'MetricsCollector',
    'SidecarHealth',
    'SidecarConfig',
    
    # Supporting classes
    'Event',
    'SignalType',
    'HealthStatus',
    'Counter',
    'Gauge',
    'Histogram',
]

__version__ = '1.0.0'
