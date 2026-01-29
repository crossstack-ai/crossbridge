"""
No-Op Profiler

Zero-cost profiler when profiling is disabled.
This ensures no overhead when profiling is turned off.

CRITICAL: This is the default profiler.
"""

from typing import Dict, Any, Optional
from .base import Profiler, ProfileRecord


class NoOpProfiler(Profiler):
    """
    No-operation profiler.
    
    All methods are no-ops and should be optimized away by Python.
    This ensures ZERO cost when profiling is disabled.
    
    Usage:
        profiler = NoOpProfiler()
        profiler.start("test")  # Does nothing
        profiler.stop("test")   # Does nothing
    """
    
    def start(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """No-op start"""
        pass
    
    def stop(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """No-op stop"""
        pass
    
    def emit(self, record: ProfileRecord) -> None:
        """No-op emit"""
        pass
    
    def is_enabled(self) -> bool:
        """Always returns False"""
        return False
    
    def should_profile(self, name: str) -> bool:
        """Always returns False"""
        return False
