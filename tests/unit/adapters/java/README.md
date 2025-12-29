# Java Extractor Layer Unit Tests

Comprehensive unit test suite for the Java adapter extractor layer (framework detection, AST parsing, PageObject mapping).

## Test Structure

```
tests/unit/adapters/java/
├── test_detector.py           # Framework detection tests (17 tests)
├── test_ast_parser.py          # AST parsing & extraction tests (17 tests)
├── test_page_object_mapper.py  # PageObject mapping tests (15 tests)
├── fixtures/                   # Sample Java test files
│   ├── junit_sample/
│   │   └── LoginTest.java
│   ├── testng_sample/
│   │   └── CheckoutTest.java
│   └── mixed_sample/
│       └── MixedTest.java
└── __init__.py
```

## Test Coverage

### Framework Detection (`test_detector.py`) - 17 tests

**Purpose**: Validate framework detection from Maven/Gradle build files and Java source code.

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestFrameworkDetectionFromPom` | 4 | JUnit 4/5, TestNG, mixed frameworks from pom.xml |
| `TestFrameworkDetectionFromGradle` | 2 | JUnit, TestNG from build.gradle |
| `TestFrameworkDetectionFromSource` | 2 | Framework detection from Java imports |
| `TestEdgeCases` | 6 | Empty/malformed files, missing directories |
| `TestDetectionContract` | 3 | Return type, naming, empty results |

**Key Tests**:
- ✅ Detect JUnit Jupiter (JUnit 5) from pom.xml
- ✅ Detect JUnit 4 from pom.xml
- ✅ Detect TestNG from pom.xml
- ✅ Detect mixed frameworks (migration scenarios)
- ✅ Handle malformed XML gracefully
- ✅ Contract stability (returns `set`, lowercase names)

### AST Parsing & Extraction (`test_ast_parser.py`) - 17 tests

**Purpose**: Validate test extraction from Java source files using AST parsing.

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestJUnit5Extraction` | 2 | JUnit 5 test methods and @Tag annotations |
| `TestTestNGExtraction` | 2 | TestNG test methods and groups |
| `TestJUnit4Extraction` | 1 | JUnit 4 test methods |
| `TestPageObjectDetection` | 2 | PageObject reference detection (placeholder) |
| `TestEdgeCases` | 4 | Empty files, invalid Java, non-test directories |
| `TestMockedJavaParser` | 2 | Mocked extraction without external dependencies |
| `TestContractStability` | 4 | TestMetadata contract validation |

**Key Tests**:
- ✅ Extract JUnit 5 test methods (testValidLogin, testInvalidLogin)
- ✅ Extract TestNG test methods with groups
- ✅ Handle invalid Java files without crashing
- ✅ Mock extraction for fast CI-safe tests
- ✅ Contract stability (TestMetadata attributes)

### PageObject Mapping (`test_page_object_mapper.py`) - 15 tests

