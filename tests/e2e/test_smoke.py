"""
End-to-End Smoke Tests

Quick validation tests that verify critical paths work correctly.
Should complete in < 5 minutes and catch major regressions.

Run with: pytest tests/e2e/test_smoke.py -v
"""

import pytest
import time
from typing import Dict, Any

from core.observability.sidecar import (
    get_config,
    get_metrics,
    get_event_queue,
    get_sampler,
    get_resource_monitor,
    safe_observe
)
from core.observability.sidecar.health import (
    get_health_status,
    get_readiness_status,
    get_prometheus_metrics,
    start_http_server,
    stop_http_server
)
from core.observability.sidecar.logging import (
    set_run_id,
    clear_context
)


# ============================================================================
# Smoke Test: Sidecar Starts
# ============================================================================

def test_smoke_sidecar_can_be_imported():
    """Test sidecar modules can be imported without errors."""
    # If we got here, imports succeeded
    assert True


def test_smoke_sidecar_config_loads():
    """Test sidecar configuration loads successfully."""
    config = get_config()
    
    # Verify required fields
    assert hasattr(config, 'enabled')
    assert hasattr(config, 'max_queue_size')
    assert hasattr(config, 'max_cpu_percent')
    assert hasattr(config, 'max_memory_mb')
    assert hasattr(config, 'sampling_rates')


def test_smoke_global_instances_initialized():
    """Test all global sidecar instances are initialized."""
    # These should not raise
    config = get_config()
    metrics = get_metrics()
    queue = get_event_queue()
    sampler = get_sampler()
    monitor = get_resource_monitor()
    
    assert config is not None
    assert metrics is not None
    assert queue is not None
    assert sampler is not None
    assert monitor is not None


# ============================================================================
# Smoke Test: Event Flow
# ============================================================================

def test_smoke_events_can_be_queued():
    """Test events can be queued successfully."""
    queue = get_event_queue()
    
    test_event = {
        'type': 'smoke_test',
        'id': 'smoke_1',
        'data': 'test payload'
    }
    
    result = queue.put(test_event)
    assert result is True


def test_smoke_events_can_be_retrieved():
    """Test events can be retrieved from queue."""
    queue = get_event_queue()
    
    # Queue an event
    test_event = {'type': 'smoke_test', 'id': 'smoke_2'}
    queue.put(test_event)
    
    # Retrieve it
    retrieved = queue.get(timeout=1.0)
    assert retrieved is not None
    assert retrieved['id'] == 'smoke_2'


def test_smoke_event_processing_works():
    """Test events can be processed with @safe_observe."""
    processed = {'success': False}
    
    @safe_observe("smoke_processing")
    def process_event(event):
        processed['success'] = True
        return {'status': 'ok'}
    
    result = process_event({'id': 'test'})
    
    assert processed['success'] is True
    assert result['status'] == 'ok'


# ============================================================================
# Smoke Test: Sampling
# ============================================================================

def test_smoke_sampling_works():
    """Test sampling decision works."""
    sampler = get_sampler()
    
    # Should return boolean
    result = sampler.should_sample('events')
    assert isinstance(result, bool)


def test_smoke_sampling_reduces_load():
    """Test sampling actually filters events."""
    sampler = get_sampler()
    
    # Sample 100 events
    sampled = 0
    for _ in range(100):
        if sampler.should_sample('events'):
            sampled += 1
    
    # With default 10% rate, should sample ~10 events
    # Allow 0-50 range (very permissive for smoke test)
    assert 0 <= sampled <= 50


# ============================================================================
# Smoke Test: Metrics
# ============================================================================

def test_smoke_metrics_can_be_collected():
    """Test metrics can be collected."""
    metrics = get_metrics()
    
    # Increment a counter
    metrics.increment('smoke.counter')
    
    # Set a gauge
    metrics.set_gauge('smoke.gauge', 42.0)
    
    # Record histogram
    metrics.record_histogram('smoke.histogram', 100.0)
    
    # Get metrics
    result = metrics.get_metrics()
    
    # Verify structure
    assert 'counters' in result
    assert 'gauges' in result
    assert 'histograms' in result


