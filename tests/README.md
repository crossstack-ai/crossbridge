# CrossBridge Test Suite

This directory contains comprehensive tests for the CrossBridge CLI architecture.

## Test Structure

```
tests/
├── conftest.py              # pytest configuration
├── unit/                    # Unit tests (fast, isolated)
│   └── test_orchestration.py
└── integration/             # Integration tests (with mocks)
    └── test_cli.py
```

## Running Tests

### All Tests
```bash
pytest tests/
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### With Coverage
```bash
pytest tests/ --cov=core --cov=cli --cov=services --cov-report=html
```

### Specific Test
```bash
pytest tests/unit/test_orchestration.py::TestMigrationRequest::test_create_basic_request -v
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Very fast (milliseconds)
- **Dependencies**: Minimal, heavily mocked
- **Coverage**:
  - Pydantic models (MigrationRequest, MigrationResponse)
  - MigrationOrchestrator workflow
  - Error code generation
  - PR description generation
  - Field validation

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions
- **Speed**: Fast (seconds)
- **Dependencies**: Mocked external services (repos, APIs)
- **Coverage**:
  - CLI branding components
  - Progress tracking
  - Interactive prompts
  - Error handling
  - Complete CLI workflow

## Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| core/orchestration/ | 90%+ | ✅ |
| cli/ | 85%+ | ✅ |
| services/ | 80%+ | ✅ |

## Key Test Scenarios

### Security Tests
- ✅ Token exclusion from serialization
- ✅ API key redaction in logs
- ✅ Sensitive data filtering
- ✅ Password prompts never echo

### Workflow Tests
- ✅ Complete migration workflow (validation → analysis → transformation → commit)
- ✅ Dry-run mode (no commits)
- ✅ PR creation with proper description
- ✅ Progress callback invocation at each stage
- ✅ Error handling and recovery

### Validation Tests
- ✅ Repository URL validation (GitHub, Bitbucket, Azure, GitLab)
- ✅ Invalid platform rejection
- ✅ Branch existence checks
- ✅ Authentication validation

### Branding Tests
- ✅ CrossStack AI company name displayed
- ✅ CrossBridge product name displayed
- ✅ Welcome screen formatting
- ✅ Error message formatting
- ✅ Completion message formatting

## Mocking Strategy

### Repository Connectors
```python
mock_connector = Mock()
mock_connector.list_branches.return_value = [Mock(name="main")]
mock_connector.list_all_files.return_value = [Mock(path="Test.java")]
```

### Progress Callbacks
```python
progress_calls = []
def progress_callback(msg, status):
    progress_calls.append((msg, status))
```

### CLI Testing
```python
from typer.testing import CliRunner
runner = CliRunner()
result = runner.invoke(app, ["migrate"])
```

## Writing New Tests

### Unit Test Template
```python
def test_feature_name():
    """Test description."""
    # Arrange
    request = MigrationRequest(...)
    
    # Act
    result = orchestrator.run(request)
    
    # Assert
    assert result.status == MigrationStatus.COMPLETED
```

### Integration Test Template
```python
@patch('cli.app.MigrationOrchestrator')
def test_cli_feature(mock_orchestrator):
    """Test CLI feature."""
    # Setup mocks
    mock_orchestrator.return_value.run.return_value = mock_response
    
    # Run CLI
    runner = CliRunner()
    result = runner.invoke(app, ["migrate"])
    
    # Verify
    assert result.exit_code == 0
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest tests/ -v --cov=core --cov=cli --cov=services
```

## Debug Tips

### Failed Test
```bash
pytest tests/unit/test_orchestration.py::test_name -vv -s
```

### Show Print Statements
```bash
pytest tests/ -s
```

### Stop on First Failure
```bash
pytest tests/ -x
```

### Run Last Failed
```bash
pytest tests/ --lf
```

## Test Data

Test fixtures use realistic data:
- **Repository URLs**: github.com, bitbucket.org, dev.azure.com
- **File Counts**: 150 Java files, 260 feature files (from real project)
- **PR Numbers**: Based on actual PR #850
- **Timing**: Realistic durations (10-50 seconds)

## Coverage Reports

Generate HTML coverage report:
```bash
pytest tests/ --cov=core --cov=cli --cov=services --cov-report=html
open htmlcov/index.html
```

## Best Practices

1. **Isolation**: Each test is independent
2. **Mocking**: External dependencies always mocked
3. **Assertions**: Multiple, specific assertions per test
4. **Naming**: Descriptive test names (test_what_when_expected)
5. **Documentation**: Docstrings explain test purpose
6. **Speed**: Fast execution for rapid feedback

## Known Issues

None currently.

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure >80% coverage for new code
3. Add integration tests for CLI changes
4. Update this README if adding new test categories
