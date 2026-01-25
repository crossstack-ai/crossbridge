"""
Health Check System

Observable health monitoring for providers and services.

Features:
- Health check contracts for all external dependencies
- Centralized health registry
- Structured health status reporting
- Circuit breaker integration ready
- YAML configuration support

Usage:
    registry = HealthRegistry()
    registry.register("ai_provider", AIProviderHealthCheck(provider))
    
    health = registry.run_all()
    if not health['healthy']:
        logger.error(f"Unhealthy services: {health['failed']}")
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import time

from core.logging import get_logger, LogCategory
from .config import load_runtime_config

logger = get_logger(__name__, category=LogCategory.GENERAL)


class HealthStatus(str, Enum):
    """Health status enumeration."""
    
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthResult:
    """
    Result of a health check.
    
    Attributes:
        status: Health status
        timestamp: When check was performed
        duration_ms: Check duration in milliseconds
        message: Optional status message
        details: Additional diagnostic information
    """
    
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    message: Optional[str] = None
    details: Dict = field(default_factory=dict)
    
    @property
    def healthy(self) -> bool:
        """Check if status is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'duration_ms': round(self.duration_ms, 2),
            'message': self.message,
            'details': self.details,
            'healthy': self.healthy
        }


class HealthCheck(ABC):
    """
    Abstract base class for health checks.
    
    All health checks must implement the `check()` method.
    """
    
    @abstractmethod
    def check(self) -> HealthResult:
        """
        Perform health check.
        
        Returns:
            HealthResult with status and details
            
        Note:
            Should not raise exceptions - catch and return UNHEALTHY status
        """
        pass
    
    @property
    def name(self) -> str:
        """Get health check name (defaults to class name)."""
        return self.__class__.__name__
    
    def _measure_check(self, check_func: Callable) -> HealthResult:
        """
        Helper to measure check duration.
        
        Args:
            check_func: Function that performs the check
            
        Returns:
            HealthResult with measured duration
        """
        start_time = time.time()
        
        try:
            result = check_func()
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Health check '{self.name}' failed: {e}",
                exc_info=True
            )
            return HealthResult(
                status=HealthStatus.UNHEALTHY,
                duration_ms=duration_ms,
                message=f"Check failed: {type(e).__name__}: {e}",
                details={'exception': str(e)}
            )


class SimpleHealthCheck(HealthCheck):
    """
    Simple health check using a callable.
    
    Example:
        check = SimpleHealthCheck(
            name="database",
            check_func=lambda: db.ping()
        )
    """
    
    def __init__(self, name: str, check_func: Callable[[], bool]):
        """
        Initialize simple health check.
        
        Args:
            name: Check name
            check_func: Function that returns True if healthy
        """
        self._name = name
        self._check_func = check_func
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthResult:
        """Perform health check."""
        def _check():
            is_healthy = self._check_func()
            return HealthResult(
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message="OK" if is_healthy else "Check returned False"
            )
        
        return self._measure_check(_check)


class PingHealthCheck(HealthCheck):
    """
    Health check for services with a ping() method.
    
    Example:
        check = PingHealthCheck("vector_store", vector_store)
    """
    
    def __init__(self, name: str, service):
        """
        Initialize ping health check.
        
        Args:
            name: Check name
            service: Service with ping() method
        """
        self._name = name
        self.service = service
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthResult:
        """Perform ping health check."""
        def _check():
            self.service.ping()
            return HealthResult(
                status=HealthStatus.HEALTHY,
                message="Ping successful"
            )
        
        return self._measure_check(_check)


class AIProviderHealthCheck(HealthCheck):
    """
    Health check for AI/LLM providers.
    
    Performs a lightweight embedding test.
    """
    
    def __init__(self, name: str, provider):
        """
        Initialize AI provider health check.
        
        Args:
            name: Provider name
            provider: Provider with embed() method
        """
        self._name = name
        self.provider = provider
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthResult:
        """Perform AI provider health check."""
        def _check():
            # Lightweight test: embed single word
            result = self.provider.embed(["health_check"])
            
            if result and len(result) > 0:
                return HealthResult(
                    status=HealthStatus.HEALTHY,
                    message="Provider responding",
                    details={'embedding_dim': len(result[0]) if result[0] else 0}
                )
            else:
                return HealthResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Provider returned empty result"
                )
        
        return self._measure_check(_check)


