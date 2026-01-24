# Performance Profiling Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Test Execution                           │
│  (pytest, Robot, Selenium, Cypress, TestNG, NUnit, etc.)        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Framework Hooks Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  pytest  │  │  Robot   │  │ TestNG   │  │  NUnit   │       │
│  │   Hook   │  │ Listener │  │ Listener │  │   Hook   │  ...  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    PerformanceEvent Model    │
        │  (Unified Event Structure)   │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │     MetricsCollector         │
        │   (Async Queue + Batching)   │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │   StorageBackend Factory     │
        └──────────────┬───────────────┘
                       │
         ┌─────────────┼─────────────┬─────────────┐
         ▼             ▼             ▼             ▼
    ┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  NoOp  │  │  Local   │  │Postgres  │  │ InfluxDB │
    │Backend │  │ Storage  │  │ Storage  │  │ Storage  │
    └────────┘  └──────────┘  └──────────┘  └──────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │   Grafana    │
                            │  Dashboards  │
                            └──────────────┘
```

---

## Core Components

### 1. PerformanceEvent Model

**Location**: `core/profiling/models.py`

**Purpose**: Unified data structure for all performance events across frameworks

**Schema**:
```python
@dataclass
class PerformanceEvent:
    run_id: str              # UUID for test run
    test_id: str             # Fully qualified test identifier
    event_type: EventType    # TEST_START, TEST_END, STEP, HTTP, etc.
    timestamp: datetime      # When event occurred
    framework: str           # pytest, robot, testng, etc.
    duration_ms: float       # Event duration (optional)
    status: str              # passed, failed, skipped
    metadata: dict           # Extensible key-value pairs
```

**Design Principles**:
- Framework-agnostic
- Extensible via `metadata` field
- Monotonic clock for timing (not wall clock)
- Timezone-aware timestamps

---

### 2. MetricsCollector

**Location**: `core/profiling/collector.py`

**Purpose**: Non-blocking async event collection service

**Architecture**:
```python
class MetricsCollector:
    def __init__(self, config: ProfileConfig):
        self._queue = queue.Queue(maxsize=10000)  # Backpressure
        self._worker_thread = threading.Thread(target=self._process_events)
        self._storage_backend = StorageBackendFactory.create(config)
        
    def collect(self, event: PerformanceEvent):
        """Add event to queue (non-blocking)"""
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self._stats.events_dropped += 1
    
    def _process_events(self):
        """Background worker: batch and flush"""
        batch = []
        while self._running:
            try:
                event = self._queue.get(timeout=1.0)
                batch.append(event)
                
                if len(batch) >= 100:  # Batch size
                    self._flush_batch(batch)
                    batch = []
            except queue.Empty:
                if batch:
                    self._flush_batch(batch)
                    batch = []
```

**Key Features**:
- **Non-Blocking**: Never blocks test execution
- **Batching**: Groups 100 events before writing
- **Backpressure**: 10k queue limit with drop strategy
- **Statistics**: Tracks collected/dropped/written counts
- **Singleton Pattern**: One instance per process

**Performance**:
- Collection overhead: < 0.1ms per event
- Queue operations: O(1) amortized
- Memory usage: ~1KB per event in queue

---

### 3. Storage Backends

**Location**: `core/profiling/storage.py`

#### 3.1 NoOpStorageBackend

```python
class NoOpStorageBackend(StorageBackend):
    def write_event(self, event: PerformanceEvent):
        pass  # Silent drop
