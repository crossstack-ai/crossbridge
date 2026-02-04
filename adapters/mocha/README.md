# CrossBridge Mocha Reporter

This adapter enables CrossBridge monitoring for Mocha tests without requiring any changes to your test code.

## Automatic Usage (Recommended)

Use the CrossBridge universal wrapper:

```bash
crossbridge-run mocha tests/
```

The wrapper automatically:
- Downloads this adapter from the sidecar
- Configures the reporter
- Runs your tests with monitoring enabled

## Manual Usage

If you prefer manual setup:

### 1. Set environment variables

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_API_HOST=your-sidecar-host
export CROSSBRIDGE_API_PORT=8765
```

### 2. Run Mocha with reporter

```bash
mocha --reporter /path/to/adapter/crossbridge_reporter.js tests/
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CROSSBRIDGE_ENABLED` | `false` | Enable/disable CrossBridge monitoring |
| `CROSSBRIDGE_API_HOST` | `localhost` | Sidecar API hostname |
| `CROSSBRIDGE_API_PORT` | `8765` | Sidecar API port |

## How It Works

The reporter listens to Mocha events:
- **EVENT_RUN_BEGIN**: Test run starts
- **EVENT_TEST_BEGIN**: Individual test starts
- **EVENT_TEST_PASS**: Test passes
- **EVENT_TEST_FAIL**: Test fails with error
- **EVENT_RUN_END**: Test run completes

All events are sent to the CrossBridge sidecar via HTTP POST to `/events`.
