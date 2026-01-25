"""
Comprehensive unit tests for Pytest Indirect Fixture Extractor.
"""

import pytest
from pathlib import Path
from adapters.selenium_pytest.indirect_fixture_extractor import PytestIndirectFixtureExtractor


@pytest.fixture
def extractor():
    return PytestIndirectFixtureExtractor()


@pytest.fixture
def test_file_with_indirect(tmp_path):
    """Create test file with indirect parametrization."""
    test_file = tmp_path / "test_indirect.py"
    test_file.write_text("""
import pytest

@pytest.fixture
def user_data(request):
    # Fixture receives parameter indirectly
    user_type = request.param
    if user_type == "admin":
        return {"username": "admin", "role": "admin"}
    elif user_type == "user":
        return {"username": "user1", "role": "user"}
    return {"username": "guest", "role": "guest"}

@pytest.mark.parametrize("user_data", ["admin", "user", "guest"], indirect=True)
def test_user_access(user_data):
    assert user_data['username']
    assert user_data['role']

@pytest.fixture
def db_connection(request):
    db_type = request.param
    connection = create_connection(db_type)
    yield connection
    connection.close()

@pytest.mark.parametrize("db_connection", ["mysql", "postgres"], indirect=True)
def test_database_query(db_connection):
    result = db_connection.query("SELECT 1")
    assert result

@pytest.fixture
def browser(request):
    browser_name = request.param
    driver = WebDriver(browser_name)
    yield driver
    driver.quit()

@pytest.fixture
def viewport(request):
    return request.param

@pytest.mark.parametrize("browser,viewport", [
    ("chrome", "1920x1080"),
    ("firefox", "1366x768"),
    ("safari", "1440x900")
], indirect=["browser", "viewport"])
def test_responsive_design(browser, viewport):
    browser.set_window_size(viewport)
    assert browser.current_window_size == viewport
    """)
    return test_file


@pytest.fixture
def test_file_indirect_all(tmp_path):
    """Create test file with indirect=True for all parameters."""
    test_file = tmp_path / "test_indirect_all.py"
    test_file.write_text("""
import pytest

@pytest.fixture
def param1(request):
    return request.param * 2

@pytest.fixture
def param2(request):
    return request.param + 10

@pytest.mark.parametrize("param1,param2", [(1, 2), (3, 4), (5, 6)], indirect=True)
def test_with_all_indirect(param1, param2):
    assert param1 > 0
    assert param2 > 0
    """)
    return test_file


class TestIndirectFixtureDetection:
    """Test detection of indirect fixtures."""
    
    def test_detect_indirect_single_param(self, extractor, test_file_with_indirect):
        """Test detection of single indirect parameter."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        assert len(fixtures) >= 2
        
        # Find the user_data test
        user_test = next((f for f in fixtures if 'user_access' in f.test_name), None)
        assert user_test is not None
        assert user_test.indirect_params == ['user_data']
    
    def test_detect_indirect_multiple_params(self, extractor, test_file_with_indirect):
        """Test detection of multiple indirect parameters."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        # Find the responsive design test
        responsive_test = next((f for f in fixtures if 'responsive_design' in f.test_name), None)
        assert responsive_test is not None
        assert 'browser' in responsive_test.indirect_params
        assert 'viewport' in responsive_test.indirect_params
    
    def test_detect_indirect_all(self, extractor, test_file_indirect_all):
        """Test detection when indirect=True (all params)."""
        fixtures = extractor.extract_indirect_parametrize(test_file_indirect_all)
        
        assert len(fixtures) > 0
        fixture = fixtures[0]
        assert fixture.is_indirect_all is True
        assert 'param1' in fixture.indirect_params
        assert 'param2' in fixture.indirect_params


