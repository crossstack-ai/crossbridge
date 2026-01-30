# JSON Structured Log Adapter

## Overview

The JSON Structured Log Adapter provides unified ingestion and analysis of application logs alongside test execution logs. This enables comprehensive correlation between test failures and application behavior, providing deeper insights into failure root causes.

**Key Capabilities:**
- Universal JSON log format support (ELK, Fluentd, Kubernetes, CloudWatch, custom)
- Automatic signal extraction (errors, timeouts, retries, circuit breakers)
- Multi-strategy correlation (trace ID, execution ID, timestamp, service)
- Intelligent sampling with rate limiting
- PostgreSQL persistent storage
- Extensible adapter registry

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Log Ingestion Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Raw Logs → Adapter Registry → JSON Adapter → Normalized    │
│              (format detection)   (parsing)     Schema       │
│                                                              │
│  Normalized Logs → Signal Extraction → Sampling             │
│                    (error/perf analysis) (rate limiting)     │
│                                                              │
│  Sampled Logs → Correlation → Storage                       │
│                 (with test events)  (PostgreSQL)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Normalized Schema

All log formats are normalized to a canonical structure:

```python
@dataclass
class NormalizedLogEvent:
    # Core fields
    timestamp: datetime
    level: LogLevel  # DEBUG, INFO, WARN, ERROR, FATAL
    message: str
    
    # Service identification
    service: Optional[str]
    component: Optional[str]
    
    # Error tracking
    error_type: Optional[str]
    exception_class: Optional[str]
    stack_trace: Optional[str]
    
    # Distributed tracing
    trace_id: Optional[str]
    span_id: Optional[str]
    parent_span_id: Optional[str]
    
    # Infrastructure
    host: Optional[str]
    container_id: Optional[str]
    pod_name: Optional[str]
    
    # Application context
    user_id: Optional[str]
    request_id: Optional[str]
    session_id: Optional[str]
    
    # Performance
    duration_ms: Optional[float]
    response_code: Optional[int]
    
    # Original data (never lost)
    raw: Dict[str, Any]
    metadata: Dict[str, Any]
```

---

## Quick Start

### 1. Enable Log Ingestion

Edit `crossbridge.yml`:

```yaml
execution:
  log_ingestion:
    enabled: true
    
    adapters:
      json:
        enabled: true
```

### 2. Feed Logs to Adapter

```python
from core.execution.intelligence.log_adapters import get_registry

# Get JSON adapter
registry = get_registry()
adapter = registry.get_adapter('application.log')

# Parse logs
with open('application.log') as f:
    for line in f:
        log_event = adapter.parse(line)
        if log_event:
            print(f"Parsed: {log_event['level']} - {log_event['message']}")
```

### 3. Correlate with Test Events

```python
from core.execution.intelligence.log_adapters.correlation import LogCorrelator

correlator = LogCorrelator()

# Correlate test event with application logs
result = correlator.correlate(test_event, app_logs)

print(f"Found {len(result.correlated_logs)} correlated logs")
print(f"Correlation method: {result.correlation_method}")
print(f"Confidence: {result.correlation_confidence}")
```

---

## Supported Log Formats

### 1. Standard JSON

```json
{
  "timestamp": "2024-01-30T10:30:00Z",
  "level": "ERROR",
  "message": "Database connection timeout",
  "service": "payment-api",
  "component": "DatabasePool",
  "error_type": "TimeoutError",
  "trace_id": "abc123",
  "host": "prod-server-01"
}
```

### 2. ELK/Elasticsearch

```json
{
  "@timestamp": "2024-01-30T10:30:00.000Z",
  "severity": "error",
  "message": "Database connection timeout",
  "service.name": "payment-api",
  "logger_name": "DatabasePool"
}
```

### 3. Fluentd/FluentBit

```json
{
  "time": 1706612400,
  "log_level": "error",
  "msg": "Database connection timeout",
  "app": "payment-api"
}
```

