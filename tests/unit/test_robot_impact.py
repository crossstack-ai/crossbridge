"""
Unit tests for Robot Framework Page Object impact mapper.

Tests detection and mapping of Page Objects in Robot Framework projects.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from adapters.robot.impact_mapper import (
    RobotPageObjectDetector,
    RobotTestToPageObjectMapper,
    create_robot_impact_map
)
from adapters.common.impact_models import MappingSource


class TestRobotPageObjectDetector:
    """Test Page Object detection in Robot Framework resources."""
    
    def test_detect_page_object_by_name(self, tmp_path):
        """Test detection of Page Object by resource name containing 'Page'."""
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        
        # Create a Page Object resource
        page_file = resources_dir / "LoginPage.robot"
        page_file.write_text("""
*** Settings ***
Documentation    Login Page Object

*** Keywords ***
Enter Username
    [Arguments]    ${username}
    Input Text    id=username    ${username}

Enter Password
    [Arguments]    ${password}
    Input Text    id=password    ${password}

Click Login Button
    Click Button    id=login

Login
    [Arguments]    ${username}    ${password}
    Enter Username    ${username}
    Enter Password    ${password}
    Click Login Button
""")
        
        detector = RobotPageObjectDetector(str(resources_dir))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 1
        assert page_objects[0].class_name == "LoginPage"
        assert page_objects[0].language == "robot"
        assert "Enter Username" in page_objects[0].methods
        assert "Enter Password" in page_objects[0].methods
        assert "Click Login Button" in page_objects[0].methods
    
    def test_detect_page_object_resource_file(self, tmp_path):
        """Test detection of .resource file extension."""
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        
        page_file = resources_dir / "DashboardPage.resource"
        page_file.write_text("""
*** Keywords ***
Get Welcome Message
    ${message}=    Get Text    id=welcome
    RETURN    ${message}

Navigate To Settings
    Click Link    Settings

Logout
    Click Button    Logout
""")
        
        detector = RobotPageObjectDetector(str(resources_dir))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 1
        assert page_objects[0].class_name == "DashboardPage"
        assert len(page_objects[0].methods) >= 3
    
    def test_detect_multiple_page_objects(self, tmp_path):
        """Test detection of multiple Page Objects."""
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        
        # Create multiple Page Objects
        (resources_dir / "LoginPage.robot").write_text("""
*** Keywords ***
Login To Application
    [Arguments]    ${user}    ${pass}
    Input Text    username    ${user}
    Input Text    password    ${pass}
    Click Button    Login
""")
        
        (resources_dir / "HomePage.robot").write_text("""
*** Keywords ***
Verify Home Page Loaded
    Page Should Contain    Welcome
""")
        
        (resources_dir / "SettingsPage.robot").write_text("""
*** Keywords ***
Update Profile
    Click Button    Update
""")
        
        # Create non-Page Object resource
        (resources_dir / "Common.robot").write_text("""
*** Keywords ***
Helper Keyword
    Log    Helper
""")
        
        detector = RobotPageObjectDetector(str(resources_dir))
        page_objects = detector.detect_page_objects()
        
        # Should detect 3 Page Objects (not Common)
        assert len(page_objects) == 3
        page_names = [po.class_name for po in page_objects]
        assert "LoginPage" in page_names
        assert "HomePage" in page_names
        assert "SettingsPage" in page_names
        assert "Common" not in page_names
    
    def test_no_page_objects_directory(self, tmp_path):
        """Test handling of missing resources directory."""
        detector = RobotPageObjectDetector(str(tmp_path / "nonexistent"))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 0
    
    def test_alternative_directory(self, tmp_path):
        """Test detection in alternative directory structures."""
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()
        
        page_file = pages_dir / "HomePage.robot"
        page_file.write_text("""
*** Keywords ***
Navigate
    Click Link    Home
