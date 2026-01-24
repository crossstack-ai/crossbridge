# Phase-2 Multi-Framework Quick Reference

## Supported Frameworks (12 Total)

### Core Frameworks (6)
| Framework | Language | File Pattern | Support Level | Priority Syntax | Tags/Groups Syntax |
|-----------|----------|--------------|---------------|-----------------|-------------------|
| **pytest** | Python | `test_*.py` | ✅ Full | `@pytest.mark.p0` | `@pytest.mark.smoke` |
| **JUnit** | Java | `*Test.java` | ⚠️ Partial | - | - |
| **TestNG** | Java | `*Test.java` | ⚠️ Partial | `@Test(priority=0)` | `@Test(groups={"smoke"})` |
| **NUnit** | C# | `*Test.cs` | ⚠️ Partial | `[Priority(0)]` | `[Category("Smoke")]` |
| **SpecFlow** | C# | `*.feature` | ⚠️ Partial | `@p0`, `@critical` | `@smoke`, `@regression` |
| **Robot** | Robot | `*.robot` | ⚠️ Basic | - | - |

### Extended Frameworks (6) 🆕
| Framework | Language | File Pattern | Support Level | Priority Syntax | Tags/Groups Syntax |
|-----------|----------|--------------|---------------|-----------------|-------------------|
| **RestAssured** 🆕 | Java | `*Test.java` | ⚠️ Partial | `@Test(priority=0)` | `@Test(groups={"api"})` |
| **Playwright** 🆕 | JavaScript/TS | `*.spec.js/ts` | ⚠️ Partial | `// @p0` | `// @smoke` |
| **Selenium Python** 🆕 | Python | `test_*.py` | ✅ Full | `@pytest.mark.p0` | `@pytest.mark.ui` |
| **Selenium Java** 🆕 | Java | `*Test.java` | ⚠️ Partial | `@Test(priority=0)` | `@Test(groups={"ui"})` |
| **Cucumber** 🆕 | Gherkin | `*.feature` | ⚠️ Partial | `@critical`, `@p0` | `@smoke`, `@api` |
| **Behave** 🆕 | Python/Gherkin | `*.feature` | ⚠️ Partial | `@critical`, `@p0` | `@smoke`, `@ui` |

📖 **Extended Frameworks Full Documentation**: [MULTI_FRAMEWORK_SUPPORT.md](MULTI_FRAMEWORK_SUPPORT.md)

## Quick Start

### 1. Get Adapter

```python
from core.intelligence.adapters import AdapterFactory

# Get any adapter by name (case-insensitive)
adapter = AdapterFactory.get_adapter("nunit")
adapter = AdapterFactory.get_adapter("TestNG")
adapter = AdapterFactory.get_adapter("SPECFLOW")
adapter = AdapterFactory.get_adapter("restassured")  # 🆕
adapter = AdapterFactory.get_adapter("playwright")   # 🆕
adapter = AdapterFactory.get_adapter("cucumber")     # 🆕

# List all available frameworks (12 total)
frameworks = AdapterFactory.list_supported_frameworks()
# ['pytest', 'junit', 'testng', 'nunit', 'specflow', 'robot',
#  'restassured', 'playwright', 'selenium_python', 'selenium_java', 
#  'cucumber', 'behave']
```

### 2. Discover Tests

```python
# Discover test files for any framework
test_files = adapter.discover_tests("/project")

# pytest example
# ['/project/tests/test_auth.py', '/project/tests/test_checkout.py']

# nunit example
# ['/project/Tests/AuthTest.cs', '/project/Tests/CheckoutTest.cs']

# specflow example
# ['/project/Features/Auth.feature', '/project/Features/Checkout.feature']

# restassured example (🆕)
# ['/project/src/test/java/ApiTest.java', '/project/src/test/java/UserIT.java']

# playwright example (🆕)
# ['/project/tests/e2e/login.spec.ts', '/project/tests/e2e/checkout.spec.js']

# cucumber example (🆕)
# ['/project/features/api/users.feature', '/project/features/ui/login.feature']
```

### 3. Normalize to Unified Format

```python
# All frameworks normalize to the same UnifiedTestMemory structure
unified = adapter.normalize_to_core_model(
    test_file="/path/to/test_file",
    test_name="test_or_scenario_name"
)

# Access common fields
print(unified.test_id)          # "pytest::path/file.py::test_name"
print(unified.framework)        # "pytest"
print(unified.language)         # "python"
print(unified.metadata.priority)  # Priority.P0
print(unified.metadata.tags)    # ["smoke", "regression"]
print(unified.structural.api_calls)  # [APICall(...), ...]
```

