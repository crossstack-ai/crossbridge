# Testing Guide for Impact Mapping

## Overview

Unit tests for Page Object → Test impact mapping system covering:
- Pytest impact mapper (14 tests)
- Java/Selenium impact mapper (14 tests)
- Robot Framework impact mapper (14 tests)
- Unified data model (21 tests)
- Database persistence layer (16 tests)

**Total Test Count: 79 impact mapping tests**

## Test Files

### 1. [test_pytest_impact.py](tests/unit/test_pytest_impact.py)
Tests pytest-specific Page Object detection and mapping.

**Coverage: 14 tests**

#### Test Classes

**TestPytestPageObjectDetector** (5 tests)
- `test_detect_page_object_by_name`: Detects classes ending with "Page"
- `test_detect_page_object_by_base_class`: Detects classes inheriting from BasePage
- `test_detect_multiple_page_objects`: Finds multiple POs in same file
- `test_no_page_objects_directory`: Handles missing pages directory
- `test_alternative_page_directory`: Finds POs in src/pages, tests/pages

**TestPytestTestToPageObjectMapper** (5 tests)
- `test_detect_page_object_fixture`: Detects PO via fixture params (`login_page`)
- `test_detect_page_object_instantiation`: Detects PO via `LoginPage()` calls
- `test_detect_multiple_page_objects_in_test`: Maps test using multiple POs
- `test_multiple_tests_in_file`: Handles multiple tests per file
- `test_no_page_objects_used`: Skips tests without PO usage

**TestCreatePytestImpactMap** (3 tests)
- `test_create_complete_impact_map`: End-to-end impact map creation
- `test_impact_map_serialization`: JSON serialization/deserialization
- `test_unified_model_format`: Conversion to unified {test_id, page_object, source, confidence}

**End-to-End** (1 test)
- `test_end_to_end_pytest_impact`: Complete workflow with realistic project

### 2. [test_java_impact.py](tests/unit/test_java_impact.py)
Tests Java/Selenium Page Object detection and mapping.

**Coverage: 14 tests**

#### Test Classes

**TestJavaPageObjectDetector** (5 tests)
- `test_detect_page_object_by_name`: Detects classes ending with "Page"
- `test_detect_page_object_by_base_class`: Detects classes extending BasePage
- `test_detect_multiple_page_objects`: Finds multiple POs including package detection
- `test_no_page_objects_directory`: Handles missing pages directory
- `test_package_detection`: Detects POs via "pages" package membership

**TestJavaTestToPageObjectMapper** (5 tests)
- `test_detect_page_object_import`: Detects PO via import statements
- `test_detect_page_object_instantiation`: Detects PO via `new LoginPage()` calls
- `test_detect_multiple_page_objects_in_test`: Maps test using multiple POs
- `test_multiple_tests_in_class`: Handles multiple @Test methods per class
- `test_no_page_objects_used`: Skips tests without PO usage

**TestCreateJavaImpactMap** (3 tests)
- `test_create_complete_impact_map`: End-to-end impact map creation
- `test_impact_map_serialization`: JSON serialization/deserialization
- `test_unified_model_format`: Conversion to unified {test_id, page_object, source, confidence}

**End-to-End** (1 test)
- `test_end_to_end_java_impact`: Complete workflow with realistic Java project

### 3. [test_robot_impact.py](tests/unit/test_robot_impact.py)
Tests Robot Framework Page Object detection and mapping.

**Coverage: 14 tests**

#### Test Classes

**TestRobotPageObjectDetector** (5 tests)
- `test_detect_page_object_by_name`: Detects .robot files with "Page" in name
- `test_detect_page_object_resource_file`: Detects .resource files with "Page"
- `test_detect_multiple_page_objects`: Finds multiple PO resources
- `test_no_page_objects_directory`: Handles missing pages directory
- `test_alternative_directory`: Finds POs in resources/pages, keywords/

**TestRobotTestToPageObjectMapper** (5 tests)
- `test_detect_page_object_import`: Detects PO via Resource imports
- `test_detect_page_object_keyword_usage`: Detects PO keyword calls in tests
- `test_detect_multiple_page_objects_in_test`: Maps test using multiple POs
- `test_multiple_tests_in_file`: Handles multiple test cases per file
- `test_no_page_objects_used`: Skips tests without PO usage

**TestCreateRobotImpactMap** (3 tests)
- `test_create_complete_impact_map`: End-to-end impact map creation
- `test_impact_map_serialization`: JSON serialization/deserialization
- `test_unified_model_format`: Conversion to unified {test_id, page_object, source, confidence}

**End-to-End** (1 test)
- `test_end_to_end_robot_impact`: Complete workflow with realistic Robot project

