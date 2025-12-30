# Selenium BDD Java Adapter

Adapter for extracting test metadata from Cucumber/Gherkin `.feature` files in Java BDD projects.

## Overview

This adapter parses Cucumber/Gherkin feature files and extracts:
- Feature names
- Scenarios and Scenario Outlines  
- Feature-level and scenario-level tags
- File paths

## Usage

### CLI Discovery

```bash
# Auto-detect and discover BDD tests
python -m cli.main discover

# Explicitly specify selenium-bdd-java framework
python -m cli.main discover --framework selenium-bdd-java

# From specific directory
cd my-bdd-project
python -m cli.main discover --framework selenium-bdd-java
```

### Programmatic Usage

```python
from adapters.selenium_bdd_java import SeleniumBDDJavaExtractor, SeleniumBDDJavaConfig

# Create config
config = SeleniumBDDJavaConfig(
    features_dir="src/test/resources/features"
)

# Extract tests
extractor = SeleniumBDDJavaExtractor(config)
tests = extractor.extract_tests()

for test in tests:
    print(f"{test.test_name} - Tags: {test.tags}")
```

## Configuration

```python
@dataclass
class SeleniumBDDJavaConfig:
    features_dir: str = "src/test/resources/features"  # Where .feature files are located
    runner_type: str = "cucumber-junit"                 # cucumber-junit or cucumber-testng
    encoding: str = "utf-8"                            # File encoding
    ignore_patterns: list = []                         # Glob patterns to ignore
```

## Example Feature File

```gherkin
@auth @smoke
Feature: Login Feature

  Background:
    Given the application is running

  @positive @critical
  Scenario: Valid login
    Given user is on login page
    When user enters valid credentials
    Then login should be successful

  @negative
  Scenario: Invalid login
    Given user is on login page
    When user enters invalid credentials
    Then error message should be displayed

  Scenario Outline: Login with different users
    Given user enters username "<username>"
    When user enters password "<password>"
    Then user should see "<result>"

    Examples:
      | username | password | result    |
      | admin    | admin123 | dashboard |
      | user     | user123  | home      |
```

## Extracted Output

```python
TestMetadata(
    framework="selenium-bdd-java",
    test_name="Login Feature::Valid login",
    file_path="src/test/resources/features/login.feature",
    tags=["auth", "smoke", "positive", "critical"],
    test_type="ui",
    language="java"
)
```

## Features

✅ **Feature Extraction**: Parses `Feature:` declarations  
✅ **Scenario Support**: Handles both `Scenario` and `Scenario Outline`  
✅ **Tag Hierarchy**: Combines feature-level and scenario-level tags  
✅ **Multiple Tags**: Supports multiple tags per line (`@tag1 @tag2`)  
✅ **Nested Directories**: Recursively discovers `.feature` files  
✅ **Ignore Patterns**: Exclude draft/WIP features via glob patterns  
✅ **Background Support**: Recognizes `Background` sections (not extracted as tests)  
✅ **Comments**: Ignores `#` comment lines  

## Test Name Format

Test names follow the pattern: `{Feature Name}::{Scenario Name}`

Examples:
- `Login Feature::Valid login`
- `Shopping Cart::Add single item to cart`
- `Search Functionality::Search with valid keyword`

## Tag Inheritance

Tags are inherited from feature level to scenario level:

```gherkin
@auth              ← Feature-level tag
Feature: Login

  @smoke           ← Scenario-level tag
  Scenario: Test
```

Result: `tags=["auth", "smoke"]` (combined)

## Integration

### With Persistence Layer

```bash
# Persist discovered tests to PostgreSQL
python -m cli.main discover --framework selenium-bdd-java --persist
```

### With Impact Analysis

```bash
# Map tests to changed files
python -m cli.main impact --framework selenium-bdd-java --changed-files src/pages/LoginPage.java
```

## Directory Structure

Standard Maven/Gradle structure:

```
project-root/
├── src/
│   ├── main/
│   │   └── java/
│   │       └── pages/         # Page Objects
│   └── test/
│       ├── java/              # Step definitions, runners
│       └── resources/
│           └── features/      # ← .feature files here
│               ├── login.feature
│               ├── cart.feature
│               └── search.feature
└── pom.xml / build.gradle
```

## Runner Adapter (Future)

The runner adapter (`SeleniumBDDJavaAdapter`) is currently a skeleton. Future implementation will support:

- **Maven Execution**: `mvn test -Dcucumber.filter.tags="@smoke"`
- **Gradle Execution**: `gradle test --tests "*LoginFeature*"`
- **Report Parsing**: Parse Cucumber JSON/XML reports
- **Result Collection**: Return `TestResult` objects with pass/fail status

For now, use the **extractor** for test discovery only.

## Testing

```bash
# Run unit tests
pytest tests/unit/adapters/selenium_bdd_java/ -v

# Expected: 19 tests pass
```

## Limitations

- **Discovery Only**: Execution not yet implemented (use Maven/Gradle directly)
- **No Step Definitions**: Doesn't parse step definition files (Java)
- **No DataTable Parsing**: Doesn't extract Examples table data
- **No Page Object Mapping**: Step → Page Object mapping not yet implemented

## Related Documentation

- [Main README](../../../README.md) - CrossBridge AI overview
- [Selenium Java Adapter](../selenium_java/README.md) - Traditional JUnit/TestNG adapter
- [Common Models](../common/models.py) - Shared `TestMetadata` structure
- [CLI Documentation](../../../cli/README.md) - Command-line usage

## Architecture

```
adapters/selenium_bdd_java/
├── __init__.py          # Package exports
├── config.py            # SeleniumBDDJavaConfig
├── patterns.py          # Regex patterns for parsing
├── extractor.py         # 🔑 Feature file parser (main logic)
└── adapter.py           # Runner skeleton (future)
```

## Contributing

When adding features:
1. Update `patterns.py` with new regex patterns
2. Add extraction logic to `extractor.py`
3. Write unit tests in `tests/unit/adapters/selenium_bdd_java/`
4. Update this README

## FAQ

**Q: Can this execute Cucumber tests?**  
A: Not yet. Use Maven/Gradle for execution. This adapter focuses on discovery.

**Q: Does it support Scenario Outline?**  
A: Yes! Scenario Outlines are extracted as single test entries (one per outline, not per example row).

**Q: Can I map steps to Page Objects?**  
A: Not yet. Future enhancement will parse step definitions and link to Page Objects.

**Q: Does it work with Cucumber 7+?**  
A: Yes! This parser works with any Gherkin syntax version.

## License

MIT License - See [LICENSE](../../../LICENSE) for details.
