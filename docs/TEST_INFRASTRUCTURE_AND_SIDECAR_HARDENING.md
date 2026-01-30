# CrossBridge Test Infrastructure & Sidecar Hardening

## Overview

This document describes the **consistent test suite** and **hardened sidecar observer** implemented for CrossBridge. These additions ensure:

1. **Deterministic Testing**: Golden fixtures, adapter contracts, and repeatable tests
2. **Resilient Observability**: Fail-open sidecar that never blocks test execution
3. **Bounded Resources**: CPU/memory budgets, load shedding, and sampling
4. **Full Observability**: Metrics, health endpoints, and structured logging

---

## Table of Contents

- [Test Infrastructure](#test-infrastructure)
  - [Test Pyramid](#test-pyramid)
  - [Golden Fixtures](#golden-fixtures)
  - [Adapter Contracts](#adapter-contracts)
  - [CI Configuration](#ci-configuration)
- [Sidecar Observer Hardening](#sidecar-observer-hardening)
  - [Architecture](#architecture)
  - [Fail-Open Execution](#fail-open-execution)
  - [Bounded Queues](#bounded-queues)
  - [Sampling](#sampling)
  - [Resource Monitoring](#resource-monitoring)
  - [Health Endpoints](#health-endpoints)
  - [Structured Logging](#structured-logging)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Testing](#testing)

---

## Test Infrastructure

### Test Pyramid

CrossBridge follows a **70-25-5 test pyramid**:

```
     /\
    /E2\     5% E2E Tests (Smoke tests, full integration)
   /────\
  / Integ\   25% Integration Tests (Sidecar, adapters)
 /────────\
/ Unit     \ 70% Unit Tests (Core logic, fixtures, contracts)
──────────── 
```

**Test Distribution:**
- **Unit Tests** (70%): `tests/unit/`
- **Integration Tests** (25%): `tests/integration/`
- **E2E Tests** (5%): `tests/e2e/`

**Coverage Requirement:** 70% minimum (enforced in CI)

### Golden Fixtures

**Location:** `tests/fixtures/`

Golden fixtures provide **deterministic, repeatable test data** with:
- ✅ Fixed timestamps (`2026-01-31T10:00:00Z`)
- ✅ No randomness
- ✅ No environment-specific data
- ✅ Consistent structure

**Available Fixtures:**

#### Sample Tests (`tests/fixtures/sample_tests.py`)
10 fixtures covering different test frameworks:

```python
from tests.fixtures import sample_test, sample_pytest_test, sample_selenium_test

# Basic test
test = sample_test()
# {'name': 'test_valid_login', 'framework': 'pytest', 'status': 'passed', ...}

# Selenium test with locators
selenium_test = sample_selenium_test()
# Includes locators: [{'type': 'ID', 'value': 'username'}, ...]

# Batch of 20 tests
batch = sample_test_batch()
# [test1, test2, ..., test20]
```

#### Sample Scenarios (`tests/fixtures/sample_scenarios.py`)
7 complete test scenarios:

```python
from tests.fixtures import sample_login_scenario, sample_e2e_scenario

# Multi-case login
login = sample_login_scenario()
# Includes valid/invalid/empty cases

# Complete E2E user journey
e2e = sample_e2e_scenario()
# 5 phases: Registration, Discovery, Shopping, Checkout, Post-Purchase
```

#### Sample Failures (`tests/fixtures/sample_failures.py`)
10 canonical failure patterns:

```python
from tests.fixtures import sample_timeout_failure, sample_flaky_failure

# Timeout failure
timeout = sample_timeout_failure()
# {'failure_type': 'ENVIRONMENT_ISSUE', 'error_type': 'TimeoutError', ...}

# Flaky test (30% failure rate)
flaky = sample_flaky_failure()
# Includes failure history: {'total_runs': 10, 'failures': 3, ...}
```

### Adapter Contracts

**Location:** `tests/unit/adapters/test_adapter_contract.py`

Adapter contracts ensure **all adapters implement required interfaces** consistently.

**Base Contract:**
```python
class AdapterContract(ABC):
    @abstractmethod
    def extract_tests(source_path: str) -> List[Dict[str, Any]]
    
    @abstractmethod
    def get_framework_name() -> str
    
    def can_handle(file_path: str) -> bool
```

**11 Contract Tests:**
1. `test_adapter_implements_contract` - Has required methods
2. `test_extract_tests_returns_list` - Returns list
3. `test_extract_tests_returns_dicts` - Returns list of dicts
4. `test_extracted_tests_have_required_fields` - Has 'name', 'framework'
5. `test_get_framework_name_returns_string` - Non-empty string
6. `test_can_handle_returns_bool` - Boolean return
7. `test_adapter_handles_appropriate_files` - File filtering
8. `test_extract_tests_is_idempotent` - Same input → same output
9. `test_extract_tests_handles_empty_file` - Graceful handling
10. `test_extract_tests_handles_invalid_file` - No exceptions
11. `test_extracted_tests_have_consistent_structure` - Consistent keys

**Usage:**
```python
from tests.unit.adapters.test_adapter_contract import run_adapter_contract_tests

# Test your adapter
run_adapter_contract_tests(
    adapter=MyAdapter(),
    test_files={
        'sample': '/path/to/sample_test.py',
        'empty': '/path/to/empty.py',
        'invalid': '/path/to/invalid.txt'
    }
)
```

### CI Configuration

**Location:** `.ci/test-configuration.yml`

**CI Pipeline Stages:**
1. **Unit Tests** → Run 70% of tests, check adapter contracts
2. **Integration Tests** → Run 25% of tests, sidecar integration
3. **Chaos Tests** → Stress test sidecar (flood, exhaustion, exceptions)
4. **E2E Tests** → Run 5% smoke tests
5. **Coverage Gate** → Enforce 70% threshold (fail build if below)

**Commands:**
```bash
# Run all tests with coverage
pytest tests/ --cov=core --cov=cli --cov-report=html

# Run unit tests only
pytest tests/unit/ --cov=core --cov-fail-under=70

# Run adapter contracts
pytest tests/unit/adapters/test_adapter_contract.py -v

# Run chaos tests
pytest tests/integration/sidecar/test_sidecar_chaos.py --timeout=60

# Check coverage threshold
coverage report --fail-under=70
```

---

## Sidecar Observer Hardening

### Architecture

The **sidecar observer** is a background monitoring system that:
- ✅ **Never blocks** test execution (fail-open design)
- ✅ **Bounded resources** (5% CPU, 100MB RAM)
- ✅ **Samples events** (10% events, 5% logs, 1% profiling)
- ✅ **Load sheds** when overwhelmed (drop events, not tests)
- ✅ **Fully observable** (Prometheus metrics, health endpoints)

**Key Components:**

```
┌─────────────────────────────────────────────────────────────┐
│                     Test Execution                          │
│                    (Main Process)                           │
└─────────────────┬───────────────────────────────────────────┘
                  │ Events (never blocking)
                  ↓
┌─────────────────────────────────────────────────────────────┐
│                  Sidecar Observer                           │
│  ┌─────────────┐   ┌─────────┐   ┌──────────────────┐     │
│  │   Bounded   │──▶│ Sampler │──▶│   @safe_observe  │     │
│  │    Queue    │   └─────────┘   │  (Fail-Open)     │     │
│  │  (5000 max) │                 └──────────────────┘     │
│  └─────────────┘                           │               │
│        │                                    ↓               │
│        │ Load shedding          ┌──────────────────┐       │
│        ↓                        │  Metrics +       │       │
│   Drop when full               │  Structured Logs  │       │
│                                └──────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                                     │
                                     ↓
                          ┌──────────────────┐
                          │ /health /metrics │
                          │  HTTP Endpoints  │
                          └──────────────────┘
```

### Fail-Open Execution

**Location:** `core/observability/sidecar/__init__.py`

All sidecar operations are wrapped in `@safe_observe` decorator:

```python
from core.observability.sidecar import safe_observe

@safe_observe("event_processing")
def process_event(event):
    # Your processing logic
    # Any exception here will NOT propagate
    return result
```

**Behavior:**
- ✅ Catches **ALL** exceptions
- ✅ Never propagates errors to caller
- ✅ Returns `None` on error (fail-open)
- ✅ Logs errors with structured context
- ✅ Increments `sidecar.{operation}.errors` metric
- ✅ Records duration histogram

### Bounded Queues

**Location:** `core/observability/sidecar/__init__.py`

Event queue with **hard size limit** and **load shedding**:

```python
from core.observability.sidecar import get_event_queue

queue = get_event_queue()

# Non-blocking put (drops if full)
if queue.put(event):
    print("Event queued")
else:
    print("Event dropped (queue full)")

# Queue statistics
stats = queue.get_stats()
# {
#   'current_size': 2341,
#   'max_size': 5000,
#   'utilization': 0.47,
#   'total_events': 12500,
#   'dropped_events': 42
# }
```

**Configuration:**
```yaml
sidecar:
  queue:
    max_size: 5000              # Hard limit
    max_event_age_seconds: 300  # Drop events older than 5 min
    drop_on_full: true          # Load shedding enabled
```

### Sampling

**Location:** `core/observability/sidecar/__init__.py`

**Sampling-first design** reduces processing load:

```python
from core.observability.sidecar import get_sampler

sampler = get_sampler()

if sampler.should_sample('events'):
    process_event(event)  # Only process 10% of events
else:
    # Event sampled out (logged with DEBUG level)
    pass

# Sampling statistics
stats = sampler.get_stats()
# {
#   'events': {
#     'configured_rate': 0.1,
#     'actual_rate': 0.098,
#     'total_events': 10000,
#     'sampled_events': 980
#   }
# }
```

**Configuration:**
```yaml
sidecar:
  sampling:
    rates:
      events: 0.1      # 10%
      logs: 0.05       # 5%
      profiling: 0.01  # 1%
      metrics: 1.0     # 100% (always)
```

### Resource Monitoring

**Location:** `core/observability/sidecar/__init__.py`

**Hard resource budgets** protect main process:

```python
from core.observability.sidecar import get_resource_monitor

monitor = get_resource_monitor()

resources = monitor.check_resources()
# {
#   'cpu_percent': 3.2,
#   'memory_mb': 45.3,
#   'cpu_over_budget': False,
#   'memory_over_budget': False,
#   'profiling_enabled': True
# }

# Auto-disable profiling when CPU > 5%
if resources['cpu_over_budget']:
    # Profiling automatically disabled
    pass
```

**Configuration:**
```yaml
sidecar:
  resources:
    max_cpu_percent: 5.0     # 5% CPU budget
    max_memory_mb: 100       # 100 MB RAM budget
    
    on_cpu_exceeded:
      action: disable_profiling
    
    on_memory_exceeded:
      action: clear_queue
```

### Health Endpoints

**Location:** `core/observability/sidecar/health.py`

**Kubernetes-compatible health checks**:

#### Endpoints

**1. Health Check** - `/health`
```bash
curl http://localhost:9090/health

{
  "status": "ok",              # ok | degraded
  "enabled": true,
  "timestamp": 1706716800.0,
  "queue": {
    "size": 1234,
    "utilization": 0.25,
    "dropped_events": 12
  },
  "resources": {
    "cpu_percent": 3.2,
    "memory_mb": 45.3,
    "profiling_enabled": true
  },
  "metrics": {
    "total_events": 50000,
    "total_errors": 42,
    "error_rate": 0.0008,
    "avg_latency_ms": 2.3
  },
  "issues": []                 # ["queue_near_capacity", "cpu_over_budget"]
}
```

**2. Readiness Probe** - `/ready`
```bash
curl http://localhost:9090/ready

{
  "ready": true,               # true | false
  "enabled": true,
  "queue_utilization": 0.25,
  "timestamp": 1706716800.0
}
```

**3. Prometheus Metrics** - `/metrics`
```bash
curl http://localhost:9090/metrics

# TYPE sidecar_events_queued_total counter
sidecar_events_queued_total 50000

# TYPE sidecar_queue_size gauge
sidecar_queue_size 1234

# TYPE sidecar_cpu_usage gauge
sidecar_cpu_usage 3.2

# TYPE sidecar_memory_usage gauge
sidecar_memory_usage 45.3
```

**4. Config Reload** - `/sidecar/config/reload` (POST)
```bash
curl -X POST http://localhost:9090/sidecar/config/reload \
  -H "Content-Type: application/json" \
  -d '{
    "sampling_rates": {"events": 0.05},
    "max_queue_size": 10000
  }'

{
  "status": "ok",
  "message": "Configuration reloaded",
  "config": {...}
}
```

**Start Server:**
```python
from core.observability.sidecar.health import start_http_server

start_http_server(port=9090)
```

### Structured Logging

**Location:** `core/observability/sidecar/logging.py`

**JSON-only logging** with correlation IDs:

```python
from core.observability.sidecar.logging import (
    log_sidecar_event,
    log_event_queued,
    log_error,
    set_run_id,
    set_test_id
)

# Set correlation context
set_run_id('test_run_123')
set_test_id('test_case_456')

# Log event
log_event_queued(event)
# {
#   "timestamp": "2026-01-31T10:00:00Z",
#   "level": "INFO",
#   "logger": "crossbridge.sidecar",
#   "message": "event_queued",
#   "run_id": "test_run_123",
#   "test_id": "test_case_456",
#   "event_type": "test_event",
#   "event_id": "evt_123"
# }

# Log error
log_error("event_processing", ValueError("Invalid event"))
# {
#   "timestamp": "2026-01-31T10:00:01Z",
#   "level": "ERROR",
#   "operation": "event_processing",
#   "error_type": "ValueError",
#   "error_message": "Invalid event",
#   "exception": "Traceback...",
#   ...
# }
```

---

## Configuration

**Location:** `crossbridge.yml`

### Minimal Configuration
```yaml
crossbridge:
  sidecar:
    enabled: true
```

### Production Configuration
```yaml
crossbridge:
  sidecar:
    enabled: true
    
    # Queue
    queue:
      max_size: 5000
      max_event_age_seconds: 300
    
    # Sampling
    sampling:
      rates:
        events: 0.1
        logs: 0.05
        profiling: 0.01
    
    # Resources
    resources:
      max_cpu_percent: 5.0
      max_memory_mb: 100
    
    # Health endpoints
    health:
      enabled: true
      port: 9090
    
    # Metrics
    metrics:
      enabled: true
      format: prometheus
```

### Environment Variables
```bash
# Override sampling rates
export SIDECAR_SAMPLE_EVENTS=0.05     # 5% events
export SIDECAR_SAMPLE_LOGS=0.01       # 1% logs

# Override resource limits
export SIDECAR_MAX_CPU=3.0            # 3% CPU
export SIDECAR_MAX_MEMORY=50          # 50 MB

# Override queue size
export SIDECAR_QUEUE_SIZE=10000       # 10K events

# Override health port
export SIDECAR_HEALTH_PORT=8080       # Port 8080

# Logging level
export SIDECAR_LOG_LEVEL=DEBUG        # DEBUG logs
```

---

## Usage Examples

### Basic Event Processing
```python
from core.observability.sidecar import (
    get_event_queue,
    get_sampler,
    safe_observe
)

# Queue event
queue = get_event_queue()
event = {'type': 'test_event', 'id': 'test_1', 'data': {...}}
queue.put(event)

# Process with sampling and fail-open
sampler = get_sampler()

@safe_observe("test_processing")
def process_test_event(evt):
    if sampler.should_sample('events'):
        # Process event (only 10% processed)
        return analyze_event(evt)
    return None

# Drain queue
while queue.size() > 0:
    evt = queue.get(timeout=1.0)
    if evt:
        process_test_event(evt)
```

### Resource Monitoring
```python
from core.observability.sidecar import get_resource_monitor

monitor = get_resource_monitor()

# Check resources
resources = monitor.check_resources()

if resources['cpu_over_budget']:
    print("⚠️  CPU over budget, profiling disabled")

if resources['memory_over_budget']:
    print("⚠️  Memory over budget")
```

### Health Monitoring
```python
from core.observability.sidecar.health import get_health_status

health = get_health_status()

if health['status'] == 'degraded':
    print(f"⚠️  Sidecar degraded: {health['issues']}")
    
    if 'queue_near_capacity' in health['issues']:
        # Queue is >90% full
        pass
    
    if 'high_error_rate' in health['issues']:
        # Error rate >10%
        pass
```

### Correlation Tracking
```python
from core.observability.sidecar.logging import (
    set_run_id,
    set_test_id,
    log_sidecar_event,
    clear_context
)

# Start of test run
set_run_id('run_123')

# Start of test case
set_test_id('test_login')

# All logs now include run_id and test_id
log_sidecar_event('test_started', test_name='test_login')

# End of test case
clear_context()
```

---

## Testing

### Run All Tests
```bash
pytest tests/ --cov=core --cov-report=html
```

### Run Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Adapter Contract Tests
```bash
pytest tests/unit/adapters/test_adapter_contract.py -v
```

### Run Integration Tests
```bash
pytest tests/integration/ -v
```

### Run Chaos Tests
```bash
pytest tests/integration/sidecar/test_sidecar_chaos.py --timeout=60 -v
```

### Run Smoke Tests
```bash
pytest tests/e2e/test_smoke.py -v
```

### Check Coverage
```bash
pytest tests/ --cov=core --cov-fail-under=70
coverage report --fail-under=70
```

### Generate Coverage Report
```bash
coverage html
# Open htmlcov/index.html
```

---

## Key Metrics

**Sidecar Metrics Emitted:**

| Metric | Type | Description |
|--------|------|-------------|
| `sidecar.{operation}.success` | Counter | Successful operations |
| `sidecar.{operation}.errors` | Counter | Failed operations |
| `sidecar.{operation}.duration_ms` | Histogram | Operation duration |
| `sidecar.events_queued` | Counter | Events queued |
| `sidecar.events_processed` | Counter | Events processed |
| `sidecar.events_dropped` | Counter | Events dropped (queue full) |
| `sidecar.events_sampled_out` | Counter | Events filtered by sampling |
| `sidecar.queue_size` | Gauge | Current queue size |
| `sidecar.cpu_usage` | Gauge | CPU percentage |
| `sidecar.memory_usage` | Gauge | Memory MB |
| `sidecar.profiling_disabled` | Counter | Profiling auto-disabled |

---

## Troubleshooting

### High Queue Utilization
```yaml
# Increase queue size
sidecar:
  queue:
    max_size: 10000  # Double the size

# Or increase sampling
sidecar:
  sampling:
    rates:
      events: 0.05  # Reduce to 5%
```

### High CPU Usage
```yaml
# Lower CPU budget triggers faster
sidecar:
  resources:
    max_cpu_percent: 3.0  # Stricter budget

# Or increase sampling
sidecar:
  sampling:
    rates:
      profiling: 0.005  # Reduce to 0.5%
```

### High Error Rate
Check structured logs:
```bash
# Filter sidecar errors
cat logs/crossbridge.log | jq 'select(.logger == "crossbridge.sidecar" and .level == "ERROR")'
```

Check metrics:
```bash
curl http://localhost:9090/metrics | grep errors
```

### Sidecar Not Starting
Check health endpoint:
```bash
curl http://localhost:9090/health
```

Check configuration:
```python
from core.observability.sidecar import get_config
print(get_config())
```

---

## Architecture Decisions

### Why Fail-Open?
**Test execution MUST never be blocked by observability failures.**

❌ **Fail-Closed** (bad):
```python
def observe_event(event):
    # If this fails, test fails
    storage.save(event)
```

✅ **Fail-Open** (good):
```python
@safe_observe("event_storage")
def observe_event(event):
    # If this fails, test continues
    storage.save(event)
```

### Why Bounded Queues?
**Prevent memory exhaustion from unbounded event accumulation.**

Without bounds: 1M events = ~100MB memory → OOM crash  
With bounds: 5K events max = ~500KB memory → load shedding

### Why Sampling?
**Process only what's needed for insights, not everything.**

Without sampling: 100K events/min → 100% overhead  
With sampling (10%): 10K events/min → 10% overhead

### Why Structured Logging?
**Machine-parseable logs enable automated analysis and indexing.**

❌ **Text logs** (bad):
```
[INFO] Event queued: test_1 for run test_run_123
```

✅ **JSON logs** (good):
```json
{
  "level": "INFO",
  "message": "event_queued",
  "event_id": "test_1",
  "run_id": "test_run_123"
}
```

---

## Next Steps

1. **Enable in Production:**
   ```yaml
   crossbridge:
     sidecar:
       enabled: true
   ```

2. **Set Up Monitoring:**
   - Add Prometheus scrape target: `http://localhost:9090/metrics`
   - Configure Kubernetes probes:
     - `livenessProbe`: `http://localhost:9090/health`
     - `readinessProbe`: `http://localhost:9090/ready`

3. **Review Metrics:**
   - Check Grafana dashboard for sidecar metrics
   - Set alerts on high error rates (>10%)
   - Set alerts on high queue utilization (>90%)

4. **Tune Configuration:**
   - Adjust sampling rates based on load
   - Adjust queue size based on throughput
   - Adjust resource budgets based on environment

---

## Summary

✅ **Deterministic Testing**: Golden fixtures, adapter contracts, repeatable tests  
✅ **Fail-Open Design**: Errors never block test execution  
✅ **Bounded Resources**: 5% CPU, 100MB RAM, 5K event queue  
✅ **Sampling-First**: 10% events, 5% logs, 1% profiling  
✅ **Load Shedding**: Drop events when overwhelmed  
✅ **Full Observability**: Prometheus metrics, health endpoints, structured logs  
✅ **Configuration Reload**: Update config without restart  
✅ **70% Coverage**: Enforced in CI with test pyramid  

**Result**: A resilient, low-overhead sidecar observer that extends CrossBridge's observability without impacting test execution.
