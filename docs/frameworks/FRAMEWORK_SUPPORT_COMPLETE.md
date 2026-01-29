# CrossBridge Framework Support Summary

**Last Updated:** January 18, 2026

## Executive Summary

CrossBridge now supports **TWO operational modes**:

1. **NO MIGRATION MODE (Sidecar Observer)** - Work with 8+ frameworks without any test code changes
2. **MIGRATION MODE (Full Transformation)** - Convert legacy tests to modern frameworks

---

## 1️⃣ NO MIGRATION MODE (Sidecar Observer)

### Concept

CrossBridge acts as a **pure observer** that monitors your existing test executions without requiring any migration or test code changes. Simply add a listener/plugin to your test framework, and CrossBridge automatically:

- ✅ Tracks test execution (status, duration, errors)
- ✅ Builds coverage graphs (APIs, pages, components)
- ✅ Detects NEW tests automatically (no remigration needed)
- ✅ Analyzes for flakiness, performance, and quality
- ✅ Provides AI-powered recommendations

**Key Principle:** Your tests run exactly as they always have. CrossBridge never controls execution or modifies behavior.

---

### Supported Frameworks

| # | Framework | Type | Status | Hook Type | Files |
|---|-----------|------|--------|-----------|-------|
| 1 | **Selenium Java** | UI | ✅ READY | TestNG/JUnit Listener | `java_listener.py` |
| 2 | **Selenium Java BDD (Cucumber)** | UI+BDD | ✅ READY | TestNG Listener (auto-detect) | `java_listener.py` |
| 3 | **Selenium Java + RestAssured** | UI+API | ✅ READY | TestNG Listener (auto-detect) | `java_listener.py` |
| 4 | **Selenium .NET SpecFlow** | UI+BDD | ✅ READY | SpecFlow Plugin | `specflow_plugin.cs` |
| 5 | **Selenium Python pytest** | UI | ✅ READY | pytest Plugin | `pytest_plugin.py` |
| 6 | **Selenium Python Robot** | UI | ✅ READY | Robot Listener | `robot_listener.py` |
| 7 | **Requests Python Robot (API)** | API | ✅ READY | Robot Listener | `robot_listener.py` |
| 8 | **Cypress** | UI | ✅ READY | Cypress Plugin | `cypress_plugin.js` |
| 9 | **Playwright** | UI | ✅ READY | Playwright Reporter | `playwright_reporter.py` |

**Total: 9 frameworks supported without migration**

---

### Implementation Details

#### Selenium Java (All Variants)

**Location:** `core/observability/hooks/java_listener.py`

**Generates:**
- `CrossBridgeListener.java` (TestNG)
- `CrossBridgeJUnitListener.java` (JUnit)

**Setup:**
```xml
<!-- testng.xml -->
<listeners>
  <listener class-name="com.crossbridge.CrossBridgeListener"/>
</listeners>
```

**Run:**
```bash
mvn test -Dcrossbridge.enabled=true \
         -Dcrossbridge.db.host=10.55.12.99 \
         -Dcrossbridge.application.version=v2.0.0
```

**Auto-Detection:**
- Detects Cucumber → tags as `selenium-java-bdd`
- Detects RestAssured → tags as `selenium-java-restassured`
- Otherwise → tags as `selenium-java`

**Database Events:**
- `test_start`: On `@Test` method start
- `test_end`: On success/failure/skip
- Extracts: test_id, duration, error_message, stack_trace, parameters

---

#### Selenium .NET SpecFlow

**Location:** `core/observability/hooks/specflow_plugin.cs`

**Setup:**
```json
// specflow.json
{
  "plugins": [
    { "name": "CrossBridge" }
  ]
}
```

**Environment Variables:**
```bash
$env:CROSSBRIDGE_ENABLED = "true"
$env:CROSSBRIDGE_DB_HOST = "10.55.12.99"
$env:CROSSBRIDGE_APPLICATION_VERSION = "v2.0.0"
```

**Database Events:**
- `test_start`: On `[BeforeScenario]`
- `test_end`: On `[AfterScenario]`
- Extracts: scenario title, feature name, tags, error details

---

#### Selenium Python pytest

**Location:** `adapters/pytest/pytest_plugin.py` (existing)

**Setup:**
```ini
# pytest.ini
[pytest]
plugins = crossbridge
```

**Or:**
```python
# conftest.py
pytest_plugins = ["crossbridge.pytest_plugin"]
```

