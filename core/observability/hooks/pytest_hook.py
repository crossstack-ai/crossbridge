"""
CrossBridge Pytest Hook

Optional pytest plugin that emits execution events to CrossBridge observer.

Installation:
    Add to conftest.py:
    ```python
    pytest_plugins = ["crossbridge.hooks.pytest_hook"]
    ```

Configuration (pytest.ini or pyproject.toml):
    [tool.pytest.ini_options]
    crossbridge_enabled = true
    crossbridge_project_id = "my-project"

The hook is completely optional and non-blocking.
Tests run normally even if CrossBridge observer is unavailable.
"""

import pytest
import logging
from datetime import datetime
from typing import Optional

try:
    from core.observability.hook_sdk import CrossBridgeHookSDK
    from core.observability.events import EventType
    CROSSBRIDGE_AVAILABLE = True
except ImportError:
    CROSSBRIDGE_AVAILABLE = False

logger = logging.getLogger(__name__)


class CrossBridgePytestPlugin:
    """Pytest plugin for CrossBridge event emission"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.getini('crossbridge_enabled') or config.getoption('--crossbridge', default=False)
        self.sdk: Optional[CrossBridgeHookSDK] = None
        
        if self.enabled and CROSSBRIDGE_AVAILABLE:
            try:
                self.sdk = CrossBridgeHookSDK()
                logger.info("CrossBridge pytest hook enabled")
            except Exception as e:
                logger.warning(f"CrossBridge hook initialization failed: {e}")
                self.enabled = False
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        """Called for each test item"""
        if self.enabled and self.sdk:
            # Emit test_start event
            try:
                self.sdk.emit_test_start(
                    framework="pytest",
                    test_id=item.nodeid,
                    metadata={
                        'file': str(item.fspath),
                        'markers': [m.name for m in item.iter_markers()],
                        'keywords': list(item.keywords.keys())
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to emit test_start: {e}")
        
        # Let test run
        outcome = yield
        
        if self.enabled and self.sdk:
            # Emit test_end event
            try:
                report = outcome.get_result()
                if hasattr(report, 'duration'):
                    self.sdk.emit_test_end(
                        framework="pytest",
                        test_id=item.nodeid,
                        status=self._get_status(report),
                        duration_ms=int(report.duration * 1000) if report.duration else None,
                        error_message=self._get_error_message(report),
                        metadata={
                            'outcome': report.outcome if hasattr(report, 'outcome') else None,
                            'when': report.when if hasattr(report, 'when') else None
                        }
                    )
            except Exception as e:
                logger.debug(f"Failed to emit test_end: {e}")
    
    def _get_status(self, report) -> str:
        """Map pytest outcome to standard status"""
        if not hasattr(report, 'outcome'):
            return 'unknown'
        
        outcome_map = {
            'passed': 'passed',
            'failed': 'failed',
            'skipped': 'skipped',
            'error': 'error'
        }
        return outcome_map.get(report.outcome, 'unknown')
    
    def _get_error_message(self, report) -> Optional[str]:
        """Extract error message from report"""
        if hasattr(report, 'longrepr') and report.longrepr:
            return str(report.longrepr)[:1000]  # Limit to 1000 chars
        return None


def pytest_addoption(parser):
    """Add CrossBridge command line options"""
    group = parser.getgroup('crossbridge')
    group.addoption(
        '--crossbridge',
        action='store_true',
        default=False,
        help='Enable CrossBridge event emission'
    )
    group.addoption(
        '--crossbridge-project',
        action='store',
        default=None,
        help='CrossBridge project ID'
    )


def pytest_configure(config):
    """Register CrossBridge plugin"""
    config.addinivalue_line(
        "markers", "crossbridge: mark test for CrossBridge tracking"
    )
    
    if CROSSBRIDGE_AVAILABLE:
        plugin = CrossBridgePytestPlugin(config)
        config.pluginmanager.register(plugin, 'crossbridge_plugin')


# API for direct integration (alternative to plugin)
def emit_test_event(test_id: str, event_type: str, **kwargs):
    """
    Direct API for emitting events from pytest tests.
    
    Usage in test:
        from crossbridge.hooks.pytest_hook import emit_test_event
        
        def test_something():
            emit_test_event("custom_event", event_type="step", step_name="Login")
            # ... test logic
    """
    if not CROSSBRIDGE_AVAILABLE:
        return
    
    try:
        sdk = CrossBridgeHookSDK()
        sdk.emit_custom_event(
            framework="pytest",
            test_id=test_id,
            event_type=event_type,
            **kwargs
        )
    except Exception as e:
        logger.debug(f"Failed to emit custom event: {e}")
