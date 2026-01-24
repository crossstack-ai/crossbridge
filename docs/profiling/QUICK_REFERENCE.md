# Performance Profiling - Quick Reference

> 5-minute setup guide for performance profiling

---

## Enable Profiling (3 Steps)

### Step 1: Edit Configuration

**File**: `crossbridge.yml`
```yaml
crossbridge:
  profiling:
    enabled: true  # ← Change this to true
    
    storage:
      backend: postgres  # or 'local' for testing
      
      postgres:
        host: 10.60.67.247
        port: 5432
        database: cbridge-unit-test-db
        user: postgres
        password: admin
```

### Step 2: Add Framework Hook

Choose your framework:

<details>
<summary><b>pytest</b> (Python)</summary>

**No changes needed** - automatic when profiling is enabled!

```bash
pytest tests/ -v
```
</details>

<details>
<summary><b>Robot Framework</b> (Python)</summary>

```bash
robot --listener core.profiling.hooks.robot_hook.CrossBridgeProfilingListener tests/
```
</details>

<details>
<summary><b>TestNG</b> (Java)</summary>

**testng.xml**:
```xml
<suite name="MyTests">
  <listeners>
    <listener class-name="com.crossbridge.profiling.CrossBridgeProfilingListener"/>
  </listeners>
  ...
</suite>
```

**Environment**:
```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
export CROSSBRIDGE_RUN_ID=$(uuidgen)
export CROSSBRIDGE_DB_HOST=10.60.67.247
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=cbridge-unit-test-db
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin

mvn test
```
</details>

<details>
<summary><b>NUnit</b> (.NET)</summary>

**AssemblyInfo.cs**:
```csharp
using CrossBridge.Profiling;

[assembly: CrossBridgeProfilingHook]
```

**Environment**:
```powershell
$env:CROSSBRIDGE_PROFILING_ENABLED="true"
$env:CROSSBRIDGE_RUN_ID=[guid]::NewGuid().ToString()
$env:CROSSBRIDGE_DB_HOST="10.60.67.247"
# ... (same as Java)

dotnet test
```
</details>

<details>
<summary><b>Cypress</b> (JavaScript)</summary>

**cypress.config.js**:
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

**cypress/support/e2e.js**:
```javascript
import './crossbridge-profiling';
```

```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
npx cypress run
```
</details>

<details>
<summary><b>Playwright</b> (JavaScript/TypeScript)</summary>

**playwright.config.ts**:
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  reporter: [
    ['list'],
    ['./playwright-crossbridge-reporter.js']
  ],
});
```

```bash
npx playwright test
```
</details>

### Step 3: Run Tests & View Data

```bash
# Run your tests normally
# Profiling happens automatically in background

# View data in PostgreSQL
psql -h 10.60.67.247 -p 5432 -U postgres -d cbridge-unit-test-db -c "
SELECT 
  test_id, 
  duration_ms, 
  status, 
  framework 
FROM profiling.tests 
ORDER BY duration_ms DESC 
LIMIT 10;
"
```

---

## View Metrics

### PostgreSQL Queries

**Slowest Tests**:
```sql
SELECT test_id, duration_ms, status, finished_at
FROM profiling.tests
ORDER BY duration_ms DESC
LIMIT 10;
```

**API Performance**:
```sql
SELECT 
  endpoint,
  AVG(duration_ms) as avg_ms,
  COUNT(*) as call_count
FROM profiling.http_calls
GROUP BY endpoint
ORDER BY avg_ms DESC;
```

**WebDriver Commands**:
```sql
SELECT 
  command,
  AVG(duration_ms) as avg_ms,
  COUNT(*) as count
FROM profiling.driver_commands
GROUP BY command
ORDER BY avg_ms DESC;
```

### Grafana Dashboards

1. Add PostgreSQL datasource in Grafana
2. Import dashboard from [Grafana Guide](../observability/GRAFANA_PERFORMANCE_PROFILING.md)
3. View 12 pre-built panels:
   - Slowest Tests
   - Duration Trends
   - API Performance
   - Regression Detection
   - And more...

---

## Framework-Specific Setup

| Framework | Setup Time | Integration Method | Documentation |
|-----------|------------|-------------------|---------------|
| **pytest** | 0 min | Automatic | [Guide](FRAMEWORK_INTEGRATION.md#pytest) |
| **Robot** | 1 min | Command flag | [Guide](FRAMEWORK_INTEGRATION.md#robot-framework) |
| **TestNG** | 5 min | Listener + env vars | [Guide](FRAMEWORK_INTEGRATION.md#testng) |
| **JUnit** | 5 min | Maven config + env | [Guide](FRAMEWORK_INTEGRATION.md#junit) |
| **NUnit** | 5 min | Assembly attr + env | [Guide](FRAMEWORK_INTEGRATION.md#nunit) |
| **SpecFlow** | 3 min | Auto-discovery | [Guide](FRAMEWORK_INTEGRATION.md#specflow) |
| **Cypress** | 5 min | Plugin + support | [Guide](FRAMEWORK_INTEGRATION.md#cypress) |
| **Playwright** | 3 min | Reporter config | [Guide](FRAMEWORK_INTEGRATION.md#playwright) |

---

## Configuration Templates

### Local Development
```yaml
profiling:
  enabled: true
  storage:
    backend: local  # Files in .crossbridge/profiles/
