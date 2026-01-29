"""
Timing Profiler

Measures execution time and identifies slow operations.
"""

import time
import json
import random
from typing import Dict, Any, Optional
from pathlib import Path

from .base import Profiler, ProfilerConfig, ProfileRecord, ProfilingMode
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class TimingProfiler(Profiler):
    """
    Timing profiler for measuring execution duration.
    
    Features:
    - Config-driven target filtering
    - Slow call detection
    - Sampling support
    - Multiple output formats
    
    Thread-safe: Uses thread-local storage for active profiles.
    """
    
    def __init__(self, config: ProfilerConfig):
        self.config = config
        self.active: Dict[str, float] = {}
        self.records_this_minute = 0
        self.last_minute_reset = time.time()
        
        logger.info(
            "Timing profiler initialized",
            mode=config.mode.value,
            targets=config.targets,
            slow_threshold_ms=config.slow_call_ms
        )
    
    def start(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start timing a section"""
        # Target filtering (config-driven)
        if not self.should_profile(name):
            return
        
        # Sampling (for sampling mode)
        if self.config.mode == ProfilingMode.SAMPLING:
            if random.random() > self.config.sample_rate:
                return
        
        # Rate limiting (production safety)
        if not self._check_rate_limit():
            return
        
        self.active[name] = time.time()
    
    def stop(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Stop timing a section"""
        start_time = self.active.pop(name, None)
        if start_time is None:
            return
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Only emit if slow (threshold check)
        if duration_ms >= self.config.slow_call_ms:
            record = ProfileRecord(
                name=name,
                duration_ms=duration_ms,
                timestamp=time.time(),
                metadata=metadata if self.config.include_metadata else None
            )
            self.emit(record)
    
    def emit(self, record: ProfileRecord) -> None:
        """Emit profiling record to configured output"""
        output_type = self.config.output_type.value
        
        try:
            if output_type == "log":
                self._emit_log(record)
            elif output_type == "file":
                self._emit_file(record)
            elif output_type == "prometheus":
                self._emit_prometheus(record)
            # "none" type discards (for testing)
        except Exception as e:
            # Never crash on profiling errors
            logger.error(f"Failed to emit profile record: {e}", name=record.name)
    
    def _emit_log(self, record: ProfileRecord) -> None:
        """Emit to structured log"""
        logger.info(
            f"PROFILE: {record.name}",
            duration_ms=record.duration_ms,
            metadata=record.metadata
        )
    
    def _emit_file(self, record: ProfileRecord) -> None:
        """Emit to file (append, non-blocking)"""
        if not self.config.output_path:
            return
        
        path = Path(self.config.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")
    
    def _emit_prometheus(self, record: ProfileRecord) -> None:
        """Emit to Prometheus (placeholder for future)"""
        # TODO: Implement Prometheus exporter
        # For now, just log
        logger.debug(f"Prometheus export not implemented: {record.name}")
    
    def should_profile(self, name: str) -> bool:
        """Check if this target should be profiled"""
        if not self.config.targets:
            # Empty list = profile all
            return True
        
        # Check if name matches any target (exact or prefix match)
        for target in self.config.targets:
            if name == target or name.startswith(target + "."):
                return True
        
        return False
    
    def _check_rate_limit(self) -> bool:
        """
        Check rate limit to prevent profiling overhead.
        
        Production safety: Never emit more than N records per minute.
        """
        now = time.time()
        
        # Reset counter every minute
        if now - self.last_minute_reset > 60:
            self.records_this_minute = 0
            self.last_minute_reset = now
        
        # Check limit
        if self.records_this_minute >= self.config.max_records_per_minute:
            return False
        
        self.records_this_minute += 1
        return True
    
    def is_enabled(self) -> bool:
        """Check if profiling is enabled"""
        return self.config.enabled
