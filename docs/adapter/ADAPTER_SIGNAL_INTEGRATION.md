# Adapter Signal Integration Guide

**How to integrate step-to-code-path mapping into your test framework adapter.**

## Overview

This guide shows adapter developers how to register signals during test discovery to enable impact analysis, migration parity validation, and test intelligence features.

## Core Principle: Register During Discovery, Not Execution

**✅ CORRECT: Register during test discovery (parse-time)**
```python
class MyAdapter(BaseTestExtractor):
    def extract_tests(self, file_path: str) -> List[IntentModel]:
        # 1. Parse test file
        test_cases = self._parse_file(file_path)
        
        # 2. Parse code implementations (Page Objects, Keywords, etc.)
        implementations = self._parse_implementations(file_path)
        
        # 3. Register signals for step → code mapping
        for impl in implementations:
            self.signal_registry.register_signal(
                pattern=impl.step_pattern,
                signal=StepSignal(
                    type=SignalType.CODE_PATH,
                    value=f"{impl.file}::{impl.class_name}.{impl.method_name}"
                )
            )
        
        # 4. Return test intents (resolver will map steps later)
        return [self._to_intent(tc) for tc in test_cases]
```

**❌ WRONG: Don't register during test execution**
```python
def execute_step(step_text):
    # Don't do this - too late, wrong place!
    self.signal_registry.register_signal(step_text, ...)
    execute(step_text)
```

## Why Register During Discovery?

1. **Performance**: Parse once, use many times
2. **Completeness**: Know all step→code mappings upfront
3. **Impact Analysis**: Can find affected tests before running them
4. **Migration Validation**: Can check parity before migration
5. **Test Intelligence**: Can analyze coverage and relationships

## Integration Pattern by Framework

### 1. Selenium BDD + Java (Cucumber/JUnit)

**Scenario:**
- Cucumber `.feature` files with Gherkin steps
- Java Page Objects with `@FindBy` annotations
- Step definitions with `@Given/@When/@Then` annotations

**Integration:**
```python
from adapters.common.mapping import StepSignal, SignalType, StepSignalRegistry

class SeleniumBDDJavaAdapter(BaseTestExtractor):
    def __init__(self):
        self.signal_registry = StepSignalRegistry()
    
    def extract_tests(self, project_path: str) -> List[IntentModel]:
        # 1. Parse Page Objects (.java files)
        page_objects = self._parse_page_objects(project_path)
        for po in page_objects:
            for method in po.methods:
                # Register Page Object methods
                self.signal_registry.register_signal(
                    pattern=self._method_to_pattern(method.name),
                    signal=StepSignal(
                        type=SignalType.CODE_PATH,
                        value=f"{po.file_path}::{po.class_name}.{method.name}",
                        metadata={
                            "parameters": method.parameters,
                            "return_type": method.return_type
                        }
                    )
                )
        
        # 2. Parse Step Definitions (@Given/@When/@Then)
        step_defs = self._parse_step_definitions(project_path)
        for step_def in step_defs:
            self.signal_registry.register_signal(
                pattern=step_def.pattern,  # From annotation: @When("user logs in with {string} and {string}")
                signal=StepSignal(
                    type=SignalType.METHOD,
                    value=f"{step_def.class_name}.{step_def.method_name}",
                    metadata={
                        "annotation": step_def.annotation,
                        "file": step_def.file_path,
                        "line": step_def.line_number
                    }
                )
            )
        
        # 3. Parse .feature files and create intents
        feature_files = glob.glob(f"{project_path}/**/*.feature", recursive=True)
        all_intents = []
        for feature_file in feature_files:
            scenarios = self._parse_feature_file(feature_file)
            for scenario in scenarios:
                intent = self._scenario_to_intent(scenario)
                all_intents.append(intent)
        
        return all_intents
    
    def _method_to_pattern(self, method_name: str) -> str:
        """Convert camelCase method to step pattern."""
        # clickLoginButton → "click login button"
        # loginWithCredentials → "login with credentials"
        import re
        words = re.sub('([A-Z])', r' \1', method_name).lower().strip()
        return words
    
    def _parse_page_objects(self, project_path: str) -> List[PageObjectInfo]:
        """Parse Java Page Object classes."""
        java_files = glob.glob(f"{project_path}/**/pages/**/*.java", recursive=True)
        page_objects = []
        
        for java_file in java_files:
            with open(java_file, 'r') as f:
                content = f.read()
            
            # Extract class name
            class_match = re.search(r'public class (\w+)', content)
            if not class_match:
                continue
            
            class_name = class_match.group(1)
            
            # Extract methods (public methods that might be test steps)
            method_pattern = r'public\s+(\w+)\s+(\w+)\s*\(([^)]*)\)'
            methods = []
            for match in re.finditer(method_pattern, content):
                return_type = match.group(1)
                method_name = match.group(2)
                params = match.group(3)
                
                methods.append(MethodInfo(
                    name=method_name,
                    parameters=params,
                    return_type=return_type
                ))
            
            page_objects.append(PageObjectInfo(
                file_path=java_file,
                class_name=class_name,
                methods=methods
            ))
        
        return page_objects
    
    def _parse_step_definitions(self, project_path: str) -> List[StepDefInfo]:
        """Parse Cucumber step definitions with @Given/@When/@Then."""
        java_files = glob.glob(f"{project_path}/**/stepdefinitions/**/*.java", recursive=True)
        step_defs = []
        
        for java_file in java_files:
            with open(java_file, 'r') as f:
                lines = f.readlines()
            
            class_name = None
            for i, line in enumerate(lines):
                # Extract class name
                if 'public class' in line:
                    class_match = re.search(r'public class (\w+)', line)
                    if class_match:
                        class_name = class_match.group(1)
                
                # Extract step definitions
                annotation_match = re.match(r'\s*@(Given|When|Then)\("([^"]+)"\)', line)
                if annotation_match and class_name:
                    annotation = annotation_match.group(1)
                    pattern = annotation_match.group(2)
                    
                    # Next line should have method definition
                    if i + 1 < len(lines):
                        method_match = re.search(r'public void (\w+)\(', lines[i + 1])
                        if method_match:
                            method_name = method_match.group(1)
                            step_defs.append(StepDefInfo(
                                class_name=class_name,
                                method_name=method_name,
                                annotation=annotation,
                                pattern=pattern,
                                file_path=java_file,
                                line_number=i + 1
                            ))
        
        return step_defs
```

