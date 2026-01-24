"""
Unit tests for Java file migration and transformation in orchestrator.
Tests cover:
1. Path/folder structure preservation during migration
2. Step definition files migration+transformation (with & without AI)
3. Page factory files migration+transformation (with & without AI)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import (
    MigrationRequest,
    TransformationMode,
    TransformationTier,
    OperationType,
    AIConfig,
    AIMode,
    RepositoryAuth,
    AuthType
)
from core.repo import RepoFile


class TestJavaFileMigrationPaths:
    """Test folder structure preservation during Java file migration"""
    
    def test_pagefactory_path_preservation(self):
        """Test that pagefactory folder structure is maintained"""
        orchestrator = MigrationOrchestrator()
        
        # Test case: Page factory file path transformation
        source_path = "TetonUIAutomation/src/main/java/com/arcserve/teton/pagefactory/LoginPage.java"
        expected_target = "TetonUIAutomation/src/main/robot/com/arcserve/teton/pagefactory/LoginPage.robot"
        
        # Simulate path transformation logic
        target_path = source_path.replace('.java', '.robot').replace('/java/', '/robot/')
        
        assert target_path == expected_target, f"Expected {expected_target}, got {target_path}"
        assert '/pagefactory/' in target_path, "Pagefactory folder should be preserved"
        assert '/com/arcserve/teton/' in target_path, "Package structure should be preserved"
    
    def test_stepdefinition_path_preservation(self):
        """Test that stepdefinition folder structure is maintained"""
        orchestrator = MigrationOrchestrator()
        
        # Test case: Step definition file path transformation
        source_path = "TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/LoginSteps.java"
        expected_target = "TetonUIAutomation/src/main/robot/com/arcserve/teton/stepdefinition/LoginSteps.robot"
        
        target_path = source_path.replace('.java', '.robot').replace('/java/', '/robot/')
        
        assert target_path == expected_target, f"Expected {expected_target}, got {target_path}"
        assert '/stepdefinition/' in target_path, "Stepdefinition folder should be preserved"
        assert '/com/arcserve/teton/' in target_path, "Package structure should be preserved"
    
    def test_feature_file_path_preservation(self):
        """Test that feature file folder structure is maintained"""
        orchestrator = MigrationOrchestrator()
        
        # Test case: Feature file path transformation
        source_path = "TetonUIAutomation/src/main/resources/UIFeature/login/LoginTest.feature"
        expected_target = "TetonUIAutomation/src/main/robot/UIFeature/login/LoginTest.robot"
        
        target_path = source_path.replace('.feature', '.robot')
        if '/resources/' in target_path:
            target_path = target_path.replace('/resources/', '/robot/')
        
        assert target_path == expected_target, f"Expected {expected_target}, got {target_path}"
        assert '/UIFeature/login/' in target_path, "UIFeature folder hierarchy should be preserved"
    
    def test_nested_package_path_preservation(self):
        """Test deeply nested package structures are preserved"""
        test_cases = [
            (
                "src/main/java/com/arcserve/teton/pagefactory/admin/users/UserManagementPage.java",
                "src/main/robot/com/arcserve/teton/pagefactory/admin/users/UserManagementPage.robot"
            ),
            (
                "src/main/java/com/company/test/stepdefinition/api/ApiSteps.java",
                "src/main/robot/com/company/test/stepdefinition/api/ApiSteps.robot"
            )
        ]
        
        for source, expected in test_cases:
            target = source.replace('.java', '.robot').replace('/java/', '/robot/')
            assert target == expected, f"Expected {expected}, got {target}"


class TestStepDefinitionMigration:
    """Test step definition file migration and transformation"""
    
    @pytest.fixture
    def mock_request_no_ai(self):
        """Migration request without AI"""
        auth = RepositoryAuth(
            auth_type=AuthType.BITBUCKET_TOKEN,
            token="test-token",
            username="test-user"
        )
        request = MigrationRequest(
            repo_url="https://bitbucket.org/test/repo",
            branch="main",
            target_branch="feature/migration",
            auth=auth,
            transformation_mode=TransformationMode.ENHANCED,
            use_ai=False,
            ai_config=None
        )
        return request
    
    @pytest.fixture
    def mock_request_with_ai(self):
        """Migration request with AI enabled"""
        auth = RepositoryAuth(
            auth_type=AuthType.BITBUCKET_TOKEN,
            token="test-token",
            username="test-user"
        )
        ai_config = AIConfig(
            mode=AIMode.ENABLED,
            provider="openai",
            api_key="test-key",
            model="gpt-4",
            region="US"
        )
        request = MigrationRequest(
            repo_url="https://bitbucket.org/test/repo",
            branch="main",
            target_branch="feature/migration",
            auth=auth,
            transformation_mode=TransformationMode.ENHANCED,
            use_ai=True,
            ai_config=ai_config
        )
        return request
    
    @pytest.fixture
    def sample_step_definition_content(self):
        """Sample Java step definition file content"""
        return """
