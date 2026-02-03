#!/usr/bin/env python3
"""
Start CrossBridge Observer in Sidecar Mode

Runs health server and keeps container alive for external test connections.
"""

import os
import sys
import json
import logging
import signal
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any
from urllib.parse import urlparse, parse_qs
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.OBSERVER)

# Global flag for graceful shutdown
running = True

# Event storage and statistics
class EventStore:
    """In-memory event store with statistics and pattern detection."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        self.suite_count = 0
        self.start_time = datetime.utcnow()
        self.failure_patterns: Counter = Counter()
        self.test_durations: List[float] = []
        self.lock = threading.Lock()
        
    def add_event(self, event: Dict[str, Any]):
        """Add event and update statistics."""
        with self.lock:
            self.events.append(event)
            
            event_type = event.get('event_type')
            data = event.get('data', {})
            
            # Update counters
            if event_type == 'test_end':
                self.test_count += 1
                status = data.get('status', 'UNKNOWN')
                
                if status == 'PASS':
                    self.passed_count += 1
                elif status == 'FAIL':
                    self.failed_count += 1
                    
                    # Track failure patterns
                    message = data.get('message', '')
                    self._extract_failure_pattern(message)
                
                # Track duration
                duration = data.get('elapsed_time')
                if duration:
                    self.test_durations.append(duration)
                    
            elif event_type == 'suite_start':
                self.suite_count += 1
    
    def _extract_failure_pattern(self, message: str):
        """Extract common failure patterns from error messages."""
        if not message:
            return
            
        # Common error patterns
        patterns = [
            (r'SSLError.*CERTIFICATE_VERIFY_FAILED', 'SSL Certificate Verification Failed'),
            (r'ConnectionRefusedError', 'Connection Refused'),
            (r'TimeoutError|timeout', 'Timeout'),
            (r'Authentication.*failed|401.*Unauthorized', 'Authentication Failed'),
            (r'404.*Not Found', '404 Not Found'),
            (r'500.*Internal Server Error', '500 Internal Server Error'),
            (r'ImportError|ModuleNotFoundError', 'Module Import Error'),
            (r'AssertionError', 'Assertion Failed'),
            (r'Parent suite setup failed', 'Suite Setup Failed'),
        ]
        
        for pattern, label in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                self.failure_patterns[label] += 1
                return
        
        # Generic failure
        self.failure_patterns['Other'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self.lock:
            elapsed = (datetime.utcnow() - self.start_time).total_seconds()
            
            return {
                'total_tests': self.test_count,
                'passed': self.passed_count,
                'failed': self.failed_count,
                'failure_rate': round(self.failed_count / self.test_count * 100, 2) if self.test_count > 0 else 0,
                'total_suites': self.suite_count,
                'elapsed_time': f"{elapsed:.0f}s",
                'avg_test_duration': round(sum(self.test_durations) / len(self.test_durations), 2) if self.test_durations else 0,
                'events_received': len(self.events),
                'start_time': self.start_time.isoformat() + 'Z'
            }
    
    def get_failure_patterns(self) -> List[Dict[str, Any]]:
        """Get failure patterns sorted by frequency."""
        with self.lock:
            return [
                {'pattern': pattern, 'count': count, 'percentage': round(count / self.failed_count * 100, 2) if self.failed_count > 0 else 0}
                for pattern, count in self.failure_patterns.most_common()
            ]
    
    def get_filtered_events(self, event_type: str = None, status: str = None, suite: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get filtered events."""
        with self.lock:
            filtered = self.events
            
            if event_type:
                filtered = [e for e in filtered if e.get('event_type') == event_type]
            
            if status:
                filtered = [e for e in filtered if e.get('data', {}).get('status') == status]
            
            if suite:
                filtered = [e for e in filtered if suite.lower() in e.get('data', {}).get('suite_name', '').lower()]
            
            return filtered[-limit:]

# Global event store
event_store = EventStore()


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info(f"Received signal {sig}, shutting down...")
    running = False
    sys.exit(0)


class SimpleHealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks and events."""
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        # Parse query parameters
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)
        
        if path in ['/health', '/health/v1', '/ready', '/live']:
            # Return simple health response
            response = {
                'status': 'healthy',
                'service': 'crossbridge-observer',
                'mode': os.getenv('CROSSBRIDGE_MODE', 'observer'),
                'framework': os.getenv('CROSSBRIDGE_FRAMEWORK', 'robot'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'version': '0.2.0'
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('X-Health-Version', '1.0')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
        
        elif path == '/stats':
            # Return real-time statistics
            stats = event_store.get_statistics()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats, indent=2).encode())
        
        elif path == '/failures/patterns':
            # Return failure patterns analysis
            patterns = event_store.get_failure_patterns()
            
            response = {
                'failure_patterns': patterns,
                'total_failures': event_store.failed_count,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
        
        elif path == '/events':
            # Return filtered events
            event_type = query_params.get('type', [None])[0]
            status = query_params.get('status', [None])[0]
            suite = query_params.get('suite', [None])[0]
            limit = int(query_params.get('limit', [100])[0])
            
            events = event_store.get_filtered_events(
                event_type=event_type,
                status=status,
                suite=suite,
                limit=limit
            )
            
            response = {
                'events': events,
                'count': len(events),
                'filters': {
                    'type': event_type,
                    'status': status,
                    'suite': suite,
                    'limit': limit
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
        
        elif path == '/summary':
            # Return comprehensive test run summary
            stats = event_store.get_statistics()
            patterns = event_store.get_failure_patterns()
            
            # Generate recommendations
            recommendations = []
            if patterns:
                top_failure = patterns[0]
                if top_failure['pattern'] == 'SSL Certificate Verification Failed':
                    recommendations.append({
                        'issue': top_failure['pattern'],
                        'severity': 'HIGH',
                        'affected_tests': top_failure['count'],
                        'suggestion': 'Add SSL certificate to trusted store or use --ssl-no-verify flag for testing',
                        'command': 'robot --variable REQUESTS_CA_BUNDLE:/path/to/cert.pem ...'
                    })
                elif top_failure['pattern'] == 'Suite Setup Failed':
                    recommendations.append({
                        'issue': top_failure['pattern'],
                        'severity': 'CRITICAL',
                        'affected_tests': top_failure['count'],
                        'suggestion': 'Fix suite setup issues before running tests - all child tests will fail',
                        'impact': f"{top_failure['count']} tests failed due to suite setup"
                    })
            
            response = {
                'statistics': stats,
                'failure_patterns': patterns[:5],  # Top 5
                'recommendations': recommendations,
                'health': 'CRITICAL' if stats['failure_rate'] == 100 else 'DEGRADED' if stats['failure_rate'] > 50 else 'HEALTHY',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        elif path == '/metrics':
            # Return enhanced Prometheus metrics
            stats = event_store.get_statistics()
            
            metrics = f"""# HELP crossbridge_up Service is up
# TYPE crossbridge_up gauge
crossbridge_up 1

# HELP crossbridge_mode Current operating mode
# TYPE crossbridge_mode gauge
crossbridge_mode{{mode="observer"}} 1

# HELP crossbridge_tests_total Total number of tests executed
# TYPE crossbridge_tests_total counter
crossbridge_tests_total {stats['total_tests']}

# HELP crossbridge_tests_passed Number of tests passed
# TYPE crossbridge_tests_passed counter
crossbridge_tests_passed {stats['passed']}

# HELP crossbridge_tests_failed Number of tests failed
# TYPE crossbridge_tests_failed counter
crossbridge_tests_failed {stats['failed']}

# HELP crossbridge_failure_rate Test failure rate percentage
# TYPE crossbridge_failure_rate gauge
crossbridge_failure_rate {stats['failure_rate']}

# HELP crossbridge_suites_total Total number of suites executed
# TYPE crossbridge_suites_total counter
crossbridge_suites_total {stats['total_suites']}

# HELP crossbridge_events_received Total events received
# TYPE crossbridge_events_received counter
crossbridge_events_received {stats['events_received']}

