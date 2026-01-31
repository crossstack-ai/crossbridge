"""
Enhanced HTTP Health Endpoints (v2)

Provides versioned health check endpoints with backward compatibility.

Endpoints:
- GET /health (v1 - backward compatible)
- GET /health/v1 (explicit v1)
- GET /health/v2 (enhanced with sub-components)
- GET /ready (readiness probe)
- GET /metrics (Prometheus metrics)
- GET /sli (Service Level Indicators)
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
import logging

from .health_v2 import get_health_monitor, HealthStatus, ComponentType

logger = logging.getLogger(__name__)


class EnhancedHealthHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for enhanced health endpoints."""
    
    def log_message(self, format, *args):
        """Override to use structured logging."""
        logger.debug(
            "health_http_request",
            extra={
                'method': self.command,
                'path': self.path,
                'client': self.client_address[0]
            }
        )
    
    def _send_json(
        self,
        data: Dict[str, Any],
        status_code: int = 200,
        headers: Dict[str, str] = None
    ):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-Content-Type-Options', 'nosniff')
        
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def _send_text(
        self,
        text: str,
        status_code: int = 200,
        content_type: str = 'text/plain'
    ):
        """Send text response."""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(text.encode())
    
    def _get_health_status_code(self, health_data: Dict[str, Any]) -> int:
        """
        Get HTTP status code based on health status.
        
        Args:
            health_data: Health status data
            
        Returns:
            HTTP status code
        """
        status = health_data.get('status', 'unknown')
        
        if status == 'healthy':
            return 200
        elif status == 'degraded':
            return 200  # Still operational
        elif status == 'unhealthy':
            return 503  # Service Unavailable
        else:
            return 500  # Internal Server Error
    
    def do_GET(self):
        """Handle GET requests."""
        monitor = get_health_monitor()
        
        # Health endpoints
        if self.path == '/health' or self.path == '/health/v1':
            # V1 format (backward compatible)
            health = monitor.get_health_v1()
            status_code = self._get_health_status_code(health)
            
            self._send_json(
                health,
                status_code=status_code,
                headers={'X-Health-Version': '1.0'}
            )
        
        elif self.path == '/health/v2':
            # V2 format (enhanced)
            health = monitor.get_health_v2()
            status_code = self._get_health_status_code(health)
            
            self._send_json(
                health,
                status_code=status_code,
                headers={'X-Health-Version': '2.0'}
            )
        
        # Readiness probe
        elif self.path == '/ready':
            # Check if system is ready to accept requests
            overall_status = monitor.get_overall_status()
            ready = overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            
            readiness = {
                'ready': ready,
                'status': overall_status.value,
                'timestamp': monitor.get_health_v1()['timestamp']
            }
            
            status_code = 200 if ready else 503
            self._send_json(readiness, status_code=status_code)
        
        # Liveness probe
        elif self.path == '/live':
            # Basic liveness check - is the process running?
            liveness = {
                'alive': True,
                'timestamp': monitor.get_health_v1()['timestamp']
            }
            self._send_json(liveness, status_code=200)
        
        # SLI endpoint
        elif self.path == '/sli':
            health_v2 = monitor.get_health_v2()
            slis = health_v2.get('slis', {})
            
            self._send_json({
                'slis': slis,
                'timestamp': health_v2['timestamp']
            })
        
        # Metrics endpoint (Prometheus format)
        elif self.path == '/metrics':
            metrics = self._generate_prometheus_metrics(monitor)
            self._send_text(
                metrics,
                content_type='text/plain; version=0.0.4; charset=utf-8'
            )
        
        # Component-specific health
        elif self.path.startswith('/health/component/'):
            component_name = self.path.split('/')[-1]
            health_v2 = monitor.get_health_v2()
            
            if component_name in health_v2['components']:
                component_health = health_v2['components'][component_name]
                status_code = 200 if component_health['status'] == 'healthy' else 503
                self._send_json(component_health, status_code=status_code)
            else:
                self._send_json(
                    {'error': f'Component not found: {component_name}'},
                    status_code=404
                )
        
        # Not found
        else:
            self._send_json(
                {
                    'error': 'Not found',
                    'available_endpoints': [
                        '/health (v1 - default)',
                        '/health/v1 (explicit v1)',
                        '/health/v2 (enhanced)',
                        '/ready (readiness probe)',
                        '/live (liveness probe)',
                        '/metrics (Prometheus)',
                        '/sli (Service Level Indicators)',
                        '/health/component/{name}'
                    ]
                },
                status_code=404
            )
    
    def _generate_prometheus_metrics(self, monitor) -> str:
        """
        Generate Prometheus metrics from health data.
        
        Args:
            monitor: Health monitor instance
            
        Returns:
            Prometheus-formatted metrics
        """
        lines = []
        health_v2 = monitor.get_health_v2()
        
        # Overall health status
        lines.append("# HELP crossbridge_health_status Overall health status (1=healthy, 0=not healthy)")
        lines.append("# TYPE crossbridge_health_status gauge")
        lines.append(f"crossbridge_health_status{{status=\"{health_v2['status']}\"}} "
                    f"{1 if health_v2['status'] == 'healthy' else 0}")
        
        # Uptime
        lines.append("# HELP crossbridge_uptime_seconds Uptime in seconds")
        lines.append("# TYPE crossbridge_uptime_seconds counter")
        lines.append(f"crossbridge_uptime_seconds {health_v2['uptime_seconds']}")
        
        # Component health
        lines.append("# HELP crossbridge_component_health_status Component health status")
        lines.append("# TYPE crossbridge_component_health_status gauge")
        for component_name, component in health_v2['components'].items():
            status_value = 1 if component['status'] == 'healthy' else 0
            lines.append(
                f"crossbridge_component_health_status{{"
                f"component=\"{component_name}\","
                f"component_type=\"{component['component_type']}\","
                f"status=\"{component['status']}\""
                f"}} {status_value}"
            )
        
        # Component metrics
        for component_name, component in health_v2['components'].items():
            for metric_name, metric in component['metrics'].items():
                safe_name = metric_name.replace('.', '_').replace('-', '_')
                prom_name = f"crossbridge_{component_name}_{safe_name}"
                
                lines.append(f"# HELP {prom_name} {component_name} {metric_name}")
                lines.append(f"# TYPE {prom_name} gauge")
                lines.append(f"{prom_name} {metric['value']}")
        
        # SLIs
        lines.append("# HELP crossbridge_sli Service Level Indicators")
        lines.append("# TYPE crossbridge_sli gauge")
        for sli_name, sli in health_v2['slis'].items():
            lines.append(
                f"crossbridge_sli_{sli_name} {sli['current_value']}"
            )
            lines.append(
                f"crossbridge_sli_{sli_name}_target {sli['target_value']}"
            )
        
        # Summary
        lines.append("# HELP crossbridge_components_total Total number of components")
        lines.append("# TYPE crossbridge_components_total gauge")
        lines.append(f"crossbridge_components_total {health_v2['summary']['total_components']}")
        
        lines.append("# HELP crossbridge_components_healthy Number of healthy components")
        lines.append("# TYPE crossbridge_components_healthy gauge")
        lines.append(f"crossbridge_components_healthy {health_v2['summary']['healthy']}")
        
        lines.append("# HELP crossbridge_components_degraded Number of degraded components")
        lines.append("# TYPE crossbridge_components_degraded gauge")
        lines.append(f"crossbridge_components_degraded {health_v2['summary']['degraded']}")
        
        lines.append("# HELP crossbridge_components_unhealthy Number of unhealthy components")
        lines.append("# TYPE crossbridge_components_unhealthy gauge")
        lines.append(f"crossbridge_components_unhealthy {health_v2['summary']['unhealthy']}")
        
        return '\n'.join(lines) + '\n'


def start_health_server(port: int = 9090, address: str = '0.0.0.0'):
    """
    Start enhanced health check server.
    
    Args:
        port: Port to listen on
        address: Address to bind to
    """
    server = HTTPServer((address, port), EnhancedHealthHTTPHandler)
    logger.info(f"Enhanced health server started on {address}:{port}")
    logger.info("Available endpoints: /health/v1, /health/v2, /ready, /live, /metrics, /sli")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Health server stopped")
    finally:
        server.shutdown()
