# Continuous Intelligence Unit Tests

This directory contains unit tests for the continuous intelligence and observability features.

## Test Files

### Intelligence Tests
- **test_continuous_intelligence_integration.py** - Tests for continuous intelligence integration
- **test_failure_reporting.py** - Tests for test failure reporting and analysis

## Coverage Areas

- Continuous intelligence pipeline
- Test execution tracking
- Failure detection and reporting
- Performance profiling
- Flaky test detection integration
- Real-time monitoring
- Database persistence for test results

## Running Tests

```bash
# Run all continuous intelligence tests
pytest tests/unit/continuous_intelligence/ -v

# Run specific test file
pytest tests/unit/continuous_intelligence/test_continuous_intelligence_integration.py -v

# Run with coverage
pytest tests/unit/continuous_intelligence/ --cov=services --cov-report=html
```

## Related Documentation

- [Continuous Intelligence Guide](../../docs/observability/CONTINUOUS_INTELLIGENCE_README.md)
- [Flaky Detection Implementation](../../FLAKY_DETECTION_IMPLEMENTATION_SUMMARY.md)
- [Performance Profiling](../../docs/profiling/README.md)
