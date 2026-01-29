"""
Comprehensive tests for Robot Framework adapter.

Tests adapter's ability to detect, extract, and process Robot Framework test files.
"""
import pytest
from pathlib import Path
from adapters.robot.adapter import RobotFrameworkAdapter
from tests.test_adapter_template import AdapterTestTemplate


class TestRobotFrameworkAdapter(AdapterTestTemplate):
    """Comprehensive test suite for Robot Framework adapter."""
    
    def get_adapter(self):
        """Return Robot Framework adapter instance."""
        return RobotFrameworkAdapter()
    
    def get_sample_test_file(self) -> Path:
        """Return path to sample Robot Framework test file."""
        return Path(__file__).parent.parent / "fixtures" / "sample_robot_test.robot"
    
    def get_sample_page_object_file(self) -> Path:
        """Return path to sample Robot Framework resource file."""
        return Path(__file__).parent.parent / "fixtures" / "sample_robot_resource.robot"
    
    def get_expected_test_count(self) -> int:
        """Expected number of tests in sample file."""
        return 12  # Test cases in sample_robot_test.robot
    
    def get_expected_page_object_count(self) -> int:
        """Expected number of resource keywords in sample file."""
        return 3  # LoginPage, Cart, Products sections


class TestRobotFrameworkSpecificFeatures:
    """Test Robot Framework-specific features and edge cases."""
    
    def setup_method(self):
        """Setup for each test."""
        self.adapter = RobotFrameworkAdapter()
    
    def test_detects_robot_file_extension(self):
        """Test adapter detects .robot file extension."""
        test_path = Path("tests/test_example.robot")
        assert self.adapter.can_handle_file(str(test_path)) is True
        
        # Should not handle .py files
        py_path = Path("tests/test_example.py")
        assert self.adapter.can_handle_file(str(py_path)) is False
    
    def test_detects_robot_settings_section(self):
        """Test adapter recognizes Robot Framework settings section."""
        code = """
*** Settings ***
Documentation    Sample test suite
Library          SeleniumLibrary

*** Test Cases ***
Sample Test
    Log    Hello World
"""
        assert self.adapter.detect_framework_from_content(code) is True
    
    def test_extracts_test_cases_section(self):
        """Test extraction of test cases from *** Test Cases *** section."""
        code = """
*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Valid Login Test
    [Documentation]    Test valid login
    [Tags]    smoke    critical
    Input Text    id=username    test@example.com
    Click Button    id=submit

Invalid Login Test
    [Documentation]    Test invalid login
    [Tags]    negative
    Input Text    id=username    invalid
"""
        tests = self.adapter.extract_tests_from_content(code, "test_login.robot")
        
        assert len(tests) == 2
        test_names = [t.test_name for t in tests]
        assert "Valid Login Test" in test_names
        assert "Invalid Login Test" in test_names
    
    def test_extracts_tags_from_test_cases(self):
        """Test extraction of [Tags] from test cases."""
        code = """
*** Test Cases ***
Smoke Test
    [Tags]    smoke    critical    login
    Log    Testing
"""
        tests = self.adapter.extract_tests_from_content(code, "test_tags.robot")
        
        assert len(tests) == 1
        test = tests[0]
        assert "smoke" in test.metadata.get("tags", [])
        assert "critical" in test.metadata.get("tags", [])
        assert "login" in test.metadata.get("tags", [])
    
    def test_extracts_documentation_from_test_cases(self):
        """Test extraction of [Documentation] from test cases."""
        code = """
*** Test Cases ***
Login Test
    [Documentation]    This test verifies login functionality with valid credentials
    [Tags]    login
    Log    Test
"""
        tests = self.adapter.extract_tests_from_content(code, "test_doc.robot")
        
        assert len(tests) == 1
        assert "documentation" in tests[0].metadata
        assert "valid credentials" in tests[0].metadata["documentation"]
    
    def test_extracts_keywords_section(self):
        """Test extraction of custom keywords from *** Keywords *** section."""
        code = """
*** Keywords ***
Login With Credentials
    [Documentation]    Login keyword
    [Arguments]    ${username}    ${password}
    Input Text    id=username    ${username}
    Input Password    id=password    ${password}
    Click Button    id=submit

Verify Welcome Message
    [Documentation]    Verify message appears
    Wait Until Page Contains Element    class=welcome
"""
        keywords = self.adapter.extract_keywords_from_content(code, "login_keywords.robot")
        
        assert len(keywords) >= 2
        keyword_names = [k["name"] for k in keywords]
        assert "Login With Credentials" in keyword_names
        assert "Verify Welcome Message" in keyword_names
    
    def test_extracts_keyword_arguments(self):
        """Test extraction of [Arguments] from keywords."""
        code = """
*** Keywords ***
Add Product To Cart
    [Arguments]    ${product_name}    ${quantity}=1
    Input Text    id=product    ${product_name}
    Input Text    id=quantity   ${quantity}
    Click Button    id=add-to-cart
"""
        keywords = self.adapter.extract_keywords_from_content(code, "cart_keywords.robot")
        
        assert len(keywords) == 1
        keyword = keywords[0]
        assert "arguments" in keyword
        assert "${product_name}" in str(keyword["arguments"])
        assert "${quantity}=1" in str(keyword["arguments"])
    
    def test_detects_selenium_library(self):
        """Test detection of SeleniumLibrary usage."""
        code = """
*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Browser Test
    Open Browser    https://example.com    Chrome
"""
        tests = self.adapter.extract_tests_from_content(code, "test_selenium.robot")
        
        assert len(tests) == 1
        metadata = tests[0].metadata
        assert "libraries" in metadata
        assert "SeleniumLibrary" in metadata["libraries"]
    
    def test_detects_builtin_library(self):
        """Test detection of BuiltIn library usage."""
        code = """
*** Settings ***
Library    BuiltIn
Library    Collections

*** Test Cases ***
Test Lists
    ${list}=    Create List    1    2    3
    Log    ${list}
"""
        tests = self.adapter.extract_tests_from_content(code, "test_builtin.robot")
        
        assert len(tests) == 1
        libraries = tests[0].metadata.get("libraries", [])
        assert "BuiltIn" in libraries or "Collections" in libraries
    
    def test_extracts_variables_section(self):
        """Test extraction of *** Variables *** section."""
        code = """
*** Variables ***
${SERVER}         https://example.com
${BROWSER}        Chrome
${USERNAME}       test@example.com
@{BROWSERS}       Chrome    Firefox    Edge

*** Test Cases ***
Use Variables
    Log    ${SERVER}
"""
        tests = self.adapter.extract_tests_from_content(code, "test_vars.robot")
        
        assert len(tests) == 1
        metadata = tests[0].metadata
        assert "variables" in metadata or "${SERVER}" in str(tests[0])
    
    def test_handles_suite_setup_teardown(self):
        """Test detection of Suite Setup and Teardown."""
        code = """
*** Settings ***
Suite Setup      Open Browser To Login Page
Suite Teardown   Close All Browsers
Test Setup       Go To Login Page
Test Teardown    Clear Browser Cache

*** Test Cases ***
Sample Test
    Log    Test
"""
        tests = self.adapter.extract_tests_from_content(code, "test_setup.robot")
        
        assert len(tests) == 1
        metadata = tests[0].metadata
        # Check if setup/teardown info is captured
        assert "setup" in str(metadata).lower() or "teardown" in str(metadata).lower()
    
    def test_handles_for_loops(self):
        """Test detection of FOR loops in test cases."""
        code = """
*** Test Cases ***
Loop Test
    FOR    ${item}    IN    @{ITEMS}
        Log    ${item}
        Click Element    ${item}
    END
"""
        tests = self.adapter.extract_tests_from_content(code, "test_loop.robot")
        
        assert len(tests) == 1
        # Verify loop syntax is captured
        assert "FOR" in str(tests[0]) or "loop" in str(tests[0].metadata).lower()
    
    def test_handles_if_conditions(self):
        """Test detection of IF conditions."""
        code = """
*** Test Cases ***
Conditional Test
    ${status}=    Get Status
    IF    '${status}' == 'active'
        Click Button    id=activate
    ELSE
        Click Button    id=deactivate
    END
"""
        tests = self.adapter.extract_tests_from_content(code, "test_if.robot")
        
        assert len(tests) == 1
        # Verify conditional logic is captured
        assert "IF" in str(tests[0]) or "condition" in str(tests[0].metadata).lower()
    
    def test_handles_resource_imports(self):
        """Test detection of resource file imports."""
        code = """
*** Settings ***
Resource    pages/login_page.robot
Resource    common/keywords.robot

*** Test Cases ***
Test With Resources
    Login With Valid Credentials
"""
        tests = self.adapter.extract_tests_from_content(code, "test_resources.robot")
        
        assert len(tests) == 1
        metadata = tests[0].metadata
        assert "resources" in metadata or "imports" in metadata
    
    def test_handles_template_tests(self):
        """Test detection of template-based tests."""
        code = """
*** Settings ***
Test Template    Login With Invalid Credentials

*** Test Cases ***
Invalid Username
    [Documentation]    Test with invalid username
    invalid_user    valid_pass

Invalid Password
    [Documentation]    Test with invalid password
    valid_user    invalid_pass
"""
        tests = self.adapter.extract_tests_from_content(code, "test_template.robot")
        
        assert len(tests) == 2
        # Verify template info is captured
        for test in tests:
            assert "template" in str(test.metadata).lower()
    
    def test_handles_empty_file(self):
        """Test adapter handles empty file gracefully."""
        tests = self.adapter.extract_tests_from_content("", "empty.robot")
        assert tests == []
    
    def test_handles_comments(self):
        """Test adapter ignores comments."""
        code = """
*** Test Cases ***
# This is a comment
Test Case One
    Log    Test
    # Another comment
    Click Button    id=btn

# Commented Out Test
#    Should Not Be Extracted
#    Log    Ignored
"""
        tests = self.adapter.extract_tests_from_content(code, "test_comments.robot")
        
        assert len(tests) == 1
        assert tests[0].test_name == "Test Case One"


