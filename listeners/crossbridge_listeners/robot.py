"""
CrossBridge Robot Framework Listener
Lightweight listener for sending test events to remote CrossBridge sidecar.

Usage:
    # Install the package
    pip install git+https://github.com/crossstack-ai/crossbridge.git#subdirectory=listeners
    
    # Set environment variables (replace <sidecar-host> with your server IP/hostname)
    export CROSSBRIDGE_ENABLED=true
    export CROSSBRIDGE_SIDECAR_HOST=<sidecar-host>
    export CROSSBRIDGE_SIDECAR_PORT=8765
    
    # Run tests with listener
    robot --listener crossbridge_listeners.robot.CrossBridgeListener tests/
"""

import os
import requests
from datetime import datetime
from typing import Dict, Any


class CrossBridgeListener:
    """Lightweight Robot Framework listener for CrossBridge remote sidecar."""
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        """Initialize listener with sidecar connection."""
        self.enabled = os.getenv('CROSSBRIDGE_ENABLED', 'false').lower() == 'true'
        
        if not self.enabled:
            return
        
        # Get sidecar connection details
        self.api_host = os.getenv('CROSSBRIDGE_SIDECAR_HOST', os.getenv('CROSSBRIDGE_API_HOST', 'localhost'))
        self.api_port = os.getenv('CROSSBRIDGE_SIDECAR_PORT', os.getenv('CROSSBRIDGE_API_PORT', '8765'))
        self.api_url = f"http://{self.api_host}:{self.api_port}/events"
        self.timeout = 2
        
        # Test connection
        try:
            health_url = f"http://{self.api_host}:{self.api_port}/health"
            response = requests.get(health_url, timeout=self.timeout)
            if response.status_code == 200:
                print(f"✅ CrossBridge listener connected to {self.api_host}:{self.api_port}")
            else:
                print(f"⚠️ CrossBridge sidecar returned status {response.status_code}")
                self.enabled = False
        except Exception as e:
            print(f"⚠️ CrossBridge listener failed to connect: {e}")
            self.enabled = False
    
    def _send_event(self, event_type: str, data: Dict[str, Any], test_id: str = None):
        """Send event to CrossBridge sidecar."""
        if not self.enabled:
            return
        
        try:
            event = {
                'event_type': event_type,
                'framework': 'robot',
                'data': data,
                'timestamp': datetime.utcnow().timestamp(),
                'test_id': test_id
            }
            requests.post(self.api_url, json=event, timeout=self.timeout)
        except Exception:
            pass  # Fail-open: never block test execution
    
    def start_suite(self, suite, result):
        """Called when a suite starts."""
        self._send_event('suite_start', {
            'suite_name': suite.name,
            'suite_id': suite.id,
            'source': str(suite.source) if suite.source else None,
        })
    
    def end_suite(self, suite, result):
        """Called when a suite ends."""
        stats_data = {}
        try:
            stats = result.statistics
            if hasattr(stats, 'total'):
                stats_data = {'total': stats.total, 'passed': stats.passed, 'failed': stats.failed}
            elif hasattr(stats, 'all'):
                all_stats = stats.all
                stats_data = {
                    'total': getattr(all_stats, 'total', 0),
                    'passed': getattr(all_stats, 'passed', 0),
                    'failed': getattr(all_stats, 'failed', 0),
                }
            else:
                tests = list(result.tests) if hasattr(result, 'tests') else []
                stats_data = {
                    'total': len(tests),
                    'passed': sum(1 for t in tests if getattr(t, 'passed', False)),
                    'failed': sum(1 for t in tests if not getattr(t, 'passed', True)),
                }
        except Exception:
            stats_data = {'total': 0, 'passed': 0, 'failed': 0}
        
        self._send_event('suite_end', {
            'suite_name': suite.name,
            'suite_id': suite.id,
            'status': result.status,
            'message': result.message,
            'elapsed_time': result.elapsedtime / 1000.0,
            'statistics': stats_data,
        })
    
    def start_test(self, test, result):
        """Called when a test starts."""
        self._send_event('test_start', {
            'test_name': test.name,
            'tags': list(test.tags) if hasattr(test, 'tags') else [],
        }, test_id=test.id)
    
    def end_test(self, test, result):
        """Called when a test ends."""
        self._send_event('test_end', {
            'test_name': test.name,
            'status': result.status,
            'message': result.message,
            'elapsed_time': result.elapsedtime / 1000.0,
            'tags': list(test.tags) if hasattr(test, 'tags') else [],
        }, test_id=test.id)
    
    def close(self):
        """Called when execution finishes."""
        if self.enabled:
            self._send_event('execution_complete', {'message': 'Test execution completed'})
