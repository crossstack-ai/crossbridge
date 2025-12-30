# Step-to-Code-Path Mapping System

**Signal-driven, deterministic step-to-code-path mapping for impact analysis, migration parity validation, and test intelligence.**

## 🎯 Overview

This module provides a **framework-agnostic, signal-driven** system for mapping BDD test steps to their underlying code implementation (Page Objects, methods, code paths). Unlike heuristic or AI-based approaches, this system relies on **explicit signal registration** by test adapters during discovery.

### Why Signal-Driven?

**Avoids:**
- ❌ NLP guessing (brittle, inaccurate)
- ❌ LLM hallucinations (unreliable)
- ❌ Regex hacks (maintenance nightmare)

**Enables:**
- ✅ Impact-based test selection (code change → find affected tests)
- ✅ Migration parity validation (source step → target code path)
- ✅ Coverage persistence (test execution → code paths covered)
- ✅ AI-assisted translation (step + code path → structured prompt)
- ✅ "What broke?" diagnostics (test failure → which code path failed)

---

## 📦 Architecture

```
adapters/common/mapping/
├── models.py         # StepSignal, CodeReference, StepMapping
├── registry.py       # StepSignalRegistry (signal storage & matching)
├── resolver.py       # StepMappingResolver (signal → mapping resolution)
└── README.md         # This file
```

### Core Components

1. **StepSignal**: A signal registered by an adapter
   - `type`: PAGE_OBJECT, METHOD, CODE_PATH, DECORATOR, ANNOTATION
   - `value`: The actual page object name, method name, or code path
   - `metadata`: Optional context (file path, line number, parameters, etc.)

2. **CodeReference**: A parsed code location
   - `file_path`: Relative file path
   - `class_name`: Class containing the method
   - `method_name`: Method implementing the step
   - `line_number`: Optional line number
   - `full_path`: Computed property (e.g., `"pages/login_page.py::LoginPage.login"`)

3. **StepMapping**: Resolution result for a step
   - `step`: The BDD step text
   - `page_objects`: List of page object names
   - `methods`: List of method names
   - `code_paths`: List of full code paths
   - `signals`: List of matched signals

4. **StepSignalRegistry**: Signal storage with deterministic matching
   - Exact match (O(1) dict lookup)
   - Contains match (substring, preserves registration order)
   - BDD keyword removal (Given/When/Then/And/But)

5. **StepMappingResolver**: Resolves steps using the registry
   - Gets signals for a step
   - Processes each signal based on type
   - Returns StepMapping with deduplicated results

---

## 🚀 Quick Start

### 1. Register Signals (Adapter's Job)

Adapters register signals during test discovery:

```python
from adapters.common.mapping import StepSignalRegistry, StepSignal, SignalType

registry = StepSignalRegistry()

# Register Page Object signal
registry.register_signal(
    "user logs in with {username} and {password}",
    StepSignal(
        type=SignalType.PAGE_OBJECT,
        value="LoginPage",
        metadata={"file": "pages/login_page.py"}
    )
)

# Register Method signal
registry.register_signal(
    "user logs in",
    StepSignal(
        type=SignalType.METHOD,
        value="LoginPage.login",
        metadata={"parameters": ["username", "password"]}
    )
)

# Register Code Path signal (most specific)
registry.register_signal(
    "user logs in",
    StepSignal(
        type=SignalType.CODE_PATH,
        value="pages/login_page.py::LoginPage.login",
        metadata={"line": 42}
    )
)
```

### 2. Resolve Steps (Migration Engine's Job)

Migration engine resolves steps to code paths:

```python
from adapters.common.mapping import StepMappingResolver

resolver = StepMappingResolver(registry)

# Resolve a single step
mapping = resolver.resolve_step("Given user logs in with admin and password123")

print(f"Step: {mapping.step}")
print(f"Page Objects: {mapping.page_objects}")  # ["LoginPage"]
print(f"Methods: {mapping.methods}")            # ["login"]
print(f"Code Paths: {mapping.code_paths}")      # ["pages/login_page.py::LoginPage.login"]
```