class TestRobotFrameworkAdapterPerformance:
    """Performance tests for Robot Framework adapter."""
    
    def setup_method(self):
        """Setup for each test."""
        self.adapter = RobotFrameworkAdapter()
    
    def test_handles_large_test_suite(self):
        """Test adapter performance with large test file."""
        # Generate large test file
        large_code = """*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
"""
        for i in range(200):
            large_code += f"""
Test Case {i}
    [Documentation]    Test case number {i}
    [Tags]    test{i}    regression
    Log    Test {i}
    Click Button    id=btn{i}
    
"""
        
        import time
        start = time.time()
        tests = self.adapter.extract_tests_from_content(large_code, "large_test.robot")
        duration = time.time() - start
        
        assert len(tests) == 200
        assert duration < 10.0  # Should process in under 10 seconds
    
    def test_handles_large_resource_file(self):
        """Test extraction of large resource file with many keywords."""
        code = "*** Keywords ***\n"
        
        # Add 100 keywords
        for i in range(100):
            code += f"""
Keyword {i}
    [Documentation]    Keyword number {i}
    [Arguments]    ${{arg1}}    ${{arg2}}
    Log    Keyword {i}
    
"""
        
        import time
        start = time.time()
        keywords = self.adapter.extract_keywords_from_content(code, "large_keywords.robot")
        duration = time.time() - start
        
        assert len(keywords) == 100
        assert duration < 5.0  # Should be fast


