# CrossBridge AI: NO MIGRATION MODE Framework Support

**CrossBridge AI works as a pure SIDECAR observer - NO test migration required!**

Your existing tests run exactly as they always have. CrossBridge AI simply watches and learns.

## ✅ Supported Frameworks (NO MIGRATION MODE)

| Framework | Type | Hook/Plugin | Migration Required |
|-----------|------|-------------|-------------------|
| **Selenium Java** | UI | TestNG/JUnit Listener | ❌ NO |
| **Selenium Java BDD** | UI+BDD | Cucumber + TestNG Listener | ❌ NO |
| **Selenium Java + RestAssured** | UI+API | TestNG Listener | ❌ NO |
| **Selenium .NET SpecFlow** | UI+BDD | SpecFlow Plugin | ❌ NO |
| **Selenium Python pytest** | UI | pytest Plugin | ❌ NO |
| **Selenium Python Robot** | UI | Robot Listener | ❌ NO |
| **Requests Python Robot** | API | Robot Listener | ❌ NO |
| **Cypress** | UI | Cypress Plugin | ❌ NO |
| **Playwright** | UI | Playwright Reporter | ❌ NO |

**All work WITHOUT changing your test code!**

---

## 🚀 Quick Start (5 Minutes)

### 1. Selenium Java (TestNG or JUnit)

```xml
<!-- pom.xml - Add dependency -->
<dependency>
  <groupId>com.crossbridge</groupId>
  <artifactId>crossbridge-java</artifactId>
  <version>1.0.0</version>
</dependency>
```

```xml
<!-- testng.xml - Add listener -->
<suite name="MyTests">
  <listeners>
    <listener class-name="com.crossbridge.CrossBridgeListener"/>
  </listeners>
  
  <test name="Test1">
    <classes>
      <class name="com.example.MyTest"/>
    </classes>
  </test>
</suite>
```

```bash
# Run tests with CrossBridge enabled
mvn test -Dcrossbridge.enabled=true \
         -Dcrossbridge.db.host=10.55.12.99 \
         -Dcrossbridge.application.version=v2.0.0
```

**That's it!** Your tests run normally, CrossBridge observes in the background.

---

### 2. Selenium Java BDD (Cucumber)

```xml
<!-- Same pom.xml as above -->
```

```xml
<!-- testng.xml - Same listener -->
<listeners>
  <listener class-name="com.crossbridge.CrossBridgeListener"/>
</listeners>
```

The listener auto-detects Cucumber and tags tests as `selenium-java-bdd`.

---

### 3. Selenium Java + RestAssured

```xml
<!-- Same pom.xml as above -->
```

The listener auto-detects RestAssured and tags tests as `selenium-java-restassured`.

**No code changes - just add the listener!**

---

### 4. Selenium .NET SpecFlow

```bash
# Install NuGet package
dotnet add package CrossBridge.SpecFlow
```

```json
// specflow.json - Add plugin
{
  "plugins": [
    {
      "name": "CrossBridge",
      "parameters": {
        "enabled": "true"
      }
    }
  ]
}
```

```bash
# Set environment variables
$env:CROSSBRIDGE_ENABLED = "true"
$env:CROSSBRIDGE_DB_HOST = "10.55.12.99"
$env:CROSSBRIDGE_APPLICATION_VERSION = "v2.0.0"

# Run tests normally
dotnet test
```

**Zero changes to .feature files or step definitions!**

---

### 5. Selenium Python pytest

```bash
# Install CrossBridge
pip install crossbridge
```

```ini
# pytest.ini - Enable plugin
[pytest]
plugins = crossbridge
```

```python
# conftest.py - Configure (optional)
def pytest_configure(config):
    config.option.crossbridge_enabled = True
    config.option.crossbridge_db_host = "10.55.12.99"
    config.option.crossbridge_application_version = "v2.0.0"
```

```bash
# Or via command line
pytest --crossbridge-enabled=true \
       --crossbridge-db-host=10.55.12.99 \
       --crossbridge-application-version=v2.0.0
```

**Your existing tests run unchanged!**

---

### 6. Selenium Python Robot Framework

```bash
# Install CrossBridge
pip install crossbridge
```

```robot
*** Settings ***
Library    SeleniumLibrary
Listener   crossbridge.RobotListener

*** Test Cases ***
My Test
    Open Browser    https://example.com    chrome
    # ... your existing test code ...
```

