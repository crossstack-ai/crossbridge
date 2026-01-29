"""
CrossBridge Unified Performance Profiling Module

CONSOLIDATED: All profiling systems unified under config-driven approach.

Profiler Types:
1. Runtime Profiling - Internal operations (semantic search, embeddings, etc.)
2. Test Execution Profiling - Test lifecycle, commands, HTTP requests
3. System Profiling - CPU, memory, threads, GC monitoring
4. Benchmarking - Adapter comparison and performance insights

All controlled via crossbridge.yml configuration.
"""

# Legacy profiling (DEPRECATED - will be removed in v2.0)
from core.profiling.models import (
    PerformanceEvent,
    EventType,
    ProfileConfig,
    PerformanceInsight,
)
from core.profiling.collector import MetricsCollector
from core.profiling.storage import StorageBackend, StorageFactory

# Config-driven profiling - Base
from core.profiling.base import (
    Profiler,
    ProfilerConfig,
    ProfileRecord,
    ProfilingMode,
    ProfilingLevel,
    OutputType,
    ProfilerType,
)

# Config-driven profiling - Implementations
from core.profiling.noop import NoOpProfiler
from core.profiling.timing import TimingProfiler
from core.profiling.memory import MemoryProfiler
from core.profiling.test_execution import TestExecutionProfiler
from core.profiling.system import SystemProfiler, SystemSnapshot
from core.profiling.benchmark import BenchmarkProfiler, BenchmarkResult

# Config-driven profiling - Factory
from core.profiling.factory import (
    create_profiler,
    get_profiler,
    initialize_profiler,
    reset_profiler,
)

# Config-driven profiling - Context managers
from core.profiling.context import (
    profile,
    profile_async,
    profiled,
    profiled_async,
    ProfilerContext,
)

__all__ = [
    # Legacy profiling (DEPRECATED)
    "PerformanceEvent",
    "EventType",
    "ProfileConfig",
    "PerformanceInsight",
    "MetricsCollector",
    "StorageBackend",
    "StorageFactory",
    
    # Config-driven profiling - Base
    "Profiler",
    "ProfilerConfig",
    "ProfileRecord",
    "ProfilingMode",
    "ProfilingLevel",
    "OutputType",
    "ProfilerType",
    
    # Config-driven profiling - Implementations
    "NoOpProfiler",
    "TimingProfiler",
    "MemoryProfiler",
    "TestExecutionProfiler",
    "SystemProfiler",
    "SystemSnapshot",
    "BenchmarkProfiler",
    "BenchmarkResult",
    
    # Config-driven profiling - Factory
    "create_profiler",
    "get_profiler",
    "initialize_profiler",
    "reset_profiler",
    
    # Config-driven profiling - Context managers
    "profile",
    "profile_async",
    "profiled",
    "profiled_async",
    "ProfilerContext",
]
