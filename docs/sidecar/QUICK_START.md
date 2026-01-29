# Sidecar Runtime - Quick Start Guide

**5-Minute Setup for Debuggable Observability**

---

## Installation

Sidecar runtime is built into CrossBridge. No additional installation required.

```bash
# Ensure CrossBridge dependencies are installed
pip install -r requirements.txt
```

---

## Configuration

### 1. Enable in `crossbridge.yml`

```yaml
runtime:
  sidecar:
    enabled: true
    sampling:
      events: 0.1        # Sample 10% of events
      adaptive: enabled  # Auto-boost on anomalies
    resources:
      max_queue_size: 10000
      max_cpu_percent: 5.0
      max_memory_mb: 100
```

### 2. Environment Variables (Optional)

```bash
export SIDECAR_ENABLED=true
export SIDECAR_SAMPLE_EVENTS=0.2
export SIDECAR_CPU_BUDGET=5.0
```

---

## Basic Usage

### Simple Example

```python
from core.sidecar import SidecarRuntime

# Create and start
sidecar = SidecarRuntime()
sidecar.start()

# Observe events
sidecar.observe('test_event', {
    'test_id': 'test_123',
    'status': 'passed',
    'duration_ms': 1234
})

# Get health
health = sidecar.get_health()
print(f"Status: {health['status']}")

# Stop
sidecar.stop()
```

### Context Manager (Recommended)

```python
from core.sidecar import SidecarRuntime

with SidecarRuntime() as sidecar:
    # Auto-started
    sidecar.observe('test_event', {'test_id': 'test_123'})
    # Auto-stopped on exit
```

---

## Common Patterns

### 1. Test Execution Monitoring

```python
with SidecarRuntime() as sidecar:
    # Test start
    sidecar.observe('test_start', {
        'test_id': 'login_test',
        'timestamp': time.time()
    })
    
    # Run test...
    
    # Test end
    sidecar.observe('test_end', {
        'test_id': 'login_test',
        'status': 'passed',
        'duration_ms': 1234
    })
```

### 2. Custom Sampling Rates

```python
config = SidecarConfig()
config.sampling.events = 0.5       # 50%
config.sampling.test_events = 0.8  # 80%

sidecar = SidecarRuntime(config=config)
```

### 3. Event Handlers

```python
def on_test_failure(event):
    print(f"Test failed: {event.data['test_id']}")
    # Send alert, log to DB, etc.

with SidecarRuntime() as sidecar:
    sidecar.register_handler('test_failure', on_test_failure)
    
    # Handler called when test_failure events observed
    sidecar.observe('test_failure', {'test_id': 'test_123'})
```

### 4. Health Checks

```python
with SidecarRuntime() as sidecar:
    health = sidecar.get_health()
    
    if health['status'] == 'healthy':
        print("✓ All systems operational")
    elif health['status'] == 'degraded':
        print("⚠ Some components degraded")
        for name, comp in health['components'].items():
            if comp['status'] != 'healthy':
                print(f"  - {name}: {comp['status']}")
```

### 5. Prometheus Metrics

```python
with SidecarRuntime() as sidecar:
    # ... observe events ...
    
    # Export metrics
    metrics = sidecar.export_metrics()
    
    # Expose on HTTP endpoint
    @app.route('/metrics')
    def metrics():
        return Response(sidecar.export_metrics(), mimetype='text/plain')
```

---

## Verification

### Check Health

```python
health = sidecar.get_health()
assert health['status'] == 'healthy'
```

### Check Metrics

```python
metrics = sidecar.get_metrics()
assert 'sidecar_events_total' in metrics
```

### Check Resource Usage

```python
snapshot = sidecar.profiler.get_current()
assert snapshot.cpu_percent < 5.0
assert snapshot.memory_mb < 100
```

---

## Troubleshooting

### High Drop Rate

```python
stats = sidecar.observer.get_stats()
drop_rate = stats['events_dropped'] / stats['events_received']

if drop_rate > 0.2:
    # Increase queue size
    config.resources.max_queue_size = 20000
```

### High CPU Usage

```python
if sidecar.profiler.is_over_budget()['cpu_over_budget']:
    # Reduce sampling
    config.sampling.events = 0.05
```

### Degraded Status

```python
health = sidecar.get_health()
for name, comp in health['components'].items():
    if comp['status'] != 'healthy':
        print(f"{name}: {comp['message']}")
```

---

## Next Steps

- 📖 [Complete Guide](SIDECAR_RUNTIME.md) - All features and APIs
- 💡 [Examples](../../examples/sidecar_examples.py) - 6 comprehensive examples
- ⚙️ [Configuration](../../crossbridge.yml) - Full config reference
- 📊 [Grafana Integration](SIDECAR_RUNTIME.md#prometheangrafana-integration) - Dashboards

---

## Key Features

✅ **Fail-Open** - Never breaks test execution  
✅ **Low Overhead** - <5% CPU, <100MB memory  
✅ **Configurable** - Runtime reload without restart  
✅ **Adaptive** - Auto-boost sampling on anomalies  
✅ **Observable** - Prometheus metrics + health checks  
✅ **Safe** - Exception isolation, bounded queues  

---

## Support

- GitHub Issues: https://github.com/crossstack-ai/crossbridge/issues
- Documentation: `docs/sidecar/`
- Examples: `examples/sidecar_examples.py`