```bash
# Run with environment variables
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_DB_HOST=10.55.12.99
export CROSSBRIDGE_APPLICATION_VERSION=v2.0.0

robot tests/
```

**Just add the Listener line - no other changes!**

---

### 7. Requests Python Robot (API Framework)

```robot
*** Settings ***
Library    RequestsLibrary
Listener   crossbridge.RobotListener

*** Test Cases ***
API Test
    Create Session    api    https://api.example.com
    ${response}=    GET On Session    api    /users
    # ... your existing API test code ...
```

**Same listener works for UI and API tests!**

---

### 8. Cypress

```bash
# Install plugin
npm install crossbridge-cypress
```

```javascript
// cypress.config.js - Register plugin
const { defineConfig } = require('cypress');
const crossbridge = require('crossbridge-cypress');

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      crossbridge.register(on, {
        enabled: true,
        dbHost: '10.55.12.99',
        applicationVersion: 'v2.0.0'
      });
      
      return config;
    }
  }
});
```

```javascript
// cypress/support/e2e.js - Optional automatic tracking
import 'crossbridge-cypress/support';
```

```bash
# Run tests normally
npx cypress run
```

**No changes to your test specs!**

---

## 🎯 Key Design Principles

### 1. **Pure Observer Pattern**
CrossBridge NEVER:
- ❌ Controls test execution
- ❌ Modifies test behavior
- ❌ Requires test code changes
- ❌ Fails tests if observer fails

### 2. **Automatic NEW Test Handling**
When CrossBridge sees a `test_id` it's never seen before:
1. ✅ Automatically creates database entry
2. ✅ Automatically tracks lifecycle (NEW → ACTIVE)
3. ✅ Automatically builds coverage graph
4. ✅ Automatically feeds AI analyzers
5. ❌ NO remigration required
6. ❌ NO manual registration needed

### 3. **Framework Detection**
CrossBridge auto-detects your framework:
- Java class names (Cucumber, RestAssured)
- Python modules (pytest, Robot)
- JavaScript test runners (Cypress, Playwright)
- .NET assemblies (SpecFlow)

### 4. **Configuration Priority**
1. System properties / Environment variables (highest)
2. Configuration files (pytest.ini, cypress.config.js, etc.)
3. Default values (lowest)

---

## 📊 What CrossBridge Tracks (Automatically)

For every test execution:

```json
{
  "test_id": "com.example.LoginTest.testValidLogin",
  "test_name": "testValidLogin",
  "framework": "selenium-java",
  "status": "passed",
  "duration_seconds": 5.23,
  "application_version": "v2.0.0",
  "product_name": "MyApp",
  "environment": "test",
  "coverage": {
    "apis": ["POST /api/login", "GET /api/user"],
    "pages": ["LoginPage", "DashboardPage"]
  },
  "metadata": {
    "browser": "chrome",
    "tags": ["smoke", "critical"]
  }
}
```

All tracked automatically - no instrumentation needed!

---

## 🧠 Release Stage AI Features (Also Automatic)

Once tests are tracked, CrossBridge AI analyzes:

### 1. **Flaky Test Prediction**
```python
# Automatic analysis after test execution
flaky_tests = ai.predict_flaky_tests(project_id="MyApp")
for test in flaky_tests:
    print(f"{test.test_id}: {test.probability:.1%} flaky")
    print(f"Reason: {test.reason}")
```

### 2. **Coverage Gaps**
```python
# Finds APIs/pages with zero test coverage
gaps = ai.find_coverage_gaps(project_id="MyApp")
for gap in gaps:
    print(f"Uncovered: {gap.node_id} (severity: {gap.severity})")
    print(f"Suggestions: {gap.suggestions}")
```

### 3. **Refactor Recommendations**
```python
# Detects slow or complex tests
refactors = ai.get_refactor_recommendations(project_id="MyApp")
for rec in refactors:
    print(f"{rec.test_id}: {rec.issue_type}")
    print(f"Metrics: {rec.metrics}")
```

### 4. **Risk Scores**
```python
# Calculates risk scores for all tests
risks = ai.calculate_risk_scores(project_id="MyApp")
for risk in risks:
    print(f"{risk.test_id}: {risk.priority} priority (score: {risk.risk_score:.2f})")
```

### 5. **Auto-Generation Suggestions**
```python
# Suggests new tests for gaps (requires approval)
suggestions = ai.suggest_test_generation(project_id="MyApp")
for suggestion in suggestions:
    if user_approves(suggestion):
        create_test_from_template(suggestion.template)
```

