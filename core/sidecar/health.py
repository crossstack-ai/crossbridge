"""
Health Monitoring for Sidecar Runtime

Provides:
- Health status checks
- Component health tracking
- HTTP health endpoint compatible
"""

import time
import threading
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a component"""
    name: str
    status: HealthStatus
    message: str = ""
    last_check: float = field(default_factory=time.time)
    metrics: Dict = field(default_factory=dict)


class SidecarHealth:
    """
    Health monitoring for sidecar runtime
    
    Tracks health of all components and provides status endpoint.
    """
    
    def __init__(self, observer=None, profiler=None, metrics_collector=None):
        """
        Initialize health monitor
        
        Args:
            observer: SidecarObserver instance
            profiler: LightweightProfiler instance
            metrics_collector: MetricsCollector instance
        """
        self._observer = observer
        self._profiler = profiler
        self._metrics_collector = metrics_collector
        
        self._start_time = time.time()
        self._component_health: Dict[str, ComponentHealth] = {}
        self._lock = threading.Lock()
        
        # Health check configuration
        self._check_interval = 30.0  # seconds
        self._failure_threshold = 3
        self._consecutive_failures: Dict[str, int] = {}
        
        # Background health checking
        self._running = False
        self._health_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start background health checking"""
        if self._running:
            return
        
        self._running = True
        self._health_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="sidecar-health"
        )
        self._health_thread.start()
    
    def stop(self) -> None:
        """Stop background health checking"""
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=2.0)
    
    def _health_check_loop(self) -> None:
        """Background health checking loop"""
        while self._running:
            try:
                self.check_all()
                time.sleep(self._check_interval)
            except Exception:
                pass  # Never crash health thread
    
    def check_all(self) -> None:
        """Check health of all components"""
        # Check observer
        if self._observer:
            self._check_observer()
        
        # Check profiler
        if self._profiler:
            self._check_profiler()
        
        # Check metrics collector
        if self._metrics_collector:
            self._check_metrics_collector()
    
    def _check_observer(self) -> None:
        """Check observer health"""
        try:
            stats = self._observer.get_stats()
            
            # Determine health based on stats
            drop_rate = stats['events_dropped'] / max(stats['events_received'], 1)
            error_rate = stats['errors'] / max(stats['events_processed'], 1)
            queue_util = stats['queue_utilization']
            
            if error_rate > 0.1 or drop_rate > 0.5:
                status = HealthStatus.UNHEALTHY
                message = f"High error rate: {error_rate:.1%}, drop rate: {drop_rate:.1%}"
            elif drop_rate > 0.2 or queue_util > 0.8:
                status = HealthStatus.DEGRADED
                message = f"Elevated drop rate: {drop_rate:.1%}, queue: {queue_util:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = "Operating normally"
            
            self._update_component_health(
                'observer',
                status,
                message,
                metrics={
                    'events_received': stats['events_received'],
                    'events_dropped': stats['events_dropped'],
                    'drop_rate': drop_rate,
                    'error_rate': error_rate,
                    'queue_utilization': queue_util,
                }
            )
            
        except Exception as e:
            self._update_component_health(
                'observer',
                HealthStatus.UNKNOWN,
                f"Health check failed: {str(e)}"
            )
    
    def _check_profiler(self) -> None:
        """Check profiler health"""
        try:
            budget = self._profiler.is_over_budget()
            
            if budget['cpu_over_budget'] or budget['memory_over_budget']:
                status = HealthStatus.DEGRADED
                message = f"Resource budget exceeded (CPU: {budget['cpu_value']:.1f}%, Memory: {budget['memory_value']:.1f}MB)"
            else:
                status = HealthStatus.HEALTHY
                message = "Within budget"
            
            self._update_component_health(
                'profiler',
                status,
                message,
                metrics={
                    'cpu_percent': budget['cpu_value'],
                    'memory_mb': budget['memory_value'],
                    'cpu_budget': budget['cpu_budget'],
                    'memory_budget': budget['memory_budget'],
                }
            )
            
        except Exception as e:
            self._update_component_health(
                'profiler',
                HealthStatus.UNKNOWN,
                f"Health check failed: {str(e)}"
            )
    
    def _check_metrics_collector(self) -> None:
        """Check metrics collector health"""
        try:
            metrics = self._metrics_collector.get_metrics()
            
            # Metrics collector is healthy if it has metrics
            if metrics:
                status = HealthStatus.HEALTHY
                message = f"{len(metrics)} metrics registered"
            else:
                status = HealthStatus.DEGRADED
                message = "No metrics registered"
            
            self._update_component_health(
                'metrics_collector',
                status,
                message,
                metrics={'metric_count': len(metrics)}
            )
            
        except Exception as e:
            self._update_component_health(
                'metrics_collector',
                HealthStatus.UNKNOWN,
                f"Health check failed: {str(e)}"
            )
    
    def _update_component_health(
        self,
        name: str,
        status: HealthStatus,
        message: str,
        metrics: Optional[Dict] = None
    ) -> None:
        """Update health status for a component"""
        with self._lock:
            self._component_health[name] = ComponentHealth(
                name=name,
                status=status,
                message=message,
                metrics=metrics or {}
            )
            
            # Track consecutive failures
            if status == HealthStatus.UNHEALTHY:
                self._consecutive_failures[name] = self._consecutive_failures.get(name, 0) + 1
            else:
                self._consecutive_failures[name] = 0
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        with self._lock:
            if not self._component_health:
                return HealthStatus.UNKNOWN
            
            statuses = [c.status for c in self._component_health.values()]
            
            # Overall status is worst component status
            if HealthStatus.UNHEALTHY in statuses:
                return HealthStatus.UNHEALTHY
            elif HealthStatus.DEGRADED in statuses:
                return HealthStatus.DEGRADED
            elif HealthStatus.UNKNOWN in statuses:
                return HealthStatus.UNKNOWN
            else:
                return HealthStatus.HEALTHY
    
    def status(self) -> Dict:
        """
        Get full health status report
        
        Returns:
            Dictionary with health information
        """
        with self._lock:
            uptime = time.time() - self._start_time
            
            return {
                'status': self.get_overall_status().value,
                'uptime_seconds': uptime,
                'uptime_human': self._format_uptime(uptime),
                'timestamp': time.time(),
                'components': {
                    name: {
                        'status': health.status.value,
                        'message': health.message,
                        'last_check': health.last_check,
                        'metrics': health.metrics,
                    }
                    for name, health in self._component_health.items()
                },
                'consecutive_failures': dict(self._consecutive_failures),
            }
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        return self.get_overall_status() == HealthStatus.HEALTHY
    
    def is_degraded(self) -> bool:
        """Check if system is degraded"""
        return self.get_overall_status() == HealthStatus.DEGRADED
    
    def is_unhealthy(self) -> bool:
        """Check if system is unhealthy"""
        return self.get_overall_status() == HealthStatus.UNHEALTHY
    
    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