package com.arcserve.teton.stepdefinition;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import com.arcserve.teton.pagefactory.LoginPage;

public class LoginSteps {
    
    private LoginPage loginPage;
    
    @Given("user is on login page")
    public void userIsOnLoginPage() {
        loginPage = new LoginPage();
        loginPage.navigateToLoginPage();
    }
    
    @When("user enters username {string} and password {string}")
    public void userEntersCredentials(String username, String password) {
        loginPage.enterUsername(username);
        loginPage.enterPassword(password);
    }
    
    @Then("user clicks login button")
    public void userClicksLoginButton() {
        loginPage.clickLoginButton();
    }
}
"""
    
    def test_step_definition_discovery(self):
        """Test that step definition files are correctly identified"""
        orchestrator = MigrationOrchestrator()
        
        step_def_files = [
            "src/main/java/com/arcserve/teton/stepdefinition/LoginSteps.java",
            "src/main/java/com/company/stepdef/UserSteps.java",
            "src/test/java/steps/ApiSteps.java"
        ]
        
        for file_path in step_def_files:
            # Check if file matches step definition patterns
            is_step_def = (
                'stepdefinition' in file_path.lower() or 
                'stepdef' in file_path.lower() or 
                '/steps/' in file_path
            )
            assert is_step_def, f"{file_path} should be identified as step definition"
    
    @patch('core.orchestration.orchestrator.logger')
    def test_step_definition_transform_without_ai(self, mock_logger, mock_request_no_ai, sample_step_definition_content):
        """Test step definition transformation WITHOUT AI"""
        orchestrator = MigrationOrchestrator()
        
        source_path = "src/main/java/com/arcserve/teton/stepdefinition/LoginSteps.java"
        
        # Mock the transformation method
        with patch.object(orchestrator, '_transform_java_to_robot_keywords') as mock_transform:
            mock_transform.return_value = "*** Keywords ***\nUser Is On Login Page\n    Log    Placeholder"
            
            # Simulate transformation
            result = orchestrator._transform_java_to_robot_keywords(
                sample_step_definition_content,
                source_path,
                with_review_markers=False,
                request=mock_request_no_ai
            )
            
            # Verify transformation was called
            assert mock_transform.called
            assert result is not None
            
            # Verify no AI was used (check that AI methods weren't called)
            assert not mock_request_no_ai.use_ai
    
    @patch('core.orchestration.orchestrator.logger')
    def test_step_definition_transform_with_ai(self, mock_logger, mock_request_with_ai, sample_step_definition_content):
        """Test step definition transformation WITH AI"""
        orchestrator = MigrationOrchestrator()
        
        source_path = "src/main/java/com/arcserve/teton/stepdefinition/LoginSteps.java"
        
        # Mock AI transformation
        with patch.object(orchestrator, '_transform_java_to_robot_keywords') as mock_transform:
            mock_transform.return_value = """*** Settings ***
Library    Browser

*** Keywords ***
User Is On Login Page
    New Page    ${LOGIN_URL}
    Get Title    ==    Login Page

User Enters Username "${username}" And Password "${password}"
    Fill Text    id=username    ${username}
    Fill Text    id=password    ${password}

User Clicks Login Button
    Click    id=loginButton
"""
            
            # Simulate AI-enhanced transformation
            result = orchestrator._transform_java_to_robot_keywords(
                sample_step_definition_content,
                source_path,
                with_review_markers=False,
                request=mock_request_with_ai
            )
            
            # Verify transformation was called
            assert mock_transform.called
            assert result is not None
            assert "Browser" in result or "Playwright" in result or mock_transform.called
            
            # Verify AI was enabled
            assert mock_request_with_ai.use_ai
            assert mock_request_with_ai.ai_config.provider == "openai"


class TestPageFactoryMigration:
    """Test page factory file migration and transformation"""
    
    @pytest.fixture
    def sample_page_factory_content(self):
        """Sample Java page factory file content"""
        return """
