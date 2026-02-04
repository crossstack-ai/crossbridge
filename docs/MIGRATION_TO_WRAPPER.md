# Migration Guide: From Manual Integration to Universal Wrapper

## Overview

If you previously integrated CrossBridge by manually copying listener files into your test repository, this guide helps you migrate to the **Universal Wrapper** approach for a cleaner, maintenance-free setup.

## Why Migrate?

### Before (Manual Integration)
```
your-test-repo/
├── tests/
├── crossbridge_listener.py    ❌ Test infrastructure in repo
├── .gitignore                  ❌ Must exclude listener
└── requirements.txt            ❌ CrossBridge as dependency
```

**Problems:**
- ❌ Listener file pollutes test repository
- ❌ Must update listener manually across all repos
- ❌ Different setup for each framework
- ❌ Onboarding requires multiple steps

### After (Universal Wrapper)
```
your-test-repo/
├── tests/
└── (no CrossBridge files!)     ✅ Clean repository
```

**Benefits:**
- ✅ No files in your test repository
- ✅ Adapters auto-update from sidecar
- ✅ Same approach for all frameworks
- ✅ One-command onboarding

## Migration Steps

### Step 1: Install Universal Wrapper

**Linux/macOS:**
```bash
curl -sSL https://crossbridge.io/install.sh | bash
```

**Windows:**
```powershell
iwr -useb https://crossbridge.io/install.ps1 | iex
```

### Step 2: Remove Listener Files

#### Robot Framework
```bash
# Remove listener from repository
cd your-test-repo
rm crossbridge_listener.py

# Remove from .gitignore
sed -i '/crossbridge_listener.py/d' .gitignore

# Commit cleanup
git add -A
git commit -m "Remove CrossBridge listener (migrated to universal wrapper)"
```

#### Pytest
```bash
# Remove plugin from repository
rm crossbridge_plugin.py

# Remove from .gitignore
sed -i '/crossbridge_plugin.py/d' .gitignore

# Remove PYTEST_PLUGINS from conftest.py or pytest.ini if added there
```

#### Jest/Mocha
```bash
# Remove reporter
rm crossbridge_reporter.js

# Remove from package.json reporters configuration
# Edit package.json manually or:
npm pkg delete jest.reporters
```

### Step 3: Update CI/CD Pipelines

#### Jenkins

**Before:**
```groovy
stage('Test') {
    steps {
        sh '''
            cp /path/to/crossbridge_listener.py .
            export CROSSBRIDGE_ENABLED=true
            export CROSSBRIDGE_API_HOST=sidecar
            robot tests/
        '''
    }
}
```

**After:**
```groovy
stage('Test') {
    environment {
        CROSSBRIDGE_API_HOST = 'sidecar'
        CROSSBRIDGE_API_PORT = '8765'
    }
    steps {
        sh 'crossbridge-run robot tests/'
    }
}
```

#### GitLab CI

**Before:**
```yaml
test:
  before_script:
    - wget http://sidecar:8765/listener -O crossbridge_listener.py
    - export CROSSBRIDGE_ENABLED=true
  script:
    - robot --listener crossbridge_listener.CrossBridgeListener tests/
```

**After:**
```yaml
test:
  variables:
    CROSSBRIDGE_API_HOST: sidecar
  script:
    - crossbridge-run robot tests/
```

#### GitHub Actions

**Before:**
```yaml
- name: Setup CrossBridge
  run: |
    wget http://sidecar:8765/listener -O crossbridge_listener.py
    echo "CROSSBRIDGE_ENABLED=true" >> $GITHUB_ENV

- name: Run tests
  run: robot --listener crossbridge_listener.CrossBridgeListener tests/
```

**After:**
```yaml
- name: Run tests
  env:
    CROSSBRIDGE_API_HOST: sidecar
  run: crossbridge-run robot tests/
```

### Step 4: Update Local Developer Workflow

#### Before
```bash
# Developer had to:
# 1. Copy listener file
# 2. Set environment variables
# 3. Remember framework-specific syntax

cd project/
cp ~/crossbridge_listener.py .
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_API_HOST=localhost
robot --listener crossbridge_listener.CrossBridgeListener tests/
```

#### After
```bash
# Developer just needs:
cd project/
crossbridge-run robot tests/
```

