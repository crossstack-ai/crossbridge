"""
Health Monitoring for Sidecar Observer

Provides health check endpoints compatible with Kubernetes/Docker.
Includes liveness and readiness probes.
"""

from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.OBSERVER)


class HealthStatus(Enum):
    """Health status levels."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Individual health check definition."""
    
    name: str
    check_func: Callable[[], Dict[str, Any]]
    critical: bool = True  # If True, failure = unhealthy
    timeout_seconds: float = 5.0


class HealthMonitor:
    """
    Health monitoring for sidecar observer.
    
    Provides Kubernetes-compatible liveness/readiness probes.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self._checks: Dict[str, HealthCheck] = {}
        self._last_check_time: Optional[datetime] = None
        self._last_check_results: Dict[str, Any] = {}
        
        # Startup tracking
        self._startup_time = datetime.now()
        self._ready = False
        
        logger.info("Health monitor initialized")
    
    def register_check(
        self,
        name: str,
        check_func: Callable[[], Dict[str, Any]],
        critical: bool = True,
        timeout_seconds: float = 5.0
    ):
        """
        Register a health check.
        
        Args:
            name: Name of health check
            check_func: Function that returns health status dict
            critical: Whether check failure = unhealthy
            timeout_seconds: Timeout for check execution
        """
        self._checks[name] = HealthCheck(
            name=name,
            check_func=check_func,
            critical=critical,
            timeout_seconds=timeout_seconds
        )
        
        logger.info(f"Registered health check: {name}", extra={"critical": critical})
    
    def run_checks(self) -> Dict[str, Any]:
        """
        Run all registered health checks.
        
        Returns:
            Health status with all check results
        """
        self._last_check_time = datetime.now()
        check_results = {}
        critical_failures = []
        warnings = []
        
        for name, check in self._checks.items():
            try:
                result = check.check_func()
                check_results[name] = result
                
                # Check for failures
                if not result.get("healthy", False):
                    if check.critical:
                        critical_failures.append(name)
                    else:
                        warnings.append(name)
            
            except Exception as e:
                logger.error(
                    f"Health check failed: {name}",
                    extra={"error": str(e)},
                    exc_info=True
                )
                
                check_results[name] = {
                    "healthy": False,
                    "error": str(e)
                }
                
                if check.critical:
                    critical_failures.append(name)
        
        # Determine overall status
        if critical_failures:
            overall_status = HealthStatus.UNHEALTHY
        elif warnings:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        self._last_check_results = {
            "status": overall_status.value,
            "timestamp": self._last_check_time.isoformat(),
            "uptime_seconds": (datetime.now() - self._startup_time).total_seconds(),
            "checks": check_results
        }
        
        if critical_failures:
            self._last_check_results["critical_failures"] = critical_failures
        if warnings:
            self._last_check_results["warnings"] = warnings
        
        return self._last_check_results
    
    def liveness_probe(self) -> Dict[str, Any]:
        """
        Kubernetes liveness probe.
        
        Returns basic "am I alive" status.
        Used to determine if pod should be restarted.
        
        Returns:
            Liveness status
        """
        uptime = (datetime.now() - self._startup_time).total_seconds()
        
        # Basic liveness: we're alive if we can respond
        return {
            "status": "alive",
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat()
        }
    
    def readiness_probe(self) -> Dict[str, Any]:
        """
        Kubernetes readiness probe.
        
        Returns "am I ready to handle requests" status.
        Used to determine if pod should receive traffic.
        
        Returns:
            Readiness status
        """
        # Run health checks if not run recently
        if (
            not self._last_check_time or
            datetime.now() - self._last_check_time > timedelta(seconds=30)
        ):
            self.run_checks()
        
        is_ready = (
            self._ready and
            self._last_check_results.get("status") != HealthStatus.UNHEALTHY.value
        )
        
        return {
            "ready": is_ready,
            "status": self._last_check_results.get("status", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "last_check": self._last_check_time.isoformat() if self._last_check_time else None
        }
    
    def startup_probe(self) -> Dict[str, Any]:
        """
        Kubernetes startup probe.
        
        Returns "have I finished starting up" status.
        Used for slow-starting applications.
        
        Returns:
            Startup status
        """
        uptime = (datetime.now() - self._startup_time).total_seconds()
        
        return {
            "started": self._ready,
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat()
        }
    
    def mark_ready(self):
        """Mark observer as ready to handle requests."""
        self._ready = True
        logger.info("Observer marked as ready")
    
    def mark_not_ready(self):
        """Mark observer as not ready."""
        self._ready = False
        logger.warning("Observer marked as not ready")
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed health status with all information.
        
        Returns:
            Comprehensive health status
        """
        # Run fresh checks
        check_results = self.run_checks()
        
        uptime = (datetime.now() - self._startup_time).total_seconds()
        
        return {
            "overall": check_results,
            "liveness": self.liveness_probe(),
            "readiness": self.readiness_probe(),
            "startup": self.startup_probe(),
            "uptime_seconds": uptime,
            "ready": self._ready
        }


def setup_default_health_checks(monitor: HealthMonitor):
    """
    Set up default health checks for observer.
    
    Args:
        monitor: HealthMonitor instance
    """
    # Import here to avoid circular dependencies
    from core.observability.circuit_breaker import circuit_breaker_registry
    from core.observability.performance_monitor import performance_monitor
    from core.observability.failure_isolation import failure_handler
    from core.observability.async_processor import async_processor
    
    # Circuit breaker health
    def check_circuit_breakers():
        """Check if any circuit breakers are open."""
        registry = circuit_breaker_registry
        breakers = registry.get_all_breakers()
        
        open_breakers = [
            name for name, breaker in breakers.items()
            if breaker.state.value == "OPEN"
        ]
        
        return {
            "healthy": len(open_breakers) == 0,
            "total_breakers": len(breakers),
            "open_breakers": open_breakers
        }
    
    # Performance health
    def check_performance():
        """Check if performance is within acceptable range."""
        status = performance_monitor.get_health_status()
        return {
            "healthy": status["healthy"],
            "tests_observed": status["tests_observed"],
            "threshold_violations": status["threshold_violations"]
        }
    
    # Failure isolation health
    def check_failure_rate():
        """Check if failure rate is acceptable."""
        status = failure_handler.get_health_status()
        return {
            "healthy": status["healthy"],
            "failures_last_minute": status["failures_last_minute"]
        }
    
    # Async processor health
    def check_async_processor():
        """Check if async processor is healthy."""
        status = async_processor.get_health_status()
        return {
            "healthy": status["healthy"],
            "queue_utilization": status["queue_utilization"],
            "events_processed": status["events_processed"]
        }
    
    # Register all checks
    monitor.register_check("circuit_breakers", check_circuit_breakers, critical=False)
    monitor.register_check("performance", check_performance, critical=False)
    monitor.register_check("failure_rate", check_failure_rate, critical=True)
    monitor.register_check("async_processor", check_async_processor, critical=True)
    
    logger.info("Default health checks registered")


# Global health monitor
health_monitor = HealthMonitor()