# HELP crossbridge_avg_test_duration_seconds Average test duration
# TYPE crossbridge_avg_test_duration_seconds gauge
crossbridge_avg_test_duration_seconds {stats['avg_test_duration']}
"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(metrics.encode())
            
        else:
            # Not found
            response = {
                'error': 'Not found',
                'available_endpoints': [
                    '/health', '/health/v1', '/ready', '/live', 
                    '/metrics', '/events', '/stats', 
                    '/failures/patterns', '/summary'
                ]
            }
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_POST(self):
        """Handle POST requests (events from tests)."""
        if self.path == '/events':
            # Read event data
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                event = json.loads(body.decode('utf-8'))
                
                # Store event in event store
                event_store.add_event(event)
                
                # Log the event with appropriate details
                event_type = event.get('event_type')
                data = event.get('data', {})
                
                # Enhanced logging with statistics
                if 'test_name' in data:
                    status = data.get('status', 'running')
                    duration = data.get('elapsed_time', 0)
                    detail = f"{data['test_name']} [{status}]"
                    if duration and status != 'running':
                        detail += f" ({duration:.2f}s)"
                elif 'suite_name' in data:
                    detail = f"{data['suite_name']}"
                    if event_type == 'suite_end':
                        suite_stats = data.get('statistics', {})
                        if suite_stats:
                            detail += f" [{suite_stats.get('passed', 0)}/{suite_stats.get('total', 0)} passed]"
                else:
                    detail = 'event'
                
                logger.info(f"📨 {event_type}: {detail}")
                
                # Log periodic statistics summary
                stats = event_store.get_statistics()
                if event_type == 'test_end' and stats['total_tests'] % 10 == 0:
                    logger.info(f"📊 Progress: {stats['total_tests']} tests ({stats['passed']} passed, {stats['failed']} failed) - Failure rate: {stats['failure_rate']}%")
                
                # Send success response
                response = {'status': 'accepted', 'timestamp': datetime.utcnow().isoformat() + 'Z'}
                self.send_response(202)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                logger.error(f"Failed to process event: {e}")
                response = {'status': 'error', 'message': str(e)}
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
        else:
            # Not found
            response = {'error': 'Not found'}
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())


def start_simple_health_server(port: int = 8765, address: str = '0.0.0.0'):
    """Start simple health check server."""
    server = HTTPServer((address, port), SimpleHealthHandler)
    logger.info(f"Health server started on {address}:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Health server stopped")
    finally:
        server.shutdown()


def main():
    """Start observer in sidecar mode."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get configuration from environment
    api_port = int(os.getenv('CROSSBRIDGE_API_PORT', '8765'))
    api_host = os.getenv('CROSSBRIDGE_API_HOST', '0.0.0.0')
    mode = os.getenv('CROSSBRIDGE_MODE', 'observer')
    framework = os.getenv('CROSSBRIDGE_FRAMEWORK', 'robot')
    
    logger.info("=" * 60)
    logger.info("CrossBridge Observer - Sidecar Mode")
    logger.info("=" * 60)
    logger.info(f"Mode: {mode}")
    logger.info(f"Framework: {framework}")
    logger.info(f"API Host: {api_host}")
    logger.info(f"API Port: {api_port}")
    logger.info("=" * 60)
    
    # Start health server in a separate thread
    health_thread = threading.Thread(
        target=start_simple_health_server,
        args=(api_port, api_host),
        daemon=True,
        name="health-server"
    )
    health_thread.start()
    
    logger.info(f"✅ Health server started on {api_host}:{api_port}")
    logger.info(f"   Available endpoints:")
    logger.info(f"   - http://{api_host}:{api_port}/health - Health check")
    logger.info(f"   - http://{api_host}:{api_port}/stats - Real-time statistics")
    logger.info(f"   - http://{api_host}:{api_port}/summary - Comprehensive summary")
    logger.info(f"   - http://{api_host}:{api_port}/failures/patterns - Failure analysis")
    logger.info(f"   - http://{api_host}:{api_port}/events?status=FAIL - Query events")
    logger.info(f"   - http://{api_host}:{api_port}/metrics - Prometheus metrics")
    logger.info("")
    logger.info("🔍 Observer ready - waiting for test connections...")
    logger.info("")
    
    # Keep main thread alive
    try:
        health_thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")


if __name__ == '__main__':
    main()
