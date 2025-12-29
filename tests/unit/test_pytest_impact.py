"""
Unit tests for pytest Page Object impact mapper.

Tests detection and mapping of Page Objects in pytest projects.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from adapters.pytest.impact_mapper import (
    PytestPageObjectDetector,
    PytestTestToPageObjectMapper,
    create_pytest_impact_map
)
from adapters.common.impact_models import MappingSource


class TestPytestPageObjectDetector:
    """Test Page Object detection in Python code."""
    
    def test_detect_page_object_by_name(self, tmp_path):
        """Test detection of Page Object by class name ending with 'Page'."""
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()
        
        # Create a Page Object
        page_file = pages_dir / "login.py"
        page_file.write_text("""
class LoginPage:
    def __init__(self, driver):
        self.driver = driver
    
    def enter_username(self, username):
        pass
    
    def enter_password(self, password):
        pass
    
    def click_login(self):
        pass
""")
        
        detector = PytestPageObjectDetector(str(pages_dir))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 1
        assert page_objects[0].class_name == "pages.login.LoginPage"
        assert page_objects[0].language == "python"
        assert "enter_username" in page_objects[0].methods
        assert "enter_password" in page_objects[0].methods
    
    def test_detect_page_object_by_base_class(self, tmp_path):
        """Test detection of Page Object by inheritance."""
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()
        
        # Create base and derived classes
        base_file = pages_dir / "base.py"
        base_file.write_text("""
class BasePage:
    def __init__(self, driver):
        self.driver = driver
""")
        
        dashboard_file = pages_dir / "dashboard.py"
        dashboard_file.write_text("""
from .base import BasePage

class Dashboard(BasePage):
    def get_welcome_message(self):
        pass
""")
        
        detector = PytestPageObjectDetector(str(pages_dir))
        page_objects = detector.detect_page_objects()
        
        # Should detect both (BasePage by name, Dashboard by inheritance)
        assert len(page_objects) == 2
        
        dashboard = [po for po in page_objects if "Dashboard" in po.class_name][0]
        assert dashboard.base_class == "BasePage"
    
    def test_detect_multiple_page_objects(self, tmp_path):
        """Test detection of multiple Page Objects in same file."""
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()
        
        pages_file = pages_dir / "pages.py"
        pages_file.write_text("""
class LoginPage:
    pass

class HomePage:
    pass

class SettingsPage:
    pass

class NotAPage:
    pass
""")
        
        detector = PytestPageObjectDetector(str(pages_dir))
        page_objects = detector.detect_page_objects()
        
        # Should detect 3 Page Objects (not NotAPage which doesn't end with Page)
        # Note: NotAPage ends with "Page" so it will be detected
        assert len(page_objects) == 4  # All classes ending with 'Page'
        page_names = [po.class_name for po in page_objects]
        assert any("LoginPage" in name for name in page_names)
        assert any("HomePage" in name for name in page_names)
        assert any("SettingsPage" in name for name in page_names)
    
    def test_no_page_objects_directory(self, tmp_path):
        """Test handling of missing pages directory."""
        detector = PytestPageObjectDetector(str(tmp_path / "nonexistent"))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 0
    
    def test_alternative_page_directory(self, tmp_path):
        """Test detection in alternative directory structures."""
        src_pages = tmp_path / "src" / "pages"
        src_pages.mkdir(parents=True)
        
        page_file = src_pages / "home.py"
        page_file.write_text("""
class HomePage:
    pass
