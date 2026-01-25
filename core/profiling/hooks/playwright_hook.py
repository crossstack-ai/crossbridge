"""
Playwright Reporter for Performance Profiling

Integrates with Playwright test runner to capture performance metrics.
"""

import time
from typing import Optional, Dict, Any

from core.profiling.models import PerformanceEvent, EventType
from core.profiling.collector import MetricsCollector
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class CrossBridgePlaywrightReporter:
    """
    Playwright reporter for performance profiling.
    
    Usage in playwright.config.js:
        reporter: [
            ['list'],
            ['./core/profiling/hooks/playwright_reporter.py']
        ]
    
    Or programmatically:
        from core.profiling.hooks.playwright_hook import CrossBridgePlaywrightReporter
        reporter = CrossBridgePlaywrightReporter()
    """
    
    def __init__(self):
        self.collector = MetricsCollector.get_instance()
        self.test_start_times: Dict[str, float] = {}
    
    def onBegin(self, config, suite):
        """Called when test run begins"""
        pass
    
    def onTestBegin(self, test, result):
        """Called when a test begins"""
        test_id = f"{test.location.file}::{test.title}"
        self.test_start_times[test_id] = time.monotonic()
        
        if self.collector.current_run_id:
            event = PerformanceEvent.create(
                run_id=self.collector.current_run_id,
                test_id=test_id,
                event_type=EventType.TEST_START,
                framework="playwright",
                duration_ms=0,
                browser=test.parent.project.use.get('browserName', 'unknown'),
            )
            self.collector.collect(event)
    
    def onTestEnd(self, test, result):
        """Called when a test ends"""
        test_id = f"{test.location.file}::{test.title}"
        
        if test_id in self.test_start_times:
            duration_ms = (time.monotonic() - self.test_start_times[test_id]) * 1000
            
            status_map = {
                'passed': 'passed',
                'failed': 'failed',
                'timedOut': 'timeout',
                'skipped': 'skipped',
            }
            status = status_map.get(result.status, 'unknown')
            
            if self.collector.current_run_id:
                event = PerformanceEvent.create(
                    run_id=self.collector.current_run_id,
                    test_id=test_id,
                    event_type=EventType.TEST_END,
                    framework="playwright",
                    duration_ms=duration_ms,
                    status=status,
                    browser=test.parent.project.use.get('browserName', 'unknown'),
                    retry=result.retry,
                    error=result.error.message if result.error else None,
                )
                self.collector.collect(event)
            
            del self.test_start_times[test_id]
    
    def onStepBegin(self, test, result, step):
        """Called when a test step begins"""
        # Track individual step performance
        pass
    
    def onStepEnd(self, test, result, step):
        """Called when a test step ends"""
        # Track individual step performance
        test_id = f"{test.location.file}::{test.title}"
        
        if self.collector.current_run_id and step.duration:
            event = PerformanceEvent.create(
                run_id=self.collector.current_run_id,
                test_id=test_id,
                event_type=EventType.STEP_END,
                framework="playwright",
                duration_ms=step.duration,
                step_name=step.title,
                category=step.category,
            )
            self.collector.collect(event)
    
    def onEnd(self, result):
        """Called when test run ends"""
        pass


# JavaScript/Node.js integration wrapper
PLAYWRIGHT_REPORTER_JS = """
// Save as: playwright-crossbridge-reporter.js
// Usage: reporter: [['./playwright-crossbridge-reporter.js']]

const { spawn } = require('child_process');

class CrossBridgeReporter {
  onBegin(config, suite) {
    // Initialize profiling
    this.startTime = Date.now();
  }

  onTestBegin(test, result) {
    const testId = `${test.location.file}::${test.title}`;
    const event = {
      test_id: testId,
      event_type: 'test_start',
      framework: 'playwright',
      timestamp: Date.now(),
      browser: test.parent.project.use.browserName || 'unknown'
    };
    this.sendEvent(event);
  }

  onTestEnd(test, result) {
    const testId = `${test.location.file}::${test.title}`;
    const event = {
      test_id: testId,
      event_type: 'test_end',
      framework: 'playwright',
      duration_ms: result.duration,
      status: result.status,
      browser: test.parent.project.use.browserName || 'unknown',
      timestamp: Date.now()
    };
    this.sendEvent(event);
  }

  sendEvent(event) {
    // Send to CrossBridge profiling endpoint
    // This would typically use HTTP or write to a file
    console.log('[CrossBridge]', JSON.stringify(event));
  }

  onEnd(result) {
    console.log('[CrossBridge] Test run complete');
  }
}

module.exports = CrossBridgeReporter;
"""