### 4. Kubernetes Container Logs

```json
{
  "timestamp": "2024-01-30T10:30:00Z",
  "stream": "stderr",
  "log": "ERROR: Database connection timeout",
  "kubernetes": {
    "pod_name": "payment-api-7d5f4b8c9-xz4wq",
    "container_name": "payment-api",
    "namespace": "production"
  }
}
```

---

## Configuration

### Complete Configuration (crossbridge.yml)

```yaml
execution:
  log_ingestion:
    enabled: true
    
    # Adapters
    adapters:
      json:
        enabled: true
        field_mapping: {}  # Custom overrides (see below)
    
    # Sampling
    sampling:
      enabled: true
      rates:
        debug: 0.01   # 1% of DEBUG logs
        info: 0.01    # 1% of INFO logs
        warn: 0.1     # 10% of WARN logs
        error: 1.0    # 100% of ERROR logs
        fatal: 1.0    # 100% of FATAL logs
      max_events_per_second: 1000
      adaptive: true
      adaptation_window: 60
      # Pattern-based sampling
      # always_sample_patterns:
      #   - "critical"
      #   - "payment.*failed"
      # never_sample_patterns:
      #   - "health.*check"
    
    # Correlation
    correlation:
      enabled: true
      strategies:
        - trace_id      # Confidence: 1.0
        - execution_id  # Confidence: 0.9
        - timestamp     # Confidence: 0.7
        - service       # Confidence: 0.5
      timestamp_window: 5  # seconds
    
    # Storage
    storage:
      enabled: true
      backend: postgresql
      batch_size: 100
      batch_timeout: 5
    
    # Signal extraction
    signals:
      enabled: true
      extract:
        - error_occurrence
        - error_type
        - timeout_indicator
        - retry_indicator
        - circuit_breaker
        - performance_metric
        - message_entropy
```

### Custom Field Mapping

For non-standard JSON formats, customize field mapping:

```yaml
execution:
  log_ingestion:
    adapters:
      json:
        enabled: true
        field_mapping:
          timestamp_fields:
            - "event_time"
            - "created_at"
          level_fields:
            - "log_severity"
            - "priority"
          message_fields:
            - "log_text"
            - "event_message"
          service_fields:
            - "application_name"
          component_fields:
            - "module_name"
```

---

## Correlation Strategies

The log correlator uses multiple strategies to match application logs with test events:

### 1. Trace ID Correlation (Confidence: 1.0)

**Best:** Perfect match via distributed tracing ID

```python
# Test event metadata contains trace_id
test_event.metadata = {'trace_id': 'trace-abc123'}

# Application log contains same trace_id
app_log = {"trace_id": "trace-abc123", "message": "Payment failed"}

# Result: Perfect correlation
```

### 2. Execution ID Correlation (Confidence: 0.9)

**Good:** Match via test execution ID

```python
# Test event has execution_id
test_event.execution_id = "test-run-789"

# Application logs tagged with same execution_id
app_log = {"execution_id": "test-run-789", "message": "API call"}
```

### 3. Timestamp Window Correlation (Confidence: 0.7)

**Moderate:** Match logs within time window (±5 seconds default)

```python
# Test event timestamp
test_event.timestamp = "2024-01-30T10:30:00Z"

# Application logs within ±5 seconds
app_log = {"timestamp": "2024-01-30T10:30:03Z", "message": "Error"}
```

### 4. Service Name Correlation (Confidence: 0.5)

**Weak:** Match by service name only

```python
# Test event metadata contains service
test_event.metadata = {'service': 'payment-api'}

# Application log from same service
app_log = {"service": "payment-api", "message": "Connection error"}
```

---

## Signal Extraction

Automatic extraction of actionable signals from logs:

### Error Signals