**Database Events:**
- `test_start`: On `pytest_runtest_protocol`
- `test_end`: On test finish
- Extracts: test_id, duration, outcome, markers, fixtures

---

#### Python Robot Framework

**Location:** `adapters/robot/robot_listener.py` (existing)

**Setup:**
```robot
*** Settings ***
Library    SeleniumLibrary
Listener   crossbridge.RobotListener

*** Test Cases ***
My Test
    # Your existing test code
```

**Works For:**
- Selenium-based Robot tests
- Requests-based API Robot tests
- Any Robot Framework test

**Database Events:**
- `test_start`: On `start_test()`
- `test_end`: On `end_test()`
- Extracts: test_id, status, duration, message, tags

---

#### Cypress

**Location:** `core/observability/hooks/cypress_plugin.js`

**Setup:**
```javascript
// cypress.config.js
const crossbridge = require('crossbridge-cypress');

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      crossbridge.register(on, {
        enabled: true,
        dbHost: '10.55.12.99'
      });
    }
  }
});
```

**Optional Auto-Tracking:**
```javascript
// cypress/support/e2e.js
import 'crossbridge-cypress/support';
```

**Database Events:**
- `test_start`: Via `cy.task('crossbridge:testStart')`
- `test_end`: Via `cy.task('crossbridge:testEnd')`
- Extracts: test_id, suite, browser, error details

---

#### Playwright

**Location:** `adapters/playwright/playwright_reporter.py` (existing)

**Setup:**
```javascript
// playwright.config.js
export default {
  reporter: [
    ['crossbridge', { enabled: true }]
  ]
};
```

**Database Events:**
- `test_start`: On `onTestBegin()`
- `test_end`: On `onTestEnd()`
- Extracts: test_id, status, duration, browser, error

---

### Common Features (All Frameworks)

#### 1. Automatic NEW Test Detection

When a test with an unknown `test_id` runs:

```sql
-- CrossBridge automatically:
INSERT INTO test_execution_event (test_id, ..., event_type) 
VALUES ('NewTest.testLogin', ..., 'test_start');

-- Drift detector identifies it:
SELECT DISTINCT test_id 
FROM test_execution_event 
WHERE test_id NOT IN (SELECT test_id FROM previous_runs);

-- Lifecycle manager transitions:
UPDATE test_lifecycle 
SET state = 'NEW', first_seen = NOW();

-- Coverage intelligence creates nodes:
INSERT INTO coverage_graph_nodes (node_id, ...) 
VALUES ('API:/api/login', ...);
```

**No remigration. No manual registration. Fully automatic.**

---

#### 2. Database Schema

All frameworks emit events to the same table:

```sql
CREATE TABLE test_execution_event (
    id SERIAL PRIMARY KEY,
    test_id VARCHAR(500) NOT NULL,
    test_name VARCHAR(500),
    framework VARCHAR(100),  -- e.g., 'selenium-java', 'cypress', 'robot'
    file_path TEXT,
    status VARCHAR(50),      -- 'passed', 'failed', 'running', 'skipped'
    duration_seconds FLOAT,
    error_message TEXT,
    stack_trace TEXT,
    application_version VARCHAR(100),
    product_name VARCHAR(100),
    environment VARCHAR(100),
    event_type VARCHAR(50),  -- 'test_start', 'test_end'
    event_timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);
```

**Universal schema works for all frameworks.**

---

#### 3. AI Intelligence (Release Stage)

All frameworks benefit from AI analysis:

**Location:** `core/observability/ai_intelligence.py`

**Features:**
1. **Flaky Test Prediction**: Analyzes status oscillation across frameworks
2. **Coverage Gap Detection**: Finds uncovered APIs/pages
3. **Refactor Recommendations**: Identifies slow/complex tests
4. **Risk Scoring**: Calculates priority for all tests
5. **Test Generation**: Suggests new tests for gaps

**Usage (framework-agnostic):**
```python
from core.observability import AIIntelligence

ai = AIIntelligence(db_connection)

# Works with any framework's data
flaky_tests = ai.predict_flaky_tests(project_id="MyApp")
coverage_gaps = ai.find_coverage_gaps(project_id="MyApp")
refactors = ai.get_refactor_recommendations(project_id="MyApp")
risks = ai.calculate_risk_scores(project_id="MyApp")
suggestions = ai.suggest_test_generation(project_id="MyApp")
```