### 3. Batch Resolution

```python
steps = [
    "Given user logs in",
    "When user navigates to dashboard",
    "Then orders should be visible"
]

mappings = resolver.resolve_steps(steps)

for mapping in mappings:
    print(f"{mapping.step} → {mapping.code_paths}")
```

---

## 📚 Core Concepts

### Signal Types

```python
class SignalType(Enum):
    PAGE_OBJECT = "page_object"    # Page Object class name
    METHOD = "method"               # Method name (may include class)
    CODE_PATH = "code_path"         # Full path: "file::Class.method"
    DECORATOR = "decorator"         # Decorator/annotation
    ANNOTATION = "annotation"       # Framework annotation
```

**When to use:**
- `PAGE_OBJECT`: Step uses a specific Page Object (e.g., "LoginPage")
- `METHOD`: Step calls a specific method (e.g., "LoginPage.login")
- `CODE_PATH`: Most specific - full file::Class.method path
- `DECORATOR`: Step has a decorator (e.g., `@given("user logs in")` in pytest-bdd)
- `ANNOTATION`: Framework annotation (e.g., JUnit `@Test`, TestNG `@Test(priority=1)`)

### Matching Strategy

**Deterministic, two-phase matching:**

1. **Exact Match** (priority, O(1))
   - Step text normalized (lowercase, BDD keywords removed)
   - Direct dict lookup: `exact_matches[normalized_step]`
   - Example: `"user logs in"` matches pattern `"user logs in"`

2. **Contains Match** (fallback, O(n))
   - Pattern substring of normalized step
   - Preserves registration order (first registered wins)
   - Example: `"user clicks submit button"` matches pattern `"clicks"` and `"button"`

### BDD Keyword Removal

Keywords removed during normalization:
- `Given` / `When` / `Then` / `And` / `But`

**Effect:**
```python
# All these steps match the same pattern:
"user logs in"
"Given user logs in"
"When user logs in"
"Then user logs in"
"And user logs in"
"But user logs in"
```

### Code Path Format

Full code paths use the format: `"file::Class.method"`

**Examples:**
```python
"pages/login_page.py::LoginPage.login"
"api/auth_api.py::AuthAPI.authenticate"
"utils/helpers.py::DateHelper.format_date"
```

**Parsing:**
```python
from adapters.common.mapping import CodeReference

# Parse code path
ref = CodeReference(
    file_path="pages/login_page.py",
    class_name="LoginPage",
    method_name="login",
    line_number=42
)

assert ref.full_path == "pages/login_page.py::LoginPage.login"
```

---

## 🔧 Usage Examples

### Example 1: Basic Registration & Resolution

```python
from adapters.common.mapping import (
    StepSignalRegistry,
    StepMappingResolver,
    StepSignal,
    SignalType
)

# Setup
registry = StepSignalRegistry()
registry.register_signal(
    "user clicks {button}",
    StepSignal(
        type=SignalType.CODE_PATH,
        value="pages/base_page.py::BasePage.click_button",
        metadata={"line": 28}
    )
)

# Resolve
resolver = StepMappingResolver(registry)
mapping = resolver.resolve_step("When user clicks submit")

assert mapping.step == "When user clicks submit"
assert mapping.code_paths == ["pages/base_page.py::BasePage.click_button"]
```

### Example 2: Multi-Signal Resolution (UI + API)