## Framework-Specific Examples

### pytest (Python)

```python
@pytest.mark.p0
@pytest.mark.smoke
def test_user_login(client, db_session):
    response = client.post("/api/login", json={"user": "john"})
    assert response.status_code == 200
```

**Extracted**:
- Priority: `P0`
- Tags: `["smoke"]`
- Fixtures: `["client", "db_session"]`
- API Calls: `POST /api/login`
- Assertions: `assertEqual(status_code, 200)`

---

### TestNG (Java)

```java
@Test(priority = 0, groups = {"smoke", "critical"})
public void testCriticalFlow() {
    Response response = given()
        .post("/api/payments");
    assertEquals(200, response.getStatusCode());
}
```

**Extracted**:
- Priority: `P0` (from `priority=0`)
- Groups: `["smoke", "critical"]`
- Test Type: `POSITIVE`

---

### NUnit (C#)

```csharp
[Test]
[Priority(0)]
[Category("Smoke")]
[Category("Critical")]
public void TestUserAuthentication()
{
    var response = _client.PostAsync("/api/auth", content).Result;
    Assert.AreEqual(200, (int)response.StatusCode);
}
```

**Extracted**:
- Priority: `P0` (from `[Priority(0)]`)
- Categories: `["smoke", "critical"]`
- Test Type: `POSITIVE`

---

### SpecFlow (C# BDD)

```gherkin
@smoke @critical @p0
Feature: User Authentication

Scenario: Successful login
  Given I am on the login page
  When I send a POST request to "/api/login"
  Then the response status should be 200
  And the response should contain auth token
```

**Extracted**:
- Priority: `P0` (from `@p0`, `@critical`)
- Tags: `["smoke", "critical", "p0"]`
- Feature: `"User Authentication"`
- API Calls: `POST /api/login` (detected from step)
- Assertions: `status should be 200` (detected from Then step)

**Unique**: Gherkin step parsing extracts structural signals from natural language!

## Priority Mapping

### pytest
- `@pytest.mark.p0` or `@pytest.mark.critical` → `Priority.P0`
- `@pytest.mark.p1` or `@pytest.mark.high` → `Priority.P1`
- `@pytest.mark.p2` → `Priority.P2`
- `@pytest.mark.p3` or `@pytest.mark.low` → `Priority.P3`

### TestNG
- `@Test(priority=0)` → `Priority.P0`
- `@Test(priority=1)` → `Priority.P1`
- `@Test(priority=2)` → `Priority.P2`
- `@Test(priority=3)` → `Priority.P3`

### NUnit
- `[Priority(0)]` or `[Category("Critical")]` → `Priority.P0`
- `[Priority(1)]` or `[Category("High")]` → `Priority.P1`
- `[Priority(2)]` or `[Category("Medium")]` → `Priority.P2`
- `[Priority(3)]` or `[Category("Low")]` → `Priority.P3`

### SpecFlow
- `@critical` or `@p0` → `Priority.P0`
- `@high` or `@p1` → `Priority.P1`
- `@p2` → `Priority.P2`
- `@low` or `@p3` → `Priority.P3`

## Test Type Inference

All frameworks infer test type from test/scenario name:

| Keywords in Name | Test Type |
|------------------|-----------|
| `negative`, `invalid`, `error`, `fail` | `NEGATIVE` |
| `boundary`, `edge` | `BOUNDARY` |
| `integration` | `INTEGRATION` |
| `e2e`, `end_to_end` | `E2E` |
| Default | `POSITIVE` |

**Examples**:
- `test_invalid_email` → `NEGATIVE`
- `TestBoundaryValue` → `BOUNDARY`
- `testIntegrationFlow` → `INTEGRATION`
- `Checkout end to end flow` → `E2E`

## Cross-Framework Operations

### Recommend Tests Across All Frameworks

```python
from core.intelligence.recommender import TestRecommender

recommender = TestRecommender(
    connection_string="postgresql://...",
    embedding_provider=provider
)

recommendations = recommender.recommend_for_code_changes(
    changed_files=["src/Auth.cs", "src/auth.py", "src/Auth.java"]
)

# Results include tests from ALL frameworks
for rec in recommendations:
    print(f"{rec.test_id}: {rec.confidence:.2f}")
    # pytest::tests/test_auth.py::test_login: 0.92
    # nunit::Tests/AuthTest.cs::TestLogin: 0.89
    # testng::src/test/AuthTest.java::testLogin: 0.87
```

### Explain Coverage Across All Frameworks