---

### Setup Time Comparison

| Framework | Setup Steps | Estimated Time | Complexity |
|-----------|-------------|----------------|------------|
| Selenium Java | Add listener to testng.xml | ⏱️ 5 min | 🟢 Easy |
| Java BDD | Same as Selenium Java | ⏱️ 5 min | 🟢 Easy |
| Java + RestAssured | Same as Selenium Java | ⏱️ 5 min | 🟢 Easy |
| .NET SpecFlow | Add plugin to specflow.json | ⏱️ 5 min | 🟢 Easy |
| Python pytest | Add plugin to pytest.ini | ⏱️ 3 min | 🟢 Easy |
| Python Robot | Add Listener to Settings | ⏱️ 3 min | 🟢 Easy |
| Cypress | Add plugin to config | ⏱️ 5 min | 🟢 Easy |
| Playwright | Add reporter to config | ⏱️ 3 min | 🟢 Easy |

**Average setup time: 4 minutes**

---

## 2️⃣ MIGRATION MODE (Full Transformation)

### Concept

CrossBridge **transforms** test code from legacy frameworks to modern frameworks, preserving intent while modernizing syntax, patterns, and best practices.

---

### Supported Transformations

| Source Framework | Target Framework | Status | Adapter Location |
|------------------|------------------|--------|------------------|
| Selenium Java + Cucumber | Robot Framework | ✅ Stable | `adapters/selenium_java/` |
| Selenium Java (no BDD) | Robot Framework | ✅ Stable | `adapters/selenium_java/` |
| Selenium Python pytest | Robot Framework | 🟡 Beta | `adapters/selenium_pytest/` |
| .NET SpecFlow | Robot Framework | 🟡 Beta | `adapters/selenium_specflow_dotnet/` |
| Robot Framework | Playwright | 🔵 Planned | - |
| Cypress | Playwright | 🔵 Planned | - |

**Primary use case: Selenium → Robot Framework**

---

### Migration Process

```bash
# Interactive CLI
python -m cli.app

# Wizard guides you through:
1. Select source framework (e.g., Selenium Java BDD)
2. Connect to repository (Bitbucket/GitHub/Azure DevOps)
3. Configure paths:
   - Feature files: src/test/resources/features/
   - Step definitions: src/test/java/stepdefs/
   - Page objects: src/test/java/pages/
4. Select transformation mode:
   - Pattern-based (fast, deterministic)
   - AI-enhanced (slower, higher quality)
   - Hybrid (recommended)
5. Review and run
```

**Output:**
- Transformed .robot files
- Resource files (keywords)
- Page object libraries
- Test data files
- Migration report
- New Git branch with changes

---

### Migration Adapters

#### Selenium Java → Robot Framework

**Adapter:** `adapters/selenium_java/`

**Transforms:**
- `.feature` files → `.robot` test cases
- Step definitions → Robot keywords
- Page objects → Resource files
- TestNG/JUnit → Robot test suites

**Example:**
```java
// Before (Java)
@When("I login with {string} and {string}")
public void login(String user, String pass) {
    loginPage.enterUsername(user);
    loginPage.enterPassword(pass);
    loginPage.clickLogin();
}
```

```robot
# After (Robot Framework)
*** Keywords ***
Login With Username And Password
    [Arguments]    ${user}    ${pass}
    Enter Username    ${user}
    Enter Password    ${pass}
    Click Login Button
```

---

## 🎯 Choosing the Right Mode

### Use NO MIGRATION MODE When:

- ✅ You want to understand your test suite first
- ✅ You need continuous intelligence without disruption
- ✅ Your framework is working fine, just needs monitoring
- ✅ You're not ready to commit to a full migration
- ✅ You want to identify which tests are worth migrating

**Time to Value: 5 minutes**

---

### Use MIGRATION MODE When:

- ✅ Your framework is outdated (e.g., Selenium 3.x)
- ✅ Tests are brittle and hard to maintain
- ✅ You're planning a framework modernization project
- ✅ You want to adopt Robot Framework or Playwright
- ✅ You have executive buy-in for transformation

**Time to Value: Hours to days (depending on test suite size)**

---

### Hybrid Approach (Recommended)

**Release Stage: Start with NO MIGRATION MODE**
- Monitor existing tests for 1-2 weeks
- Identify flaky tests, coverage gaps, slow tests
- Build historical data for AI analysis