```python
# Complex step with multiple signals
registry.register_signal(
    "user creates order",
    StepSignal(type=SignalType.PAGE_OBJECT, value="OrderPage", metadata={})
)
registry.register_signal(
    "user creates order",
    StepSignal(type=SignalType.PAGE_OBJECT, value="OrderAPI", metadata={})
)
registry.register_signal(
    "user creates order",
    StepSignal(
        type=SignalType.CODE_PATH,
        value="pages/order_page.py::OrderPage.createOrder",
        metadata={"line": 87}
    )
)
registry.register_signal(
    "user creates order",
    StepSignal(
        type=SignalType.CODE_PATH,
        value="api/order_api.py::OrderAPI.post_order",
        metadata={"line": 120}
    )
)

# Resolve
mapping = resolver.resolve_step("When user creates order for laptop")

assert len(mapping.page_objects) == 2  # ["OrderPage", "OrderAPI"]
assert len(mapping.code_paths) == 2    # UI + API paths
```

### Example 3: Integration with BDD Expansion

```python
from adapters.common.bdd import ScenarioOutline, ExamplesTable, expand_scenario_outline
from adapters.common.bdd import map_expanded_scenario_to_intent

# 1. Expand scenario outline
outline = ScenarioOutline(
    name="Login Test",
    steps=["Given user logs in with <username> and <password>"],
    tags=[]
)
examples = ExamplesTable(
    headers=["username", "password"],
    rows=[["admin", "admin123"], ["user1", "pass456"]]
)
expanded_scenarios = expand_scenario_outline(outline, examples)

# 2. Map to intents
intents = [map_expanded_scenario_to_intent(s) for s in expanded_scenarios]

# 3. Resolve code paths for each intent
for intent in intents:
    all_code_paths = []
    for step in intent.steps:
        mapping = resolver.resolve_step(step.action)
        all_code_paths.extend(mapping.code_paths)
    
    # Populate IntentModel.code_paths (deduplicated)
    intent.code_paths = list(dict.fromkeys(all_code_paths))
```

### Example 4: Impact Analysis

**Use Case:** Code change → find affected tests

```python
# Test suite with code path mappings (persisted from previous runs)
test_suite = {
    "LoginTest": ["pages/login_page.py::LoginPage.login", "pages/base_page.py::BasePage.wait"],
    "DashboardTest": ["pages/dashboard_page.py::DashboardPage.load", "pages/base_page.py::BasePage.wait"],
    "ProfileTest": ["pages/profile_page.py::ProfilePage.edit", "pages/base_page.py::BasePage.save"],
}

# Developer changes BasePage.wait
changed_code_path = "pages/base_page.py::BasePage.wait"

# Find affected tests
affected_tests = [
    test_name
    for test_name, code_paths in test_suite.items()
    if changed_code_path in code_paths
]

print(f"Affected tests: {affected_tests}")
# Output: ["LoginTest", "DashboardTest"]
```

### Example 5: Serialization (Persistence)

```python
# Resolve and serialize
mapping = resolver.resolve_step("When user clicks submit")
mapping_dict = mapping.to_dict()

# Save to database/file (JSON)
import json
json_str = json.dumps(mapping_dict, indent=2)

# Restore from database/file
from adapters.common.mapping import StepMapping
restored_mapping = StepMapping.from_dict(json.loads(json_str))

assert restored_mapping.step == mapping.step
assert restored_mapping.code_paths == mapping.code_paths
```

---

## 🧪 Testing

### Run All Mapping Tests

```bash
# All mapping tests
python -m pytest tests/unit/adapters/common/mapping/ -v

# Registry tests only
python -m pytest tests/unit/adapters/common/mapping/test_registry.py -v

# Resolver tests only
python -m pytest tests/unit/adapters/common/mapping/test_resolver.py -v
```

### Test Coverage

**Registry Tests (24):**
- Signal registration (single, multiple, count)
- Deterministic matching (exact, contains, case-insensitive, whitespace)
- BDD keyword removal (Given/When/Then/And/But)
- Order preservation (registration, contains matches)
- Deduplication (duplicates removed, different signals kept)
- Registry management (clear, get_all_patterns)
- Edge cases (empty text/pattern, special chars, long text)

