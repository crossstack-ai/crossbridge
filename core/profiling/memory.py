"""
Memory Profiler

Tracks memory usage during execution.
"""

import tracemalloc
import time
from typing import Dict, Any, Optional

from .timing import TimingProfiler
from .base import ProfilerConfig, ProfileRecord, ProfilingLevel
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class MemoryProfiler(TimingProfiler):
    """
    Memory profiler extends timing profiler with memory tracking.
    
    Uses tracemalloc for lightweight memory snapshots.
    Only active when level=detailed in config.
    
    Warning: tracemalloc has overhead (~10-20%). Use carefully.
    """
    
    def __init__(self, config: ProfilerConfig):
        super().__init__(config)
        self.memory_snapshots: Dict[str, tuple] = {}
        
        # Only enable memory profiling for detailed level
        self.track_memory = config.level == ProfilingLevel.DETAILED
        
        if self.track_memory:
            logger.info("Memory profiler initialized (tracemalloc enabled)")
        else:
            logger.info("Memory profiler initialized (timing only)")
    
    def start(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start timing and memory tracking"""
        # Target filtering first
        if not self.should_profile(name):
            return
        
        # Start timing
        super().start(name, metadata)
        
        # Start memory tracking (if enabled and name was accepted)
        if self.track_memory and name in self.active:
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            
            # Take memory snapshot
            current, peak = tracemalloc.get_traced_memory()
            self.memory_snapshots[name] = (current, peak)
    
    def stop(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Stop timing and memory tracking"""
        # Get timing info
        start_time = self.active.pop(name, None)
        if start_time is None:
            return
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Get memory info
        peak_memory_mb = None
        if self.track_memory and name in self.memory_snapshots:
            start_current, start_peak = self.memory_snapshots.pop(name)
            
            if tracemalloc.is_tracing():
                end_current, end_peak = tracemalloc.get_traced_memory()
                
                # Calculate peak memory delta
                peak_delta = end_peak - start_peak
                peak_memory_mb = peak_delta / (1024 * 1024)
                
                # Stop tracing if no more active profiles
                if not self.memory_snapshots:
                    tracemalloc.stop()
        
        # Only emit if slow OR high memory
        should_emit = (
            duration_ms >= self.config.slow_call_ms or
            (peak_memory_mb is not None and peak_memory_mb >= self.config.memory_mb)
        )
        
        if should_emit:
            record = ProfileRecord(
                name=name,
                duration_ms=duration_ms,
                timestamp=time.time(),
                peak_memory_mb=peak_memory_mb,
                metadata=metadata if self.config.include_metadata else None
            )
            self.emit(record)