**Release Stage: Analyze and Decide**
- Review AI recommendations
- Identify high-value tests for migration
- Keep stable tests in original framework

**Release Stage: Selective MIGRATION**
- Migrate high-priority tests first
- Use AI-enhanced transformation
- Run both old and new tests in parallel

**Release Stage: Gradual Retirement**
- Retire old tests as new tests prove stable
- Keep CrossBridge observer on both
- Achieve 100% modern framework coverage

---

## 📊 Feature Comparison Matrix

| Feature | NO MIGRATION MODE | MIGRATION MODE |
|---------|-------------------|----------------|
| **Setup Time** | ⏱️ 5 minutes | ⏱️ Hours |
| **Test Code Changes** | ❌ None | ✅ Complete transformation |
| **Framework Coverage** | ✅ 9 frameworks | 🟡 4 frameworks |
| **Coverage Tracking** | ✅ Automatic | ✅ Automatic |
| **Flaky Detection** | ✅ Yes | ✅ Yes |
| **AI Recommendations** | ✅ Yes | ✅ Yes |
| **Test Generation** | ✅ Suggestions | ✅ Suggestions |
| **Risk Scoring** | ✅ Yes | ✅ Yes |
| **NEW Test Auto-Detection** | ✅ Yes | ✅ Yes |
| **Impact on CI/CD** | ✅ None (observer) | 🟡 Requires test updates |
| **Rollback Risk** | ✅ None | 🟡 Medium (new code) |
| **Team Training** | ✅ Minimal | 🟡 Significant (new framework) |

---

## 🚀 Getting Started

### For NO MIGRATION MODE:

1. Read: [NO_MIGRATION_FRAMEWORK_SUPPORT.md](docs/NO_MIGRATION_FRAMEWORK_SUPPORT.md)
2. Choose your framework from the 9 supported
3. Add listener/plugin (5 minutes)
4. Run tests normally
5. View insights in Grafana dashboard

### For MIGRATION MODE:

1. Read: [AI_TRANSFORMATION_USAGE.md](docs/AI_TRANSFORMATION_USAGE.md)
2. Run: `python -m cli.app`
3. Follow interactive wizard
4. Review transformed tests
5. Test and validate

---

## 📁 File Locations

### NO MIGRATION MODE

```
core/observability/hooks/
├── java_listener.py          # Generates Java listeners
├── specflow_plugin.cs         # .NET SpecFlow plugin
├── cypress_plugin.js          # Cypress plugin
└── cypress_support_example.js # Cypress support file

adapters/
├── pytest/pytest_plugin.py    # pytest plugin
├── robot/robot_listener.py    # Robot listener
└── playwright/playwright_reporter.py  # Playwright reporter
```

### MIGRATION MODE

```
adapters/
├── selenium_java/             # Java → Robot
├── selenium_pytest/           # pytest → Robot
├── selenium_specflow_dotnet/  # SpecFlow → Robot
└── common/                    # Shared utilities
```

### AI Intelligence (Both Modes)

```
core/observability/
├── ai_intelligence.py         # Release Stage AI features
├── observer_service.py        # Event processing pipeline
├── lifecycle.py               # Test state management
├── drift_detector.py          # NEW test detection
└── coverage_intelligence.py   # Coverage tracking
```

---

## 🎯 Summary

**CrossBridge Now Offers:**

1. **NO MIGRATION MODE** (NEW!)
   - 9 frameworks supported
   - 5-minute setup
   - Zero test code changes
   - Full observability & AI
   - **Recommended starting point**

2. **MIGRATION MODE** (Existing)
   - 4 source frameworks
   - Full transformation
   - AI-enhanced quality
   - Comprehensive validation
   - For committed modernization

**Both modes share:**
- Same database schema
- Same AI intelligence features
- Same Grafana dashboards
- Same continuous intelligence

**The choice is yours: Observe first, migrate when ready!**

---

## 📞 Next Steps

- **Quick Start**: [NO_MIGRATION_FRAMEWORK_SUPPORT.md](docs/NO_MIGRATION_FRAMEWORK_SUPPORT.md)
- **AI Features**: [AI_TRANSFORMATION_USAGE.md](docs/AI_TRANSFORMATION_USAGE.md)
- **Architecture**: [docs/cli-architecture.md](docs/cli-architecture.md)

**Questions?** Contact vikas.sdet@gmail.com or open an issue on GitHub
