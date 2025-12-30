# Coverage Mapping Implementation Guide

## Overview

The Coverage Mapping system enables **precise test-to-code coverage tracking** for impact analysis. Unlike heuristic-based approaches, coverage mapping provides deterministic knowledge of which production code paths are executed by each test.

## Key Features

### 1. Per-Test Isolation (High Confidence)
- Execute single test with coverage instrumentation
- Confidence score: **0.90-0.95**
- Use case: Critical tests, pre-merge validation
- Trade-off: Slower execution, highest accuracy

### 2. Batch Correlation (Lower Confidence)
- Execute multiple tests, correlate shared coverage
- Confidence score: **0.60-0.75**
- Use case: Large test suites, overnight builds
- Trade-off: Faster execution, reduced precision

### 3. Cucumber Scenario Aggregation
- Map scenarios → steps → Java methods → production code
- Aggregate step coverage into scenario-level view
- Support for step-level granularity

### 4. Database Persistence
- Append-only design (never UPDATE coverage data)
- Fast impact queries via indexed class/method lookups
- Historical tracking of coverage evolution

### 5. Impact Analysis
- Query: "Which tests cover `LoginService.java`?"
- Query: "What code does `testUserLogin` execute?"
- Query: "Which tests must run after `UserService.java` changed?"

## Architecture

```
┌─────────────────────────────────────────────────┐
│ CoverageMappingEngine                           │
│  - collect_coverage_isolated()                  │
│  - collect_coverage_batch()                     │
│  - query_impact()                               │
└──────────────┬──────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼──────────────┐  ┌──▼──────────────────────┐
│ JaCoCoXMLParser  │  │ CucumberCoverageAggregator│
│  - parse()       │  │  - aggregate_scenario()   │
│  - parse_batch() │  │  - aggregate_feature()    │
└──────────────────┘  └──────────────────────────┘
         │                      │
         │                      │
    ┌────▼──────────────────────▼───┐
    │ CoverageRepository             │
    │  - save_test_coverage()        │
    │  - get_tests_covering_class()  │
    │  - get_impact_for_changed_classes() │
    └────────────────────────────────┘
              │
         ┌────▼─────┐
         │ Database │
         │  - test_code_coverage       │
         │  - scenario_code_coverage   │
         │  - coverage_discovery_run   │
         └──────────────────────────────┘
```

## Quick Start

### 1. Maven Project Setup

**Add JaCoCo plugin to `pom.xml`:**

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.jacoco</groupId>
            <artifactId>jacoco-maven-plugin</artifactId>
            <version>0.8.11</version>
            <executions>
                <execution>
                    <goals>
                        <goal>prepare-agent</goal>
                    </goals>
                </execution>
                <execution>
                    <id>report</id>
                    <phase>test</phase>
                    <goals>
                        <goal>report</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

**JaCoCo report location:** `target/site/jacoco/jacoco.xml`

### 2. Gradle Project Setup

**Add JaCoCo plugin to `build.gradle`:**

```gradle
plugins {
    id 'java'
    id 'jacoco'
}

jacoco {
    toolVersion = "0.8.11"
}

jacocoTestReport {
    reports {
        xml.required = true
        html.required = true
    }
}

test {
    finalizedBy jacocoTestReport
}
```

**JaCoCo report location:** `build/reports/jacoco/test/jacocoTestReport.xml`

### 3. Collect Coverage (Isolated)

```bash
# Collect coverage for single test (highest confidence)
crossbridge coverage collect-isolated \
    --test-id "LoginTest.testSuccessfulLogin" \
    --test-command "mvn test -Dtest=LoginTest#testSuccessfulLogin" \
    --working-dir ./my-project \
    --framework junit
```

**Output:**
```
Collecting isolated coverage for: LoginTest.testSuccessfulLogin
✓ Coverage collected successfully
  Classes covered: 12
  Methods covered: 34
  Confidence: 0.95
```

### 4. Collect Coverage (Batch)

```bash
# Collect coverage for multiple tests (faster, lower confidence)
crossbridge coverage collect-batch \
    --test-command "mvn test" \
    --working-dir ./my-project \
    LoginTest.testSuccessfulLogin \
    LoginTest.testFailedLogin \
    UserTest.testRegistration
```

**Output:**
```
Collecting batch coverage for 3 tests
✓ Coverage collected for 3 tests
  Total classes covered: 25
  Total methods covered: 78
```

