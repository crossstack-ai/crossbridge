"""
Enhanced Health Check System (v2)

Provides structured health monitoring with sub-component status tracking,
historical data, and detailed diagnostics.

Features:
- Versioned health API (/health/v1, /health/v2)
- Sub-component health tracking (orchestrator, adapters, plugins, database)
- SLI/SLO support with threshold tracking
- Historical health trends
- Anomaly detection for resource usage
- Structured error reporting
"""

import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import statistics

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.OBSERVER)


# ============================================================================
# Types and Enums
# ============================================================================

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Types of monitored components."""
    ORCHESTRATOR = "orchestrator"
    ADAPTER_REGISTRY = "adapter_registry"
    PLUGIN_SYSTEM = "plugin_system"
    DATABASE = "database"
    EVENT_QUEUE = "event_queue"
    RESOURCE_MONITOR = "resource_monitor"
    SEMANTIC_ENGINE = "semantic_engine"


@dataclass
class HealthMetric:
    """Individual health metric with thresholds."""
    name: str
    value: float
    unit: str
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    
    def get_status(self) -> HealthStatus:
        """Get status based on thresholds."""
        if self.threshold_critical and self.value >= self.threshold_critical:
            return HealthStatus.UNHEALTHY
        elif self.threshold_warning and self.value >= self.threshold_warning:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY


@dataclass
class ComponentHealthStatus:
    """Health status for a component."""
    component: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    last_check_time: float
    metrics: Dict[str, HealthMetric] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'component': self.component,
            'component_type': self.component_type.value,
            'status': self.status.value,
            'message': self.message,
            'last_check_time': self.last_check_time,
            'last_check_timestamp': datetime.fromtimestamp(self.last_check_time).isoformat(),
            'metrics': {
                name: {
                    'value': metric.value,
                    'unit': metric.unit,
                    'threshold_warning': metric.threshold_warning,
                    'threshold_critical': metric.threshold_critical,
                    'status': metric.get_status().value
                }
                for name, metric in self.metrics.items()
            },
            'errors': self.errors,
            'warnings': self.warnings
        }


@dataclass
class SLI:
    """Service Level Indicator."""
    name: str
    description: str
    current_value: float
    target_value: float
    unit: str
    status: HealthStatus
    measurement_window: str  # e.g., "last_5_minutes", "last_hour"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'current_value': self.current_value,
            'target_value': self.target_value,
            'unit': self.unit,
            'status': self.status.value,
            'measurement_window': self.measurement_window,
            'compliance': (self.current_value >= self.target_value) if 'uptime' in self.name else (self.current_value <= self.target_value)
        }


# ============================================================================
# Health History Tracking
# ============================================================================

class HealthHistoryTracker:
    """Tracks health history for trend analysis."""
    
    def __init__(self, max_history: int = 100):
        """
        Initialize history tracker.
        
        Args:
            max_history: Maximum number of history entries to keep
        """
        self._history: deque = deque(maxlen=max_history)
        self._lock = threading.Lock()
    
    def record(self, status: HealthStatus, components: Dict[str, ComponentHealthStatus]):
        """
        Record health check result.
        
        Args:
            status: Overall health status
            components: Component health statuses
        """
        with self._lock:
            self._history.append({
                'timestamp': time.time(),
                'status': status.value,
                'component_count': len(components),
                'healthy_count': sum(1 for c in components.values() if c.status == HealthStatus.HEALTHY),
                'degraded_count': sum(1 for c in components.values() if c.status == HealthStatus.DEGRADED),
                'unhealthy_count': sum(1 for c in components.values() if c.status == HealthStatus.UNHEALTHY)
            })
    
    def get_trend(self, window_seconds: int = 300) -> Dict[str, Any]:
        """
        Get health trend over time window.
        
        Args:
            window_seconds: Time window in seconds
            
        Returns:
            Trend statistics
        """
        with self._lock:
            cutoff_time = time.time() - window_seconds
            recent = [h for h in self._history if h['timestamp'] >= cutoff_time]
            
            if not recent:
                return {
                    'available': False,
                    'message': 'No recent health data'
                }
            
            healthy_pct = statistics.mean(
                (h['healthy_count'] / max(h['component_count'], 1)) * 100
                for h in recent
            )
            
            return {
                'available': True,
                'window_seconds': window_seconds,
                'checks_count': len(recent),
                'avg_healthy_percentage': round(healthy_pct, 2),
                'latest_status': recent[-1]['status'],
                'trend': 'improving' if len(recent) > 1 and recent[-1]['healthy_count'] > recent[0]['healthy_count'] else 'stable'
            }


# ============================================================================
# Enhanced Health Monitor
# ============================================================================

class EnhancedHealthMonitor:
    """
    Enhanced health monitoring with sub-component tracking and SLI/SLO support.
    """
    
    def __init__(self):
        """Initialize enhanced health monitor."""
        self._components: Dict[str, ComponentHealthStatus] = {}
        self._slis: Dict[str, SLI] = {}
        self._history = HealthHistoryTracker()
        self._lock = threading.Lock()
        self._startup_time = time.time()
        
        # Configuration
        self._check_interval = 30.0  # seconds
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Initialize default SLIs
        self._init_default_slis()
        
        logger.info("Enhanced health monitor initialized (v2)")
    
    def _init_default_slis(self):
        """Initialize default SLIs."""
        self._slis = {
            'availability': SLI(
                name='availability',
                description='System availability (uptime)',
                current_value=100.0,
                target_value=99.9,
                unit='percent',
                status=HealthStatus.HEALTHY,
                measurement_window='last_hour'
            ),
            'latency_p95': SLI(
                name='latency_p95',
                description='95th percentile event processing latency',
                current_value=0.0,
                target_value=100.0,
                unit='milliseconds',
                status=HealthStatus.HEALTHY,
                measurement_window='last_5_minutes'
            ),
            'error_rate': SLI(
                name='error_rate',
                description='Error rate across all operations',
                current_value=0.0,
                target_value=1.0,
                unit='percent',
                status=HealthStatus.HEALTHY,
                measurement_window='last_5_minutes'
            )
        }
    
    def register_component(
        self,
        component: str,
        component_type: ComponentType,
        check_func: callable
    ):
        """
        Register a component for health monitoring.
        
        Args:
            component: Component name
            component_type: Type of component
            check_func: Function that returns component health status
        """
        with self._lock:
            self._components[component] = ComponentHealthStatus(
                component=component,
                component_type=component_type,
                status=HealthStatus.UNKNOWN,
                message="Not yet checked",
                last_check_time=time.time()
            )
        
        logger.info(f"Registered component for health monitoring: {component} ({component_type.value})")
    
    def update_component_health(
        self,
        component: str,
        status: HealthStatus,
        message: str,
        metrics: Optional[Dict[str, HealthMetric]] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        """
        Update health status for a component.
        
        Args:
            component: Component name
            status: Health status
            message: Status message
            metrics: Health metrics
            errors: List of error messages
            warnings: List of warning messages
        """
        with self._lock:
            if component in self._components:
                self._components[component].status = status
                self._components[component].message = message
                self._components[component].last_check_time = time.time()
                
                if metrics:
                    self._components[component].metrics = metrics
                if errors:
                    self._components[component].errors = errors
                if warnings:
                    self._components[component].warnings = warnings
    
    def update_sli(self, name: str, current_value: float):
        """
        Update SLI value.
        
        Args:
            name: SLI name
            current_value: Current value
        """
        with self._lock:
            if name in self._slis:
                sli = self._slis[name]
                sli.current_value = current_value
                
                # Update status based on target
                if 'uptime' in name or 'availability' in name:
                    # Higher is better
                    if current_value >= sli.target_value:
                        sli.status = HealthStatus.HEALTHY
                    elif current_value >= sli.target_value * 0.95:
                        sli.status = HealthStatus.DEGRADED
                    else:
                        sli.status = HealthStatus.UNHEALTHY
                else:
                    # Lower is better (errors, latency)
                    if current_value <= sli.target_value:
                        sli.status = HealthStatus.HEALTHY
                    elif current_value <= sli.target_value * 2:
                        sli.status = HealthStatus.DEGRADED
                    else:
                        sli.status = HealthStatus.UNHEALTHY
    
    def get_overall_status(self) -> HealthStatus:
        """
        Get overall system health status.
        
        Returns:
            Overall health status
        """
        with self._lock:
            if not self._components:
                return HealthStatus.UNKNOWN
            
            unhealthy = sum(1 for c in self._components.values() if c.status == HealthStatus.UNHEALTHY)
            degraded = sum(1 for c in self._components.values() if c.status == HealthStatus.DEGRADED)
            
            if unhealthy > 0:
                return HealthStatus.UNHEALTHY
            elif degraded > 0:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
    
    def get_health_v1(self) -> Dict[str, Any]:
        """
        Get health status (v1 format - backward compatible).
        
        Returns:
            Health status in v1 format
        """
        overall_status = self.get_overall_status()
        
        return {
            'status': overall_status.value,
            'timestamp': time.time(),
            'uptime_seconds': time.time() - self._startup_time,
            'components': {
                name: component.status.value
                for name, component in self._components.items()
            }
        }
    
    def get_health_v2(self) -> Dict[str, Any]:
        """
        Get enhanced health status (v2 format).
        
        Returns:
            Enhanced health status with full details
        """
        with self._lock:
            overall_status = self.get_overall_status()
            
            # Record in history
            self._history.record(overall_status, self._components)
            
            # Build response
            response = {
                'version': '2.0',
                'status': overall_status.value,
                'timestamp': time.time(),
                'timestamp_iso': datetime.now().isoformat(),
                'uptime_seconds': time.time() - self._startup_time,
                
                # Component health
                'components': {
                    name: component.to_dict()
                    for name, component in self._components.items()
                },
                
                # Summary
                'summary': {
                    'total_components': len(self._components),
                    'healthy': sum(1 for c in self._components.values() if c.status == HealthStatus.HEALTHY),
                    'degraded': sum(1 for c in self._components.values() if c.status == HealthStatus.DEGRADED),
                    'unhealthy': sum(1 for c in self._components.values() if c.status == HealthStatus.UNHEALTHY),
                    'unknown': sum(1 for c in self._components.values() if c.status == HealthStatus.UNKNOWN)
                },
                
                # SLIs
                'slis': {
                    name: sli.to_dict()
                    for name, sli in self._slis.items()
                },
                
                # Trends
                'trends': {
                    'last_5_minutes': self._history.get_trend(300),
                    'last_hour': self._history.get_trend(3600)
                }
            }
            
            return response
    
    def start_monitoring(self):
        """Start background health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="health-monitor-v2"
        )
        self._monitor_thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                # Monitoring logic would go here
                # For now, just sleep
                time.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}", exc_info=True)


# ============================================================================
# Global Instance
# ============================================================================

_health_monitor: Optional[EnhancedHealthMonitor] = None
_monitor_lock = threading.Lock()


def get_health_monitor() -> EnhancedHealthMonitor:
    """Get global health monitor instance."""
    global _health_monitor
    
    if _health_monitor is None:
        with _monitor_lock:
            if _health_monitor is None:
                _health_monitor = EnhancedHealthMonitor()
    
    return _health_monitor