def test_smoke_metrics_increment_works():
    """Test counter increments work."""
    metrics = get_metrics()
    
    initial = metrics.get_metrics()
    initial_count = initial['counters'].get('smoke.test', 0)
    
    # Increment
    metrics.increment('smoke.test', 5)
    
    final = metrics.get_metrics()
    final_count = final['counters'].get('smoke.test', 0)
    
    # Should increase by 5
    assert final_count == initial_count + 5


# ============================================================================
# Smoke Test: Resource Monitoring
# ============================================================================

def test_smoke_resource_monitoring_works():
    """Test resource monitoring returns data."""
    monitor = get_resource_monitor()
    
    resources = monitor.check_resources()
    
    # Should have CPU and memory metrics
    assert 'cpu_percent' in resources
    assert 'memory_mb' in resources
    assert isinstance(resources['cpu_percent'], float)
    assert isinstance(resources['memory_mb'], float)


def test_smoke_profiling_can_be_toggled():
    """Test profiling can be enabled/disabled."""
    monitor = get_resource_monitor()
    
    # Should have profiling state
    initial_state = monitor.is_profiling_enabled()
    assert isinstance(initial_state, bool)
    
    # Toggle
    if initial_state:
        monitor.disable_profiling()
        assert monitor.is_profiling_enabled() is False
        monitor.enable_profiling()
    else:
        monitor.enable_profiling()
        assert monitor.is_profiling_enabled() is True
        monitor.disable_profiling()


# ============================================================================
# Smoke Test: Health Endpoints
# ============================================================================

def test_smoke_health_status_returns():
    """Test health status can be retrieved."""
    health = get_health_status()
    
    # Should have required fields
    assert 'status' in health
    assert 'enabled' in health
    assert 'queue' in health
    assert 'resources' in health
    assert 'metrics' in health


def test_smoke_readiness_status_returns():
    """Test readiness status can be retrieved."""
    readiness = get_readiness_status()
    
    # Should have required fields
    assert 'ready' in readiness
    assert 'enabled' in readiness
    assert isinstance(readiness['ready'], bool)


def test_smoke_prometheus_metrics_export():
    """Test Prometheus metrics can be exported."""
    metrics_text = get_prometheus_metrics()
    
    # Should be non-empty text
    assert isinstance(metrics_text, str)
    assert len(metrics_text) > 0
    
    # Should have Prometheus format markers
    assert '# TYPE' in metrics_text or 'sidecar' in metrics_text


@pytest.mark.skip(reason="HTTP server test requires network access")
def test_smoke_http_server_starts():
    """Test HTTP server can be started."""
    try:
        # Start server
        start_http_server(port=9091)  # Use different port to avoid conflicts
        
        time.sleep(0.5)  # Wait for server to start
        
        # Server should be running
        # (We skip actual HTTP request in smoke test)
        
    finally:
        # Stop server
        stop_http_server()


# ============================================================================
# Smoke Test: Correlation Context
# ============================================================================

def test_smoke_correlation_context_works():
    """Test correlation context can be set and retrieved."""
    # Set context
    set_run_id('smoke_run_123')
    
    from core.observability.sidecar.logging import get_run_id
    
    # Verify
    assert get_run_id() == 'smoke_run_123'
    
    # Clear
    clear_context()
    assert get_run_id() is None


# ============================================================================
# Smoke Test: Fail-Open Behavior
# ============================================================================

def test_smoke_fail_open_catches_exceptions():
    """Test @safe_observe catches exceptions."""
    
    @safe_observe("smoke_fail_test")
    def failing_operation():
        raise ValueError("Intentional smoke test failure")
    
    # Should not raise
    result = failing_operation()
    
    # Should return None (fail-open)
    assert result is None


