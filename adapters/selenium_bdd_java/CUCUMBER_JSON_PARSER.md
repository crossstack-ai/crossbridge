# Cucumber JSON Parser

Framework-neutral parser for Cucumber JSON reports, designed for the CrossBridge platform.

## Overview

The Cucumber JSON Parser extracts test execution data from Cucumber JSON reports (compatible with Cucumber JVM, Cucumber JS, and other implementations) and converts them into framework-neutral domain models suitable for persistence and impact analysis.

## Features

- **Framework-neutral**: Works with any Cucumber implementation that produces standard JSON reports
- **Deterministic**: Same input always produces the same output
- **Execution-independent**: Parses existing reports without requiring test execution
- **DB-ready**: Produces clean domain objects ready for database persistence
- **Robust error handling**: Gracefully handles malformed reports and missing data
- **Comprehensive metadata**: Extracts features, scenarios, steps, tags, statuses, durations, and error messages

## Quick Start

### Basic Usage

```python
from adapters.selenium_bdd_java import parse_cucumber_json

# Parse a Cucumber JSON report
features = parse_cucumber_json("target/cucumber-report.json")

# Access parsed data
for feature in features:
    print(f"Feature: {feature.name}")
    print(f"Status: {feature.overall_status}")
    
    for scenario in feature.scenarios:
        print(f"  Scenario: {scenario.scenario}")
        print(f"  Status: {scenario.status}")
        print(f"  Duration: {scenario.total_duration_ns / 1_000_000}ms")
```

### Multiple Reports

```python
from adapters.selenium_bdd_java import parse_multiple_cucumber_reports

# Parse multiple reports (useful for multi-module projects)
report_paths = [
    "module-a/target/cucumber.json",
    "module-b/target/cucumber.json",
]

all_features = parse_multiple_cucumber_reports(report_paths)
```

## Domain Models

The parser converts Cucumber JSON into three main domain models:

### FeatureResult

Represents a feature file's execution results.

```python
@dataclass
class FeatureResult:
    name: str                           # Feature name
    uri: str                            # Feature file path
    scenarios: List[ScenarioResult]     # List of scenarios
    description: Optional[str]          # Feature description
    tags: List[str]                     # Feature-level tags
    
    # Properties
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    skipped_scenarios: int
    overall_status: str                 # passed | failed | skipped | partial
```

### ScenarioResult

Represents a scenario's execution results.

```python
@dataclass
class ScenarioResult:
    feature: str                        # Parent feature name
    scenario: str                       # Scenario name
    scenario_type: str                  # scenario | scenario_outline
    tags: List[str]                     # Combined feature + scenario tags
    steps: List[StepResult]             # List of steps
    status: str                         # passed | failed | skipped
    uri: str                            # Feature file path
    line: int                           # Line number in feature file
    
    # Properties
    total_duration_ns: int
    failed_steps: List[StepResult]
```

### StepResult

Represents a step's execution results.

```python
@dataclass
class StepResult:
    name: str                           # Step name (includes keyword)
    status: str                         # passed | failed | skipped | pending | undefined
    duration_ns: int                    # Duration in nanoseconds
    error_message: Optional[str]        # Error message if failed
```

## Status Computation

Scenario status is computed from step statuses using the following rules:

| Condition | Scenario Status |
|-----------|----------------|
| Any step failed | `failed` |
| No failures, some skipped/pending/undefined | `skipped` |
| All steps passed | `passed` |

This logic matches Cucumber's standard semantics.

## Input Format

The parser expects standard Cucumber JSON format:

```json
[
  {
    "uri": "features/login.feature",
    "name": "Login Feature",
    "tags": [{"name": "@smoke"}],
    "elements": [
      {
        "type": "scenario",
        "name": "Valid login",
        "line": 10,
        "tags": [{"name": "@critical"}],
        "steps": [
          {
            "keyword": "Given ",
            "name": "user is on login page",
            "result": {
              "status": "passed",
              "duration": 100000000
            }
          }
        ]
      }
    ]
  }
]
```

## Generating Cucumber JSON Reports

