"""
Profiler Factory

Config-driven profiler creation with support for all profiler types.
"""

from typing import Optional
from .base import Profiler, ProfilerConfig, ProfilingLevel, ProfilerType
from .noop import NoOpProfiler
from .timing import TimingProfiler
from .memory import MemoryProfiler
from .test_execution import TestExecutionProfiler
from .system import SystemProfiler
from .benchmark import BenchmarkProfiler
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)

# Global profiler instance
_global_profiler: Optional[Profiler] = None


def create_profiler(config: ProfilerConfig) -> Profiler:
    """
    Create profiler based on configuration.
    
    Decision tree:
    1. If disabled → NoOpProfiler (zero cost)
    2. If profiler_type == TEST_EXECUTION → TestExecutionProfiler
    3. If profiler_type == SYSTEM → SystemProfiler  
    4. If profiler_type == BENCHMARK → BenchmarkProfiler
    5. If profiler_type == RUNTIME:
       - If level == BASIC → TimingProfiler
       - If level == DETAILED → MemoryProfiler
       - If level == SYSTEM → raise error (use SYSTEM type)
    
    Args:
        config: Profiler configuration
        
    Returns:
        Profiler instance (NoOp or real profiler)
    """
    if not config.enabled:
        logger.info("Profiling disabled, using NoOpProfiler")
        return NoOpProfiler()
    
    profiler_type = config.profiler_type
    
    # Test execution profiling
    if profiler_type == ProfilerType.TEST_EXECUTION:
        logger.info("Creating TestExecutionProfiler")
        return TestExecutionProfiler(config)
    
    # System profiling
    if profiler_type == ProfilerType.SYSTEM:
        logger.info("Creating SystemProfiler")
        return SystemProfiler(config)
    
    # Benchmark profiling
    if profiler_type == ProfilerType.BENCHMARK:
        logger.info("Creating BenchmarkProfiler")
        return BenchmarkProfiler(config)
    
    # Runtime profiling (default)
    if profiler_type == ProfilerType.RUNTIME:
        if config.level == ProfilingLevel.BASIC:
            logger.info("Creating TimingProfiler (basic)")
            return TimingProfiler(config)
        elif config.level == ProfilingLevel.DETAILED:
            logger.info("Creating MemoryProfiler (detailed)")
            return MemoryProfiler(config)
        elif config.level == ProfilingLevel.SYSTEM:
            raise ValueError(
                "ProfilingLevel.SYSTEM requires ProfilerType.SYSTEM. "
                "Set profiler_type='system' in config."
            )
    
    # Fallback to NoOp
    logger.warning(f"Unknown profiler configuration, using NoOpProfiler")
    return NoOpProfiler()


def get_profiler() -> Profiler:
    """
    Get global profiler instance.
    
    Returns NoOpProfiler if not initialized.
    Call initialize_profiler() first in application startup.
    
    Returns:
        Global profiler instance
    """
    global _global_profiler
    
    if _global_profiler is None:
        # Return NoOp by default (safe fallback)
        return NoOpProfiler()
    
    return _global_profiler


def initialize_profiler(config: ProfilerConfig) -> Profiler:
    """
    Initialize global profiler.
    
    Call this once during application startup.
    
    Args:
        config: Profiler configuration
        
    Returns:
        Created profiler instance
    """
    global _global_profiler
    
    _global_profiler = create_profiler(config)
    logger.info(f"Global profiler initialized: {type(_global_profiler).__name__}")
    
    return _global_profiler


def reset_profiler() -> None:
    """
    Reset global profiler (for testing).
    
    Sets profiler back to None, forcing re-initialization.
    """
    global _global_profiler
    _global_profiler = None
