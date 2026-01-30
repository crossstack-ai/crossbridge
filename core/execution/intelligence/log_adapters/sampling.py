"""
Log Sampling System

High-volume log management with intelligent sampling:
- Level-based sampling (INFO: 1%, ERROR: 100%)
- Rate limiting
- Performance guardrails

Prevents system overload while preserving critical events.
"""

import logging
import random
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

from core.execution.intelligence.log_adapters.schema import LogLevel

logger = logging.getLogger(__name__)


@dataclass
class SamplingConfig:
    """Configuration for log sampling."""
    
    # Sampling rates by log level (0.0-1.0)
    debug_rate: float = 0.01    # 1% of DEBUG logs
    info_rate: float = 0.01     # 1% of INFO logs
    warn_rate: float = 0.1      # 10% of WARN logs
    error_rate: float = 1.0     # 100% of ERROR logs
    fatal_rate: float = 1.0     # 100% of FATAL logs
    
    # Rate limiting (events per second)
    max_events_per_second: int = 1000
    
    # Always sample these patterns (even if rate limited)
    always_sample_patterns: list = None
    
    # Never sample these patterns (blacklist)
    never_sample_patterns: list = None
    
    def __post_init__(self):
        if self.always_sample_patterns is None:
            self.always_sample_patterns = []
        if self.never_sample_patterns is None:
            self.never_sample_patterns = []