@pytest.mark.integration
class TestRobotFrameworkAdapterIntegration:
    """Integration tests for Robot Framework adapter."""
    
    def setup_method(self):
        """Setup for each test."""
        self.adapter = RobotFrameworkAdapter()
    
    def test_end_to_end_test_extraction(self):
        """Test complete test extraction workflow."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_robot_test.robot"
        
        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")
        
        # Detect framework
        assert self.adapter.detect_framework(str(fixture_path))
        
        # Extract tests
        tests = self.adapter.extract_tests(str(fixture_path))
        assert len(tests) >= 10  # Should have many test cases
        
        # Verify all tests have required metadata
        for test in tests:
            assert test.framework == "robot"
            assert test.test_name
            assert test.file_path == str(fixture_path)
    
    def test_end_to_end_resource_extraction(self):
        """Test complete resource extraction workflow."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_robot_resource.robot"
        
        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")
        
        # Extract keywords/resources
        keywords = self.adapter.extract_keywords(str(fixture_path))
        assert len(keywords) >= 15  # Should have many keywords
        
        # Verify keyword metadata
        for keyword in keywords:
            assert keyword["name"]
            assert "file_path" in keyword
    
    def test_framework_detection_negative_cases(self):
        """Test framework detection rejects non-Robot files."""
        # Python pytest file
        pytest_code = """
import pytest

def test_example():
    assert 1 + 1 == 2
"""
        assert self.adapter.detect_framework_from_content(pytest_code) is False
        
        # Regular text file
        text_code = """
This is just a regular text file
with multiple lines
but no Robot Framework syntax
"""
        assert self.adapter.detect_framework_from_content(text_code) is False
    
    def test_mixed_test_and_keyword_file(self):
        """Test file with both tests and keywords."""
        code = """
*** Settings ***
Library    SeleniumLibrary

*** Variables ***
${URL}    https://example.com

*** Test Cases ***
First Test
    [Tags]    smoke
    Custom Keyword

Second Test
    [Tags]    regression
    Another Keyword

*** Keywords ***
Custom Keyword
    Log    Custom

Another Keyword
    Log    Another
"""
        tests = self.adapter.extract_tests_from_content(code, "mixed.robot")
        keywords = self.adapter.extract_keywords_from_content(code, "mixed.robot")
        
        assert len(tests) == 2
        assert len(keywords) == 2
        
        # Verify separation
        test_names = [t.test_name for t in tests]
        keyword_names = [k["name"] for k in keywords]
        
        assert "First Test" in test_names
        assert "Custom Keyword" in keyword_names
        # Keywords should not appear as tests
        assert "Custom Keyword" not in test_names
