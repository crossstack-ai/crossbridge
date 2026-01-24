# CrossBridge Framework Support - Quick Reference

**Last Updated:** January 18, 2026

## 🎯 At a Glance

CrossBridge supports **TWO MODES**:
- **NO MIGRATION** (Sidecar): 9 frameworks, 5-min setup, zero code changes
- **MIGRATION** (Transform): 4 frameworks, full conversion

---

## ✅ NO MIGRATION MODE (Sidecar Observer)

**Your tests run unchanged. CrossBridge watches and provides intelligence.**

| # | Framework | Type | Setup | Hook File | Works With |
|---|-----------|------|-------|-----------|------------|
| 1 | **Selenium Java (TestNG)** | UI | 5min | `java_listener.py` | TestNG 6.x/7.x ✅ |
| 2 | **Selenium Java (JUnit 4)** | UI | 5min | `java_listener.py` | JUnit 4.x ✅ |
| 3 | **Selenium Java (JUnit 5)** | UI | 5min | `java_listener.py` | JUnit Jupiter 5.x ✅ |
| 4 | **Java BDD (Cucumber)** | UI+BDD | 5min | `java_listener.py` | Cucumber + TestNG/JUnit ✅ |
| 5 | **Java + RestAssured** | UI+API | 5min | `java_listener.py` | TestNG/JUnit ✅ |
| 6 | **.NET NUnit** | UI | 5min | `nunit_listener.cs` | NUnit 3.x ✅ |
| 7 | **.NET SpecFlow** | UI+BDD | 5min | `specflow_plugin.cs` | SpecFlow 3.x+ ✅ |
| 8 | **Python pytest** | UI | 3min | `pytest_plugin.py` | pytest 6.x+ |
| 9 | **Python Robot (UI)** | UI | 3min | `robot_listener.py` | Robot 4.x+ |
| 10 | **Python Robot (API)** | API | 3min | `robot_listener.py` | Requests, Robot |
| 11 | **Cypress** | UI | 5min | `cypress_plugin.js` | Cypress 10.x+ |
| 12 | **Playwright** | UI | 3min | `playwright_reporter.py` | Playwright 1.x+ |

### What You Get (All Frameworks)

- ✅ **Automatic test tracking** (status, duration, errors)
- ✅ **Coverage graphs** (APIs, pages, components)
- ✅ **NEW test auto-detection** (no remigration needed)
- ✅ **Flaky test prediction** (AI-powered)
- ✅ **Coverage gap analysis** (uncovered endpoints/pages)
- ✅ **Risk scoring** (prioritize critical tests)
- ✅ **Refactor recommendations** (slow/complex tests)
- ✅ **Test generation suggestions** (AI templates)

### Setup Examples

<details>
<summary><b>Selenium Java (TestNG 6.x/7.x)</b></summary>

```bash
# Generate Java listeners
python core/observability/hooks/java_listener.py
# Creates: CrossBridgeListener.java (TestNG), CrossBridgeJUnitListener.java (JUnit 4), CrossBridgeExtension.java (JUnit 5)
```

```xml
<!-- testng.xml -->
<suite name="MyTests" parallel="methods" thread-count="4">
  <listeners>
    <listener class-name="com.crossbridge.CrossBridgeListener"/>
  </listeners>
  <test name="Test1">
    <classes><class name="com.example.MyTest"/></classes>
  </test>
</suite>
```

```bash
mvn test -Dcrossbridge.enabled=true \
         -Dcrossbridge.db.host=10.55.12.99 \
         -Dcrossbridge.application.version=v2.0.0
```

**✅ Thread-safe for parallel execution**
</details>

<details>
<summary><b>Selenium Java (JUnit 4)</b></summary>

```xml
<!-- pom.xml - maven-surefire-plugin -->
<plugin>
  <artifactId>maven-surefire-plugin</artifactId>
  <configuration>
    <properties>
      <property>
        <name>listener</name>
        <value>com.crossbridge.CrossBridgeJUnitListener</value>
      </property>
    </properties>
    <systemPropertyVariables>
      <crossbridge.enabled>true</crossbridge.enabled>
      <crossbridge.db.host>10.55.12.99</crossbridge.db.host>
    </systemPropertyVariables>
  </configuration>
</plugin>
```

```bash
mvn test
```

**✅ Thread-safe for parallel execution**
</details>

<details>
<summary><b>Selenium Java (JUnit 5 / Jupiter)</b></summary>

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import com.crossbridge.CrossBridgeExtension;

