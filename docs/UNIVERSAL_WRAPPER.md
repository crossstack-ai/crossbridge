# CrossBridge Universal Wrapper

## Overview

The CrossBridge universal wrapper (`crossbridge-run`) enables **zero-touch integration** with any supported test framework. No code changes, no listener files in your repository, no configuration files to maintain.

## Philosophy

- **Non-invasive**: No changes to your test repository
- **Universal**: One command for all frameworks (Robot, Pytest, Jest, JUnit, Mocha)
- **Dynamic**: Adapters downloaded from sidecar at runtime
- **Framework-agnostic**: Detects framework automatically

## Quick Start

### 1. Install CrossBridge Wrapper

**Linux/macOS:**
```bash
curl -sSL https://crossbridge.io/install.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr -useb https://crossbridge.io/install.ps1 | iex
```

### 2. Start CrossBridge Sidecar

On your monitoring server:
```bash
docker-compose up -d
```

### 3. Run Your Tests

**Instead of:**
```bash
robot tests/
pytest tests/
jest tests/
mocha tests/
mvn test
```

**Use:**
```bash
crossbridge-run robot tests/
crossbridge-run pytest tests/
crossbridge-run jest tests/
crossbridge-run mocha tests/
crossbridge-run mvn test
```

That's it! No code changes needed.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ 1. You run: crossbridge-run robot tests/                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Wrapper detects framework: robot                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Checks sidecar health: http://sidecar:8765/health       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Downloads adapter: GET /adapters/robot                   │
│    Extracts to: ~/.crossbridge/adapters/robot/              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Configures environment:                                  │
│    PYTHONPATH=~/.crossbridge/adapters/robot:$PYTHONPATH    │
│    CROSSBRIDGE_ENABLED=true                                 │
│    CROSSBRIDGE_API_HOST=sidecar                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Executes: robot --listener crossbridge_listener tests/  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Tests send events to sidecar: POST /events              │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

Set these environment variables before running tests:

### Required
```bash
export CROSSBRIDGE_API_HOST=your-sidecar-host  # Default: localhost
export CROSSBRIDGE_API_PORT=8765               # Default: 8765
```

### Optional
```bash
export CROSSBRIDGE_ENABLED=true                # Default: true
export CROSSBRIDGE_ADAPTER_DIR=~/.crossbridge/adapters  # Cache location
```

## Supported Frameworks

| Framework | Command Example | Auto-Configured |
|-----------|----------------|-----------------|
| **Robot Framework** | `crossbridge-run robot tests/` | ✅ Listener |
| **Pytest** | `crossbridge-run pytest tests/` | ✅ Plugin |
| **Jest** | `crossbridge-run jest tests/` | ✅ Reporter |
| **Mocha** | `crossbridge-run mocha tests/` | ✅ Reporter |
| **JUnit/Maven** | `crossbridge-run mvn test` | ⚠️ Manual config required |

### Framework-Specific Notes

#### Robot Framework
- Automatically adds `--listener crossbridge_listener.CrossBridgeListener`
- Works with existing Robot options
- Compatible with Robot 3.x and 4.x

#### Pytest
- Sets `PYTEST_PLUGINS=crossbridge_plugin`
- Compatible with existing pytest plugins
- Works with pytest fixtures and markers

#### Jest
- Adds `--reporters=default --reporters=<adapter>/crossbridge_reporter.js`
- Preserves existing reporters
- Works with Jest 27+

#### Mocha
- Adds `--reporter <adapter>/crossbridge_reporter.js`
- Compatible with Mocha 8+
- Works with existing test files

#### JUnit/Maven
- Downloads adapter with instructions
- Requires one-time pom.xml configuration
- Works with Maven Surefire 2.22+

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

### Debug Mode
```bash
export CROSSBRIDGE_LOG_LEVEL=DEBUG
crossbridge-run pytest tests/
```

### Use with CI/CD

**Jenkins:**
```groovy
pipeline {
    environment {
        CROSSBRIDGE_API_HOST = 'crossbridge-sidecar'
        CROSSBRIDGE_API_PORT = '8765'
        CROSSBRIDGE_ENABLED = 'true'
    }
    stages {
        stage('Test') {
            steps {
                sh 'crossbridge-run robot tests/'
            }
        }
    }
}
```