```python
extracted_signals = adapter.extract_signals(log_event)

# Error indicators
is_error: bool              # ERROR or FATAL level
is_timeout: bool            # "timeout" in message
is_retry: bool              # "retry" or "retrying" in message
is_circuit_breaker: bool    # "circuit breaker" in message

# Error categorization
error_category: str
# - "network": connection, socket, network errors
# - "database": SQL, connection pool, query timeout
# - "authentication": auth, unauthorized, forbidden
# - "null_reference": NullPointerException, AttributeError
# - "application": other errors
```

### Performance Signals

```python
# Slow operations
is_slow: bool              # duration > 5 seconds
duration_ms: Optional[float]

# Message characteristics
message_length: int
message_entropy: float     # Information density
```

---

## Sampling

High-volume log management with intelligent sampling:

### Level-Based Sampling

```python
# Default sampling rates
DEBUG: 1%    # Sample 1 in 100 debug logs
INFO:  1%    # Sample 1 in 100 info logs
WARN:  10%   # Sample 1 in 10 warnings
ERROR: 100%  # Keep ALL errors
FATAL: 100%  # Keep ALL fatal errors
```

### Rate Limiting

```python
# Enforce maximum events per second
max_events_per_second: 1000

# If exceeded, additional logs are dropped
# ERROR and FATAL logs are always preserved
```

### Adaptive Sampling

Automatically reduces sampling rates under high load:

```python
# Monitor system load over 60-second window
adaptation_window: 60

# High load (>80%): Reduce sampling by 50%
# Medium load (>60%): Reduce sampling by 25%
# ERROR/FATAL: Never reduced
```

### Pattern-Based Sampling

```yaml
# Always sample (whitelist)
always_sample_patterns:
  - "critical"
  - "payment.*failed"
  - "security.*alert"

# Never sample (blacklist)
never_sample_patterns:
  - "health.*check"
  - "heartbeat"
  - "ping"
```

---

## Storage

### PostgreSQL Schema

```sql
CREATE TABLE application_logs (
    id BIGSERIAL PRIMARY KEY,
    
    -- Timestamps
    timestamp TIMESTAMP NOT NULL,
    ingested_at TIMESTAMP DEFAULT NOW(),
    
    -- Core fields
    level TEXT,
    service TEXT,
    component TEXT,
    message TEXT,
    
    -- Error tracking
    error_type TEXT,
    exception_class TEXT,
    stack_trace TEXT,
    
    -- Distributed tracing
    trace_id TEXT,
    span_id TEXT,
    parent_span_id TEXT,
    
    -- Infrastructure
    host TEXT,
    container_id TEXT,
    pod_name TEXT,
    
    -- Application context
    user_id TEXT,
    request_id TEXT,
    session_id TEXT,
    
    -- Performance
    duration_ms DOUBLE PRECISION,
    response_code INTEGER,
    
    -- JSONB (flexible querying)
    raw JSONB,
    metadata JSONB
);

-- Indexes for performance
CREATE INDEX idx_app_logs_timestamp ON application_logs(timestamp);
CREATE INDEX idx_app_logs_level ON application_logs(level);
CREATE INDEX idx_app_logs_service ON application_logs(service);
CREATE INDEX idx_app_logs_trace_id ON application_logs(trace_id);
CREATE INDEX idx_app_logs_error_type ON application_logs(error_type);
CREATE INDEX idx_app_logs_request_id ON application_logs(request_id);
```

### Batch Insert Optimization

```python
from core.execution.intelligence.log_adapters.storage import LogStorage

storage = LogStorage(session)

# Batch insert for performance
log_events = [...]  # List of normalized log events
count = storage.store_batch(log_events)
print(f"Inserted {count} logs")
```

### Querying

```python
# Query by trace ID
logs = storage.query_by_trace_id('trace-abc123')

# Query by service and time range
logs = storage.query_by_service(
    'payment-api',
    start_time=datetime(2024, 1, 30, 10, 0),
    end_time=datetime(2024, 1, 30, 11, 0)
)

# Query errors
errors = storage.query_errors(
    start_time=datetime(2024, 1, 30),
    end_time=datetime(2024, 1, 31),
    limit=1000
)
```

