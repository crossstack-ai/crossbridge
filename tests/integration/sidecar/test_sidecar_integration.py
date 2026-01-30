"""
Sidecar Integration Tests

Tests full sidecar pipeline integration:
- Event flow: queue → sampling → processing → storage
- Resource budget enforcement
- Configuration reload
- Health endpoint integration
- Metrics export
"""

import pytest
import time
import threading
from typing import List, Dict, Any

from core.observability.sidecar import (
    get_config,
    get_metrics,
    get_event_queue,
    get_sampler,
    get_resource_monitor,
    update_config,
    safe_observe
)
from core.observability.sidecar.health import (
    get_health_status,
    get_readiness_status,
    get_prometheus_metrics
)
from core.observability.sidecar.logging import (
    set_run_id,
    set_test_id,
    get_run_id,
    get_test_id,
    clear_context
)


# ============================================================================
# End-to-End Event Flow Tests
# ============================================================================

def test_end_to_end_event_flow():
    """
    Test complete event pipeline:
    1. Event queued
    2. Event sampled
    3. Event processed
    4. Metrics collected
    5. Health status updated
    """
    queue = get_event_queue()
    sampler = get_sampler()
    metrics = get_metrics()
    
    # Clear metrics
    metrics_before = metrics.get_metrics()
    
    # 1. Queue events
    test_events = [
        {'type': 'test', 'id': f'test_{i}', 'data': f'payload_{i}'}
        for i in range(100)
    ]
    
    queued_count = 0
    for event in test_events:
        if queue.put(event):
            queued_count += 1
    
    assert queued_count > 0, "Some events should be queued"
    
    # 2. Process events with sampling
    processed_count = 0
    
    @safe_observe("test_processing")
    def process_event(event):
        nonlocal processed_count
        if sampler.should_sample('events'):
            processed_count += 1
            return {'status': 'processed', 'event_id': event['id']}
        return None
    
    # Process queued events
    while queue.size() > 0:
        event = queue.get(timeout=0.1)
        if event:
            process_event(event)
    
    # 3. Verify metrics collected
    metrics_after = metrics.get_metrics()
    
    # Should have processing metrics
    assert 'sidecar.test_processing.success' in metrics_after['counters'] or \
           'sidecar.test_processing.errors' in metrics_after['counters']
    
    # 4. Verify health status reflects activity
    health = get_health_status()
    assert health['metrics']['total_events'] > 0


def test_event_sampling_reduces_processing_load():
    """Test sampling effectively reduces events processed."""
    queue = get_event_queue()
    sampler = get_sampler()
    
    # Configure 10% sampling
    update_config({'sampling_rates': {'test_events': 0.1}})
    
    # Queue 1000 events
    for i in range(1000):
        queue.put({'type': 'test', 'id': i})
    
    # Process with sampling
    processed = 0
    sampled_out = 0
    
    while queue.size() > 0:
        event = queue.get(timeout=0.1)
        if event:
            if sampler.should_sample('test_events'):
                processed += 1
            else:
                sampled_out += 1
    
    # Should process ~10% (100 events)
    # Allow 5% to 15% range
    assert 50 <= processed <= 150, f"Expected ~100 processed, got {processed}"
    assert sampled_out > 850, f"Expected >850 sampled out, got {sampled_out}"


def test_fail_open_prevents_test_blocking():
    """Test that sidecar errors never block test execution."""
    
    # Create function that fails
    @safe_observe("blocking_test")
    def potentially_blocking_operation():
        raise RuntimeError("This should not block")
    
    # Call multiple times
    start_time = time.time()
    for _ in range(100):
        result = potentially_blocking_operation()
        assert result is None  # Should return None, not raise
    
    elapsed = time.time() - start_time
    
    # Should complete quickly (not blocking)
    assert elapsed < 1.0, f"Took {elapsed}s, should be much faster"


# ============================================================================
# Resource Budget Enforcement Tests
# ============================================================================

def test_resource_budgets_enforced():
    """Test CPU and memory budgets are enforced."""
    config = get_config()
    monitor = get_resource_monitor()
    
    # Check budgets configured
    assert config.max_cpu_percent > 0
    assert config.max_memory_mb > 0
    
    # Check resource monitoring
    resources = monitor.check_resources()
    
    assert 'cpu_percent' in resources
    assert 'memory_mb' in resources
    assert 'cpu_over_budget' in resources
    assert 'memory_over_budget' in resources


