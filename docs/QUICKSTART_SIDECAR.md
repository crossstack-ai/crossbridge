# Quick Start Guide: Test Infrastructure & Sidecar Observer

**Get started in 5 minutes** ⚡

---

## 1. Installation (30 seconds)

```bash
# Already installed! No additional dependencies needed.
# Sidecar is built into CrossBridge core
```

---

## 2. Enable Sidecar (1 minute)

**Edit `crossbridge.yml`:**

```yaml
crossbridge:
  sidecar:
    enabled: true  # That's it!
```

**Or use environment variable:**

```bash
export CROSSBRIDGE_SIDECAR_ENABLED=true
```

---

## 3. Run Your Tests (2 minutes)

```bash
# Run tests normally - sidecar works in background
pytest tests/

# Or with CrossBridge CLI
python -m cli.main run-tests --config crossbridge.yml
```

**What happens:**
- ✅ Tests run normally (no changes needed)
- ✅ Sidecar observes in background (fail-open)
- ✅ Events sampled (10%) and queued
- ✅ Metrics collected automatically

---

## 4. Check Health (1 minute)

**Start health server (automatic on first use):**

```python
from core.observability.sidecar.health import start_http_server

start_http_server(port=9090)
```

**Check endpoints:**

```bash
# Health check
curl http://localhost:9090/health
# Returns: {"status": "ok", ...}

# Readiness probe
curl http://localhost:9090/ready
# Returns: {"ready": true}

# Prometheus metrics
curl http://localhost:9090/metrics
# Returns: Prometheus format metrics
```

---

## 5. View Metrics (30 seconds)

```bash
# View all metrics
curl http://localhost:9090/metrics

# Key metrics:
# - sidecar_events_queued_total
# - sidecar_events_processed_total
# - sidecar_events_dropped_total
# - sidecar_queue_size
# - sidecar_cpu_usage
# - sidecar_memory_usage
```

---

## Done! 🎉

You now have:
- ✅ Sidecar observing test execution
- ✅ Events being sampled and queued
- ✅ Metrics being collected
- ✅ Health endpoints available
- ✅ Full observability

---

## Common Use Cases

### Use Case 1: Monitor Queue Status

```python
from core.observability.sidecar import get_event_queue

queue = get_event_queue()
stats = queue.get_stats()

print(f"Queue size: {stats['current_size']}/{stats['max_size']}")
print(f"Utilization: {stats['utilization']:.1%}")
print(f"Dropped: {stats['dropped_events']}")
```

### Use Case 2: Check Resource Usage

```python
from core.observability.sidecar import get_resource_monitor

monitor = get_resource_monitor()
resources = monitor.check_resources()

print(f"CPU: {resources['cpu_percent']:.1f}% (max: 5%)")
print(f"Memory: {resources['memory_mb']:.1f} MB (max: 100 MB)")
print(f"Profiling: {'enabled' if resources['profiling_enabled'] else 'disabled'}")
```

### Use Case 3: Track Events

```python
from core.observability.sidecar import get_event_queue

queue = get_event_queue()

# Queue event
event = {
    'type': 'test_completed',
    'test_name': 'test_login',
    'status': 'passed',
    'duration': 2.5
}

if queue.put(event):
    print("✅ Event queued")
else:
    print("⚠️  Event dropped (queue full)")
```

### Use Case 4: Correlation Tracking

```python
from core.observability.sidecar.logging import set_run_id, set_test_id

# At start of test run
set_run_id('run_123')

# At start of test case
set_test_id('test_login')

# All logs now include run_id and test_id
# All events include correlation IDs
```

---

## Configuration Examples

### Minimal (Default)

```yaml
crossbridge:
  sidecar:
    enabled: true
```

### Custom Sampling

```yaml
crossbridge:
  sidecar:
    enabled: true
    sampling:
      rates:
        events: 0.05   # 5% events (lower for high volume)
        logs: 0.01     # 1% logs
        profiling: 0.005  # 0.5% profiling
```

### Higher Resource Limits

```yaml
crossbridge:
  sidecar:
    enabled: true
    resources:
      max_cpu_percent: 10.0    # 10% CPU (higher limit)
      max_memory_mb: 200       # 200 MB RAM
    queue:
      max_size: 10000          # 10K events
```

### Custom Health Port

```yaml
crossbridge:
  sidecar:
    enabled: true
    health:
      port: 8080    # Custom port
```

---

## Testing

### Run All Tests

```bash
pytest tests/ --cov=core
```

### Run Unit Tests Only

```bash
pytest tests/unit/ -v
```

### Run Smoke Tests (< 5 min)

```bash
pytest tests/e2e/test_smoke.py -v
```

### Check Coverage

```bash
pytest tests/ --cov=core --cov-fail-under=70
```

---

## Troubleshooting

### Problem: Queue filling up

**Solution:**
```yaml
# Increase queue size OR increase sampling
sidecar:
  queue:
    max_size: 10000
  # OR
  sampling:
    rates:
      events: 0.05  # Lower from 10% to 5%
```

### Problem: High CPU usage

**Solution:**
```yaml
# Lower CPU budget (profiling will auto-disable sooner)
sidecar:
  resources:
    max_cpu_percent: 3.0  # Stricter
```