class LogSampler:
    """
    Intelligent log sampling with rate limiting.
    
    Ensures system performance while preserving critical events.
    """
    
    def __init__(self, config: Optional[SamplingConfig] = None):
        """
        Initialize log sampler.
        
        Args:
            config: Sampling configuration
        """
        self.config = config or SamplingConfig()
        
        # Rate limiting state
        self._event_count = 0
        self._window_start = datetime.now(UTC)
        self._window_duration = timedelta(seconds=1)
        
        # Sampling statistics
        self._total_events = 0
        self._sampled_events = 0
        self._rate_limited_events = 0
        self._by_level = {
            LogLevel.DEBUG: {'total': 0, 'sampled': 0},
            LogLevel.INFO: {'total': 0, 'sampled': 0},
            LogLevel.WARN: {'total': 0, 'sampled': 0},
            LogLevel.ERROR: {'total': 0, 'sampled': 0},
            LogLevel.FATAL: {'total': 0, 'sampled': 0},
        }
    
    def should_sample(self, log_event: Dict) -> bool:
        """
        Determine if a log event should be sampled.
        
        Args:
            log_event: Normalized log event dict
            
        Returns:
            True if event should be processed, False if should be dropped
        """
        self._total_events += 1
        
        # Get log level
        level_str = log_event.get('level', 'INFO')
        try:
            level = LogLevel(level_str)
        except ValueError:
            level = LogLevel.INFO
        
        # Update level statistics
        if level in self._by_level:
            self._by_level[level]['total'] += 1
        
        # Check blacklist patterns (never sample)
        message = log_event.get('message', '').lower()
        if self._matches_patterns(message, self.config.never_sample_patterns):
            return False
        
        # Check whitelist patterns (always sample)
        if self._matches_patterns(message, self.config.always_sample_patterns):
            self._sampled_events += 1
            if level in self._by_level:
                self._by_level[level]['sampled'] += 1
            return True
        
        # Check rate limiting
        if not self._check_rate_limit():
            self._rate_limited_events += 1
            return False
        
        # Apply level-based sampling
        sample_rate = self._get_sample_rate(level)
        should_sample = random.random() < sample_rate
        
        if should_sample:
            self._sampled_events += 1
            if level in self._by_level:
                self._by_level[level]['sampled'] += 1
        
        return should_sample
    
    def _get_sample_rate(self, level: LogLevel) -> float:
        """Get sampling rate for log level."""
        rate_map = {
            LogLevel.DEBUG: self.config.debug_rate,
            LogLevel.INFO: self.config.info_rate,
            LogLevel.WARN: self.config.warn_rate,
            LogLevel.ERROR: self.config.error_rate,
            LogLevel.FATAL: self.config.fatal_rate,
        }
        return rate_map.get(level, 1.0)
    
    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.
        
        Returns:
            True if within limits, False if rate limited
        """
        now = datetime.now(UTC)
        
        # Reset window if needed
        if now - self._window_start >= self._window_duration:
            self._event_count = 0
            self._window_start = now
        
        # Check limit
        if self._event_count >= self.config.max_events_per_second:
            return False
        
        self._event_count += 1
        return True
    
    def _matches_patterns(self, message: str, patterns: list) -> bool:
        """Check if message matches any patterns."""
        if not patterns:
            return False
        
        for pattern in patterns:
            if pattern.lower() in message:
                return True
        
        return False
    
    def get_statistics(self) -> Dict:
        """
        Get sampling statistics.
        
        Returns:
            Dictionary with sampling stats
        """
        sampling_rate = 0.0
        if self._total_events > 0:
            sampling_rate = self._sampled_events / self._total_events
        
        # Level-wise statistics
        level_stats = {}
        for level, stats in self._by_level.items():
            total = stats['total']
            sampled = stats['sampled']
            rate = sampled / total if total > 0 else 0.0
            level_stats[level.value] = {
                'total': total,
                'sampled': sampled,
                'rate': rate
            }
        
        return {
            'total_events': self._total_events,
            'sampled_events': self._sampled_events,
            'rate_limited_events': self._rate_limited_events,
            'overall_sampling_rate': sampling_rate,
            'by_level': level_stats,
            'config': {
                'debug_rate': self.config.debug_rate,
                'info_rate': self.config.info_rate,
                'warn_rate': self.config.warn_rate,
                'error_rate': self.config.error_rate,
                'fatal_rate': self.config.fatal_rate,
                'max_events_per_second': self.config.max_events_per_second,
            }
        }
    
    def reset_statistics(self):
        """Reset sampling statistics."""
        self._total_events = 0
        self._sampled_events = 0
        self._rate_limited_events = 0
        for level in self._by_level:
            self._by_level[level] = {'total': 0, 'sampled': 0}


class AdaptiveSampler(LogSampler):
    """
    Adaptive log sampler that adjusts rates based on load.
    
    Automatically reduces sampling when system is under heavy load.
    """
    
    def __init__(
        self,
        config: Optional[SamplingConfig] = None,
        adaptation_window: int = 60  # seconds
    ):
        """
        Initialize adaptive sampler.
        
        Args:
            config: Base sampling configuration
            adaptation_window: Time window for load measurement (seconds)
        """
        super().__init__(config)
        self.adaptation_window = adaptation_window
        self._load_history = []
        self._adaptation_factor = 1.0  # 1.0 = no adaptation
    
    def should_sample(self, log_event: Dict) -> bool:
        """Sample with adaptive rate adjustment."""
        # Update load metrics
        self._update_load()
        
        # Adjust sampling rates based on load
        original_config = self.config
        if self._adaptation_factor < 1.0:
            # Reduce sampling rates proportionally
            self.config = SamplingConfig(
                debug_rate=original_config.debug_rate * self._adaptation_factor,
                info_rate=original_config.info_rate * self._adaptation_factor,
                warn_rate=original_config.warn_rate * self._adaptation_factor,
                error_rate=original_config.error_rate,  # Never reduce error sampling
                fatal_rate=original_config.fatal_rate,  # Never reduce fatal sampling
                max_events_per_second=original_config.max_events_per_second,
                always_sample_patterns=original_config.always_sample_patterns,
                never_sample_patterns=original_config.never_sample_patterns,
            )
        
        result = super().should_sample(log_event)
        
        # Restore original config
        self.config = original_config
        
        return result
    
    def _update_load(self):
        """Update load metrics and adaptation factor."""
        now = datetime.now(UTC)
        
        # Add current load sample
        load = self._event_count / max(1, self.config.max_events_per_second)
        self._load_history.append((now, load))
        
        # Remove old samples
        cutoff = now - timedelta(seconds=self.adaptation_window)
        self._load_history = [
            (t, l) for t, l in self._load_history
            if t > cutoff
        ]
        
        # Calculate average load
        if self._load_history:
            avg_load = sum(l for _, l in self._load_history) / len(self._load_history)
            
            # Adjust adaptation factor
            if avg_load > 0.8:
                # High load: reduce sampling aggressively
                self._adaptation_factor = 0.5
            elif avg_load > 0.6:
                # Medium load: reduce sampling moderately
                self._adaptation_factor = 0.75
            else:
                # Normal load: no adaptation
                self._adaptation_factor = 1.0


__all__ = [
    'SamplingConfig',
    'LogSampler',
    'AdaptiveSampler',
]