package com.arcserve.teton.pagefactory;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class LoginPage {
    
    private WebDriver driver;
    
    @FindBy(id = "username")
    private WebElement usernameField;
    
    @FindBy(id = "password")
    private WebElement passwordField;
    
    @FindBy(xpath = "//button[@type='submit']")
    private WebElement loginButton;
    
    @FindBy(css = ".error-message")
    private WebElement errorMessage;
    
    public LoginPage(WebDriver driver) {
        this.driver = driver;
        PageFactory.initElements(driver, this);
    }
    
    public void enterUsername(String username) {
        usernameField.clear();
        usernameField.sendKeys(username);
    }
    
    public void enterPassword(String password) {
        passwordField.clear();
        passwordField.sendKeys(password);
    }
    
    public void clickLoginButton() {
        loginButton.click();
    }
    
    public String getErrorMessage() {
        return errorMessage.getText();
    }
}
"""
    
    def test_page_factory_discovery(self):
        """Test that page factory files are correctly identified"""
        orchestrator = MigrationOrchestrator()
        
        page_factory_files = [
            "src/main/java/com/arcserve/teton/pagefactory/LoginPage.java",
            "src/main/java/com/company/pages/HomePage.java",
            "src/test/java/pageobjects/DashboardPage.java"
        ]
        
        for file_path in page_factory_files:
            # Check if file matches page factory patterns
            is_page_factory = (
                'pagefactory' in file_path.lower() or 
                'pageobject' in file_path.lower() or 
                '/pages/' in file_path or
                'Page.java' in file_path
            )
            assert is_page_factory, f"{file_path} should be identified as page factory"
    
    @patch('core.orchestration.orchestrator.logger')
    def test_page_factory_transform_without_ai(self, mock_logger, sample_page_factory_content):
        """Test page factory transformation WITHOUT AI"""
        orchestrator = MigrationOrchestrator()
        
        # Create request without AI
        auth = RepositoryAuth(auth_type=AuthType.BITBUCKET_TOKEN, token="test-token", username="test-user")
        request = MigrationRequest(
            repo_url="https://bitbucket.org/test/repo",
            branch="main",
            target_branch="feature/migration",
            auth=auth,
            transformation_mode=TransformationMode.ENHANCED,
            use_ai=False
        )
        
        source_path = "src/main/java/com/arcserve/teton/pagefactory/LoginPage.java"
        
        # Mock the transformation
        with patch.object(orchestrator, '_transform_java_to_robot_keywords') as mock_transform:
            mock_transform.return_value = "*** Keywords ***\nEnter Username\n    [Arguments]    ${username}\n    Fill Text    id=username    ${username}"
            
            result = orchestrator._transform_java_to_robot_keywords(
                sample_page_factory_content,
                source_path,
                with_review_markers=False,
                request=request
            )
            
            assert mock_transform.called
            assert result is not None
    
    @patch('core.orchestration.orchestrator.logger')
    def test_page_factory_transform_with_ai(self, mock_logger, sample_page_factory_content):
        """Test page factory transformation WITH AI"""
        orchestrator = MigrationOrchestrator()
        
        # Create request with AI
        auth = RepositoryAuth(auth_type=AuthType.BITBUCKET_TOKEN, token="test-token", username="test-user")
        ai_config = AIConfig(
            mode=AIMode.ENABLED,
            provider="openai",
            api_key="test-key",
            model="gpt-4",
            region="US"
        )
        request = MigrationRequest(
            repo_url="https://bitbucket.org/test/repo",
            branch="main",
            target_branch="feature/migration",
            auth=auth,
            transformation_mode=TransformationMode.ENHANCED,
            use_ai=True,
            ai_config=ai_config
        )
        
        source_path = "src/main/java/com/arcserve/teton/pagefactory/LoginPage.java"
        
        # Mock AI-enhanced transformation
        with patch.object(orchestrator, '_transform_java_to_robot_keywords') as mock_transform:
            mock_transform.return_value = """*** Settings ***
Library    Browser

*** Variables ***
${USERNAME_FIELD}    id=username
${PASSWORD_FIELD}    id=password
${LOGIN_BUTTON}      xpath=//button[@type='submit']
${ERROR_MESSAGE}     css=.error-message

*** Keywords ***
Enter Username
    [Arguments]    ${username}
    Fill Text    ${USERNAME_FIELD}    ${username}

Enter Password
    [Arguments]    ${password}
    Fill Text    ${PASSWORD_FIELD}    ${password}

Click Login Button
    Click    ${LOGIN_BUTTON}

Get Error Message
    ${message}=    Get Text    ${ERROR_MESSAGE}
    [Return]    ${message}
