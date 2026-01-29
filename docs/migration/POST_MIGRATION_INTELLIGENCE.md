# CrossBridge Post-Migration Continuous Intelligence

## Overview

**CrossBridge is not a one-time migration tool.**

It is a **continuous observability and intelligence layer** that remains active after migration, without owning or controlling test execution.

### System Contract

> CrossBridge establishes the initial coverage graph during migration and then remains permanently connected via lightweight framework hooks, continuously observing execution metadata to evolve coverage intelligence and AI insights without owning or regenerating test code.

## Lifecycle Phases

### Release Stage: Migration (Initial Graph Creation)

**Objective**: Create the initial coverage & intent graph

**What CrossBridge Does**:
- Discovers legacy tests
- Extracts intent, steps, flows
- Migrates tests to target frameworks
- Creates initial mappings:
  - Test → Feature
  - Test → Code
  - Change → Impact

**Output**: Persisted coverage graph in PostgreSQL

**Transition**: After migration completes, CrossBridge automatically switches to **observer mode**

### Release Stage: Continuous Intelligence (Post-Migration)

**Key Rule**: CrossBridge **never re-migrates** tests in this phase

**What CrossBridge Does**:
- Observes test execution via lightweight hooks
- Collects execution metadata
- Updates coverage graph
- Detects new tests automatically
- Tracks coverage evolution
- Provides AI-powered insights

**No Migration Required**: All intelligence is metadata-driven

### Release Stage: Optimization & AI Evolution

**Available Features**:
- Flaky test detection
- Missing coverage suggestions
- Test refactor recommendations
- Auto-generation of tests (from coverage gaps)
- Risk-based execution prioritization

**All features operate on metadata, not code**

## Observer Mode Architecture

### How It Works

CrossBridge runs as:
- A background service
- A sidecar process
- Or a lightweight daemon

It **receives** execution events from test frameworks via hooks.

### Hook-Based Integration Model

**Key Principle**: Hooks emit metadata — they **do not** control execution

**Characteristics**:
- ✅ **Optional**: Can be disabled without breaking tests
- ✅ **Lightweight**: Minimal overhead (<5ms per test)
- ✅ **Versioned**: Event schema versioned for backward compatibility
- ✅ **Framework-agnostic**: Works with any test framework

## Hook SDK

### Event Contract

All frameworks emit standardized events:

```python
@dataclass
class CrossBridgeEvent:
    event_type: str              # test_start | test_end | step | api_call
    framework: str               # pytest | robot | playwright
    test_id: str
    timestamp: datetime
    status: Optional[str]        # passed | failed | skipped
    duration_ms: Optional[int]
    metadata: dict               # framework-specific
```

### Framework Integrations

#### 1. Pytest Hook

**Installation**:
```python
# conftest.py
pytest_plugins = ['crossbridge.hooks.pytest_hooks']
```

**Automatic Events**:
- `test_start`: When test begins
- `test_end`: When test completes (with status, duration, errors)

**Manual Instrumentation** (optional):
```python
from crossbridge.hooks.pytest_hooks import track_api_call, track_ui_interaction

def test_api_endpoint():
    response = requests.get("/api/users")
    track_api_call("/api/users", "GET", response.status_code, response.elapsed.total_seconds() * 1000)
```

#### 2. Playwright Hook

**Installation**:
```typescript
// playwright.config.ts
import { crossbridgeReporter } from 'crossbridge/hooks/playwright_hooks';

export default defineConfig({
  reporter: [
    ['html'],
    [crossbridgeReporter]
  ]
});
```

Or inline:
```typescript
import { test } from '@playwright/test';
import { emitTestEnd } from 'crossbridge/hooks/playwright_hooks';

test.afterEach(async ({}, testInfo) => {
  await emitTestEnd(testInfo);
});
```

#### 3. Robot Framework Hook

**Installation**:
```bash
robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener tests/
```

**Manual Keywords** (optional):
```robot
*** Test Cases ***
Test API Endpoint
    ${response}=    GET    /api/users
    Track API Call    /api/users    GET    ${response.status_code}
```

## What CrossBridge Does with Events

### 1. Persist Execution Metadata

Every event stored in PostgreSQL table: `test_execution_event`

Used for:
- History tracking
- Trend analysis
- Flakiness detection
- AI context

### 2. Update Coverage Intelligence

From events, CrossBridge continuously updates:
- Test → Feature coverage
- Test → Page/API coverage
- Change → Impact mappings

**No test regeneration required**

### 3. Detect Drift Automatically

CrossBridge detects:
- ✅ New tests added
- ✅ Tests removed
- ✅ Changed behavior
- ✅ Coverage gaps
- ✅ Redundant tests

**All without migration**

## Handling New Tests (Post-Migration)

### Automatic Detection

When a new test appears:

1. CrossBridge detects unknown `test_id`
2. Creates new test node in graph
3. Links it via:
   - Coverage patterns
   - API calls
   - UI interactions
   - Steps
