# ✅ Automatic Sidecar Hook Integration During Migration

**Feature:** CrossBridge automatically configures sidecar observer hooks when transforming tests to a target framework.

**Status:** ✅ IMPLEMENTED  
**Default:** ENABLED (can be disabled via flag)

---

## 🎯 Overview

When you migrate tests using CrossBridge (e.g., Selenium Java → Robot Framework), the sidecar observer hooks are **automatically configured** in the migrated project. This means your transformed tests are immediately observable without any manual setup.

### Before This Feature
1. Migrate tests: `crossbridge translate --source selenium-java --target robot`
2. **Manual Step:** Configure Robot listener
3. **Manual Step:** Add database configuration
4. **Manual Step:** Update test files
5. Run tests

### After This Feature
1. Migrate tests: `crossbridge translate --source selenium-java --target robot`
2. Run tests ✅ (hooks already configured!)

**Zero manual steps required!**

---

## 🚀 Supported Frameworks

All target frameworks automatically get sidecar hooks:

| Target Framework | Hook Type | Auto-Generated Files | Enabled By |
|------------------|-----------|---------------------|------------|
| **Robot Framework** | Robot Listener | `robot_config.py`, `*.robot` (updated) | Listener directive in Settings |
| **Playwright Python** | pytest Plugin | `conftest.py`, `pytest.ini` | pytest_plugins |
| **Playwright TypeScript** | Playwright Reporter | `playwright.config.ts` | reporters array |
| **pytest** | pytest Plugin | `conftest.py`, `pytest.ini` | pytest_plugins |
| **Cypress** | Cypress Plugin | `cypress.config.js`, `cypress/support/e2e.js` | setupNodeEvents |

---

## 📋 How It Works

### Workflow

```
1. User runs translation command
   ↓
2. CrossBridge transforms test files
   ↓
3. MigrationHookIntegrator detects target framework
   ↓
4. Framework-specific hook configuration generated
   ↓
5. Configuration files created/updated
   ↓
6. Test files updated (if needed)
   ↓
7. Migration complete with hooks enabled!
```

---

## 💻 Usage Examples

### Example 1: Selenium Java → Robot Framework

```bash
# Standard migration (hooks enabled by default)
crossbridge translate \
    --source selenium-java \
    --target robot \
    --input src/test/java/ \
    --output robot-tests/
```

**What Gets Created:**
```
robot-tests/
├── *.robot                # Migrated tests
├── robot_config.py        # CrossBridge configuration ⭐ AUTO-GENERATED
└── resources/
    └── keywords.robot
```

**`robot_config.py` content:**
```python
"""
Robot Framework Configuration with CrossBridge Observer

Auto-generated during migration.
To disable, remove the Listener line from test files.
"""

# CrossBridge Configuration
CROSSBRIDGE_ENABLED = True
CROSSBRIDGE_DB_HOST = "10.55.12.99"
CROSSBRIDGE_DB_PORT = 5432
CROSSBRIDGE_DB_NAME = "udp-native-webservices-automation"
CROSSBRIDGE_APPLICATION_VERSION = "v1.0.0"
CROSSBRIDGE_PRODUCT_NAME = "RobotApp"
CROSSBRIDGE_ENVIRONMENT = "test"
```

**Updated `.robot` files:**
```robot
*** Settings ***
Listener    crossbridge.RobotListener    ⭐ AUTO-ADDED
Library     SeleniumLibrary

*** Test Cases ***
Test Login
    # Your migrated test code...
```

**Run immediately:**
```bash
cd robot-tests
robot tests/
# Tests are already being observed! ✅
```

---

### Example 2: Selenium Python → Playwright Python

```bash
# Migration with custom database host
crossbridge translate \
    --source selenium-python \
    --target playwright-python \
    --input tests/ \
    --output playwright-tests/ \
    --sidecar-db-host 192.168.1.100 \
    --sidecar-app-version v2.5.0
```

**What Gets Created:**
```
playwright-tests/
├── tests/
│   └── test_*.py          # Migrated tests
├── conftest.py            # CrossBridge configuration ⭐ AUTO-GENERATED
└── pytest.ini             # pytest configuration ⭐ AUTO-GENERATED
```

**`conftest.py` content:**
```python
"""
pytest configuration with CrossBridge Observer

Auto-generated during migration.
To disable, set crossbridge_enabled = False or remove this section.
"""

import pytest

# CrossBridge Configuration
def pytest_configure(config):
    """Configure CrossBridge observer for pytest"""
    config.option.crossbridge_enabled = True
    config.option.crossbridge_db_host = "192.168.1.100"
    config.option.crossbridge_db_port = 5432
    config.option.crossbridge_db_name = "udp-native-webservices-automation"
    config.option.crossbridge_application_version = "v2.5.0"
    config.option.crossbridge_product_name = "PytestApp"
    config.option.crossbridge_environment = "test"


# Load CrossBridge plugin
pytest_plugins = ["crossbridge.pytest_plugin"]
```

