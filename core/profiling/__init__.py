"""
CrossBridge Performance Profiling Module

Passive, framework-agnostic performance profiling for test execution.
Captures timing, automation overhead, and application interaction metrics.
"""

from core.profiling.models import (
    PerformanceEvent,
    EventType,
    ProfileConfig,
    PerformanceInsight,
)
from core.profiling.collector import MetricsCollector
from core.profiling.storage import StorageBackend, StorageFactory

__all__ = [
    "PerformanceEvent",
    "EventType",
    "ProfileConfig",
    "PerformanceInsight",
    "MetricsCollector",
    "StorageBackend",
    "StorageFactory",
]
