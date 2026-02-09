# CrossBridge Sidecar API Reference

**Version:** v0.2.0  
**Last Updated:** January 31, 2026

---

## Overview

The CrossBridge Sidecar Observer provides HTTP endpoints for health monitoring, metrics collection, and runtime configuration. All endpoints are optional and can be disabled via configuration.

---

## Health Endpoints

### GET /health

Returns the overall health status of the sidecar observer.

**Response Codes:**
- `200 OK` - Sidecar is healthy
- `503 Service Unavailable` - Sidecar is degraded or down

**Response Format:**
```json
{
  "status": "ok",  // "ok", "degraded", or "down"
  "timestamp": 1738339200.0,
  "queue": {
    "size": 42,
    "max_size": 5000,
    "utilization": 0.0084,
    "dropped_events": 0
  },
  "resources": {
    "cpu_percent": 2.5,
    "memory_mb": 45.2,
    "cpu_over_budget": false,
    "memory_over_budget": false
  },
  "metrics": {
    "events_queued": 1250,
    "events_processed": 1248,
    "events_dropped": 2,
    "errors_total": 0
  }
}
```

**Health Status Logic:**
- `ok` - Queue <80%, errors <10, resources within budget
- `degraded` - Queue 80-95%, errors 10-50, or resources over budget
- `down` - Queue >95%, errors >50, or critical failure

---

### GET /ready

Kubernetes-style readiness probe. Returns whether the sidecar is ready to accept events.

**Response Codes:**
- `200 OK` - Sidecar is ready
- `503 Service Unavailable` - Sidecar is not ready

**Response Format:**
```json
{
  "ready": true,
  "timestamp": 1738339200.0,
  "queue_utilization": 0.0084,
  "enabled": true
}
```

**Readiness Logic:**
- Ready if: enabled AND queue utilization <90%
- Not ready if: disabled OR queue full

---

### GET /metrics

Returns Prometheus-compatible metrics in text format.

**Response Format:** `text/plain; version=0.0.4`

```prometheus
# HELP sidecar_events_queued Total events queued
# TYPE sidecar_events_queued counter
sidecar_events_queued 1250

# HELP sidecar_events_processed Total events processed
# TYPE sidecar_events_processed counter
sidecar_events_processed 1248

# HELP sidecar_events_dropped Events dropped due to full queue
# TYPE sidecar_events_dropped counter
sidecar_events_dropped 2

# HELP sidecar_queue_size Current queue size
# TYPE sidecar_queue_size gauge
sidecar_queue_size 42

# HELP sidecar_cpu_usage Current CPU usage percentage
# TYPE sidecar_cpu_usage gauge
sidecar_cpu_usage 2.5

# HELP sidecar_memory_usage Current memory usage in MB
# TYPE sidecar_memory_usage gauge
sidecar_memory_usage 45.2

# HELP sidecar_errors_total Total errors encountered
# TYPE sidecar_errors_total counter
sidecar_errors_total 0
```

**Metrics Categories:**
- Counters: events_queued, events_processed, events_dropped, errors_total
- Gauges: queue_size, queue_utilization, cpu_usage, memory_usage
- Histograms: event_processing_duration_ms, sampling_rate

---

### POST /sidecar/config/reload

Reload sidecar configuration at runtime without restart.

**Request Body:**
```json
{
  "sampling_rates": {
    "events": 0.2,
    "logs": 0.1,
    "profiling": 0.05
  },
  "max_cpu_percent": 10.0,
  "max_memory_mb": 200.0
}
```

**Response Codes:**
- `200 OK` - Configuration reloaded successfully
- `400 Bad Request` - Invalid configuration
- `500 Internal Server Error` - Reload failed

**Response Format:**
```json
{
  "status": "ok",
  "message": "Configuration reloaded successfully",
  "timestamp": 1738339200.0,
  "updated_fields": ["sampling_rates", "max_cpu_percent"]
}
```

---

## Intelligence Analysis APIs

### POST /analyze

Analyze parsed test logs with execution intelligence to classify failures, extract signals, and generate recommendations.

**Request Body:**
```json
{
  "data": {
    "tests": [...],
    "framework": "robot",
    ...
  },
  "framework": "robot|cypress|pytest|etc",
  "workspace_root": "/path/to/project",
  "enable_ai": true,
  "ai_provider": "openai|anthropic|ollama|selfhosted",
  "ai_model": "gpt-3.5-turbo"
}
```

**Response Codes:**
- `200 OK` - Analysis completed successfully
- `403 Forbidden` - AI license validation failed (cloud providers only)
- `500 Internal Server Error` - Analysis failed

