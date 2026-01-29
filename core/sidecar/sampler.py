"""
Configurable Sampler for Sidecar Runtime

Provides sampling capabilities with:
- Global sampling rates
- Per-signal sampling rates
- Adaptive sampling (boost on anomalies)
- Thread-safe operations
"""

import random
import threading
import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


class SignalType(Enum):
    """Types of signals that can be sampled"""
    EVENTS = "events"
    TRACES = "traces"
    PROFILING = "profiling"
    TEST_EVENTS = "test_events"
    PERF_METRICS = "perf_metrics"
    DEBUG_LOGS = "debug_logs"


@dataclass
class SamplingBoost:
    """Temporary sampling boost configuration"""
    factor: float
    start_time: float
    duration: float


class Sampler:
    """
    Configurable sampler with per-signal rates
    
    Thread-safe and low overhead.
    """
    
    def __init__(self, default_rate: float = 0.1):
        """
        Initialize sampler
        
        Args:
            default_rate: Default sampling rate (0.0 - 1.0)
        """
        self._default_rate = max(0.0, min(1.0, default_rate))
        self._rates: Dict[str, float] = {}
        self._boosts: Dict[str, SamplingBoost] = {}
        self._lock = threading.RLock()
        self._sample_count: Dict[str, int] = {}
        self._total_count: Dict[str, int] = {}
    
    def set_rate(self, signal_type: str, rate: float) -> None:
        """Set sampling rate for a specific signal type"""
        rate = max(0.0, min(1.0, rate))
        with self._lock:
            self._rates[signal_type] = rate
    
    def should_sample(self, signal_type: str) -> bool:
        """
        Determine if a signal should be sampled
        
        Args:
            signal_type: Type of signal to sample
            
        Returns:
            True if should sample, False otherwise
        """
        with self._lock:
            # Track total count
            self._total_count[signal_type] = self._total_count.get(signal_type, 0) + 1
            
            # Get effective rate (with boost if active)
            rate = self._get_effective_rate(signal_type)
            
            # Sample based on rate
            should_sample = random.random() < rate
            
            if should_sample:
                self._sample_count[signal_type] = self._sample_count.get(signal_type, 0) + 1
            
            return should_sample
    
    def _get_effective_rate(self, signal_type: str) -> float:
        """Get effective sampling rate including any active boosts"""
        base_rate = self._rates.get(signal_type, self._default_rate)
        
        # Check for active boost
        if signal_type in self._boosts:
            boost = self._boosts[signal_type]
            elapsed = time.time() - boost.start_time
            
            if elapsed < boost.duration:
                # Boost is active
                return min(1.0, base_rate * boost.factor)
            else:
                # Boost expired, remove it
                del self._boosts[signal_type]
        
        return base_rate
    
    def boost(self, signal_type: str, factor: float, duration: float) -> None:
        """
        Temporarily boost sampling rate for a signal type
        
        Args:
            signal_type: Signal type to boost
            factor: Multiplication factor (e.g., 5.0 for 5x)
            duration: Duration in seconds
        """
        with self._lock:
            self._boosts[signal_type] = SamplingBoost(
                factor=factor,
                start_time=time.time(),
                duration=duration
            )
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get sampling statistics"""
        with self._lock:
            stats = {}
            for signal_type in set(list(self._rates.keys()) + list(self._sample_count.keys())):
                total = self._total_count.get(signal_type, 0)
                sampled = self._sample_count.get(signal_type, 0)
                rate = self._rates.get(signal_type, self._default_rate)
                
                stats[signal_type] = {
                    'configured_rate': rate,
                    'effective_rate': sampled / total if total > 0 else 0.0,
                    'total_signals': total,
                    'sampled_signals': sampled,
                    'dropped_signals': total - sampled,
                    'has_boost': signal_type in self._boosts
                }
            
            return stats
    
    def reset_stats(self) -> None:
        """Reset sampling statistics"""
        with self._lock:
            self._sample_count.clear()
            self._total_count.clear()


class AdaptiveSampler(Sampler):
    """
    Adaptive sampler that automatically boosts sampling on anomalies
    
    Monitors signal patterns and increases sampling when:
    - Error rates spike
    - Latency increases significantly
    - Resource usage jumps
    """
    
    def __init__(self, default_rate: float = 0.1, anomaly_boost_factor: float = 5.0):
        super().__init__(default_rate)
        self._anomaly_boost_factor = anomaly_boost_factor
        self._anomaly_boost_duration = 60.0  # 60 seconds
        self._error_counts: Dict[str, int] = {}
        self._error_threshold = 5  # Trigger boost after 5 errors
    
    def report_anomaly(self, signal_type: str, anomaly_type: str = "error") -> None:
        """
        Report an anomaly and trigger adaptive boost if threshold reached
        
        Args:
            signal_type: Signal type experiencing anomaly
            anomaly_type: Type of anomaly (error, latency, resource)
        """
        with self._lock:
            key = f"{signal_type}:{anomaly_type}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            
            if self._error_counts[key] >= self._error_threshold:
                # Trigger adaptive boost
                self.boost(signal_type, self._anomaly_boost_factor, self._anomaly_boost_duration)
                # Reset counter
                self._error_counts[key] = 0
    
    def clear_anomalies(self, signal_type: Optional[str] = None) -> None:
        """Clear anomaly counters"""
        with self._lock:
            if signal_type:
                keys_to_clear = [k for k in self._error_counts.keys() if k.startswith(signal_type)]
                for key in keys_to_clear:
                    del self._error_counts[key]
            else:
                self._error_counts.clear()