### Problem: Can't access health endpoint

**Check:**
```bash
# Is server running?
curl http://localhost:9090/health

# Wrong port?
# Check crossbridge.yml: sidecar.health.port

# Firewall blocking?
# Allow port 9090 (or configured port)
```

### Problem: Not seeing metrics

**Check:**
```python
from core.observability.sidecar import get_metrics

metrics = get_metrics().get_metrics()
print(metrics)  # Should have counters, gauges, histograms
```

---

## Integration with Kubernetes

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crossbridge
spec:
  template:
    spec:
      containers:
      - name: crossbridge
        image: crossbridge:latest
        ports:
        - containerPort: 9090
          name: health
        
        # Liveness probe
        livenessProbe:
          httpGet:
            path: /health
            port: 9090
          initialDelaySeconds: 30
          periodSeconds: 10
        
        # Readiness probe
        readinessProbe:
          httpGet:
            path: /ready
            port: 9090
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: crossbridge-sidecar
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
    prometheus.io/path: "/metrics"
spec:
  selector:
    app: crossbridge
  ports:
  - port: 9090
    name: metrics
```

---

## Integration with Prometheus

### Scrape Config

```yaml
scrape_configs:
  - job_name: 'crossbridge-sidecar'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Example Queries

```promql
# Event processing rate
rate(sidecar_events_processed_total[5m])

# Queue utilization
sidecar_queue_size / sidecar_queue_max_size

# Error rate
rate(sidecar_errors_total[5m])

# CPU usage
sidecar_cpu_usage

# Average latency
rate(sidecar_event_processing_duration_ms_sum[5m]) /
rate(sidecar_event_processing_duration_ms_count[5m])
```

---

## Integration with Grafana

### Dashboard Panels

**Panel 1: Event Throughput**
```promql
sum(rate(sidecar_events_queued_total[5m]))
```

**Panel 2: Queue Utilization**
```promql
(sidecar_queue_size / sidecar_queue_max_size) * 100
```

**Panel 3: Error Rate**
```promql
rate(sidecar_errors_total[5m])
```

**Panel 4: Resource Usage**
```promql
# CPU
sidecar_cpu_usage

# Memory
sidecar_memory_usage
```

---

## Using with CI/CD

### GitHub Actions

```yaml
name: Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=core --cov-fail-under=70
```

### GitLab CI

```yaml
test:
  script:
    - pip install -r requirements.txt
    - pytest tests/ --cov=core --cov-fail-under=70
```

---

## Best Practices

### ✅ DO:
- Enable sidecar in production (fail-open is safe)
- Monitor `/health` endpoint
- Set up Prometheus scraping
- Configure alerts on high error rates
- Use correlation IDs for tracking

### ❌ DON'T:
- Don't disable fail-open behavior
- Don't set sampling rates to 100% (high overhead)
- Don't ignore high queue utilization warnings
- Don't run without health monitoring

---

## Support

### Documentation
- Full Guide: `docs/TEST_INFRASTRUCTURE_AND_SIDECAR_HARDENING.md`
- Implementation Summary: `docs/IMPLEMENTATION_SUMMARY.md`

### Examples
- Fixtures: `tests/fixtures/`
- Integration Tests: `tests/integration/sidecar/`
- Smoke Tests: `tests/e2e/test_smoke.py`

### Configuration
- Main Config: `crossbridge.yml` (section: `sidecar:`)
- CI Config: `.ci/test-configuration.yml`

---

## Quick Reference

### Common Commands
```bash
# Run tests
pytest tests/

# Check coverage
pytest tests/ --cov=core --cov-fail-under=70

# Run smoke tests
pytest tests/e2e/test_smoke.py -v

# View metrics
curl http://localhost:9090/metrics

# Check health
curl http://localhost:9090/health
```

### Common Python Operations
```python
# Get queue stats
from core.observability.sidecar import get_event_queue
stats = get_event_queue().get_stats()

# Get resource usage
from core.observability.sidecar import get_resource_monitor
resources = get_resource_monitor().check_resources()

# Get metrics
from core.observability.sidecar import get_metrics
metrics = get_metrics().get_metrics()

# Check health
from core.observability.sidecar.health import get_health_status
health = get_health_status()
```

### Environment Variables
```bash
export SIDECAR_SAMPLE_EVENTS=0.05      # 5% events
export SIDECAR_MAX_CPU=3.0             # 3% CPU
export SIDECAR_QUEUE_SIZE=10000        # 10K queue
export SIDECAR_HEALTH_PORT=8080        # Port 8080
export SIDECAR_LOG_LEVEL=DEBUG         # DEBUG logs
```

---

## Next Steps

1. ✅ **Enable sidecar** in `crossbridge.yml`
2. ✅ **Run tests** to verify
3. ✅ **Check health** endpoint
4. ✅ **Set up monitoring** (Prometheus + Grafana)
5. ✅ **Configure alerts** (queue full, high errors)
6. ✅ **Tune sampling** based on load

**You're ready to go!** 🚀

---

**Questions?** See full documentation: `docs/TEST_INFRASTRUCTURE_AND_SIDECAR_HARDENING.md`
