# CrossBridge Continuous Intelligence Integration Guide

## Overview

CrossBridge's continuous intelligence system operates as a **pure observer** that:
- ✅ Never owns test execution
- ✅ Never regenerates tests post-migration
- ✅ Automatically detects new tests without remigration
- ✅ Provides drift detection and coverage intelligence
- ✅ Operates via optional, lightweight framework hooks

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Test Execution (Your Control)         │
├─────────────────────────────────────────────────┤
│  Pytest │ Robot Framework │ Playwright         │
│    ↓    │       ↓         │     ↓              │
│  Hook   │    Listener     │  Reporter          │
└────┼────┴────────┼────────┴─────┼──────────────┘
     │             │              │
     └─────────────┼──────────────┘
                   ↓
         ┌─────────────────────┐
         │  CrossBridge Hook   │
         │      SDK (emit)     │
         └─────────────────────┘
                   ↓
         ┌─────────────────────┐
         │  Observer Service   │
         │   (async queue)     │
         └─────────────────────┘
                   ↓
     ┌─────────────┼─────────────┐
     ↓             ↓             ↓
Persistence   Coverage      Drift
 (events)   Intelligence  Detection
```

## Release Stage: Database Setup

### 1. Run Migration

```bash
cd d:\Future-work2\crossbridge
python scripts/migrate_continuous_intelligence.py
```

This creates:
- `migration_state` - lifecycle tracking
- `coverage_graph_nodes` - test/API/page entities
- `coverage_graph_edges` - relationships
- `drift_signals` - anomaly detection

### 2. Verify Tables

```sql
-- Check migration
SELECT * FROM migration_state;

-- Check coverage graph
SELECT node_type, COUNT(*) 
FROM coverage_graph_nodes 
GROUP BY node_type;

-- Check drift signals
SELECT signal_type, COUNT(*) 
FROM drift_signals 
WHERE detected_at > NOW() - INTERVAL '7 days'
GROUP BY signal_type;
```

## Release Stage: Lifecycle Initialization

### 3. Initialize Migration State

```python
from core.observability import LifecycleManager, CrossBridgeMode

manager = LifecycleManager(
    project_id="my-project",
    db_host="10.55.12.99",
    db_port=5432,
    db_name="udp-native-webservices-automation",
    db_user="postgres",
    db_password="admin"
)

# Start in migration mode
manager.initialize_migration()

# When migration complete, transition to observer
manager.transition_to_observer()
```

### 4. Verify Mode

```python
mode = manager.get_current_mode()
print(f"Current mode: {mode}")  # CrossBridgeMode.OBSERVER
```

## Release Stage: Observer Service

### 5. Start Observer Service

```python
from core.observability import CrossBridgeObserverService

observer = CrossBridgeObserverService(
    db_host="10.55.12.99",
    db_port=5432,
    db_name="udp-native-webservices-automation",
    db_user="postgres",
    db_password="admin"
)

# Start async processing
observer.start()

# Service runs in background thread, processing events
```

### 6. Monitor Health

```python
health = observer.get_health_metrics()
print(f"Events processed: {health['events_processed']}")
print(f"Processing errors: {health['processing_errors']}")
print(f"Queue size: {health['queue_size']}")
```

## Release Stage: Framework Hooks

### Option A: Pytest Plugin

#### Install Hook

```bash
# Add to pytest.ini
[pytest]
plugins = core.observability.hooks.pytest_hook

[crossbridge]
enabled = true
db_host = 10.55.12.99
db_port = 5432
db_name = udp-native-webservices-automation
db_user = postgres
db_password = admin
application_version = v2.1.0
product_name = MyWebApp
environment = staging
```

#### Run Tests

```bash
pytest tests/ --crossbridge
```

#### Verify Events

```sql
SELECT test_name, status, duration_seconds
FROM test_execution_event
WHERE event_timestamp > NOW() - INTERVAL '1 hour'
ORDER BY event_timestamp DESC
LIMIT 10;
```

### Option B: Robot Framework Listener

#### Register Listener

```bash
robot --listener core.observability.hooks.robot_listener.CrossBridgeListener \
      --variable CROSSBRIDGE_DB_HOST:10.55.12.99 \
      --variable CROSSBRIDGE_DB_PORT:5432 \
      --variable CROSSBRIDGE_DB_NAME:udp-native-webservices-automation \
      --variable APP_VERSION:v2.1.0 \
      --variable PRODUCT_NAME:MyWebApp \
      --variable ENVIRONMENT:staging \
      tests/