```

### CI/CD Pipeline
```yaml
profiling:
  enabled: true
  sampling_rate: 0.5  # 50% to reduce volume
  storage:
    backend: postgres
    postgres:
      host: ${CI_DB_HOST}  # From environment
      # ...
```

### Production (Selective)
```yaml
profiling:
  enabled: false  # Enable via CROSSBRIDGE_PROFILING=true
  storage:
    backend: postgres
```

---

## Environment Variables

Quick override without changing `crossbridge.yml`:

```bash
# Enable globally
export CROSSBRIDGE_PROFILING=true

# Database connection
export CROSSBRIDGE_DB_HOST=10.60.67.247
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=cbridge-unit-test-db
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin

# Run ID (Java/.NET)
export CROSSBRIDGE_RUN_ID=$(uuidgen)  # Linux/Mac
# or
$env:CROSSBRIDGE_RUN_ID=[guid]::NewGuid().ToString()  # PowerShell
```

---

## Troubleshooting

### No Data Captured

**Check 1**: Profiling enabled?
```bash
grep "enabled:" crossbridge.yml
# Should show: enabled: true
```

**Check 2**: Database connection?
```bash
psql -h 10.60.67.247 -p 5432 -U postgres -d cbridge-unit-test-db -c "SELECT 1;"
```

**Check 3**: Schema exists?
```bash
psql -h 10.60.67.247 -p 5432 -U postgres -d cbridge-unit-test-db -c "\dt profiling.*"
```

### Import Errors (Python)

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Listener Not Found (Java)

```bash
mvn clean compile test-compile
```

---

## Performance Impact

- **Collection**: < 0.1ms per event
- **Storage**: Async, non-blocking
- **Test Runtime**: < 1% overhead
- **Memory**: ~10MB for typical suite

---

## What's Tracked?

### Python Frameworks
- ✅ Test start/end timing
- ✅ Setup/teardown duration
- ✅ WebDriver commands (Selenium)
- ✅ HTTP requests (requests library)

### Java Frameworks
- ✅ Test lifecycle (TestNG/JUnit)
- ✅ Configuration methods
- ✅ Parallel execution

### .NET Frameworks
- ✅ Test timing (NUnit)
- ✅ Scenario execution (SpecFlow)

### JavaScript Frameworks
- ✅ Test/spec execution
- ✅ HTTP interception (Cypress)
- ✅ Step-level timing (Playwright)

---

## Support

- **Full Documentation**: [docs/profiling/README.md](README.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Integration Guide**: [FRAMEWORK_INTEGRATION.md](FRAMEWORK_INTEGRATION.md)
- **Grafana Setup**: [Grafana Guide](../observability/GRAFANA_PERFORMANCE_PROFILING.md)
- **Email**: vikas.sdet@gmail.com

---

## Quick Commands Cheat Sheet

```bash
# Enable profiling
export CROSSBRIDGE_PROFILING=true

# Run Python tests
pytest tests/ -v

# Run Robot tests
robot --listener core.profiling.hooks.robot_hook.CrossBridgeProfilingListener tests/

# Run Java tests (Maven)
mvn test

# Run .NET tests
dotnet test

# Run Cypress tests
npx cypress run

# Run Playwright tests
npx playwright test

# Query results (PostgreSQL)
psql -h 10.60.67.247 -p 5432 -U postgres -d cbridge-unit-test-db \
  -c "SELECT test_id, duration_ms FROM profiling.tests ORDER BY duration_ms DESC LIMIT 10;"

# Generate test data (unit tests)
pytest tests/test_performance_profiling.py -v
```

---

**🚀 Ready to profile? Enable profiling and run your tests!**