**GitLab CI:**
```yaml
test:
  variables:
    CROSSBRIDGE_API_HOST: crossbridge-sidecar
    CROSSBRIDGE_API_PORT: "8765"
    CROSSBRIDGE_ENABLED: "true"
  script:
    - crossbridge-run pytest tests/
```

**GitHub Actions:**
```yaml
- name: Run tests
  env:
    CROSSBRIDGE_API_HOST: crossbridge-sidecar
    CROSSBRIDGE_API_PORT: 8765
    CROSSBRIDGE_ENABLED: true
  run: crossbridge-run jest tests/
```

## Troubleshooting

### Wrapper not found after installation
**Solution:** Restart your terminal or run:
```bash
# Linux/macOS
source ~/.bashrc  # or ~/.zshrc

# Windows PowerShell
refreshenv
```

### Cannot reach sidecar
```
⚠️  Cannot reach CrossBridge sidecar at localhost:8765
Tests will run without CrossBridge monitoring
```

**Solutions:**
1. Check sidecar is running: `curl http://localhost:8765/health`
2. Verify hostname: `export CROSSBRIDGE_API_HOST=correct-hostname`
3. Check firewall/network connectivity

### Adapter download fails
```
Failed to download robot adapter
```

**Solutions:**
1. Check sidecar is running: `docker-compose ps`
2. Verify adapter endpoint: `curl http://localhost:8765/adapters/robot`
3. Check disk space: `df -h ~/.crossbridge/`

### Framework not detected
```
Unknown test framework: my-custom-runner
Running tests without CrossBridge monitoring
```

**Solution:** The wrapper auto-detects common frameworks. For custom runners, manually set up the adapter:
```bash
export PYTHONPATH=~/.crossbridge/adapters/robot:$PYTHONPATH
robot tests/
```

## Architecture

### Directory Structure
```
~/.crossbridge/
└── adapters/
    ├── robot/
    │   ├── crossbridge_listener.py
    │   └── README.md
    ├── pytest/
    │   ├── crossbridge_plugin.py
    │   └── README.md
    ├── jest/
    │   ├── crossbridge_reporter.js
    │   └── README.md
    ├── mocha/
    │   ├── crossbridge_reporter.js
    │   └── README.md
    └── junit/
        ├── CrossBridgeListener.java
        └── README.md
```

### Adapter Caching
- Adapters are cached locally in `~/.crossbridge/adapters/`
- Cache refreshed if older than 24 hours
- Manual refresh: `rm -rf ~/.crossbridge/adapters/robot`

### Event Flow
```
Test Framework
    └──> Adapter (listener/plugin/reporter)
         └──> HTTP POST /events
              └──> CrossBridge Sidecar
                   ├──> Event Storage
                   ├──> Statistics Calculation
                   ├──> Failure Pattern Detection
                   └──> Metrics Export
```

## Comparison with Manual Integration

| Feature | Universal Wrapper | Manual Integration |
|---------|------------------|-------------------|
| **Repository Changes** | ❌ None | ✅ Add listener file |
| **Configuration Files** | ❌ None | ✅ Update config files |
| **Framework Switch** | ✅ Automatic | ❌ Manual per framework |
| **Updates** | ✅ Auto-download | ❌ Manual copy |
| **Onboarding** | ✅ 1 command | ❌ Multiple steps |
| **CI/CD Integration** | ✅ Simple env vars | ❌ File management |

## Benefits for Enterprises

### For QA Engineers
- **Zero friction**: Just prefix your test command
- **No learning curve**: Use your existing test commands
- **No maintenance**: Adapters auto-update from sidecar

### For DevOps Teams
- **Consistent integration**: Same approach for all frameworks
- **Easy rollout**: One wrapper install across all teams
- **No repository pollution**: No test infrastructure files in test repos

### For Management
- **Fast adoption**: Minutes to integrate, not days
- **Scalable**: Works for 1 team or 100 teams
- **Non-disruptive**: Doesn't interfere with existing workflows

## Next Steps

1. **Install wrapper**: `curl -sSL https://crossbridge.io/install.sh | bash`
2. **Start sidecar**: `docker-compose up -d`
3. **Run tests**: `crossbridge-run <framework> tests/`
4. **View metrics**: `curl http://localhost:8765/stats`

## Support

- **Documentation**: https://docs.crossbridge.io
- **Issues**: https://github.com/crossbridge/crossbridge/issues
- **Community**: https://discord.gg/crossbridge
- **Enterprise**: support@crossbridge.io
