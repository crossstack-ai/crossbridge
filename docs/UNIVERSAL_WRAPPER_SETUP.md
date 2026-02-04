# CrossBridge Universal Wrapper - Quick Setup Guide

The universal wrapper (`crossbridge-run`) enables **zero-touch integration** - run your tests with CrossBridge monitoring without any code changes or manual listener installation.

## What Was Added

### 1. New Sidecar API Endpoints

**Health Check:**
```bash
curl http://localhost:8765/health
# Returns: {"status": "healthy", "uptime_seconds": 1234, ...}
```

**Readiness Probe (Kubernetes-compatible):**
```bash
curl http://localhost:8765/ready
# Returns: {"status": "ready", "queue_utilization": "100/5000", "queue_percent": 2.0}
# HTTP 200 if ready, 503 if degraded (queue >90% full)
```

**List Available Adapters:**
```bash
curl http://localhost:8765/adapters
```

**Download Framework Adapter:**
```bash
curl http://localhost:8765/adapters/robot -o robot-adapter.tar.gz
curl http://localhost:8765/adapters/pytest -o pytest-adapter.tar.gz
curl http://localhost:8765/adapters/jest -o jest-adapter.tar.gz
```

**View Configuration:**
```bash
curl http://localhost:8765/config
```

### 2. Supported Frameworks

All adapters in the `adapters/` directory are automatically available:

- ✅ **robot** - Robot Framework
- ✅ **pytest** - Python Pytest
- ✅ **jest** - JavaScript Jest
- ✅ **mocha** - JavaScript Mocha  
- ✅ **cypress** - Cypress E2E
- ✅ **playwright** - Playwright
- ✅ **java** - Java/JUnit
- ✅ **restassured_java** - REST Assured (Java)
- ✅ **selenium_java** - Selenium (Java)
- ✅ **selenium_pytest** - Selenium (Python/Pytest)
- ✅ **selenium_behave** - Selenium (Python/Behave)
- ✅ **selenium_dotnet** - Selenium (.NET)
- ✅ **selenium_bdd_java** - Selenium BDD (Java)
- ✅ **selenium_specflow_dotnet** - Selenium SpecFlow (.NET)

## How to Use

### Step 1: Update Sidecar on Linux Server

```bash
# Pull latest changes
cd /path/to/crossbridge
git pull origin dev

# Rebuild and restart sidecar
docker compose -f docker-compose-remote-sidecar.yml down
docker compose -f docker-compose-remote-sidecar.yml up -d --build
```

### Step 2: Install Universal Wrapper on Test Machines

**Linux/macOS:**
```bash
# Download the wrapper script
curl -o /usr/local/bin/crossbridge-run \
  https://raw.githubusercontent.com/crossstack-ai/crossbridge/dev/bin/crossbridge-run

# Make executable
chmod +x /usr/local/bin/crossbridge-run
```

**Windows (PowerShell):**
```powershell
# Download to local bin directory
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crossstack-ai/crossbridge/dev/bin/crossbridge-run.ps1" `
  -OutFile "$env:USERPROFILE\bin\crossbridge-run.ps1"

# Add to PATH (one-time setup)
$env:PATH += ";$env:USERPROFILE\bin"
```

### Step 3: Configure Environment

Set these environment variables on your test machines:

```bash
# Linux/macOS
export CROSSBRIDGE_API_HOST=10.60.75.145  # Your sidecar server IP
export CROSSBRIDGE_API_PORT=8765
export CROSSBRIDGE_ENABLED=true

# Windows (PowerShell)
$env:CROSSBRIDGE_API_HOST="10.60.75.145"
$env:CROSSBRIDGE_API_PORT="8765"
$env:CROSSBRIDGE_ENABLED="true"
```

Or create a `.env` file:
```bash
CROSSBRIDGE_API_HOST=10.60.75.145
CROSSBRIDGE_API_PORT=8765
CROSSBRIDGE_ENABLED=true
```

### Step 4: Run Your Tests

**Instead of:**
```bash
robot tests/
pytest tests/
jest tests/
mocha tests/
```

**Use:**
```bash
crossbridge-run robot tests/
crossbridge-run pytest tests/
crossbridge-run jest tests/
crossbridge-run mocha tests/
```

That's it! No code changes needed.

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│ 1. You run: crossbridge-run robot tests/                    │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. Wrapper checks: http://10.60.75.145:8765/health          │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. Downloads adapter: GET /adapters/robot → robot.tar.gz    │
│    Extracts to: ~/.crossbridge/adapters/robot/              │
│    (Cached for 24 hours)                                     │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. Sets environment:                                         │
│    PYTHONPATH=~/.crossbridge/adapters/robot:$PYTHONPATH    │
│    CROSSBRIDGE_SIDECAR_HOST=10.60.75.145                    │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. Executes: robot --listener crossbridge_listener tests/   │
│    (Options placed BEFORE test path for Robot compatibility) │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. Tests send events: POST http://10.60.75.145:8765/events  │
└──────────────────────────────────────────────────────────────┘
```

## Testing the Setup

### 1. Test Sidecar Adapter Endpoint

```bash
# List available adapters
curl http://10.60.75.145:8765/adapters | jq

# Expected output:
{
  "adapters": [
    {
      "name": "robot",
      "description": "Robot Framework adapter",
      "download_url": "/adapters/robot"
    },
    ...
  ],
  "total": 15
}
```

### 2. Download an Adapter Manually

```bash
# Download Robot adapter
curl -o robot-adapter.tar.gz http://10.60.75.145:8765/adapters/robot

# Extract and inspect
tar -xzf robot-adapter.tar.gz
ls -la robot/
```

### 3. Test Wrapper (Dry Run)

