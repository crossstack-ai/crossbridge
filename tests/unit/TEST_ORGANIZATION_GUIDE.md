# Unit Test Organization Guide

**Last Updated**: January 29, 2026  
**Version**: 2.0

---

## Overview

All unit tests are organized under `tests/unit/` with clear categorization by functionality, component, and purpose.

## Directory Structure

```
tests/unit/
├── adapters/              # Framework adapter tests
│   ├── common/           # Common adapter utilities
│   ├── java/             # Java framework adapters
│   ├── python/           # Python framework adapters
│   └── ...
├── ai/                   # AI functionality tests (NEW ✨)
│   ├── test_ai_transform.py
│   ├── test_ai_summary.py
│   ├── test_aiconfig_dict.py
│   ├── test_model_selection.py
│   └── test_fallback_integration.py
├── cli/                  # CLI interface tests
├── continuous_intelligence/  # Continuous intelligence tests (NEW ✨)
│   ├── test_continuous_intelligence_integration.py
│   └── test_failure_reporting.py
├── core/                 # Core functionality tests
│   ├── ai/              # Core AI module
│   ├── orchestration/   # Orchestration logic
│   ├── performance/     # Performance optimizations
│   └── ...
├── coverage/            # Coverage tracking tests
├── grafana/             # Grafana integration tests (NEW ✨)
│   ├── test_dashboard_queries.py
│   ├── test_grafana_query.py
│   ├── test_grafana_format.py
│   └── test_pie_query.py
├── integration_tests/   # Component integration tests (NEW ✨)
│   ├── test_hook_integration.py
│   └── test_parser_integration.py
├── migration/           # Migration functionality tests
├── persistence/         # Database persistence tests
│   ├── test_discovery_repo.py
│   ├── test_mapping_repo.py
│   ├── test_page_object_repo.py
│   └── ...
├── repo/                # Repository operations tests
├── runtime/             # Runtime functionality tests
├── translation/         # Test translation tests
├── version_tracking/    # Version tracking tests (NEW ✨)
│   └── test_version_tracking.py
└── ...                  # Framework-specific tests
```

## Categorization Logic

### 1. **AI Tests** (`tests/unit/ai/`)

Tests for AI-powered features:
- AI transformation logic
- Model selection and fallback
- OpenAI/Anthropic integration
- Configuration management
- Cost tracking and token usage

**Key Files**:
- `test_ai_transform.py` - AI transformation pipeline
- `test_ai_summary.py` - AI summary generation
- `test_model_selection.py` - Model selection logic
- `test_fallback_integration.py` - Fallback mechanisms

### 2. **Grafana Tests** (`tests/unit/grafana/`)

Tests for Grafana dashboards and visualization:
- Dashboard query generation
- Data formatting
- Query DSL
- Visualization configuration

**Key Files**:
- `test_dashboard_queries.py` - Dashboard queries
- `test_grafana_query.py` - Query DSL
- `test_grafana_format.py` - Data formatting
- `test_pie_query.py` - Pie chart queries

### 3. **Continuous Intelligence Tests** (`tests/unit/continuous_intelligence/`)

Tests for continuous intelligence and observability:
- Test execution tracking
- Failure reporting
- Performance profiling
- Flaky test detection

**Key Files**:
- `test_continuous_intelligence_integration.py` - CI integration
- `test_failure_reporting.py` - Failure reporting

### 4. **Integration Tests** (`tests/unit/integration_tests/`)

Unit-level integration tests for component interactions:
- Hook system integration
- Parser pipeline integration
- Cross-module workflows

**Key Files**:
- `test_hook_integration.py` - Hook integration
- `test_parser_integration.py` - Parser integration

**Note**: For full system integration tests, see `tests/integration/`

### 5. **Version Tracking Tests** (`tests/unit/version_tracking/`)

Tests for test versioning and tracking:
- Version detection
- Version comparison
- Historical queries
- Impact analysis

**Key Files**:
- `test_version_tracking.py` - Version tracking logic

### 6. **Adapter Tests** (`tests/unit/adapters/`)

Framework-specific adapter tests:
- Selenium adapters (Java, Python, .NET)
- Cypress adapter
- Robot Framework adapter
- pytest/JUnit/TestNG adapters

### 7. **Core Tests** (`tests/unit/core/`)

Core functionality tests:
- Orchestration logic
- Transformation pipeline
- Performance optimizations
- AI core modules

### 8. **Persistence Tests** (`tests/unit/persistence/`)

Database persistence layer tests:
- Repository operations
- Model validation
- Database queries
- UUID migration

**Note**: See [UUID Migration Guide](../../docs/testing/UUID_MIGRATION_GUIDE.md) for details.

---

## Running Tests

### Run All Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Tests by Category

```bash
# AI tests
pytest tests/unit/ai/ -v

# Grafana tests
pytest tests/unit/grafana/ -v

# Continuous Intelligence tests
pytest tests/unit/continuous_intelligence/ -v

# Integration tests
pytest tests/unit/integration_tests/ -v

# Version tracking tests
pytest tests/unit/version_tracking/ -v

# Adapter tests
pytest tests/unit/adapters/ -v

# Core tests
pytest tests/unit/core/ -v

# Persistence tests
pytest tests/unit/persistence/ -v
```