**Run immediately:**
```bash
cd playwright-tests
pytest
# Tests are already being observed! ✅
```

---

### Example 3: Disable Sidecar Hooks

```bash
# Migration WITHOUT automatic hooks
crossbridge translate \
    --source selenium-java \
    --target robot \
    --input src/test/java/ \
    --output robot-tests/ \
    --disable-sidecar
```

**Result:**
- Tests are migrated
- NO hook configuration files created
- Manual setup required if you want observability later

---

### Example 4: Cypress Migration

```bash
crossbridge translate \
    --source selenium-python \
    --target cypress \
    --input tests/ \
    --output cypress-tests/
```

**What Gets Created:**
```
cypress-tests/
├── cypress/
│   ├── e2e/
│   │   └── *.cy.js        # Migrated tests
│   └── support/
│       └── e2e.js         # Auto-tracking ⭐ AUTO-GENERATED
└── cypress.config.js      # CrossBridge plugin ⭐ AUTO-GENERATED
```

**`cypress.config.js` content:**
```javascript
const { defineConfig } = require('cypress');
const crossbridge = require('crossbridge-cypress');

/**
 * Cypress Configuration with CrossBridge Observer
 * Auto-generated during migration.
 * To disable, remove crossbridge.register() call.
 */
module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      // CrossBridge Plugin (auto-configured)
      crossbridge.register(on, {
        enabled: true,
        dbHost: '10.55.12.99',
        dbPort: 5432,
        dbName: 'udp-native-webservices-automation',
        applicationVersion: 'v1.0.0',
        productName: 'CypressApp',
        environment: 'test'
      });
      
      return config;
    },
  },
});
```

**Run immediately:**
```bash
cd cypress-tests
npx cypress run
# Tests are already being observed! ✅
```

---

## 🎛️ Configuration Options

### Command Line Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--enable-sidecar` | ✅ Enabled | Enable automatic hook integration |
| `--disable-sidecar` | ❌ Disabled | Disable automatic hook integration |
| `--sidecar-db-host` | `10.55.12.99` | Database host for observer |
| `--sidecar-app-version` | `v1.0.0` | Application version for tracking |

### Examples

**Custom database:**
```bash
--sidecar-db-host my-postgres.company.com \
--sidecar-app-version v3.2.1
```

**Disable hooks:**
```bash
--disable-sidecar
```

**Default (hooks enabled):**
```bash
# No flag needed, enabled by default
```

---

## 🔧 Manual Configuration Override

Even with auto-generated hooks, you can customize the configuration:

### Robot Framework

Edit `robot_config.py`:
```python
CROSSBRIDGE_DB_HOST = "custom-host.com"
CROSSBRIDGE_APPLICATION_VERSION = "v2.0.0"
```

### pytest

Edit `conftest.py`:
```python
def pytest_configure(config):
    config.option.crossbridge_db_host = "custom-host.com"
    # ... other options
```

### Cypress

Edit `cypress.config.js`:
```javascript
crossbridge.register(on, {
  dbHost: 'custom-host.com',
  applicationVersion: 'v2.0.0'
});
```

---

## 🚫 Disabling Hooks After Migration

If you want to disable hooks after migration:

### Robot Framework
```robot
*** Settings ***
# Listener    crossbridge.RobotListener    ← Comment out or remove
Library     SeleniumLibrary
```

### pytest
```python
# conftest.py
def pytest_configure(config):
    config.option.crossbridge_enabled = False  # ← Set to False
```

### Cypress
```javascript
// cypress.config.js
crossbridge.register(on, {
  enabled: false,  // ← Set to false
  // ... other config
});
```

---

## 📊 Migration Output Example

```bash
$ crossbridge translate --source selenium-java --target robot --input src/test/java/ --output robot-tests/

🔄 CrossBridge Framework Translation
   Source: selenium-java
   Target: robot
   Mode: assistive

📂 Scanning directory: src/test/java/
   Found 24 test files

🔄 Translating files...
   ✅ LoginTest.java → test_login.robot (confidence: 92%)
   ✅ SearchTest.java → test_search.robot (confidence: 88%)
   ✅ CheckoutTest.java → test_checkout.robot (confidence: 90%)
   ... (21 more files)

📊 Translation Summary:
   ✅ Successful: 24
   ❌ Failed: 0
   📈 Average Confidence: 90.5%

💾 Writing files...
   ✅ Saved to: robot-tests/

🔌 Integrating sidecar observer hooks...
   ✅ Sidecar hooks integrated (robot_listener)
   📁 Config: robot_config.py
   📝 Instructions:
      To disable CrossBridge observer in Robot Framework:
      1. Remove 'Listener    crossbridge.RobotListener' from *** Settings ***
      2. Or delete robot_config.py

✅ Migration complete!
   Your tests are ready to run with automatic observability enabled.
   
   Next steps:
   1. cd robot-tests/
   2. robot tests/
   3. View insights at http://10.55.12.99:3000/
```

