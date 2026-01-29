"""
System Profiler

System-level monitoring: CPU, memory, threads, GC.
Consolidates sidecar profiler functionality with config-driven approach.
"""

import os
import gc
import time
import threading
import psutil
from typing import Dict, List, Optional
from dataclasses import dataclass
from core.profiling.base import Profiler, ProfilerConfig, ProfileRecord
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


@dataclass
class SystemSnapshot:
    """Point-in-time system snapshot"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    thread_count: int
    gc_count: Dict[int, int]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "thread_count": self.thread_count,
            "gc_count": self.gc_count,
        }


class SystemProfiler(Profiler):
    """
    System-level profiler with <1% overhead.
    
    Monitors:
    - CPU usage
    - Memory usage
    - Thread count
    - Garbage collection
    
    Replaces LightweightProfiler from sidecar.
    """
    
    def __init__(self, config: ProfilerConfig):
        """Initialize system profiler"""
        if not config.enabled:
            raise ValueError("SystemProfiler requires enabled=True")
        
        self._config = config
        self._process = psutil.Process(os.getpid())
        self._snapshots: List[SystemSnapshot] = []
        self._lock = threading.Lock()
        
        # Background sampling
        self._running = False
        self._sampler_thread: Optional[threading.Thread] = None
        
        # Baseline
        self._baseline_memory_mb = self._process.memory_info().rss / 1024 / 1024
        
        logger.info(
            f"SystemProfiler initialized: "
            f"interval={config.sampling_interval}s, "
            f"cpu={config.monitor_cpu}, "
            f"memory={config.monitor_memory}, "
            f"threads={config.monitor_threads}, "
            f"gc={config.monitor_gc}"
        )
    
    def start(self, name: str, metadata: Optional[Dict] = None) -> None:
        """Start background profiling"""
        if self._running:
            logger.warning("SystemProfiler already running")
            return
        
        self._running = True
        self._sampler_thread = threading.Thread(
            target=self._sample_loop,
            daemon=True,
            name="system-profiler"
        )
        self._sampler_thread.start()
        logger.info("SystemProfiler started")
    
    def stop(self, name: str, metadata: Optional[Dict] = None) -> None:
        """Stop background profiling"""
        if not self._running:
            return
        
        self._running = False
        if self._sampler_thread:
            self._sampler_thread.join(timeout=2.0)
        
        logger.info(f"SystemProfiler stopped ({len(self._snapshots)} snapshots collected)")
    
    def emit(self, record: ProfileRecord) -> None:
        """Emit not used for system profiling (uses snapshots)"""
        pass
    
    def _sample_loop(self) -> None:
        """Background sampling loop"""
        while self._running:
            try:
                self._collect_snapshot()
                time.sleep(self._config.sampling_interval)
            except Exception as e:
                logger.error(f"SystemProfiler sampling error: {e}", exc_info=True)
    
    def _collect_snapshot(self) -> None:
        """Collect single system snapshot"""
        snapshot = SystemSnapshot(
            timestamp=time.time(),
            cpu_percent=self._process.cpu_percent() if self._config.monitor_cpu else 0.0,
            memory_mb=self._process.memory_info().rss / 1024 / 1024 if self._config.monitor_memory else 0.0,
            thread_count=threading.active_count() if self._config.monitor_threads else 0,
            gc_count={i: gc.get_count()[i] for i in range(3)} if self._config.monitor_gc else {}
        )
        
        with self._lock:
            self._snapshots.append(snapshot)
            
            # Keep only max_snapshots
            if len(self._snapshots) > self._config.max_snapshots:
                self._snapshots.pop(0)
        
        # Check thresholds and emit warnings
        if self._config.monitor_cpu and snapshot.cpu_percent > self._config.cpu_percent:
            logger.warning(f"High CPU usage: {snapshot.cpu_percent:.1f}%")
        
        if self._config.monitor_memory:
            memory_increase = snapshot.memory_mb - self._baseline_memory_mb
            if memory_increase > self._config.memory_mb:
                logger.warning(f"High memory increase: {memory_increase:.1f} MB")
    
    def get_snapshots(self, count: Optional[int] = None) -> List[SystemSnapshot]:
        """
        Get recent snapshots.
        
        Args:
            count: Number of snapshots to return (None = all)
        
        Returns:
            List of snapshots
        """
        with self._lock:
            if count is None:
                return list(self._snapshots)
            return list(self._snapshots[-count:])
    
    def get_summary(self, window_seconds: Optional[float] = None) -> Dict:
        """
        Get summary statistics.
        
        Args:
            window_seconds: Time window in seconds (None = all)
        
        Returns:
            Summary statistics
        """
        with self._lock:
            snapshots = self._snapshots
            
            if window_seconds is not None:
                cutoff = time.time() - window_seconds
                snapshots = [s for s in snapshots if s.timestamp >= cutoff]
            
            if not snapshots:
                return {
                    "count": 0,
                    "window_seconds": window_seconds,
                }
            
            cpu_values = [s.cpu_percent for s in snapshots if s.cpu_percent > 0]
            memory_values = [s.memory_mb for s in snapshots if s.memory_mb > 0]
            
            return {
                "count": len(snapshots),
                "window_seconds": window_seconds,
                "cpu": {
                    "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
                    "max": max(cpu_values) if cpu_values else 0.0,
                    "min": min(cpu_values) if cpu_values else 0.0,
                },
                "memory": {
                    "avg_mb": sum(memory_values) / len(memory_values) if memory_values else 0.0,
                    "max_mb": max(memory_values) if memory_values else 0.0,
                    "min_mb": min(memory_values) if memory_values else 0.0,
                    "baseline_mb": self._baseline_memory_mb,
                },
                "threads": {
                    "current": threading.active_count(),
                },
            }
    
    def clear_snapshots(self) -> None:
        """Clear all snapshots"""
        with self._lock:
            self._snapshots.clear()
        logger.info("SystemProfiler snapshots cleared")
