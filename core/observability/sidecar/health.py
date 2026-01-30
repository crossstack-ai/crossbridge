"""
Sidecar Health and Metrics Endpoints

Provides HTTP endpoints for health checks, readiness probes, and Prometheus metrics.

Endpoints:
- GET /health - Health check
- GET /ready - Readiness probe
- GET /metrics - Prometheus metrics
- POST /sidecar/config/reload - Reload configuration
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
import threading
import logging

from . import (
    get_config,
    get_metrics,
    get_event_queue,
    get_sampler,
    get_resource_monitor,
    update_config
)

logger = logging.getLogger(__name__)


# ============================================================================
# Health Status
# ============================================================================

def get_health_status() -> Dict[str, Any]:
    """
    Get current health status.
    
    Returns:
        Health status dictionary
    """
    config = get_config()
    queue_stats = get_event_queue().get_stats()
    resource_stats = get_resource_monitor().check_resources()
    metrics = get_metrics().get_metrics()
    
    # Determine overall status
    status = "ok"
    issues = []
    
    # Check queue utilization
    if queue_stats['utilization'] > 0.9:
        status = "degraded"
        issues.append("queue_near_capacity")
    
    # Check resource usage
    if resource_stats.get('cpu_over_budget', False):
        status = "degraded"
        issues.append("cpu_over_budget")
    
    if resource_stats.get('memory_over_budget', False):
        status = "degraded"
        issues.append("memory_over_budget")
    
    # Check error rate
    total_events = metrics['counters'].get('sidecar.events_queued', 0)
    total_errors = metrics['counters'].get('sidecar.errors.total', 0)
    error_rate = total_errors / max(total_events, 1)
    
    if error_rate > 0.1:  # >10% error rate
        status = "degraded"
        issues.append("high_error_rate")
    
    return {
        'status': status,
        'enabled': config.enabled,
        'issues': issues,
        'timestamp': time.time(),
        'queue': {
            'size': queue_stats['current_size'],
            'max_size': queue_stats['max_size'],
            'utilization': queue_stats['utilization'],
            'dropped_events': queue_stats['dropped_events']
        },
        'resources': {
            'cpu_percent': resource_stats.get('cpu_percent', 0),
            'memory_mb': resource_stats.get('memory_mb', 0),
            'profiling_enabled': resource_stats.get('profiling_enabled', True)
        },
        'metrics': {
            'total_events': total_events,
            'total_errors': total_errors,
            'error_rate': error_rate,
            'avg_latency_ms': metrics['histograms'].get(
                'sidecar.event_processing.duration_ms', {}
            ).get('avg', 0)
        }
    }


def get_readiness_status() -> Dict[str, Any]:
    """
    Get readiness status (for Kubernetes readiness probes).
    
    Returns:
        Readiness status dictionary
    """
    config = get_config()
    queue_stats = get_event_queue().get_stats()
    
    # Ready if enabled and queue not full
    ready = config.enabled and queue_stats['utilization'] < 0.95
    
    return {
        'ready': ready,
        'enabled': config.enabled,
        'queue_utilization': queue_stats['utilization'],
        'timestamp': time.time()
    }


# ============================================================================
# Prometheus Metrics
# ============================================================================

def get_prometheus_metrics() -> str:
    """
    Get metrics in Prometheus format.
    
    Returns:
        Prometheus-formatted metrics string
    """
    metrics = get_metrics().get_metrics()
    queue_stats = get_event_queue().get_stats()
    resource_stats = get_resource_monitor().check_resources()
    sampling_stats = get_sampler().get_stats()
    
    lines = []
    
    # Counter metrics
    for name, value in metrics['counters'].items():
        prom_name = name.replace('.', '_')
        lines.append(f"# TYPE {prom_name} counter")
        lines.append(f"{prom_name} {value}")
    
    # Gauge metrics
    for name, value in metrics['gauges'].items():
        prom_name = name.replace('.', '_')
        lines.append(f"# TYPE {prom_name} gauge")
        lines.append(f"{prom_name} {value}")
    
    # Queue metrics
    lines.append("# TYPE sidecar_queue_size gauge")
    lines.append(f"sidecar_queue_size {queue_stats['current_size']}")
    
    lines.append("# TYPE sidecar_queue_utilization gauge")
    lines.append(f"sidecar_queue_utilization {queue_stats['utilization']}")
    
    lines.append("# TYPE sidecar_events_dropped_total counter")
    lines.append(f"sidecar_events_dropped_total {queue_stats['dropped_events']}")
    
    # Resource metrics
    lines.append("# TYPE sidecar_cpu_usage gauge")
    lines.append(f"sidecar_cpu_usage {resource_stats.get('cpu_percent', 0)}")
    
    lines.append("# TYPE sidecar_memory_usage gauge")
    lines.append(f"sidecar_memory_usage {resource_stats.get('memory_mb', 0)}")
    
    # Histogram metrics (summary)
    for name, stats in metrics['histograms'].items():
        prom_name = name.replace('.', '_')
        lines.append(f"# TYPE {prom_name} summary")
        lines.append(f"{prom_name}_count {stats['count']}")
        lines.append(f"{prom_name}_sum {stats['avg'] * stats['count']}")
        lines.append(f"{prom_name}_avg {stats['avg']}")
    
    # Sampling metrics
    for event_type, stats in sampling_stats.items():
        lines.append(f"# TYPE sidecar_sampling_{event_type}_rate gauge")
        lines.append(f"sidecar_sampling_{event_type}_rate {stats['actual_rate']}")
    
    return '\n'.join(lines) + '\n'


# ============================================================================
# HTTP Request Handler
# ============================================================================

class SidecarHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for sidecar endpoints."""
    
    def log_message(self, format, *args):
        """Override to use structured logging."""
        logger.debug(
            "sidecar_http_request",
            extra={
                'method': self.command,
                'path': self.path,
                'client': self.client_address[0]
            }
        )
    
    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def _send_text(self, text: str, status_code: int = 200, content_type: str = 'text/plain'):
        """Send text response."""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(text.encode())
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            health = get_health_status()
            status_code = 200 if health['status'] == 'ok' else 503
            self._send_json(health, status_code)
        
        elif self.path == '/ready':
            readiness = get_readiness_status()
            status_code = 200 if readiness['ready'] else 503
            self._send_json(readiness, status_code)
        
        elif self.path == '/metrics':
            metrics = get_prometheus_metrics()
            self._send_text(metrics, content_type='text/plain; version=0.0.4')
        
        else:
            self._send_json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/sidecar/config/reload':
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            
            try:
                new_config = json.loads(body)
                update_config(new_config)
                self._send_json({
                    'status': 'ok',
                    'message': 'Configuration reloaded',
                    'config': new_config
                })
            except Exception as e:
                self._send_json({
                    'error': str(e)
                }, 400)
        
        else:
            self._send_json({'error': 'Not found'}, 404)


# ============================================================================
# Server Management
# ============================================================================

class SidecarHTTPServer:
    """HTTP server for sidecar endpoints."""
    
    def __init__(self, port: int = 9090):
        """
        Initialize HTTP server.
        
        Args:
            port: Port to listen on
        """
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """Start HTTP server in background thread."""
        if self.server:
            logger.warning("Server already running")
            return
        
        try:
            self.server = HTTPServer(('', self.port), SidecarHTTPHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            logger.info(
                "sidecar_http_server_started",
                extra={'port': self.port}
            )
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
    
    def stop(self):
        """Stop HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.thread = None
            
            logger.info("sidecar_http_server_stopped")


# ============================================================================
# Global Server Instance
# ============================================================================

_http_server = None


def start_http_server(port: int = 9090):
    """
    Start HTTP server for health and metrics endpoints.
    
    Args:
        port: Port to listen on
    """
    global _http_server
    
    if _http_server is None:
        _http_server = SidecarHTTPServer(port)
        _http_server.start()


def stop_http_server():
    """Stop HTTP server."""
    global _http_server
    
    if _http_server:
        _http_server.stop()
        _http_server = None