---

## 🧪 Verification

After migration, verify hooks are working:

### 1. Run Tests
```bash
cd <output-directory>
<run-command>  # robot tests/, pytest, etc.
```

### 2. Check Database
```sql
SELECT test_id, framework, status, event_timestamp
FROM test_execution_event
WHERE framework = '<target-framework>'
ORDER BY event_timestamp DESC
LIMIT 10;
```

### 3. Expected Results
- ✅ Test events appear in database
- ✅ Framework matches target (e.g., 'robot', 'pytest', 'cypress')
- ✅ Status, duration, timestamps populated
- ✅ No errors in test output

---

## 🎯 Benefits

### For Users
1. **Zero Manual Setup** - Hooks configured automatically
2. **Immediate Observability** - Tests tracked from first run
3. **Consistent Configuration** - Same database, same settings
4. **Easy to Disable** - Simple flag or config change
5. **Production Ready** - Auto-generated configs are production-grade

### For Teams
1. **Faster Adoption** - No learning curve for hook setup
2. **Reduced Errors** - No manual configuration mistakes
3. **Standardization** - All projects configured identically
4. **Documentation** - Auto-generated configs are self-documenting
5. **Scalability** - Works for 1 test or 10,000 tests

---

## 📚 Technical Details

### Implementation

**Module:** `core/translation/migration_hooks.py`

**Classes:**
- `MigrationHookConfig` - Configuration for hook integration
- `MigrationHookIntegrator` - Handles framework-specific integration

**Key Methods:**
- `integrate_hooks()` - Main integration orchestrator
- `_integrate_robot_listener()` - Robot Framework specific
- `_integrate_pytest_plugin()` - pytest specific
- `_integrate_playwright_reporter()` - Playwright specific
- `_integrate_cypress_plugin()` - Cypress specific

### Integration Points

**CLI Command:** `cli/commands/translate.py`
- Added flags: `--enable-sidecar`, `--disable-sidecar`, `--sidecar-db-host`, `--sidecar-app-version`
- Calls `_integrate_sidecar_hooks()` after successful migration

**Translation Pipeline:** `core/translation/pipeline.py`
- Hooks called automatically after file generation
- Non-blocking - migration succeeds even if hook integration fails

---

## 🔍 Troubleshooting

### Issue: Hooks not working after migration

**Check:**
1. Are hooks enabled? (default: yes)
2. Is database accessible? (`psql -h <host> -U postgres`)
3. Are configuration files created? (`ls -la <output-dir>`)
4. Any errors in test output? (look for CrossBridge messages)

**Solution:**
```bash
# Re-run migration with verbose mode
crossbridge translate ... --verbose

# Or manually verify config files
cat <output-dir>/conftest.py  # pytest
cat <output-dir>/robot_config.py  # robot
```

---

### Issue: Want to disable hooks temporarily

**Quick disable:**

**Robot:**
```bash
# Set environment variable
export CROSSBRIDGE_ENABLED=false
robot tests/
```

**pytest:**
```bash
# Command line flag
pytest --crossbridge-enabled=false
```

**Cypress:**
```bash
# Edit cypress.config.js and set enabled: false
```

---

### Issue: Want different database for different projects

**Solution:** Edit auto-generated config files with project-specific settings:

```python
# conftest.py or robot_config.py
CROSSBRIDGE_DB_HOST = "project-a-db.company.com"
CROSSBRIDGE_PRODUCT_NAME = "ProjectA"
```

---

## ✅ Summary

**CrossBridge now automatically:**
- ✅ Configures sidecar hooks during migration
- ✅ Creates framework-specific configuration files
- ✅ Updates test files (when needed)
- ✅ Uses migration settings (db host, app version)
- ✅ Provides disable instructions
- ✅ Works for all target frameworks

**Result:**
- **Migrated tests are immediately observable**
- **Zero manual configuration required**
- **Can be disabled with a flag**
- **Production-ready out of the box**

🎉 **Your tests. Your framework. Automatically observable!**

---

## 📖 Related Documentation

- [NO_MIGRATION_FRAMEWORK_SUPPORT.md](NO_MIGRATION_FRAMEWORK_SUPPORT.md) - Sidecar mode for existing tests
- [FRAMEWORK_SUPPORT_COMPLETE.md](FRAMEWORK_SUPPORT_COMPLETE.md) - Complete framework comparison
- [AI_TRANSFORMATION_USAGE.md](docs/AI_TRANSFORMATION_USAGE.md) - Migration mode guide
