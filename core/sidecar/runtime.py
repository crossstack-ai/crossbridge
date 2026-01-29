"""
Sidecar Runtime - Main Entry Point

Provides a complete sidecar runtime that integrates:
- Observer
- Sampler
- Profiler
- Metrics Collector
- Health Monitor

Example usage:
    from core.sidecar import SidecarRuntime, SidecarConfig
    
    # Initialize with config
    config = SidecarConfig.from_file('crossbridge.yml')
    sidecar = SidecarRuntime(config)
    
    # Start sidecar
    sidecar.start()
    
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)
    
    # Observe events
    sidecar.observe('test_event', {'test_id': '123', 'status': 'passed'})
    
    # Get health status
    health = sidecar.get_health()
    
    # Get metrics (Prometheus format)
    metrics = sidecar.export_metrics()
    
    # Stop sidecar
    sidecar.stop()
"""

import logging
from typing import Dict, Optional, Any, Callable

from .config import SidecarConfig
from .sampler import Sampler, AdaptiveSampler
from .observer import SidecarObserver, Event
from .profiler import LightweightProfiler, DeepProfiler
from .metrics import MetricsCollector
from .health import SidecarHealth


logger = logging.getLogger(__name__)


class SidecarRuntime:
    """
    Complete sidecar runtime
    
    Integrates all sidecar components with fail-open design.
    """
    
    def __init__(self, config: Optional[SidecarConfig] = None, adaptive_sampling: bool = True):
        """
        Initialize sidecar runtime
        
        Args:
            config: Sidecar configuration (defaults to default config)
            adaptive_sampling: Use adaptive sampler (auto-boost on anomalies)
        """
        self.config = config or SidecarConfig()
        self.config.validate()
        
        # Initialize components
        self.metrics = MetricsCollector()
        
        # Sampler
        if adaptive_sampling:
            self.sampler = AdaptiveSampler(default_rate=self.config.sampling.events)
        else:
            self.sampler = Sampler(default_rate=self.config.sampling.events)
        
        # Configure sampling rates
        self.sampler.set_rate('events', self.config.sampling.events)
        self.sampler.set_rate('traces', self.config.sampling.traces)
        self.sampler.set_rate('profiling', self.config.sampling.profiling)
        self.sampler.set_rate('test_events', self.config.sampling.test_events)
        self.sampler.set_rate('perf_metrics', self.config.sampling.perf_metrics)
        self.sampler.set_rate('debug_logs', self.config.sampling.debug_logs)
        
        # Observer
        self.observer = SidecarObserver(
            sampler=self.sampler,
            metrics_collector=self.metrics,
            max_queue_size=self.config.resources.max_queue_size,
            drop_on_full=self.config.resources.drop_on_full
        )
        
        # Profiler
        if self.config.profiling.deep_profiling:
            self.profiler = DeepProfiler(
                duration_sec=self.config.profiling.deep_duration_sec,
                sampling_interval=self.config.profiling.sampling_interval
            )
        else:
            self.profiler = LightweightProfiler(
                sampling_interval=self.config.profiling.sampling_interval
            )
        
        # Health monitor
        self.health = SidecarHealth(
            observer=self.observer,
            profiler=self.profiler,
            metrics_collector=self.metrics
        )
        
        self._running = False
        
        logger.info("SidecarRuntime initialized", extra={
            'enabled': self.config.enabled,
            'adaptive_sampling': adaptive_sampling,
            'deep_profiling': self.config.profiling.deep_profiling
        })
    
    def start(self) -> None:
        """Start all sidecar components"""
        if not self.config.enabled:
            logger.info("Sidecar disabled, not starting")
            return
        
        if self._running:
            logger.warning("SidecarRuntime already running")
            return
        
        try:
            # Start observer
            self.observer.start()
            
            # Start profiler
            if self.config.profiling.enabled:
                self.profiler.start()
            
            # Start health monitoring
            if self.config.health_checks.enabled:
                self.health.start()
            
            self._running = True
            logger.info("SidecarRuntime started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start SidecarRuntime: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop all sidecar components"""
        if not self._running:
            return
        
        logger.info("Stopping SidecarRuntime...")
        
        try:
            # Stop health monitoring
            self.health.stop()
            
            # Stop profiler
            self.profiler.stop()
            
            # Stop observer
            self.observer.stop()
            
            self._running = False
            logger.info("SidecarRuntime stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during SidecarRuntime shutdown: {e}")
    
    def observe(
        self,
        event_type: str,
        data: Dict[str, Any],
        execution_id: Optional[str] = None,
        test_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> bool:
        """
        Observe an event (non-blocking, fail-open)
        
        Args:
            event_type: Type of event
            data: Event data
            execution_id: Execution context ID
            test_id: Test context ID
            run_id: Run context ID
            
        Returns:
            True if event was accepted, False if dropped
        """
        if not self.config.enabled or not self._running:
            return False
        
        return self.observer.observe_event(
            event_type=event_type,
            data=data,
            execution_id=execution_id,
            test_id=test_id,
            run_id=run_id
        )
    
    def register_handler(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Register a custom event handler"""
        self.observer.register_handler(event_type, handler)
    
    def get_health(self) -> Dict:
        """Get complete health status"""
        return self.health.status()
    
    def get_metrics(self) -> Dict:
        """Get all metrics"""
        metrics = self.metrics.get_metrics()
        
        # Add profiler metrics
        if self.config.profiling.enabled:
            summary = self.profiler.get_summary(window_seconds=60)
            metrics['sidecar_cpu_usage'] = {'type': 'gauge', 'value': summary['cpu_avg']}
            metrics['sidecar_memory_usage_mb'] = {'type': 'gauge', 'value': summary['memory_avg']}
            metrics['sidecar_thread_count'] = {'type': 'gauge', 'value': summary['thread_avg']}
        
        # Add observer metrics
        stats = self.observer.get_stats()
        metrics['sidecar_queue_size'] = {'type': 'gauge', 'value': stats['queue_size']}
        
        return metrics
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        # Update gauge values first
        if self.config.profiling.enabled:
            summary = self.profiler.get_summary(window_seconds=60)
            self.metrics.set_gauge('sidecar_cpu_usage', summary['cpu_avg'])
            self.metrics.set_gauge('sidecar_memory_usage_mb', summary['memory_avg'])
            self.metrics.set_gauge('sidecar_thread_count', summary['thread_avg'])
        
        stats = self.observer.get_stats()
        self.metrics.set_gauge('sidecar_queue_size', stats['queue_size'])
        
        return self.metrics.export_prometheus()
    
    def reload_config(self) -> bool:
        """Reload configuration from file"""
        if self.config.reload():
            logger.info("Configuration reloaded successfully")
            
            # Update sampler rates
            self.sampler.set_rate('events', self.config.sampling.events)
            self.sampler.set_rate('traces', self.config.sampling.traces)
            self.sampler.set_rate('profiling', self.config.sampling.profiling)
            self.sampler.set_rate('test_events', self.config.sampling.test_events)
            self.sampler.set_rate('perf_metrics', self.config.sampling.perf_metrics)
            self.sampler.set_rate('debug_logs', self.config.sampling.debug_logs)
            
            return True
        
        logger.warning("Configuration reload failed")
        return False
    
    def __enter__(self):
        """Context manager support"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.stop()
        return False