### 4. [test_unified_model.py](tests/unit/test_unified_model.py)
Tests unified data model format and multi-phase support.

**Coverage: 21 tests**

#### Test Classes

**TestUnifiedModelConversion** (4 tests)
- `test_mapping_to_unified_model_basic`: Basic conversion
- `test_mapping_to_unified_model_different_sources`: All source types (static_ast, coverage, ai)
- `test_mapping_to_unified_model_confidence_range`: Confidence values 0.0-1.0
- `test_mapping_to_unified_model_multiple_page_objects`: Multiple POs per test

**TestMappingSourceEnum** (2 tests)
- `test_mapping_source_values`: Enum value verification
- `test_mapping_source_phase_alignment`: Release Stage/2/3 source alignment

**TestPageObjectReference** (3 tests)
- `test_reference_creation`: Reference data class
- `test_reference_simple_name`: Qualified to simple name conversion
- `test_reference_simple_name_already_simple`: Simple name extraction

**TestTestToPageObjectMapping** (5 tests)
- `test_mapping_creation`: Mapping creation
- `test_add_page_object`: Adding PO references
- `test_get_page_object_count`: Counting unique POs
- `test_to_dict_serialization`: Dictionary serialization

**TestPageObjectImpactMap** (4 tests)
- `test_impact_map_creation`: Map initialization
- `test_add_mapping`: Adding mappings
- `test_get_impacted_tests`: Querying impacted tests
- `test_get_statistics`: Statistics generation

**TestMultiPhaseCompatibility** (3 tests)
- `test_static_ast_phase`: Release Stage static analysis
- `test_coverage_phase`: Release Stage code coverage
- `test_ai_phase`: Release Stage AI inference
- `test_multiple_phases_same_mapping`: Same mapping from different sources

### 5. [test_db_models.py](tests/unit/test_db_models.py)
Tests database persistence with PostgreSQL/SQLite.

**Coverage: 16 tests** (requires SQLAlchemy)

#### Test Classes

**TestDatabaseModels** (5 tests)
- `test_create_page_object`: Create PO entity
- `test_create_test_case`: Create test entity
- `test_create_mapping`: Create test-PO mapping
- `test_update_existing_page_object`: Update existing PO
- `test_update_mapping_confidence`: Update mapping to max confidence

**TestDatabaseQueries** (5 tests)
- `test_get_impacted_tests`: Query tests impacted by PO change
- `test_get_impacted_tests_with_min_confidence`: Confidence filtering
- `test_get_page_objects_for_test`: Query POs used by test
- `test_get_mappings_by_source`: Query by source type
- `test_get_statistics`: Database statistics

**TestUnifiedModelFormat** (3 tests)
- `test_unified_model_format`: Conversion to unified format
- `test_model_to_dict`: Model serialization
- `test_mapping_to_unified_model`: Mapping format conversion

**TestMultiPhaseSupport** (2 tests)
- `test_multiple_sources_for_same_mapping`: Store same mapping from multiple phases
- `test_query_by_source_phase`: Query mappings by phase

**Other** (1 test)
- `test_missing_sqlalchemy`: Graceful handling without SQLAlchemy

## Running Tests

### Run All Impact Tests
```bash
# All framework impact mappers (pytest, Java, Robot)
pytest tests/unit/test_pytest_impact.py tests/unit/test_java_impact.py tests/unit/test_robot_impact.py -v

# All impact tests including unified model and database
pytest tests/unit/test_pytest_impact.py tests/unit/test_java_impact.py tests/unit/test_robot_impact.py tests/unit/test_unified_model.py tests/unit/test_db_models.py -v
```

### Run Framework-Specific Tests
```bash
# Pytest impact mapper only
pytest tests/unit/test_pytest_impact.py -v

# Java/Selenium impact mapper only
pytest tests/unit/test_java_impact.py -v

# Robot Framework impact mapper only
pytest tests/unit/test_robot_impact.py -v
```

### Run Specific Test Class
```bash
pytest tests/unit/test_pytest_impact.py::TestPytestPageObjectDetector -v
pytest tests/unit/test_java_impact.py::TestJavaTestToPageObjectMapper -v
pytest tests/unit/test_robot_impact.py::TestRobotPageObjectDetector -v
```

### Run With Coverage
```bash
pytest tests/unit/ --cov=adapters --cov-report=html
```

### Database Tests Only
```bash
# Requires: pip install sqlalchemy
pytest tests/unit/test_db_models.py -v
```

## Test Results

**Total Tests:** 79 impact mapping tests
- ✅ 79 passed (when SQLAlchemy installed)
- ✅ 63 passed, ⏭️ 16 skipped (without SQLAlchemy)

**Success Rate: 100%**

## Test Coverage