### 2. Robot Framework + Python

**Scenario:**
- `.robot` test files with keywords
- Python keyword libraries

**Integration:**
```python
class RobotFrameworkAdapter(BaseTestExtractor):
    def extract_tests(self, robot_file: str) -> List[IntentModel]:
        # 1. Parse keyword libraries
        libraries = self._get_imported_libraries(robot_file)
        for lib in libraries:
            keywords = self._parse_library_keywords(lib)
            for keyword in keywords:
                self.signal_registry.register_signal(
                    pattern=keyword.name.lower().replace('_', ' '),
                    signal=StepSignal(
                        type=SignalType.CODE_PATH,
                        value=f"{lib.file_path}::{lib.class_name}.{keyword.name}",
                        metadata={
                            "library": lib.name,
                            "arguments": keyword.arguments
                        }
                    )
                )
        
        # 2. Parse test cases
        test_cases = self._parse_robot_file(robot_file)
        return [self._test_to_intent(tc) for tc in test_cases]
    
    def _parse_library_keywords(self, library_path: str) -> List[KeywordInfo]:
        """Parse Robot Framework keyword library."""
        import ast
        
        with open(library_path, 'r') as f:
            tree = ast.parse(f.read())
        
        keywords = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a public keyword (not starting with _)
                if not node.name.startswith('_'):
                    keywords.append(KeywordInfo(
                        name=node.name,
                        arguments=[arg.arg for arg in node.args.args]
                    ))
        
        return keywords
```

### 3. Behave + Python (BDD)

**Scenario:**
- `.feature` files with Gherkin steps
- Python step definitions with `@given/@when/@then` decorators