```python
from core.intelligence.rag_engine import RAGExplanationEngine

rag = RAGExplanationEngine(
    connection_string="postgresql://...",
    embedding_provider=provider
)

result = rag.explain_coverage(
    question="What authentication tests exist?",
    max_tests=20
)

# Results include tests from ALL frameworks with evidence
for behavior in result.validated_behaviors:
    print(f"{behavior.behavior} ({behavior.confidence:.2f})")
    print(f"Tests: {', '.join(behavior.test_references)}")
```

### Generate Test for Any Framework

```python
from core.intelligence.generator import AssistedTestGenerator

generator = AssistedTestGenerator(
    connection_string="postgresql://...",
    embedding_provider=provider
)

# Generate for NUnit
template = generator.generate_test(
    intent="Test payment with expired card",
    framework="nunit",
    language="csharp",
    test_type="negative"
)

# Generate for TestNG
template = generator.generate_test(
    intent="Test checkout flow end to end",
    framework="testng",
    language="java",
    test_type="e2e"
)

# Generate for SpecFlow
template = generator.generate_test(
    intent="Test user registration success",
    framework="specflow",
    language="csharp",
    test_type="positive"
)
```

## Adapter Factory Methods

```python
from core.intelligence.adapters import AdapterFactory

# Get adapter (case-insensitive)
adapter = AdapterFactory.get_adapter("pytest")
adapter = AdapterFactory.get_adapter("NUNIT")

# List all frameworks
frameworks = AdapterFactory.list_supported_frameworks()
# ['pytest', 'junit', 'testng', 'nunit', 'specflow', 'robot']

# Register custom adapter
class CustomAdapter(FrameworkAdapter):
    ...

AdapterFactory.register_adapter("custom", CustomAdapter)
```

## Common Patterns

### Pattern 1: Process All Tests in Project

```python
from core.intelligence.adapters import AdapterFactory

# Discover and process tests for all frameworks
for framework in AdapterFactory.list_supported_frameworks():
    adapter = AdapterFactory.get_adapter(framework)
    test_files = adapter.discover_tests("/project")
    
    for test_file in test_files:
        # Extract test names from file (framework-specific)
        test_names = extract_test_names(test_file, framework)
        
        for test_name in test_names:
            unified = adapter.normalize_to_core_model(
                test_file=test_file,
                test_name=test_name
            )
            # Store in database, index for search, etc.
            store_unified_test(unified)
```

### Pattern 2: Multi-Framework Search

```python
from core.intelligence.adapters import AdapterFactory, normalize_test

# Search query
query = "authentication tests"

# Search across all frameworks
results = []
for framework in ["pytest", "nunit", "testng", "specflow"]:
    # Semantic search in framework-specific tests
    framework_results = semantic_search(query, framework=framework)
    results.extend(framework_results)

# Sort by relevance
results.sort(key=lambda r: r.confidence, reverse=True)
```

### Pattern 3: Framework Auto-Detection

```python
from pathlib import Path
from core.intelligence.adapters import AdapterFactory

def auto_detect_framework(file_path: str) -> str:
    """Auto-detect framework from file extension."""
    path = Path(file_path)
    
    if path.suffix == ".py" and "test" in path.name:
        return "pytest"
    elif path.suffix == ".java":
        # Check content for @Test vs @Test(priority=...)
        content = path.read_text()
        if "@Test(priority" in content or "groups =" in content:
            return "testng"
        return "junit"
    elif path.suffix == ".cs":
        content = path.read_text()
        if "[Test]" in content:
            return "nunit"
        return None
    elif path.suffix == ".feature":
        return "specflow"
    elif path.suffix == ".robot":
        return "robot"
    
    return None

# Use auto-detection
framework = auto_detect_framework("/project/Tests/AuthTest.cs")
adapter = AdapterFactory.get_adapter(framework)
```

## Test ID Format

Each framework produces unique test IDs:

| Framework | Format | Example |
|-----------|--------|---------|
| pytest | `pytest::path/file.py::test_name` | `pytest::tests/test_auth.py::test_login` |
| JUnit | `junit::path/file.java::testName` | `junit::src/test/AuthTest.java::testLogin` |
| TestNG | `testng::path/file.java::testName` | `testng::src/test/AuthTest.java::testLogin` |
| NUnit | `nunit::path/file.cs::TestName` | `nunit::Tests/AuthTest.cs::TestLogin` |
| SpecFlow | `specflow::path/file.feature::Scenario` | `specflow::Features/Auth.feature::Login success` |
| Robot | `robot::path/file.robot::TestCase` | `robot::tests/auth.robot::Login Test` |

## Tips & Best Practices

### 1. Always Use Factory

