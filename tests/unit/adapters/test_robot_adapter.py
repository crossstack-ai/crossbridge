"""
Tests for Robot Framework adapter.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from adapters.robot.robot_adapter import (
    RobotAdapter,
    RobotExtractor,
    RobotDetector
)
from adapters.robot.config import RobotConfig


class TestRobotAdapter:
    """Test Robot Framework adapter functionality."""
    
    def test_adapter_initialization(self, tmp_path):
        """Test adapter initialization."""
        adapter = RobotAdapter(str(tmp_path))
        
        assert adapter.project_root == tmp_path
        assert adapter.config is not None
    
    def test_adapter_with_custom_config(self, tmp_path):
        """Test adapter with custom config."""
        config = RobotConfig(
            tests_path=str(tmp_path / "robot_tests"),
            pythonpath=str(tmp_path / "resources")
        )
        
        adapter = RobotAdapter(str(tmp_path), config=config)
        assert adapter.config.tests_path == str(tmp_path / "robot_tests")
    
    @patch('subprocess.run')
    def test_discover_tests(self, mock_run, tmp_path):
        """Test test discovery."""
        # Create mock output.xml
        output_xml = tmp_path / "output.xml"
        output_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<robot>
    <suite name="Test Suite">
        <test name="Valid Login Test" />
        <test name="Invalid Login Test" />
        <test name="Search Product Test" />
    </suite>
</robot>
""")
        
        # Mock subprocess to create the file
        def create_output(*args, **kwargs):
            # Extract output dir from command
            cmd = args[0]
            for i, arg in enumerate(cmd):
                if arg == "--output":
                    output_path = Path(cmd[i + 1])
                    output_path.write_text(output_xml.read_text())
                    break
            return Mock(returncode=0)
        
        mock_run.side_effect = create_output
        
        adapter = RobotAdapter(str(tmp_path))
        tests = adapter.discover_tests()
        
        assert len(tests) == 3
        assert "Valid Login Test" in tests
        assert "Search Product Test" in tests
    
    def test_parse_results(self, tmp_path):
        """Test parsing Robot Framework results."""
        # Create sample output.xml
        output_xml = tmp_path / "output.xml"
        output_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<robot>
    <suite name="Login Tests">
        <test name="Valid Login">
            <status status="PASS" elapsedtime="1500">Test passed</status>
        </test>
        <test name="Invalid Login">
            <status status="FAIL" elapsedtime="800">AssertionError: Expected error not shown</status>
        </test>
    </suite>
</robot>
""")
        
        adapter = RobotAdapter(str(tmp_path))
        results = adapter._parse_results(output_xml)
        
        assert len(results) == 2
        assert results[0].name == "Valid Login"
        assert results[0].status == "pass"
        assert results[0].duration_ms == 1500
        
        assert results[1].name == "Invalid Login"
        assert results[1].status == "fail"
        assert "AssertionError" in results[1].message


class TestRobotExtractor:
    """Test Robot Framework extractor."""
    
    def test_extract_simple_tests(self, tmp_path):
        """Test extracting simple test cases."""
        robot_file = tmp_path / "login_tests.robot"
        robot_file.write_text("""*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Valid Login
    Open Browser    https://example.com/login    chrome
    Input Text    id=username    testuser
    Input Text    id=password    password123
    Click Button    id=login-button
    Title Should Be    Dashboard
    Close Browser

Invalid Login
    [Tags]    negative
    Open Browser    https://example.com/login    chrome
    Input Text    id=username    invalid
    Input Text    id=password    wrong
    Click Button    id=login-button
    Element Should Be Visible    class=error-message
    Close Browser
""")
        
        extractor = RobotExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        assert tests[0].test_name == "Valid Login"
        assert tests[0].framework == "robot"
        assert tests[1].test_name == "Invalid Login"
        assert "negative" in tests[1].tags
    
    def test_extract_with_suite_tags(self, tmp_path):
        """Test extracting tests with Force Tags."""
        robot_file = tmp_path / "suite_tests.robot"
        robot_file.write_text("""*** Settings ***
Force Tags    smoke    regression

*** Test Cases ***
Test One
    Log    First test

Test Two
    [Tags]    critical
    Log    Second test
""")
        
        extractor = RobotExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        # Both tests should have suite-level tags
        assert "smoke" in tests[0].tags
        assert "regression" in tests[0].tags
        # Second test has both suite and test tags
        assert "smoke" in tests[1].tags
        assert "critical" in tests[1].tags
    
    def test_extract_multiple_files(self, tmp_path):
        """Test extracting from multiple .robot files."""
        # Create first file
        file1 = tmp_path / "test_login.robot"
        file1.write_text("""*** Test Cases ***
