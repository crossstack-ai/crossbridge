# Cucumber JSON Parser - Quick Reference

## Installation

Already included in CrossBridge. No additional installation needed.

## Basic Usage

```python
from adapters.selenium_bdd_java import parse_cucumber_json

# Parse a single report
features = parse_cucumber_json("target/cucumber-report.json")

# Iterate through results
for feature in features:
    for scenario in feature.scenarios:
        print(f"{scenario.scenario}: {scenario.status}")
```

## Multiple Reports

```python
from adapters.selenium_bdd_java import parse_multiple_cucumber_reports

reports = ["module-a/target/cucumber.json", "module-b/target/cucumber.json"]
features = parse_multiple_cucumber_reports(reports)
```

## Domain Models

### FeatureResult
```python
feature.name              # "Login Feature"
feature.uri               # "features/login.feature"
feature.tags              # ["@smoke", "@regression"]
feature.scenarios         # List[ScenarioResult]
feature.total_scenarios   # 5
feature.passed_scenarios  # 4
feature.failed_scenarios  # 1
feature.overall_status    # "failed" | "passed" | "skipped" | "partial"
```

### ScenarioResult
```python
scenario.scenario         # "Valid login"
scenario.scenario_type    # "scenario" | "scenario_outline"
scenario.feature          # "Login Feature"
scenario.status           # "passed" | "failed" | "skipped"
scenario.uri              # "features/login.feature"
scenario.line             # 10
scenario.tags             # ["@smoke", "@critical"]
scenario.steps            # List[StepResult]
scenario.total_duration_ns # 300000000
scenario.failed_steps     # List[StepResult] - only failed steps
```

### StepResult
```python
step.name                 # "Given user is on login page"
step.status               # "passed" | "failed" | "skipped" | "pending" | "undefined"
step.duration_ns          # 100000000
step.error_message        # "AssertionError: ..." (if failed)
```

## Common Patterns

### Filter by Tag
```python
smoke_scenarios = [
    scenario for feature in features
    for scenario in feature.scenarios
    if "@smoke" in scenario.tags
]
```

### Find Failed Tests
```python
failed_tests = [
    (feature.name, scenario.scenario, scenario.uri, scenario.line)
    for feature in features
    for scenario in feature.scenarios
    if scenario.status == "failed"
]
```

### Calculate Statistics
```python
total = sum(f.total_scenarios for f in features)
passed = sum(f.passed_scenarios for f in features)
pass_rate = (passed / total * 100) if total > 0 else 0
```

### Get Test Duration
```python
# Total duration across all tests
total_duration_ns = sum(
    scenario.total_duration_ns
    for feature in features
    for scenario in feature.scenarios
)

# Convert to milliseconds
total_duration_ms = total_duration_ns / 1_000_000
```

## Error Handling

```python
from adapters.selenium_bdd_java import CucumberJsonParseError

try:
    features = parse_cucumber_json("report.json")
except FileNotFoundError:
    print("Report file not found")
except CucumberJsonParseError as e:
    print(f"Invalid Cucumber JSON: {e}")
```

## Generate Cucumber JSON

### Maven
```xml
<plugin>
    <groupId>io.cucumber</groupId>
    <artifactId>cucumber-maven-plugin</artifactId>
    <configuration>
        <jsonOutputDirectory>target</jsonOutputDirectory>
    </configuration>
</plugin>
```

Or:
```bash
mvn test -Dcucumber.plugin=json:target/cucumber-report.json
```

### Gradle
```groovy
test {
    systemProperty "cucumber.plugin", "json:build/cucumber-report.json"
}
```

## Status Computation Rules

| Step Statuses | Scenario Status |
|--------------|----------------|
| All passed | `passed` |
| Any failed | `failed` |
| No failures, some skipped/pending/undefined | `skipped` |

## Examples

Full examples available in:
- `examples/cucumber_json_parser_demo.py`
- `examples/crossbridge_cucumber_integration.py`
- `examples/verify_cucumber_parser.py`

## Documentation

- User Guide: `adapters/selenium_bdd_java/CUCUMBER_JSON_PARSER.md`
- Complete Overview: `CUCUMBER_JSON_PARSER_COMPLETE.md`

## Tests

Run unit tests:
```bash
pytest tests/unit/adapters/test_cucumber_json_parser.py -v
```

Run verification:
```bash
python examples/verify_cucumber_parser.py
```
