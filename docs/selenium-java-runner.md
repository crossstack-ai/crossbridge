# Selenium-Java Runner Adapter

## Overview

The Selenium-Java Runner Adapter enables running JUnit and TestNG Selenium tests from CrossBridge AI CLI with selective execution support. 

**Key Design Principle**: The adapter **does not** reimplement Selenium execution logic in Python. Instead, it delegates execution to native Java build tools (Maven/Gradle), acting as an orchestrator.

## Architecture

```
crossbridge run --framework selenium-java
      ↓
Selenium-Java Adapter (Python)
      ↓
Build Tool Detection (Maven/Gradle)
      ↓
Test Framework Detection (JUnit 4/5/TestNG)
      ↓
Command Builder (native build tool commands)
      ↓
Execution (mvn test / gradle test)
      ↓
Result Parser (JUnit XML + console output)
      ↓
Normalized TestExecutionResult
```

## Supported Features

### Build Tools
- ✅ **Maven** (with Maven Surefire plugin)
- ✅ **Gradle** (with test task)
- ✅ Maven Wrapper (mvnw / mvnw.cmd)
- ✅ Gradle Wrapper (gradlew / gradlew.bat)

### Test Frameworks
- ✅ **JUnit 4** (categories support)
- ✅ **JUnit 5** (tags support)
- ✅ **TestNG** (groups support)

### Selective Execution
- ✅ Specific test classes
- ✅ Specific test methods
- ✅ JUnit 5 tags (e.g., `@Tag("smoke")`)
- ✅ TestNG groups (e.g., `@Test(groups = {"smoke"})`)
- ✅ JUnit 4 categories
- ✅ Parallel execution
- ✅ Custom system properties

## Installation

The adapter is included in CrossBridge AI. No additional installation required.

## Usage

### Basic Test Execution

Run all tests in a class:
```bash
crossbridge run --framework selenium-java --tests com.example.LoginTest
```

Run multiple test classes:
```bash
crossbridge run --framework selenium-java --tests com.example.LoginTest,com.example.OrderTest
```

### Run Specific Test Methods

Maven/JUnit format (using `#`):
```bash
crossbridge run --framework selenium-java --tests LoginTest#testValidLogin,OrderTest#testCheckout
```

Gradle format (using `.`):
```bash
crossbridge run --framework selenium-java --tests LoginTest.testValidLogin
```

### Run By Tags (JUnit 5)

Run all tests tagged with "smoke":
```bash
crossbridge run --framework selenium-java --tags smoke
```

Run multiple tags:
```bash
crossbridge run --framework selenium-java --tags smoke,integration
```

### Run By Groups (TestNG)

Run all tests in "smoke" group:
```bash
crossbridge run --framework selenium-java --groups smoke
```

Run multiple groups:
```bash
crossbridge run --framework selenium-java --groups smoke,regression
```

### Run By Categories (JUnit 4)

```bash
crossbridge run --framework selenium-java --categories SmokeTests,IntegrationTests
```

### Parallel Execution

Enable parallel execution with 4 threads:
```bash
crossbridge run --framework selenium-java --tests LoginTest --parallel --threads 4
```

### Custom System Properties

Pass additional properties to Maven/Gradle:
```bash
crossbridge run --framework selenium-java \\
  --tests LoginTest \\
  --properties "browser=chrome,headless=true"
```

### Verbose Output

Show detailed execution logs:
```bash
crossbridge run --framework selenium-java --tests LoginTest --verbose
```

## Integration with CrossBridge Features

### 1. Impact-Based Execution

Combine with `discover` and `impact` commands:

```bash
# Discover tests and Page Object mappings
crossbridge discover --framework selenium-java --include-page-mapping

# Get impacted tests when LoginPage.java changes
crossbridge impact --framework selenium-java --page-object LoginPage

# Run only impacted tests
crossbridge run --framework selenium-java --tests LoginTest,UserProfileTest
```

### 2. CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Selenium Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Set up Java
        uses: actions/setup-java@v3
        with:
          java-version: '11'
      
      - name: Install CrossBridge AI
        run: pip install -e .
      
      - name: Run smoke tests
        run: |
          crossbridge run --framework selenium-java \\
            --tags smoke \\
            --parallel --threads 4
      
      - name: Run regression tests
        if: github.event_name == 'push'
        run: |
          crossbridge run --framework selenium-java \\
            --tags regression
```

### 3. Change-Based Testing

Run tests affected by specific Page Object changes:

```python
# Python script: ci/run_changed_tests.py
from adapters.java.selenium import run_selenium_java_tests
from adapters.java.impact_mapper import create_impact_map

# Get changed files from git
changed_files = get_changed_files()

# Get impacted tests
impact_map = create_impact_map(".")
impacted_tests = set()

for file in changed_files:
    if "Page.java" in file:
        page_object = extract_class_name(file)
        tests = impact_map.get_impacted_tests(page_object)
        impacted_tests.update(tests)