class VectorStoreHealthCheck(HealthCheck):
    """
    Health check for vector stores.
    
    Checks connectivity and basic operations.
    """
    
    def __init__(self, name: str, store):
        """
        Initialize vector store health check.
        
        Args:
            name: Store name
            store: Store with ping() or similar method
        """
        self._name = name
        self.store = store
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthResult:
        """Perform vector store health check."""
        def _check():
            # Try to ping the store
            if hasattr(self.store, 'ping'):
                self.store.ping()
            elif hasattr(self.store, 'health_check'):
                self.store.health_check()
            else:
                # Fallback: try to get collection info
                if hasattr(self.store, 'get_collection'):
                    self.store.get_collection()
            
            return HealthResult(
                status=HealthStatus.HEALTHY,
                message="Store accessible"
            )
        
        return self._measure_check(_check)


class HealthRegistry:
    """
    Centralized registry for health checks.
    
    Features:
    - Register multiple health checks
    - Run all checks or specific checks
    - Aggregate health status
    - Track check history
    
    Usage:
        registry = HealthRegistry()
        registry.register("database", DatabaseHealthCheck())
        registry.register("cache", CacheHealthCheck())
        
        # Run all checks
        health = registry.run_all()
        print(health['overall_status'])  # "healthy" or "unhealthy"
    """
    
    def __init__(self):
        """Initialize health registry."""
        self.checks: Dict[str, HealthCheck] = {}
        self.last_results: Dict[str, HealthResult] = {}
    
    def register(self, name: str, check: HealthCheck):
        """
        Register a health check.
        
        Args:
            name: Unique check name
            check: HealthCheck instance
        """
        if name in self.checks:
            logger.warning(f"Overwriting existing health check: {name}")
        
        self.checks[name] = check
        logger.info(f"Registered health check: {name}")
    
    def unregister(self, name: str):
        """Remove a health check."""
        if name in self.checks:
            del self.checks[name]
            logger.info(f"Unregistered health check: {name}")
    
    def run(self, name: str) -> HealthResult:
        """
        Run a specific health check.
        
        Args:
            name: Check name
            
        Returns:
            HealthResult
            
        Raises:
            KeyError: If check not found
        """
        if name not in self.checks:
            raise KeyError(f"Health check not found: {name}")
        
        check = self.checks[name]
        result = check.check()
        
        self.last_results[name] = result
        
        logger.info(
            f"Health check '{name}': {result.status.value} "
            f"({result.duration_ms:.2f}ms)"
        )
        
        return result
    
    def run_all(self) -> dict:
        """
        Run all registered health checks.
        
        Returns:
            Dictionary with aggregated results:
            {
                'overall_status': 'healthy' | 'unhealthy' | 'degraded',
                'healthy': True | False,
                'total_checks': int,
                'passed': int,
                'failed': int,
                'timestamp': str,
                'checks': {
                    'check_name': {...result...}
                }
            }
        """
        results = {}
        passed = 0
        failed = 0
        
        for name in self.checks:
            try:
                result = self.run(name)
                results[name] = result.to_dict()
                
                if result.healthy:
                    passed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Failed to run health check '{name}': {e}")
                failed += 1
                results[name] = {
                    'status': HealthStatus.UNKNOWN.value,
                    'message': f"Check execution failed: {e}",
                    'healthy': False
                }
        
        total = passed + failed
        
        # Determine overall status
        if failed == 0:
            overall_status = HealthStatus.HEALTHY
        elif passed == 0:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return {
            'overall_status': overall_status.value,
            'healthy': failed == 0,
            'total_checks': total,
            'passed': passed,
            'failed': failed,
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }
    
    def get_status(self, name: str) -> Optional[HealthResult]:
        """Get last result for a specific check."""
        return self.last_results.get(name)
    
    def get_failed_checks(self) -> List[str]:
        """Get names of checks that failed."""
        return [
            name for name, result in self.last_results.items()
            if not result.healthy
        ]
    
    def is_healthy(self) -> bool:
        """Check if all registered checks are healthy."""
        if not self.checks:
            return True
        
        health = self.run_all()
        return health['healthy']
    
    def clear(self):
        """Clear all registered checks."""
        self.checks.clear()
        self.last_results.clear()


# Global health registry instance
_global_health_registry: Optional[HealthRegistry] = None


def get_health_registry() -> HealthRegistry:
    """Get or create global health registry."""
    global _global_health_registry
    
    if _global_health_registry is None:
        _global_health_registry = HealthRegistry()
    
    return _global_health_registry