## CLI Commands

### `collect-isolated`

Collect coverage for a single test with highest confidence.

```bash
crossbridge coverage collect-isolated \
    --test-id <test_id> \
    --test-command <maven_or_gradle_command> \
    --working-dir <project_directory> \
    --framework junit|cucumber \
    --timeout 300
```

**Parameters:**
- `--test-id`: Unique test identifier (e.g., `LoginTest.testSuccessfulLogin`)
- `--test-command`: Command to run test (e.g., `mvn test -Dtest=LoginTest#testSuccessfulLogin`)
- `--working-dir`: Project root directory (default: current directory)
- `--framework`: Test framework (default: `junit`)
- `--timeout`: Execution timeout in seconds (default: 300)
- `--db`: Database path (default: `crossbridge.db`)

**Example:**
```bash
crossbridge coverage collect-isolated \
    --test-id "com.example.LoginTest.testSuccessfulLogin" \
    --test-command "mvn test -Dtest=LoginTest#testSuccessfulLogin" \
    --working-dir /path/to/project
```

### `collect-batch`

Collect coverage for multiple tests in one execution.

```bash
crossbridge coverage collect-batch \
    --test-command <maven_or_gradle_command> \
    --working-dir <project_directory> \
    <test_id_1> <test_id_2> <test_id_3>
```

**Example:**
```bash
crossbridge coverage collect-batch \
    --test-command "mvn test" \
    LoginTest.testSuccessfulLogin \
    LoginTest.testFailedLogin \
    UserTest.testRegistration
```

### `show`

Display coverage for a specific test.

```bash
crossbridge coverage show \
    --test-id <test_id> \
    --format text|json
```

**Example:**
```bash
crossbridge coverage show --test-id LoginTest.testSuccessfulLogin
```

**Output:**
```
Coverage for: LoginTest.testSuccessfulLogin
Total records: 15

  com.example.service.LoginService
    - authenticate: 95.2% (confidence: 0.95)
    - validateCredentials: 88.7% (confidence: 0.95)

  com.example.repository.UserRepository
    - findByUsername: 100.0% (confidence: 0.95)
```

### `stats`

Show overall coverage statistics.

```bash
crossbridge coverage stats
```

**Output:**
```
Coverage Statistics:
  Total tests: 145
  Total classes covered: 78
  Total methods covered: 456
  Average confidence: 0.82

  By framework:
    junit: 120 tests
    cucumber: 25 tests
```

### `impact`

Query which tests are impacted by changed classes.

```bash
crossbridge coverage impact \
    --min-confidence 0.7 \
    com.example.LoginService \
    com.example.UserService
```

**Output:**
```
Impact Analysis:
  Changed classes: 2
    - com.example.LoginService
    - com.example.UserService

  Affected tests: 18
    - LoginTest.testSuccessfulLogin (junit)
      Confidence: 0.95
      Covers: com.example.LoginService, com.example.UserService

    - LoginTest.testFailedLogin (junit)
      Confidence: 0.92
      Covers: com.example.LoginService
```

### `tests-for-class`

Find all tests that cover a specific class.

```bash
crossbridge coverage tests-for-class \
    --class-name com.example.LoginService \
    --min-confidence 0.7
```

**Output:**
```
Tests covering com.example.LoginService:
Total: 12

  LoginTest.testSuccessfulLogin (junit)
    Confidence: 0.95
    Methods covered: 5
    Latest discovery: 2024-01-15 10:23:45
```

### `tests-for-method`

Find all tests that cover a specific method.

```bash
crossbridge coverage tests-for-method \
    --class-name com.example.LoginService \
    --method-name authenticate \
    --min-confidence 0.7
```

## Database Schema

### `test_code_coverage` Table

Stores test-to-code coverage mappings (append-only).

```sql
CREATE TABLE test_code_coverage (
    id INTEGER PRIMARY KEY,
    test_id TEXT NOT NULL,
    test_name TEXT,
    test_framework TEXT,
    class_name TEXT NOT NULL,
    method_name TEXT,
    coverage_type TEXT NOT NULL,  -- 'instruction', 'line', 'branch'
    covered_count INTEGER,
    missed_count INTEGER,
    coverage_percentage REAL,
    confidence REAL,
    execution_mode TEXT,  -- 'isolated', 'small_batch', 'full_suite'
    discovery_run_id TEXT,
    discovery_timestamp TIMESTAMP,
    ...
);

-- Indexes for fast queries
CREATE INDEX idx_coverage_class ON test_code_coverage(class_name, confidence DESC);
CREATE INDEX idx_coverage_method ON test_code_coverage(class_name, method_name, confidence DESC);
```

