# CrossBridge Unified CLI

CrossBridge now provides a unified command-line interface for all operations. The legacy `crossbridge-run` and `crossbridge-log` bash scripts have been replaced with pure Python implementations accessible through the `crossbridge` command.

## Installation

```bash
# Install from source
pip install -e .

# Or using pip
pip install crossbridge
```

After installation, the `crossbridge` command will be available in your PATH.

## Quick Start

### Run Tests with Monitoring

```bash
# Run Robot Framework tests
crossbridge run robot tests/

# Run Pytest tests
crossbridge run pytest tests/

# Run Jest tests
crossbridge run jest tests/

# Run Mocha tests
crossbridge run mocha tests/

# Run Maven tests
crossbridge run mvn test
```

### Parse and Analyze Logs

```bash
# Parse Robot Framework output
crossbridge log output.xml

# Parse with AI enhancement
crossbridge log output.xml --enable-ai

# Save results to file
crossbridge log output.xml --output results.json

# Filter failed tests only
crossbridge log output.xml --status FAIL

# Filter by test name pattern
crossbridge log output.xml --test-name "Login*"

# Correlate with application logs
crossbridge log output.xml --app-logs app/logs/service.log
```

## Unified Command Structure

All CrossBridge functionality is now accessible through subcommands:

```
crossbridge
├── run             # Execute tests with CrossBridge monitoring
├── log             # Parse and analyze test logs
├── migrate         # Convert tests to Robot Framework
├── transform       # Enhance Robot Framework tests
├── coverage        # Code coverage analysis
├── flaky           # Flaky test detection
├── analyze         # Log analysis and intelligence
├── exec            # Test execution orchestration
├── memory          # Semantic memory management
├── search          # Semantic search
└── sidecar         # Sidecar management
```

## Command Reference

### crossbridge run

Execute tests with automatic CrossBridge monitoring injection.

**Usage:**
```bash
crossbridge run <test-command> [args...]
```

**Supported Frameworks:**
- Robot Framework (robot, pybot)
- Pytest (pytest, py.test)
- Jest (jest, npm test)
- Mocha (mocha)
- JUnit/Maven (mvn test)

**Environment Variables:**
- `CROSSBRIDGE_SIDECAR_HOST` - Sidecar API host (default: localhost)
- `CROSSBRIDGE_SIDECAR_PORT` - Sidecar API port (default: 8765)
- `CROSSBRIDGE_ENABLED` - Enable/disable CrossBridge (default: true)
- `CROSSBRIDGE_ADAPTER_DIR` - Adapter cache directory (default: ~/.crossbridge/adapters)

**Examples:**
```bash
# Run Robot Framework suite
crossbridge run robot tests/login_tests.robot

# Run Pytest with markers
crossbridge run pytest -m smoke tests/

# Run Jest with coverage
crossbridge run jest --coverage tests/

# Disable CrossBridge monitoring
CROSSBRIDGE_ENABLED=false crossbridge run pytest tests/
```

**How it works:**
1. Detects your test framework automatically
2. Downloads the appropriate CrossBridge adapter from the sidecar
3. Injects monitoring (listeners, reporters, plugins) into your test command
4. Executes tests with real-time telemetry streaming to the sidecar

### crossbridge log

Parse and analyze test execution logs with intelligence features.

**Usage:**
```bash
crossbridge log <log-file> [options]
```

**Supported Formats:**
- Robot Framework (output.xml)
- Cypress (cypress-results.json)
- Playwright (playwright-trace.json)
- Behave (behave-results.json)
- Java Cucumber (*Steps.java)

**Options:**
- `--output, -o FILE` - Save parsed results to file
- `--enable-ai` - Enable AI-enhanced analysis (may incur costs)
- `--app-logs, -a FILE` - Application logs for correlation
- `--test-name, -t PATTERN` - Filter by test name pattern (wildcards supported)
- `--test-id, -i ID` - Filter by specific test ID
- `--status, -s STATUS` - Filter by status (PASS/FAIL/SKIP)
- `--error-code, -e CODE` - Filter by error code
- `--pattern, -p PATTERN` - Filter by text pattern
- `--time-from DATETIME` - Filter tests after datetime
- `--time-to DATETIME` - Filter tests before datetime
- `--no-analyze` - Disable intelligence analysis

**Examples:**
```bash
# Basic parsing
crossbridge log output.xml

# AI-enhanced analysis (Cloud AI with costs)
crossbridge log output.xml --enable-ai

# Filter failed tests
crossbridge log output.xml --status FAIL

# Filter by test name pattern
crossbridge log output.xml --test-name "Login*"

# Correlate with app logs
crossbridge log output.xml --app-logs app.log

# Save to file
crossbridge log output.xml --output results.json

# Filter by time range
crossbridge log output.xml --time-from "2026-02-10T10:00:00"
```

**Intelligence Features:**
- **Failure Classification** - Categorizes failures as PRODUCT_DEFECT, AUTOMATION_DEFECT, ENVIRONMENT_ISSUE, etc.
- **Signal Extraction** - Identifies timeout, assertion, locator errors, etc.
- **Code Reference Resolution** - Pinpoints exact test code location
- **Root Cause Analysis** - Explains why tests failed (AI-enhanced)
- **Application Log Correlation** - Links test failures to application errors