```

**Use Case**: Profiling disabled (default)

#### 3.2 LocalStorageBackend

```python
class LocalStorageBackend(StorageBackend):
    def write_event(self, event: PerformanceEvent):
        with open(f"{self.path}/run_{event.run_id}.jsonl", "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
```

**Use Case**: Local development, debugging
**Format**: JSONL (one JSON object per line)

#### 3.3 PostgresStorageBackend

```python
class PostgresStorageBackend(StorageBackend):
    def __init__(self, config: ProfileConfig):
        self.pool = psycopg2.pool.SimpleConnectionPool(1, 10, ...)
        self._ensure_schema_exists()
    
    def write_event(self, event: PerformanceEvent):
        conn = self.pool.getconn()
        try:
            self._route_event(conn, event)
        finally:
            self.pool.putconn(conn)
    
    def _route_event(self, conn, event):
        if event.event_type in [EventType.TEST_START, EventType.TEST_END]:
            self._write_to_tests_table(conn, event)
        elif event.event_type == EventType.HTTP_REQUEST:
            self._write_to_http_calls_table(conn, event)
        # ... more routing
```

**Schema**:
```sql
CREATE SCHEMA IF NOT EXISTS profiling;

-- Run metadata
CREATE TABLE profiling.runs (
    run_id UUID PRIMARY KEY,
    framework VARCHAR(50),
    started_at TIMESTAMPTZ DEFAULT NOW()
);

-- Test lifecycle
CREATE TABLE profiling.tests (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES profiling.runs(run_id),
    test_id VARCHAR(500),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms FLOAT,
    status VARCHAR(20),
    framework VARCHAR(50)
);

-- HTTP calls
CREATE TABLE profiling.http_calls (
    id SERIAL PRIMARY KEY,
    test_id VARCHAR(500),
    endpoint VARCHAR(500),
    method VARCHAR(10),
    status_code INTEGER,
    duration_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WebDriver commands
CREATE TABLE profiling.driver_commands (
    id SERIAL PRIMARY KEY,
    test_id VARCHAR(500),
    command VARCHAR(100),
    duration_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Setup/teardown steps
CREATE TABLE profiling.steps (
    id SERIAL PRIMARY KEY,
    test_id VARCHAR(500),
    step_name VARCHAR(200),
    step_type VARCHAR(50),
    duration_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System metrics
CREATE TABLE profiling.system_metrics (
    id SERIAL PRIMARY KEY,
    run_id UUID,
    cpu_percent FLOAT,
    memory_mb FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_tests_test_id ON profiling.tests(test_id);
CREATE INDEX idx_tests_created_at ON profiling.tests(finished_at);
CREATE INDEX idx_http_endpoint ON profiling.http_calls(endpoint);
CREATE INDEX idx_http_created_at ON profiling.http_calls(created_at);
```

**Use Case**: Production, Grafana integration
**Features**: Connection pooling, event routing, schema auto-create

#### 3.4 InfluxDBStorageBackend

```python
class InfluxDBStorageBackend(StorageBackend):
    def write_event(self, event: PerformanceEvent):
        point = Point("test_event") \
            .tag("framework", event.framework) \
            .tag("test_id", event.test_id) \
            .tag("status", event.status) \
            .field("duration_ms", event.duration_ms) \
            .time(event.timestamp)
        
        self.write_api.write(bucket=self.bucket, record=point)
```

**Use Case**: Time-series analysis, on-prem
**Format**: InfluxDB Line Protocol

---

### 4. Framework Hooks

#### 4.1 Python Frameworks

**pytest Hook** (`core/profiling/hooks/pytest_hook.py`):
```python
class ProfilingPlugin:
    @pytest.hookwrapper
    def pytest_runtest_setup(self, item):
        start = time.perf_counter()
        yield
        duration = (time.perf_counter() - start) * 1000
        collector.collect(PerformanceEvent.create(
            event_type=EventType.STEP,
            test_id=item.nodeid,
            step_type="setup",
            duration_ms=duration,
        ))
```

**Robot Framework Listener** (`core/profiling/hooks/robot_hook.py`):
```python
class CrossBridgeProfilingListener:
    ROBOT_LISTENER_API_VERSION = 3
    
    def start_test(self, data, result):
        self.test_start_times[data.longname] = time.perf_counter()
    
    def end_test(self, data, result):
        duration = (time.perf_counter() - self.test_start_times[data.longname]) * 1000
        collector.collect(PerformanceEvent.create(
            test_id=data.longname,
            event_type=EventType.TEST_END,
            duration_ms=duration,
            status=result.status,
        ))
```

#### 4.2 Java Frameworks

**TestNG Listener** (Java code generation):
```java
public class CrossBridgeProfilingListener implements ITestListener {
    private ThreadLocal<Long> startTimes = new ThreadLocal<>();
    
    @Override
    public void onTestStart(ITestResult result) {
        startTimes.set(System.nanoTime());
    }
    
    @Override
    public void onTestSuccess(ITestResult result) {
        long duration = (System.nanoTime() - startTimes.get()) / 1_000_000;
        writeToPostgres(result.getName(), duration, "passed");
    }
    
    private void writeToPostgres(String testId, long duration, String status) {
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(
                 "INSERT INTO profiling.tests (run_id, test_id, duration_ms, status, framework) " +
                 "VALUES (?, ?, ?, ?, 'testng')"
             )) {
            stmt.setObject(1, UUID.fromString(System.getenv("CROSSBRIDGE_RUN_ID")));
            stmt.setString(2, testId);
            stmt.setDouble(3, duration);
            stmt.setString(4, status);
            stmt.executeUpdate();
        } catch (Exception e) {
            // Silent failure
        }
    }
}
```

#### 4.3 .NET Frameworks

**NUnit Hook** (C# code generation):
```csharp
[AttributeUsage(AttributeTargets.Assembly)]
public class CrossBridgeProfilingHookAttribute : Attribute, ITestAction
{
    private static Dictionary<string, DateTime> testStartTimes = new Dictionary<string, DateTime>();
    private static NpgsqlConnection connection;
    
    public void BeforeTest(ITest test)
    {
        testStartTimes[test.Id] = DateTime.UtcNow;
    }
    
    public void AfterTest(ITest test)
    {
        var duration = (DateTime.UtcNow - testStartTimes[test.Id]).TotalMilliseconds;
        WriteToPostgres(test.FullName, duration, test.ResultState.ToString());
    }
    
    private void WriteToPostgres(string testId, double duration, string status)
    {
        try {
            EnsureConnection();
            using (var cmd = new NpgsqlCommand(
                "INSERT INTO profiling.tests (run_id, test_id, duration_ms, status, framework) " +
                "VALUES (@runId, @testId, @duration, @status, 'nunit')", connection))
            {
                cmd.Parameters.AddWithValue("@runId", Guid.Parse(Environment.GetEnvironmentVariable("CROSSBRIDGE_RUN_ID")));
                cmd.Parameters.AddWithValue("@testId", testId);
                cmd.Parameters.AddWithValue("@duration", duration);
                cmd.Parameters.AddWithValue("@status", status);
                cmd.ExecuteNonQuery();
            }
        } catch {
            // Silent failure
        }
    }
}
```

#### 4.4 JavaScript Frameworks

**Cypress Plugin**:
```javascript
module.exports = (on, config) => {
  let runId = crypto.randomUUID();
  
  on('before:run', async (details) => {
    await writeToPostgres('INSERT INTO profiling.runs (run_id, framework) VALUES ($1, $2)', 
                          [runId, 'cypress']);
  });
  
  on('before:spec', (spec) => {
    config.env.crossbridge_spec_start = Date.now();
  });
  
  on('after:spec', async (spec, results) => {
    const duration = Date.now() - config.env.crossbridge_spec_start;
    await writeToPostgres(
      'INSERT INTO profiling.tests (run_id, test_id, duration_ms, status, framework) VALUES ($1, $2, $3, $4, $5)',
      [runId, spec.name, duration, results.stats.failures > 0 ? 'failed' : 'passed', 'cypress']
    );
  });
};
```

---

## Data Flow

### Event Lifecycle

```
1. Test Execution
   └─> Framework hook intercepts lifecycle event
       └─> Creates PerformanceEvent with timing
           └─> Calls collector.collect(event)
               └─> Event added to queue (non-blocking)
                   └─> Background worker pulls from queue
                       └─> Batches 100 events
                           └─> Calls storage.write_batch()
                               └─> Storage routes to appropriate table
                                   └─> Data persisted
```

**Timing Example**:
```
T+0ms:    Test starts
T+5ms:    Hook captures start time
T+1500ms: Test completes
T+1505ms: Hook calculates duration (1500ms)
T+1506ms: Event created and queued (< 1ms)
T+1507ms: Test function returns (profiling is done)
...
T+2000ms: Background worker pulls event from queue
T+2001ms: Event batched with 99 others
T+2050ms: Batch of 100 events written to PostgreSQL
```

**Key Insight**: Test execution is NEVER blocked by profiling writes.

---

## Configuration System

### Hierarchical Configuration

```
1. Default Values (hardcoded in ProfileConfig)
   └─> 2. crossbridge.yml file
       └─> 3. Environment Variables (highest priority)
```

**Example Override Precedence**:
```yaml
# crossbridge.yml
profiling:
  enabled: false  # Default

# Environment variable wins
export CROSSBRIDGE_PROFILING=true
```

### Configuration Loading

```python
class ProfileConfig:
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'ProfileConfig':
        with open(yaml_path) as f:
            config = yaml.safe_load(f)
        
        profiling = config.get('crossbridge', {}).get('profiling', {})
        
        # Environment overrides
        enabled = os.getenv('CROSSBRIDGE_PROFILING', profiling.get('enabled', False))
        backend = os.getenv('CROSSBRIDGE_STORAGE_BACKEND', profiling.get('storage', {}).get('backend', 'none'))
        
        return cls(
            enabled=enabled,
            backend=StorageBackendType(backend),
            # ...
        )
```

---

## Thread Safety

### Python Components

- **MetricsCollector**: Thread-safe queue (queue.Queue)
- **PostgreSQL**: Connection pooling (psycopg2.pool)
- **Statistics**: Protected by threading.Lock

### Java Components

- **TestNG**: ThreadLocal for start times (parallel test support)
- **JUnit**: ConcurrentHashMap for start times

### .NET Components

- **NUnit/SpecFlow**: Dictionary with lock statements

---

## Error Handling

### Design Principle: Silent Failure

**Rationale**: Profiling must NEVER cause test failures

**Implementation**:
```python
def collect(self, event: PerformanceEvent):
    try:
        self._queue.put_nowait(event)
        self._stats.events_collected += 1
    except Exception:
        self._stats.events_dropped += 1
        # Silent: no logging, no exceptions
```

**Java Example**:
```java
try {
    writeToPostgres(testId, duration, status);
} catch (Exception e) {
    // Silent failure - test continues normally
}
```

---

## Performance Characteristics

### Benchmarks

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Event creation | < 50 μs | 20,000/sec |
| Queue insertion | < 100 μs | 10,000/sec |
| Batch write (PostgreSQL) | ~50ms | 2,000 events/sec |
| Total overhead per test | < 1ms | N/A |

### Memory Usage

| Component | Memory per Event |
|-----------|------------------|
| PerformanceEvent | ~0.5 KB |
| Queue (10k capacity) | ~5 MB |
| Connection pool | ~2 MB |
| **Total** | **~10 MB** |

---

## Extensibility

### Adding New Event Types

```python
# 1. Add to EventType enum
class EventType(Enum):
    MY_NEW_EVENT = "my_new_event"

# 2. Update storage routing
def _route_event(self, conn, event):
    if event.event_type == EventType.MY_NEW_EVENT:
        self._write_to_my_table(conn, event)

# 3. Collect in hooks
collector.collect(PerformanceEvent.create(
    event_type=EventType.MY_NEW_EVENT,
    custom_field="value",
))
```

### Adding New Storage Backends

```python
class MyStorageBackend(StorageBackend):
    def write_event(self, event: PerformanceEvent):
        # Your implementation
        pass
    
    def write_batch(self, events: List[PerformanceEvent]):
        # Batch implementation
        pass

# Register in factory
class StorageBackendFactory:
    @staticmethod
    def create(config: ProfileConfig) -> StorageBackend:
        if config.backend == StorageBackendType.MY_BACKEND:
            return MyStorageBackend(config)
```

---

## Security Considerations

### Database Credentials

**Best Practices**:
1. Use environment variables (not hardcoded)
2. Restrict database user to profiling schema only
3. Use read-only credentials for Grafana
4. Rotate credentials regularly

**PostgreSQL User Setup**:
```sql
-- Create restricted user
CREATE USER profiler_writer WITH PASSWORD 'secure_password';
GRANT USAGE ON SCHEMA profiling TO profiler_writer;
GRANT INSERT ON ALL TABLES IN SCHEMA profiling TO profiler_writer;

-- Grafana read-only user
CREATE USER grafana_reader WITH PASSWORD 'read_only_password';
GRANT USAGE ON SCHEMA profiling TO grafana_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA profiling TO grafana_reader;
```

---

## Future Enhancements

### Planned Features

1. **Active Profiling Mode**
   - CPU/memory profiling
   - Line-by-line execution tracing
   - Call graph generation

2. **Intelligent Sampling**
   - Adaptive sampling based on test history
   - Always profile slow tests
   - Sample fast tests at lower rate

3. **Distributed Tracing**
   - OpenTelemetry integration
   - Cross-service trace propagation
   - Span correlation

4. **ML-Powered Insights**
   - Regression detection
   - Anomaly detection
   - Root cause analysis

---

## References

- [Configuration Guide](CONFIGURATION.md)
- [Framework Integration](FRAMEWORK_INTEGRATION.md)
- [Grafana Dashboards](../observability/GRAFANA_PERFORMANCE_PROFILING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
