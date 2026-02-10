# Migration Guide: Bash Scripts to Unified CLI

This guide helps you migrate from the legacy bash scripts (`crossbridge-run` and `crossbridge-log`) to the new unified Python CLI.

## Why Migrate?

### Benefits of the Unified CLI

✅ **Cross-Platform** - Pure Python works identically on Windows, Linux, and macOS  
✅ **Better Error Messages** - Rich formatting and detailed troubleshooting guidance  
✅ **Consistent Interface** - All CrossBridge features through one command  
✅ **Better Help** - Comprehensive `--help` documentation for every command  
✅ **Faster Startup** - No bash interpreter overhead  
✅ **Better Testing** - Full unit test coverage with pytest  
✅ **Active Development** - New features added to unified CLI first  

### Deprecated Features

⚠️ The bash scripts in `bin/` are **deprecated** but still functional for backward compatibility.  
They will be removed in v1.0.0 (estimated Q3 2026).

## Command Mapping

### Test Execution (crossbridge-run → crossbridge run)

| Legacy Bash Script | New Unified CLI | Notes |
|-------------------|-----------------|-------|
| `./bin/crossbridge-run robot tests/` | `crossbridge run robot tests/` | Direct replacement |
| `./bin/crossbridge-run pytest tests/` | `crossbridge run pytest tests/` | Direct replacement |
| `./bin/crossbridge-run jest tests/` | `crossbridge run jest tests/` | Direct replacement |
| `./bin/crossbridge-run mvn test` | `crossbridge run mvn test` | Direct replacement |
| `crossbridge-run --help` | `crossbridge run --help` | Better formatting |

**Environment variables remain the same:**
- `CROSSBRIDGE_SIDECAR_HOST`
- `CROSSBRIDGE_SIDECAR_PORT`
- `CROSSBRIDGE_ENABLED`
- `CROSSBRIDGE_ADAPTER_DIR`

### Log Parsing (crossbridge-log → crossbridge log)

| Legacy Bash Script | New Unified CLI | Notes |
|-------------------|-----------------|-------|
| `./bin/crossbridge-log output.xml` | `crossbridge log output.xml` | Direct replacement |
| `./bin/crossbridge-log output.xml --output results.json` | `crossbridge log output.xml --output results.json` | Same options |
| `./bin/crossbridge-log output.xml --enable-ai` | `crossbridge log output.xml --enable-ai` | Same behavior |
| `./bin/crossbridge-log output.xml --status FAIL` | `crossbridge log output.xml --status FAIL` | Same filtering |
| `./bin/crossbridge-log output.xml --app-logs app.log` | `crossbridge log output.xml --app-logs app.log` | Same correlation |
| `crossbridge-log --help` | `crossbridge log --help` | Better formatting |

**All command-line options remain compatible.**

## Migration Steps

### Step 1: Install Python Package

If you haven't already, install CrossBridge as a Python package:

```bash
# From source (development)
cd /path/to/crossbridge
pip install -e .

# From PyPI (production)
pip install crossbridge
```

Verify installation:
```bash
crossbridge --help
```

You should see the unified CLI help with all available commands.

### Step 2: Update Scripts Locally

Test the new commands locally before updating CI/CD:

```bash
# Old way (bash)
./bin/crossbridge-run pytest tests/
./bin/crossbridge-log output.xml

# New way (Python)
crossbridge run pytest tests/
crossbridge log output.xml
```

Verify that:
- ✅ Tests execute correctly
- ✅ Monitoring is active (check sidecar logs)
- ✅ Log parsing produces same output
- ✅ All filters and options work as expected

### Step 3: Update CI/CD Pipelines

#### GitHub Actions

**Before:**
```yaml
steps:
  - name: Run tests
    run: ./bin/crossbridge-run pytest tests/
  
  - name: Parse logs
    run: ./bin/crossbridge-log output.xml --output results.json
```

**After:**
```yaml
steps:
  - name: Install CrossBridge
    run: pip install crossbridge
  
  - name: Run tests
    run: crossbridge run pytest tests/
  
  - name: Parse logs
    run: crossbridge log output.xml --output results.json
```

#### Jenkins

**Before:**
```groovy
stage('Test') {
    steps {
        sh './bin/crossbridge-run pytest tests/'
        sh './bin/crossbridge-log output.xml'
    }
}
```

**After:**
```groovy
stage('Test') {
    steps {
        sh 'pip install crossbridge'
        sh 'crossbridge run pytest tests/'
        sh 'crossbridge log output.xml'
    }
}
```

#### GitLab CI

**Before:**
```yaml
test:
  script:
    - ./bin/crossbridge-run pytest tests/
    - ./bin/crossbridge-log output.xml
```

**After:**
```yaml
test:
  before_script:
    - pip install crossbridge
  script:
    - crossbridge run pytest tests/
    - crossbridge log output.xml
```

#### Azure Pipelines

**Before:**
```yaml
- script: ./bin/crossbridge-run pytest tests/
  displayName: 'Run tests'

- script: ./bin/crossbridge-log output.xml
  displayName: 'Parse logs'
```

