"""
CrossBridge Pytest Plugin
Universal sidecar adapter for Pytest test monitoring.

Usage:
    export PYTHONPATH=$PYTHONPATH:/path/to/adapter
    export PYTEST_PLUGINS=crossbridge_plugin
    
    # For remote sidecar mode:
    export CROSSBRIDGE_ENABLED=true
    export CROSSBRIDGE_SIDECAR_HOST=crossbridge-server.example.com
    export CROSSBRIDGE_SIDECAR_PORT=8765
    
    pytest tests/
"""

import os
import sys
import pytest
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from services.sidecar_client import RemoteSidecarClient
    REMOTE_CLIENT_AVAILABLE = True
except ImportError:
    REMOTE_CLIENT_AVAILABLE = False
    import requests  # Fallback to direct HTTP calls


class CrossBridgePlugin:
    """Universal Pytest plugin for CrossBridge sidecar."""
    
    def __init__(self):
        """Initialize plugin with sidecar connection."""
        self.enabled = os.getenv('CROSSBRIDGE_ENABLED', 'false').lower() == 'true'
        self.session_start_time = None
        
        if not self.enabled:
            return
        
        # Use remote client if available, otherwise fallback to direct HTTP
        if REMOTE_CLIENT_AVAILABLE:
            host = os.getenv('CROSSBRIDGE_SIDECAR_HOST', os.getenv('CROSSBRIDGE_API_HOST', 'localhost'))
            port = int(os.getenv('CROSSBRIDGE_SIDECAR_PORT', os.getenv('CROSSBRIDGE_API_PORT', '8765')))
            
            try:
                self.client = RemoteSidecarClient(host=host, port=port)
                self.client.start()
                print(f"✅ CrossBridge pytest plugin connected to {host}:{port} (using RemoteSidecarClient)")
            except Exception as e:
                print(f"⚠️ CrossBridge pytest plugin failed to initialize client: {e}")
                self.enabled = False
                self.client = None
        else:
            # Fallback to direct HTTP calls
            self.client = None
            self.api_host = os.getenv('CROSSBRIDGE_SIDECAR_HOST', os.getenv('CROSSBRIDGE_API_HOST', 'localhost'))
            self.api_port = os.getenv('CROSSBRIDGE_SIDECAR_PORT', os.getenv('CROSSBRIDGE_API_PORT', '8765'))
            self.api_url = f"http://{self.api_host}:{self.api_port}/events"
            self.timeout = 2
            
            try:
                health_url = f"http://{self.api_host}:{self.api_port}/health"
                response = requests.get(health_url, timeout=self.timeout)
                if response.status_code == 200:
                    print(f"✅ CrossBridge pytest plugin connected to {self.api_host}:{self.api_port} (using direct HTTP)")
                else:
                    self.enabled = False
            except Exception:
                self.enabled = False
    
    def _send_event(self, event_type: str, data: Dict[str, Any]):
        """Send event to CrossBridge sidecar."""
        if not self.enabled:
            return
        
        try:
            if self.client:
                # Use remote client (preferred)
                self.client.send_event(
                    event_type=event_type,
                    data=data,
                    metadata={'framework': 'pytest'}
                )
            else:
                # Fallback to direct HTTP
                event = {
                    'event_type': event_type,
                    'framework': 'pytest',
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                requests.post(self.api_url, json=event, timeout=self.timeout)
        except Exception:
            pass  # Fail-open: never block test execution
    
    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        """Called after Session object has been created."""
        self.session_start_time = datetime.utcnow()
        self._send_event('session_start', {
            'session_id': id(session),
            'testpaths': getattr(session.config.option, 'file_or_dir', []),
        })
    
    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """Called after whole test run finished."""
        elapsed = (datetime.utcnow() - self.session_start_time).total_seconds() if self.session_start_time else 0
        self._send_event('session_finish', {
            'session_id': id(session),
            'exit_status': exitstatus,
            'elapsed_time': elapsed,
        })
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        """Called for each test item."""
        self._send_event('test_start', {
            'test_name': item.name,
            'test_id': item.nodeid,
            'file': str(item.fspath),
            'markers': [m.name for m in item.iter_markers()],
        })
        
        outcome = yield
        
        # Test has completed, get results
        result = outcome.get_result()
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """Called for each test phase (setup, call, teardown)."""
        outcome = yield
        report = outcome.get_result()
        
        if report.when == 'call':  # Only report the actual test call
            self._send_event('test_end', {
                'test_name': item.name,
                'test_id': item.nodeid,
                'status': 'PASS' if report.passed else 'FAIL',
                'message': str(report.longrepr) if report.failed else '',
                'elapsed_time': report.duration,
                'markers': [m.name for m in item.iter_markers()],
            })


# Plugin instance
_plugin_instance = None


def pytest_configure(config):
    """Register plugin."""
    global _plugin_instance
    _plugin_instance = CrossBridgePlugin()
    config.pluginmanager.register(_plugin_instance, "crossbridge_plugin")


def pytest_unconfigure(config):
    """Unregister plugin."""
    global _plugin_instance
    if _plugin_instance:
        config.pluginmanager.unregister(_plugin_instance)
        _plugin_instance = None
