# CrossBridge Performance Profiling

> Passive, framework-agnostic performance profiling for test execution

## Overview

CrossBridge Performance Profiling captures test execution timing, automation overhead, and application interaction metrics **without modifying your test code**. It works as a pure observer, collecting performance data in the background while your tests run normally.

### Key Features

- ✅ **Framework-Agnostic**: Works with 12+ testing frameworks
- ✅ **Passive Observation**: Zero impact on test execution
- ✅ **Disabled by Default**: Explicitly opt-in when needed
- ✅ **Multiple Storage Backends**: Local files, PostgreSQL, InfluxDB
- ✅ **Grafana Integration**: Pre-built dashboards and queries
- ✅ **Non-Blocking**: Async operation never blocks tests
- ✅ **Exception-Safe**: Profiling failures never fail tests

---

## Supported Frameworks

| Framework | Status | Integration Method |
|-----------|--------|-------------------|
| **pytest** | ✅ Ready | Python plugin |
| **Robot Framework** | ✅ Ready | Robot listener |
| **Selenium (Python)** | ✅ Ready | WebDriver wrapper |
| **Selenium (Java)** | ✅ Ready | TestNG/JUnit listener |
| **TestNG** | ✅ Ready | Java listener |
| **JUnit** | ✅ Ready | Java listener |
| **NUnit** | ✅ Ready | C# hook attribute |
| **SpecFlow** | ✅ Ready | C# binding |
| **Cypress** | ✅ Ready | JavaScript plugin |
| **Playwright** | ✅ Ready | Reporter |
| **RestAssured** | ✅ Ready | HTTP interceptor |
| **Cucumber/Behave** | ✅ Ready | BDD hooks |

---

## Quick Start

### 1. Enable Profiling

Edit `crossbridge.yml`:

```yaml
crossbridge:
  profiling:
    enabled: true  # Enable profiling
    
    storage:
      backend: postgres  # or 'local', 'influxdb'
      
      postgres:
        host: 10.60.67.247
        port: 5432
        database: cbridge-unit-test-db
        user: postgres
        password: admin
```

### 2. Run Tests

```bash
# Tests run normally - profiling happens in background
pytest tests/ -v
```

### 3. View Metrics

- **PostgreSQL**: Query `profiling.tests`, `profiling.http_calls`, etc.
- **Grafana**: Import pre-built dashboards
- **Local Files**: Check `.crossbridge/profiles/run_*.jsonl`

---

## Framework Integration Guides

### Python Frameworks

#### pytest

**File**: `conftest.py`
```python
# Profiling is automatic when enabled in crossbridge.yml
pytest_plugins = ["core.profiling.hooks.pytest_hook"]
```

**Run**:
```bash
pytest tests/ -v
```

#### Robot Framework

**Command**:
```bash
robot --listener core.profiling.hooks.robot_hook.CrossBridgeProfilingListener tests/
```

#### Selenium Python

**Code**:
```python
from selenium import webdriver
from core.profiling.hooks import profile_webdriver

driver = webdriver.Chrome()
profiled_driver = profile_webdriver(driver, test_id="test_login")

# Use profiled_driver normally
profiled_driver.get("https://example.com")
profiled_driver.find_element("id", "username").send_keys("test")
```

#### HTTP Requests

**Code**:
```python
from core.profiling.hooks import profile_requests_session

session = profile_requests_session(test_id="test_api")
response = session.get("https://api.example.com/users")
```

---

### Java Frameworks

#### TestNG

**File**: `testng.xml`
```xml
<suite name="MyTests">
  <listeners>
    <listener class-name="com.crossbridge.profiling.CrossBridgeProfilingListener"/>
  </listeners>
  
  <test name="Test1">
    <classes>
      <class name="com.example.MyTest"/>
    </classes>
  </test>
</suite>
```

**Environment Variables**:
```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
export CROSSBRIDGE_DB_HOST=10.60.67.247
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=cbridge-unit-test-db
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin

mvn test
```

#### JUnit

**File**: `pom.xml` (Maven Surefire)
```xml
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-surefire-plugin</artifactId>
  <configuration>
    <properties>
      <property>
        <name>listener</name>
        <value>com.crossbridge.profiling.CrossBridgeJUnitListener</value>
      </property>
    </properties>
  </configuration>
</plugin>
```

---

### .NET Frameworks

#### NUnit

**File**: `AssemblyInfo.cs`
```csharp
using CrossBridge.Profiling;

[assembly: CrossBridgeProfilingHook]
```

**Environment Variables**:
```powershell
$env:CROSSBRIDGE_PROFILING_ENABLED="true"
$env:CROSSBRIDGE_DB_HOST="10.60.67.247"
$env:CROSSBRIDGE_DB_PORT="5432"
$env:CROSSBRIDGE_DB_NAME="cbridge-unit-test-db"
$env:CROSSBRIDGE_DB_USER="postgres"
$env:CROSSBRIDGE_DB_PASSWORD="admin"

dotnet test
```

#### SpecFlow

Add the hook file to your project and SpecFlow will automatically discover it.

---

### JavaScript Frameworks

#### Cypress

**File**: `cypress.config.js`
```javascript
const crossbridge = require('./cypress/plugins/crossbridge-profiling');

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      crossbridge(on, config);
      return config;
    },
  },
});
```

**File**: `cypress/support/e2e.js`
```javascript
import './crossbridge-profiling';
```

**Environment Variables**:
```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
cypress run
```

#### Playwright

**File**: `playwright.config.ts`
```typescript
import { CrossBridgePlaywrightReporter } from './core/profiling/hooks/playwright_hook';

export default defineConfig({
  reporter: [
    ['list'],
    [new CrossBridgePlaywrightReporter()]
  ],
});
```

---

## Storage Backends