""")
        
        detector = RobotPageObjectDetector("resources")
        detector.source_root = pages_dir
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 1


class TestRobotTestToPageObjectMapper:
    """Test mapping of Robot tests to Page Objects."""
    
    def test_detect_page_object_import(self, tmp_path):
        """Test detection of Page Object via Resource import."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "login_tests.robot"
        test_file.write_text("""
*** Settings ***
Resource    ../resources/LoginPage.robot

*** Test Cases ***
Valid Login
    Login    user@example.com    password123
    Dashboard Should Be Visible
""")
        
        mapper = RobotTestToPageObjectMapper(
            str(tests_dir),
            known_page_objects={"LoginPage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 1
        
        login_test = [m for m in impact_map.mappings if "Valid Login" in m.test_id]
        assert len(login_test) > 0
        assert "LoginPage" in login_test[0].page_objects
    
    def test_detect_page_object_keyword_usage(self, tmp_path):
        """Test detection of Page Object via keyword usage."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "home_tests.robot"
        test_file.write_text("""
*** Settings ***
Resource    ../resources/HomePage.robot

*** Test Cases ***
Homepage Load
    Open Browser    http://example.com    chrome
    HomePage Should Be Loaded
    Verify Welcome Message
""")
        
        mapper = RobotTestToPageObjectMapper(
            str(tests_dir),
            known_page_objects={"HomePage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 1
        
        home_test = [m for m in impact_map.mappings if "Homepage Load" in m.test_id]
        assert len(home_test) > 0
        assert "HomePage" in home_test[0].page_objects
    
    def test_detect_multiple_page_objects_in_test(self, tmp_path):
        """Test detection of multiple Page Objects in single test."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "flow_tests.robot"
        test_file.write_text("""
*** Settings ***
Resource    ../resources/LoginPage.robot
Resource    ../resources/DashboardPage.robot
Resource    ../resources/SettingsPage.robot

*** Test Cases ***
Complete User Flow
    LoginPage.Login    user@example.com    password
    DashboardPage.Navigate To Settings
    SettingsPage.Update Profile
    Verify Profile Updated
""")
        
        mapper = RobotTestToPageObjectMapper(
            str(tests_dir),
            known_page_objects={"LoginPage", "DashboardPage", "SettingsPage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 1
        
        flow_test = [m for m in impact_map.mappings if "Complete User Flow" in m.test_id]
        assert len(flow_test) > 0
        
        # Should detect all 3 Page Objects
        assert len(flow_test[0].page_objects) >= 3
        assert "LoginPage" in flow_test[0].page_objects
        assert "DashboardPage" in flow_test[0].page_objects
        assert "SettingsPage" in flow_test[0].page_objects
    
    def test_multiple_tests_in_file(self, tmp_path):
        """Test mapping multiple tests in same file."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "auth_tests.robot"
        test_file.write_text("""
*** Settings ***
Resource    ../resources/LoginPage.robot
Resource    ../resources/RegistrationPage.robot

*** Test Cases ***
Test Login
    LoginPage.Login    user    pass
    Verify Logged In

Test Logout
    LoginPage.Logout
    Verify Logged Out

Test Register
    RegistrationPage.Register New User    newuser    email@test.com
    Verify Registration Successful
""")
        
        mapper = RobotTestToPageObjectMapper(
            str(tests_dir),
            known_page_objects={"LoginPage", "RegistrationPage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 3
        
        test_ids = [m.test_id for m in impact_map.mappings]
        assert any("Test Login" in tid for tid in test_ids)
        assert any("Test Logout" in tid for tid in test_ids)
        assert any("Test Register" in tid for tid in test_ids)
    
    def test_no_page_objects_used(self, tmp_path):
        """Test handling of tests that don't use Page Objects."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "unit_tests.robot"
        test_file.write_text("""
*** Test Cases ***
Test String Operations
    ${result}=    Catenate    Hello    World
    Should Be Equal    ${result}    Hello World

Test Math Operations
    ${sum}=    Evaluate    1 + 1
    Should Be Equal As Integers    ${sum}    2
""")
        
        mapper = RobotTestToPageObjectMapper(
            str(tests_dir),
            known_page_objects=set()
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        # Should not create mappings for tests without Page Objects
        assert len(impact_map.mappings) == 0


class TestCreateRobotImpactMap:
    """Test complete impact map creation."""
    
    def test_create_complete_impact_map(self, tmp_path):
        """Test end-to-end impact map creation."""
        # Setup project structure
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        # Create Page Objects
        (resources_dir / "LoginPage.robot").write_text("""
*** Keywords ***
Login
    [Arguments]    ${user}    ${pass}
    Input Text    username    ${user}
    Input Text    password    ${pass}
    Click Button    Login
""")
        
        (resources_dir / "HomePage.robot").write_text("""
*** Keywords ***
Navigate
    Click Link    Home
""")
        
        # Create tests
        (tests_dir / "auth_tests.robot").write_text("""
*** Settings ***
Resource    ../resources/LoginPage.robot
Resource    ../resources/HomePage.robot

*** Test Cases ***
Test Login
    LoginPage.Login    user    pass

Test Logout
    HomePage.Navigate
""")
        
        # Create impact map
        impact_map = create_robot_impact_map(str(tmp_path))
        
        assert len(impact_map.mappings) >= 2
        
        # Verify impact queries
        login_tests = impact_map.get_impacted_tests("LoginPage")
        assert len(login_tests) >= 1
        assert any("Test Login" in test for test in login_tests)
        
        home_tests = impact_map.get_impacted_tests("HomePage")
        assert len(home_tests) >= 1
        assert any("Test Logout" in test for test in home_tests)
    
    def test_impact_map_serialization(self, tmp_path):
        """Test serialization and deserialization of impact map."""
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        (resources_dir / "TestPage.robot").write_text("""
*** Keywords ***
Test Keyword
    Log    Test
""")
        
        (tests_dir / "test.robot").write_text("""
*** Settings ***
Resource    ../resources/TestPage.robot

*** Test Cases ***
Test Feature
    TestPage.Test Keyword
""")
        
        impact_map = create_robot_impact_map(str(tmp_path))
        
        # Serialize
        data = impact_map.to_dict()
        assert "mappings" in data
        assert "project_root" in data
        
        # Verify mapping format
        if data["mappings"]:
            mapping = data["mappings"][0]
            assert "test_id" in mapping
            assert "page_objects" in mapping
            assert "mapping_source" in mapping
            assert mapping["mapping_source"] == MappingSource.STATIC_AST.value
    
    def test_unified_model_format(self, tmp_path):
        """Test conversion to unified data model format."""
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        (resources_dir / "LoginPage.robot").write_text("""
*** Keywords ***
Login
    Log    Login
""")
        
        (tests_dir / "login_test.robot").write_text("""
*** Settings ***
Resource    ../resources/LoginPage.robot

*** Test Cases ***
Valid Login Test
    LoginPage.Login
""")
        
        impact_map = create_robot_impact_map(str(tmp_path))
        
        # Get unified format
        if impact_map.mappings:
            mapping = impact_map.mappings[0]
            if mapping.page_objects:
                po = list(mapping.page_objects)[0]
                unified = mapping.to_unified_model(po)
                
                # Verify format: {test_id, page_object, source, confidence}
                assert "test_id" in unified
                assert "page_object" in unified
                assert unified["source"] == "static_ast"
                assert "confidence" in unified
                assert 0.0 <= unified["confidence"] <= 1.0


@pytest.fixture
def sample_robot_project(tmp_path):
    """Create a sample Robot Framework project with Page Objects and tests."""
    # Resources
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir()
    
    (resources_dir / "LoginPage.robot").write_text("""
*** Keywords ***
Login
    [Arguments]    ${username}    ${password}
    Input Text    id=username    ${username}
    Input Text    id=password    ${password}
    Click Button    id=login
""")
    
    (resources_dir / "HomePage.robot").write_text("""
*** Keywords ***
Navigate To Settings
    Click Link    Settings

Verify Welcome Message
    Page Should Contain    Welcome
""")
    
    # Tests
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    
    (tests_dir / "auth_tests.robot").write_text("""
*** Settings ***
Resource    ../resources/LoginPage.robot

*** Test Cases ***
Valid Login
    LoginPage.Login    user@example.com    password123
    Sleep    1s

Invalid Login
    LoginPage.Login    bad@example.com    wrongpass
    Page Should Contain    Error
""")
    
    (tests_dir / "navigation_tests.robot").write_text("""
*** Settings ***
Resource    ../resources/HomePage.robot

*** Test Cases ***
Navigate To Settings
    HomePage.Navigate To Settings
    Page Should Contain    Settings
""")
    
    return tmp_path


def test_end_to_end_robot_impact(sample_robot_project):
    """End-to-end test with realistic Robot Framework project structure."""
    impact_map = create_robot_impact_map(str(sample_robot_project))
    
    # Should have 3 test mappings
    assert len(impact_map.mappings) >= 3
    
    # Test impact queries
    login_tests = impact_map.get_impacted_tests("LoginPage")
    assert len(login_tests) >= 2
    assert any("Valid Login" in t for t in login_tests)
    assert any("Invalid Login" in t for t in login_tests)
    
    home_tests = impact_map.get_impacted_tests("HomePage")
    assert len(home_tests) >= 1
    assert any("Navigate To Settings" in t for t in home_tests)
    
    # Test statistics
    stats = impact_map.get_statistics()
    assert stats["total_tests"] >= 3
    assert stats["total_page_objects"] >= 2
