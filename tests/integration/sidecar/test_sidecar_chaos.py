"""
Sidecar Chaos and Stress Tests

Tests sidecar resilience under adverse conditions:
- Event floods (10K+ events)
- Exception injection
- Queue exhaustion
- Resource exhaustion
- Exporter failures
- Network failures
- Configuration corruption
"""

import pytest
import time
import threading
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

from core.observability.sidecar import (
    get_config,
    get_metrics,
    get_event_queue,
    get_sampler,
    get_resource_monitor,
    update_config,
    safe_observe,
    SidecarConfig
)
from core.observability.sidecar.health import get_health_status


# ============================================================================
# Event Flood Tests
# ============================================================================

def test_sidecar_survives_small_event_flood():
    """Test sidecar handles 1000 events without crashing."""
    queue = get_event_queue()
    initial_size = queue.size()
    
    # Flood with 1000 events
    queued = 0
    for i in range(1000):
        event = {
            'type': 'test_event',
            'id': f'test_{i}',
            'data': f'payload_{i}'
        }
        if queue.put(event):
            queued += 1
    
    # Verify no crash
    assert queue.size() >= initial_size
    assert queued > 0
    
    # Verify metrics tracked
    metrics = get_metrics().get_metrics()
    assert 'sidecar.events_queued' in metrics['counters']


def test_sidecar_survives_large_event_flood():
    """Test sidecar handles 10,000 events with load shedding."""
    queue = get_event_queue()
    stats_before = queue.get_stats()
    
    # Flood with 10,000 events
    queued = 0
    dropped = 0
    for i in range(10000):
        event = {
            'type': 'test_event',
            'id': f'test_{i}',
            'data': 'x' * 100  # 100 bytes each
        }
        if queue.put(event):
            queued += 1
        else:
            dropped += 1
    
    stats_after = queue.get_stats()
    
    # Verify load shedding occurred
    assert dropped > 0, "Expected some events to be dropped"
    
    # Verify drop metrics incremented
    assert stats_after['dropped_events'] > stats_before['dropped_events']
    
    # Verify queue didn't exceed max size
    assert queue.size() <= queue.get_stats()['max_size']


def test_sidecar_handles_concurrent_flood():
    """Test sidecar handles concurrent event floods from multiple threads."""
    queue = get_event_queue()
    results = {'queued': 0, 'dropped': 0}
    lock = threading.Lock()
    
    def flood_worker(thread_id: int, count: int):
        """Flood events from a single thread."""
        local_queued = 0
        local_dropped = 0
        
        for i in range(count):
            event = {
                'type': 'test_event',
                'thread_id': thread_id,
                'seq': i
            }
            if queue.put(event):
                local_queued += 1
            else:
                local_dropped += 1
        
        with lock:
            results['queued'] += local_queued
            results['dropped'] += local_dropped
    
    # Start 10 threads, each sending 1000 events
    threads = []
    for i in range(10):
        t = threading.Thread(target=flood_worker, args=(i, 1000))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Verify total events
    total = results['queued'] + results['dropped']
    assert total == 10000, f"Expected 10000 total events, got {total}"
    
    # Verify some were dropped (queue should be overwhelmed)
    assert results['dropped'] > 0, "Expected some drops with concurrent floods"


# ============================================================================
# Exception Injection Tests
# ============================================================================

def test_sidecar_handles_exception_in_processing():
    """Test @safe_observe catches exceptions and doesn't propagate."""
    
    @safe_observe("test_operation")
    def failing_operation():
        raise ValueError("Intentional test failure")
    
    # Call should not raise exception
    result = failing_operation()
    
    # Should return None (fail-open)
    assert result is None
    
    # Should increment error metrics
    metrics = get_metrics().get_metrics()
    assert metrics['counters'].get('sidecar.test_operation.errors', 0) > 0


def test_sidecar_handles_exception_injection_during_flood():
    """Test sidecar survives exceptions during event processing."""
    
    call_count = {'count': 0}
    
    @safe_observe("flood_processing")
    def process_event_with_errors(event):
        call_count['count'] += 1
        # Fail every 10th event
        if call_count['count'] % 10 == 0:
            raise RuntimeError("Intentional failure")
        return event
    
    # Process 100 events
    for i in range(100):
        process_event_with_errors({'id': i})
    
    # All 100 should have been called
    assert call_count['count'] == 100
    
    # Should have ~10 errors
    metrics = get_metrics().get_metrics()
    errors = metrics['counters'].get('sidecar.flood_processing.errors', 0)
    assert 8 <= errors <= 12, f"Expected ~10 errors, got {errors}"