**Integration:**
```python
class BehaveAdapter(BaseTestExtractor):
    def extract_tests(self, project_path: str) -> List[IntentModel]:
        # 1. Parse step definitions
        step_files = glob.glob(f"{project_path}/steps/**/*.py", recursive=True)
        for step_file in step_files:
            step_defs = self._parse_step_definitions(step_file)
            for step_def in step_defs:
                self.signal_registry.register_signal(
                    pattern=step_def.pattern,
                    signal=StepSignal(
                        type=SignalType.CODE_PATH,
                        value=f"{step_file}::{step_def.function_name}",
                        metadata={
                            "decorator": step_def.decorator,
                            "line": step_def.line_number
                        }
                    )
                )
        
        # 2. Parse .feature files
        feature_files = glob.glob(f"{project_path}/features/**/*.feature", recursive=True)
        all_intents = []
        for feature_file in feature_files:
            intents = self._parse_feature_file(feature_file)
            all_intents.extend(intents)
        
        return all_intents
    
    def _parse_step_definitions(self, step_file: str) -> List[StepDefInfo]:
        """Parse Behave step definitions with @given/@when/@then decorators."""
        import ast
        
        with open(step_file, 'r') as f:
            content = f.read()
            tree = ast.parse(content)
        
        step_defs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Check for @given/@when/@then decorators
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, 'id'):
                            decorator_name = decorator.func.id
                            if decorator_name in ['given', 'when', 'then', 'step']:
                                # Extract pattern from decorator argument
                                if decorator.args:
                                    pattern_node = decorator.args[0]
                                    if isinstance(pattern_node, ast.Constant):
                                        pattern = pattern_node.value
                                        step_defs.append(StepDefInfo(
                                            function_name=node.name,
                                            decorator=decorator_name,
                                            pattern=pattern,
                                            line_number=node.lineno
                                        ))
        
        return step_defs
```

### 4. pytest-bdd + Python

**Scenario:**
- `.feature` files with Gherkin steps
- pytest fixtures with `@scenario/@given/@when/@then` decorators

**Integration:**
```python
class PytestBDDAdapter(BaseTestExtractor):
    def extract_tests(self, project_path: str) -> List[IntentModel]:
        # 1. Parse conftest.py and test files for step definitions
        py_files = glob.glob(f"{project_path}/**/*.py", recursive=True)
        for py_file in py_files:
            if 'test_' in os.path.basename(py_file) or 'conftest' in os.path.basename(py_file):
                step_defs = self._parse_pytest_bdd_steps(py_file)
                for step_def in step_defs:
                    self.signal_registry.register_signal(
                        pattern=step_def.pattern,
                        signal=StepSignal(
                            type=SignalType.CODE_PATH,
                            value=f"{py_file}::{step_def.function_name}",
                            metadata={
                                "decorator": step_def.decorator,
                                "is_fixture": step_def.is_fixture
                            }
                        )
                    )
        
        # 2. Parse .feature files
        feature_files = glob.glob(f"{project_path}/**/*.feature", recursive=True)
        return self._parse_features(feature_files)
```

## Signal Type Selection Guide

Choose the appropriate `SignalType` based on what you're registering:

```python
# CODE_PATH: Full path to implementation (PREFERRED)
StepSignal(
    type=SignalType.CODE_PATH,
    value="pages/login_page.py::LoginPage.login"
)

# PAGE_OBJECT: Just the page object class name
StepSignal(
    type=SignalType.PAGE_OBJECT,
    value="LoginPage"
)

# METHOD: Class.method or just method name
StepSignal(
    type=SignalType.METHOD,
    value="LoginPage.login"  # or just "login"
)

# DECORATOR: From framework decorators
StepSignal(
    type=SignalType.DECORATOR,
    value="@step('user logs in with {username}')"
)

# ANNOTATION: From Java/C# annotations
StepSignal(
    type=SignalType.ANNOTATION,
    value="@Keyword('Login With')"
)
```

**Best Practice:** Always prefer `CODE_PATH` when possible - it provides the most complete information.

## Pattern Matching Tips

### Use Parameter Placeholders
```python
# ✅ GOOD: Generic pattern with placeholders
registry.register_signal(
    "user logs in with {username} and {password}",  # Matches any values
    signal
)

# ❌ BAD: Specific values
registry.register_signal(
    "user logs in with admin and pass123",  # Only matches this exact step
    signal
)
```

### Register Multiple Patterns
```python
# Register both specific and general patterns for better matching
registry.register_signal("user logs in with credentials", signal)  # Specific
registry.register_signal("logs in", signal)                         # General
```

### Handle Framework Variations
```python
# Cucumber: {string}, {int}, etc.
"user logs in with {string} and {string}"

# Robot Framework: ${var} syntax
"Login With ${username} And ${password}"

# Behave: {name:Type} syntax
"user logs in with {username:string} and {password:string}"

# Normalize to generic placeholders for crossbridge
"user logs in with {username} and {password}"
```

## Metadata Best Practices

Include useful metadata for debugging and analysis:

```python
StepSignal(
    type=SignalType.CODE_PATH,
    value="pages/login_page.py::LoginPage.login",
    metadata={
        # Source location
        "file": "src/pages/LoginPage.java",
        "line": 42,
        
        # Method details
        "parameters": ["username: String", "password: String"],
        "return_type": "void",
        
        # Framework-specific
        "annotation": "@When",
        "page_object": "LoginPage",
        
        # For analysis
        "tags": ["auth", "critical"],
        "complexity": "simple"
    }
)
```

## Testing Your Integration

```python
def test_adapter_registers_signals():
    """Verify adapter registers signals correctly."""
    adapter = MyAdapter()
    intents = adapter.extract_tests("test_file.java")
    
    # Check signals were registered
    assert adapter.signal_registry.count() > 0
    
    # Check specific signal exists
    signals = adapter.signal_registry.get_signals_for_step("user logs in")
    assert len(signals) > 0
    assert any(s.value.endswith("LoginPage.login") for s in signals)
```

## Integration Checklist

- [ ] **Parse implementation code** (Page Objects, Keywords, Step Defs)
- [ ] **Register signals during discovery** (not execution)
- [ ] **Use CODE_PATH signal type** (most complete information)
- [ ] **Use parameter placeholders** (e.g., `{username}` not `admin`)
- [ ] **Register multiple patterns** (specific and general)
- [ ] **Include useful metadata** (file, line, parameters)
- [ ] **Test signal registration** (verify signals are registered)
- [ ] **Pass registry to resolver** (for step→code mapping)
- [ ] **Populate IntentModel.code_paths** (use resolver in intent mapping)

## Complete Example

Here's a complete mini-adapter showing the full flow:

```python
from adapters.common.mapping import StepSignal, SignalType, StepSignalRegistry, StepMappingResolver
from adapters.common.models import IntentModel
from adapters.common.bdd import map_expanded_scenario_to_intent

class MiniAdapter:
    def __init__(self):
        self.signal_registry = StepSignalRegistry()
        self.resolver = StepMappingResolver(self.signal_registry)
    
    def extract_tests(self, project_path: str) -> List[IntentModel]:
        # 1. DISCOVERY PHASE: Register signals
        self._register_signals(project_path)
        
        # 2. EXTRACTION PHASE: Parse tests
        test_cases = self._parse_tests(project_path)
        
        # 3. MAPPING PHASE: Create intents with code paths
        intents = []
        for test_case in test_cases:
            intent = self._test_to_intent(test_case)
            
            # Resolve code paths for each step
            for step in intent.steps:
                mapping = self.resolver.resolve_step(step.description)
                intent.code_paths.extend(mapping.code_paths)
            
            intents.append(intent)
        
        return intents
    
    def _register_signals(self, project_path: str):
        """Register all step→code signals."""
        # Parse Page Objects
        page_objects = self._parse_page_objects(project_path)
        for po in page_objects:
            for method in po.methods:
                self.signal_registry.register_signal(
                    pattern=method.step_pattern,
                    signal=StepSignal(
                        type=SignalType.CODE_PATH,
                        value=f"{po.file}::{po.class_name}.{method.name}"
                    )
                )
    
    def _parse_tests(self, project_path: str):
        """Parse test files."""
        # Your test parsing logic here
        pass
    
    def _test_to_intent(self, test_case) -> IntentModel:
        """Convert test case to IntentModel."""
        # Your conversion logic here
        pass
```

## Troubleshooting

### No signals registered
**Problem:** `signal_registry.count() == 0` after discovery

**Solutions:**
- Check file glob patterns (are you finding the right files?)
- Verify parsing logic (are you extracting methods correctly?)
- Add debug logging to see what's being parsed

### Signals don't match steps
**Problem:** `resolver.resolve_step(step)` returns empty mapping

**Solutions:**
- Check pattern normalization (BDD keywords are removed)
- Try registering more general patterns
- Add debug logging: `registry.get_all_patterns()`

### Duplicate signals
**Problem:** Same signal registered multiple times

**Solutions:**
- Deduplicate during discovery
- Use a set to track registered patterns
- Check your parsing logic for duplicate iterations

## Related Documentation

- [Step-to-Code-Path Mapping README](../adapters/common/mapping/README.md) - Full API documentation
- [BDD Expansion README](../adapters/common/bdd/README.md) - Scenario Outline expansion
- [Mapping Demo](../examples/mapping_demo.py) - Interactive demonstration

## Support

If you encounter issues integrating your adapter:
1. Check the [mapping demo](../examples/mapping_demo.py) for examples
2. Review existing adapters in `adapters/`
3. Add debug logging to see what signals are registered
4. Test with simple cases first, then add complexity