**Response Format:**
```json
{
  "analyzed": true,
  "data": { /* original data */ },
  "intelligence_summary": {
    "classifications": {
      "PRODUCT_DEFECT": 2,
      "AUTOMATION_DEFECT": 1,
      "ENVIRONMENT_ISSUE": 1
    },
    "signals": {
      "timeout": 1,
      "assertion_failure": 2,
      "api_error": 1
    },
    "recommendations": [
      "Check API endpoint availability",
      "Verify test environment configuration",
      "Review timeout settings"
    ],
    "top_failures": [
      {
        "test_name": "Login Test",
        "failure_type": "API_ERROR",
        "confidence": 0.95,
        "reason": "HTTP 500 error from /api/login"
      }
    ]
  },
  "enriched_tests": [
    {
      "id": "test_001",
      "name": "Login Test",
      "classification": {
        "type": "API_ERROR",
        "confidence": 0.95,
        "reason": "HTTP 500 error detected"
      },
      "signals": [
        {
          "type": "api_error",
          "confidence": 0.95,
          "message": "API returned status code 500"
        }
      ],
      "ai_enhanced": true,
      "ai_reasoning": "API gateway timeout - backend service unresponsive"
    }
  ]
}
```

**Features:**
- Automatic failure classification (5 categories + 31 sub-categories)
- Signal extraction (20+ signal types)
- AI-enhanced root cause analysis (optional)
- Code reference resolution for automation defects
- Confidence scoring for all classifications
- Works deterministically without AI

**AI Providers:**
- OpenAI (requires API key, ~$0.01-$0.10 per run)
- Anthropic (requires API key, ~$0.015-$0.15 per run)
- Azure OpenAI (requires credentials, varies by subscription)
- Ollama/Self-hosted (no license, free inference)

---

### POST /summarize-recommendations 🆕

Intelligently summarize verbose recommendations using AI to produce concise, actionable outputs.

**Request Body:**
```json
{
  "recommendations": [
    "The error message 'start_instant_vm job ended with status: failed' suggests that there's a problem with the instant VM (a feature of Hyper-V) process. This could be due to several factors including insufficient resources, configuration issues, or networking problems.",
    "Another long verbose recommendation that needs summarization..."
  ],
  "max_length": 200,
  "ai_provider": "openai|anthropic|ollama",
  "ai_model": "gpt-3.5-turbo"
}
```

**Response Codes:**
- `200 OK` - Summarization completed
- `500 Internal Server Error` - Summarization failed

**Response Format:**
```json
{
  "summarized": true,
  "recommendations": [
    "Check Hyper-V instant VM configuration and verify host has sufficient resources to initialize virtual machines",
    "Review network settings and confirm VM networking is properly configured"
  ],
  "original_count": 2,
  "summarized_count": 2
}
```

**Features:**
- AI-powered intelligent summarization
- Eliminates mid-sentence truncation
- Combines duplicate recommendations automatically
- Maintains technical accuracy while removing fluff
- Smart sentence-boundary awareness (fallback without AI)
- Configurable length limits (default: 200 chars)
- Works with all AI providers (OpenAI, Anthropic, Ollama)

**Fallback Behavior:**
- If AI unavailable or fails, falls back to sentence-boundary truncation
- Returns `"summarized": false` when fallback is used
- Always returns valid recommendations (never fails completely)

**Usage Example:**
```bash
# CLI automatically uses this endpoint when --enable-ai is set
./bin/crossbridge-log output.xml --enable-ai

# Recommendations are intelligently summarized:
# Before: "The error message... This could be due to several"
# After: "Check Hyper-V instant VM configuration and verify resources"
```

---

## Internal APIs

These APIs are used internally by CrossBridge and are not exposed via HTTP.

### Event Queue API

#### `queue.put(event: Dict) -> bool`

Add event to the bounded queue.

**Parameters:**
- `event` (Dict): Event dictionary with arbitrary fields

**Returns:**
- `True` if event was queued
- `False` if event was dropped (queue full)

**Example:**
```python
from core.observability.sidecar import get_event_queue

queue = get_event_queue()
success = queue.put({
    'type': 'test_completed',
    'test_name': 'test_login',
    'status': 'passed',
    'duration_ms': 1250
})
```

#### `queue.get(timeout: float = 1.0) -> Optional[Dict]`

Retrieve event from queue with timeout.

**Parameters:**
- `timeout` (float): Maximum wait time in seconds

**Returns:**
- Event dict if available
- `None` if timeout or queue empty

---

### Metrics API

#### `metrics.increment(name: str, value: int = 1)`

Increment a counter metric.

**Example:**
```python
from core.observability.sidecar import get_metrics

metrics = get_metrics()
metrics.increment('custom_events')
metrics.increment('custom_events', 5)  # Increment by 5
```

#### `metrics.set_gauge(name: str, value: float)`

Set a gauge metric to a specific value.

**Example:**
```python
metrics.set_gauge('active_connections', 42.0)
```

#### `metrics.record_histogram(name: str, value: float)`

Record a histogram value (for latency, durations, etc.).

**Example:**
```python
metrics.record_histogram('request_duration_ms', 125.5)
```

---

### Sampler API

#### `sampler.should_sample(event_type: str) -> bool`

Determine if an event should be sampled based on configured rates.

**Parameters:**
- `event_type` (str): Event type ('events', 'logs', 'profiling', 'metrics')

**Returns:**
- `True` if event should be sampled
- `False` if event should be skipped