### Run Specific Test File

```bash
pytest tests/unit/ai/test_ai_transform.py -v
```

### Run with Coverage

```bash
# Coverage for specific category
pytest tests/unit/ai/ --cov=core.ai --cov-report=html

# Coverage for all unit tests
pytest tests/unit/ --cov=core --cov=adapters --cov=services --cov-report=html
```

---

## Test Naming Conventions

### File Naming

- **Format**: `test_<module_or_feature>.py`
- **Examples**:
  - `test_ai_transform.py`
  - `test_grafana_query.py`
  - `test_hook_integration.py`

### Class Naming

- **Format**: `Test<ComponentName>` or `Test<Feature>`
- **Examples**:
  ```python
  class TestAITransformation:
  class TestGrafanaQueryGeneration:
  class TestHookIntegration:
  ```

### Method Naming

- **Format**: `test_<scenario>_<expected_result>`
- **Examples**:
  ```python
  def test_ai_transform_with_openai_returns_transformed_code():
  def test_grafana_query_with_invalid_datasource_raises_error():
  def test_hook_integration_with_pytest_executes_successfully():
  ```

---

## Test Organization Best Practices

### 1. **One Test Class Per Component**

Each test class should focus on a single component or feature:

```python
class TestAITransformation:
    """Tests for AI transformation functionality."""
    
    def test_transform_with_gpt4():
        pass
    
    def test_transform_with_fallback():
        pass
```

### 2. **Use Fixtures for Common Setup**

Create fixtures in `conftest.py` for shared setup:

```python
# tests/unit/ai/conftest.py
@pytest.fixture
def mock_ai_config():
    return {"provider": "openai", "model": "gpt-4"}
```

### 3. **Categorize by Functionality, Not Technology**

- ✅ **Good**: `tests/unit/ai/` (functionality)
- ❌ **Bad**: `tests/unit/openai/` (technology)

### 4. **Keep Integration Tests Separate**

- **Unit-level integration**: `tests/unit/integration_tests/`
- **System-level integration**: `tests/integration/`

### 5. **Document Each Directory**

Every test directory should have:
- `README.md` - Overview and running instructions
- `__init__.py` - Python package marker
- `conftest.py` - Shared fixtures (if needed)

---

## Migration Summary

### Files Moved (January 29, 2026)

The following files were reorganized from the project root:

#### AI Tests → `tests/unit/ai/`
- `test_aiconfig_dict.py`
- `test_ai_summary.py`
- `test_ai_summary_quick.py`
- `test_ai_transform.py`
- `test_model_selection.py`
- `test_fallback_integration.py`

#### Grafana Tests → `tests/unit/grafana/`
- `test_dashboard_queries.py`
- `test_grafana_format.py`
- `test_grafana_query.py`
- `test_pie_query.py`

#### Continuous Intelligence Tests → `tests/unit/continuous_intelligence/`
- `test_continuous_intelligence_integration.py`
- `test_failure_reporting.py`

#### Integration Tests → `tests/unit/integration_tests/`
- `test_hook_integration.py`
- `test_parser_integration.py`

#### Version Tracking Tests → `tests/unit/version_tracking/`
- `test_version_tracking.py`

**Total Files Moved**: 16 files

---

## Test Coverage Goals

| Category | Current Coverage | Target |
|----------|-----------------|--------|
| AI | ~85% | 90% |
| Grafana | ~80% | 90% |
| Continuous Intelligence | ~75% | 85% |
| Integration Tests | ~70% | 85% |
| Version Tracking | ~60% | 80% |
| Adapters | ~90% | 95% |
| Core | ~85% | 90% |
| Persistence | ~56% | 100% |

---

## Continuous Integration

All unit tests run automatically on:

- **Pull Requests**: Full test suite
- **Main Branch Commits**: Full test suite + coverage
- **Nightly Builds**: Full test suite + performance tests

### CI Commands

```yaml
# .github/workflows/tests.yml
- name: Run Unit Tests
  run: |
    pytest tests/unit/ -v --cov=core --cov=adapters --cov=services
    pytest tests/unit/ai/ --cov=core.ai
    pytest tests/unit/grafana/ --cov=grafana
```

---

## Related Documentation

- [UUID Migration Guide](../../docs/testing/UUID_MIGRATION_GUIDE.md)
- [Production Readiness Report](../../PRODUCTION_READINESS_FINAL_REPORT.md)
- [Test Coverage Summary](../../TEST_COVERAGE_SUMMARY.md)
- [Unit Test Execution Report](../../UNIT_TEST_EXECUTION_REPORT.md)

---

## Contributing

When adding new tests:

1. **Choose the right directory** based on functionality
2. **Follow naming conventions** for files and tests
3. **Add documentation** if creating a new category
4. **Update this guide** if adding new test directories
5. **Write clear test names** that describe the scenario

---

## Questions or Issues?

- Check the [Contributing Guide](../../CONTRIBUTING.md)
- Review [Test Coverage Summary](../../TEST_COVERAGE_SUMMARY.md)
- See [Testing Completion Summary](../../TESTING_COMPLETION_SUMMARY.md)

---

**Last Updated**: January 29, 2026  
**Maintained By**: CrossBridge Team
