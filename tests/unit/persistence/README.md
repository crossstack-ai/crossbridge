# Persistence Layer Unit Tests

Comprehensive unit tests for the PostgreSQL persistence layer.

## Test Structure

```
tests/unit/persistence/
├── __init__.py
├── test_db.py                    # Database connection & health checks (24 tests)
├── test_models.py                # Data models & conversions (~25 tests)
├── test_discovery_repo.py        # Discovery repository (25 tests)
├── test_test_case_repo.py        # Test case repository (23 tests)
├── test_page_object_repo.py      # Page object repository (22 tests)
├── test_mapping_repo.py          # Mapping repository (25 tests)
├── test_orchestrator.py          # Orchestrator workflows (20+ tests)
└── README.md                     # This file
```

**Total: ~164 unit tests**

## Running Tests

### Run All Persistence Tests

```bash
pytest tests/unit/persistence/ -v
```

### Run Specific Test Module

```bash
# Database connection tests
pytest tests/unit/persistence/test_db.py -v

# Model tests
pytest tests/unit/persistence/test_models.py -v

# Repository tests
pytest tests/unit/persistence/test_discovery_repo.py -v
pytest tests/unit/persistence/test_test_case_repo.py -v
pytest tests/unit/persistence/test_page_object_repo.py -v
pytest tests/unit/persistence/test_mapping_repo.py -v

# Orchestrator tests
pytest tests/unit/persistence/test_orchestrator.py -v
```

### Run with Coverage

```bash
pytest tests/unit/persistence/ --cov=persistence --cov-report=html
```

### Run Specific Test Class

```bash
pytest tests/unit/persistence/test_db.py::TestDatabaseConfig -v
pytest tests/unit/persistence/test_orchestrator.py::TestPersistDiscovery -v
```

## Test Coverage

### test_db.py (24 tests)
- **DatabaseConfig**: Environment variable handling, URL construction, is_configured checks
- **create_session**: Session creation, connection failures, graceful degradation
- **check_database_health**: Health checks, schema validation, error handling
- **Edge Cases**: Empty URLs, malformed URLs, NULL values
- **Contract Stability**: Return type guarantees

### test_models.py (~25 tests)
- **DiscoveryRun**: Model instantiation, defaults (triggered_by="cli")
- **TestCase**: full_name property (ClassName.methodName)
- **PageObject**: Basic instantiation
- **TestPageMapping**: Confidence defaults (1.0)
- **Conversion Helpers**: from_test_metadata (package parsing), from_page_object_reference
- **Edge Cases**: Empty tags, None values, malformed names
- **Contract Stability**: Required attributes validation

### test_discovery_repo.py (25 tests)
- **create_discovery_run**: Minimal parameters, git context, metadata, custom triggered_by
- **get_discovery_run**: Finding existing/non-existent runs
- **get_latest_discovery_run**: Latest run retrieval by project
- **list_discovery_runs**: All runs, filtering by project, limit
- **get_discovery_stats**: Test/page/mapping counts
- **Edge Cases**: Empty project names, None metadata, NULL results
- **Contract Stability**: Return types (int, DiscoveryRun, list, dict)

### test_test_case_repo.py (23 tests)
- **upsert_test_case**: New inserts, updates on conflict, tags handling
- **find_test_case**: Finding by framework/package/class/method
- **link_test_to_discovery**: Linking tests to discoveries, idempotency
- **get_tests_in_discovery**: Retrieving all tests in a discovery
- **Edge Cases**: None tags, empty packages, special characters
- **Contract Stability**: Return types (int, TestCase, list)

### test_page_object_repo.py (22 tests)
- **upsert_page_object**: New inserts, metadata handling, updates on conflict
- **find_page_object**: Finding by name and file path
- **get_page_object_usage**: Test counts, discovery counts, sources
- **get_most_used_page_objects**: Ranking by usage, limiting results
- **Edge Cases**: Empty names, None metadata, special characters
- **Contract Stability**: Return types (int, PageObject, dict, list of tuples)

### test_mapping_repo.py (25 tests)
- **insert_mapping**: Append-only inserts, confidence scores, different sources
- **get_mappings_by_test**: Filtering by test and discovery
- **get_impacted_tests**: Finding tests affected by page changes, confidence thresholds
- **get_latest_mappings_for_test**: Deduplication by page_object_id
- **get_mapping_source_stats**: Source distribution statistics
- **Edge Cases**: Zero/max confidence, high thresholds
- **Contract Stability**: Return types (int, list)

### test_orchestrator.py (20+ tests)
- **persist_discovery**: Full workflow (discovery → tests → pages → mappings), empty tests
- **get_latest_discovery_stats**: Stats retrieval, not found cases
- **compare_discoveries**: Comparing two runs, positive/negative diffs
- **get_git_commit**: Success, not a repo, no commits
- **get_git_branch**: Success, detached HEAD, not a repo
- **Edge Cases**: Duplicate page objects, None framework hint
- **Contract Stability**: Return types (int, dict, str or None)

## Testing Philosophy

### Mocking Strategy
- **Mock Database Sessions**: All tests use `mock_session` fixture to avoid database dependency
- **Mock External Calls**: Git commands, subprocess calls mocked
- **Mock Repository Functions**: Orchestrator tests mock repository calls
- **No Real Database**: Tests run without PostgreSQL installation

### Contract Testing
Each test module includes a `TestContractStability` class that validates:
- Return types match API documentation
- Required dictionary keys are present
- None vs empty list/dict handling is consistent
- Error conditions raise expected exceptions

### Edge Case Coverage
Comprehensive edge case testing:
- **None Values**: NULL handling in all contexts
- **Empty Collections**: Empty lists, empty strings, zero counts
- **Special Characters**: Unicode, SQL injection attempts
- **Boundary Values**: Min/max confidence (0.0/1.0), zero limits
- **Malformed Data**: Invalid URLs, unparseable test names

### Error Handling
All repository functions test:
- Exception propagation
- Rollback on error
- Graceful degradation (return None vs raise)

## Continuous Integration

These tests are designed to run in CI environments:
- **Fast**: No database required, runs in < 5 seconds
- **Isolated**: No shared state between tests
- **Deterministic**: No flaky tests, reproducible results
- **Parallel-Safe**: Can run with `pytest -n auto`

### CI Example

```yaml
# .github/workflows/test.yml
- name: Run persistence tests
  run: |
    pytest tests/unit/persistence/ -v --cov=persistence
```

## Future Test Additions

### Integration Tests (Coming Soon)
- Tests with real PostgreSQL database
- Docker Compose setup for CI
- End-to-end workflows (discover → persist → query)
- Performance tests with large datasets

### CLI Tests (Coming Soon)
- Testing `crossbridge discover --persist`
- Database health check command
- Error messages when DB not configured

## Maintenance

### Adding New Tests
When adding new persistence functionality:
1. Add unit tests with mocked database
2. Include edge cases (None, empty, special characters)
3. Add contract stability tests
4. Update this README with test counts

### Test Naming Convention
- `test_<function_name>_<scenario>`: Descriptive test names
- `test_<function_name>_error_handling`: Error paths
- `test_<function_name>_edge_case`: Edge cases

### Fixtures
Common fixtures used:
- `mock_session`: Mocked SQLAlchemy session
- `sample_tests`: Sample TestMetadata objects
- `@patch`: Mocking external dependencies

## Related Documentation

- [Persistence Layer README](../../../persistence/README.md) - Architecture and usage
- [Database Schema](../../../persistence/schema.sql) - Table definitions
- [Extractor Tests README](../adapters/java/README.md) - Extractor test suite