### Modules Tested
1. **adapters/pytest/impact_mapper.py**
   - PytestPageObjectDetector
   - PytestTestToPageObjectMapper
   - create_pytest_impact_map()

2. **adapters/java/impact_mapper.py**
   - JavaPageObjectDetector
   - JavaTestToPageObjectMapper
   - create_impact_map()

3. **adapters/robot/impact_mapper.py**
   - RobotPageObjectDetector
   - RobotTestToPageObjectMapper
   - create_robot_impact_map()

4. **adapters/common/impact_models.py**
   - MappingSource enum
   - PageObjectReference
   - TestToPageObjectMapping
   - PageObjectImpactMap
   - Unified model conversion

5. **adapters/common/db_models.py**
   - PageObjectModel, TestCaseModel, TestPageMappingModel
   - DatabaseManager CRUD operations
   - Impact queries
   - Multi-phase support

## Test Fixtures

### sample_project
Creates realistic pytest project structure:
```
tmp_path/
├── pages/
│   ├── login.py (LoginPage)
│   └── home.py (HomePage)
└── tests/
    ├── test_auth.py (test_valid_login, test_invalid_login)
    └── test_navigation.py (test_navigate)
```

### db_manager
Creates in-memory SQLite database for testing.

### populated_db
Database pre-populated with sample Page Objects, tests, and mappings.

## Key Test Scenarios

### Framework Coverage Summary

| Framework | Detection Tests | Mapping Tests | Pipeline Tests | Total |
|-----------|----------------|---------------|----------------|-------|
| Pytest | 5 | 5 | 4 | 14 |
| Java/Selenium | 5 | 5 | 4 | 14 |
| Robot Framework | 5 | 5 | 4 | 14 |
| Unified Model | - | - | 21 | 21 |
| Database | - | - | 16 | 16 |
| **TOTAL** | **15** | **15** | **49** | **79** |

### Page Object Detection
- **Pytest:**
  - Name-based: Classes ending with "Page"
  - Inheritance-based: Classes extending BasePage
  - Directory-based: pages/, src/pages/
  
- **Java:**
  - Name-based: Classes ending with "Page"
  - Inheritance-based: Classes extending BasePage
  - Package-based: Classes in "pages" package
  
- **Robot:**
  - File-based: .robot/.resource files with "Page" in name
  - Keyword extraction: From `*** Keywords ***` sections
  - Directory-based: pages/, resources/pages/, keywords/

### Test-to-PO Mapping

- **Pytest:**
  - Fixture parameters: `def test_login(login_page)`
  - Instantiations: `page = LoginPage(driver)`
  - Multiple POs per test
  
- **Java:**
  - Import detection: `import com.example.pages.LoginPage;`
  - Instantiations: `LoginPage page = new LoginPage(driver);`
  - Multiple POs per test class
  
- **Robot:**
  - Resource imports: `Resource    pages/LoginPage.robot`
  - Keyword usage: Calling keywords defined in Page Objects
  - Multiple POs per test case
- Multiple tests per file

### Database Operations
- CRUD for Page Objects, Tests, Mappings
- Impact queries with confidence filtering
- Multi-source mappings (static_ast, coverage, ai)
- Statistics and analytics

### Unified Model Format
```python
{
  "test_id": "LoginTest.testValidLogin",
  "page_object": "LoginPage",
  "source": "static_ast",
  "confidence": 0.85
}
```

## Adding New Tests

### For New Detectors
```python
def test_new_detection_method(self, tmp_path):
    # Setup test files
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    
    # Create test file
    (pages_dir / "page.py").write_text("""
class MyPage:
    pass
""")
    
    # Test detection
    detector = PytestPageObjectDetector(str(pages_dir))
    page_objects = detector.detect_page_objects()
    
    assert len(page_objects) == 1
    assert page_objects[0].class_name == "pages.page.MyPage"
```

### For New Mapping Sources
```python
def test_new_source_type(self):
    mapping = TestToPageObjectMapping(
        test_id="Test.test",
        test_file="test.py",
        mapping_source=MappingSource.NEW_SOURCE,
        confidence=0.9
    )
    
    unified = mapping.to_unified_model("Page")
    assert unified["source"] == "new_source"
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Run Impact Mapping Tests
  run: |
    pip install sqlalchemy
    pytest tests/unit/test_*impact*.py tests/unit/test_unified_model.py tests/unit/test_db_models.py -v --cov
```

## Troubleshooting

### SQLAlchemy Not Found
```bash
pip install sqlalchemy
# Database tests will be skipped without it
```

### Coverage Not Working
```bash
# Use source paths
pytest --cov=adapters --cov-report=term-missing
```

### ResourceWarnings
Database connections in tests - expected with in-memory SQLite, doesn't affect test results.