**Example:**
```python
from core.observability.sidecar import get_sampler

sampler = get_sampler()

if sampler.should_sample('events'):
    # Process event
    queue.put(event)
else:
    # Skip event (sampling)
    pass
```

---

### Resource Monitor API

#### `monitor.check_resources() -> Dict`

Check current resource usage and budget compliance.

**Returns:**
```python
{
    'cpu_percent': 2.5,
    'memory_mb': 45.2,
    'cpu_over_budget': False,
    'memory_over_budget': False,
    'profiling_enabled': True
}
```

**Example:**
```python
from core.observability.sidecar import get_resource_monitor

monitor = get_resource_monitor()
resources = monitor.check_resources()

if resources['cpu_over_budget']:
    print("WARNING: CPU usage over budget!")
```

---

## Fail-Open Decorator

### `@safe_observe(operation_name: str)`

Decorator that catches all exceptions and never blocks execution.

**Features:**
- Catches all exception types
- Logs errors with structured logging
- Tracks error metrics
- Returns None on failure
- Never propagates exceptions

**Example:**
```python
from core.observability.sidecar import safe_observe

@safe_observe('process_test_result')
def process_result(test_result):
    # This function will never crash the caller
    # Even if it raises any exception
    risky_operation(test_result)
    return "success"

# Calling this is always safe
result = process_result(test_data)  # Returns None if error occurs
```

---

## Configuration

All sidecar settings are configured via `crossbridge.yml`:

```yaml
crossbridge:
  sidecar:
    enabled: true
    
    fail_open:
      enabled: true
      log_errors: true
    
    queue:
      max_size: 5000
      drop_on_full: true
    
    sampling:
      rates:
        events: 0.1      # 10% of events
        logs: 0.05       # 5% of logs
        profiling: 0.01  # 1% of profiling data
        metrics: 1.0     # 100% of metrics
    
    resources:
      max_cpu_percent: 5.0   # 5% CPU budget
      max_memory_mb: 100     # 100MB RAM budget
    
    health:
      enabled: true
      port: 9090
    
    metrics:
      enabled: true
      format: prometheus
```

---

## Error Handling

All errors are handled gracefully:

1. **Queue Full** - Events are dropped with metrics tracking
2. **Resource Over Budget** - Profiling is auto-disabled
3. **Exception in Observer** - Caught by @safe_observe, never propagates
4. **Health Endpoint Failure** - Returns 503 with error details

**Structured Error Logging:**
```json
{
  "level": "warning",
  "logger": "core.observability.sidecar",
  "message": "sidecar_error",
  "operation": "process_event",
  "error_type": "ValueError",
  "error_message": "Invalid event format",
  "function": "process_event",
  "timestamp": "2026-01-31T10:00:00Z"
}
```

---

## Integration Examples

### With pytest

```python
# conftest.py
import pytest
from core.observability.sidecar import get_event_queue, safe_observe

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item):
    queue = get_event_queue()
    
    # Log test start
    queue.put({
        'type': 'test_start',
        'test_id': item.nodeid,
        'timestamp': time.time()
    })
    
    yield
    
    # Log test end (in @safe_observe context)
```

### With Robot Framework

```robot
*** Settings ***
Library    SidecarObserver.py

*** Test Cases ***
Example Test
    [Setup]    Sidecar.Start Observation    test_name=${TEST NAME}
    # Your test steps here
    [Teardown]    Sidecar.Stop Observation
```

### With JUnit (Java)

```java
@Rule
public SidecarObserver observer = new SidecarObserver();

@Test
public void testExample() {
    observer.recordEvent("test_start", testName);
    // Your test code
    observer.recordEvent("test_end", testName);
}
```

---

## Performance Characteristics

- **Throughput**: 5000 events/second (with sampling)
- **Latency**: <1ms per event (queue put/get)
- **Memory**: ~100MB baseline, +20MB per 1000 queued events
- **CPU**: <5% under normal load, <2% with sampling
- **Queue Capacity**: 5000 events before load shedding

---

## Troubleshooting

### Events Being Dropped

**Symptom:** `sidecar_events_dropped` metric increasing

**Solutions:**
1. Increase queue size in config
2. Increase sampling rate (sample less)
3. Speed up event processing
4. Check for event floods

### High CPU Usage

**Symptom:** CPU >5%, profiling auto-disabled

**Solutions:**
1. Increase CPU budget in config
2. Increase sampling rate
3. Reduce event processing complexity
4. Check for tight loops

### Health Endpoint Returns 503

**Symptom:** `/health` returns "degraded" or "down"

**Causes:**
- Queue >80% full → Increase queue size or sampling
- Errors >10 → Check error logs
- Resources over budget → Adjust budgets or reduce load

---

## See Also

- [Sidecar Hardening Guide](TEST_INFRASTRUCTURE_AND_SIDECAR_HARDENING.md)
- [Health Monitoring Best Practices](../observability/HEALTH_MONITORING.md)
- [Prometheus Integration](../observability/PROMETHEUS_INTEGRATION.md)

---

**Generated:** January 31, 2026  
**API Version:** v0.2.0  
**Status:** ✅ Production Ready