---

## Framework Compatibility

The JSON log adapter is compatible with all CrossBridge-supported frameworks:

| Framework | Compatibility | Notes |
|-----------|---------------|-------|
| **Rest Assured (Java)** | ✅ Full | Log4j/SLF4J JSON appenders |
| **Cypress** | ✅ Full | Winston JSON transport |
| **Playwright** | ✅ Full | Node.js JSON logging |
| **Pytest BDD** | ✅ Full | Python JSON formatter |
| **Robot Framework** | ✅ Full | Custom JSON listener |
| **Selenium (Java)** | ✅ Full | Log4j JSON appenders |
| **SpecFlow (.NET)** | ✅ Full | Serilog JSON formatter |
| **TestNG** | ✅ Full | Log4j JSON appenders |
| **Cucumber** | ✅ Full | Logback JSON encoder |
| **Karate** | ✅ Full | Log4j JSON appenders |
| **WebdriverIO** | ✅ Full | Winston JSON transport |
| **Nightwatch** | ✅ Full | Node.js JSON logging |

---

## Advanced Usage

### Custom Adapter Registration

```python
from core.execution.intelligence.log_adapters import BaseLogAdapter, get_registry

class CustomLogAdapter(BaseLogAdapter):
    def can_handle(self, source: str) -> bool:
        return source.endswith('.custom')
    
    def parse(self, raw_line: str) -> Optional[dict]:
        # Custom parsing logic
        pass
    
    def extract_signals(self, log_event: dict) -> dict:
        # Custom signal extraction
        pass

# Register custom adapter
registry = get_registry()
registry.register(CustomLogAdapter())
```

### Correlation with Batch Processing

```python
from core.execution.intelligence.log_adapters.correlation import LogCorrelator

correlator = LogCorrelator()

# Correlate multiple test events at once
results = correlator.correlate_batch(test_events, app_logs)

# Get statistics
stats = correlator.get_correlation_stats(results)
print(f"Average correlated logs: {stats['avg_correlated_logs']}")
print(f"Correlation rate: {stats['correlation_rate']*100}%")
```

### Sampling Statistics

```python
from core.execution.intelligence.log_adapters.sampling import LogSampler, SamplingConfig

config = SamplingConfig(debug_rate=0.01, info_rate=0.01)
sampler = LogSampler(config)

# Sample logs
for log in logs:
    if sampler.should_sample(log['level'], log):
        # Process sampled log
        pass

# Get statistics
stats = sampler.get_statistics()
print(f"Total events: {stats['total_events']}")
print(f"Sampled events: {stats['sampled_events']}")
print(f"Overall sampling rate: {stats['overall_sampling_rate']}")
```

---

## Troubleshooting

### Issue: Logs not being parsed

**Symptoms:**
- `adapter.parse()` returns `None`
- No logs in database

**Solutions:**
1. Verify JSON format is valid
2. Check custom field mapping configuration
3. Enable debug logging:
   ```python
   import logging
   logging.getLogger('core.execution.intelligence.log_adapters').setLevel(logging.DEBUG)
   ```

### Issue: Correlation not finding logs

**Symptoms:**
- `correlate()` returns empty `correlated_logs` list
- Correlation confidence is 0.0

**Solutions:**
1. Verify trace_id in test event metadata
2. Check timestamp window configuration
3. Ensure logs are within time window (±5 seconds default)
4. Verify service names match

### Issue: Too many/few logs being sampled

**Symptoms:**
- Database filling up too quickly
- Missing important ERROR logs

**Solutions:**
1. Adjust sampling rates in `crossbridge.yml`
2. Add pattern-based sampling:
   ```yaml
   always_sample_patterns: ["critical", "payment"]
   never_sample_patterns: ["health", "heartbeat"]
   ```