```

#### Verify Events

```sql
SELECT test_name, status, COUNT(*) as execution_count
FROM test_execution_event
WHERE framework = 'robot'
  AND event_timestamp > NOW() - INTERVAL '1 day'
GROUP BY test_name, status
ORDER BY execution_count DESC;
```

### Option C: Playwright Reporter

#### Generate Reporter

```python
from core.observability.hooks.playwright_hook import generate_playwright_reporter

# Generate TypeScript reporter
generate_playwright_reporter(output_dir="tests")
```

#### Configure Playwright

```javascript
// playwright.config.ts
import CrossBridgeReporter from './crossbridge-reporter';

export default {
  reporter: [
    ['list'],
    ['html'],
    [CrossBridgeReporter, {
      dbHost: '10.55.12.99',
      dbPort: 5432,
      dbName: 'udp-native-webservices-automation',
      appVersion: 'v2.1.0',
      productName: 'MyWebApp',
      environment: 'staging'
    }]
  ],
  // ... other config
};
```

#### Run Tests

```bash
npx playwright test
```

## Phase 5: Coverage Intelligence

### 7. Query Coverage Graph

```python
from core.observability import CoverageIntelligence

coverage = CoverageIntelligence(
    db_host="10.55.12.99",
    db_port=5432,
    db_name="udp-native-webservices-automation",
    db_user="postgres",
    db_password="admin"
)

# Get all tests for an API
tests = coverage.get_tests_for_api("/api/payments/create")
print(f"Tests covering payment API: {tests}")

# Find impacted tests when page changes
impacted = coverage.get_impacted_tests(
    changed_node_id="page:checkout",
    node_type="page"
)
print(f"Tests impacted by checkout page change: {impacted}")
```

### 8. View Coverage in SQL

```sql
-- Test-to-API coverage
SELECT 
    n1.node_id as test_id,
    n2.node_id as api_endpoint,
    e.weight as call_count
FROM coverage_graph_edges e
JOIN coverage_graph_nodes n1 ON e.from_node = n1.node_id
JOIN coverage_graph_nodes n2 ON e.to_node = n2.node_id
WHERE n1.node_type = 'test'
  AND n2.node_type = 'api'
  AND e.edge_type = 'calls_api'
ORDER BY e.weight DESC;

-- Page coverage
SELECT 
    n2.node_id as page,
    COUNT(DISTINCT n1.node_id) as test_count
FROM coverage_graph_edges e
JOIN coverage_graph_nodes n1 ON e.from_node = n1.node_id
JOIN coverage_graph_nodes n2 ON e.to_node = n2.node_id
WHERE n1.node_type = 'test'
  AND n2.node_type = 'page'
  AND e.edge_type = 'visits_page'
GROUP BY n2.node_id
ORDER BY test_count DESC;
```

## Phase 6: Drift Detection

### 9. Monitor Drift Signals

```python
from core.observability import DriftDetector

detector = DriftDetector(
    db_host="10.55.12.99",
    db_port=5432,
    db_name="udp-native-webservices-automation",
    db_user="postgres",
    db_password="admin"
)

# Detect new tests (auto-registers them)
new_tests = detector.detect_new_tests()
for signal in new_tests:
    print(f"🆕 {signal.test_id}: {signal.description}")

# Detect removed tests (7-day inactivity)
removed = detector.detect_removed_tests()
for signal in removed:
    print(f"🗑️ {signal.test_id}: {signal.description}")

# Detect behavior changes (50% duration threshold)
behavior_changes = detector.detect_behavior_changes()
for signal in behavior_changes:
    print(f"⚠️ {signal.test_id}: {signal.description}")

# Detect flaky tests (30% status oscillation)
flaky = detector.detect_flaky_tests()
for signal in flaky:
    print(f"⚡ {signal.test_id}: {signal.description}")
```

### 10. Query Drift in SQL

```sql
-- Recent drift signals
SELECT 
    signal_type,
    test_id,
    severity,
    description,
    detected_at
FROM drift_signals
WHERE detected_at > NOW() - INTERVAL '7 days'
  AND acknowledged = false
ORDER BY 
    CASE severity
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END,
    detected_at DESC;

-- Flaky test trend
SELECT 
    test_id,
    COUNT(*) as flake_count,
    MAX(detected_at) as last_flake
FROM drift_signals
WHERE signal_type = 'flaky'
  AND detected_at > NOW() - INTERVAL '30 days'
