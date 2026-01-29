# Contributing to CrossBridge

Copyright (c) 2025 Vikas Verma  
Licensed under the Apache License, Version 2.0

Thank you for your interest in contributing to CrossBridge! We welcome contributions from the community.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Contribution Workflow](#contribution-workflow)
5. [Code Standards](#code-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Submitting Changes](#submitting-changes)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors.

### Our Standards

**Positive behaviors:**
- ✅ Being respectful and inclusive
- ✅ Providing constructive feedback
- ✅ Accepting constructive criticism gracefully
- ✅ Focusing on what's best for the community

**Unacceptable behaviors:**
- ❌ Harassment or discriminatory language
- ❌ Personal or political attacks
- ❌ Public or private harassment
- ❌ Publishing others' private information

### Enforcement

Violations may be reported to vikas.sdet@gmail.com. All complaints will be reviewed and investigated.

---

## Getting Started

### Prerequisites

- **Python**: 3.8+
- **Git**: Latest version
- **PostgreSQL**: 12+ (optional, for database features)
- **Node.js**: 14+ (optional, for JavaScript parsing)

### Areas for Contribution

We welcome contributions in these areas:

1. **New Framework Adapters**: Add support for more test frameworks
2. **Bug Fixes**: Fix issues reported in GitHub Issues
3. **Documentation**: Improve guides, examples, and API docs
4. **Performance**: Optimize core algorithms
5. **Testing**: Increase test coverage
6. **AI Features**: Enhance AI transformation quality
7. **CI/CD Integration**: Add integration examples

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/crossbridge.git
cd crossbridge
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt
```

### 4. Configure Environment

```bash
# Copy example configuration
# Edit crossbridge.yml with your settings

# Set up environment variables
export OPENAI_API_KEY="your_key_here"
export DB_HOST="localhost"
export DB_PORT="5432"
```

### 5. Set Up Database (Optional)

```bash
# Create database
createdb crossbridge

# Run migrations
python scripts/setup_database.py

# Or use the setup script
./setup_flaky_db.sh
```

### 6. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=adapters --cov-report=html

# Run specific test
pytest tests/test_normalizer.py -v
```

---

## Contribution Workflow

### 1. Create a Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-new-feature

# Or bugfix branch
git checkout -b bugfix/issue-123
```

### 2. Make Changes

- Write clean, readable code
- Follow the style guide (below)
- Add tests for new features
- Update documentation

### 3. Test Your Changes

```bash
# Run tests
pytest

# Run linters
flake8 core adapters tests
black --check core adapters tests
mypy core adapters

# Format code
black core adapters tests
```

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add Mocha framework adapter"

# Follow conventional commits:
# feat: New feature
# fix: Bug fix
# docs: Documentation changes
# test: Adding tests
# refactor: Code refactoring
# perf: Performance improvements
```

### 5. Sign Your Commits

```bash
# Sign commit to accept CLA
git commit -s -m "feat: Add new feature"

# This adds:
# Signed-off-by: Your Name <your.email@example.com>
```

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-new-feature

# Create Pull Request on GitHub
# Include:
# - Clear description
# - Link to related issues
# - Screenshots (if UI changes)
# - Test results
```

---

## Code Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

```python
# Good examples

def transform_test_file(
    source_path: Path,
    target_framework: str,
    use_ai: bool = False
) -> TransformResult:
    """
    Transform a test file to target framework.
    
    Args:
        source_path: Path to source test file
        target_framework: Target framework name
        use_ai: Whether to use AI enhancement
        
    Returns:
        TransformResult with transformation details
        
    Raises:
        TransformationError: If transformation fails
    """
    try:
        # Implementation
        result = perform_transformation(source_path, target_framework)
        return result
    except Exception as e:
        logger.error(f"Transformation failed: {e}", exc_info=True)
        raise TransformationError(f"Failed to transform {source_path}") from e
```

### Key Conventions

**Naming:**
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

**Type Hints:**
```python
from typing import List, Optional, Dict, Any
from pathlib import Path

def process_tests(
    tests: List[Path],
    framework: str,
    options: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Always include type hints."""
    pass
```

**Docstrings:**
```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description (one line).
    
    Longer description if needed. Explain what the function does,
    any important details, side effects, etc.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is negative
        
    Example:
        >>> my_function("test", 42)
        True
    """
    pass
```

**Error Handling:**
```python
# Good: Specific exceptions
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except FileNotFoundError:
    logger.warning("File not found, using defaults")
    result = default_value()

# Bad: Bare except
try:
    result = risky_operation()
except:  # Too broad!
    pass
```

### File Organization

```
crossbridge/
├── adapters/
│   ├── common/          # Shared adapter utilities
│   ├── pytest/          # pytest adapter
│   └── <framework>/     # Framework-specific adapters
├── core/
│   ├── intelligence/    # AI and intelligence features
│   ├── memory/          # Memory and embeddings
│   ├── orchestration/   # Workflow orchestration
│   └── <module>/        # Other core modules
├── cli/                 # CLI interface
├── tests/               # Test suite
└── docs/                # Documentation
```

---

## Testing Guidelines

### Test Structure

```python
# tests/test_normalizer.py
import pytest
from pathlib import Path
from adapters.common.normalizer import UniversalTestNormalizer

@pytest.fixture
def normalizer():
    """Fixture for test normalizer."""
    return UniversalTestNormalizer(
        config_path="tests/fixtures/test_config.yml"
    )

@pytest.fixture
def sample_metadata():
    """Fixture for test metadata."""
    return TestMetadata(
        test_id="test_001",
        test_name="test_login",
        framework="pytest"
    )

class TestUniversalTestNormalizer:
    """Test suite for UniversalTestNormalizer."""
    
    def test_normalize_basic(self, normalizer, sample_metadata):
        """Test basic normalization."""
        result = normalizer.normalize(sample_metadata)
        
        assert result.test_id == "test_001"
        assert result.framework == "pytest"
        assert result.test_name == "test_login"
    
    def test_normalize_with_embeddings(self, normalizer):
        """Test normalization with embedding generation."""
        # Test implementation
        pass
    
    @pytest.mark.asyncio
    async def test_async_normalize(self, normalizer):
        """Test async normalization."""
        # Test implementation
        pass
    
    def test_normalize_invalid_input(self, normalizer):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            normalizer.normalize(None)
```

### Test Coverage Requirements

- **Minimum coverage**: 80% for new code
- **Required tests**: Unit tests for all new functions/classes
- **Integration tests**: For adapter and API changes
- **Documentation**: Examples in docstrings should work

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_normalizer.py

# With coverage
pytest --cov=core --cov-report=html

# Fast (skip slow tests)
pytest -m "not slow"

# Verbose
pytest -v

# Stop on first failure
pytest -x
```

---

## Documentation

### What to Document

1. **API Changes**: Update [API.md](API.md)
2. **New Features**: Add to [CHANGELOG.md](CHANGELOG.md)
3. **Configuration**: Update [crossbridge.yml](crossbridge.yml) examples
4. **Guides**: Add to `docs/` directory
5. **Code Examples**: Include in docstrings and guides

### Documentation Style

```markdown
# Module Name

Brief description of what the module does.

## Usage

Basic usage example:

\`\`\`python
from core.module import ClassName

# Initialize
obj = ClassName(param1="value")

# Use
result = obj.method()
\`\`\`

## API Reference

### ClassName

**Purpose**: What this class does

**Parameters:**
- `param1` (str): Description
- `param2` (int, optional): Description. Default: 0

**Methods:**

#### method_name(arg1, arg2)

Description of method.

**Returns**: Description of return value

**Example:**
\`\`\`python
result = obj.method_name("test", 42)
\`\`\`
```

### Adding Examples

```python
def example_function():
    """
    Example with code that runs in tests.
    
    Example:
        >>> from core.example import example_function
        >>> result = example_function()
        >>> assert result == "expected"
    """
    return "expected"
```

---

## Submitting Changes

### Before Submitting

**Checklist:**
- ✅ Code follows style guide
- ✅ Tests added and passing
- ✅ Documentation updated
- ✅ Commits are signed (`git commit -s`)
- ✅ Branch is up to date with main
- ✅ No merge conflicts
- ✅ [CLA.md](CLA.md) terms accepted

### Pull Request Template

```markdown
## Description
Brief description of changes

## Related Issues
Fixes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Tests passing
- [ ] Commits signed
- [ ] CLA accepted
```

### Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Code Review**: Maintainer reviews code
3. **Feedback**: Address review comments
4. **Approval**: Maintainer approves PR
5. **Merge**: PR merged to main branch

### After Merge

- Your contribution will be listed in [CHANGELOG.md](CHANGELOG.md)
- You'll be added to contributors list
- Feature will be included in next release

---

## Adding New Framework Adapters

### Step-by-Step Guide

**1. Create Adapter Directory:**

```bash
mkdir -p adapters/myframework
touch adapters/myframework/__init__.py
touch adapters/myframework/adapter.py
```

**2. Implement Adapter:**

```python
# adapters/myframework/adapter.py
from core.intelligence.adapters import FrameworkAdapter
from pathlib import Path
from typing import List

class MyFrameworkAdapter(FrameworkAdapter):
    """Adapter for MyFramework."""
    
    def __init__(self):
        super().__init__(
            framework_name="myframework",
            supported_extensions=[".mytest"],
            supports_ast=False
        )
    
    def discover_tests(self, directory: Path) -> List[Path]:
        """Discover test files."""
        return list(directory.rglob("*.mytest"))
    
    def extract_to_memory(self, test_path: Path):
        """Extract test to unified memory."""
        # Implementation
        pass
```

**3. Register Adapter:**

```python
# adapters/myframework/__init__.py
from core.intelligence.adapters import AdapterFactory
from .adapter import MyFrameworkAdapter

AdapterFactory.register_adapter("myframework", MyFrameworkAdapter)
```

**4. Add Tests:**

```python
# tests/test_myframework_adapter.py
def test_myframework_discovery():
    adapter = AdapterFactory.get_adapter("myframework")
    tests = adapter.discover_tests(Path("tests/fixtures/myframework"))
    assert len(tests) > 0
```

**5. Update Documentation:**

- Add to [API.md](API.md) supported frameworks table
- Add example in [FRAMEWORK_ADAPTERS_REFERENCE.md](FRAMEWORK_ADAPTERS_REFERENCE.md)
- Update [README.md](README.md) framework list

---

## Getting Help

### Resources

- **API Documentation**: [API.md](API.md)
- **Architecture Guide**: [INTELLIGENT_TEST_ASSISTANCE.md](INTELLIGENT_TEST_ASSISTANCE.md)
- **Framework Guide**: [MULTI_FRAMEWORK_SUPPORT.md](MULTI_FRAMEWORK_SUPPORT.md)
- **GitHub Issues**: Report bugs and ask questions

### Contact

- **Email**: vikas.sdet@gmail.com
- **GitHub**: @vverna-crossstack

---

## Contributor License Agreement

By contributing, you agree to the terms in [CLA.md](CLA.md):

1. You have the legal right to submit the contribution
2. Your contribution doesn't violate any employer IP agreements
3. You grant the project rights under Apache License 2.0
4. You confirm this is your original work

**Sign commits:**
```bash
git commit -s -m "Your commit message"
```

This adds:
```
Signed-off-by: Your Name <your.email@example.com>
```

---

## Recognition

Contributors are recognized in:
- [CHANGELOG.md](CHANGELOG.md) release notes
- GitHub contributors page
- Special acknowledgments for significant contributions

---

## License

All contributions will be licensed under the Apache License 2.0.

Copyright (c) 2025 Vikas Verma

See [LICENSE](LICENSE) for details.

---

**Thank you for contributing to CrossBridge! Your contributions help make test automation better for everyone.** 🙏
