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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.OBSERVER)

# Global flag for graceful shutdown
running = True


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
        if self.path in ['/health', '/health/v1', '/ready', '/live']:
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
            
        elif self.path == '/metrics':
            # Return basic Prometheus metrics
            metrics = """# HELP crossbridge_up Service is up
# TYPE crossbridge_up gauge
crossbridge_up 1

# HELP crossbridge_mode Current operating mode
# TYPE crossbridge_mode gauge
crossbridge_mode{mode="observer"} 1
"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(metrics.encode())
            
        else:
            # Not found
            response = {
                'error': 'Not found',
                'available_endpoints': ['/health', '/health/v1', '/ready', '/live', '/metrics', '/events']
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
                
                # Log the event with appropriate details
                event_type = event.get('event_type')
                data = event.get('data', {})
                
                if 'test_name' in data:
                    detail = f"{data['test_name']} [{data.get('status', 'running')}]"
                elif 'suite_name' in data:
                    detail = f"{data['suite_name']}"
                else:
                    detail = 'event'
                
                logger.info(f"📨 {event_type}: {detail}")
                
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
    logger.info(f"   - http://{api_host}:{api_port}/health")
    logger.info(f"   - http://{api_host}:{api_port}/ready")
    logger.info(f"   - http://{api_host}:{api_port}/live")
    logger.info(f"   - http://{api_host}:{api_port}/metrics")
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