Login Test
    Log    Testing login
""")
        
        # Create second file in subdirectory
        subdir = tmp_path / "api_tests"
        subdir.mkdir()
        file2 = subdir / "test_api.robot"
        file2.write_text("""*** Test Cases ***
API Test
    Log    Testing API
""")
        
        extractor = RobotExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        test_names = [t.test_name for t in tests]
        assert "Login Test" in test_names
        assert "API Test" in test_names
    
    def test_skip_output_directories(self, tmp_path):
        """Test that output directories are skipped."""
        # Create test in main directory
        main_test = tmp_path / "test_main.robot"
        main_test.write_text("""*** Test Cases ***
Main Test
    Log    Main test
""")
        
        # Create test in output directory (should be skipped)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        output_test = output_dir / "test_output.robot"
        output_test.write_text("""*** Test Cases ***
Output Test
    Log    Should be skipped
""")
        
        extractor = RobotExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].test_name == "Main Test"


class TestRobotDetector:
    """Test Robot Framework project detector."""
    
    def test_detect_with_robot_files(self, tmp_path):
        """Test detection with .robot files."""
        robot_file = tmp_path / "test_example.robot"
        robot_file.write_text("""*** Test Cases ***
Example Test
    Log    Test
""")
        
        assert RobotDetector.detect(str(tmp_path)) is True
    
    def test_detect_with_requirements(self, tmp_path):
        """Test detection via requirements.txt."""
        # Create requirements with robotframework
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("robotframework==6.0.0\nseleniumlibrary==6.1.0\n")
        
        # Create robot config
        config_file = tmp_path / "robot.yaml"
        config_file.write_text("# Robot config\n")
        
        assert RobotDetector.detect(str(tmp_path)) is True
    
    def test_detect_no_robot_files(self, tmp_path):
        """Test no detection without .robot files."""
        python_file = tmp_path / "test_example.py"
        python_file.write_text("def test(): pass")
        
        assert RobotDetector.detect(str(tmp_path)) is False
    
    def test_detect_with_subdirectory(self, tmp_path):
        """Test detection with .robot files in subdirectory."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        
        robot_file = test_dir / "test_suite.robot"
        robot_file.write_text("""*** Test Cases ***
Suite Test
    Log    Test
""")
        
        assert RobotDetector.detect(str(tmp_path)) is True


class TestIntegration:
    """Integration tests for Robot adapter."""
    
    def test_full_workflow(self, tmp_path):
        """Test complete workflow: detect -> extract -> discover."""
        # Create Robot test file
        robot_file = tmp_path / "test_workflow.robot"
        robot_file.write_text("""*** Settings ***
Force Tags    integration

*** Test Cases ***
Workflow Test One
    [Tags]    smoke
    Log    Step one

Workflow Test Two
    [Tags]    regression
    Log    Step two
""")
        
        # Detect
        detected = RobotDetector.detect(str(tmp_path))
        assert detected is True
        
        # Extract
        extractor = RobotExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        assert len(tests) == 2
        
        # Verify metadata
        assert all(t.framework == "robot" for t in tests)
        assert all(t.test_type == "robot" for t in tests)
        assert all("integration" in t.tags for t in tests)
    
    def test_adapter_with_real_structure(self, tmp_path):
        """Test adapter with realistic project structure."""
        # Create project structure
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        resources_dir = tmp_path / "resources"
        resources_dir.mkdir()
        
        # Create test file
        test_file = tests_dir / "test_login.robot"
        test_file.write_text("""*** Settings ***
Library    SeleniumLibrary
Resource    ../resources/common.robot

*** Test Cases ***
User Can Login
    [Tags]    smoke    critical
    Open Browser To Login Page
    Input Username    demo
    Input Password    mode
    Submit Credentials
    Welcome Page Should Be Open
""")
        
        # Create resource file
        resource_file = resources_dir / "common.robot"
        resource_file.write_text("""*** Keywords ***
Open Browser To Login Page
    Open Browser    ${URL}    ${BROWSER}
""")
        
        # Detect
        assert RobotDetector.detect(str(tmp_path)) is True
        
        # Extract
        extractor = RobotExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        # Should find test but not resource file
        assert len(tests) == 1
        assert tests[0].test_name == "User Can Login"
        assert "smoke" in tests[0].tags
        assert "critical" in tests[0].tags
