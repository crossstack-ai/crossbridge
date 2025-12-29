"""
Example CLI usage documentation.
"""

# Discover Tests with Page Object Mappings

## Pytest Example

```bash
# Discover all tests and show which Page Objects they use
python -m cli.main --project-root examples/pytest_sample discover --framework pytest --include-page-mapping
```

**Output:**
```
Found 5 test(s):

  - test_dashboard_navigation
  - test_dashboard_logout
  - test_valid_login
  - test_invalid_login
  - test_empty_credentials

============================================================
PAGE OBJECT MAPPINGS
============================================================

tests.test_dashboard.test_dashboard_navigation
  -> DashboardPage

tests.test_dashboard.test_dashboard_logout
  -> DashboardPage

tests.test_login.test_valid_login
  -> DashboardPage
  -> LoginPage

tests.test_login.test_invalid_login
  -> LoginPage

tests.test_login.test_empty_credentials
  -> LoginPage
```

## Java Example

```bash
# Discover Java tests with Page Object mappings
python -m cli.main --project-root examples/java_tests/junit5_project discover --framework selenium-java --include-page-mapping
```

# Impact Analysis

## Analyze Page Object Changes

When a Page Object changes, find which tests are affected:

```bash
# Find tests impacted by LoginPage changes
python -m cli.main --project-root examples/pytest_sample impact --page-object LoginPage
```

**Output:**
```
Detected framework: pytest

Analyzing impact of changes to: LoginPage
Minimum confidence: 0.5

Impacted tests (3):

  • tests.test_login.test_invalid_login
    Confidence: 1.00
  • tests.test_login.test_empty_credentials
    Confidence: 1.00
  • tests.test_login.test_valid_login
    Confidence: 1.00

Total: 3 test(s) may be affected by changes to LoginPage
```

## Advanced Options

### Confidence Filtering

Only show tests with high confidence:

```bash
python -m cli.main --project-root . impact --page-object LoginPage --min-confidence 0.8
```

### Explicit Framework

Specify framework explicitly:

```bash
python -m cli.main --project-root . impact --framework pytest --page-object LoginPage
```

### Java Impact Analysis

```bash
python -m cli.main --project-root examples/java_tests/junit5_project impact --framework selenium-java --page-object LoginPage
```

# Auto-Detection

If you don't specify `--framework`, it will auto-detect:

```bash
# Auto-detects pytest
python -m cli.main --project-root examples/pytest_sample discover --include-page-mapping

# Auto-detects framework for impact analysis
python -m cli.main --project-root examples/pytest_sample impact --page-object LoginPage
```

# Real-World Scenarios

## Scenario 1: CI/CD Integration

When a Page Object file changes, run only impacted tests:

```bash
# Detect which file changed
CHANGED_FILE="pages/LoginPage.py"

# Extract Page Object name
PAGE_OBJECT=$(basename "$CHANGED_FILE" .py)

# Get impacted tests
python -m cli.main --project-root . impact --page-object "${PAGE_OBJECT}" --min-confidence 0.7 > impacted_tests.txt

# Run only those tests
python -m pytest $(cat impacted_tests.txt | grep "test_" | awk '{print $2}')
```

## Scenario 2: Documentation

Generate test coverage documentation:

```bash
# Show all Page Object mappings
python -m cli.main --project-root . discover --include-page-mapping > test_coverage.txt
```

## Scenario 3: Selective Test Execution

Changed files: `LoginPage.java`, `DashboardPage.java`

```bash
# Get all impacted tests
python -m cli.main impact --page-object LoginPage > login_tests.txt
python -m cli.main impact --page-object DashboardPage > dashboard_tests.txt

# Combine and deduplicate
cat login_tests.txt dashboard_tests.txt | sort -u > all_impacted_tests.txt

# Run with Maven/Gradle
mvn test -Dtest=$(cat all_impacted_tests.txt | grep "test" | tr '\n' ',')
```

## Scenario 4: Test Maintenance

Find all tests using a specific Page Object before refactoring:

```bash
# Before refactoring LoginPage
python -m cli.main impact --page-object LoginPage

# Review list
# Refactor LoginPage
# Re-run those specific tests to verify
```

# Command Reference

## discover

Discover tests in a project.

**Options:**
- `--framework`: Test framework (optional, auto-detects)
- `--include-page-mapping`: Show Page Object mappings

**Examples:**
```bash
# Auto-detect and show mappings
python -m cli.main discover --include-page-mapping

# Specific framework
python -m cli.main --project-root . discover --framework pytest --include-page-mapping
```

## impact

Analyze impact of Page Object changes.

**Options:**
- `--framework`: Test framework (optional, auto-detects)
- `--page-object`: Page Object class name (required)
- `--min-confidence`: Minimum confidence threshold (default: 0.5)

**Examples:**
```bash
# Basic usage
python -m cli.main impact --page-object LoginPage

# With confidence filter
python -m cli.main impact --page-object LoginPage --min-confidence 0.8

# Explicit framework
python -m cli.main --project-root . impact --framework selenium-java --page-object HomePage
```

## Supported Frameworks

- **pytest**: Python testing framework
- **selenium-java**: Java Selenium tests (JUnit 4/5, TestNG)
- **robot**: Robot Framework (coming soon)

# Output Formats

## Page Object Mapping Format

```
<test_id>
  -> <PageObjectName>
  -> <AnotherPageObject>
```

## Impact Analysis Format

```
Impacted tests (<count>):

  • <test_id>
    Confidence: <0.00-1.00>
  • <test_id>
    Confidence: <0.00-1.00>

Total: <count> test(s) may be affected by changes to <PageObject>
```

# Tips

1. **Auto-detection**: Omit `--framework` to auto-detect
2. **Confidence**: Use `--min-confidence` to filter out low-confidence mappings
3. **CI/CD**: Integrate with Git hooks to run impact analysis on changed files
4. **Documentation**: Use `--include-page-mapping` to document test coverage
5. **Selective Testing**: Use impact analysis to run only affected tests