@ExtendWith(CrossBridgeExtension.class)
public class MyTest {
    @Test
    public void testLogin() {
        // Your test code
    }
}
```

```bash
mvn test -Dcrossbridge.enabled=true \
         -Dcrossbridge.db.host=10.55.12.99
```

**✅ Thread-safe for parallel execution**
</details>

<details>
<summary><b>.NET NUnit</b></summary>

```csharp
using NUnit.Framework;
using CrossBridge.NUnit;

[TestFixture]
[CrossBridgeListener]
public class LoginTests
{
    [Test]
    [Category("Smoke")]
    public void TestLogin()
    {
        // Your test code
    }
}
```

```bash
$env:CROSSBRIDGE_ENABLED = "true"
$env:CROSSBRIDGE_DB_HOST = "10.55.12.99"
dotnet test
```

**✅ Thread-safe for parallel execution**
</details>

<details>
<summary><b>.NET SpecFlow</b></summary>

```json
// specflow.json
{
  "plugins": [
    { "name": "CrossBridge" }
  ]
}
```

```powershell
$env:CROSSBRIDGE_ENABLED = "true"
$env:CROSSBRIDGE_DB_HOST = "10.55.12.99"
dotnet test
```
</details>

<details>
<summary><b>Python pytest</b></summary>

```ini
# pytest.ini
[pytest]
plugins = crossbridge
```

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_DB_HOST=10.55.12.99
pytest
```
</details>

<details>
<summary><b>Python Robot</b></summary>

```robot
*** Settings ***
Library    SeleniumLibrary
Listener   crossbridge.RobotListener

*** Test Cases ***
My Test
    # Your existing test code
```

```bash
export CROSSBRIDGE_ENABLED=true
robot tests/
```
</details>

<details>
<summary><b>Cypress</b></summary>

```javascript
// cypress.config.js
const crossbridge = require('crossbridge-cypress');

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      crossbridge.register(on, { enabled: true });
    }
  }
});
```

```bash
npx cypress run
```
</details>

---

## 🔄 MIGRATION MODE (Full Transformation)

**Convert legacy tests to modern frameworks.**

| Source | Target | Status | Quality | Adapter |
|--------|--------|--------|---------|---------|
| **Selenium Java + Cucumber** | Robot Framework | ✅ Stable | High | `selenium_java/` |
| **Selenium Java (no BDD)** | Robot Framework | ✅ Stable | High | `selenium_java/` |
| **Selenium Python pytest** | Robot Framework | 🟡 Beta | Medium | `selenium_pytest/` |
| **.NET SpecFlow** | Robot Framework | 🟡 Beta | Medium | `selenium_specflow_dotnet/` |

### Transformation Features

- ✅ Feature files → Robot test cases
- ✅ Step definitions → Robot keywords
- ✅ Page objects → Resource files
- ✅ AI-enhanced locators (optional)
- ✅ Pattern-based transformation (fast)
- ✅ Validation & quality checks
- ✅ Git branch integration

### Quick Start

```bash
python -m cli.app
# Select: Migration + Transformation
# Follow interactive wizard
```

---

## 🎯 Which Mode Should I Use?

### Start with NO MIGRATION MODE if:
- ✅ You want to **try CrossBridge quickly** (5 min setup)
- ✅ You need **intelligence about existing tests** first
- ✅ Your framework is **working fine**, just needs monitoring
- ✅ You want **zero disruption** to current workflow
- ✅ You're **not sure** if migration is worth it

### Use MIGRATION MODE if:
- ✅ Your framework is **outdated** (e.g., Selenium 3.x)
- ✅ Tests are **brittle** and hard to maintain
- ✅ You have **executive buy-in** for modernization
- ✅ You want to adopt **Robot Framework** or **Playwright**
- ✅ You're ready to **commit to transformation**

### Recommended Hybrid Approach:
1. **Week 1**: NO MIGRATION MODE - Monitor all tests
2. **Week 2**: Analyze AI insights - Find flaky/slow tests
3. **Week 3**: MIGRATION MODE - Migrate high-value tests
4. **Week 4+**: Run both old & new in parallel, gradual retirement

---

## 📊 Feature Comparison

