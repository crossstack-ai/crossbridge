# CrossBridge Hook SDK Examples

This directory contains practical examples of using CrossBridge hooks in different test frameworks.

## Examples

### 1. Pytest Integration
- `pytest_example/conftest.py` - Basic pytest hook setup
- `pytest_example/test_api.py` - Manual API call tracking
- `pytest_example/test_ui.py` - Manual UI interaction tracking

### 2. Playwright Integration
- `playwright_example/playwright.config.ts` - Playwright reporter setup
- `playwright_example/tests/example.spec.ts` - Inline hook usage

### 3. Robot Framework Integration
- `robot_example/listener_setup.robot` - Robot listener configuration
- `robot_example/api_test.robot` - API tracking keywords
- `robot_example/ui_test.robot` - UI tracking keywords

## Quick Start

### Pytest

```python
# conftest.py
pytest_plugins = ['crossbridge.hooks.pytest_hooks']

# test_example.py
def test_login():
    response = requests.post("/api/auth/login", json={"user": "admin"})
    
    # Optional: Track API call manually
    from crossbridge.hooks.pytest_hooks import track_api_call
    track_api_call("/api/auth/login", "POST", response.status_code, response.elapsed.total_seconds() * 1000)
```

### Robot Framework

```bash
# Run with listener
robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener tests/

# In .robot file
*** Test Cases ***
Test Login
    ${response}=    POST    /api/auth/login    {"user": "admin"}
    Track API Call    /api/auth/login    POST    ${response.status_code}
```

### Playwright

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';
import { crossbridgeReporter } from 'crossbridge/hooks/playwright_hooks';

export default defineConfig({
  reporter: [['html'], [crossbridgeReporter]]
});
```

## Configuration

All examples can be configured via:

```yaml
# crossbridge.yaml
crossbridge:
  mode: observer
  hooks:
    enabled: true
```

Or environment variables:

```bash
export CROSSBRIDGE_HOOKS_ENABLED=true
export CROSSBRIDGE_MODE=observer
export CROSSBRIDGE_DB_URL=postgresql://user:pass@host:5432/db
```

## Running Examples

```bash
# Pytest
cd examples/hooks/pytest_example
pytest -v

# Robot
cd examples/hooks/robot_example
robot tests/

# Playwright
cd examples/hooks/playwright_example
npx playwright test
```

## Viewing Results

Check Grafana dashboards or query database:

```sql
-- View execution events
SELECT * FROM test_execution_event 
WHERE framework = 'pytest' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Test execution summary
SELECT 
  framework,
  status,
  COUNT(*) as count,
  AVG(duration_ms) as avg_duration_ms
FROM test_execution_event
WHERE event_type = 'test_end'
GROUP BY framework, status;
```
