# BDD Scenario Outline Expansion

Framework-agnostic expansion of BDD Scenario Outlines into concrete test cases with parameter substitution.

## Overview

This module provides deterministic expansion of Scenario Outlines with Examples tables into individual test scenarios. It supports all major BDD frameworks (Robot Framework, Cucumber, Behave) by keeping the logic framework-agnostic and reusable.

## Why This Matters

**Without expansion, all downstream intelligence is wrong:**
- ❌ Impact analysis treats outline as single test
- ❌ Migration produces one test instead of N
- ❌ AI generation loses parameter context
- ❌ Coverage tracking is inaccurate
- ❌ Reporting shows wrong pass/fail counts

**With expansion, every use case works:**
- ✅ Each example row becomes a separate test
- ✅ Parameters become structured input for AI
- ✅ Coverage tracked per data combination
- ✅ Accurate impact analysis per scenario
- ✅ Correct pass/fail reporting

## Architecture

```
adapters/common/bdd/
├── models.py           # Data models (ScenarioOutline, ExamplesTable, ExpandedScenario)
├── expander.py         # Core expansion algorithm
├── intent_mapper.py    # Convert ExpandedScenario → IntentModel
└── __init__.py         # Public API exports

tests/unit/adapters/common/bdd/
├── test_expander.py        # 16 tests for expansion logic
├── test_intent_mapper.py   # 17 tests for intent mapping
└── __init__.py
```

## Data Models

### ScenarioOutline
```python
@dataclass(frozen=True)
class ScenarioOutline:
    name: str                     # "User logs in"
    steps: tuple[str, ...]        # ("Given...", "When...", "Then...")
    tags: tuple[str, ...] = ()    # ("smoke", "auth")
```

### ExamplesTable
```python
@dataclass(frozen=True)
class ExamplesTable:
    headers: tuple[str, ...]           # ("username", "password", "result")
    rows: tuple[tuple[Any, ...], ...]  # (("admin", "admin123", "success"), ...)
```

### ExpandedScenario
```python
@dataclass(frozen=True)
class ExpandedScenario:
    name: str                        # "User logs in [admin123/admin]"
    steps: tuple[str, ...]           # Placeholders replaced
    parameters: Dict[str, Any]       # {"username": "admin", "password": "admin123"}
    tags: tuple[str, ...] = ()       # Inherited from outline
    original_outline_name: str = ""  # "User logs in"
```

## Core Algorithm

### expand_scenario_outline()

**Input:**
```python
outline = ScenarioOutline(
    name="User logs in",
    steps=("Given user is on login page",
           "When user logs in with <username> and <password>",
           "Then login should be <result>"),
    tags=("auth",)
)

examples = ExamplesTable(
    headers=("username", "password", "result"),
    rows=(("admin", "admin123", "success"),
          ("user", "wrong123", "failure"))
)
```

**Execution:**
```python
from adapters.common.bdd import expand_scenario_outline

scenarios = expand_scenario_outline(outline, examples)
```

**Output:**
```python
[
    ExpandedScenario(
        name="User logs in [admin123/admin]",
        steps=(
            "Given user is on login page",
            "When user logs in with admin and admin123",
            "Then login should be success"
        ),
        parameters={"username": "admin", "password": "admin123", "result": "success"},
        tags=("auth",),
        original_outline_name="User logs in"
    ),
    ExpandedScenario(
        name="User logs in [user/wrong123]",
        steps=(
            "Given user is on login page",
            "When user logs in with user and wrong123",
            "Then login should be failure"
        ),
        parameters={"username": "user", "password": "wrong123", "result": "failure"},
        tags=("auth",),
        original_outline_name="User logs in"
    )
]
```

**Guarantees:**
- ✅ Deterministic output (same input → same output)
- ✅ No mutation of input objects
- ✅ Output order matches example row order
- ✅ All placeholders replaced correctly
- ✅ Validation: errors if placeholder missing from examples

## Intent Mapping

### map_expanded_scenario_to_intent()

Converts expanded scenarios to framework-agnostic IntentModel for migration/AI processing.

**Input:**
```python
scenario = ExpandedScenario(
    name="User logs in [admin/admin123]",
    steps=(
        "Given user is on login page",
        "When user logs in with admin and admin123",
        "Then login should be success"
    ),
    parameters={"username": "admin", "password": "admin123", "result": "success"},
    tags=("auth",),
    original_outline_name="User logs in"
)
```

**Execution:**
```python
from adapters.common.bdd import map_expanded_scenario_to_intent

intent = map_expanded_scenario_to_intent(scenario)
```

**Output:**
```python
IntentModel(
    test_name="User logs in [admin/admin123]",
    intent="User logs in",
    steps=[
        TestStep(description="Given user is on login page", action="Given", target="login page"),
        TestStep(description="When user logs in with admin and admin123", action="When", target=None),
        TestStep(description="Then login should be success", action="Then", target=None)
    ],
    assertions=[
        Assertion(type=AssertionType.EXISTS, expected="Then login should be success")
    ]
)
```

