# CrossBridge Continuous Intelligence System

## 🎯 Overview

CrossBridge's continuous intelligence system is a **post-migration observability platform** that operates as a pure observer, never owning test execution or regenerating code.

### Key Principles

✅ **CrossBridge NEVER owns test execution**  
✅ **CrossBridge NEVER regenerates tests post-migration**  
✅ **CrossBridge operates as pure observer via hooks**  
✅ **Automatic new test detection without remigration**

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│           Test Execution (Your Control)                  │
│   pytest │ Robot Framework │ Playwright │ Others        │
└─────┬──────────────┬─────────────┬──────────────────────┘
      │              │             │
      ↓              ↓             ↓
┌─────────────────────────────────────────────────────────┐
│            Framework Hooks (Optional)                    │
│   pytest_plugin │ robot_listener │ playwright_reporter  │
└─────────────────────────────────────────────────────────┘
                      ↓
         ┌─────────────────────────┐
         │  CrossBridge Hook SDK   │
         │    (Event Emission)     │
         └─────────────────────────┘
                      ↓
         ┌─────────────────────────┐
         │   Observer Service      │
         │   (Async Processing)    │
         └─────────────────────────┘
                      ↓
      ┌───────────────┼───────────────┐
      ↓               ↓               ↓
┌──────────┐  ┌──────────────┐  ┌─────────────┐
│ Persist  │  │  Coverage    │  │   Drift     │
│ Events   │  │Intelligence  │  │ Detection   │
└──────────┘  └──────────────┘  └─────────────┘
```

## 📦 Components

### 1. Lifecycle Management
**File**: `core/observability/lifecycle.py`

Manages project lifecycle states:
- `MIGRATION` - Initial test conversion phase
- `OBSERVER` - Post-migration continuous monitoring (**permanent state**)
- `OPTIMIZATION` - AI-powered enhancement suggestions

**Key Features**:
- One-way transition: migration → observer (irreversible)
- State persistence in PostgreSQL
- Guard functions to enforce mode constraints

### 2. Observer Service
**File**: `core/observability/observer_service.py`

Core runtime that processes test execution events asynchronously.

**Key Features**:
- Non-blocking event ingestion via queue
- Worker thread for async processing
- 4-stage pipeline: Persist → Coverage → Drift → AI
- Health metrics and monitoring
- Graceful degradation on failures

### 3. Framework Hooks

#### Pytest Plugin
**File**: `core/observability/hooks/pytest_hook.py`

```ini
# pytest.ini
[pytest]
plugins = core.observability.hooks.pytest_hook

[crossbridge]
enabled = true
db_host = 10.55.12.99
```

```bash
pytest tests/ --crossbridge
```

#### Robot Framework Listener
**File**: `core/observability/hooks/robot_listener.py`

```bash
robot --listener core.observability.hooks.robot_listener.CrossBridgeListener \
      --variable APP_VERSION:v2.0.0 \
      tests/
```

#### Playwright Reporter
**File**: `core/observability/hooks/playwright_hook.py`

```typescript
// playwright.config.ts
import CrossBridgeReporter from './crossbridge-reporter';

export default {
  reporter: [
    [CrossBridgeReporter, { dbHost: '10.55.12.99', ... }]
  ]
};
```

### 4. Coverage Intelligence
**File**: `core/observability/coverage_intelligence.py`

Graph-based system tracking test relationships:
- **Nodes**: Tests, APIs, Pages, UI Components, Features
- **Edges**: `calls_api`, `visits_page`, `interacts_with`, `tests`

**Key Features**:
- Incremental updates (append-only, never overwrites)
- Change impact analysis
- Test-to-feature traceability
- PostgreSQL persistence

### 5. Drift Detection
**File**: `core/observability/drift_detector.py`

Detects 4 types of signals:
1. **New Test** - Automatic registration without remigration
2. **Removed Test** - 7-day inactivity threshold
3. **Behavior Change** - 50% duration difference from baseline
4. **Flaky Test** - 30% status oscillation over 20+ runs

**Key Features**:
- Historical analysis with PostgreSQL queries
- Severity classification (low/medium/high)
- Acknowledgement workflow
- Trend analysis

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install psycopg2 pytest
```

### 2. Run Automated Setup

```bash
python setup_continuous_intelligence.py
```

This will:
- ✅ Create database tables
- ✅ Initialize lifecycle (migration → observer)
- ✅ Start observer service
- ✅ Run integration tests
- ✅ Verify all components

### 3. Install Framework Hook

**Pytest** (Recommended for quick start):