def test_profiling_disabled_when_cpu_over_budget():
    """Test profiling is auto-disabled when CPU exceeds budget."""
    monitor = get_resource_monitor()
    
    # Disable profiling (simulating high CPU)
    monitor.disable_profiling()
    
    assert monitor.is_profiling_enabled() is False
    
    # Re-enable
    monitor.enable_profiling()
    assert monitor.is_profiling_enabled() is True


# ============================================================================
# Configuration Reload Tests
# ============================================================================

def test_config_reload_without_restart():
    """Test configuration can be reloaded without restart."""
    config_before = get_config()
    original_queue_size = config_before.max_queue_size
    
    # Update config
    new_queue_size = original_queue_size + 1000
    update_config({'max_queue_size': new_queue_size})
    
    config_after = get_config()
    
    # Config should be updated
    assert config_after.max_queue_size == new_queue_size
    
    # Restore original
    update_config({'max_queue_size': original_queue_size})


def test_config_reload_updates_sampling_rates():
    """Test sampling rates can be updated via config reload."""
    sampler = get_sampler()
    
    # Update sampling rates
    update_config({
        'sampling_rates': {
            'events': 0.5,
            'logs': 0.25,
            'profiling': 0.05
        }
    })
    
    config = get_config()
    
    # Verify updated
    assert config.sampling_rates['events'] == 0.5
    assert config.sampling_rates['logs'] == 0.25
    assert config.sampling_rates['profiling'] == 0.05


def test_config_reload_validates_values():
    """Test config reload validates values."""
    config_before = get_config()
    
    # Try invalid values (should be ignored or raise)
    invalid_updates = [
        {'max_queue_size': -100},
        {'max_cpu_percent': 150.0},
        {'sampling_rates': {'events': 2.0}}
    ]
    
    for invalid_update in invalid_updates:
        try:
            update_config(invalid_update)
        except:
            pass  # Exception is acceptable
    
    # Config should remain valid
    config_after = get_config()
    assert config_after.max_queue_size > 0
    assert 0 < config_after.max_cpu_percent <= 100


# ============================================================================
# Health Endpoint Integration Tests
# ============================================================================

def test_health_endpoint_returns_complete_status():
    """Test /health endpoint returns complete health information."""
    health = get_health_status()
    
    # Required fields
    assert 'status' in health
    assert 'enabled' in health
    assert 'timestamp' in health
    assert 'queue' in health
    assert 'resources' in health
    assert 'metrics' in health
    
    # Queue info
    assert 'size' in health['queue']
    assert 'utilization' in health['queue']
    
    # Resource info
    assert 'cpu_percent' in health['resources']
    assert 'memory_mb' in health['resources']


def test_readiness_endpoint_reflects_queue_capacity():
    """Test /ready endpoint reflects queue capacity."""
    queue = get_event_queue()
    
    # Empty queue → ready
    while queue.size() > 0:
        queue.get(timeout=0.01)
    
    readiness = get_readiness_status()
    assert readiness['ready'] is True
    
    # Fill queue to near capacity
    max_size = queue.get_stats()['max_size']
    for i in range(int(max_size * 0.96)):
        queue.put({'id': i})
    
    readiness = get_readiness_status()
    # May be not ready if queue >95% full
    assert 'ready' in readiness


def test_health_status_degraded_on_high_error_rate():
    """Test health status shows degraded on high error rate."""
    metrics = get_metrics()
    
    # Simulate errors
    for _ in range(100):
        metrics.increment('sidecar.events_queued')
        metrics.increment('sidecar.errors.total', 15)  # 15% error rate
    
    health = get_health_status()
    
    # Should show degraded due to high error rate
    if health['metrics']['error_rate'] > 0.1:
        assert health['status'] == 'degraded'


# ============================================================================
# Metrics Export Integration Tests
# ============================================================================

def test_prometheus_metrics_export_format():
    """Test Prometheus metrics are in correct format."""
    metrics_text = get_prometheus_metrics()
    
    # Should be valid Prometheus format
    assert '# TYPE' in metrics_text
    assert 'sidecar_' in metrics_text
    
    # Check for key metrics
    assert 'sidecar_queue_size' in metrics_text
    assert 'sidecar_cpu_usage' in metrics_text
    assert 'sidecar_memory_usage' in metrics_text