GROUP BY test_id
HAVING COUNT(*) > 3
ORDER BY flake_count DESC;
```

## Phase 7: Grafana Dashboards

### 11. Import Drift Dashboard

```json
{
  "title": "CrossBridge Drift Detection",
  "panels": [
    {
      "title": "New Tests (Last 7 Days)",
      "targets": [{
        "rawSql": "SELECT test_id, detected_at FROM drift_signals WHERE signal_type = 'new_test' AND detected_at > NOW() - INTERVAL '7 days'"
      }]
    },
    {
      "title": "Flaky Tests",
      "targets": [{
        "rawSql": "SELECT test_id, COUNT(*) as flake_count FROM drift_signals WHERE signal_type = 'flaky' GROUP BY test_id ORDER BY flake_count DESC"
      }]
    },
    {
      "title": "Behavior Changes",
      "targets": [{
        "rawSql": "SELECT test_id, description FROM drift_signals WHERE signal_type = 'behavior_change' AND detected_at > NOW() - INTERVAL '24 hours'"
      }]
    }
  ]
}
```

### 12. Import Coverage Dashboard

```json
{
  "title": "CrossBridge Coverage Intelligence",
  "panels": [
    {
      "title": "API Coverage",
      "targets": [{
        "rawSql": "SELECT n2.node_id as api, COUNT(DISTINCT n1.node_id) as test_count FROM coverage_graph_edges e JOIN coverage_graph_nodes n1 ON e.from_node = n1.node_id JOIN coverage_graph_nodes n2 ON e.to_node = n2.node_id WHERE n1.node_type = 'test' AND n2.node_type = 'api' GROUP BY n2.node_id"
      }]
    },
    {
      "title": "Page Coverage",
      "targets": [{
        "rawSql": "SELECT n2.node_id as page, COUNT(DISTINCT n1.node_id) as test_count FROM coverage_graph_edges e JOIN coverage_graph_nodes n1 ON e.from_node = n1.node_id JOIN coverage_graph_nodes n2 ON e.to_node = n2.node_id WHERE n1.node_type = 'test' AND n2.node_type = 'page' GROUP BY n2.node_id"
      }]
    }
  ]
}
```

## Troubleshooting

### Hook Not Emitting Events

1. **Check observer service is running**:
   ```python
   observer.get_health_metrics()  # Should show non-zero queue_size
   ```

2. **Verify database connection**:
   ```python
   from core.observability import EventPersistence
   persistence = EventPersistence(...)
   persistence.ping()  # Should return True
   ```

3. **Check hook configuration**:
   - Pytest: Verify `pytest.ini` has correct `[crossbridge]` section
   - Robot: Ensure `--listener` flag is passed
   - Playwright: Check `playwright.config.ts` reporter config

### Events Not Appearing in Grafana

1. **Check time range**: Ensure Grafana time range matches event timestamps
2. **Verify datasource**: UID must match `postgres_crossbridge`
3. **Query events directly**:
   ```sql
   SELECT * FROM test_execution_event ORDER BY event_timestamp DESC LIMIT 10;
   ```

### Drift Detection Not Working

1. **Verify historical data**: Need at least 7 days of events for removed test detection
2. **Check thresholds**:
   - Behavior change: 50% duration difference
   - Flakiness: 30% status oscillation over 20+ runs
3. **Run detector manually**:
   ```python
   detector.detect_all()  # Returns all drift signals
   ```

## Best Practices

1. **Lifecycle Management**:
   - Always initialize migration state before first run
   - Transition to observer mode ONLY when migration is complete
   - Observer mode is permanent (one-way transition)

2. **Hook Installation**:
   - Hooks are optional - start with one framework
   - Use environment variables for sensitive config
   - Test hooks in dev environment first

3. **Observer Service**:
   - Run as daemon/sidecar in CI/CD pipeline
   - Monitor health metrics regularly
   - Set up alerts for processing errors

4. **Coverage Intelligence**:
   - Graph is incremental - never overwrites existing data
   - New tests auto-register with first execution
   - Use change impact analysis before deployments

5. **Drift Detection**:
   - Review drift signals daily
   - Acknowledge false positives to reduce noise
   - Investigate high-severity signals immediately

## Next Steps

1. ✅ Run database migration
2. ✅ Initialize lifecycle (migration → observer)
3. ✅ Start observer service
4. ✅ Install framework hook (pytest/Robot/Playwright)
5. ✅ Run tests and verify events in database
6. ✅ Import Grafana dashboards
7. ✅ Set up drift detection alerts
8. ✅ Review coverage intelligence weekly
