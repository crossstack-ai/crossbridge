# Version Tracking Unit Tests

This directory contains unit tests for version tracking and test versioning functionality.

## Test Files

### Version Tests
- **test_version_tracking.py** - Tests for test version tracking and management

## Coverage Areas

- Test version detection
- Version comparison logic
- Version metadata management
- Test evolution tracking
- Historical version queries
- Version-based impact analysis

## Running Tests

```bash
# Run all version tracking tests
pytest tests/unit/version_tracking/ -v

# Run specific test file
pytest tests/unit/version_tracking/test_version_tracking.py -v

# Run with coverage
pytest tests/unit/version_tracking/ --cov=services.version --cov-report=html
```

## Related Documentation

- [Version Tracking Guide](../../docs/features/VERSION_TRACKING.md)
- [Test Versioning Architecture](../../docs/architecture/VERSIONING_ARCHITECTURE.md)