## Usage in Adapters

### Robot Framework Adapter
```python
from adapters.common.bdd import expand_scenario_outline, ScenarioOutline, ExamplesTable

# Parse Robot file
outline = parse_robot_scenario_outline(robot_file)
examples = parse_robot_examples_table(robot_file)

# Expand
expanded = expand_scenario_outline(outline, examples)

# Emit as individual tests
for scenario in expanded:
    test_metadata = TestMetadata(
        framework="robot",
        test_name=scenario.name,
        file_path=robot_file,
        tags=list(scenario.tags),
        test_type="ui"
    )
    yield test_metadata
```

### Cucumber/Behave Adapter
```python
# Parse feature file
outline = parse_feature_scenario_outline(feature_file)
examples = parse_examples_table(feature_file)

# Expand
expanded = expand_scenario_outline(outline, examples)

# Convert to IntentModel for migration
intents = [map_expanded_scenario_to_intent(s) for s in expanded]
```

## Testing

### Run All BDD Tests
```bash
pytest tests/unit/adapters/common/bdd/ -v
```

**Coverage:**
- ✅ 16 expander tests (basic expansion, placeholders, determinism, edge cases)
- ✅ 17 intent mapper tests (step parsing, assertion extraction, complex scenarios)
- ✅ 33 total tests, all passing

### Test Categories

**Expansion Tests:**
- Basic expansion (outline + examples → scenarios)
- Placeholder replacement (`<username>` → `admin`)
- Parameter suffix formatting (`[admin123/admin]`)
- Placeholder safety (error on missing params)
- Determinism (no mutations, order preserved)
- Edge cases (empty examples, numeric values)

**Intent Mapping Tests:**
- Test name and intent extraction
- BDD step parsing (Given/When/Then/And/But)
- Target extraction from step descriptions
- Assertion extraction from Then steps
- Complex multi-step scenarios

## Key Design Decisions

### 1. Immutable Data Models
All models use `frozen=True` and tuples to prevent accidental mutations.

### 2. Alphabetical Parameter Ordering
Parameter suffixes use alphabetical key ordering for determinism:
```python
{"password": "admin123", "username": "admin"} → "[admin123/admin]"
#   ^^ password < username alphabetically
```

### 3. Framework-Agnostic
No dependencies on specific BDD frameworks. Works with:
- Cucumber (Gherkin)
- Robot Framework
- Behave
- pytest-bdd
- Any BDD syntax with scenario outlines

### 4. Validation Over Silent Failures
Raises `ValueError` if step contains placeholder not in examples headers.

### 5. Placeholder Case-Sensitivity
`<Username>` ≠ `<username>` - exact match required.

## Integration Points

### Persistence Layer
```python
# Expanded scenarios → database
for scenario in expanded:
    test_case = TestCase(
        framework="cucumber",
        method_name=scenario.name,
        file_path=feature_file,
        tags=list(scenario.tags)
    )
    db_repo.insert_test_case(test_case)
```

### Impact Analysis
```python
# Each expanded scenario is separate test for impact tracking
for scenario in expanded:
    if should_run_based_on_changes(scenario.original_outline_name):
        execute_test(scenario.name)
```

### Migration Pipeline
```python
# Scenario Outline → N target tests
for scenario in expanded:
    intent = map_expanded_scenario_to_intent(scenario)
    target_code = generate_pytest_test(intent)
    write_test_file(target_code)
```

### AI Generation
```python
# Parameters as structured input for AI
for scenario in expanded:
    prompt = f"""
    Generate test code for: {scenario.name}
    Intent: {scenario.original_outline_name}
    Parameters: {scenario.parameters}
    Steps: {scenario.steps}
    """
    ai_generated_code = llm.generate(prompt)
```

## Limitations

1. **Scenario Outline only**: Does not handle plain Scenarios (no expansion needed)
2. **Single Examples table per outline**: Multiple tables not supported yet
3. **No step definition resolution**: Only expands, doesn't link to step implementations
4. **Basic target extraction**: Heuristic-based, not semantic analysis
5. **Assertion inference limited**: Only "Then" steps, basic placeholder

## Future Enhancements

- [ ] Support multiple Examples tables per outline
- [ ] Advanced target extraction (semantic analysis)
- [ ] Step definition → Page Object mapping
- [ ] Custom parameter formatters
- [ ] Examples table filtering by tags
- [ ] Scenario Outline validation (structural checks)

## Contributing

When modifying expansion logic:
1. ✅ Keep it deterministic (no random, no datetime)
2. ✅ Maintain immutability (frozen dataclasses)
3. ✅ Add comprehensive tests (expander + mapper)
4. ✅ Update this README with examples
5. ✅ Verify all 33 tests pass

## License

Part of CrossBridge AI - internal test migration framework.