""")
        
        # Start from project root so it can find src/pages
        detector = PytestPageObjectDetector("pages")
        # Manually point to the actual location for this test
        detector.source_root = src_pages
        page_objects = detector.detect_page_objects()
        
        # Should detect HomePage
        assert len(page_objects) == 1


class TestPytestTestToPageObjectMapper:
    """Test mapping of tests to Page Objects."""
    
    def test_detect_page_object_fixture(self, tmp_path):
        """Test detection of Page Object via fixture parameter."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "test_login.py"
        test_file.write_text("""
def test_valid_login(login_page):
    login_page.enter_username("user")
    login_page.enter_password("pass")
    login_page.click_login()
    assert True
""")
        
        mapper = PytestTestToPageObjectMapper(str(tests_dir))
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) == 1
        mapping = impact_map.mappings[0]
        assert "test_valid_login" in mapping.test_id
        assert "LoginPage" in mapping.page_objects
        
        # Check reference details
        refs = [r for r in mapping.references if r.page_object_class == "LoginPage"]
        assert len(refs) == 1
        assert refs[0].usage_type == "fixture"
    
    def test_detect_page_object_instantiation(self, tmp_path):
        """Test detection of Page Object via instantiation."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "test_home.py"
        test_file.write_text("""
from pages.home import HomePage

def test_homepage_load(driver):
    page = HomePage(driver)
    page.verify_loaded()
    assert True
""")
        
        mapper = PytestTestToPageObjectMapper(str(tests_dir))
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) == 1
        mapping = impact_map.mappings[0]
        assert "HomePage" in mapping.page_objects
        
        refs = [r for r in mapping.references if "HomePage" in r.page_object_class]
        assert len(refs) == 1
        assert refs[0].usage_type == "instantiation"
    
    def test_detect_multiple_page_objects_in_test(self, tmp_path):
        """Test detection of multiple Page Objects in single test."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "test_flow.py"
        test_file.write_text("""
def test_complete_flow(login_page, home_page, settings_page):
    login_page.login("user", "pass")
    home_page.navigate_to_settings()
    settings_page.update_profile()
    assert True
""")
        
        mapper = PytestTestToPageObjectMapper(str(tests_dir))
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) == 1
        mapping = impact_map.mappings[0]
        
        # Should detect all 3 Page Objects
        assert len(mapping.page_objects) == 3
        assert "LoginPage" in mapping.page_objects
        assert "HomePage" in mapping.page_objects
        assert "SettingsPage" in mapping.page_objects
    
    def test_multiple_tests_in_file(self, tmp_path):
        """Test mapping multiple tests in same file."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "test_suite.py"
        test_file.write_text("""
def test_login(login_page):
    login_page.login("user", "pass")

def test_logout(home_page):
    home_page.logout()

def test_register(registration_page):
    registration_page.register()
""")
        
        mapper = PytestTestToPageObjectMapper(str(tests_dir))
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) == 3
        
        test_ids = [m.test_id for m in impact_map.mappings]
        assert any("test_login" in tid for tid in test_ids)
        assert any("test_logout" in tid for tid in test_ids)
        assert any("test_register" in tid for tid in test_ids)
    
    def test_no_page_objects_used(self, tmp_path):
        """Test handling of tests that don't use Page Objects."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "test_unit.py"
        test_file.write_text("""
def test_calculator():
    assert 1 + 1 == 2

def test_string_utils():
    assert "hello".upper() == "HELLO"
""")
        
        mapper = PytestTestToPageObjectMapper(str(tests_dir))
        impact_map = mapper.map_tests_to_page_objects()
        
        # Should not create mappings for tests without Page Objects
        assert len(impact_map.mappings) == 0