## Migration from Legacy Scripts

### Before (Bash Scripts)
```bash
# Old way
./bin/crossbridge-run robot tests/
./bin/crossbridge-log output.xml
```

### Now (Unified CLI)
```bash
# New way
crossbridge run robot tests/
crossbridge log output.xml
```

The bash scripts in `bin/` are retained for backward compatibility but are deprecated. We recommend updating your CI/CD pipelines to use the new unified commands.

## Configuration

CrossBridge can be configured via:

1. **Environment Variables**
   ```bash
   export CROSSBRIDGE_SIDECAR_HOST=remote.host
   export CROSSBRIDGE_SIDECAR_PORT=9000
   export CROSSBRIDGE_ENABLED=true
   ```

2. **Configuration File** (crossbridge.yml)
   ```yaml
   sidecar:
     host: localhost
     port: 8765
     enabled: true
   
   adapters:
     cache_dir: ~/.crossbridge/adapters
   ```

## Troubleshooting

### Sidecar Not Reachable

If you see "CROSSBRIDGE SIDECAR API NOT REACHABLE":

1. **Check if sidecar is running:**
   ```bash
   docker ps | grep crossbridge-sidecar
   ```

2. **Start the sidecar:**
   ```bash
   docker-compose up -d crossbridge-sidecar
   ```

3. **Or run locally:**
   ```bash
   python -m services.sidecar_api
   ```

4. **Verify connection:**
   ```bash
   curl http://localhost:8765/health
   ```

### Framework Not Detected

If CrossBridge can't detect your framework:

```bash
# Check which command you're using
crossbridge run pytest tests/  # ✓ Correct
crossbridge run python -m pytest tests/  # ✗ Won't detect pytest
```

### Tests Run Without Monitoring

If tests run but without CrossBridge monitoring:

1. Check `CROSSBRIDGE_ENABLED` environment variable
2. Verify sidecar is reachable
3. Check adapter cache directory exists
4. Review command output for warnings

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests with CrossBridge
  run: |
    pip install crossbridge
    crossbridge run pytest tests/
    crossbridge log output.xml --output results.json
  env:
    CROSSBRIDGE_SIDECAR_HOST: sidecar.example.com
    CROSSBRIDGE_SIDECAR_PORT: 8765
```

### Jenkins

```groovy
stage('Test with CrossBridge') {
    steps {
        sh 'pip install crossbridge'
        sh 'crossbridge run robot tests/'
        sh 'crossbridge log output.xml --enable-ai'
    }
}
```

### GitLab CI

```yaml
test:
  script:
    - pip install crossbridge
    - crossbridge run pytest tests/
    - crossbridge log pytest-results.xml
```

## Platform Support

- ✅ **Linux** - Full support
- ✅ **macOS** - Full support
- ✅ **Windows** - Full support (pure Python, no bash required)

The unified CLI is pure Python, eliminating previous Windows compatibility issues with bash scripts.

## Getting Help

```bash
# General help
crossbridge --help

# Command-specific help
crossbridge run --help
crossbridge log --help

# View all available commands
crossbridge --help
```

## Advanced Usage

### Custom Adapter Directory

```bash
export CROSSBRIDGE_ADAPTER_DIR=/custom/path/adapters
crossbridge run robot tests/
```

### Remote Sidecar

```bash
export CROSSBRIDGE_SIDECAR_HOST=sidecar.production.com
export CROSSBRIDGE_SIDECAR_PORT=443
crossbridge run pytest tests/
```

### Disable Intelligence Analysis

```bash
# For faster parsing without AI/classification
crossbridge log output.xml --no-analyze
```

### Batch Log Processing

```bash
# Process multiple logs
for log in output-*.xml; do
    crossbridge log "$log" --output "parsed-$(basename $log).json"
done
```

## Performance

- **Adapter Caching** - Adapters are cached for 24 hours to avoid repeated downloads
- **Fast Parsing** - Log parsing is optimized for large files
- **Parallel Analysis** - Intelligence analysis processes tests in parallel
- **Streaming** - Test telemetry streams in real-time during execution

## Security

- **No Credentials in Logs** - Sensitive data is masked automatically
- **Local Adapters** - Adapters run locally, not on remote servers
- **Optional AI** - AI features are opt-in with explicit `--enable-ai` flag
- **Secure Connection** - Supports HTTPS for sidecar communication

## What's New

### v0.2.0 - Unified CLI
- ✨ Merged `crossbridge-run` and `crossbridge-log` into unified `crossbridge` command
- ✨ Pure Python implementation (full Windows support)
- ✨ Improved help documentation
- ✨ Backward compatible with legacy bash scripts
- ✨ Enhanced error messages and troubleshooting guides
- ✨ Consistent command structure across all operations

## Feedback & Support

- **Issues**: https://github.com/crossstack-ai/crossbridge/issues
- **Documentation**: https://docs.crossbridge.dev
- **Community**: https://community.crossbridge.dev

---

**© 2026 CrossStack AI - CrossBridge Test Intelligence Platform**