### Local Files (Development)

```yaml
profiling:
  storage:
    backend: local
    local:
      path: .crossbridge/profiles
```

Files are written to `.crossbridge/profiles/run_*.jsonl` in JSONL format.

### PostgreSQL (Production)

```yaml
profiling:
  storage:
    backend: postgres
    postgres:
      host: 10.60.67.247
      port: 5432
      database: cbridge-unit-test-db
      user: postgres
      password: admin
      schema: profiling
```

**Schema**:
- `profiling.runs` - Run metadata
- `profiling.tests` - Test lifecycle events
- `profiling.steps` - Setup/teardown timing
- `profiling.http_calls` - API/HTTP metrics
- `profiling.driver_commands` - WebDriver timing
- `profiling.system_metrics` - Resource usage

### InfluxDB (Time-Series)

```yaml
profiling:
  storage:
    backend: influxdb
    influxdb:
      url: http://localhost:8086
      org: crossbridge
      bucket: profiling
      token: ${INFLUX_TOKEN}
```

---

## Grafana Dashboards

See [GRAFANA_PERFORMANCE_PROFILING.md](../observability/GRAFANA_PERFORMANCE_PROFILING.md) for:

- ✅ 12 pre-built dashboard panels
- ✅ SQL queries for all visualizations
- ✅ Alerting rules
- ✅ Variable configuration
- ✅ Troubleshooting guide

**Sample Panels**:
1. Slowest Tests (Top 10)
2. Test Duration Trend
3. API Endpoint Performance
4. WebDriver Command Heatmap
5. Performance Regression Detection
6. And more...

---

## Configuration Reference

### Complete Configuration

```yaml
crossbridge:
  profiling:
    # Core settings
    enabled: false  # DEFAULT: disabled
    mode: passive   # passive | active (future)
    sampling_rate: 1.0  # 1.0 = 100%, 0.5 = 50%
    
    # Collectors (what to capture)
    collectors:
      test_lifecycle: true   # Test start/end timing
      webdriver: true        # Selenium commands
      http: true             # API/HTTP calls
      system_metrics: false  # CPU/memory (expensive)
    
    # Storage backend
    storage:
      backend: none  # none | local | postgres | influxdb
      
      local:
        path: .crossbridge/profiles
      
      postgres:
        host: ${CROSSBRIDGE_DB_HOST:-localhost}
        port: ${CROSSBRIDGE_DB_PORT:-5432}
        database: ${CROSSBRIDGE_DB_NAME:-crossbridge}
        user: ${CROSSBRIDGE_DB_USER:-crossbridge}
        password: ${CROSSBRIDGE_DB_PASSWORD:-crossbridge}
        schema: profiling
      
      influxdb:
        url: ${INFLUXDB_URL:-http://localhost:8086}
        org: ${INFLUXDB_ORG:-crossbridge}
        bucket: ${INFLUXDB_BUCKET:-profiling}
        token: ${INFLUX_TOKEN}
    
    # Grafana integration
    grafana:
      enabled: false
      datasource: postgres  # postgres | influxdb
```

### Environment Variable Override

```bash
# Globally disable profiling
export CROSSBRIDGE_PROFILING=false

# Framework-specific enables
export CROSSBRIDGE_PROFILING_ENABLED=true
```

---

## API Reference

### Python API

```python
from core.profiling import (
    PerformanceEvent,
    EventType,
    ProfileConfig,
    MetricsCollector,
)
from core.profiling.collector import start_profiling, stop_profiling, collect_event

# Start profiling
config = ProfileConfig(
    enabled=True,
    backend=StorageBackendType.POSTGRES,
    postgres_host="10.60.67.247",
    # ...
)
start_profiling(config)

# Collect custom events
event = PerformanceEvent.create(
    run_id=collector.current_run_id,
    test_id="my_custom_test",
    event_type=EventType.TEST_END,
    framework="custom",
    duration_ms=1500,
    custom_field="value",
)
collect_event(event)

# Stop profiling
stop_profiling()
```

---

## Troubleshooting

### Profiling Not Working

**Check configuration**:
```bash
# Verify enabled
grep "enabled:" crossbridge.yml

# Check environment
echo $CROSSBRIDGE_PROFILING
```

**Verify database connection**:
```bash
psql -h 10.60.67.247 -p 5432 -U postgres -d cbridge-unit-test-db -c "SELECT COUNT(*) FROM profiling.tests;"
```

### No Data in Grafana

1. Check time range in Grafana
2. Verify PostgreSQL datasource connection
3. Run unit tests to generate sample data:
   ```bash
   pytest tests/test_performance_profiling.py -v
   ```

### High Memory Usage

Reduce sampling rate:
```yaml
profiling:
  sampling_rate: 0.5  # Only 50% of events
```

---

## Best Practices

1. **Start with Local Storage** during development
2. **Use PostgreSQL** for production and Grafana integration
3. **Keep Sampling Rate at 1.0** unless high volume
4. **Monitor Queue Size** in collector statistics
5. **Set Alerts** in Grafana for regressions
6. **Review Regularly** to identify slow tests

---

## Performance Impact

- **Collection Overhead**: < 0.1ms per event
- **Storage Latency**: Async, non-blocking
- **Memory Usage**: ~10MB for 10,000 events in queue
- **Test Runtime Impact**: < 1% overhead

---

## Support

- **Documentation**: See `docs/profiling/` for detailed guides
- **Issues**: https://github.com/crossstack-ai/crossbridge/issues
- **Email**: vikas.sdet@gmail.com

---

## See Also

- [Grafana Integration Guide](../observability/GRAFANA_PERFORMANCE_PROFILING.md)
- [Framework Integration Examples](integration/)
- [API Reference](api.md)
- [Troubleshooting Guide](troubleshooting.md)
