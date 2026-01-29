# Integration Tests (Unit Level)

This directory contains unit-level integration tests for component interactions.

## Test Files

### Integration Tests
- **test_hook_integration.py** - Tests for test framework hook integration
- **test_parser_integration.py** - Tests for parser component integration

## Coverage Areas

- Hook system integration (pytest, Robot Framework, TestNG, etc.)
- Parser pipeline integration
- Component interaction testing
- Cross-module functionality
- End-to-end workflows at unit level

## Running Tests

```bash
# Run all integration tests
pytest tests/unit/integration_tests/ -v

# Run specific test file
pytest tests/unit/integration_tests/test_hook_integration.py -v

# Run with coverage
pytest tests/unit/integration_tests/ --cov=core --cov=hooks --cov-report=html
```

## Note

These are **unit-level integration tests** that test component interactions without external dependencies.

For **full integration tests** with external systems (databases, APIs), see: `tests/integration/`

## Related Documentation

- [Hook Integration Guide](../../docs/hooks/HOOK_INTEGRATION_GUIDE.md)
- [Parser Documentation](../../docs/architecture/PARSER_ARCHITECTURE.md)
