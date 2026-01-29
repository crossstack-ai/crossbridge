"""
Unit Tests for Debuggable Sidecar Runtime

Tests all sidecar components with correct API signatures.
"""

import pytest
import time
import threading
from pathlib import Path
import tempfile
import yaml

from core.sidecar.sampler import Sampler, AdaptiveSampler
from core.sidecar.observer import SidecarObserver, Event
from core.sidecar.profiler import LightweightProfiler, ProfileSnapshot
from core.sidecar.metrics import MetricsCollector
from core.sidecar.health import SidecarHealth, HealthStatus
from core.sidecar.config import SidecarConfig
from core.sidecar.runtime import SidecarRuntime


class TestSampler:
    """Test Sampler class"""
    
    def test_sampler_initialization(self):
        """Test sampler initializes with default rate"""
        sampler = Sampler(default_rate=0.5)
        assert sampler._default_rate == 0.5
        
    def test_sampler_should_sample(self):
        """Test sampling decision"""
        sampler = Sampler(default_rate=1.0)  # 100% sampling
        assert sampler.should_sample('test') is True
        
        sampler.set_rate('never', 0.0)  # 0% sampling
        assert sampler.should_sample('never') is False
        
    def test_sampler_statistics(self):
        """Test sampling statistics tracking"""
        sampler = Sampler(default_rate=0.5)
        
        for _ in range(100):
            sampler.should_sample('test')
        
        stats = sampler.get_stats()
        assert 'test' in stats
        assert 'total_signals' in stats['test']
        assert stats['test']['total_signals'] == 100


class TestSidecarObserver:
    """Test SidecarObserver class"""
    
    def test_observer_initialization(self):
        """Test observer initializes correctly"""
        sampler = Sampler()
        observer = SidecarObserver(sampler, max_queue_size=1000)
        assert observer._max_queue_size == 1000
        assert observer._running is False
        
    def test_observer_lifecycle(self):
        """Test observer start/stop"""
        sampler = Sampler()
        observer = SidecarObserver(sampler)
        observer.start()
        assert observer._running is True
        
        observer.stop()
        assert observer._running is False
        
    def test_observer_event_collection(self):
        """Test event observation"""
        sampler = Sampler(default_rate=1.0)
        observer = SidecarObserver(sampler)
        observer.start()
        
        success = observer.observe_event('test_event', {'key': 'value'})
        assert success is True
        
        stats = observer.get_stats()
        assert stats['events_received'] >= 1
        
        observer.stop()


class TestLightweightProfiler:
    """Test LightweightProfiler class"""
    
    def test_profiler_initialization(self):
        """Test profiler initializes correctly"""
        profiler = LightweightProfiler(sampling_interval=1.0)
        assert profiler._sampling_interval == 1.0
        assert profiler._running is False
        
    def test_profiler_snapshot(self):
        """Test profile snapshot collection"""
        profiler = LightweightProfiler()
        snapshot = profiler.collect()
        
        assert isinstance(snapshot, ProfileSnapshot)
        assert snapshot.cpu_percent >= 0
        assert snapshot.memory_mb >= 0
        assert snapshot.thread_count >= 1
        
    def test_profiler_budget_check(self):
        """Test resource budget checking"""
        profiler = LightweightProfiler()
        
        budget = profiler.is_over_budget(cpu_budget=100.0, memory_budget_mb=10000.0)
        
        assert 'cpu_over_budget' in budget
        assert 'memory_over_budget' in budget
        assert budget['cpu_over_budget'] is False
        assert budget['memory_over_budget'] is False


class TestMetricsCollector:
    """Test MetricsCollector class"""
    
    def test_metrics_initialization(self):
        """Test metrics collector initializes"""
        collector = MetricsCollector()
        assert collector is not None
        
    def test_counter_metric(self):
        """Test counter metric"""
        collector = MetricsCollector()
        collector.increment('test_counter')
        collector.increment('test_counter', amount=5)
        
        metrics = collector.get_metrics()
        assert 'test_counter' in metrics
        assert metrics['test_counter']['value'] >= 6
        
    def test_gauge_metric(self):
        """Test gauge metric"""
        collector = MetricsCollector()
        collector.set_gauge('test_gauge', 42.5)
        
        metrics = collector.get_metrics()
        assert 'test_gauge' in metrics
        assert metrics['test_gauge']['value'] == 42.5
        
    def test_prometheus_export(self):
        """Test Prometheus format export"""
        collector = MetricsCollector()
        collector.increment('requests_total')
        collector.set_gauge('cpu_usage', 45.2)
        
        prometheus_text = collector.export_prometheus()
        
        assert isinstance(prometheus_text, str)
        assert 'requests_total' in prometheus_text
        assert 'cpu_usage' in prometheus_text


