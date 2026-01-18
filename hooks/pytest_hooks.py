"""
CrossBridge Pytest Hook Plugin

Lightweight pytest plugin that emits execution events to CrossBridge.

Installation:
    Add to conftest.py:
    
    pytest_plugins = ['crossbridge.hooks.pytest_hooks']
    
Or install as pytest plugin:
    
    pip install crossbridge
    pytest --crossbridge-enabled

The hook is optional and can be disabled via:
    - Environment: CROSSBRIDGE_HOOKS_ENABLED=false
    - Config: crossbridge.yaml
    - CLI: pytest --no-crossbridge
"""

import pytest
import time
from typing import Optional

from core.observability import crossbridge


# Plugin enable/disable flag
def pytest_addoption(parser):
    """Add CrossBridge command-line options"""
    group = parser.getgroup('crossbridge')
    group.addoption(
        '--crossbridge-enabled',
        action='store_true',
        default=True,
        help='Enable CrossBridge observability hooks (default: True)'
    )
    group.addoption(
        '--no-crossbridge',
        action='store_true',
        default=False,
        help='Disable CrossBridge hooks'
    )


def pytest_configure(config):
    """Configure CrossBridge plugin"""
    config.addinivalue_line(
        "markers", "crossbridge: mark test for CrossBridge observability"
    )
    
    # Disable if requested
    if config.getoption('--no-crossbridge'):
        crossbridge.enabled = False


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """
    Hook called for each test execution.
    Wraps test execution to emit start/end events.
    """
    if not crossbridge.enabled:
        yield
        return
    
    # Record start time
    start_time = time.time()
    
    # Emit test start event
    try:
        crossbridge.emit_test_start(
            framework="pytest",
            test_id=item.nodeid,
            file_path=str(item.fspath),
            function_name=item.name,
            markers=[marker.name for marker in item.iter_markers()]
        )
    except Exception as e:
        # Never fail test due to hook errors
        pass
    
    # Execute test
    outcome = yield
    
    # Calculate duration
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Emit test end event (handled in pytest_runtest_makereport)
    return outcome


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook called after test execution to create report.
    Emits test end event with status and duration.
    """
    outcome = yield
    report = outcome.get_result()
    
    if not crossbridge.enabled:
        return
    
    # Only emit on test call phase (not setup/teardown)
    if call.when == "call":
        try:
            # Determine status
            if report.passed:
                status = "passed"
            elif report.failed:
                status = "failed"
            elif report.skipped:
                status = "skipped"
            else:
                status = "error"
            
            # Extract error details
            error_message = None
            stack_trace = None
            if report.failed:
                if hasattr(report.longrepr, 'reprcrash'):
                    error_message = report.longrepr.reprcrash.message
                if hasattr(report.longrepr, 'reprtraceback'):
                    stack_trace = str(report.longrepr.reprtraceback)
            
            # Emit test end event
            crossbridge.emit_test_end(
                framework="pytest",
                test_id=item.nodeid,
                status=status,
                duration_ms=int(call.duration * 1000),
                error_message=error_message,
                stack_trace=stack_trace,
                file_path=str(item.fspath),
                function_name=item.name
            )
            
        except Exception as e:
            # Never fail test due to hook errors
            pass


# Additional hooks for API/UI coverage

def pytest_runtest_call(item):
    """
    Hook called during test execution.
    Can be used to intercept API calls, UI interactions, etc.
    """
    # Future: Auto-detect API calls via monkey-patching requests/httpx
    # Future: Auto-detect UI interactions via Selenium/Playwright hooks
    pass


# Usage example for manual instrumentation
def track_api_call(endpoint: str, method: str, status_code: int, duration_ms: Optional[int] = None):
    """
    Helper function for manual API call tracking in tests.
    
    Usage in test:
        from crossbridge.hooks.pytest_hooks import track_api_call
        
        response = requests.get("/api/users")
        track_api_call("/api/users", "GET", response.status_code, response.elapsed.total_seconds() * 1000)
    """
    if not crossbridge.enabled:
        return
    
    # Get current test ID from pytest
    import inspect
    frame = inspect.currentframe()
    test_id = "unknown"
    try:
        # Walk up stack to find pytest test
        while frame:
            if 'item' in frame.f_locals and hasattr(frame.f_locals['item'], 'nodeid'):
                test_id = frame.f_locals['item'].nodeid
                break
            frame = frame.f_back
    finally:
        del frame
    
    crossbridge.emit_api_call(
        framework="pytest",
        test_id=test_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms
    )


def track_ui_interaction(component_name: str, interaction_type: str, page_url: str):
    """
    Helper function for manual UI interaction tracking.
    
    Usage in test:
        from crossbridge.hooks.pytest_hooks import track_ui_interaction
        
        driver.find_element(By.ID, "login-button").click()
        track_ui_interaction("login-button", "click", driver.current_url)
    """
    if not crossbridge.enabled:
        return
    
    # Get current test ID
    import inspect
    frame = inspect.currentframe()
    test_id = "unknown"
    try:
        while frame:
            if 'item' in frame.f_locals and hasattr(frame.f_locals['item'], 'nodeid'):
                test_id = frame.f_locals['item'].nodeid
                break
            frame = frame.f_back
    finally:
        del frame
    
    crossbridge.emit_ui_interaction(
        framework="pytest",
        test_id=test_id,
        component_name=component_name,
        interaction_type=interaction_type,
        page_url=page_url
    )
