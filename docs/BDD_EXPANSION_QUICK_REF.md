# BDD Scenario Outline Expansion - Quick Reference

## 🚀 Quick Start

```python
from adapters.common.bdd import expand_scenario_outline, ScenarioOutline, ExamplesTable

# Define outline
outline = ScenarioOutline(
    name="User logs in",
    steps=("When user logs in with <username> and <password>",
           "Then login should be <result>"),
    tags=("auth",)
)

# Define examples
examples = ExamplesTable(
    headers=("username", "password", "result"),
    rows=(("admin", "admin123", "success"),
          ("user", "wrong123", "failure"))
)

# Expand
scenarios = expand_scenario_outline(outline, examples)

# Result: 2 ExpandedScenario objects
for scenario in scenarios:
    print(scenario.name)  # "User logs in [admin123/success/admin]"
    print(scenario.steps)  # Placeholders replaced
    print(scenario.parameters)  # {"username": "admin", ...}
```

## 📦 Core Functions

### expand_scenario_outline(outline, examples) → List[ExpandedScenario]
**Purpose:** Expand Scenario Outline into concrete test scenarios  
**Input:** ScenarioOutline + ExamplesTable  
**Output:** List of ExpandedScenario (one per example row)  
**Guarantees:** Deterministic, no mutations, validated placeholders

### map_expanded_scenario_to_intent(scenario) → IntentModel
**Purpose:** Convert ExpandedScenario to migration-ready IntentModel  
**Input:** ExpandedScenario  
**Output:** IntentModel with parsed steps and assertions  
**Use Case:** Migration pipeline, AI generation

## 🎯 Common Patterns

### Pattern 1: Adapter Discovery
```python
# In your adapter's extract_tests() method
outline = parse_scenario_outline(test_file)
examples = parse_examples_table(test_file)
expanded = expand_scenario_outline(outline, examples)

for scenario in expanded:
    yield TestMetadata(
        framework="your-framework",
        test_name=scenario.name,
        file_path=test_file,
        tags=list(scenario.tags)
    )
```

### Pattern 2: Migration Pipeline
```python
# Convert expanded scenarios to target framework
outline, examples = parse_source_file(source_file)
expanded = expand_scenario_outline(outline, examples)

for scenario in expanded:
    intent = map_expanded_scenario_to_intent(scenario)
    target_code = generate_pytest_test(intent)
    write_to_file(target_code)
```

### Pattern 3: Impact Analysis
```python
# Track which scenarios affected by code changes
expanded = expand_scenario_outline(outline, examples)

for scenario in expanded:
    if code_change_affects_test(scenario.original_outline_name):
        execute_test(scenario.name)
```

## 🔍 Data Models Cheat Sheet

```python
ScenarioOutline(
    name: str,                    # "User logs in"
    steps: tuple[str, ...],       # ("Given...", "When <param>", "Then...")
    tags: tuple[str, ...]         # ("smoke", "auth")
)

ExamplesTable(
    headers: tuple[str, ...],     # ("username", "password")
    rows: tuple[tuple, ...]       # (("admin", "admin123"), ...)
)

ExpandedScenario(
    name: str,                    # "User logs in [admin123/admin]"
    steps: tuple[str, ...],       # Placeholders replaced
    parameters: Dict[str, Any],   # {"username": "admin", ...}
    tags: tuple[str, ...],        # Inherited from outline
    original_outline_name: str    # "User logs in"
)

IntentModel(
    test_name: str,               # "User logs in [admin123/admin]"
    intent: str,                  # "User logs in"
    steps: List[TestStep],        # Parsed steps with action/target
    assertions: List[Assertion]   # Extracted from Then steps
)
```

## ⚡ Key Features

✅ **Deterministic:** Same input → same output, always  
✅ **Immutable:** No mutations, frozen dataclasses  
✅ **Validated:** Errors on missing placeholders  
✅ **Framework-agnostic:** Works with Robot, Cucumber, Behave, pytest-bdd  
✅ **Production-ready:** 33 tests, 100% pass rate

## ⚠️ Important Notes

### Parameter Ordering
Parameters sorted **alphabetically by key** for determinism:
```python
{"password": "admin123", "username": "admin"}
→ "[admin123/admin]"  # password < username alphabetically
```

### Case Sensitivity
Placeholders are **case-sensitive**:
```python
<Username> ≠ <username>  # Will raise ValueError
```

### Validation
Missing placeholders cause **immediate errors**:
```python
steps = ("login with <missing>",)
headers = ("username", "password")
# ValueError: placeholder '<missing>' not in examples
```

## 📊 Test Coverage

```bash
# Run all tests
pytest tests/unit/adapters/common/bdd/ -v

# Run with coverage
pytest tests/unit/adapters/common/bdd/ --cov=adapters.common.bdd

# Run demo
python examples/bdd_expansion_demo.py
```

## 🐛 Debugging Tips

### Tip 1: Check Parameter Names
If expansion fails, verify placeholder names match example headers exactly.

### Tip 2: Use Demo Script
Run `python examples/bdd_expansion_demo.py` to see expansion in action.

### Tip 3: Check Alphabetical Ordering
Test names use alphabetical key ordering, not definition order.

### Tip 4: Validate Before Expanding
```python
try:
    scenarios = expand_scenario_outline(outline, examples)
except ValueError as e:
    print(f"Validation error: {e}")
```

## 📚 More Resources

- Full docs: [adapters/common/bdd/README.md](../adapters/common/bdd/README.md)
- Implementation: [docs/BDD_EXPANSION_IMPLEMENTATION.md](BDD_EXPANSION_IMPLEMENTATION.md)
- Demo: [examples/bdd_expansion_demo.py](../examples/bdd_expansion_demo.py)
- Tests: [tests/unit/adapters/common/bdd/](../tests/unit/adapters/common/bdd/)

---

**Quick Help:**
- Import: `from adapters.common.bdd import *`
- Main function: `expand_scenario_outline(outline, examples)`
- For migration: `map_expanded_scenario_to_intent(scenario)`
- Tests: 33 passing ✅