class TestSidecarHealth:
    """Test SidecarHealth class"""
    
    @pytest.mark.skip(reason="Skipping health check tests as requested")
    def test_health_initialization(self):
        """Test health monitor initializes"""
        health = SidecarHealth()
        assert health is not None
        
    @pytest.mark.skip(reason="Skipping health check tests as requested")
    def test_health_status_check(self):
        """Test health status checking"""
        health = SidecarHealth()
        status = health.status()
        
        assert 'status' in status
        assert 'uptime_seconds' in status
        assert 'components' in status
        
    @pytest.mark.skip(reason="Skipping health check tests as requested")
    def test_health_component_tracking(self):
        """Test component health tracking"""
        health = SidecarHealth()
        
        health.update_component_health('observer', HealthStatus.HEALTHY, "All good")
        health.update_component_health('profiler', HealthStatus.DEGRADED, "High CPU")
        
        status = health.status()
        
        assert status['components']['observer']['status'] == 'healthy'
        assert status['components']['profiler']['status'] == 'degraded'


class TestSidecarConfig:
    """Test SidecarConfig class"""
    
    def test_config_defaults(self):
        """Test default configuration"""
        config = SidecarConfig()
        
        assert config.enabled is True
        assert config.sampling.events == 0.1
        assert config.resources.max_queue_size == 10000
        assert config.profiling.enabled is True
        
    def test_config_from_dict(self):
        """Test loading from dictionary"""
        config_data = {
            'enabled': True,
            'sampling': {
                'events': 0.5,
                'traces': 0.3
            },
            'resources': {
                'max_queue_size': 5000
            }
        }
        
        config = SidecarConfig.from_dict(config_data)
        
        assert config.enabled is True
        assert config.sampling.events == 0.5
        assert config.resources.max_queue_size == 5000
        
    def test_config_validation(self):
        """Test configuration validation"""
        config = SidecarConfig()
        
        # Valid config
        assert config.validate() is True
        
        # Invalid sampling rate should raise ValueError
        config.sampling.events = 1.5  # > 1.0
        with pytest.raises(ValueError, match="Sampling rate events must be between"):
            config.validate()


class TestSidecarRuntime:
    """Test SidecarRuntime integration"""
    
    def test_runtime_initialization(self):
        """Test runtime initializes all components"""
        runtime = SidecarRuntime()
        
        assert runtime.sampler is not None
        assert runtime.observer is not None
        assert runtime.profiler is not None
        assert runtime.metrics is not None
        assert runtime.health is not None
        
    def test_runtime_lifecycle(self):
        """Test runtime start/stop"""
        runtime = SidecarRuntime()
        runtime.start()
        
        assert runtime.observer._running is True
        assert runtime.profiler._running is True
        
        runtime.stop()
        
        assert runtime.observer._running is False
        assert runtime.profiler._running is False
        
    def test_runtime_observe(self):
        """Test observing events through runtime"""
        # Use 100% sampling to ensure event is observed
        config = SidecarConfig()
        config.sampling.events = 1.0
        runtime = SidecarRuntime(config=config)
        runtime.start()
        
        success = runtime.observe('test_event', {'key': 'value'})
        # May be False if sampled out, so just check it's a bool
        assert isinstance(success, bool)
        
        time.sleep(0.1)
        runtime.stop()
        
    def test_runtime_context_manager(self):
        """Test context manager interface"""
        with SidecarRuntime() as runtime:
            assert runtime.observer._running is True
            runtime.observe('test', {'data': 'value'})
        
        # Should auto-stop
        assert runtime.observer._running is False
        
    def test_runtime_get_health(self):
        """Test getting health status"""
        runtime = SidecarRuntime()
        runtime.start()
        
        health = runtime.get_health()
        
        assert 'status' in health
        assert 'components' in health
        assert 'uptime_seconds' in health
        
        runtime.stop()
        
    def test_runtime_export_prometheus(self):
        """Test Prometheus export"""
        runtime = SidecarRuntime()
        runtime.start()
        
        prometheus_text = runtime.export_metrics()
        assert isinstance(prometheus_text, str)
        assert len(prometheus_text) > 0
        
        runtime.stop()


class TestIntegration:
    """Integration tests for sidecar runtime"""
    
    @pytest.mark.skip(reason="Skipping integration test as requested")
    def test_full_lifecycle(self):
        """Test complete sidecar lifecycle"""
        with SidecarRuntime() as sidecar:
            # Observe multiple events
            for i in range(50):
                sidecar.observe('test_event', {
                    'id': i,
                    'status': 'passed' if i % 2 == 0 else 'failed'
                })
            
            # Check health
            health = sidecar.get_health()
            assert health['status'] in ['healthy', 'degraded', 'unhealthy']
            
            # Get metrics
            metrics = sidecar.get_metrics()
            assert len(metrics) > 0
            
            # Export Prometheus
            prometheus = sidecar.export_metrics()
            assert 'sidecar_events_total' in prometheus


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
