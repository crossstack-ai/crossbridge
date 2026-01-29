"""
Profiling Base Abstractions

Core profiler interface and configuration model.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class ProfilingMode(Enum):
    """Profiling mode"""
    SAMPLING = "sampling"  # Profile 1 in N requests
    FULL = "full"  # Profile all requests


class ProfilingLevel(Enum):
    """Profiling detail level"""
    BASIC = "basic"  # Timing only
    DETAILED = "detailed"  # Timing + memory + metadata
    SYSTEM = "system"  # System-level monitoring (CPU, memory, threads, GC)


class OutputType(Enum):
    """Profiling output type"""
    LOG = "log"  # Log to stdout/stderr
    FILE = "file"  # Write to file
    PROMETHEUS = "prometheus"  # Export to Prometheus
    DATABASE = "database"  # Store in SQLite (for test execution)
    NONE = "none"  # Discard (for testing)


class ProfilerType(Enum):
    """Type of profiler"""
    RUNTIME = "runtime"  # Runtime profiling (semantic search, embeddings, etc.)
    TEST_EXECUTION = "test_execution"  # Test execution profiling (test lifecycle, commands)
    SYSTEM = "system"  # System profiling (CPU, memory, threads, GC)
    BENCHMARK = "benchmark"  # Benchmarking and comparison


@dataclass
class ProfilerConfig:
    """
    Unified profiler configuration loaded from YAML.
    
    Consolidates configuration for:
    - Runtime profiling (semantic search, embeddings, etc.)
    - Test execution profiling (test lifecycle, driver commands)
    - System profiling (CPU, memory, threads, GC)
    - Benchmarking (adapter comparison)
    """
    # Core settings
    enabled: bool = False
    profiler_type: ProfilerType = ProfilerType.RUNTIME
    mode: ProfilingMode = ProfilingMode.SAMPLING
    level: ProfilingLevel = ProfilingLevel.BASIC
    
    # Target modules/functions to profile (for runtime/test profiling)
    targets: List[str] = field(default_factory=list)
    
    # Thresholds
    slow_call_ms: float = 500.0
    memory_mb: float = 50.0
    cpu_percent: float = 80.0  # System profiling threshold
    
    # Sampling
    sample_rate: float = 0.1  # 10% of requests (runtime/test profiling)
    sampling_interval: float = 1.0  # Seconds (system profiling)
    
    # Output
    output_type: OutputType = OutputType.LOG
    output_path: Optional[str] = None
    database_path: Optional[str] = None  # For test execution storage
    
    # Production safety
    max_records_per_minute: int = 100
    max_snapshots: int = 1000  # For system profiling
    include_metadata: bool = True
    include_stack_trace: bool = False
    
    # Test execution specific
    capture_test_lifecycle: bool = True  # Start/end test events
    capture_commands: bool = True  # Driver commands (Selenium, Playwright, etc.)
    capture_http: bool = True  # HTTP requests
    capture_assertions: bool = False  # Individual assertions
    
    # System profiling specific
    monitor_cpu: bool = True
    monitor_memory: bool = True
    monitor_threads: bool = True
    monitor_gc: bool = True  # Garbage collection
    
    # Benchmarking specific
    benchmark_iterations: int = 10
    compare_baselines: bool = True
    baseline_adapters: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "ProfilerConfig":
        """Create config from dictionary"""
        return cls(
            enabled=config.get("enabled", False),
            profiler_type=ProfilerType(config.get("type", "runtime")),
            mode=ProfilingMode(config.get("mode", "sampling")),
            level=ProfilingLevel(config.get("level", "basic")),
            targets=config.get("targets", []),
            slow_call_ms=config.get("thresholds", {}).get("slow_call_ms", 500.0),
            memory_mb=config.get("thresholds", {}).get("memory_mb", 50.0),
            cpu_percent=config.get("thresholds", {}).get("cpu_percent", 80.0),
            sample_rate=config.get("sample_rate", 0.1),
            sampling_interval=config.get("sampling_interval", 1.0),
            output_type=OutputType(config.get("output", {}).get("type", "log")),
            output_path=config.get("output", {}).get("path"),
            database_path=config.get("output", {}).get("database_path"),
            max_records_per_minute=config.get("max_records_per_minute", 100),
            max_snapshots=config.get("max_snapshots", 1000),
            include_metadata=config.get("include_metadata", True),
            include_stack_trace=config.get("include_stack_trace", False),
            capture_test_lifecycle=config.get("test_execution", {}).get("capture_lifecycle", True),
            capture_commands=config.get("test_execution", {}).get("capture_commands", True),
            capture_http=config.get("test_execution", {}).get("capture_http", True),
            capture_assertions=config.get("test_execution", {}).get("capture_assertions", False),
            monitor_cpu=config.get("system", {}).get("monitor_cpu", True),
            monitor_memory=config.get("system", {}).get("monitor_memory", True),
            monitor_threads=config.get("system", {}).get("monitor_threads", True),
            monitor_gc=config.get("system", {}).get("monitor_gc", True),
            benchmark_iterations=config.get("benchmarking", {}).get("iterations", 10),
            compare_baselines=config.get("benchmarking", {}).get("compare_baselines", True),
            baseline_adapters=config.get("benchmarking", {}).get("baseline_adapters", []),
        )


@dataclass
class ProfileRecord:
    """
    Single profiling record.
    
    This is what gets emitted to output.
    """
    name: str
    duration_ms: float
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
    peak_memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }
        
        if self.metadata:
            result["metadata"] = self.metadata
        if self.peak_memory_mb is not None:
            result["peak_memory_mb"] = round(self.peak_memory_mb, 2)
        if self.cpu_percent is not None:
            result["cpu_percent"] = round(self.cpu_percent, 2)
        if self.stack_trace:
            result["stack_trace"] = self.stack_trace
        
        return result


class Profiler(ABC):
    """
    Base profiler interface.
    
    All profilers must implement this interface.
    Ensures consistent API across implementations.
    """
    
    @abstractmethod
    def start(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Start profiling a section.
        
        Args:
            name: Profiling section name (e.g., "semantic_search")
            metadata: Optional metadata to attach to this profile
        """
        pass
    
    @abstractmethod
    def stop(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Stop profiling a section.
        
        Args:
            name: Profiling section name (must match start())
            metadata: Additional metadata to attach
        """
        pass
    
    @abstractmethod
    def emit(self, record: ProfileRecord) -> None:
        """
        Emit a profiling record.
        
        Args:
            record: Profile record to emit
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if profiling is enabled"""
        return True
    
    def should_profile(self, name: str) -> bool:
        """
        Check if this target should be profiled.
        
        Args:
            name: Target name
            
        Returns:
            True if should profile
        """
        return True