class TestFixtureExtraction:
    """Test fixture definition extraction."""
    
    def test_extract_fixture_definitions(self, extractor, test_file_with_indirect):
        """Test extraction of fixture definitions."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        user_test = next((f for f in fixtures if 'user_access' in f.test_name), None)
        assert user_test is not None
        
        # Check fixture definition is found
        assert 'user_data' in user_test.fixture_definitions
        fixture_def = user_test.fixture_definitions['user_data']
        assert 'request.param' in fixture_def
    
    def test_fixture_with_yield(self, extractor, test_file_with_indirect):
        """Test fixture with yield statement."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        db_test = next((f for f in fixtures if 'database_query' in f.test_name), None)
        assert db_test is not None
        
        fixture_def = db_test.fixture_definitions.get('db_connection', '')
        assert 'yield' in fixture_def
    
    def test_fixture_with_cleanup(self, extractor, test_file_with_indirect):
        """Test fixture with cleanup logic."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        browser_test = next((f for f in fixtures if 'responsive_design' in f.test_name), None)
        assert browser_test is not None
        
        fixture_def = browser_test.fixture_definitions.get('browser', '')
        assert 'quit' in fixture_def.lower() or 'close' in fixture_def.lower()


class TestParameterValues:
    """Test parameter value extraction."""
    
    def test_extract_parameter_values_list(self, extractor, test_file_with_indirect):
        """Test extraction of parameter values from list."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        user_test = next((f for f in fixtures if 'user_access' in f.test_name), None)
        assert user_test is not None
        
        values = user_test.parameter_values
        assert len(values) == 3
        assert ["admin"] in values or ("admin",) in values
        assert ["user"] in values or ("user",) in values
        assert ["guest"] in values or ("guest",) in values
    
    def test_extract_parameter_values_tuples(self, extractor, test_file_with_indirect):
        """Test extraction of parameter values from tuples."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        responsive_test = next((f for f in fixtures if 'responsive_design' in f.test_name), None)
        assert responsive_test is not None
        
        values = responsive_test.parameter_values
        assert len(values) == 3
        # Each value should be a tuple with 2 elements
        assert all(len(v) == 2 for v in values)


class TestRobotFrameworkConversion:
    """Test conversion to Robot Framework format."""
    
    def test_convert_simple_indirect_to_robot(self, extractor, test_file_with_indirect):
        """Test conversion of simple indirect fixture to Robot Framework."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        user_test = next((f for f in fixtures if 'user_access' in f.test_name), None)
        robot_code = extractor.convert_to_robot_keyword(user_test)
        
        assert "*** Keywords ***" in robot_code or "*** Test Cases ***" in robot_code
        assert "admin" in robot_code
        assert "user" in robot_code
        assert "guest" in robot_code
    
    def test_convert_multiple_params_to_robot(self, extractor, test_file_with_indirect):
        """Test conversion of multiple indirect params to Robot Framework."""
        fixtures = extractor.extract_indirect_parametrize(test_file_with_indirect)
        
        responsive_test = next((f for f in fixtures if 'responsive_design' in f.test_name), None)
        robot_code = extractor.convert_to_robot_keyword(responsive_test)
        
        assert robot_code is not None
        assert "chrome" in robot_code or "firefox" in robot_code


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_no_indirect_fixtures(self, extractor, tmp_path):
        """Test file with no indirect fixtures."""
        test_file = tmp_path / "test_regular.py"
        test_file.write_text("""
import pytest

@pytest.mark.parametrize("value", [1, 2, 3])
def test_regular(value):
    assert value > 0
        """)
        
        fixtures = extractor.extract_indirect_parametrize(test_file)
        assert len(fixtures) == 0
    
    def test_indirect_false_explicit(self, extractor, tmp_path):
        """Test indirect=False explicitly set."""
        test_file = tmp_path / "test_false.py"
        test_file.write_text("""
import pytest

@pytest.mark.parametrize("value", [1, 2, 3], indirect=False)
def test_not_indirect(value):
    assert value > 0
        """)
        
        fixtures = extractor.extract_indirect_parametrize(test_file)
        assert len(fixtures) == 0
    
    def test_missing_fixture_definition(self, extractor, tmp_path):
        """Test indirect fixture without definition in file."""
        test_file = tmp_path / "test_missing.py"
        test_file.write_text("""
import pytest

# Fixture defined elsewhere (conftest.py)
@pytest.mark.parametrize("external_fixture", ["a", "b"], indirect=True)
def test_with_external_fixture(external_fixture):
    assert external_fixture
        """)
        
        fixtures = extractor.extract_indirect_parametrize(test_file)
        assert len(fixtures) > 0
        # Should still extract even without definition
        assert fixtures[0].test_name == "test_with_external_fixture"
    
    def test_nonexistent_file(self, extractor, tmp_path):
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / "doesnt_exist.py"
        
        fixtures = extractor.extract_indirect_parametrize(nonexistent)
        assert len(fixtures) == 0
    
    def test_invalid_python_file(self, extractor, tmp_path):
        """Test handling of invalid Python file."""
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("This is not valid Python code {{{")
        
        fixtures = extractor.extract_indirect_parametrize(invalid_file)
        assert len(fixtures) == 0


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_indirect_with_ids(self, extractor, tmp_path):
        """Test indirect parametrization with custom IDs."""
        test_file = tmp_path / "test_ids.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def config(request):
    return load_config(request.param)

