"""
CrossBridge Robot Framework Listener
Universal sidecar adapter for Robot Framework test monitoring.

Usage:
    export PYTHONPATH=$PYTHONPATH:/path/to/adapter
    export ROBOT_LISTENER=crossbridge_listener.CrossBridgeListener
    
    # For remote sidecar mode:
    export CROSSBRIDGE_ENABLED=true
    export CROSSBRIDGE_SIDECAR_HOST=crossbridge-server.example.com
    export CROSSBRIDGE_SIDECAR_PORT=8765
    
    robot tests/
"""

import os
import sys
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


class CrossBridgeListener:
    """Universal Robot Framework listener for CrossBridge sidecar."""
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        """Initialize listener with sidecar connection."""
        self.enabled = os.getenv('CROSSBRIDGE_ENABLED', 'false').lower() == 'true'
        
        if not self.enabled:
            return
        
        # Use remote client if available, otherwise fallback to direct HTTP
        if REMOTE_CLIENT_AVAILABLE:
            host = os.getenv('CROSSBRIDGE_SIDECAR_HOST', os.getenv('CROSSBRIDGE_API_HOST', 'localhost'))
            port = int(os.getenv('CROSSBRIDGE_SIDECAR_PORT', os.getenv('CROSSBRIDGE_API_PORT', '8765')))
            
            try:
                self.client = RemoteSidecarClient(host=host, port=port)
                self.client.start()
                print(f"✅ CrossBridge listener connected to {host}:{port} (using RemoteSidecarClient)")
            except Exception as e:
                print(f"⚠️ CrossBridge listener failed to initialize client: {e}")
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
                    print(f"✅ CrossBridge listener connected to {self.api_host}:{self.api_port} (using direct HTTP)")
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
                    metadata={'framework': 'robot'}
                )
            else:
                # Fallback to direct HTTP
                event = {
                    'event_type': event_type,
                    'framework': 'robot',
                    'data': data,
                    'timestamp': datetime.utcnow().timestamp()
                }
                requests.post(self.api_url, json=event, timeout=self.timeout)
        except Exception:
            pass  # Fail-open: never block test execution
    
    def close(self):
        """Cleanup on listener close."""
        if hasattr(self, 'client') and self.client:
            try:
                self.client.stop()
            except Exception:
                pass
    
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
            'test_id': test.id,
            'tags': list(test.tags) if hasattr(test, 'tags') else [],
        })
    
    def end_test(self, test, result):
        """Called when a test ends."""
        self._send_event('test_end', {
            'test_name': test.name,
            'test_id': test.id,
            'status': result.status,
            'message': result.message,
            'elapsed_time': result.elapsedtime / 1000.0,
            'tags': list(test.tags) if hasattr(test, 'tags') else [],
        })
    
    def close(self):
        """Called when execution finishes."""
        if self.enabled:
            self._send_event('execution_complete', {'message': 'Test execution completed'})
