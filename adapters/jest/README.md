# CrossBridge Jest Reporter

This adapter enables CrossBridge monitoring for Jest tests without requiring any changes to your test code.

## Automatic Usage (Recommended)

Use the CrossBridge universal wrapper:

```bash
crossbridge-run jest tests/
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

### 2. Add reporter to jest.config.js

```javascript
module.exports = {
  reporters: [
    'default',
    '/path/to/adapter/crossbridge_reporter.js'
  ]
};
```

### 3. Run Jest

```bash
jest tests/
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CROSSBRIDGE_ENABLED` | `false` | Enable/disable CrossBridge monitoring |
| `CROSSBRIDGE_API_HOST` | `localhost` | Sidecar API hostname |
| `CROSSBRIDGE_API_PORT` | `8765` | Sidecar API port |

## How It Works

The reporter implements Jest's reporter interface:
- **onRunStart**: Test run begins
- **onTestStart**: Individual test starts
- **onTestResult**: Test completes with results
- **onRunComplete**: Test run finishes

All events are sent to the CrossBridge sidecar via HTTP POST to `/events`.
