# CrossBridge Listeners

Lightweight listeners for sending test framework events to remote CrossBridge sidecar.

## Installation

```bash
# Install from GitHub (development)
pip install git+https://github.com/crossstack-ai/crossbridge.git#subdirectory=listeners
```

## Usage

### Robot Framework

```bash
# Set environment variables (replace <sidecar-host> with your server IP/hostname)
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=<sidecar-host>
export CROSSBRIDGE_SIDECAR_PORT=8765

# Run tests with listener
robot --listener crossbridge_listeners.robot.CrossBridgeListener tests/
```

### Windows PowerShell

```powershell
# Replace <sidecar-host> with your server IP/hostname
$env:CROSSBRIDGE_ENABLED="true"
$env:CROSSBRIDGE_SIDECAR_HOST="<sidecar-host>"
$env:CROSSBRIDGE_SIDECAR_PORT="8765"

robot --listener crossbridge_listeners.robot.CrossBridgeListener tests/
```

## Features

- ✅ Lightweight (no dependencies except `requests`)
- ✅ Fail-open design (never blocks test execution)
- ✅ Works with remote CrossBridge sidecar
- ✅ Automatic connection health check
- ✅ No configuration files needed

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CROSSBRIDGE_ENABLED` | `false` | Enable/disable listener |
| `CROSSBRIDGE_SIDECAR_HOST` | `localhost` | Sidecar server hostname/IP |
| `CROSSBRIDGE_SIDECAR_PORT` | `8765` | Sidecar server port |

## License

MIT