**Resolver Tests (22):**
- Basic mapping (CODE_PATH, PAGE_OBJECT, METHOD signals)
- Determinism (empty mapping, order, no mutations, no duplicates)
- Multi-step mapping (multiple page objects, UI+API, multiple methods)
- Batch resolution (resolve_steps, order preservation)
- Code path parsing (full/class-only/method-only/file-only paths)
- Signal extraction (dotted names, code paths)

**Total: 46 tests, 100% passing**

---

## 🎓 Advanced Topics

### Custom Signal Metadata

Metadata can store any JSON-serializable data:

```python
registry.register_signal(
    "user submits form",
    StepSignal(
        type=SignalType.CODE_PATH,
        value="pages/form_page.py::FormPage.submit",
        metadata={
            "line": 145,
            "parameters": ["data", "validate"],
            "returns": "bool",
            "async": True,
            "tags": ["ui", "critical"]
        }
    )
)
```

### Adapter Integration Pattern

**Discovery Phase:**
```python
class SeleniumBDDAdapter(BaseTestExtractor):
    def discover_tests(self, root_dir: str):
        registry = StepSignalRegistry()
        
        # Parse step definitions
        for step_def in self._find_step_definitions(root_dir):
            # Extract pattern and implementation
            pattern = step_def.pattern
            code_path = step_def.code_path
            
            # Register signal
            registry.register_signal(
                pattern,
                StepSignal(
                    type=SignalType.CODE_PATH,
                    value=code_path,
                    metadata={
                        "file": step_def.file,
                        "line": step_def.line_number,
                        "framework": "selenium-bdd-java"
                    }
                )
            )
        
        return registry
```

**Resolution Phase:**
```python
class MigrationEngine:
    def migrate_test(self, source_test):
        # Resolve code paths for source test steps
        resolver = StepMappingResolver(self.source_registry)
        
        for step in source_test.steps:
            mapping = resolver.resolve_step(step)
            
            # Use mapping.code_paths for validation
            # Use mapping.page_objects for AI context
            # Use mapping.methods for translation hints
```

### IntentModel Integration

```python
from adapters.common.models import IntentModel, TestStep

# Create intent with code paths
intent = IntentModel(
    test_name="LoginTest [admin/admin123]",
    intent="Verify user can log in with valid credentials",
    steps=[
        TestStep(action="user logs in", target="LoginPage"),
        TestStep(action="dashboard loads", target="DashboardPage")
    ],
    code_paths=[
        "pages/login_page.py::LoginPage.login",
        "pages/dashboard_page.py::DashboardPage.wait_for_load"
    ]
)

# Impact analysis: Find tests affected by code change
changed_path = "pages/login_page.py::LoginPage.login"
if changed_path in intent.code_paths:
    print(f"Test {intent.test_name} affected by change to {changed_path}")
```

---

## 🔍 Troubleshooting

### No Signals Matched

**Problem:** `resolver.resolve_step(...)` returns empty mapping

**Causes:**
1. Signal pattern doesn't match step text
2. BDD keyword not removed in pattern
3. Case mismatch (both are lowercased, so check for typos)

**Solution:**
```python
# Debug: Check registered patterns
patterns = registry.get_all_patterns()
print(f"Registered patterns: {patterns}")

# Debug: Check signals for a step
signals = registry.get_signals_for_step("user logs in")
print(f"Matched signals: {signals}")
```

### Duplicate Code Paths

**Problem:** `mapping.code_paths` has duplicates

**Cause:** Multiple signals with same CODE_PATH value

**Solution:** StepMapping automatically deduplicates - check signal registration:
```python
# StepMapping.add_code_path() checks existence before adding
mapping.add_code_path("pages/login_page.py::LoginPage.login")  # OK
mapping.add_code_path("pages/login_page.py::LoginPage.login")  # Ignored (duplicate)
```

### Wrong Extraction from Code Path

**Problem:** `_extract_page_object_name()` returns file path instead of class name

**Cause:** Code path parsing order (must check `::` before `.`)