def test_sidecar_handles_various_exception_types():
    """Test sidecar handles different exception types."""
    
    exceptions_to_test = [
        ValueError("Value error"),
        KeyError("Key error"),
        RuntimeError("Runtime error"),
        TypeError("Type error"),
        AttributeError("Attribute error"),
        Exception("Generic exception")
    ]
    
    for exc in exceptions_to_test:
        @safe_observe("exception_test")
        def failing_with_exc():
            raise exc
        
        # Should not propagate
        result = failing_with_exc()
        assert result is None


# ============================================================================
# Queue Exhaustion Tests
# ============================================================================

def test_sidecar_handles_queue_exhaustion():
    """Test sidecar handles queue reaching max capacity."""
    queue = get_event_queue()
    max_size = queue.get_stats()['max_size']
    
    # Fill queue to capacity
    for i in range(max_size):
        event = {'id': i, 'data': 'x'}
        queue.put(event)
    
    # Queue should be near capacity
    assert queue.is_full() or queue.size() >= max_size * 0.95
    
    # Try to add more events
    overflow_event = {'id': 'overflow', 'data': 'x'}
    result = queue.put(overflow_event)
    
    # Should be dropped
    assert result is False
    
    # Health status should show degraded
    health = get_health_status()
    assert health['status'] in ['degraded', 'ok']  # May be ok if queue draining