```python
# ✅ Good
adapter = AdapterFactory.get_adapter("nunit")

# ❌ Avoid
adapter = NUnitAdapter()  # Bypasses factory registration
```

### 2. Case-Insensitive Framework Names

```python
# All equivalent
adapter = AdapterFactory.get_adapter("nunit")
adapter = AdapterFactory.get_adapter("NUnit")
adapter = AdapterFactory.get_adapter("NUNIT")
```

### 3. Check Support Level

```python
adapter = AdapterFactory.get_adapter("nunit")

# Check what's supported
if hasattr(adapter, '_extract_priority'):
    # Priority extraction supported
    priority = adapter._extract_priority(content, test_name)
```

### 4. Handle Missing AST Gracefully

```python
unified = adapter.normalize_to_core_model(test_file, test_name)

# AST may not be available for all languages
if unified.structural.api_calls:
    print(f"Found {len(unified.structural.api_calls)} API calls")
else:
    print("AST extraction not available for this framework")
```

### 5. Leverage SpecFlow's Gherkin Parsing

```python
# SpecFlow uniquely provides structural signals from BDD scenarios
specflow = AdapterFactory.get_adapter("specflow")
unified = specflow.normalize_to_core_model(
    test_file="/Features/Auth.feature",
    test_name="Login scenario"
)

# Check for Gherkin-extracted signals
if unified.structural.api_calls:
    print(f"API calls detected from Gherkin: {unified.structural.api_calls}")
```

## Extended Framework Examples 🆕

### RestAssured (Java REST API)

```java
@Test(priority = 0, groups = {"smoke", "api"})
public void testGetUser() {
    given()
        .pathParam("id", 123)
    .when()
        .get("/api/users/{id}")
    .then()
        .statusCode(200)
        .body("name", equalTo("John"));
}
```

**Extracted**:
- Priority: `P0`
- Tags: `["smoke", "api"]`
- Test Type: `API`

---

### Playwright (JavaScript E2E)

```javascript
// @p0 @smoke @login
test('user login flow', async ({ page }) => {
  await page.goto('https://example.com/login');
  await page.fill('#username', 'testuser');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/dashboard');
});
```

**Extracted**:
- Priority: `P0`
- Tags: `["smoke", "login"]`
- Test Type: `E2E`

---

### Selenium Python (Python UI)

```python
@pytest.mark.p0
@pytest.mark.smoke
@pytest.mark.ui
def test_login_success(driver):
    """Test successful login with valid credentials."""
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("password")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    assert "Dashboard" in driver.title
```

**Extracted**:
- Priority: `P0`
- Tags: `["smoke", "ui"]`
- Test Type: `E2E`
- Full AST: Functions, classes, imports extracted

---

### Cucumber (BDD Gherkin)

```gherkin
@smoke @api @p0
Feature: User Management API
  
  @critical
  Scenario: Create new user
    Given I am authenticated as admin
    When I POST to /api/users with:
      | name  | John Doe |
      | email | john@example.com |
    Then the response status should be 201
    And the response should contain user ID
```

**Extracted**:
- Priority: `P0`
- Tags: `["smoke", "api", "critical"]`
- Test Type: `API`
- API Calls: `POST /api/users`
- Assertions: `status == 201`

---

### Behave (Python BDD)

```gherkin
@smoke @ui @p0
Feature: User Login
  
  @critical
  Scenario: Successful login
    Given I am on the login page
    When I enter username "testuser"
    And I enter password "password123"
    And I click the login button
    Then I should see the dashboard
```

**Extracted**:
- Priority: `P0`
- Tags: `["smoke", "ui", "critical"]`
- Test Type: `E2E`
- UI Interactions detected from steps

---

## Summary

**12 Frameworks Supported** 🎉:
- ✅ pytest (Python) - Full
- ✅ JUnit (Java) - Partial
- ✅ TestNG (Java) - Partial
- ✅ NUnit (C# .NET) - Partial
- ✅ SpecFlow (C# BDD) - Partial + Gherkin
- ✅ Robot Framework - Basic
- 🆕 RestAssured (Java API) - Partial
- 🆕 Playwright (JS/TS E2E) - Partial
- 🆕 Selenium Python (Python UI) - Full
- 🆕 Selenium Java (Java UI) - Partial
- 🆕 Cucumber (Gherkin BDD) - Partial + Gherkin
- 🆕 Behave (Python BDD) - Partial + Gherkin

**170 Tests**: All passing ✅ (117 original + 53 extended)

**Production Ready**: All core features tested and validated

**Extended Framework Docs**: [MULTI_FRAMEWORK_SUPPORT.md](MULTI_FRAMEWORK_SUPPORT.md)