4. Updates coverage graph
5. Feeds AI analyzers

**No remigration. No manual action required.**

## Configuration

### Modes

```yaml
# crossbridge.yaml
crossbridge:
  mode: observer        # migration | observer
  hooks:
    enabled: true
  persistence:
    postgres: enabled
```

**Default mode after migration**: `observer`

### Environment Variables

```bash
# Disable hooks
export CROSSBRIDGE_HOOKS_ENABLED=false

# Set mode
export CROSSBRIDGE_MODE=observer

# Database connection
export CROSSBRIDGE_DB_URL=postgresql://user:pass@host:5432/db
```

## Ownership Boundary

### Test Framework Owns
- ✅ Test code
- ✅ Execution
- ✅ Assertions
- ✅ CI lifecycle

### CrossBridge Owns
- ✅ Coverage graph
- ✅ Intent mapping
- ✅ Anomaly signals
- ✅ Flakiness intelligence
- ✅ AI context

**Result**: No lock-in, safe adoption, long-term relevance

## Explicit Non-Goals

CrossBridge **MUST NOT**:
- ❌ Replace test frameworks
- ❌ Force execution
- ❌ Require test regeneration
- ❌ Block pipelines
- ❌ Become a test runner

## Quick Start

### 1. Run Migration (One Time)

```bash
crossbridge migrate \
  --source legacy_tests/ \
  --target pytest \
  --output migrated_tests/
```

CrossBridge creates initial coverage graph and switches to observer mode.

### 2. Enable Hooks (Permanent)

**Pytest**:
```python
# conftest.py
pytest_plugins = ['crossbridge.hooks.pytest_hooks']
```

**Robot**:
```bash
robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener tests/
```

**Playwright**: See TypeScript integration above

### 3. Run Tests Normally

```bash
pytest tests/
robot tests/
npx playwright test
```

CrossBridge observes execution automatically.

### 4. View Intelligence

```bash
# Check coverage evolution
crossbridge coverage status

# Detect flaky tests
crossbridge flaky-tests

# Get AI recommendations
crossbridge recommendations
```

## Benefits

### For Teams

- ✅ **Zero Lock-In**: Remove CrossBridge anytime, tests keep working
- ✅ **No Migration Debt**: Never need to re-migrate
- ✅ **Continuous Value**: Intelligence improves over time
- ✅ **Framework Agnostic**: Works with any test framework

### For Leaders

- ✅ **Low Risk**: Optional hooks, no code ownership
- ✅ **High ROI**: One-time migration → permanent intelligence
- ✅ **Future-Proof**: AI layer evolves with your tests
- ✅ **Platform Play**: Enables entire ecosystem of intelligence tools

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Test Frameworks                       │
│         (pytest | playwright | robot | ...)             │
└───────────────────┬─────────────────────────────────────┘
                    │ Lightweight Hooks
                    │ (emit events)
                    ▼
┌─────────────────────────────────────────────────────────┐
│              CrossBridge Observer Layer                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Hook SDK  │  │ Event Store  │  │ Graph Engine  │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Drift       │  │ Flaky        │  │ AI Analyzer   │  │
│  │ Detector    │  │ Detector     │  │               │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└───────────────────┬─────────────────────────────────────┘
                    │ Intelligence APIs
                    ▼
┌─────────────────────────────────────────────────────────┐
│           Dashboards | CLI | CI/CD Integration          │
│              (Grafana | Slack | Jenkins)                │
└─────────────────────────────────────────────────────────┘
```

## FAQ

**Q: Do I need to re-run migration when I add new tests?**
A: No. CrossBridge automatically detects new tests via hooks.

**Q: What if I disable hooks?**
A: Tests work normally. CrossBridge just stops collecting intelligence.

**Q: Can I use CrossBridge with existing tests (no migration)?**
A: Yes! Enable hooks on existing tests. Migration is optional.

**Q: Does CrossBridge slow down my tests?**
A: Negligible (<5ms overhead per test). Async event emission.

**Q: What if CrossBridge service crashes?**
A: Tests continue running. Hooks fail silently and never block execution.

**Q: Can I export data and stop using CrossBridge?**
A: Yes. Export coverage graph from PostgreSQL. Zero lock-in.

## Next Steps

1. ✅ **Review Architecture**: Understand observer mode
2. ✅ **Enable Hooks**: Add to test frameworks
3. ✅ **Configure Database**: Set up PostgreSQL persistence
4. ✅ **Run Tests**: Execute normally with hooks
5. ✅ **View Insights**: Use Grafana dashboards / CLI

## Support

- **Documentation**: `docs/POST_MIGRATION_INTELLIGENCE.md`
- **Hook SDK API**: `core/observability/hook_sdk.py`
- **Examples**: `examples/hooks/`
- **Issues**: GitHub Issues