**Solution:** Already fixed in resolver.py:
```python
def _extract_page_object_name(self, value: str) -> str:
    # Check :: BEFORE . (code paths have dots in file names)
    if "::" in value:
        parts = value.split("::")
        if len(parts) >= 2:
            class_method = parts[1]
            if "." in class_method:
                return class_method.split(".")[0]
            return class_method
    # ... rest of method
```

---

## 📖 API Reference

### StepSignal

```python
@dataclass(frozen=True)
class StepSignal:
    type: SignalType          # PAGE_OBJECT, METHOD, CODE_PATH, DECORATOR, ANNOTATION
    value: str                # Page object name, method name, or code path
    metadata: dict            # Optional context (JSON-serializable)
```

### CodeReference

```python
@dataclass(frozen=True)
class CodeReference:
    file_path: str            # Relative file path
    class_name: str           # Class containing the method
    method_name: str          # Method implementing the step
    line_number: int | None   # Optional line number
    
    @property
    def full_path(self) -> str:
        """Returns 'file::Class.method' format"""
```

### StepMapping

```python
@dataclass
class StepMapping:
    step: str                      # BDD step text
    page_objects: List[str]        # Page object names
    methods: List[str]             # Method names
    code_paths: List[str]          # Full code paths
    signals: List[StepSignal]      # Matched signals
    
    def to_dict(self) -> dict:
        """Serialize to dict (JSON-compatible)"""
    
    @staticmethod
    def from_dict(data: dict) -> "StepMapping":
        """Deserialize from dict"""
    
    def add_code_path(self, code_path: str) -> None:
        """Add code path (deduplicated)"""
    
    def add_page_object(self, page_object: str) -> None:
        """Add page object (deduplicated)"""
    
    def add_method(self, method: str) -> None:
        """Add method (deduplicated)"""
```

### StepSignalRegistry

```python
class StepSignalRegistry:
    def register_signal(self, step_pattern: str, signal: StepSignal) -> None:
        """Register a signal for a step pattern"""
    
    def get_signals_for_step(self, step_text: str) -> List[StepSignal]:
        """Get all signals matching a step (exact first, then contains)"""
    
    def clear(self) -> None:
        """Clear all registered signals"""
    
    def count(self) -> int:
        """Return total number of registered signal patterns"""
    
    def get_all_patterns(self) -> List[str]:
        """Return all registered step patterns"""
```

### StepMappingResolver

```python
class StepMappingResolver:
    def __init__(self, registry: StepSignalRegistry):
        """Initialize resolver with a signal registry"""
    
    def resolve_step(self, step_text: str) -> StepMapping:
        """Resolve a single step to its code mapping"""
    
    def resolve_steps(self, step_texts: List[str]) -> List[StepMapping]:
        """Resolve multiple steps to their code mappings"""
```

---

## 🎯 Design Principles

1. **Explicit Over Implicit**: No heuristics, no guessing - only registered signals
2. **Deterministic**: Same input → same output, always
3. **Framework-Agnostic**: Works with Robot, Cucumber, Behave, pytest-bdd, Selenium
4. **Immutable Data**: Frozen dataclasses prevent mutations
5. **Separation of Concerns**: Adapters register, resolver processes
6. **Performance**: O(1) exact match, O(n) contains match
7. **Testable**: Pure logic, no side effects, easy to test

---

## 🚀 Next Steps

1. **Integrate into Adapters**: Register signals during test discovery
2. **Populate IntentModel.code_paths**: Use resolver in intent mapper
3. **Enable Impact Analysis**: Build test → code path index
4. **Persist Mappings**: Save StepMapping to database for historical analysis
5. **CLI Integration**: Add commands to view/validate mappings

---

## 📝 Related Documentation

- [BDD Expansion System](../bdd/README.md) - Scenario Outline expansion
- [IntentModel Specification](../models.py) - Core intent data model
- [Test Adapters Guide](../../README.md) - How to build adapters

---

## 📄 License

See [LICENSE](../../../LICENSE) for details.