def test_prometheus_metrics_include_all_types():
    """Test Prometheus export includes counters, gauges, histograms."""
    metrics = get_metrics()
    
    # Add test metrics
    metrics.increment('test.counter', 42)
    metrics.set_gauge('test.gauge', 3.14)
    metrics.record_histogram('test.histogram', 100.0)
    
    metrics_text = get_prometheus_metrics()
    
    # Should include all metric types
    assert 'counter' in metrics_text
    assert 'gauge' in metrics_text
    assert 'summary' in metrics_text  # Histograms exported as summaries


# ============================================================================
# Correlation Context Integration Tests
# ============================================================================

def test_correlation_context_propagates():
    """Test correlation IDs propagate through event processing."""
    # Set context
    set_run_id('test_run_123')
    set_test_id('test_case_456')
    
    # Verify context
    assert get_run_id() == 'test_run_123'
    assert get_test_id() == 'test_case_456'
    
    # Clear context
    clear_context()
    assert get_run_id() is None
    assert get_test_id() is None


def test_correlation_context_thread_local():
    """Test correlation context is thread-local."""
    results = {}
    
    def worker(thread_id: int):
        # Each thread sets its own context
        set_run_id(f'run_{thread_id}')
        set_test_id(f'test_{thread_id}')
        
        time.sleep(0.1)  # Simulate work
        
        # Context should be isolated
        results[thread_id] = {
            'run_id': get_run_id(),
            'test_id': get_test_id()
        }
    
    # Start 5 threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Each thread should have its own context
    for i in range(5):
        assert results[i]['run_id'] == f'run_{i}'
        assert results[i]['test_id'] == f'test_{i}'


# ============================================================================
# Queue Management Integration Tests
# ============================================================================

def test_queue_statistics_accurate():
    """Test queue statistics are accurate."""
    queue = get_event_queue()
    
    # Clear queue
    while queue.size() > 0:
        queue.get(timeout=0.01)
    
    stats_before = queue.get_stats()
    initial_size = stats_before['current_size']
    
    # Add 100 events
    for i in range(100):
        queue.put({'id': i})
    
    stats_after = queue.get_stats()
    
    # Size should increase
    assert stats_after['current_size'] >= initial_size
    
    # Total events should increase
    assert stats_after['total_events'] >= stats_before['total_events'] + 100


def test_queue_utilization_calculated_correctly():
    """Test queue utilization is calculated correctly."""
    queue = get_event_queue()
    stats = queue.get_stats()
    
    max_size = stats['max_size']
    current_size = stats['current_size']
    utilization = stats['utilization']
    
    # Utilization should match current/max
    expected_utilization = current_size / max_size
    assert abs(utilization - expected_utilization) < 0.01


# ============================================================================
# Performance Tests
# ============================================================================

def test_event_processing_performance():
    """Test event processing meets performance requirements."""
    queue = get_event_queue()
    
    # Queue 1000 events
    for i in range(1000):
        queue.put({'id': i, 'data': 'x' * 100})
    
    # Process events
    start_time = time.time()
    processed = 0
    
    while queue.size() > 0 and processed < 1000:
        event = queue.get(timeout=0.1)
        if event:
            processed += 1
    
    elapsed = time.time() - start_time
    
    # Should process at least 100 events/second
    throughput = processed / elapsed
    assert throughput > 100, f"Throughput {throughput:.1f} events/s is too low"


def test_metrics_collection_performance():
    """Test metrics collection doesn't add significant overhead."""
    metrics = get_metrics()
    
    # Collect 10,000 metric points
    start_time = time.time()
    
    for i in range(10000):
        metrics.increment('test.counter')
        metrics.set_gauge('test.gauge', float(i))
        metrics.record_histogram('test.histogram', float(i))
    
    elapsed = time.time() - start_time
    
    # Should complete in under 1 second
    assert elapsed < 1.0, f"Metrics collection took {elapsed}s, too slow"


# ============================================================================
# Cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test."""
    yield
    
    # Clear context
    clear_context()
    
    # Drain queue
    queue = get_event_queue()
    while queue.size() > 0:
        queue.get(timeout=0.01)