3. Enable adaptive sampling:
   ```yaml
   sampling:
     adaptive: true
     adaptation_window: 60
   ```

### Issue: Timestamp parsing errors

**Symptoms:**
- Logs have current timestamp instead of original
- `Failed to parse timestamp` warnings

**Solutions:**
1. Add custom timestamp fields:
   ```yaml
   field_mapping:
     timestamp_fields: ["event_time", "created_at"]
   ```
2. Verify timestamp format (ISO 8601 or Unix timestamp)
3. Check timezone handling (should be UTC)

---

## Performance Considerations

### Ingestion Rate

- **Target:** 1000 events/second
- **Batch Size:** 100 logs per insert
- **Database:** Use PostgreSQL connection pooling
- **Sampling:** Enable adaptive sampling for high-volume environments

### Memory Usage

- **Batch Processing:** Process logs in batches of 100-1000
- **Correlation:** Use timestamp-based windowing to limit search space
- **Storage:** Set up log rotation and archival policies

### Scalability

- **Horizontal:** Multiple ingestion workers with shared PostgreSQL
- **Vertical:** Increase PostgreSQL resources for high write throughput
- **Partitioning:** Partition `application_logs` table by timestamp

---

## Integration Examples

### Example 1: Pytest Test with Application Logs

```python
import pytest
from core.execution.intelligence.log_adapters import get_registry
from core.execution.intelligence.log_adapters.correlation import LogCorrelator

@pytest.fixture
def app_logs():
    """Load application logs for correlation."""
    registry = get_registry()
    adapter = registry.get_adapter('app.log')
    
    logs = []
    with open('app.log') as f:
        for line in f:
            log = adapter.parse(line)
            if log:
                logs.append(log)
    return logs

def test_payment_processing(app_logs):
    # Execute test
    result = process_payment()
    
    # Correlate with application logs
    correlator = LogCorrelator()
    correlation = correlator.correlate(
        test_event=result.test_event,
        app_logs=app_logs
    )
    
    # Analyze correlated logs
    if not result.success:
        errors = [log for log in correlation.correlated_logs 
                  if log['level'] == 'ERROR']
        pytest.fail(f"Payment failed with {len(errors)} errors")
```

### Example 2: Continuous Log Ingestion

```python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from core.execution.intelligence.log_adapters import get_registry

class LogFileHandler(FileSystemEventHandler):
    def __init__(self):
        self.registry = get_registry()
        self.adapter = self.registry.get_adapter('app.log')
    
    def on_modified(self, event):
        if event.src_path.endswith('.log'):
            with open(event.src_path) as f:
                for line in f:
                    log = self.adapter.parse(line)
                    if log:
                        # Process log event
                        self.process_log(log)
    
    def process_log(self, log):
        # Store, correlate, analyze
        pass

# Watch log directory
observer = Observer()
observer.schedule(LogFileHandler(), '/var/log/app', recursive=True)
observer.start()
```

---

## API Reference

See module docstrings for detailed API documentation:

- [BaseLogAdapter](../../core/execution/intelligence/log_adapters/__init__.py)
- [JSONLogAdapter](../../core/execution/intelligence/log_adapters/json_adapter.py)
- [LogCorrelator](../../core/execution/intelligence/log_adapters/correlation.py)
- [LogSampler](../../core/execution/intelligence/log_adapters/sampling.py)
- [LogStorage](../../core/execution/intelligence/log_adapters/storage.py)
- [NormalizedLogEvent](../../core/execution/intelligence/log_adapters/schema.py)

---

## Contributing

To add support for a new log format:

1. Implement `BaseLogAdapter` interface
2. Register adapter with `get_registry().register(adapter)`
3. Add tests in `tests/unit/log_adapters/`
4. Update this documentation

---

## License

Copyright © 2024 CrossStack/CrossBridge. All rights reserved.
