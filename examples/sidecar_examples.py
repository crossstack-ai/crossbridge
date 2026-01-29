"""
Example: Basic Sidecar Usage

Shows how to use the debuggable sidecar runtime for test observation.
"""

from core.sidecar import SidecarRuntime, SidecarConfig

# Example 1: Basic usage with default configuration
def example_basic():
    """Basic sidecar usage"""
    print("Example 1: Basic Sidecar Usage\n" + "="*50)
    
    # Initialize with defaults
    sidecar = SidecarRuntime()
    
    # Start sidecar
    sidecar.start()
    print("✓ Sidecar started")
    
    # Observe some events
    for i in range(100):
        sidecar.observe(
            event_type='test_event',
            data={
                'test_id': f'test_{i}',
                'status': 'passed' if i % 10 != 0 else 'failed',
                'duration_ms': 100 + i
            },
            run_id='run_123'
        )
    
    print(f"✓ Observed 100 events")
    
    # Get health status
    health = sidecar.get_health()
    print(f"\nHealth Status: {health['status']}")
    print(f"Uptime: {health['uptime_human']}")
    
    # Get metrics
    metrics = sidecar.get_metrics()
    print(f"\nMetrics collected: {len(metrics)}")
    print(f"Events received: {metrics.get('sidecar_events_total', {}).get('value', 0)}")
    
    # Export Prometheus metrics
    print("\n--- Prometheus Metrics ---")
    print(sidecar.export_metrics())
    
    # Stop sidecar
    sidecar.stop()
    print("\n✓ Sidecar stopped gracefully")


# Example 2: Custom configuration
def example_custom_config():
    """Custom sidecar configuration"""
    print("\n\nExample 2: Custom Configuration\n" + "="*50)
    
    # Create custom config
    config = SidecarConfig()
    config.sampling.events = 0.5  # Sample 50% of events
    config.resources.max_queue_size = 5000
    config.profiling.enabled = True
    
    sidecar = SidecarRuntime(config=config)
    sidecar.start()
    
    print(f"✓ Sidecar started with custom config")
    print(f"  - Event sampling: {config.sampling.events * 100}%")
    print(f"  - Max queue size: {config.resources.max_queue_size}")
    print(f"  - Profiling: {'enabled' if config.profiling.enabled else 'disabled'}")
    
    # Observe events
    for i in range(50):
        sidecar.observe('test_event', {'test_id': f'test_{i}'})
    
    stats = sidecar.observer.get_stats()
    print(f"\n✓ Events received: {stats['events_received']}")
    print(f"✓ Events sampled: {stats['events_sampled']}")
    print(f"✓ Events dropped: {stats['events_dropped']}")
    
    sidecar.stop()


# Example 3: Context manager usage
def example_context_manager():
    """Using sidecar as context manager"""
    print("\n\nExample 3: Context Manager\n" + "="*50)
    
    with SidecarRuntime() as sidecar:
        print("✓ Sidecar auto-started")
        
        # Observe events
        for i in range(20):
            sidecar.observe('test_event', {'test_id': f'test_{i}'})
        
        print(f"✓ Observed 20 events")
        
        # Health check
        if sidecar.health.is_healthy():
            print("✓ Sidecar is healthy")
    
    print("✓ Sidecar auto-stopped")


# Example 4: Custom event handler
def example_custom_handler():
    """Register custom event handler"""
    print("\n\nExample 4: Custom Event Handler\n" + "="*50)
    
    def my_handler(event):
        """Custom handler for test failures"""
        if event.data.get('status') == 'failed':
            print(f"⚠ Test failed: {event.data.get('test_id')}")
    
    sidecar = SidecarRuntime()
    sidecar.start()
    
    # Register handler
    sidecar.register_handler('test_event', my_handler)
    print("✓ Custom handler registered")
    
    # Observe events (some will trigger handler)
    for i in range(10):
        sidecar.observe(
            'test_event',
            {
                'test_id': f'test_{i}',
                'status': 'failed' if i % 3 == 0 else 'passed'
            }
        )
    
    import time
    time.sleep(0.5)  # Give handler time to process
    
    sidecar.stop()


