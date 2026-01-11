"""
Unit tests for Orchestrator transformation methods.
Tests transformation mode routing and content generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import (
    MigrationRequest,
    MigrationType,
    TransformationMode,
    MigrationMode
)


class TestOrchestratorTransformation:
    """Test suite for orchestrator transformation methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MigrationOrchestrator()
    
    def test_create_manual_placeholder_feature(self):
        """Test creating manual placeholder for feature file."""
        content = self.orchestrator._create_manual_placeholder(
            "features/login.feature",
            "feature"
        )
        
        assert "*** Settings ***" in content
        assert "*** Test Cases ***" in content
        assert "# TODO: Implement test cases" in content
        assert "Placeholder Test" in content
        assert "features/login.feature" in content
    
    def test_create_manual_placeholder_java(self):
        """Test creating manual placeholder for Java file."""
        content = self.orchestrator._create_manual_placeholder(
            "LoginSteps.java",
            "java"
        )
        
        assert "*** Settings ***" in content
        assert "*** Keywords ***" in content
        assert "# TODO: Implement keywords" in content
        assert "Placeholder Keyword" in content
        assert "LoginSteps.java" in content
    
    def test_transform_feature_to_robot_valid_gherkin(self):
        """Test transforming valid Gherkin to Robot Framework."""
        gherkin_content = """
Feature: Login Test
  Scenario: User logs in
    Given user is on login page
    When user enters credentials
    Then user sees dashboard
"""
        
        robot_content = self.orchestrator._transform_feature_to_robot(
            gherkin_content,
            "features/login.feature",
            with_review_markers=False
        )
        
        assert "*** Settings ***" in robot_content
        assert "Login Test" in robot_content
        assert "*** Test Cases ***" in robot_content
        # Test case name may be formatted differently (capitalization)
        assert "User logs in" in robot_content or "User Logs In" in robot_content
        # Should have actual test steps, not placeholder
        assert "User Is On Login Page" in robot_content or "User Enters Credentials" in robot_content
    
    def test_transform_feature_to_robot_invalid_gherkin(self):
        """Test transforming invalid Gherkin falls back to placeholder."""
        invalid_content = "This is not valid Gherkin"
        
        robot_content = self.orchestrator._transform_feature_to_robot(
            invalid_content,
            "test.feature",
            with_review_markers=False
        )
        
        # Should fall back to placeholder
        assert "# TODO" in robot_content or "Placeholder" in robot_content
    
    def test_transform_feature_with_review_markers(self):
        """Test transforming feature with Hybrid mode review markers."""
        gherkin_content = """
Feature: Test
  Scenario: Test
    Given step
"""
        
        robot_content = self.orchestrator._transform_feature_to_robot(
            gherkin_content,
            "test.feature",
            with_review_markers=True
        )
        
        assert "REVIEW REQUIRED" in robot_content
        assert "Hybrid Mode" in robot_content
        assert "Please review" in robot_content
    
    def test_transform_java_to_robot_keywords_basic(self):
        """Test transforming Java to Robot keywords."""
        java_content = """
public class LoginSteps {
    @Given("user is on login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com");
    }
}
"""
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            java_content,
            "LoginSteps.java",
            with_review_markers=False
        )
        
        assert "*** Settings ***" in robot_content
        assert "*** Keywords ***" in robot_content
        assert "LoginSteps.java" in robot_content
    
    def test_transform_java_with_review_markers(self):
        """Test transforming Java with review markers."""
        java_content = "public class Test { }"
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            java_content,
            "Test.java",
            with_review_markers=True
        )
        
        assert "REVIEW REQUIRED" in robot_content
    
    def test_add_review_markers(self):
        """Test adding review markers to content."""
        original = "*** Settings ***\nLibrary    Browser"
        
        marked = self.orchestrator._add_review_markers(original, "test.feature")
        
        assert "REVIEW REQUIRED" in marked
        assert "Hybrid Mode" in marked
        assert "test.feature" in marked
        assert original in marked
    
    def test_sanitize_filename_with_spaces(self):
        """Test filename sanitization replaces spaces."""
        path = "features/Login Page.robot"
        sanitized = MigrationOrchestrator.sanitize_filename(path)
        
        assert sanitized == "features/Login_Page.robot"
        assert " " not in sanitized.split("/")[-1]
    
    def test_sanitize_filename_no_spaces(self):
        """Test filename sanitization with no spaces."""
        path = "features/LoginPage.robot"
        sanitized = MigrationOrchestrator.sanitize_filename(path)
        
        assert sanitized == "features/LoginPage.robot"
    
    def test_sanitize_filename_multiple_spaces(self):
        """Test filename with multiple spaces."""
        path = "features/My Test Page.robot"
        sanitized = MigrationOrchestrator.sanitize_filename(path)
        
        assert sanitized == "features/My_Test_Page.robot"
    
    def test_sanitize_filename_no_directory(self):
        """Test sanitizing filename without directory."""
        path = "Test Page.robot"
        sanitized = MigrationOrchestrator.sanitize_filename(path)
        
        assert sanitized == "Test_Page.robot"


class TestTransformationModeIntegration:
    """Integration tests for transformation mode selection."""
    
    def test_migration_request_default_transformation_mode(self):
        """Test that MigrationRequest defaults to ENHANCED mode."""
        from core.orchestration.models import RepositoryAuth, AuthType
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token")
        )
        
        assert request.transformation_mode == TransformationMode.ENHANCED
    
    def test_migration_request_manual_mode(self):
        """Test setting manual transformation mode."""
        from core.orchestration.models import RepositoryAuth, AuthType
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            transformation_mode=TransformationMode.MANUAL
        )
        
        assert request.transformation_mode == TransformationMode.MANUAL
    
    def test_migration_request_hybrid_mode(self):
        """Test setting hybrid transformation mode."""
        from core.orchestration.models import RepositoryAuth, AuthType
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            transformation_mode=TransformationMode.HYBRID
        )
        
        assert request.transformation_mode == TransformationMode.HYBRID
    
    def test_transformation_mode_enum_values(self):
        """Test TransformationMode enum has correct values."""
        assert TransformationMode.MANUAL.value == "manual"
        assert TransformationMode.ENHANCED.value == "enhanced"
        assert TransformationMode.HYBRID.value == "hybrid"


class TestOrchestratorErrorHandling:
    """Test error handling in orchestrator transformation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MigrationOrchestrator()
    
    def test_transform_feature_handles_parser_error(self):
        """Test that parser errors are handled gracefully."""
        # Malformed Gherkin that might cause parser error
        bad_content = "Feature:" * 1000  # Potentially problematic
        
        # Should not raise exception, should return placeholder
        result = self.orchestrator._transform_feature_to_robot(
            bad_content,
            "test.feature"
        )
        
        assert result is not None
        assert isinstance(result, str)
    
    def test_transform_java_handles_error(self):
        """Test that Java transformation errors are handled."""
        bad_content = None  # Will cause error
        
        # Should not raise exception, should return placeholder
        result = self.orchestrator._transform_java_to_robot_keywords(
            bad_content,
            "test.java"
        )
        
        assert result is not None
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