### `scenario_code_coverage` Table

Stores Cucumber scenario-level coverage (aggregated from steps).

```sql
CREATE TABLE scenario_code_coverage (
    id INTEGER PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    scenario_name TEXT,
    feature_name TEXT,
    class_name TEXT NOT NULL,
    method_name TEXT,
    coverage_type TEXT,
    confidence REAL,
    step_count INTEGER,
    ...
);
```

## Confidence Scoring

Coverage confidence is calculated based on **execution mode**:

| Execution Mode | Confidence | Use Case |
|---------------|-----------|----------|
| `ISOLATED` | 0.90-0.95 | Single test execution, no interference |
| `SMALL_BATCH` | 0.60-0.75 | 5-20 tests together, shared coverage |
| `FULL_SUITE` | 0.40-0.50 | 100+ tests, high ambiguity |

**Confidence formula:**
```python
confidence = base_confidence * (1 - batch_penalty)

# Isolated: 0.95 * 1.0 = 0.95
# Small batch (10 tests): 0.95 * (1 - 0.2) = 0.76
# Full suite (100 tests): 0.95 * (1 - 0.5) = 0.47
```

**Adjustments:**
- Has source paths: +0.05
- Has line numbers: +0.03
- Multiple coverage types (line + branch): +0.02

## Integration with Flaky Detection

Coverage mapping enhances flaky detection by providing **coverage-weighted flaky scores**:

```python
# Traditional flaky score
flaky_score = ml_model.predict(features)

# Coverage-weighted flaky score
coverage_confidence = get_coverage_confidence(test_id)
weighted_score = flaky_score * (0.7 + 0.3 * coverage_confidence)
```

**Benefits:**
- Tests with high coverage confidence get more reliable flaky scores
- Tests with low/no coverage data are flagged for coverage collection
- Reduces false positives by considering execution isolation

## Cucumber Scenario Aggregation

### Problem
JaCoCo knows about Java methods, not Cucumber scenarios. We need to bridge:
```
Scenario → Steps → Java step definitions → Production code
```

### Solution

**1. Parse Cucumber JSON:**
```json
{
  "name": "User logs in successfully",
  "steps": [
    {"keyword": "Given", "name": "user is on login page"},
    {"keyword": "When", "name": "user enters valid credentials"},
    {"keyword": "Then", "name": "user sees dashboard"}
  ]
}
```

**2. Map Steps to Java Methods:**
```java
@Given("user is on login page")
public void userIsOnLoginPage() {
    loginPage.open();  // → com.example.pages.LoginPage.open()
}
```

**3. Aggregate Coverage:**
```
Scenario "User logs in successfully"
  ├─ Step: "Given user is on login page"
  │   └─ Methods: LoginPage.open(), LoginPage.waitForLoad()
  ├─ Step: "When user enters valid credentials"
  │   └─ Methods: LoginPage.enterUsername(), LoginPage.enterPassword(), LoginPage.clickLogin()
  └─ Step: "Then user sees dashboard"
      └─ Methods: DashboardPage.isDisplayed(), DashboardPage.getWelcomeMessage()

Aggregated Coverage:
  - com.example.pages.LoginPage: [open, waitForLoad, enterUsername, enterPassword, clickLogin]
  - com.example.pages.DashboardPage: [isDisplayed, getWelcomeMessage]
```

### CLI Example

```bash
# Collect Cucumber scenario coverage
crossbridge coverage collect-isolated \
    --test-id "Login.feature::User logs in successfully" \
    --test-command "mvn test -Dcucumber.options='--name \"User logs in successfully\"'" \
    --framework cucumber
```

## Impact Analysis Workflow

### 1. Code Change Detected
```bash
git diff --name-only HEAD~1
# Output: src/main/java/com/example/LoginService.java
```

### 2. Extract Changed Classes
```bash
# Parse changed files to extract fully qualified class names
changed_classes = ["com.example.LoginService", "com.example.UserRepository"]
```

### 3. Query Impact
```bash
crossbridge coverage impact \
    --min-confidence 0.7 \
    com.example.LoginService \
    com.example.UserRepository \
    --format json
```