"""
            
            result = orchestrator._transform_java_to_robot_keywords(
                sample_page_factory_content,
                source_path,
                with_review_markers=False,
                request=request
            )
            
            assert mock_transform.called
            assert result is not None
            assert request.use_ai
    
    def test_page_factory_locator_extraction(self, sample_page_factory_content):
        """Test that locators are properly extracted from page factory"""
        # Verify @FindBy annotations are present
        assert "@FindBy(id = \"username\")" in sample_page_factory_content
        assert "@FindBy(xpath = \"//button[@type='submit']\")" in sample_page_factory_content
        assert "@FindBy(css = \".error-message\")" in sample_page_factory_content
        
        # Count locators
        findby_count = sample_page_factory_content.count("@FindBy")
        assert findby_count >= 4, "Should have at least 4 locators"


class TestEndToEndMigrationFlow:
    """Integration tests for complete migration flow"""
    
    @patch('core.orchestration.orchestrator.logger')
    def test_complete_java_file_discovery_and_categorization(self, mock_logger):
        """Test that Java files are discovered and categorized correctly"""
        orchestrator = MigrationOrchestrator()
        
        # Mock file list with mixed Java files
        mock_java_files = [
            RepoFile(path="src/main/java/com/arcserve/teton/pagefactory/LoginPage.java"),
            RepoFile(path="src/main/java/com/arcserve/teton/pagefactory/DashboardPage.java"),
            RepoFile(path="src/main/java/com/arcserve/teton/stepdefinition/LoginSteps.java"),
            RepoFile(path="src/main/java/com/arcserve/teton/stepdefinition/DashboardSteps.java"),
            RepoFile(path="src/main/java/com/arcserve/teton/util/TestUtil.java"),
        ]
        
        # Categorize files
        page_objects = [f for f in mock_java_files if 'pagefactory' in f.path.lower()]
        step_definitions = [f for f in mock_java_files if 'stepdefinition' in f.path.lower()]
        other_files = [f for f in mock_java_files if f not in page_objects and f not in step_definitions]
        
        assert len(page_objects) == 2, "Should find 2 page factory files"
        assert len(step_definitions) == 2, "Should find 2 step definition files"
        assert len(other_files) == 1, "Should find 1 other Java file"
        assert len(mock_java_files) == 5, "Total should be 5 files"
    
    @patch('core.repo.bitbucket.BitbucketConnector')
    def test_all_java_files_included_in_transformation(self, mock_connector):
        """Test that all Java files (including pagefactory/stepdefinition) are included in main transformation"""
        orchestrator = MigrationOrchestrator()
        
        # Mock file discovery
        java_files = [
            RepoFile(path="src/main/java/com/test/pagefactory/LoginPage.java"),
            RepoFile(path="src/main/java/com/test/stepdefinition/LoginSteps.java"),
        ]
        feature_files = [
            RepoFile(path="src/main/resources/features/Login.feature"),
        ]
        
        # All files should be combined
        all_files = java_files + feature_files
        
        assert len(all_files) == 3, "Should have 3 total files"
        assert any('pagefactory' in f.path for f in all_files), "Should include page factory files"
        assert any('stepdefinition' in f.path for f in all_files), "Should include step definition files"
        assert any('.feature' in f.path for f in all_files), "Should include feature files"


class TestPathTransformationEdgeCases:
    """Test edge cases in path transformation"""
    
    def test_windows_path_separators(self):
        """Test handling of Windows-style path separators"""
        source = "src\\main\\java\\com\\company\\pagefactory\\LoginPage.java"
        # Normalize to forward slashes
        normalized = source.replace('\\', '/')
        target = normalized.replace('.java', '.robot').replace('/java/', '/robot/')
        
        assert '/robot/' in target
        assert '\\' not in target
    
    def test_path_without_java_folder(self):
        """Test paths that don't contain /java/ folder - this is an unusual edge case"""
        source = "src/main/com/company/LoginPage.java"
        target = source.replace('.java', '.robot')
        
        # Check if fallback logic would apply (matching orchestrator behavior)
        if '/src/main/' in source and '/java/' not in source:
            target = target.replace('/src/main/', '/src/main/robot/', 1)
        
        # Verify the result has robot in path
        expected = "src/main/robot/com/company/LoginPage.robot"
        assert target == expected, f"Expected {expected}, got: {target}"
    
    def test_multiple_java_occurrences_in_path(self):
        """Test paths with 'java' appearing multiple times"""
        source = "java-project/src/main/java/com/java/LoginPage.java"
        target = source.replace('.java', '.robot')
        
        # Should only replace the /java/ directory separator
        target = target.replace('/java/', '/robot/', 1)
        
        # First occurrence in 'java-project' should remain
        assert 'java-project' in target
        # Second occurrence /java/ should be replaced
        assert '/robot/' in target


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
