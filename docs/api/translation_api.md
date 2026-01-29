# Translation API Documentation

## Overview

The CrossBridge Translation API provides interfaces and utilities for transforming test automation code between different frameworks. The translation pipeline consists of parsers, transformers, and generators that work together to convert tests while preserving their intent and behavior.

## Core Interfaces

### Parser Interface

Parsers are responsible for reading source test code and converting it into an intermediate representation (TestIntent model).

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.translation.models import TestIntent

class BaseParser(ABC):
    """Base interface for framework-specific parsers."""
    
    @abstractmethod
    def parse(self, source_file: str) -> TestIntent:
        """
        Parse a test file into TestIntent model.
        
        Args:
            source_file: Path to the source test file
            
        Returns:
            TestIntent: Intermediate representation of the test
            
        Raises:
            ParseError: If the file cannot be parsed
        """
        pass
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """
        Check if this parser can handle the given file.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if this parser supports the file
        """
        pass
```

### Generator Interface

Generators convert TestIntent models into target framework code.

```python
class BaseGenerator(ABC):
    """Base interface for framework-specific code generators."""
    
    @abstractmethod
    def generate(self, intent: TestIntent) -> str:
        """
        Generate target framework code from TestIntent.
        
        Args:
            intent: Test intent model to generate from
            
        Returns:
            str: Generated test code in target framework
            
        Raises:
            GenerationError: If code cannot be generated
        """
        pass
    
    @abstractmethod
    def get_imports(self, intent: TestIntent) -> List[str]:
        """
        Get required imports for the generated code.
        
        Args:
            intent: Test intent model
            
        Returns:
            List[str]: Import statements needed
        """
        pass
```

### TestIntent Model

The TestIntent model is the intermediate representation that captures test behavior in a framework-agnostic way.

```python
@dataclass
class TestIntent:
    """Framework-agnostic representation of a test."""
    
    # Test identification
    test_id: str
    test_name: str
    test_file: str
    framework: str
    
    # Test structure
    setup_steps: List[TestStep]
    test_steps: List[TestStep]
    teardown_steps: List[TestStep]
    
    # Test metadata
    tags: List[str]
    description: Optional[str]
    timeout: Optional[int]
    
    # Dependencies
    fixtures: List[str]
    imports: List[str]
    
    # Page Objects and locators
    page_objects: List[PageObject]
    locators: Dict[str, Locator]
```

## Translation Pipeline

### Step 1: Parse Source

```python
from adapters.pytest.parser import PytestParser

parser = PytestParser()
intent = parser.parse("tests/test_login.py")
```

### Step 2: Transform (Optional)

Apply transformations to modernize or enhance the test intent.

```python
from core.translation.transformers import LocatorModernizer, WaitImprover

# Modernize locators
modernizer = LocatorModernizer()
intent = modernizer.transform(intent)

# Improve wait strategies
wait_improver = WaitImprover()
intent = wait_improver.transform(intent)
```

### Step 3: Generate Target

```python
from adapters.playwright.generator import PlaywrightGenerator

generator = PlaywrightGenerator()
target_code = generator.generate(intent)

# Save to file
with open("tests/test_login.spec.ts", "w") as f:
    f.write(target_code)
```

## Custom Idioms

Create custom transformation patterns for specific use cases.

### Defining a Custom Idiom

```python
from core.translation.idioms import IdiomPattern, IdiomMatcher

class CustomLoginIdiom(IdiomPattern):
    """Custom idiom for login patterns."""
    
    def matches(self, steps: List[TestStep]) -> bool:
        """Check if steps match this idiom."""
        return (len(steps) >= 3 and
                any("username" in s.target for s in steps) and
                any("password" in s.target for s in steps) and
                any("login" in s.action for s in steps))
    
    def transform(self, steps: List[TestStep]) -> List[TestStep]:
        """Transform matched steps."""
        # Extract values
        username = steps[0].value
        password = steps[1].value
        
        # Return simplified idiom
        return [TestStep(
            action="login_as",
            target="user",
            value={"username": username, "password": password},
            description="Perform login with credentials"
        )]
```

### Registering Custom Idioms

```python
from core.translation.idiom_registry import IdiomRegistry

registry = IdiomRegistry()
registry.register(CustomLoginIdiom())