### 4. Execute Affected Tests
```bash
# Run only affected tests
mvn test -Dtest=LoginTest,UserTest,RegistrationTest
```

## Performance Considerations

### Isolated Execution
- **Time:** 5-10 seconds per test
- **Confidence:** 0.95
- **Use case:** Pre-merge, critical tests

### Batch Execution
- **Time:** 2-5 minutes for 100 tests
- **Confidence:** 0.75 (10 tests), 0.50 (100+ tests)
- **Use case:** Overnight builds, large test suites

### Recommendations

1. **Tier 1 (Critical):** Always isolate (500-1000 tests)
2. **Tier 2 (Important):** Small batches of 10-20 tests
3. **Tier 3 (Regression):** Full suite batch execution

## Troubleshooting

### JaCoCo Report Not Found

**Error:** `JaCoCo report not found in /path/to/project`

**Solution:**
1. Verify JaCoCo plugin is configured in `pom.xml` or `build.gradle`
2. Check report path:
   - Maven: `target/site/jacoco/jacoco.xml`
   - Gradle: `build/reports/jacoco/test/jacocoTestReport.xml`
3. Run tests to generate report: `mvn test` or `gradle test jacocoTestReport`

### Low Confidence Scores

**Issue:** Coverage confidence is below 0.5

**Causes:**
- Batch execution with 100+ tests
- Missing source file paths in JaCoCo report
- No line number information

**Solution:**
- Use isolated execution for critical tests
- Enable source paths in JaCoCo configuration
- Reduce batch size to 10-20 tests

### No Coverage Data

**Issue:** `get_tests_covering_class()` returns empty

**Causes:**
- Coverage not collected for tests
- Class name mismatch (package naming)
- Database not initialized

**Solution:**
1. Run `collect-isolated` or `collect-batch` first
2. Verify class name format: `com.example.LoginService` (not `LoginService`)
3. Check database: `crossbridge coverage stats`

## Future Extensions

### Phase 2: Python Coverage
- Use `coverage.py` for Pytest
- Parse `.coverage` file or `coverage.xml`
- Map tests to Python modules/functions

### Phase 3: JavaScript Coverage
- Use Istanbul/NYC for Playwright/Cypress
- Parse `coverage/coverage-final.json`
- Map tests to JS/TS files/functions

### Phase 4: Coverage-Driven Test Selection
- ML model predicts test failure using coverage + git changes
- Prioritize tests by coverage-weighted risk score
- Adaptive test selection based on confidence

## API Reference

### `CoverageMappingEngine`

```python
from core.coverage import CoverageMappingEngine
from pathlib import Path

engine = CoverageMappingEngine(db_path=Path("crossbridge.db"))

# Collect isolated coverage
mapping = engine.collect_coverage_isolated(
    test_id="LoginTest.testSuccessfulLogin",
    test_command="mvn test -Dtest=LoginTest#testSuccessfulLogin",
    working_dir=Path("./my-project"),
    test_framework="junit",
    timeout=300
)

# Query impact
impact = engine.query_impact(
    changed_classes={"com.example.LoginService"},
    min_confidence=0.7
)

print(f"Affected tests: {impact.affected_test_count}")
for test_id in impact.affected_tests:
    print(f"  - {test_id}")
```

### `JaCoCoXMLParser`

```python
from core.coverage import JaCoCoXMLParser
from pathlib import Path

parser = JaCoCoXMLParser()

# Parse single test coverage
mapping = parser.parse(
    xml_path=Path("target/site/jacoco/jacoco.xml"),
    test_id="LoginTest.testSuccessfulLogin",
    test_name="Test Successful Login"
)

print(f"Classes: {len(mapping.covered_classes)}")
print(f"Methods: {len(mapping.covered_methods)}")
print(f"Confidence: {mapping.confidence}")
```

## Summary

The Coverage Mapping system provides:

1. **Precise Impact Analysis:** Know exactly which tests cover changed code
2. **Confidence Scoring:** Quantify mapping reliability based on execution isolation
3. **Framework Support:** JaCoCo (Java/Selenium), coverage.py (Python), Istanbul (JS) planned
4. **BDD Aggregation:** Cucumber scenarios mapped to production code
5. **Fast Queries:** Indexed database for sub-second impact lookups

This foundational capability enables **coverage-driven test selection**, **flaky detection enhancement**, and **AI-assisted test generation**.
