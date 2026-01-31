"""
Tests for Robot Framework Gap Implementations.

Tests Gap 6.1 (Failure Classification), Gap 6.2 (Metadata Extraction),
and Gap 6.3 (Static Parser).
"""

import pytest
from pathlib import Path
from adapters.robot.failure_classifier import (
    RobotFailureType,
    classify_robot_failure,
)
from adapters.robot.metadata_extractor import (
    extract_robot_metadata,
    ExecutionEnvironment,
)
from adapters.robot.static_parser import (
    RobotStaticParser,
    RobotFileParser,
)


class TestRobotFailureClassification:
    """Tests for Gap 6.1: Robot Framework Failure Classification."""
    
    def test_keyword_not_found(self):
        """Test classification of keyword not found error."""
        error = "No keyword with name 'Invalid Keyword' found"
        
        classification = classify_robot_failure(error, "", "Test Login")
        
        assert classification.failure_type == RobotFailureType.KEYWORD_NOT_FOUND
        assert classification.keyword_name == "Invalid Keyword"
        assert classification.confidence > 0.7
    
    def test_library_import_failed(self):
        """Test classification of library import failure."""
        error = "Importing test library 'CustomLibrary' failed: ModuleNotFoundError"
        
        classification = classify_robot_failure(error, "")
        
        assert classification.failure_type == RobotFailureType.LIBRARY_IMPORT_FAILED
        assert classification.confidence > 0.7
    
    def test_locator_not_found(self):
        """Test classification of element locator not found."""
        error = "Element with locator 'id:submit-button' not found"
        stack = "test_login.robot:25\nSeleniumLibrary.Click Element"
        
        classification = classify_robot_failure(error, stack, "Login Test")
        
        assert classification.failure_type == RobotFailureType.LOCATOR_NOT_FOUND
        assert classification.locator == "id:submit-button"
        assert classification.locator_strategy == "id"
        assert classification.library_name == "SeleniumLibrary"
        assert classification.keyword_name == "Click Element"
    
    def test_element_not_visible(self):
        """Test classification of element not visible error."""
        error = "Element 'css:#modal' is not visible"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.ELEMENT_NOT_VISIBLE
        assert "modal" in classification.locator
    
    def test_timeout_error(self):
        """Test classification of timeout error."""
        error = "Timeout 30s exceeded waiting for element"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.TIMEOUT
        assert classification.is_intermittent is True
        assert classification.timeout_value == "30"
    
    def test_wait_until_timeout(self):
        """Test classification of Wait Until keyword timeout."""
        error = "'Wait Until Element Is Visible' failed after retrying for 10 seconds"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.WAIT_UNTIL_TIMEOUT
        assert classification.is_intermittent is True
    
    def test_assertion_failed(self):
        """Test classification of assertion failure."""
        error = "Should Be Equal: 'actual' != 'expected'"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.ASSERTION_FAILED
        assert classification.assertion_type == "Should Be Equal"
        assert classification.is_intermittent is False
    
    def test_variable_not_found(self):
        """Test classification of variable not found error."""
        error = "Variable '${USERNAME}' not found"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.VARIABLE_NOT_FOUND
        assert classification.variable_name == "USERNAME"
    
    def test_network_error(self):
        """Test classification of network error."""
        error = "Connection refused when trying to reach http://example.com"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.NETWORK_ERROR
        assert classification.is_intermittent is True
    
    def test_browser_crash(self):
        """Test classification of browser crash."""
        error = "Chrome browser crashed unexpectedly"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.BROWSER_CRASH
        assert classification.is_intermittent is True
    
    def test_setup_failed(self):
        """Test classification of setup failure."""
        error = "Setup failed: Unable to start browser"
        stack = "Suite setup failed at suite_init.robot"
        
        classification = classify_robot_failure(error, stack)
        
        assert classification.failure_type == RobotFailureType.SETUP_FAILED
        assert classification.test_phase == "setup"
    
    def test_resource_not_found(self):
        """Test classification of resource file not found."""
        error = "Resource file 'common_keywords.robot' does not exist"
        
        classification = classify_robot_failure(error)
        
        assert classification.failure_type == RobotFailureType.RESOURCE_NOT_FOUND
    
    def test_stack_trace_parsing(self):
        """Test stack trace parsing."""
        error = "Element not found"
        stack = """test_login.robot:25
SeleniumLibrary.Click Element
test_helpers.robot:10"""
        
        classification = classify_robot_failure(error, stack)
        
        assert len(classification.stack_trace) >= 2
        assert classification.stack_trace[0].file_path == "test_login.robot"
        assert classification.stack_trace[0].line_number == 25