# Run only impacted tests
if impacted_tests:
    result = run_selenium_java_tests(
        project_root=".",
        tests=list(impacted_tests)
    )
    
    print(f"Ran {result.tests_run} impacted tests")
    print(f"Status: {result.status}")
```

## Command Reference

### Maven Commands Generated

| Scenario | Generated Command |
|----------|-------------------|
| Run test class | `mvn test -Dtest=LoginTest` |
| Run method | `mvn test -Dtest=LoginTest#testValidLogin` |
| Multiple tests | `mvn test -Dtest=LoginTest,OrderTest` |
| JUnit 5 tags | `mvn test -Dgroups=smoke,integration` |
| TestNG groups | `mvn test -Dgroups=smoke,regression` |
| JUnit 4 categories | `mvn test -Dcategories=SmokeTests` |
| Parallel | `mvn test -Dparallel=methods -DthreadCount=4` |

### Gradle Commands Generated

| Scenario | Generated Command |
|----------|-------------------|
| Run test class | `gradle test --tests LoginTest` |
| Run method | `gradle test --tests LoginTest.testValidLogin` |
| Multiple tests | `gradle test --tests LoginTest --tests OrderTest` |
| JUnit 5 tags | `gradle test -DincludeTags=smoke` |
| TestNG groups | `gradle test -Dgroups=smoke` |

## API Reference

### Python API

```python
from adapters.java.selenium import run_selenium_java_tests

# Run tests programmatically
result = run_selenium_java_tests(
    project_root="/path/to/project",
    tests=["com.example.LoginTest"],
    tags=["smoke"],
    parallel=True,
    thread_count=4
)

# Check results
print(f"Status: {result.status}")
print(f"Tests run: {result.tests_run}")
print(f"Tests passed: {result.tests_passed}")
print(f"Tests failed: {result.tests_failed}")
print(f"Execution time: {result.execution_time}s")
print(f"Report path: {result.report_path}")
```

### SeleniumJavaAdapter Class

```python
from adapters.java.selenium import SeleniumJavaAdapter

# Create adapter
adapter = SeleniumJavaAdapter("/path/to/project")

# Get project info
info = adapter.get_info()
print(f"Build tool: {info['build_tool']}")
print(f"Test framework: {info['test_framework']}")

# Run tests
result = adapter.run_tests(
    tests=["LoginTest"],
    tags=["smoke"]
)
```

## Test Reports

### Maven (Surefire Reports)

Reports location: `target/surefire-reports/`

- JUnit XML: `TEST-*.xml`
- Text summaries: `*.txt`
- HTML reports (with maven-surefire-report-plugin)

### Gradle

Reports location: `build/test-results/test/`

- JUnit XML: `TEST-*.xml`
- HTML reports: `build/reports/tests/test/index.html`

## Troubleshooting

### Maven Not Found

**Error**: `Maven not found. Please install Maven or use Maven wrapper (mvnw).`

**Solution**:
1. Install Maven: `brew install maven` (macOS) or download from maven.apache.org
2. Or use Maven wrapper if available: `./mvnw` (auto-detected by adapter)

### Gradle Not Found

**Error**: `Gradle not found. Please install Gradle or use Gradle wrapper (gradlew).`

**Solution**:
1. Install Gradle: `brew install gradle` (macOS) or download from gradle.org
2. Or use Gradle wrapper if available: `./gradlew` (auto-detected by adapter)

### Tags Not Supported

**Error**: `Tags are not supported by junit4. Use categories instead.`

**Solution**: Use the correct selective execution feature for your framework:
- JUnit 4: `--categories`
- JUnit 5: `--tags`
- TestNG: `--groups`

### No Tests Executed

**Possible Causes**:
1. Test class name pattern doesn't match Maven/Gradle configuration
2. Test methods are not public (JUnit 4)
3. Test class is abstract
4. Tag/group doesn't exist

**Solution**: Run with `--verbose` to see full output:
```bash
crossbridge run --framework selenium-java --tests LoginTest --verbose
```

## Examples

See [examples/selenium-java-runner/](../examples/selenium-java-runner/) for complete working examples:

- `maven-junit5/` - Maven project with JUnit 5 and tags
- `maven-testng/` - Maven project with TestNG and groups
- `gradle-junit5/` - Gradle project with JUnit 5
- `mixed-framework/` - Project with both JUnit and TestNG

## Performance Considerations

### Parallel Execution

Enable parallel execution for faster test runs:

```bash
# Run tests in parallel with 4 threads
crossbridge run --framework selenium-java \\
  --tests "com.example.*Test" \\
  --parallel --threads 4
```

**Maven Configuration Required**:
```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <parallel>methods</parallel>
        <threadCount>4</threadCount>
    </configuration>
</plugin>
```

### Test Discovery Caching

The adapter caches test discovery results for faster subsequent runs. To force re-discovery:

```bash
crossbridge discover --framework selenium-java --force-refresh
```

## Related Documentation

- [CLI Usage Guide](cli-usage.md)
- [Impact Mapping](cli-page-mapping.md)
- [Test Discovery](test-discovery.md)
- [CI/CD Integration](cicd-integration.md)