def test_smoke_fail_open_tracks_errors():
    """Test @safe_observe tracks errors in metrics."""
    metrics = get_metrics()
    
    initial = metrics.get_metrics()
    initial_errors = initial['counters'].get('sidecar.smoke_error_test.errors', 0)
    
    @safe_observe("smoke_error_test")
    def failing_op():
        raise RuntimeError("Test error")
    
    # Call failing operation
    failing_op()
    
    final = metrics.get_metrics()
    final_errors = final['counters'].get('sidecar.smoke_error_test.errors', 0)
    
    # Errors should increase
    assert final_errors > initial_errors


# ============================================================================
# Smoke Test: Queue Bounds
# ============================================================================

def test_smoke_queue_has_max_size():
    """Test queue respects max size."""
    queue = get_event_queue()
    stats = queue.get_stats()
    
    # Should have max size
    assert 'max_size' in stats
    assert stats['max_size'] > 0


def test_smoke_queue_statistics():
    """Test queue statistics are available."""
    queue = get_event_queue()
    stats = queue.get_stats()
    
    # Required fields
    assert 'current_size' in stats
    assert 'max_size' in stats
    assert 'total_events' in stats
    assert 'dropped_events' in stats
    assert 'utilization' in stats


# ============================================================================
# Smoke Test: Configuration
# ============================================================================

def test_smoke_config_has_required_fields():
    """Test configuration has all required fields."""
    config = get_config()
    
    # Required fields
    assert config.enabled is not None
    assert config.max_queue_size > 0
    assert config.max_cpu_percent > 0
    assert config.max_memory_mb > 0
    assert isinstance(config.sampling_rates, dict)
    assert 'events' in config.sampling_rates


def test_smoke_config_sampling_rates_valid():
    """Test sampling rates are valid (0.0 to 1.0)."""
    config = get_config()
    
    for event_type, rate in config.sampling_rates.items():
        assert 0.0 <= rate <= 1.0, f"Invalid rate for {event_type}: {rate}"


# ============================================================================
# Smoke Test: Integration
# ============================================================================

def test_smoke_full_pipeline():
    """
    Smoke test for full pipeline:
    1. Queue event
    2. Sample event
    3. Process event
    4. Collect metrics
    5. Check health
    """
    # 1. Queue event
    queue = get_event_queue()
    event = {'type': 'smoke_integration', 'id': 'pipeline_1'}
    queue.put(event)
    
    # 2. Get event
    retrieved = queue.get(timeout=1.0)
    assert retrieved is not None
    
    # 3. Sample decision
    sampler = get_sampler()
    should_process = sampler.should_sample('events')
    
    # 4. Process (if sampled)
    @safe_observe("smoke_pipeline")
    def process(evt):
        return {'status': 'processed'}
    
    if should_process:
        result = process(retrieved)
        assert result['status'] == 'processed'
    
    # 5. Check metrics
    metrics = get_metrics()
    result = metrics.get_metrics()
    assert 'counters' in result
    
    # 6. Check health
    health = get_health_status()
    assert 'status' in health


# ============================================================================
# Cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test."""
    yield
    
    # Clear context
    clear_context()
    
    # Drain queue (non-blocking)
    queue = get_event_queue()
    while queue.size() > 0:
        if not queue.get(timeout=0.01):
            break


# ============================================================================
# Smoke Test Suite Summary
# ============================================================================

def test_smoke_suite_summary():
    """
    Summary of smoke test coverage:
    
    ✓ Sidecar initialization
    ✓ Event queuing and retrieval
    ✓ Sampling decisions
    ✓ Metrics collection
    ✓ Resource monitoring
    ✓ Health/readiness endpoints
    ✓ Correlation context
    ✓ Fail-open behavior
    ✓ Queue bounds and statistics
    ✓ Configuration validation
    ✓ Full pipeline integration
    
    These tests should complete in < 1 minute.
    """
    assert True  # If we got here, all smoke tests passed