```bash
# Set debug mode
export CROSSBRIDGE_LOG_LEVEL=DEBUG

# Run with wrapper
crossbridge-run robot --help

# Should show:
# [CrossBridge] ✅ Connected to CrossBridge sidecar at 10.60.75.145:8765
# [CrossBridge] Detected framework: robot
# [CrossBridge] Using cached robot adapter
# [CrossBridge] Robot Framework configured with CrossBridge listener
```

### 4. Run Actual Tests

```bash
# Your existing test command
crossbridge-run robot tests/

# Check sidecar logs
ssh your-linux-server
docker logs -f crossbridge-sidecar

# Should see enhanced logs:
# Event: test_start | test='Your Test Name' | tags=['P1']
# Event: test_end | test='Your Test Name' | status=PASS | elapsed=2.34s
```

## Advantages Over Manual Installation

| Feature | Manual Listener | Universal Wrapper |
|---------|----------------|-------------------|
| **Installation** | `pip install git+...` | One-time wrapper download |
| **Updates** | Manual `pip install --upgrade` | Auto-updated from sidecar |
| **Command** | `robot --listener crossbridge_listeners...` | `crossbridge-run robot` |
| **Multi-framework** | Install per framework | One wrapper for all |
| **CI/CD** | Different setup per framework | Consistent across all |
| **Maintenance** | Update on each machine | Central sidecar update |

## Advanced Usage

### Custom Adapter Location

```bash
export CROSSBRIDGE_ADAPTER_DIR=/custom/path
crossbridge-run robot tests/
```

### Disable CrossBridge Temporarily

```bash
export CROSSBRIDGE_ENABLED=false
crossbridge-run robot tests/  # Runs without monitoring
```

### Force Adapter Re-download

```bash
rm -rf ~/.crossbridge/adapters/robot
crossbridge-run robot tests/
```

### Use in CI/CD

**Jenkins:**
```groovy
pipeline {
    environment {
        CROSSBRIDGE_API_HOST = '10.60.75.145'
        CROSSBRIDGE_API_PORT = '8765'
        CROSSBRIDGE_ENABLED = 'true'
    }
    stages {
        stage('Setup') {
            steps {
                sh 'curl -o /tmp/crossbridge-run https://raw.githubusercontent.com/.../crossbridge-run'
                sh 'chmod +x /tmp/crossbridge-run'
            }
        }
        stage('Test') {
            steps {
                sh '/tmp/crossbridge-run robot tests/'
            }
        }
    }
}
```

**GitLab CI:**
```yaml
variables:
  CROSSBRIDGE_API_HOST: "10.60.75.145"
  CROSSBRIDGE_API_PORT: "8765"
  CROSSBRIDGE_ENABLED: "true"

before_script:
  - curl -o /usr/local/bin/crossbridge-run https://raw.githubusercontent.com/.../crossbridge-run
  - chmod +x /usr/local/bin/crossbridge-run

test:
  script:
    - crossbridge-run robot tests/
```

## Troubleshooting

### Wrapper Can't Connect to Sidecar

**Problem:** `Cannot reach CrossBridge sidecar at 10.60.75.145:8765`

**Solution:**
1. Check sidecar is running: `curl http://10.60.75.145:8765/health`
2. Check firewall allows port 8765
3. Verify CROSSBRIDGE_API_HOST is set correctly

### Adapter Download Fails

**Problem:** `Failed to download robot adapter`

**Solution:**
1. Check sidecar logs: `docker logs crossbridge-sidecar`
2. Test endpoint directly: `curl http://10.60.75.145:8765/adapters/robot`
3. Check adapters directory exists in container

### Tests Run But No Events in Sidecar

**Problem:** Tests execute but sidecar shows no events

**Solution:**
1. Check wrapper actually injected listener: Add `CROSSBRIDGE_LOG_LEVEL=DEBUG`
2. Verify adapter was downloaded: `ls ~/.crossbridge/adapters/robot`
3. Check test machine can reach sidecar: `curl http://10.60.75.145:8765/health`
4. Verify sidecar is ready: `curl http://10.60.75.145:8765/ready`

### Robot Framework Parsing Errors

**Problem:** `Parsing 'E:\--listener' failed: File or directory to execute does not exist`

**Solution:** This issue was fixed in the latest version. The wrapper now correctly places `--listener` options BEFORE the test path. Update your wrapper:
```bash
# Linux/macOS
curl -o /usr/local/bin/crossbridge-run \
  https://raw.githubusercontent.com/crossstack-ai/crossbridge/dev/bin/crossbridge-run
chmod +x /usr/local/bin/crossbridge-run

# Windows (Git Bash)
curl -o crossbridge-run \
  https://raw.githubusercontent.com/crossstack-ai/crossbridge/dev/bin/crossbridge-run
chmod +x crossbridge-run
```

## Next Steps

1. **Roll out to all test machines** - Just set environment variables and install wrapper
2. **Update CI/CD pipelines** - Replace manual commands with `crossbridge-run`
3. **Monitor centrally** - All tests now visible in sidecar logs
4. **Enable Grafana** - Visualize test execution across all machines

## Comparison: Three Options

| Aspect | Option 1: Pip Install | Option 2: Universal Wrapper | Option 3: Docker |
|--------|----------------------|----------------------------|------------------|
| **Setup** | pip install per machine | One-time wrapper install | Mount tests in container |
| **Command** | `robot --listener...` | `crossbridge-run robot` | Inside container |
| **Updates** | Manual per machine | Auto from sidecar | Rebuild container |
| **Best For** | Single machine | Multiple machines | CI/CD, isolation |

For your use case (multiple Windows test machines), **Option 2 (Universal Wrapper)** is ideal!