### Maven (Java)

Add to `pom.xml`:

```xml
<plugin>
    <groupId>io.cucumber</groupId>
    <artifactId>cucumber-maven-plugin</artifactId>
    <configuration>
        <jsonOutputDirectory>target</jsonOutputDirectory>
    </configuration>
</plugin>
```

Or run tests with:
```bash
mvn test -Dcucumber.plugin=json:target/cucumber-report.json
```

### Gradle (Java)

In `build.gradle`:

```groovy
test {
    systemProperty "cucumber.plugin", "json:build/cucumber-report.json"
}
```

### Cucumber JS

```javascript
// cucumber.js
module.exports = {
  default: '--format json:cucumber-report.json'
}
```

## Error Handling

The parser provides robust error handling:

```python
from adapters.selenium_bdd_java import CucumberJsonParseError

try:
    features = parse_cucumber_json("report.json")
except FileNotFoundError:
    print("Report file not found")
except CucumberJsonParseError as e:
    print(f"Invalid Cucumber JSON: {e}")
```

## Integration with CrossBridge

The parser fits into the CrossBridge platform workflow:

```
┌─────────────────────┐
│ Execute Tests       │
│ (Maven/Gradle)      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Generate            │
│ cucumber.json       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Parse Report        │  ← THIS PARSER
│ (cucumber_json_     │
│  parser.py)         │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Normalize Results   │
│ (FeatureResult,     │
│  ScenarioResult)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Persist to DB       │
│ (Next Phase)        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Impact Analysis &   │
│ Test Selection      │
└─────────────────────┘
```

## Examples

See [`examples/cucumber_json_parser_demo.py`](../../examples/cucumber_json_parser_demo.py) for comprehensive usage examples.

## Testing

Run the test suite:

```bash
pytest tests/unit/adapters/test_cucumber_json_parser.py -v
```

## API Reference

### Functions

#### `parse_cucumber_json(report_path: str | Path) -> List[FeatureResult]`

Parse a single Cucumber JSON report.

**Parameters:**
- `report_path`: Path to cucumber-report.json file

**Returns:**
- List of FeatureResult objects

**Raises:**
- `FileNotFoundError`: If report file doesn't exist
- `CucumberJsonParseError`: If JSON is invalid or malformed

#### `parse_multiple_cucumber_reports(report_paths: List[str | Path]) -> List[FeatureResult]`

Parse multiple Cucumber JSON reports and combine results.

**Parameters:**
- `report_paths`: List of paths to report files

**Returns:**
- Combined list of FeatureResult objects

**Note:** Missing or invalid files are logged but don't raise exceptions.

## Best Practices

1. **Generate JSON reports during test execution**: Configure your build tool to always generate Cucumber JSON
2. **Parse reports after test completion**: Parse once per test run, not per feature
3. **Handle missing reports gracefully**: Use `parse_multiple_cucumber_reports` when dealing with optional modules
4. **Leverage domain models**: Use the rich properties (e.g., `failed_steps`, `total_duration_ns`) for analysis
5. **Preserve raw reports**: Keep original JSON files for debugging and re-parsing

## Troubleshooting

### Report not generated

Ensure Cucumber JSON plugin is configured in your build tool. Check the output directory.

### Invalid JSON error

Verify the report file is complete. Incomplete reports can occur if tests are interrupted.

### Missing data

The parser uses sensible defaults for missing optional fields. Check the warnings in the output.

## Limitations

- **Background steps**: Currently, background steps merged by Cucumber into scenarios are included in scenario step counts
- **Embedded data**: Embedded screenshots/attachments in steps are not parsed (may be added in future)
- **Hooks**: Before/After hooks are not separately tracked (they appear as steps in Cucumber JSON)

## Future Enhancements

- [ ] Support for embedded screenshots and attachments
- [ ] Hook detection and separate tracking
- [ ] Performance optimization for very large reports
- [ ] Streaming parser for memory efficiency
- [ ] Integration with real-time test execution monitoring

## License

Part of CrossBridge platform. See main project LICENSE.