@pytest.mark.parametrize("config", ["dev", "staging", "prod"], 
                         indirect=True,
                         ids=["development", "staging", "production"])
def test_environment(config):
    assert config.is_valid()
        """)
        
        fixtures = extractor.extract_indirect_parametrize(test_file)
        assert len(fixtures) > 0
        
        fixture = fixtures[0]
        assert fixture.test_name == "test_environment"
        assert len(fixture.parameter_values) == 3
    
    def test_nested_indirect_fixtures(self, extractor, tmp_path):
        """Test nested indirect fixtures."""
        test_file = tmp_path / "test_nested.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def database(request):
    return Database(request.param)

@pytest.fixture
def user(request, database):
    return database.get_user(request.param)

@pytest.mark.parametrize("database,user", [
    ("mysql", "admin"),
    ("postgres", "user")
], indirect=True)
def test_user_operations(database, user):
    assert user in database
        """)
        
        fixtures = extractor.extract_indirect_parametrize(test_file)
        assert len(fixtures) > 0
        
        fixture = fixtures[0]
        assert 'database' in fixture.indirect_params
        assert 'user' in fixture.indirect_params
    
    def test_indirect_with_marks(self, extractor, tmp_path):
        """Test indirect fixtures with other pytest marks."""
        test_file = tmp_path / "test_marks.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def browser(request):
    return WebDriver(request.param)

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.parametrize("browser", ["chrome", "firefox"], indirect=True)
def test_cross_browser(browser):
    assert browser.is_available()
        """)
        
        fixtures = extractor.extract_indirect_parametrize(test_file)
        assert len(fixtures) > 0
        
        fixture = fixtures[0]
        assert fixture.test_name == "test_cross_browser"
    
    def test_indirect_mixed_params(self, extractor, tmp_path):
        """Test mix of indirect and non-indirect parameters."""
        test_file = tmp_path / "test_mixed.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def browser(request):
    return WebDriver(request.param)

@pytest.mark.parametrize("browser,url,expected", [
    ("chrome", "http://example.com", 200),
    ("firefox", "http://test.com", 200)
], indirect=["browser"])
def test_mixed_params(browser, url, expected):
    response = browser.get(url)
    assert response.status_code == expected
        """)
        
        fixtures = extractor.extract_indirect_parametrize(test_file)
        assert len(fixtures) > 0
        
        fixture = fixtures[0]
        assert fixture.indirect_params == ['browser']
        assert not fixture.is_indirect_all