# Example 5: Adaptive sampling
def example_adaptive_sampling():
    """Adaptive sampling with anomaly detection"""
    print("\n\nExample 5: Adaptive Sampling\n" + "="*50)
    
    # Enable adaptive sampling
    sidecar = SidecarRuntime(adaptive_sampling=True)
    sidecar.start()
    
    print("✓ Adaptive sampling enabled")
    
    # Simulate normal operation
    for i in range(50):
        sidecar.observe('test_event', {'test_id': f'test_{i}'})
    
    print("✓ Observed 50 normal events")
    
    # Simulate anomaly (trigger adaptive boost)
    print("\n⚠ Simulating anomaly...")
    for i in range(5):
        sidecar.sampler.report_anomaly('test_event', 'error')
    
    # Check if boost was triggered
    stats = sidecar.sampler.get_stats()
    if stats.get('test_event', {}).get('has_boost'):
        print("✓ Adaptive boost triggered! Sampling increased 5x for 60 seconds")
    
    # Observe more events (should have higher sampling rate now)
    for i in range(50):
        sidecar.observe('test_event', {'test_id': f'test_boost_{i}'})
    
    stats = sidecar.observer.get_stats()
    print(f"\n✓ Total events received: {stats['events_received']}")
    print(f"✓ Total events sampled: {stats['events_sampled']}")
    print(f"✓ Sampling rate: {stats['events_sampled'] / max(stats['events_received'], 1) * 100:.1f}%")
    
    sidecar.stop()


# Example 6: Profiling and resource monitoring
def example_profiling():
    """Monitor resource usage"""
    print("\n\nExample 6: Profiling & Resource Monitoring\n" + "="*50)
    
    config = SidecarConfig()
    config.profiling.enabled = True
    config.profiling.sampling_interval = 0.5  # Sample every 0.5s
    
    sidecar = SidecarRuntime(config=config)
    sidecar.start()
    
    import time
    
    # Run for a few seconds
    print("✓ Profiling for 3 seconds...")
    for i in range(30):
        sidecar.observe('test_event', {'test_id': f'test_{i}'})
        time.sleep(0.1)
    
    # Get profiling summary
    summary = sidecar.profiler.get_summary(window_seconds=10)
    print(f"\n📊 Resource Usage:")
    print(f"  CPU: {summary['cpu_avg']:.2f}% (max: {summary['cpu_max']:.2f}%)")
    print(f"  Memory: {summary['memory_avg']:.1f} MB (max: {summary['memory_max']:.1f} MB)")
    print(f"  Threads: {summary['thread_avg']:.0f} (max: {summary['thread_max']})")
    print(f"  Memory growth: {summary['memory_growth_mb']:.2f} MB")
    
    # Check if within budget
    budget = sidecar.profiler.is_over_budget(
        cpu_budget=5.0,
        memory_budget_mb=100.0
    )
    
    if not budget['cpu_over_budget'] and not budget['memory_over_budget']:
        print("\n✓ Within resource budget!")
    else:
        print(f"\n⚠ Resource budget exceeded")
        if budget['cpu_over_budget']:
            print(f"  CPU: {budget['cpu_value']:.1f}% > {budget['cpu_budget']:.1f}%")
        if budget['memory_over_budget']:
            print(f"  Memory: {budget['memory_value']:.1f} MB > {budget['memory_budget']:.1f} MB")
    
    sidecar.stop()


if __name__ == '__main__':
    # Run all examples
    example_basic()
    example_custom_config()
    example_context_manager()
    example_custom_handler()
    example_adaptive_sampling()
    example_profiling()
    
    print("\n\n" + "="*50)
    print("All examples completed successfully! ✓")