# Use in transformation
transformer = IdiomTransformer(registry)
transformed_intent = transformer.transform(intent)
```

## Locator Strategies

CrossBridge supports multiple locator strategies and can convert between them.

### Locator Types

```python
class LocatorType(Enum):
    ID = "id"
    NAME = "name"
    CSS = "css"
    XPATH = "xpath"
    CLASS_NAME = "class"
    TAG_NAME = "tag"
    LINK_TEXT = "link_text"
    PARTIAL_LINK_TEXT = "partial_link_text"
    PLAYWRIGHT_SELECTOR = "playwright"
    ACCESSIBLE_NAME = "accessible_name"
    ROLE = "role"
```

### Locator Conversion

```python
from core.translation.locator_converter import LocatorConverter

converter = LocatorConverter()

# Convert XPath to CSS
css_locator = converter.convert(
    "//input[@name='username']",
    from_type=LocatorType.XPATH,
    to_type=LocatorType.CSS
)
# Result: "input[name='username']"

# Convert to modern Playwright selector
playwright_locator = converter.convert_to_playwright(
    "css=#login-button"
)
# Result: "page.locator('#login-button')"
```

## Validation

Validate generated code before writing to files.

```python
from core.translation.validator import CodeValidator

validator = CodeValidator()

# Validate syntax
is_valid, errors = validator.validate_syntax(generated_code, language="python")

if not is_valid:
    for error in errors:
        print(f"Syntax error at line {error.line}: {error.message}")

# Validate framework compatibility
is_compatible = validator.validate_framework_compatibility(
    intent,
    target_framework="playwright"
)
```

## Error Handling

The translation API provides specific exception types for different failure scenarios.

```python
from core.translation.exceptions import (
    ParseError,
    GenerationError,
    TransformationError,
    ValidationError
)

try:
    intent = parser.parse(source_file)
    transformed = transformer.transform(intent)
    code = generator.generate(transformed)
except ParseError as e:
    print(f"Failed to parse: {e}")
except TransformationError as e:
    print(f"Transformation failed: {e}")
except GenerationError as e:
    print(f"Code generation failed: {e}")
```

## Best Practices

### 1. Always Validate Input

```python
if not parser.can_parse(file_path):
    raise ValueError(f"Parser cannot handle {file_path}")
```

### 2. Use Progressive Enhancement

```python
# Start with basic transformation
intent = parser.parse(source)

# Add enhancements progressively
if enable_locator_modernization:
    intent = modernizer.transform(intent)

if enable_ai_enhancement:
    intent = ai_enhancer.enhance(intent)

# Generate final code
code = generator.generate(intent)
```

### 3. Preserve Test Metadata

```python
# Ensure test metadata is preserved
generated_intent.tags = original_intent.tags
generated_intent.description = original_intent.description
generated_intent.timeout = original_intent.timeout
```

### 4. Handle Framework-Specific Features

```python
# Check for unsupported features
if intent.has_feature("parallel_execution") and not generator.supports_parallel:
    warnings.warn("Target framework doesn't support parallel execution")
    # Provide fallback or alternative
```

## API Reference

### Core Modules

- `core.translation.parser` - Base parser interfaces
- `core.translation.generator` - Base generator interfaces
- `core.translation.models` - Data models (TestIntent, TestStep, etc.)
- `core.translation.transformers` - Code transformation utilities
- `core.translation.idioms` - Idiom pattern matching and transformation
- `core.translation.locator_converter` - Locator conversion utilities
- `core.translation.validator` - Code validation utilities

### Adapter Modules

Each adapter provides framework-specific implementations:

- `adapters.pytest.parser.PytestParser`
- `adapters.selenium_python.parser.SeleniumParser`
- `adapters.robot.parser.RobotParser`
- `adapters.playwright.generator.PlaywrightGenerator`
- And more...

## Examples

See the [examples/translation/](../examples/translation/) directory for complete working examples of:

- Custom parser implementation
- Custom generator implementation
- Custom idiom patterns
- End-to-end translation pipeline
- Batch translation of test suites

## Further Reading

- [Creating Custom Adapters](../guides/creating_adapters.md)
- [Custom Parser Development](../guides/custom_parsers.md)
- [Locator Best Practices](../guides/locator_best_practices.md)