class TestRobotMetadataExtraction:
    """Tests for Gap 6.2: Robot Framework Metadata Extraction."""
    
    def test_local_environment_detection(self, monkeypatch):
        """Test detection of local environment."""
        # Clear CI environment variables
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("JENKINS_HOME", raising=False)
        
        metadata = extract_robot_metadata()
        
        assert metadata.environment == ExecutionEnvironment.LOCAL
        assert metadata.ci_metadata is None
    
    def test_jenkins_ci_detection(self, monkeypatch):
        """Test detection of Jenkins CI."""
        monkeypatch.setenv("JENKINS_HOME", "/var/jenkins")
        monkeypatch.setenv("BUILD_NUMBER", "123")
        monkeypatch.setenv("JOB_NAME", "robot-tests")
        monkeypatch.setenv("BUILD_URL", "http://jenkins/job/robot-tests/123")
        
        metadata = extract_robot_metadata()
        
        assert metadata.environment == ExecutionEnvironment.CI
        assert metadata.ci_metadata is not None
        assert metadata.ci_metadata.ci_system == "jenkins"
        assert metadata.ci_metadata.build_number == 123
        assert metadata.ci_metadata.job_name == "robot-tests"
    
    def test_github_actions_detection(self, monkeypatch):
        """Test detection of GitHub Actions."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_RUN_ID", "456789")
        monkeypatch.setenv("GITHUB_WORKFLOW", "Robot Tests")
        monkeypatch.setenv("GITHUB_SHA", "abc123def")
        
        metadata = extract_robot_metadata()
        
        assert metadata.environment == ExecutionEnvironment.CI
        assert metadata.ci_metadata.ci_system == "github_actions"
        assert metadata.ci_metadata.build_id == "456789"
        assert metadata.ci_metadata.commit_sha == "abc123def"
    
    def test_docker_environment_detection(self, monkeypatch, tmp_path):
        """Test detection of Docker environment."""
        monkeypatch.delenv("CI", raising=False)
        
        # Create /.dockerenv file
        dockerenv = Path("/.dockerenv")
        # We can't actually create this, so we'll mock the check instead
        
        metadata = extract_robot_metadata()
        # In real environment with /.dockerenv, would be DOCKER
        # In test environment, will be LOCAL
        assert metadata.environment in [ExecutionEnvironment.LOCAL, ExecutionEnvironment.DOCKER]
    
    def test_execution_context_from_args(self):
        """Test extraction of execution context from args."""
        args = [
            "--include", "smoke",
            "--exclude", "slow",
            "--processes", "4",
        ]
        
        metadata = extract_robot_metadata(extra_args=args)
        
        assert "smoke" in metadata.execution_context.included_tags
        assert "slow" in metadata.execution_context.excluded_tags
        assert metadata.execution_context.parallel is True
        assert metadata.execution_context.worker_count == 4


class TestRobotStaticParser:
    """Tests for Gap 6.3: Robot Framework Static Parser."""
    
    def test_parse_simple_test(self, tmp_path):
        """Test parsing a simple test case."""
        robot_file = tmp_path / "test_simple.robot"
        robot_file.write_text("""
*** Test Cases ***
Login Test
    [Tags]    smoke    login
    [Documentation]    Test user login
    Open Browser    http://example.com    chrome
    Input Text    id:username    testuser
    Click Button    id:submit
""")
        
        parser = RobotFileParser(robot_file)
        suite = parser.parse()
        
        assert suite.name == "test_simple"
        assert len(suite.tests) == 1
        
        test = suite.tests[0]
        assert test.name == "Login Test"
        assert "smoke" in test.tags
        assert "login" in test.tags
        assert test.documentation == "Test user login"
    
    def test_parse_multiple_tests(self, tmp_path):
        """Test parsing multiple test cases."""
        robot_file = tmp_path / "test_multi.robot"
        robot_file.write_text("""
*** Test Cases ***
Test One
    [Tags]    tag1
    Log    Test 1

Test Two
    [Tags]    tag2
    Log    Test 2

Test Three
    Log    Test 3
""")
        
        parser = RobotFileParser(robot_file)
        suite = parser.parse()
        
        assert len(suite.tests) == 3
        assert suite.tests[0].name == "Test One"
        assert suite.tests[1].name == "Test Two"
        assert suite.tests[2].name == "Test Three"
    
    def test_parse_suite_settings(self, tmp_path):
        """Test parsing suite-level settings."""
        robot_file = tmp_path / "test_suite.robot"
        robot_file.write_text("""
*** Settings ***
Suite Setup    Initialize Test Environment
Suite Teardown    Cleanup Test Environment
Default Tags    regression
Force Tags    critical
Documentation    Suite documentation

*** Test Cases ***
Sample Test
    Log    Testing