| Feature | NO MIGRATION | MIGRATION |
|---------|--------------|-----------|
| **Setup Time** | ⏱️ 5 min | ⏱️ Hours |
| **Code Changes** | ❌ None | ✅ Full transform |
| **Framework Support** | ✅ 9 | 🟡 4 |
| **Risk** | ✅ None | 🟡 Medium |
| **Team Training** | ✅ None | 🟡 Required |
| **CI/CD Impact** | ✅ None | 🟡 Updates needed |
| **Rollback** | ✅ Instant | 🟡 Complex |
| **Coverage Tracking** | ✅ Yes | ✅ Yes |
| **Flaky Detection** | ✅ Yes | ✅ Yes |
| **AI Intelligence** | ✅ Yes | ✅ Yes |
| **NEW Test Handling** | ✅ Automatic | ✅ Automatic |

---

## 🚀 Getting Started (30 seconds)

### For NO MIGRATION MODE:

1. Choose your framework from table above
2. Add listener/plugin (see examples)
3. Set `CROSSBRIDGE_ENABLED=true`
4. Run tests normally
5. View insights in Grafana

**Total Time: 5 minutes**

### For MIGRATION MODE:

1. Run `python -m cli.app`
2. Select "Migration + Transformation"
3. Follow wizard
4. Review transformed tests
5. Validate and deploy

**Total Time: 1-4 hours (depending on suite size)**

---

## 📚 Documentation

- **[NO_MIGRATION_FRAMEWORK_SUPPORT.md](docs/NO_MIGRATION_FRAMEWORK_SUPPORT.md)** - Complete NO MIGRATION guide
- **[FRAMEWORK_SUPPORT_COMPLETE.md](FRAMEWORK_SUPPORT_COMPLETE.md)** - Full framework comparison
- **[AI_TRANSFORMATION_USAGE.md](docs/AI_TRANSFORMATION_USAGE.md)** - MIGRATION mode guide
- **[CRITICAL_FEATURES_CONFIRMED.md](CRITICAL_FEATURES_CONFIRMED.md)** - Phase 3 AI features
- **[README.md](README.md)** - Main project overview

---

## 🎯 Quick Decision Tree

```
Do you want to change your test code?
│
├─ NO → Use NO MIGRATION MODE
│       ├─ Selenium Java? → java_listener.py
│       ├─ .NET SpecFlow? → specflow_plugin.cs
│       ├─ Python pytest? → pytest_plugin.py
│       ├─ Python Robot? → robot_listener.py
│       └─ Cypress? → cypress_plugin.js
│
└─ YES → Use MIGRATION MODE
        ├─ Selenium Java + Cucumber → Robot Framework
        ├─ Selenium Java → Robot Framework
        ├─ Selenium Python pytest → Robot Framework
        └─ .NET SpecFlow → Robot Framework
```

---

## 💡 Pro Tips

1. **Always start with NO MIGRATION MODE** - Get insights first!
2. **Run for 1-2 weeks** before deciding on migration
3. **Use AI recommendations** to identify high-value tests
4. **Migrate incrementally** - Not all tests need migration
5. **Keep CrossBridge on both old and new tests** for continuity

---

## 📁 Key Files

### NO MIGRATION MODE
- `core/observability/hooks/java_listener.py`
- `core/observability/hooks/specflow_plugin.cs`
- `core/observability/hooks/cypress_plugin.js`
- `adapters/pytest/pytest_plugin.py`
- `adapters/robot/robot_listener.py`
- `adapters/playwright/playwright_reporter.py`

### MIGRATION MODE
- `adapters/selenium_java/`
- `adapters/selenium_pytest/`
- `adapters/selenium_specflow_dotnet/`
- `cli/app.py` (interactive CLI)

### AI Intelligence (Both)
- `core/observability/ai_intelligence.py`
- `core/observability/observer_service.py`
- `core/observability/drift_detector.py`
- `core/observability/coverage_intelligence.py`

---

## ✨ Summary

**CrossBridge gives you TWO paths to continuous intelligence:**

### Path 1: NO MIGRATION (Recommended Start)
- 9 frameworks supported
- 5-minute setup
- Zero risk
- Immediate insights

### Path 2: MIGRATION (When Ready)
- 4 frameworks supported
- Full transformation
- AI-enhanced quality
- Modern frameworks

**Both paths lead to the same destination: Intelligent, optimized test automation.**

**Start with Path 1. Upgrade to Path 2 when ready. Or stay on Path 1 forever. Your choice!**

---

**Questions?** See [NO_MIGRATION_FRAMEWORK_SUPPORT.md](docs/NO_MIGRATION_FRAMEWORK_SUPPORT.md) for detailed setup guides.
