# Selenium-Java Runner Quick Start

## Installation

No additional installation required - included with CrossBridge.

## Basic Usage

### Run All Tests in a Class
```bash
crossbridge run --framework selenium-java --tests com.example.LoginTest
```

### Run Specific Method
```bash
crossbridge run --framework selenium-java --tests LoginTest#testValidLogin
```

### Run Multiple Tests
```bash
crossbridge run --framework selenium-java --tests LoginTest,OrderTest,CheckoutTest
```

## Selective Execution

### By Tags (JUnit 5)
```bash
crossbridge run --framework selenium-java --tags smoke
crossbridge run --framework selenium-java --tags smoke,integration
```

### By Groups (TestNG)
```bash
crossbridge run --framework selenium-java --groups smoke
crossbridge run --framework selenium-java --groups smoke,regression
```

### By Categories (JUnit 4)
```bash
crossbridge run --framework selenium-java --categories SmokeTests
```

## Advanced Options

### Parallel Execution
```bash
crossbridge run --framework selenium-java \\
  --tests LoginTest \\
  --parallel --threads 4
```

### Custom Properties
```bash
crossbridge run --framework selenium-java \\
  --tests LoginTest \\
  --properties "browser=chrome,headless=true"
```

### Verbose Output
```bash
crossbridge run --framework selenium-java \\
  --tests LoginTest \\
  --verbose
```

## Integration with Impact Analysis

### 1. Discover Tests with Page Object Mappings
```bash
crossbridge discover --framework selenium-java --include-page-mapping
```

### 2. Find Tests Impacted by Page Object Change
```bash
crossbridge impact --framework selenium-java --page-object LoginPage
```

### 3. Run Only Impacted Tests
```bash
crossbridge run --framework selenium-java --tests LoginTest,UserProfileTest
```

## Supported Build Tools

- ✅ Maven (with Maven Surefire plugin)
- ✅ Gradle (with test task)
- ✅ Maven Wrapper (mvnw)
- ✅ Gradle Wrapper (gradlew)

## Supported Test Frameworks

- ✅ JUnit 4 (with categories)
- ✅ JUnit 5 (with tags)
- ✅ TestNG (with groups)

## CLI Command Reference

| Option | Description | Example |
|--------|-------------|---------|
| `--tests` | Comma-separated test classes/methods | `LoginTest,OrderTest#testCheckout` |
| `--tags` | JUnit 5 tags | `smoke,integration` |
| `--groups` | TestNG groups | `smoke,regression` |
| `--categories` | JUnit 4 categories | `SmokeTests,IntegrationTests` |
| `--parallel` | Enable parallel execution | (flag, no value) |
| `--threads` | Number of parallel threads | `4` |
| `--properties` | Custom system properties | `browser=chrome,headless=true` |
| `--verbose` | Show detailed output | (flag, no value) |

## Example Workflows

### Smoke Test Suite
```bash
crossbridge run --framework selenium-java --tags smoke --parallel --threads 4
```

### Regression Test Suite
```bash
crossbridge run --framework selenium-java --tags regression
```

### Specific Test Debugging
```bash
crossbridge run --framework selenium-java --tests LoginTest#testValidLogin --verbose
```

### CI/CD Integration
```bash
# Run smoke tests on every commit
crossbridge run --framework selenium-java --tags smoke

# Run full regression on main branch
if [ "$BRANCH" = "main" ]; then
  crossbridge run --framework selenium-java --tags regression
fi
```

## Python API

```python
from adapters.java.selenium import run_selenium_java_tests

result = run_selenium_java_tests(
    project_root=".",
    tests=["com.example.LoginTest"],
    tags=["smoke"],
    parallel=True,
    thread_count=4
)

print(f"Status: {result.status}")
print(f"Tests: {result.tests_run} run, {result.tests_passed} passed")
```

## Troubleshooting

### Maven/Gradle Not Found
- Install Maven or Gradle, or use wrapper (mvnw/gradlew)
- Wrapper is auto-detected if present

### Tags Not Working
- JUnit 5: Use `--tags`
- TestNG: Use `--groups`
- JUnit 4: Use `--categories`

### No Tests Executed
- Check test class name matches Maven/Gradle pattern
- Verify tags/groups exist in test classes
- Use `--verbose` to see full output

## More Information

- [Full Documentation](selenium-java-runner.md)
- [Test Examples](../examples/selenium-java-runner/)
- [CLI Usage Guide](cli-usage.md)
- [Impact Analysis](cli-page-mapping.md)