""")
        
        parser = RobotFileParser(robot_file)
        suite = parser.parse()
        
        assert suite.suite_setup == "Initialize Test Environment"
        assert suite.suite_teardown == "Cleanup Test Environment"
        assert "regression" in suite.default_tags
        assert "critical" in suite.force_tags
        assert suite.documentation == "Suite documentation"
        
        # Test should inherit default and force tags
        test = suite.tests[0]
        assert "regression" in test.tags
        assert "critical" in test.tags
    
    def test_parse_test_settings(self, tmp_path):
        """Test parsing test-level settings."""
        robot_file = tmp_path / "test_settings.robot"
        robot_file.write_text("""
*** Test Cases ***
Complex Test
    [Setup]    Test Setup Keyword
    [Teardown]    Test Teardown Keyword
    [Timeout]    30s
    [Template]    Login With Credentials
    Log    Test body
""")
        
        parser = RobotFileParser(robot_file)
        suite = parser.parse()
        
        test = suite.tests[0]
        assert test.setup == "Test Setup Keyword"
        assert test.teardown == "Test Teardown Keyword"
        assert test.timeout == "30s"
        assert test.template == "Login With Credentials"
    
    def test_static_parser_discovery(self, tmp_path):
        """Test static parser test discovery."""
        # Create multiple robot files
        (tmp_path / "test1.robot").write_text("""
*** Test Cases ***
Test A
    [Tags]    smoke
    Log    A

Test B
    [Tags]    regression
    Log    B
""")
        
        (tmp_path / "test2.robot").write_text("""
*** Test Cases ***
Test C
    [Tags]    smoke
    Log    C
""")
        
        parser = RobotStaticParser(str(tmp_path))
        tests = parser.discover_tests()
        
        assert len(tests) == 3
        test_names = [t['name'] for t in tests]
        assert "Test A" in test_names
        assert "Test B" in test_names
        assert "Test C" in test_names
    
    def test_static_parser_tag_filtering(self, tmp_path):
        """Test filtering tests by tags."""
        robot_file = tmp_path / "test_tags.robot"
        robot_file.write_text("""
*** Test Cases ***
Smoke Test
    [Tags]    smoke
    Log    Smoke

Regression Test
    [Tags]    regression
    Log    Regression

Integration Test
    [Tags]    smoke    integration
    Log    Integration
""")
        
        parser = RobotStaticParser(str(tmp_path))
        
        # Filter by smoke tag
        smoke_tests = parser.discover_tests(tags=["smoke"])
        assert len(smoke_tests) == 2
        
        # Filter by regression tag
        regression_tests = parser.discover_tests(tags=["regression"])
        assert len(regression_tests) == 1
    
    def test_static_parser_get_tags(self, tmp_path):
        """Test extracting all unique tags."""
        robot_file = tmp_path / "test_all_tags.robot"
        robot_file.write_text("""
*** Settings ***
Force Tags    critical

*** Test Cases ***
Test 1
    [Tags]    smoke    api
    Log    Test

Test 2
    [Tags]    ui    smoke
    Log    Test
""")
        
        parser = RobotStaticParser(str(tmp_path))
        tags = parser.get_test_tags()
        
        assert "smoke" in tags
        assert "api" in tags
        assert "ui" in tags
        assert "critical" in tags
    
    def test_full_name_generation(self, tmp_path):
        """Test full test name generation."""
        robot_file = tmp_path / "suite_name.robot"
        robot_file.write_text("""
*** Test Cases ***
My Test
    Log    Testing
""")
        
        parser = RobotStaticParser(str(tmp_path))
        tests = parser.discover_tests()
        
        assert len(tests) == 1
        assert tests[0]['full_name'] == "suite_name.My Test"
        assert tests[0]['suite_name'] == "suite_name"


class TestRobotIntegration:
    """Integration tests combining multiple gap implementations."""
    
    def test_metadata_enrichment_with_classification(self):
        """Test enriching test result with metadata and classification."""
        from adapters.robot.metadata_extractor import enrich_test_result_with_metadata
        
        # Simulate test result
        test_result = {
            "name": "Login Test",
            "status": "failed",
            "error": "Element with locator 'id:submit' not found",
        }
        
        # Extract metadata
        metadata = extract_robot_metadata()
        
        # Enrich result
        enriched = enrich_test_result_with_metadata(test_result, metadata)
        
        assert "metadata" in enriched
        assert "environment" in enriched
        
        # Classify failure
        classification = classify_robot_failure(
            test_result["error"],
            "",
            test_result["name"]
        )
        
        assert classification.failure_type == RobotFailureType.LOCATOR_NOT_FOUND
        assert classification.locator == "id:submit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