### Step 5: Update Documentation

Update your team's documentation to remove listener setup instructions:

**Before:**
```markdown
## Running Tests with CrossBridge

1. Copy crossbridge_listener.py to project root
2. Set environment variables:
   export CROSSBRIDGE_ENABLED=true
   export CROSSBRIDGE_API_HOST=localhost
3. Run: robot --listener crossbridge_listener.CrossBridgeListener tests/
```

**After:**
```markdown
## Running Tests with CrossBridge

Run: crossbridge-run robot tests/

Configuration:
- Set CROSSBRIDGE_API_HOST if not using localhost
- See https://docs.crossbridge.io/universal-wrapper
```

## Verification

### Test the Migration

1. **Verify wrapper is installed:**
   ```bash
   which crossbridge-run
   # Should show: /usr/local/bin/crossbridge-run (or similar)
   ```

2. **Test connection:**
   ```bash
   curl http://localhost:8765/health
   # Should return: {"status": "healthy", ...}
   ```

3. **Run tests:**
   ```bash
   crossbridge-run robot tests/
   # Should show: ✅ CrossBridge listener connected to localhost:8765
   ```

4. **Verify events:**
   ```bash
   curl http://localhost:8765/stats
   # Should show test statistics
   ```

### Rollback Plan

If issues occur, you can temporarily revert:

```bash
# 1. Copy listener back from sidecar
curl http://localhost:8765/adapters/robot | tar -xz

# 2. Run tests manually
export CROSSBRIDGE_ENABLED=true
robot --listener crossbridge_listener.CrossBridgeListener tests/
```

## Common Issues

### Wrapper not found after installation

**Solution:**
```bash
# Restart terminal or reload shell
source ~/.bashrc  # or ~/.zshrc

# Verify PATH
echo $PATH | grep crossbridge
```

### Old listener conflicts with wrapper

**Solution:**
```bash
# Remove all listener files
find . -name "crossbridge_listener.py" -delete
find . -name "crossbridge_plugin.py" -delete
find . -name "crossbridge_reporter.js" -delete
```

### CI/CD can't find wrapper

**Solution:** Install wrapper in CI/CD setup stage:

```yaml
before_script:
  - curl -sSL https://crossbridge.io/install.sh | bash
  - export PATH="$HOME/.local/bin:$PATH"
```

## Framework-Specific Notes

### Robot Framework
- Remove `--listener` option from all robot commands
- Remove listener imports from resource files
- Verify no ROBOT_OPTIONS environment variable references listener

### Pytest
- Remove `pytest_plugins = ["crossbridge_plugin"]` from conftest.py
- Remove PYTEST_PLUGINS environment variable
- Verify pytest.ini doesn't reference plugin

### Jest/Mocha
- Remove reporters from jest.config.js / .mocharc.js
- Remove NODE_PATH references to CrossBridge adapter
- Verify package.json doesn't have reporter config

### JUnit/Maven
- Keep pom.xml configuration (still required for JUnit)
- Wrapper will download adapter for reference
- No code changes needed

## Team Rollout Strategy

### Phase 1: Pilot (Week 1)
- Install wrapper on 1-2 developer machines
- Test with non-critical test suites
- Gather feedback

### Phase 2: Team Rollout (Week 2)
- Update CI/CD pipelines
- Install wrapper for all developers
- Update team documentation

### Phase 3: Cleanup (Week 3)
- Remove listener files from all repositories
- Update .gitignore files
- Archive old integration docs

### Phase 4: Monitor (Ongoing)
- Track adoption via sidecar metrics
- Address questions/issues
- Celebrate clean repositories! 🎉

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Repository Files** | +1 per repo | 0 |
| **Setup Steps** | 5+ per developer | 1 |
| **Update Process** | Manual copy to each repo | Auto-download |
| **Onboarding Time** | 30+ minutes | 2 minutes |
| **Framework Switch** | Different steps | Same command |
| **Maintenance** | Per-repo updates | Zero maintenance |

## Support

- **Docs:** https://docs.crossbridge.io/universal-wrapper
- **Issues:** https://github.com/crossbridge/crossbridge/issues
- **Team Chat:** #crossbridge-migration
- **Support:** support@crossbridge.io
