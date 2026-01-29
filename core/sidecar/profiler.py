"""
Lightweight Profiler for Sidecar Runtime

Collects performance metrics with minimal overhead:
- CPU time buckets
- Memory usage trends
- Thread counts
- GC pauses (Python-specific)
"""

import os
import gc
import time
import threading
import psutil
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


@dataclass
class ProfileSnapshot:
    """Point-in-time profile snapshot"""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    thread_count: int = 0
    gc_count: Dict[int, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_mb': self.memory_mb,
            'thread_count': self.thread_count,
            'gc_count': self.gc_count,
        }


class LightweightProfiler:
    """
    Lightweight profiler with <1% overhead
    
    Collects basic performance metrics without deep inspection.
    """
    
    def __init__(self, sampling_interval: float = 1.0):
        """
        Initialize profiler
        
        Args:
            sampling_interval: How often to collect samples (seconds)
        """
        self._sampling_interval = sampling_interval
        self._process = psutil.Process(os.getpid())
        self._snapshots: List[ProfileSnapshot] = []
        self._max_snapshots = 1000  # Keep last 1000 samples
        self._lock = threading.Lock()
        
        # Background sampling
        self._running = False
        self._sampler_thread: Optional[threading.Thread] = None
        
        # Baseline measurement
        self._baseline_memory = self._process.memory_info().rss / 1024 / 1024
    
    def start(self) -> None:
        """Start background profiling"""
        if self._running:
            return
        
        self._running = True
        self._sampler_thread = threading.Thread(
            target=self._sample_loop,
            daemon=True,
            name="sidecar-profiler"
        )
        self._sampler_thread.start()
    
    def stop(self) -> None:
        """Stop background profiling"""
        self._running = False
        if self._sampler_thread:
            self._sampler_thread.join(timeout=2.0)
    
    def _sample_loop(self) -> None:
        """Background sampling loop"""
        while self._running:
            try:
                self.collect()
                time.sleep(self._sampling_interval)
            except Exception:
                # Never crash the profiler thread
                pass
    
    def collect(self) -> ProfileSnapshot:
        """
        Collect a profile snapshot (lightweight)
        
        Returns:
            ProfileSnapshot with current metrics
        """
        try:
            # CPU usage (non-blocking)
            cpu_percent = self._process.cpu_percent(interval=0)
            
            # Memory usage
            mem_info = self._process.memory_info()
            memory_mb = mem_info.rss / 1024 / 1024
            
            # Thread count
            thread_count = threading.active_count()
            
            # GC stats (Python-specific)
            gc_count = {i: gc.get_count()[i] for i in range(3)}
            
            snapshot = ProfileSnapshot(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                thread_count=thread_count,
                gc_count=gc_count
            )
            
            # Store snapshot
            with self._lock:
                self._snapshots.append(snapshot)
                if len(self._snapshots) > self._max_snapshots:
                    self._snapshots.pop(0)
            
            return snapshot
            
        except Exception as e:
            # Fail gracefully
            return ProfileSnapshot()
    
    def get_current(self) -> ProfileSnapshot:
        """Get current profile snapshot"""
        return self.collect()
    
    def get_summary(self, window_seconds: Optional[float] = None) -> Dict:
        """
        Get summary statistics over a time window
        
        Args:
            window_seconds: Time window to analyze (None = all)
            
        Returns:
            Dictionary with summary stats
        """
        with self._lock:
            if not self._snapshots:
                return {
                    'cpu_avg': 0.0,
                    'cpu_max': 0.0,
                    'memory_avg': 0.0,
                    'memory_max': 0.0,
                    'memory_growth_mb': 0.0,
                    'thread_avg': 0.0,
                    'thread_max': 0,
                    'sample_count': 0,
                }
            
            # Filter by window if specified
            snapshots = self._snapshots
            if window_seconds:
                cutoff = time.time() - window_seconds
                snapshots = [s for s in snapshots if s.timestamp >= cutoff]
            
            if not snapshots:
                return self.get_summary(None)  # Fallback to all
            
            cpu_values = [s.cpu_percent for s in snapshots]
            mem_values = [s.memory_mb for s in snapshots]
            thread_values = [s.thread_count for s in snapshots]
            
            return {
                'cpu_avg': sum(cpu_values) / len(cpu_values),
                'cpu_max': max(cpu_values),
                'memory_avg': sum(mem_values) / len(mem_values),
                'memory_max': max(mem_values),
                'memory_growth_mb': mem_values[-1] - mem_values[0] if len(mem_values) > 1 else 0.0,
                'thread_avg': sum(thread_values) / len(thread_values),
                'thread_max': max(thread_values),
                'sample_count': len(snapshots),
            }
    
    def get_recent_snapshots(self, count: int = 10) -> List[ProfileSnapshot]:
        """Get most recent snapshots"""
        with self._lock:
            return self._snapshots[-count:]
    
    def clear_history(self) -> None:
        """Clear snapshot history"""
        with self._lock:
            self._snapshots.clear()
    
    def is_over_budget(self, cpu_budget: float = 5.0, memory_budget_mb: float = 100.0) -> Dict[str, bool]:
        """
        Check if profiler is exceeding resource budgets
        
        Args:
            cpu_budget: CPU budget percentage
            memory_budget_mb: Memory budget in MB
            
        Returns:
            Dictionary with budget violations
        """
        summary = self.get_summary(window_seconds=60)  # Last 60 seconds
        
        return {
            'cpu_over_budget': summary['cpu_avg'] > cpu_budget,
            'memory_over_budget': (summary['memory_avg'] - self._baseline_memory) > memory_budget_mb,
            'cpu_value': summary['cpu_avg'],
            'memory_value': summary['memory_avg'] - self._baseline_memory,
            'cpu_budget': cpu_budget,
            'memory_budget': memory_budget_mb,
        }


class DeepProfiler(LightweightProfiler):
    """
    Deep profiler for debug mode only
    
    WARNING: Higher overhead, should be enabled manually or on anomalies.
    Auto-disables after configured duration.
    """
    
    def __init__(self, duration_sec: float = 30, **kwargs):
        super().__init__(**kwargs)
        self._duration = duration_sec
        self._start_time: Optional[float] = None
        self._enabled = False
    
    def enable(self, duration_sec: Optional[float] = None) -> None:
        """Enable deep profiling for a duration"""
        if duration_sec:
            self._duration = duration_sec
        self._start_time = time.time()
        self._enabled = True
        self.start()
    
    def disable(self) -> None:
        """Disable deep profiling"""
        self._enabled = False
        self.stop()
    
    def _sample_loop(self) -> None:
        """Override to auto-disable after duration"""
        while self._running and self._enabled:
            try:
                # Check if duration expired
                if self._start_time and (time.time() - self._start_time) >= self._duration:
                    self.disable()
                    break
                
                self.collect()
                time.sleep(self._sampling_interval)
            except Exception:
                pass
