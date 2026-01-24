"""
Robot Framework Listener for Performance Profiling

Integrates with Robot Framework test lifecycle to capture performance metrics.
"""

import logging
import time
from typing import Optional
from datetime import datetime, timezone

from core.profiling.models import PerformanceEvent, EventType
from core.profiling.collector import MetricsCollector

logger = logging.getLogger(__name__)


class CrossBridgeProfilingListener:
    """
    Robot Framework listener for performance profiling.
    
    Usage:
        robot --listener core.profiling.hooks.robot_hook.CrossBridgeProfilingListener tests/
    """
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        self.collector = MetricsCollector.get_instance()
        self.test_start_times = {}
        self.suite_start_times = {}
    
    def start_suite(self, data, result):
        """Called when a test suite starts"""
        suite_id = result.id
        self.suite_start_times[suite_id] = time.monotonic()
    
    def end_suite(self, data, result):
        """Called when a test suite ends"""
        pass
    
    def start_test(self, data, result):
        """Called when a test case starts"""
        test_id = f"{result.parent.name}::{result.name}"
        self.test_start_times[test_id] = time.monotonic()
        
        if self.collector.current_run_id:
            event = PerformanceEvent.create(
                run_id=self.collector.current_run_id,
                test_id=test_id,
                event_type=EventType.TEST_START,
                framework="robot",
                duration_ms=0,
                suite=result.parent.name,
            )
            self.collector.collect(event)
    
    def end_test(self, data, result):
        """Called when a test case ends"""
        test_id = f"{result.parent.name}::{result.name}"
        
        if test_id in self.test_start_times:
            duration_ms = (time.monotonic() - self.test_start_times[test_id]) * 1000
            
            status = "passed" if result.passed else "failed"
            
            if self.collector.current_run_id:
                event = PerformanceEvent.create(
                    run_id=self.collector.current_run_id,
                    test_id=test_id,
                    event_type=EventType.TEST_END,
                    framework="robot",
                    duration_ms=duration_ms,
                    status=status,
                    suite=result.parent.name,
                    message=result.message if result.message else "",
                )
                self.collector.collect(event)
            
            del self.test_start_times[test_id]
    
    def start_keyword(self, data, result):
        """Called when a keyword starts"""
        # Optional: Track keyword-level performance
        pass
    
    def end_keyword(self, data, result):
        """Called when a keyword ends"""
        # Optional: Track keyword-level performance
        pass