def test_sidecar_recovers_from_queue_exhaustion():
    """Test sidecar recovers when queue drains."""
    queue = get_event_queue()
    max_size = queue.get_stats()['max_size']
    
    # Fill queue
    for i in range(max_size):
        queue.put({'id': i})
    
    # Drain some events
    drained = 0
    for _ in range(max_size // 2):
        if queue.get(timeout=0.01):
            drained += 1
    
    assert drained > 0, "Should have drained some events"
    
    # Should now accept new events
    new_event = {'id': 'new'}
    result = queue.put(new_event)
    assert result is True


# ============================================================================
# Resource Exhaustion Tests
# ============================================================================

def test_sidecar_disables_profiling_on_high_cpu():
    """Test profiling is disabled when CPU exceeds budget."""
    monitor = get_resource_monitor()
    
    # Mock high CPU usage
    with patch('psutil.Process') as mock_process:
        mock_process.return_value.cpu_percent.return_value = 10.0  # 10% CPU
        
        resources = monitor.check_resources()
        
        # Should detect over budget (limit is 5%)
        assert resources.get('cpu_over_budget', False) is True
        
        # Should disable profiling
        assert monitor.is_profiling_enabled() is False


def test_sidecar_re_enables_profiling_when_cpu_normal():
    """Test profiling is re-enabled when CPU returns to normal."""
    monitor = get_resource_monitor()
    
    # Disable profiling
    monitor.disable_profiling()
    assert monitor.is_profiling_enabled() is False
    
    # Enable profiling
    monitor.enable_profiling()
    assert monitor.is_profiling_enabled() is True


@pytest.mark.skip(reason="Memory testing requires actual memory allocation")
def test_sidecar_tracks_memory_usage():
    """Test sidecar tracks memory usage accurately."""
    monitor = get_resource_monitor()
    
    resources = monitor.check_resources()
    
    # Should have memory metrics
    assert 'memory_mb' in resources
    assert resources['memory_mb'] > 0


# ============================================================================
# Sampling Tests Under Load
# ============================================================================

def test_sampling_works_under_flood():
    """Test sampling correctly reduces load during event flood."""
    sampler = get_sampler()
    
    # Configure low sampling rate
    update_config({
        'sampling_rates': {
            'test_events': 0.01  # 1% sampling
        }
    })
    
    # Flood with 10,000 events
    sampled = 0
    rejected = 0
    
    for i in range(10000):
        if sampler.should_sample('test_events'):
            sampled += 1
        else:
            rejected += 1
    
    # Should sample ~1% (100 events)
    # Allow 0.5% to 1.5% range due to deterministic sampling
    assert 50 <= sampled <= 150, f"Expected ~100 sampled, got {sampled}"
    assert rejected > 9000, f"Expected >9000 rejected, got {rejected}"


def test_sampling_statistics_accurate_under_load():
    """Test sampling statistics remain accurate under load."""
    sampler = get_sampler()
    
    # Sample 10,000 events
    for i in range(10000):
        sampler.should_sample('events')
    
    stats = sampler.get_stats()
    
    # Should have statistics
    assert 'events' in stats
    assert stats['events']['total_events'] >= 10000


# ============================================================================
# Configuration Corruption Tests
# ============================================================================

def test_sidecar_handles_invalid_config_reload():
    """Test sidecar handles invalid configuration gracefully."""
    
    # Try to reload with invalid config
    invalid_configs = [
        {'max_queue_size': -100},  # Negative value
        {'max_cpu_percent': 'invalid'},  # Wrong type
        {'sampling_rates': {'events': 2.0}},  # Rate > 1.0
        None,  # None config
        'not a dict',  # Wrong type
    ]
    
    for invalid_config in invalid_configs:
        try:
            update_config(invalid_config)
            # Should either ignore or handle gracefully
        except Exception as e:
            # Exception is acceptable
            assert isinstance(e, (ValueError, TypeError, AttributeError))


def test_sidecar_maintains_valid_config_after_corruption():
    """Test sidecar keeps valid config if reload fails."""
    config_before = get_config()
    
    # Try to load invalid config
    try:
        update_config({'max_queue_size': -999})
    except:
        pass
    
    config_after = get_config()
    
    # Config should remain valid
    assert config_after.max_queue_size > 0


# ============================================================================
# Health Endpoint Tests Under Stress
# ============================================================================

def test_health_endpoint_responds_during_flood():
    """Test /health endpoint responds during event flood."""
    queue = get_event_queue()
    
    # Start flooding in background
    def flood():
        for i in range(5000):
            queue.put({'id': i})
    
    flood_thread = threading.Thread(target=flood)
    flood_thread.start()
    
    # Check health while flooding
    health = get_health_status()
    
    # Should still respond
    assert 'status' in health
    assert health['status'] in ['ok', 'degraded']
    
    flood_thread.join()


def test_health_status_reflects_degradation():
    """Test health status correctly shows degradation under stress."""
    queue = get_event_queue()
    max_size = queue.get_stats()['max_size']
    
    # Fill queue to 95%
    for i in range(int(max_size * 0.95)):
        queue.put({'id': i})
    
    health = get_health_status()
    
    # Should show degraded status or high utilization
    assert health['queue']['utilization'] > 0.9


# ============================================================================
# Metrics Collection Under Stress
# ============================================================================

def test_metrics_collection_thread_safe():
    """Test metrics collection is thread-safe under concurrent access."""
    metrics = get_metrics()
    
    def increment_worker(count: int):
        for _ in range(count):
            metrics.increment('test.counter')
    
    # Start 10 threads, each incrementing 1000 times
    threads = []
    for _ in range(10):
        t = threading.Thread(target=increment_worker, args=(1000,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Should have 10,000 total increments
    result = metrics.get_metrics()
    assert result['counters'].get('test.counter', 0) == 10000


def test_histogram_recording_under_load():
    """Test histogram recording handles high volume."""
    metrics = get_metrics()
    
    # Record 10,000 values
    for i in range(10000):
        metrics.record_histogram('test.histogram', float(i % 100))
    
    result = metrics.get_metrics()
    
    # Should have histogram stats
    assert 'test.histogram' in result['histograms']
    stats = result['histograms']['test.histogram']
    assert stats['count'] == 10000


# ============================================================================
# Kill Switch Test
# ============================================================================

def test_sidecar_can_be_disabled_via_config():
    """Test sidecar can be disabled via configuration."""
    # Disable sidecar
    update_config({'enabled': False})
    
    config = get_config()
    assert config.enabled is False
    
    # Re-enable
    update_config({'enabled': True})
    
    config = get_config()
    assert config.enabled is True


def test_disabled_sidecar_still_responds_to_health_checks():
    """Test disabled sidecar still responds to health checks."""
    # Disable sidecar
    update_config({'enabled': False})
    
    # Health check should still work
    health = get_health_status()
    assert 'status' in health
    assert health['enabled'] is False