```ini
# pytest.ini
[pytest]
plugins = core.observability.hooks.pytest_hook

[crossbridge]
enabled = true
db_host = 10.55.12.99
db_port = 5432
db_name = udp-native-webservices-automation
db_user = postgres
db_password = admin
application_version = v2.0.0
product_name = MyApp
environment = staging
```

```bash
pytest tests/ --crossbridge
```

### 4. View Results

**Database**:
```sql
-- Recent test executions
SELECT test_name, status, duration_seconds
FROM test_execution_event
WHERE event_timestamp > NOW() - INTERVAL '1 hour'
ORDER BY event_timestamp DESC;

-- Drift signals
SELECT signal_type, test_id, severity, description
FROM drift_signals
WHERE detected_at > NOW() - INTERVAL '24 hours'
ORDER BY detected_at DESC;

-- Coverage graph
SELECT node_type, COUNT(*) 
FROM coverage_graph_nodes 
GROUP BY node_type;
```

**Grafana**:
1. Open http://10.55.12.99:3000/
2. Import `grafana/dashboard_complete.json`
3. View behavioral coverage + version analytics

## 📚 Documentation

- **[Integration Guide](docs/CONTINUOUS_INTELLIGENCE_GUIDE.md)** - Complete setup and usage
- **[Database Schema](#database-schema)** - Table structures
- **[API Reference](#api-reference)** - Python API docs

## 🗄️ Database Schema

### `migration_state`
Tracks project lifecycle state.

| Column | Type | Description |
|--------|------|-------------|
| project_id | TEXT | Primary key |
| mode | TEXT | migration \| observer \| optimization |
| migration_completed_at | TIMESTAMP | When migration finished |
| observer_enabled | BOOLEAN | Observer service active |
| hooks_registered | BOOLEAN | Framework hooks installed |
| last_event_at | TIMESTAMP | Most recent event |
| metadata | JSONB | Additional metadata |

### `coverage_graph_nodes`
Entities in coverage graph.

| Column | Type | Description |
|--------|------|-------------|
| node_id | TEXT | Primary key |
| node_type | TEXT | test \| api \| page \| ui_component \| feature |
| metadata | JSONB | Node-specific data |
| created_at | TIMESTAMP | First seen |
| updated_at | TIMESTAMP | Last modified |

### `coverage_graph_edges`
Relationships between nodes.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| from_node | TEXT | Source node |
| to_node | TEXT | Target node |
| edge_type | TEXT | tests \| calls_api \| visits_page \| interacts_with |
| weight | INTEGER | Relationship strength |
| first_seen | TIMESTAMP | First observation |
| last_seen | TIMESTAMP | Most recent observation |
| metadata | JSONB | Edge-specific data |

### `drift_signals`
Detected anomalies and changes.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| signal_type | TEXT | new_test \| removed_test \| behavior_change \| flaky |
| test_id | TEXT | Affected test |
| severity | TEXT | low \| medium \| high |
| description | TEXT | Human-readable description |
| metadata | JSONB | Signal-specific data |
| detected_at | TIMESTAMP | When detected |
| acknowledged | BOOLEAN | User acknowledged |
| acknowledged_at | TIMESTAMP | When acknowledged |
| acknowledged_by | TEXT | Who acknowledged |

## 🔧 API Reference

### Lifecycle Management

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

# Initialize migration
manager.initialize_migration()

# Transition to observer (one-way, permanent)
manager.transition_to_observer()

# Get current mode
mode = manager.get_current_mode()  # CrossBridgeMode.OBSERVER
```

### Observer Service

```python
from core.observability import CrossBridgeObserverService

observer = CrossBridgeObserverService(
    db_host="10.55.12.99",
    db_port=5432,
    db_name="udp-native-webservices-automation",
    db_user="postgres",
    db_password="admin"
)

# Start service
observer.start()

# Monitor health
health = observer.get_health_metrics()
print(f"Events processed: {health['events_processed']}")
print(f"Queue size: {health['queue_size']}")
print(f"Errors: {health['processing_errors']}")

# Stop service
observer.stop()
```

### Coverage Intelligence

```python
from core.observability import CoverageIntelligence

coverage = CoverageIntelligence(
    db_host="10.55.12.99",
    db_port=5432,
    db_name="udp-native-webservices-automation",
    db_user="postgres",
    db_password="admin"
)

# Get tests covering an API
tests = coverage.get_tests_for_api("/api/payments/create")
print(f"Tests covering API: {tests}")

# Get tests visiting a page
tests = coverage.get_tests_for_page("checkout")
print(f"Tests visiting page: {tests}")

# Change impact analysis
impacted = coverage.get_impacted_tests(
    changed_node_id="api:/api/users",
    node_type="api"
)
print(f"Impacted tests: {impacted}")
```

### Drift Detection

```python
from core.observability import DriftDetector

detector = DriftDetector(
    db_host="10.55.12.99",
    db_port=5432,
    db_name="udp-native-webservices-automation",
    db_user="postgres",
    db_password="admin"
)

# Detect new tests (auto-registers)
new_tests = detector.detect_new_tests()
for signal in new_tests:
    print(f"New: {signal.test_id} - {signal.description}")

# Detect removed tests (7-day threshold)
removed = detector.detect_removed_tests()
for signal in removed:
    print(f"Removed: {signal.test_id} - {signal.description}")

# Detect behavior changes (50% duration threshold)
behavior = detector.detect_behavior_changes()
for signal in behavior:
    print(f"Behavior: {signal.test_id} - {signal.description}")

# Detect flaky tests (30% oscillation)
flaky = detector.detect_flaky_tests()
for signal in flaky:
    print(f"Flaky: {signal.test_id} - {signal.description}")
```

## 🧪 Testing

### Integration Tests

```bash
pytest test_continuous_intelligence_integration.py -v
```

This runs comprehensive tests including:
- ✅ Lifecycle state machine
- ✅ Observer service async processing
- ✅ Hook SDK event emission
- ✅ Coverage intelligence updates
- ✅ Drift detection signals
- ✅ End-to-end workflow

### Manual Verification

```bash
# 1. Check database tables
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation
\dt migration_state coverage_graph_* drift_signals

# 2. Run sample test with hook
pytest tests/test_sample.py --crossbridge

# 3. Query recent events
SELECT * FROM test_execution_event 
WHERE event_timestamp > NOW() - INTERVAL '1 hour'
ORDER BY event_timestamp DESC LIMIT 10;

# 4. Check drift signals
SELECT * FROM drift_signals 
WHERE detected_at > NOW() - INTERVAL '24 hours'
ORDER BY detected_at DESC;
```

## 🔍 Troubleshooting

### No Events Appearing

1. **Check observer service**:
   ```python
   observer.get_health_metrics()
   # Should show is_running: True
   ```

2. **Verify hook configuration**:
   - Pytest: Check `pytest.ini` has `[crossbridge]` section
   - Robot: Ensure `--listener` flag is passed
   - Playwright: Verify `playwright.config.ts` has reporter

3. **Check database connection**:
   ```python
   from core.observability import EventPersistence
   persistence = EventPersistence(...)
   # Should connect without errors
   ```

### Observer Service Not Starting

1. **Check PostgreSQL**:
   ```bash
   psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation -c "SELECT 1"
   ```

2. **Verify tables exist**:
   ```bash
   python scripts/migrate_continuous_intelligence.py
   ```

3. **Check logs**:
   - Look for connection errors
   - Verify credentials are correct

### Drift Detection Not Working

1. **Verify historical data**:
   ```sql
   SELECT COUNT(*) FROM test_execution_event;
   -- Should have multiple executions per test
   ```

2. **Check thresholds**:
   - Behavior change: 50% duration difference
   - Flakiness: 30% status oscillation, 20+ runs
   - Removed test: 7-day inactivity

3. **Run detector manually**:
   ```python
   detector.detect_all()
   ```

## 🎯 Best Practices

1. **Lifecycle Management**:
   - Initialize migration state before first run
   - Transition to observer ONLY when migration complete
   - Observer mode is permanent (no going back)

2. **Hook Installation**:
   - Start with one framework (pytest recommended)
   - Use environment variables for sensitive config
   - Test hooks in dev before production

3. **Observer Service**:
   - Run as daemon/sidecar in CI/CD
   - Monitor health metrics regularly
   - Set up alerts for processing errors

4. **Coverage Intelligence**:
   - Graph is incremental (never overwrites)
   - New tests auto-register on first run
   - Use change impact analysis before deployments

5. **Drift Detection**:
   - Review signals daily
   - Acknowledge false positives
   - Investigate high-severity signals immediately

## 📖 Additional Resources

- **ChatGPT Plan**: Original 15-step implementation guide
- **Migration Guide**: `docs/CONTINUOUS_INTELLIGENCE_GUIDE.md`
- **Database Schema**: `scripts/migrate_continuous_intelligence.py`
- **Example Hooks**: `core/observability/hooks/`
- **Integration Tests**: `test_continuous_intelligence_integration.py`

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## 📄 License

See [LICENSE](LICENSE) for license information.

---

**CrossBridge Continuous Intelligence** - Post-migration observability that never owns execution.