**Purpose**: Validate PageObject → Test mapping for impact analysis.

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestBasicPageObjectMapping` | 3 | Single/multiple PageObjects per test |
| `TestMultipleTestsMapping` | 2 | Tests sharing PageObjects |
| `TestReverseMapping` | 1 | PageObject → Tests reverse mapping |
| `TestImpactAnalysis` | 1 | Impact analysis when PageObject changes |
| `TestEdgeCases` | 3 | Empty, None, duplicate PageObjects |
| `TestContractStability` | 4 | Mapping output format validation |
| `TestRealWorldScenarios` | 2 | E2E checkout flow, real-world impact |

**Key Tests**:
- ✅ Map test → PageObjects (LoginTest.testValidLogin → {LoginPage})
- ✅ Reverse mapping (LoginPage → {LoginTest.testValidLogin, LoginTest.testInvalidLogin})
- ✅ Impact analysis (CartPage changed → 3 tests impacted)
- ✅ Handle None/empty PageObjects gracefully
- ✅ Contract stability (dict[str, set[str]])

## Running Tests

### Run all extractor tests
```bash
pytest tests/unit/adapters/java/ -v
```

### Run specific test file
```bash
pytest tests/unit/adapters/java/test_detector.py -v
pytest tests/unit/adapters/java/test_ast_parser.py -v
pytest tests/unit/adapters/java/test_page_object_mapper.py -v
```

### Run with coverage
```bash
pytest tests/unit/adapters/java/ --cov=adapters.selenium_java --cov-report=html
```

### CI-friendly run (fast, no warnings)
```bash
pytest tests/unit/adapters/java/ --disable-warnings --maxfail=1 -q
```

## Test Philosophy

### ✅ DO

- **Pure function testing**: Extractors are stateless parsers
- **Mock external dependencies**: Use `@patch` for JavaParser/file system
- **Test edge cases**: Empty files, malformed input, None values
- **Contract testing**: Validate output schema stability
- **Fast tests**: < 1 second total for all 49 tests
- **Deterministic tests**: Use `tmp_path` fixture for filesystem

### ❌ DON'T

- Test Selenium execution (that's the runner's job)
- Test Maven/Gradle correctness (we delegate to them)
- Test JavaParser itself (external dependency)
- Use real file system without `tmp_path`
- Make tests depend on external tools in CI

## Test Data (Fixtures)

### JUnit 5 Sample (`junit_sample/LoginTest.java`)
- 3 test methods with @Tag annotations
- PageObject references (LoginPage, DashboardPage)
- Smoke and regression tags

### TestNG Sample (`testng_sample/CheckoutTest.java`)
- 3 test methods with groups
- PageObject references (CartPage, CheckoutPage, ConfirmationPage)
- Smoke, critical, and regression groups

### Mixed Sample (`mixed_sample/MixedTest.java`)
- Both JUnit 5 and TestNG tests
- Represents migration scenarios
- Multiple PageObject references

## Contract Guarantees

### Framework Detection
```python
detect_all_frameworks(project_root, source_root) -> set[str]
```
- Returns: `{"junit5"}`, `{"testng"}`, or `{"junit5", "testng"}`
- Never returns `None`
- Framework names are lowercase
- Empty result = `set()`

### Test Extraction
```python
extractor.extract_tests() -> list[TestMetadata]
```
- Returns: List of `TestMetadata` objects
- Never returns `None`
- Empty result = `[]`
- Each `TestMetadata` has: framework, test_name, file_path, tags, test_type, language

### PageObject Mapping
```python
mapping: dict[str, set[str]]
```
- Key: Test ID (ClassName.methodName)
- Value: Set of PageObject names
- Empty PageObjects = `set()`
- Never returns `None`

## Performance

All 49 tests complete in **< 1 second**:

```
=============== 49 passed, 1 warning in 0.42s ===============
```

- Fast enough for pre-commit hooks
- CI-safe (no external dependencies)
- Deterministic (no flaky tests)

## Test Maintenance

When adding new features:

1. **Add test for happy path** (e.g., `test_detect_new_framework`)
2. **Add edge case test** (e.g., `test_malformed_new_config`)
3. **Add contract test** (e.g., `test_new_api_returns_expected_type`)
4. **Update fixtures** if needed (e.g., new Java sample)
5. **Run full suite** to ensure no regressions

## Integration with Existing Tests

These extractor tests complement existing test suites:

- `tests/unit/test_java_detection.py` (28 tests) - Integration tests
- `tests/unit/test_java_impact.py` (14 tests) - Impact analysis
- `tests/unit/test_selenium_runner.py` (26 tests) - Runner adapter
- **Total: 49 + 68 = 117 tests** for Java adapter

## Contributing

When contributing tests:

1. Follow naming: `test_<component>_<scenario>`
2. Use descriptive docstrings
3. Mock external dependencies
4. Test both success and failure paths
5. Add contract tests for public APIs
6. Keep tests fast (<100ms each)

## See Also

- [Selenium Java Runner Documentation](../../../docs/selenium-java-runner.md)
- [Test Discovery Documentation](../../../docs/java-test-discovery.md)
- [Impact Analysis Documentation](../../../docs/java-impact-analysis.md)
