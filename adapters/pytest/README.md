# CrossBridge Pytest Plugin

This adapter enables CrossBridge monitoring for Pytest tests without requiring any changes to your test code.

## Automatic Usage (Recommended)

Use the CrossBridge universal wrapper:

```bash
crossbridge-run pytest tests/
```

The wrapper automatically:
- Downloads this adapter from the sidecar
- Configures the plugin
- Runs your tests with monitoring enabled

## Manual Usage

If you prefer manual setup:

### 1. Set environment variables

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_API_HOST=your-sidecar-host
export CROSSBRIDGE_API_PORT=8765
export PYTHONPATH=/path/to/adapter:$PYTHONPATH
export PYTEST_PLUGINS=crossbridge_plugin
```

### 2. Run Pytest

```bash
pytest tests/
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CROSSBRIDGE_ENABLED` | `false` | Enable/disable CrossBridge monitoring |
| `CROSSBRIDGE_API_HOST` | `localhost` | Sidecar API hostname |
| `CROSSBRIDGE_API_PORT` | `8765` | Sidecar API port |
| `PYTEST_PLUGINS` | - | Comma-separated list of plugins to load |

## How It Works

The plugin uses Pytest hooks:
- **pytest_sessionstart**: Test session begins
- **pytest_sessionfinish**: Test session completes
- **pytest_runtest_protocol**: Test item execution wrapper
- **pytest_runtest_makereport**: Captures test results (pass/fail)

All events are sent to the CrossBridge sidecar via HTTP POST to `/events`.
