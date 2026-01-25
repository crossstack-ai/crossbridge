"""
Framework-Specific Performance Profiling Hooks

Pytest integration for performance profiling.
"""

import time
import pytest
from typing import Optional

from core.profiling.models import PerformanceEvent, EventType
from core.profiling.collector import MetricsCollector
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class ProfilingPlugin:
    """Pytest plugin for performance profiling"""
    
    def __init__(self, collector: Optional[MetricsCollector] = None):
        self.collector = collector or MetricsCollector.get_instance()
        self.test_start_times = {}
        self.setup_start_times = {}
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        """Hook: before test setup"""
        test_id = item.nodeid
        self.setup_start_times[test_id] = time.monotonic()
        
        yield
        
        # After setup
        if test_id in self.setup_start_times:
            duration_ms = (time.monotonic() - self.setup_start_times[test_id]) * 1000
            
            if self.collector.current_run_id:
                event = PerformanceEvent.create(
                    run_id=self.collector.current_run_id,
                    test_id=test_id,
                    event_type=EventType.SETUP_END,
                    framework="pytest",
                    duration_ms=duration_ms,
                )
                self.collector.collect(event)
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        """Hook: before test execution"""
        test_id = item.nodeid
        self.test_start_times[test_id] = time.monotonic()
        
        # Emit test start event
        if self.collector.current_run_id:
            event = PerformanceEvent.create(
                run_id=self.collector.current_run_id,
                test_id=test_id,
                event_type=EventType.TEST_START,
                framework="pytest",
                duration_ms=0,
            )
            self.collector.collect(event)
        
        yield
        
        # After test execution
        if test_id in self.test_start_times:
            duration_ms = (time.monotonic() - self.test_start_times[test_id]) * 1000
            
            if self.collector.current_run_id:
                event = PerformanceEvent.create(
                    run_id=self.collector.current_run_id,
                    test_id=test_id,
                    event_type=EventType.TEST_END,
                    framework="pytest",
                    duration_ms=duration_ms,
                    status="passed",  # pytest will handle actual status
                )
                self.collector.collect(event)
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        """Hook: before test teardown"""
        test_id = item.nodeid
        teardown_start = time.monotonic()
        
        yield
        
        # After teardown
        duration_ms = (time.monotonic() - teardown_start) * 1000
        
        if self.collector.current_run_id:
            event = PerformanceEvent.create(
                run_id=self.collector.current_run_id,
                test_id=test_id,
                event_type=EventType.TEARDOWN_END,
                framework="pytest",
                duration_ms=duration_ms,
            )
            self.collector.collect(event)
    
    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_makereport(self, item, call):
        """Hook: capture test outcome"""
        if call.when == "call":
            test_id = item.nodeid
            outcome = "passed" if call.excinfo is None else "failed"
            
            # Update test status in metadata
            # This would be stored with the test_end event
            pass


def pytest_configure(config):
    """Register profiling plugin"""
    if config.pluginmanager.hasplugin("profiling"):
        return
    
    plugin = ProfilingPlugin()
    config.pluginmanager.register(plugin, "profiling")


def pytest_unconfigure(config):
    """Unregister profiling plugin"""
    plugin = config.pluginmanager.getplugin("profiling")
    if plugin:
        config.pluginmanager.unregister(plugin)