**All AI features operate on metadata only - never access your code!**

---

## 🔧 Configuration Options

### Environment Variables (All Frameworks)

```bash
# Enable/disable CrossBridge
CROSSBRIDGE_ENABLED=true

# Database connection
CROSSBRIDGE_DB_HOST=10.55.12.99
CROSSBRIDGE_DB_PORT=5432
CROSSBRIDGE_DB_NAME=udp-native-webservices-automation
CROSSBRIDGE_DB_USER=postgres
CROSSBRIDGE_DB_PASSWORD=admin

# Application metadata
CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
CROSSBRIDGE_PRODUCT_NAME=MyApp
CROSSBRIDGE_ENVIRONMENT=test
```

### Framework-Specific

**Java (System Properties):**
```bash
-Dcrossbridge.enabled=true
-Dcrossbridge.db.host=10.55.12.99
-Dcrossbridge.application.version=v2.0.0
```

**Python (pytest.ini):**
```ini
[pytest]
crossbridge_enabled = true
crossbridge_db_host = 10.55.12.99
crossbridge_application_version = v2.0.0
```

**JavaScript (cypress.config.js):**
```javascript
crossbridge.register(on, {
  enabled: true,
  dbHost: '10.55.12.99',
  applicationVersion: 'v2.0.0'
});
```

---

## 🎬 Real-World Example

**Before CrossBridge:**
```java
@Test
public void testLogin() {
    driver.get("https://app.example.com");
    driver.findElement(By.id("username")).sendKeys("user");
    driver.findElement(By.id("password")).sendKeys("pass");
    driver.findElement(By.id("login")).click();
    
    assertTrue(driver.findElement(By.id("dashboard")).isDisplayed());
}
```

**After CrossBridge:**
```java
@Test
public void testLogin() {
    driver.get("https://app.example.com");
    driver.findElement(By.id("username")).sendKeys("user");
    driver.findElement(By.id("password")).sendKeys("pass");
    driver.findElement(By.id("login")).click();
    
    assertTrue(driver.findElement(By.id("dashboard")).isDisplayed());
}
```

**Exactly the same!** CrossBridge observes from the TestNG listener.

---

## 📈 What You Get

### Day 1: Add listener/plugin
- ✅ Test execution tracking
- ✅ Duration monitoring
- ✅ Success/failure trends

### Week 1: Historical data builds
- ✅ Flaky test detection
- ✅ Performance baselines
- ✅ Lifecycle tracking (NEW → ACTIVE → STABLE → DEPRECATED)

### Month 1: Full intelligence
- ✅ Coverage gap analysis
- ✅ Risk-based prioritization
- ✅ Test generation suggestions
- ✅ Refactor recommendations

**All without changing a single test!**

---

## 🚨 Failure Handling

If CrossBridge fails (database down, network issue, etc.):
1. ❌ Test execution continues normally
2. ⚠️ Warning logged to console
3. ✅ Your CI/CD pipeline is NOT affected

**CrossBridge failure never fails your tests!**

---

## 🔍 Verification

After adding CrossBridge, verify it's working:

```bash
# Check database for events
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation

SELECT test_id, status, framework, event_timestamp 
FROM test_execution_event 
ORDER BY event_timestamp DESC 
LIMIT 10;
```

You should see your test executions appearing automatically!

---

## 📚 Framework Files

| Framework | Hook File | Location |
|-----------|-----------|----------|
| Java | `java_listener.py` | `core/observability/hooks/` |
| SpecFlow | `specflow_plugin.cs` | `core/observability/hooks/` |
| Cypress | `cypress_plugin.js` | `core/observability/hooks/` |
| pytest | `pytest_plugin.py` | `adapters/pytest/` |
| Robot | `robot_listener.py` | `adapters/robot/` |
| Playwright | `playwright_reporter.py` | `adapters/playwright/` |

---

## 🎯 Summary

**CrossBridge = Zero Migration Testing Intelligence**

1. **Add a listener/plugin** (5 minutes)
2. **Run your tests as normal** (no changes)
3. **Get continuous intelligence** (automatic)

No migration. No refactoring. No risk.

**Your tests. Your frameworks. Your way. CrossBridge just watches and learns.**

---

## 💡 Next Steps

1. Choose your framework from the list above
2. Follow the 5-minute Quick Start
3. Run your tests once to verify
4. Watch CrossBridge build intelligence automatically

Questions? See `docs/AI_TRANSFORMATION_USAGE.md` for advanced features.