**After:**
```yaml
- script: pip install crossbridge
  displayName: 'Install CrossBridge'

- script: crossbridge run pytest tests/
  displayName: 'Run tests'

- script: crossbridge log output.xml
  displayName: 'Parse logs'
```

### Step 4: Update Documentation

Update any internal documentation, runbooks, or READMEs that reference the bash scripts:

- Replace `./bin/crossbridge-run` with `crossbridge run`
- Replace `./bin/crossbridge-log` with `crossbridge log`
- Add installation step: `pip install crossbridge`
- Link to official docs: https://docs.crossbridge.dev

### Step 5: Clean Up (Optional)

Once fully migrated, you can:

1. **Remove bash scripts from PATH:**
   ```bash
   # They're still in bin/ for backward compatibility
   # but you don't need them symlinked anywhere
   ```

2. **Add deprecation notice to internal docs:**
   ```
   ⚠️ Using `./bin/crossbridge-run` and `./bin/crossbridge-log` directly
   is deprecated. Please use `crossbridge run` and `crossbridge log` instead.
   ```

3. **Update team communication:**
   - Send team announcement about the migration
   - Update onboarding documentation
   - Add to knowledge base

## Troubleshooting Migration

### Issue: "crossbridge: command not found"

**Cause:** CrossBridge Python package not installed or not in PATH.

**Solution:**
```bash
# Ensure package is installed
pip install crossbridge

# Verify installation
which crossbridge  # Should show path to executable

# If still not found, check pip install location
pip show crossbridge

# May need to add to PATH (rare)
export PATH="$PATH:$(python -m site --user-base)/bin"
```

### Issue: "Different behavior between bash and Python versions"

**Cause:** Environment variables or sidecar configuration differences.

**Solution:**
```bash
# Compare environment
./bin/crossbridge-run pytest tests/ 2>&1 | grep "Sidecar"
crossbridge run pytest tests/ 2>&1 | grep "Sidecar"

# Should show same host:port

# Check environment explicitly
env | grep CROSSBRIDGE
```

### Issue: "Bash script works, Python CLI doesn't"

**Cause:** Different error handling or Python dependencies.

**Solution:**
```bash
# Run with verbose output
crossbridge run pytest tests/ 2>&1 | tee debug.log

# Check Python version (requires 3.8+)
python --version

# Reinstall with dependencies
pip install --force-reinstall crossbridge
```

### Issue: "CI/CD pipeline breaks after migration"

**Cause:** Missing installation step or PATH issues in CI environment.

**Solution:**
```yaml
# Ensure pip is available
- run: python -m pip install --upgrade pip

# Install CrossBridge explicitly
- run: pip install crossbridge

# Verify before use
- run: crossbridge --version
```

## Gradual Migration Strategy

If you have many scripts or pipelines, migrate gradually:

### Phase 1: Run in Parallel (1-2 weeks)
```bash
# Run both for comparison
./bin/crossbridge-run pytest tests/ || exit 1
crossbridge run pytest tests/  # Validate new CLI works
```

### Phase 2: Switch Primary (1-2 weeks)
```bash
# Use new CLI as primary, bash as backup
crossbridge run pytest tests/ || ./bin/crossbridge-run pytest tests/
```

### Phase 3: New CLI Only (Final)
```bash
# Remove bash fallback
crossbridge run pytest tests/
```

## Feature Comparison

| Feature | Bash Scripts | Unified CLI | Notes |
|---------|-------------|-------------|-------|
| Framework detection | ✅ | ✅ | Identical |
| Adapter download | ✅ | ✅ | Identical |
| Environment variables | ✅ | ✅ | Same names |
| Windows support | ⚠️ WSL/Git Bash | ✅ Native | Unified CLI better |
| Error messages | ⚠️ Basic | ✅ Rich formatting | Unified CLI better |
| Help documentation | ⚠️ Basic | ✅ Comprehensive | Unified CLI better |
| AI cost warnings | ✅ | ✅ | Identical |
| Log filtering | ✅ | ✅ | Identical |
| App log correlation | ✅ | ✅ | Identical |
| Intelligence analysis | ✅ | ✅ | Identical |
| Unit tests | ❌ | ✅ | Unified CLI only |
| Active development | ❌ Deprecated | ✅ | Unified CLI only |

## Getting Help

If you encounter issues during migration:

1. **Check the docs:**
   - [Unified CLI Guide](UNIFIED_CLI.md)
   - [README](../README.md)

2. **Report issues:**
   - GitHub Issues: https://github.com/crossstack-ai/crossbridge/issues
   - Include: OS, Python version, error logs, bash vs CLI comparison

3. **Community support:**
   - Slack: crossbridge.slack.com
   - Forum: community.crossbridge.dev

## Timeline

| Date | Milestone |
|------|-----------|
| **February 2026** | Unified CLI released (v0.2.x) |
| **March 2026** | Deprecation warnings added to bash scripts |
| **June 2026** | Last release supporting bash scripts (v0.9.x) |
| **September 2026** | Bash scripts removed (v1.0.0) |

**Recommendation:** Migrate before June 2026 to avoid disruption.

---

**Need help?** Contact support@crossbridge.dev or open an issue on GitHub.
