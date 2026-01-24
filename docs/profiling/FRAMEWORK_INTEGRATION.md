# Framework Integration Guide

Complete setup instructions for performance profiling with all 12 supported frameworks.

---

## Table of Contents

- [Python Frameworks](#python-frameworks)
  - [pytest](#pytest)
  - [Robot Framework](#robot-framework)
  - [Selenium Python](#selenium-python)
  - [HTTP Requests](#http-requests-python)
- [Java Frameworks](#java-frameworks)
  - [TestNG](#testng)
  - [JUnit](#junit)
  - [RestAssured](#restassured)
  - [Selenium Java](#selenium-java)
- [.NET Frameworks](#net-frameworks)
  - [NUnit](#nunit)
  - [SpecFlow](#specflow)
- [JavaScript Frameworks](#javascript-frameworks)
  - [Cypress](#cypress)
  - [Playwright](#playwright)
- [BDD Frameworks](#bdd-frameworks)
  - [Cucumber Java](#cucumber-java)
  - [Behave Python](#behave-python)

---

## Python Frameworks

### pytest

**Setup**: Automatic when profiling is enabled in `crossbridge.yml`

**File**: `conftest.py` (optional explicit registration)
```python
pytest_plugins = ["core.profiling.hooks.pytest_hook"]
```

**What's Tracked**:
- ✅ Test setup duration
- ✅ Test execution duration
- ✅ Test teardown duration
- ✅ Test outcome (passed/failed/skipped)
- ✅ Test node ID (full path)

**Run Tests**:
```bash
# Standard pytest execution
pytest tests/ -v

# With specific markers
pytest tests/ -m slow -v

# With coverage
pytest tests/ --cov=myapp -v
```

**Example Data Captured**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "test_id": "tests/test_login.py::TestAuth::test_login_success",
  "event_type": "TEST_END",
  "framework": "pytest",
  "duration_ms": 1523.4,
  "status": "passed",
  "metadata": {
    "setup_ms": 245.1,
    "teardown_ms": 89.3
  }
}
```

---

### Robot Framework

**Setup**: Add listener to robot command

**Command**:
```bash
robot --listener core.profiling.hooks.robot_hook.CrossBridgeProfilingListener tests/
```

**Integration in CI/CD**:
```yaml
# .gitlab-ci.yml
test:
  script:
    - export CROSSBRIDGE_PROFILING=true
    - robot --listener core.profiling.hooks.robot_hook.CrossBridgeProfilingListener --outputdir results tests/
```

**What's Tracked**:
- ✅ Suite start/end
- ✅ Test start/end
- ✅ Test duration
- ✅ Test status (PASS/FAIL)
- ✅ Suite hierarchy

**Example Test**:
```robot
*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Login Test
    [Documentation]    Test user login flow
    Open Browser    https://example.com    chrome
    Input Text    id=username    testuser
    Input Text    id=password    testpass
    Click Button    id=login
    Page Should Contain    Welcome
    Close Browser
```

**Data Captured**:
```json
{
  "test_id": "LoginSuite::Login Test",
  "event_type": "TEST_END",
  "framework": "robot",
  "duration_ms": 3456.7,
  "status": "PASS"
}
```

---

### Selenium Python

**Setup**: Wrap WebDriver with profiling

**File**: `tests/conftest.py`
```python
import pytest
from selenium import webdriver
from core.profiling.hooks.selenium_hook import ProfilingWebDriver

@pytest.fixture
def driver(request):
    base_driver = webdriver.Chrome()
    test_id = request.node.nodeid
    profiled_driver = ProfilingWebDriver(base_driver, test_id=test_id)
    
    yield profiled_driver
    
    profiled_driver.quit()
```

**Test File**: `tests/test_example.py`
```python
def test_search(driver):
    # ProfilingWebDriver tracks all commands automatically
    driver.get("https://example.com")
    
    search_box = driver.find_element("name", "q")
    search_box.send_keys("CrossBridge AI")
    search_box.submit()
    
    assert "CrossBridge AI" in driver.title
```

**What's Tracked**:
- ✅ `get()` - page navigation
- ✅ `find_element()` / `find_elements()` - locator performance
- ✅ `click()` - interaction timing
- ✅ `send_keys()` - input speed
- ✅ `execute_script()` - JavaScript execution
- ✅ All other WebDriver commands

**Data Captured**:
```json
{
  "test_id": "tests/test_example.py::test_search",
  "event_type": "DRIVER_COMMAND",
  "command": "get",
  "duration_ms": 1234.5,
  "metadata": {
    "url": "https://example.com"
  }
}
```

---

### HTTP Requests (Python)

**Setup**: Use `ProfilingSession` instead of `requests.Session`

**File**: `tests/test_api.py`
```python
from core.profiling.hooks.http_hook import ProfilingSession

def test_api_users():
    test_id = "test_api_users"
    session = ProfilingSession(test_id=test_id)
    
    # All requests are automatically profiled
    response = session.get("https://api.example.com/users")
    assert response.status_code == 200
    
    user_data = {"name": "Test User", "email": "test@example.com"}
    response = session.post("https://api.example.com/users", json=user_data)
    assert response.status_code == 201
```

**What's Tracked**:
- ✅ HTTP method (GET, POST, PUT, DELETE, etc.)
- ✅ Endpoint URL
- ✅ Status code
- ✅ Duration (DNS + connect + TLS + transfer)
- ✅ Request/response sizes

**Data Captured**:
```json
{
  "test_id": "test_api_users",
  "event_type": "HTTP_REQUEST",
  "endpoint": "https://api.example.com/users",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 234.5
}
```

---

## Java Frameworks

### TestNG

**Setup**: Generate listener code and add to project

**Step 1**: Generate Java code
```bash
python -c "
from core.profiling.hooks.java_hook import TESTNG_LISTENER_JAVA
with open('src/test/java/com/crossbridge/profiling/CrossBridgeProfilingListener.java', 'w') as f:
    f.write(TESTNG_LISTENER_JAVA)
"
```

**Step 2**: Add to `testng.xml`
```xml
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="CrossBridge Profiled Suite" parallel="methods" thread-count="4">
  <listeners>
    <listener class-name="com.crossbridge.profiling.CrossBridgeProfilingListener"/>
  </listeners>
  
  <test name="API Tests">
    <classes>
      <class name="com.example.tests.UserApiTest"/>
      <class name="com.example.tests.ProductApiTest"/>
    </classes>
  </test>
</suite>
```

**Step 3**: Add PostgreSQL dependency to `pom.xml`
```xml
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <version>42.6.0</version>
</dependency>
```

**Step 4**: Set environment variables
```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
export CROSSBRIDGE_RUN_ID=$(uuidgen)
export CROSSBRIDGE_DB_HOST=10.60.67.247
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=cbridge-unit-test-db
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin

mvn test
```

**What's Tracked**:
- ✅ Test start/end timing
- ✅ Configuration methods (@BeforeMethod, @AfterMethod)
- ✅ Test success/failure/skip
- ✅ Parallel execution (thread-safe)

**Example Test**:
```java
import org.testng.annotations.Test;

public class UserApiTest {
    @Test
    public void testGetUser() {
        // Listener tracks this automatically
        RestAssured.get("/api/users/1")
            .then()
            .statusCode(200);
    }
}
```

---

### JUnit

**Setup**: Generate listener code and configure Maven Surefire

**Step 1**: Generate Java code
```bash
python -c "
from core.profiling.hooks.java_hook import JUNIT_LISTENER_JAVA
with open('src/test/java/com/crossbridge/profiling/CrossBridgeJUnitListener.java', 'w') as f:
    f.write(JUNIT_LISTENER_JAVA)
"
```

**Step 2**: Configure Maven Surefire in `pom.xml`
```xml
<build>
  <plugins>
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-surefire-plugin</artifactId>
      <version>3.0.0-M7</version>
      <configuration>
        <properties>
          <property>
            <name>listener</name>
            <value>com.crossbridge.profiling.CrossBridgeJUnitListener</value>
          </property>
        </properties>
      </configuration>
    </plugin>
  </plugins>
</build>
```

**Step 3**: Run tests with environment variables
```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
export CROSSBRIDGE_RUN_ID=$(uuidgen)
export CROSSBRIDGE_DB_HOST=10.60.67.247
# ... (same as TestNG)

mvn test
```

**Example Test**:
```java
import org.junit.Test;
import static org.junit.Assert.*;

public class CalculatorTest {
    @Test
    public void testAddition() {
        assertEquals(4, 2 + 2);
    }
}
```

---

### RestAssured

**Setup**: RestAssured tests work with TestNG/JUnit listeners

**File**: `src/test/java/com/example/ApiTest.java`
```java
import io.restassured.RestAssured;
import io.restassured.response.Response;
import org.testng.annotations.Test;
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;

public class ApiTest {
    
    @Test
    public void testGetUsers() {
        given()
            .baseUri("https://api.example.com")
        .when()
            .get("/users")
        .then()
            .statusCode(200)
            .body("size()", greaterThan(0));
    }
    
    @Test
    public void testCreateUser() {
        given()
            .baseUri("https://api.example.com")
            .contentType("application/json")
            .body("{ \"name\": \"Test User\" }")
        .when()
            .post("/users")
        .then()
            .statusCode(201)
            .body("name", equalTo("Test User"));
    }
}
```

**What's Tracked**:
- ✅ Test-level timing (via TestNG/JUnit listener)
- ✅ HTTP request performance (future: RestAssured interceptor)
- ✅ API endpoint patterns

---

### Selenium Java

**Setup**: Selenium Java tests work with TestNG/JUnit listeners

**File**: `src/test/java/com/example/SeleniumTest.java`
```java
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.By;
import org.testng.annotations.*;

public class SeleniumTest {
    private WebDriver driver;
    
    @BeforeMethod
    public void setup() {
        driver = new ChromeDriver();
    }
    
    @Test
    public void testLogin() {
        driver.get("https://example.com/login");
        driver.findElement(By.id("username")).sendKeys("testuser");
        driver.findElement(By.id("password")).sendKeys("testpass");
        driver.findElement(By.id("login-button")).click();
        
        assert driver.getTitle().contains("Dashboard");
    }
    
    @AfterMethod
    public void teardown() {
        driver.quit();
    }
}
```

**What's Tracked**:
- ✅ Test-level timing (via listener)
- ✅ Setup/teardown timing
- ✅ Test outcomes

---

## .NET Frameworks

### NUnit

**Setup**: Generate C# hook code and add to project

**Step 1**: Generate C# code
```bash
python -c "
from core.profiling.hooks.dotnet_hook import NUNIT_HOOK_CSHARP
with open('CrossBridge.Profiling/CrossBridgeProfilingHook.cs', 'w') as f:
    f.write(NUNIT_HOOK_CSHARP)
"
```

**Step 2**: Add Npgsql package
```bash
dotnet add package Npgsql --version 7.0.0
```

**Step 3**: Add assembly attribute to `AssemblyInfo.cs`
```csharp
using CrossBridge.Profiling;

[assembly: CrossBridgeProfilingHook]
```

**Step 4**: Set environment variables
```powershell
$env:CROSSBRIDGE_PROFILING_ENABLED="true"
$env:CROSSBRIDGE_RUN_ID=[guid]::NewGuid().ToString()
$env:CROSSBRIDGE_DB_HOST="10.60.67.247"
$env:CROSSBRIDGE_DB_PORT="5432"
$env:CROSSBRIDGE_DB_NAME="cbridge-unit-test-db"
$env:CROSSBRIDGE_DB_USER="postgres"
$env:CROSSBRIDGE_DB_PASSWORD="admin"

dotnet test
```

**Example Test**:
```csharp
using NUnit.Framework;

namespace MyTests
{
    [TestFixture]
    public class CalculatorTests
    {
        [Test]
        public void TestAddition()
        {
            Assert.AreEqual(4, 2 + 2);
        }
        
        [Test]
        public void TestSubtraction()
        {
            Assert.AreEqual(0, 2 - 2);
        }
    }
}
```

**What's Tracked**:
- ✅ Test start/end timing
- ✅ Test outcome (Passed/Failed/Skipped)
- ✅ Fixture setup/teardown

---

### SpecFlow

**Setup**: Generate SpecFlow binding code

**Step 1**: Generate C# code
```bash
python -c "
from core.profiling.hooks.dotnet_hook import SPECFLOW_HOOK_CSHARP
with open('CrossBridge.Profiling/CrossBridgeSpecFlowHook.cs', 'w') as f:
    f.write(SPECFLOW_HOOK_CSHARP)
"
```

**Step 2**: SpecFlow automatically discovers the hook

**Example Feature**:
```gherkin
Feature: User Login
  As a user
  I want to log in
  So that I can access my account

  Scenario: Successful login
    Given I am on the login page
    When I enter username "testuser"
    And I enter password "testpass"
    And I click the login button
    Then I should see the dashboard
```

**Step Definitions**:
```csharp
using TechTalk.SpecFlow;

[Binding]
public class LoginSteps
{
    [Given(@"I am on the login page")]
    public void GivenIAmOnTheLoginPage()
    {
        // Navigation code
    }
    
    [When(@"I enter username ""(.*)""")]
    public void WhenIEnterUsername(string username)
    {
        // Input code
    }
    
    [Then(@"I should see the dashboard")]
    public void ThenIShouldSeeTheDashboard()
    {
        // Assertion code
    }
}
```

**What's Tracked**:
- ✅ Scenario start/end timing
- ✅ Scenario outcome
- ✅ Feature context

---

## JavaScript Frameworks

### Cypress

**Setup**: Install plugin and support files

**Step 1**: Generate JavaScript plugin
```bash
python -c "
from core.profiling.hooks.cypress_hook import CYPRESS_PLUGIN_JS, CYPRESS_SUPPORT_JS
import os
os.makedirs('cypress/plugins', exist_ok=True)
os.makedirs('cypress/support', exist_ok=True)
with open('cypress/plugins/crossbridge-profiling.js', 'w') as f:
    f.write(CYPRESS_PLUGIN_JS)
with open('cypress/support/crossbridge-profiling.js', 'w') as f:
    f.write(CYPRESS_SUPPORT_JS)
"
```

**Step 2**: Register plugin in `cypress.config.js`
```javascript
const { defineConfig } = require('cypress');
const crossbridge = require('./cypress/plugins/crossbridge-profiling');

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      crossbridge(on, config);
      return config;
    },
  },
});
```

**Step 3**: Import support file in `cypress/support/e2e.js`
```javascript
import './crossbridge-profiling';
```

**Step 4**: Set environment variables
```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
export CROSSBRIDGE_DB_HOST=10.60.67.247
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=cbridge-unit-test-db
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin

npx cypress run
```

**Example Test**:
```javascript
describe('Login Tests', () => {
  it('should login successfully', () => {
    cy.visit('https://example.com/login');
    cy.get('#username').type('testuser');
    cy.get('#password').type('testpass');
    cy.get('#login-button').click();
    cy.url().should('include', '/dashboard');
  });
});
```

**What's Tracked**:
- ✅ Run start/end
- ✅ Spec file execution
- ✅ Test start/end timing
- ✅ HTTP requests (automatic interception)
- ✅ Test outcomes

**Manual HTTP Tracking**:
```javascript
it('should track custom HTTP call', () => {
  cy.task('crossbridge:httpCall', {
    endpoint: '/api/users',
    method: 'GET',
    status_code: 200,
    duration_ms: 123.4
  });
});
```

---

### Playwright

**Setup**: Add Playwright reporter

**Step 1**: For Python Playwright
```python
from core.profiling.hooks.playwright_hook import CrossBridgePlaywrightReporter

# In your test configuration
reporter = CrossBridgePlaywrightReporter()
```

**Step 2**: For JavaScript/TypeScript Playwright

Generate reporter:
```bash
python -c "
from core.profiling.hooks.playwright_hook import PLAYWRIGHT_REPORTER_JS
with open('playwright-crossbridge-reporter.js', 'w') as f:
    f.write(PLAYWRIGHT_REPORTER_JS)
"
```

Add to `playwright.config.ts`:
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  reporter: [
    ['list'],
    ['./playwright-crossbridge-reporter.js']
  ],
  use: {
    baseURL: 'https://example.com',
  },
});
```

**Step 3**: Set environment variables
```bash
export CROSSBRIDGE_PROFILING_ENABLED=true
export CROSSBRIDGE_DB_HOST=10.60.67.247
# ... (same as Cypress)

npx playwright test
```

**Example Test**:
```typescript
import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example/);
});

test('login flow', async ({ page }) => {
  await page.goto('https://example.com/login');
  await page.fill('#username', 'testuser');
  await page.fill('#password', 'testpass');
  await page.click('#login-button');
  await expect(page).toHaveURL(/.*dashboard/);
});
```

**What's Tracked**:
- ✅ Test suite start/end
- ✅ Test start/end timing
- ✅ Step-level timing
- ✅ Browser context
- ✅ Retry count
- ✅ Error messages

---

## BDD Frameworks

### Cucumber Java

**Setup**: Use TestNG/JUnit listener (Cucumber runs on top of these)

**File**: `src/test/java/com/example/RunCucumberTest.java`
```java
import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "src/test/resources/features",
    glue = "com.example.steps",
    plugin = {"pretty", "html:target/cucumber-reports"}
)
public class RunCucumberTest {
    // Profiling via JUnit listener
}
```

**Feature File**: `src/test/resources/features/login.feature`
```gherkin
Feature: User Login
  
  Scenario: Successful login
    Given I am on the login page
    When I enter valid credentials
    Then I should be logged in
```

**What's Tracked**:
- ✅ Scenario-level timing (via JUnit/TestNG)
- ✅ Feature execution

---

### Behave Python

**Setup**: Use pytest integration or custom profiling

**File**: `features/environment.py`
```python
from core.profiling import MetricsCollector, PerformanceEvent, EventType
import time

collector = MetricsCollector.instance()

def before_scenario(context, scenario):
    context.scenario_start = time.perf_counter()
    collector.collect(PerformanceEvent.create(
        test_id=f"{scenario.feature.name}::{scenario.name}",
        event_type=EventType.TEST_START,
        framework="behave"
    ))

def after_scenario(context, scenario):
    duration = (time.perf_counter() - context.scenario_start) * 1000
    status = "passed" if scenario.status == "passed" else "failed"
    
    collector.collect(PerformanceEvent.create(
        test_id=f"{scenario.feature.name}::{scenario.name}",
        event_type=EventType.TEST_END,
        framework="behave",
        duration_ms=duration,
        status=status
    ))
```

---

## Troubleshooting

### Python: Import Errors

```bash
# Ensure CrossBridge is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Java: ClassNotFoundException

```bash
# Verify listener class is compiled
mvn clean compile test-compile
```

### .NET: Assembly Not Found

```bash
# Rebuild solution
dotnet clean
dotnet build
```

### JavaScript: Module Not Found

```bash
# Install node dependencies
npm install pg  # For PostgreSQL
```

### Database Connection Issues

```bash
# Test connection
psql -h 10.60.67.247 -p 5432 -U postgres -d cbridge-unit-test-db -c "SELECT 1;"
```

---

## Next Steps

1. ✅ Enable profiling in `crossbridge.yml`
2. ✅ Integrate framework hook for your stack
3. ✅ Run tests to generate data
4. ✅ Set up [Grafana dashboards](../observability/GRAFANA_PERFORMANCE_PROFILING.md)
5. ✅ Configure alerts for regressions

---

## See Also

- [Architecture](ARCHITECTURE.md)
- [Configuration Reference](CONFIGURATION.md)
- [Grafana Integration](../observability/GRAFANA_PERFORMANCE_PROFILING.md)
- [API Reference](API.md)
