# Java Test Examples

This directory contains various Java test project scenarios for testing CrossBridge's detection capabilities.

## Project Structure

### 1. junit4_project/
- **Framework**: JUnit 4
- **Build Tool**: Maven (pom.xml)
- **Test Files**:
  - LoginTest.java (4 tests with @Before/@After)
  - SearchTest.java (3 tests with @Category)
- **Detection Methods**: PRIMARY (pom.xml)

### 2. junit5_project/
- **Framework**: JUnit 5 (Jupiter)
- **Build Tool**: Gradle (build.gradle)
- **Test Files**:
  - CheckoutTest.java (7 tests with @DisplayName, @Tag)
  - RegistrationTest.java (5 tests with @ParameterizedTest)
- **Detection Methods**: PRIMARY (build.gradle)

### 3. testng_project/
- **Framework**: TestNG
- **Build Tool**: Maven (pom.xml)
- **Config**: testng.xml
- **Test Files**:
  - ApiTest.java (7 tests with groups, priorities, dependencies)
  - DataDrivenTest.java (5 tests with @DataProvider)
- **Detection Methods**: PRIMARY (pom.xml) + SUPPORTING (testng.xml)

### 4. mixed_project/
- **Frameworks**: JUnit 5 + TestNG (mixed)
- **Build Tool**: Maven (pom.xml with both dependencies)
- **Test Files**:
  - junit/PaymentJUnitTest.java (3 JUnit tests)
  - junit/InventoryJUnitTest.java (2 JUnit tests)
  - testng/NotificationTestNGTest.java (5 TestNG tests)
  - testng/ReportingTestNGTest.java (4 TestNG tests)
- **Detection Methods**: PRIMARY (pom.xml detects both)

### 5. no_build_file/
- **Frameworks**: JUnit 5 + TestNG (mixed)
- **Build Tool**: None (tests source-only detection)
- **Test Files**:
  - CalculatorTest.java (3 JUnit tests)
  - StringUtilsTest.java (3 TestNG tests)
- **Detection Methods**: SECONDARY (source code imports only)

## Testing Commands

### Test Individual Projects

```bash
# JUnit 4 Project
python -m cli.main --project-root examples/java_tests/junit4_project discover

# JUnit 5 Project
python -m cli.main --project-root examples/java_tests/junit5_project discover

# TestNG Project
python -m cli.main --project-root examples/java_tests/testng_project discover

# Mixed Project (should detect both JUnit and TestNG)
python -m cli.main --project-root examples/java_tests/mixed_project discover

# No Build File (source-only detection)
python -m cli.main --project-root examples/java_tests/no_build_file discover
```

### Test Auto-Detection

```bash
# Auto-detect from any project
python -m cli.main --project-root examples/java_tests/junit4_project discover
python -m cli.main --project-root examples/java_tests/mixed_project discover
```

### Test Explicit Framework

```bash
# Override auto-detection
python -m cli.main --project-root examples/java_tests/mixed_project discover --framework selenium-java
```

## Expected Outputs

### junit4_project
```
Detected frameworks: selenium-java
Discovering tests...

[selenium-java]
  Java test frameworks: junit
  [junit] 7 test(s)
```

### mixed_project
```
Detected frameworks: selenium-java
Discovering tests...

[selenium-java]
  Java test frameworks: junit, testng
  [junit] 5 test(s)
  [testng] 9 test(s)

Total: 14 test(s) across 1 framework(s)
```

### no_build_file
```
Detected frameworks: selenium-java
Discovering tests...

[selenium-java]
  Java test frameworks: junit, testng
  [junit] 3 test(s)
  [testng] 3 test(s)
```

## Test Coverage

These examples test:
- ✓ JUnit 4 detection via pom.xml
- ✓ JUnit 5 detection via build.gradle
- ✓ TestNG detection via pom.xml
- ✓ TestNG config file detection (testng.xml)
- ✓ Mixed framework projects (both JUnit + TestNG)
- ✓ Source-only detection (no build files)
- ✓ Maven vs Gradle build tools
- ✓ Various test annotations and patterns
- ✓ Test groups, tags, categories
- ✓ Parameterized/data-driven tests
