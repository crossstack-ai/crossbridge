"""
Unit tests for Selenium-Java runner adapter.

Tests the Maven and Gradle runners, adapter orchestration, and CLI integration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from adapters.java.selenium.models import (
    TestExecutionRequest,
    TestExecutionResult,
    BuildToolConfig,
    TestFrameworkConfig
)
from adapters.java.selenium.maven_runner import MavenRunner
from adapters.java.selenium.gradle_runner import GradleRunner
from adapters.java.selenium.adapter import SeleniumJavaAdapter, run_selenium_java_tests


class TestDataModels:
    """Test data model classes."""
    
    def test_test_execution_request_creation(self):
        """Test creating a test execution request."""
        request = TestExecutionRequest(
            working_dir="/path/to/project",
            tests=["com.example.LoginTest", "com.example.OrderTest"],
            tags=["smoke", "integration"]
        )
        
        assert request.working_dir is not None
        assert len(request.tests) == 2
        assert len(request.tags) == 2
        assert request.parallel is False
    
    def test_test_execution_result_success(self):
        """Test creating a successful test execution result."""
        result = TestExecutionResult(
            status="passed",
            exit_code=0,
            tests_run=10,
            tests_passed=10,
            tests_failed=0,
            execution_time=5.5
        )
        
        assert result.is_successful()
        assert result.tests_run == 10
        assert result.tests_passed == 10
    
    def test_test_execution_result_failure(self):
        """Test creating a failed test execution result."""
        result = TestExecutionResult(
            status="failed",
            exit_code=1,
            tests_run=10,
            tests_passed=8,
            tests_failed=2
        )
        
        assert not result.is_successful()
        assert result.tests_failed == 2
    
    def test_test_execution_result_to_dict(self):
        """Test converting result to dictionary."""
        result = TestExecutionResult(
            status="passed",
            exit_code=0,
            tests_run=5,
            tests_passed=5
        )
        
        result_dict = result.to_dict()
        assert result_dict["status"] == "passed"
        assert result_dict["tests_run"] == 5
        assert result_dict["tests_passed"] == 5
    
    def test_build_tool_config_maven(self):
        """Test Maven build tool configuration."""
        config = BuildToolConfig(
            tool="maven",
            test_output_dir="target/surefire-reports"
        )
        
        report_path = config.get_report_path("/project/root")
        assert "target" in report_path
        assert "surefire-reports" in report_path
    
    def test_build_tool_config_gradle(self):
        """Test Gradle build tool configuration."""
        config = BuildToolConfig(
            tool="gradle",
            test_output_dir="build/test-results/test"
        )
        
        report_path = config.get_report_path("/project/root")
        assert "build" in report_path
        assert "test-results" in report_path
    
    def test_test_framework_config_junit5(self):
        """Test JUnit 5 framework configuration."""
        config = TestFrameworkConfig(
            framework="junit5",
            supports_tags=True
        )
        
        support = config.get_selective_execution_support()
        assert support["tests"] is True
        assert support["tags"] is True
        assert support["groups"] is False
    
    def test_test_framework_config_testng(self):
        """Test TestNG framework configuration."""
        config = TestFrameworkConfig(
            framework="testng",
            supports_groups=True
        )
        
        support = config.get_selective_execution_support()
        assert support["groups"] is True
        assert support["tags"] is False


class TestMavenRunner:
    """Test Maven test runner."""
    
    @pytest.fixture
    def maven_project(self, tmp_path):
        """Create a mock Maven project."""
        project = tmp_path / "maven-project"
        project.mkdir()
        
        # Create pom.xml
        pom_xml = project / "pom.xml"
        pom_xml.write_text("""
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter-api</artifactId>
                </dependency>
            </dependencies>
        </project>
        """)
        
        return project
    
    def test_maven_runner_initialization(self, maven_project):
        """Test Maven runner initialization."""
        runner = MavenRunner(str(maven_project))
        assert runner.working_dir == maven_project
        assert runner.maven_cmd in ["mvn", "./mvnw", "mvnw.cmd"]
    
    def test_build_maven_command_simple(self, maven_project):
        """Test building simple Maven command."""
        runner = MavenRunner(str(maven_project))
        request = TestExecutionRequest(
            working_dir=str(maven_project),
            tests=["LoginTest", "OrderTest"]
        )
        
        cmd = runner._build_command(request)
        assert "test" in cmd
        assert "-Dtest=LoginTest,OrderTest" in cmd
    
    def test_build_maven_command_with_tags(self, maven_project):
        """Test building Maven command with JUnit 5 tags."""
        runner = MavenRunner(str(maven_project))
        request = TestExecutionRequest(
            working_dir=str(maven_project),
            tags=["smoke", "integration"]
        )
        
        cmd = runner._build_command(request)
        assert "-Dgroups=smoke,integration" in cmd
    
    def test_build_maven_command_with_parallel(self, maven_project):
        """Test building Maven command with parallel execution."""
        runner = MavenRunner(str(maven_project))
        request = TestExecutionRequest(
            working_dir=str(maven_project),
            parallel=True,
            thread_count=4
        )
        
        cmd = runner._build_command(request)
        assert "-Dparallel=methods" in cmd
        assert "-DthreadCount=4" in cmd
    
    @patch('subprocess.run')
    def test_maven_runner_successful_execution(self, mock_run, maven_project):
        """Test successful Maven test execution."""
        # Mock successful execution
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Tests run: 5, Failures: 0, Errors: 0, Skipped: 0",
            stderr=""
        )
        
        runner = MavenRunner(str(maven_project))
        request = TestExecutionRequest(
            working_dir=str(maven_project),
            tests=["LoginTest"]
        )
        
        result = runner.run_tests(request)
        
        assert result.status == "passed"
        assert result.exit_code == 0
        assert result.tests_run == 5
        assert result.tests_failed == 0
    
    @patch('subprocess.run')
    def test_maven_runner_failed_execution(self, mock_run, maven_project):
        """Test failed Maven test execution."""
        # Mock failed execution
        mock_run.return_value = Mock(
            returncode=1,
            stdout="Tests run: 5, Failures: 2, Errors: 1, Skipped: 0",
            stderr=""
        )
        
        runner = MavenRunner(str(maven_project))
        request = TestExecutionRequest(
            working_dir=str(maven_project),
            tests=["LoginTest"]
        )
        
        result = runner.run_tests(request)
        
        assert result.status == "failed"
        assert result.exit_code == 1
        assert result.tests_run == 5
        assert result.tests_failed == 3  # 2 failures + 1 error


class TestGradleRunner:
    """Test Gradle test runner."""
    
    @pytest.fixture
    def gradle_project(self, tmp_path):
        """Create a mock Gradle project."""
        project = tmp_path / "gradle-project"
        project.mkdir()
        
        # Create build.gradle
        build_gradle = project / "build.gradle"
        build_gradle.write_text("""
        plugins {
            id 'java'
        }
        dependencies {
            testImplementation 'org.junit.jupiter:junit-jupiter-api:5.8.1'
        }
        """)
        
        return project
    
    def test_gradle_runner_initialization(self, gradle_project):
        """Test Gradle runner initialization."""
        runner = GradleRunner(str(gradle_project))
        assert runner.working_dir == gradle_project
        assert runner.gradle_cmd in ["gradle", "./gradlew", "gradlew.bat"]
    
    def test_build_gradle_command_simple(self, gradle_project):
        """Test building simple Gradle command."""
        runner = GradleRunner(str(gradle_project))
        request = TestExecutionRequest(
            working_dir=str(gradle_project),
            tests=["LoginTest", "OrderTest"]
        )
        
        cmd = runner._build_command(request)
        assert "test" in cmd
        assert "--tests" in cmd
        assert "LoginTest" in cmd
        assert "OrderTest" in cmd
    
    def test_build_gradle_command_with_methods(self, gradle_project):
        """Test building Gradle command with test methods."""
        runner = GradleRunner(str(gradle_project))
        request = TestExecutionRequest(
            working_dir=str(gradle_project),
            test_methods=["LoginTest#testValidLogin", "OrderTest#testCheckout"]
        )
        
        cmd = runner._build_command(request)
        # Gradle converts # to .
        assert "--tests" in cmd
        assert "LoginTest.testValidLogin" in cmd or "LoginTest#testValidLogin" in cmd
    
    @patch('subprocess.run')
    def test_gradle_runner_successful_execution(self, mock_run, gradle_project):
        """Test successful Gradle test execution."""
        # Mock successful execution
        mock_run.return_value = Mock(
            returncode=0,
            stdout="BUILD SUCCESSFUL\\n5 tests completed",
            stderr=""
        )
        
        runner = GradleRunner(str(gradle_project))
        request = TestExecutionRequest(
            working_dir=str(gradle_project),
            tests=["LoginTest"]
        )
        
        result = runner.run_tests(request)
        
        assert result.status == "passed"
        assert result.exit_code == 0
        assert result.tests_run == 5


class TestSeleniumJavaAdapter:
    """Test Selenium-Java adapter orchestration."""
    
    @pytest.fixture
    def maven_project(self, tmp_path):
        """Create a Maven project for testing."""
        project = tmp_path / "selenium-project"
        project.mkdir()
        
        pom_xml = project / "pom.xml"
        pom_xml.write_text("<project></project>")
        
        return project
    
    def test_adapter_detect_maven(self, maven_project):
        """Test detecting Maven build tool."""
        adapter = SeleniumJavaAdapter(str(maven_project))
        
        assert adapter.build_config.tool == "maven"
        assert "surefire" in adapter.build_config.test_output_dir
    
    def test_adapter_detect_gradle(self, tmp_path):
        """Test detecting Gradle build tool."""
        project = tmp_path / "gradle-project"
        project.mkdir()
        
        build_gradle = project / "build.gradle"
        build_gradle.write_text("plugins { id 'java' }")
        
        adapter = SeleniumJavaAdapter(str(project))
        
        assert adapter.build_config.tool == "gradle"
        assert "test-results" in adapter.build_config.test_output_dir
    
    def test_adapter_no_build_tool(self, tmp_path):
        """Test error when no build tool found."""
        project = tmp_path / "empty-project"
        project.mkdir()
        
        with pytest.raises(RuntimeError, match="No supported build tool"):
            SeleniumJavaAdapter(str(project))
    
    def test_adapter_validate_request_tags_junit5(self, maven_project):
        """Test validation allows tags for JUnit 5."""
        adapter = SeleniumJavaAdapter(str(maven_project))
        adapter.framework_config = TestFrameworkConfig(
            framework="junit5",
            supports_tags=True
        )
        
        # Should not raise
        adapter._validate_request(tags=["smoke"], groups=None, categories=None)
    
    def test_adapter_validate_request_tags_junit4_error(self, maven_project):
        """Test validation rejects tags for JUnit 4."""
        adapter = SeleniumJavaAdapter(str(maven_project))
        adapter.framework_config = TestFrameworkConfig(
            framework="junit4",
            supports_tags=False,
            supports_categories=True
        )
        
        with pytest.raises(ValueError, match="Tags are not supported"):
            adapter._validate_request(tags=["smoke"], groups=None, categories=None)
    
    def test_adapter_get_info(self, maven_project):
        """Test getting adapter information."""
        adapter = SeleniumJavaAdapter(str(maven_project))
        
        info = adapter.get_info()
        assert "build_tool" in info
        assert "test_framework" in info
        assert "selective_execution" in info
    
    @patch('adapters.java.selenium.maven_runner.MavenRunner.run_tests')
    @patch('adapters.java.selenium.maven_runner.MavenRunner.verify_maven_available')
    def test_adapter_run_tests_maven(self, mock_verify, mock_run, maven_project):
        """Test running tests through adapter with Maven."""
        mock_verify.return_value = True
        mock_run.return_value = TestExecutionResult(
            status="passed",
            exit_code=0,
            tests_run=5,
            tests_passed=5
        )
        
        adapter = SeleniumJavaAdapter(str(maven_project))
        result = adapter.run_tests(tests=["LoginTest"])
        
        assert result.status == "passed"
        assert mock_run.called


class TestConvenienceFunction:
    """Test the convenience function."""
    
    @patch('adapters.java.selenium.adapter.SeleniumJavaAdapter')
    def test_run_selenium_java_tests_function(self, mock_adapter_class):
        """Test the run_selenium_java_tests convenience function."""
        # Mock adapter instance
        mock_adapter = Mock()
        mock_adapter.run_tests.return_value = TestExecutionResult(
            status="passed",
            exit_code=0
        )
        mock_adapter_class.return_value = mock_adapter
        
        result = run_selenium_java_tests(
            project_root="/path/to/project",
            tests=["LoginTest"]
        )
        
        assert result.status == "passed"
        mock_adapter.run_tests.assert_called_once()