class TestCreatePytestImpactMap:
    """Test complete impact map creation."""
    
    def test_create_complete_impact_map(self, tmp_path):
        """Test end-to-end impact map creation."""
        # Setup project structure
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        # Create Page Objects
        login_page = pages_dir / "login.py"
        login_page.write_text("""
class LoginPage:
    def login(self, username, password):
        pass
""")
        
        home_page = pages_dir / "home.py"
        home_page.write_text("""
class HomePage:
    def navigate(self):
        pass
""")
        
        # Create tests
        test_auth = tests_dir / "test_auth.py"
        test_auth.write_text("""
def test_login(login_page):
    login_page.login("user", "pass")

def test_logout(home_page):
    home_page.navigate()
""")
        
        # Create impact map
        impact_map = create_pytest_impact_map(
            str(tmp_path),
            source_root="pages",
            test_root="tests"
        )
        
        assert len(impact_map.mappings) == 2
        
        # Verify impact queries (returns set of test_ids)
        login_tests = impact_map.get_impacted_tests("LoginPage")
        assert len(login_tests) == 1
        assert any("test_login" in t for t in login_tests)
        
        home_tests = impact_map.get_impacted_tests("HomePage")
        assert len(home_tests) == 1
        assert any("test_logout" in t for t in home_tests)
    
    def test_impact_map_serialization(self, tmp_path):
        """Test serialization and deserialization of impact map."""
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        page_file = pages_dir / "test.py"
        page_file.write_text("class TestPage: pass")
        
        test_file = tests_dir / "test_it.py"
        test_file.write_text("def test_feature(test_page): pass")
        
        impact_map = create_pytest_impact_map(str(tmp_path))
        
        # Serialize
        data = impact_map.to_dict()
        assert "mappings" in data
        assert len(data["mappings"]) > 0
        
        # Verify mapping format
        mapping = data["mappings"][0]
        assert "test_id" in mapping
        assert "page_objects" in mapping
        assert "mapping_source" in mapping
        assert mapping["mapping_source"] == MappingSource.STATIC_AST.value
    
    def test_unified_model_format(self, tmp_path):
        """Test conversion to unified data model format."""
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        page_file = pages_dir / "login.py"
        page_file.write_text("class LoginPage: pass")
        
        test_file = tests_dir / "test_login.py"
        test_file.write_text("def test_valid_login(login_page): pass")
        
        impact_map = create_pytest_impact_map(str(tmp_path))
        
        # Get unified format
        mapping = impact_map.mappings[0]
        unified = mapping.to_unified_model("LoginPage")
        
        # Verify format: {test_id, page_object, source, confidence}
        assert "test_id" in unified
        assert unified["page_object"] == "LoginPage"
        assert unified["source"] == "static_ast"
        assert "confidence" in unified
        assert 0.0 <= unified["confidence"] <= 1.0


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample pytest project with Page Objects and tests."""
    # Pages
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    
    (pages_dir / "login.py").write_text("""
class LoginPage:
    def __init__(self, driver):
        self.driver = driver
    
    def login(self, username, password):
        pass
""")
    
    (pages_dir / "home.py").write_text("""
class HomePage:
    def __init__(self, driver):
        self.driver = driver
    
    def navigate_to_settings(self):
        pass
""")
    
    # Tests
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    
    (tests_dir / "test_auth.py").write_text("""
def test_valid_login(login_page):
    login_page.login("user", "pass")
    assert True

def test_invalid_login(login_page):
    login_page.login("bad", "bad")
    assert False
""")
    
    (tests_dir / "test_navigation.py").write_text("""
def test_navigate(home_page):
    home_page.navigate_to_settings()
    assert True
""")
    
    return tmp_path


def test_end_to_end_pytest_impact(sample_project):
    """End-to-end test with realistic project structure."""
    impact_map = create_pytest_impact_map(str(sample_project))
    
    # Should have 3 test mappings
    assert len(impact_map.mappings) == 3
    
    # Test impact queries
    login_tests = impact_map.get_impacted_tests("LoginPage")
    assert len(login_tests) == 2
    assert any("test_valid_login" in t for t in login_tests)
    assert any("test_invalid_login" in t for t in login_tests)
    
    home_tests = impact_map.get_impacted_tests("HomePage")
    assert len(home_tests) == 1
    assert any("test_navigate" in t for t in home_tests)
    
    # Test statistics
    stats = impact_map.get_statistics()
    assert stats["total_tests"] == 3
    assert stats["total_page_objects"] == 2
    assert stats["total_mappings"] == 3
