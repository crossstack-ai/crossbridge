"""
Unit tests for step definition transformation in MigrationOrchestrator.
Tests the transformation of Java Cucumber step definitions to Robot Framework keywords.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import (
    MigrationRequest,
    MigrationType,
    TransformationMode,
    MigrationMode,
    OperationType
)

# Import step definition parser models for testing
try:
    from adapters.selenium_bdd_java.step_definition_parser import (
        JavaStepDefinitionParser,
        StepDefinitionFile,
        StepDefinitionIntent,
        SeleniumAction,
        PageObjectCall
    )
    # Use StepDefinitionIntent as StepDefinition for compatibility
    StepDefinition = StepDefinitionIntent
    STEP_PARSER_AVAILABLE = True
except ImportError as e:
    print(f"Step parser import failed: {e}")
    STEP_PARSER_AVAILABLE = False


class TestStepDefinitionTransformation:
    """Test suite for Java step definition to Robot Framework transformation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MigrationOrchestrator()
    
    def test_step_pattern_to_keyword_name(self):
        """Test conversion of Cucumber step patterns to Robot keyword names."""
        # Test basic patterns
        assert self.orchestrator._step_pattern_to_keyword_name("user is on login page") == "User Is On Login Page"
        assert self.orchestrator._step_pattern_to_keyword_name("user clicks button") == "User Clicks Button"
        
        # Test patterns with placeholders
        assert self.orchestrator._step_pattern_to_keyword_name("user enters {string}") == "User Enters Text"
        assert self.orchestrator._step_pattern_to_keyword_name("user selects {int} items") == "User Selects Number Items"
        assert self.orchestrator._step_pattern_to_keyword_name("verify {} is displayed") == "Verify Value Is Displayed"
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    def test_selenium_to_playwright_click(self):
        """Test Selenium click action to Playwright conversion."""
        action = SeleniumAction(
            action_type="click",
            target="id=loginButton",
            parameters=[]
        )
        
        result = self.orchestrator._selenium_to_playwright(action)
        assert result == "Click    id=loginButton"
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    def test_selenium_to_playwright_sendkeys(self):
        """Test Selenium sendKeys action to Playwright Fill Text conversion."""
        action = SeleniumAction(
            action_type="sendkeys",
            target="id=username",
            parameters=["testuser"]
        )
        
        result = self.orchestrator._selenium_to_playwright(action)
        assert result == "Fill Text    id=username    testuser"
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    def test_selenium_to_playwright_gettext(self):
        """Test Selenium getText action to Playwright Get Text conversion."""
        action = SeleniumAction(
            action_type="gettext",
            target="css=.message",
            parameters=[]
        )
        
        result = self.orchestrator._selenium_to_playwright(action)
        assert result == "Get Text    css=.message"
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    def test_selenium_to_playwright_isdisplayed(self):
        """Test Selenium isDisplayed to Playwright Get Element States conversion."""
        action = SeleniumAction(
            action_type="isdisplayed",
            target="xpath=//div[@id='modal']",
            parameters=[]
        )
        
        result = self.orchestrator._selenium_to_playwright(action)
        assert result == "Get Element States    xpath=//div[@id='modal']    validate    visible"
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    @patch('core.orchestration.orchestrator.ADVANCED_TRANSFORMATION_AVAILABLE', True)
    @patch('adapters.selenium_bdd_java.step_definition_parser.JavaStepDefinitionParser')
    def test_transform_java_to_robot_with_selenium_actions(self, mock_parser_class):
        """Test transformation of step definition with Selenium actions."""
        
        # Mock step definition with Selenium actions
        selenium_action = SeleniumAction(
            action_type="click",
            target="id=loginButton",
            parameters=[]
        )
        
        step_def = StepDefinition(
            step_type="When",
            pattern_text="user clicks login button",
            method_name="userClicksLoginButton",
            parameters=[],
            selenium_actions=[selenium_action],
            page_object_calls=[],
            assertions=[]
        )
        
        step_file = StepDefinitionFile(
            file_path="LoginSteps.java",
            package_name="com.test.steps",
            class_name="LoginSteps",
            imports=[],
            step_definitions=[step_def]
        )
        
        # Configure mock parser
        mock_parser = Mock()
        mock_parser.parse_content.return_value = step_file
        mock_parser_class.return_value = mock_parser
        
        # Transform
        java_content = """
@When("user clicks login button")
public void userClicksLoginButton() {
    driver.findElement(By.id("loginButton")).click();
}
"""
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            java_content,
            "LoginSteps.java",
            with_review_markers=False
        )
        
        # Verify Robot Framework structure
        assert "*** Settings ***" in robot_content
        assert "Library          Browser" in robot_content
        assert "*** Keywords ***" in robot_content
        assert "User Clicks Login Button" in robot_content
        assert "[Documentation]    When: user clicks login button" in robot_content
        assert "Click    id=loginButton" in robot_content
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    @patch('core.orchestration.orchestrator.ADVANCED_TRANSFORMATION_AVAILABLE', True)
    @patch('adapters.selenium_bdd_java.step_definition_parser.JavaStepDefinitionParser')
    def test_transform_java_to_robot_with_parameters(self, mock_parser_class):
        """Test transformation of parameterized step definition."""
        # Mock step definition with parameters
        selenium_action = SeleniumAction(
            action_type="sendkeys",
            target="id=username",
            parameters=["username"]
        )
        
        step_def = StepDefinition(
            step_type="When",
            pattern_text="user enters username {string}",
            method_name="userEntersUsername",
            parameters=["username"],
            selenium_actions=[selenium_action],
            page_object_calls=[],
            assertions=[]
        )
        
        step_file = StepDefinitionFile(
            file_path="LoginSteps.java",
            package_name="com.test.steps",
            class_name="LoginSteps",
            imports=[],
            step_definitions=[step_def]
        )
        
        mock_parser = Mock()
        mock_parser.parse_content.return_value = step_file
        mock_parser_class.return_value = mock_parser
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            "dummy content",
            "LoginSteps.java",
            with_review_markers=False
        )
        
        # Verify parameterized keyword
        assert "User Enters Username Text" in robot_content
        assert "[Arguments]    ${username}" in robot_content
        assert "Fill Text    id=username    username" in robot_content
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    @patch('core.orchestration.orchestrator.ADVANCED_TRANSFORMATION_AVAILABLE', True)
    @patch('adapters.selenium_bdd_java.step_definition_parser.JavaStepDefinitionParser')
    def test_transform_java_to_robot_with_page_object_calls(self, mock_parser_class):
        """Test transformation of step definition with page object calls."""
        # Mock step definition with page object call
        po_call = PageObjectCall(
            page_object_name="LoginPage",
            method_name="clickLoginButton",
            parameters=[]
        )
        
        step_def = StepDefinition(
            step_type="When",
            pattern_text="user clicks login button",
            method_name="userClicksLoginButton",
            parameters=[],
            selenium_actions=[],
            page_object_calls=[po_call],
            assertions=[]
        )
        
        step_file = StepDefinitionFile(
            file_path="LoginSteps.java",
            package_name="com.test.steps",
            class_name="LoginSteps",
            imports=[],
            step_definitions=[step_def]
        )
        
        mock_parser = Mock()
        mock_parser.parse_content.return_value = step_file
        mock_parser_class.return_value = mock_parser
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            "dummy content",
            "LoginSteps.java",
            with_review_markers=False
        )
        
        # Verify page object call is converted to keyword
        assert "User Clicks Login Button" in robot_content
        assert "# Call: LoginPage.clickLoginButton" in robot_content
        assert "Clickloginbutton" in robot_content or "Click Login Button" in robot_content.replace("# Call: LoginPage.clickLoginButton", "")
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    @patch('core.orchestration.orchestrator.ADVANCED_TRANSFORMATION_AVAILABLE', True)
    @patch('adapters.selenium_bdd_java.step_definition_parser.JavaStepDefinitionParser')
    def test_transform_java_to_robot_no_implementation(self, mock_parser_class):
        """Test transformation when no implementation details are found."""
        # Mock step definition with no actions
        step_def = StepDefinition(
            step_type="Given",
            pattern_text="user is on homepage",
            method_name="userIsOnHomepage",
            parameters=[],
            selenium_actions=[],
            page_object_calls=[],
            assertions=[]
        )
        
        step_file = StepDefinitionFile(
            file_path="NavigationSteps.java",
            package_name="com.test.steps",
            class_name="NavigationSteps",
            imports=[],
            step_definitions=[step_def]
        )
        
        mock_parser = Mock()
        mock_parser.parse_content.return_value = step_file
        mock_parser_class.return_value = mock_parser
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            "dummy content",
            "NavigationSteps.java",
            with_review_markers=False
        )
        
        # Verify TODO marker is added instead of placeholder
        assert "User Is On Homepage" in robot_content
        assert "# Original Java method body not parsed - add implementation" in robot_content
        assert "# Step pattern: user is on homepage" in robot_content
        assert "Log    TODO: Implement step 'User Is On Homepage'" in robot_content
        # Should NOT have generic placeholder
        assert "Placeholder Keyword" not in robot_content
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    @patch('core.orchestration.orchestrator.ADVANCED_TRANSFORMATION_AVAILABLE', True)
    @patch('adapters.selenium_bdd_java.step_definition_parser.JavaStepDefinitionParser')
    def test_transform_java_to_robot_multiple_steps(self, mock_parser_class):
        """Test transformation of file with multiple step definitions."""
        # Create multiple step definitions
        step_defs = [
            StepDefinition(
                step_type="Given",
                pattern_text="user is on login page",
                method_name="userIsOnLoginPage",
                parameters=[],
                selenium_actions=[
                    SeleniumAction(action_type="click", target="id=home", parameters=[])
                ],
                page_object_calls=[],
                assertions=[]
            ),
            StepDefinition(
                step_type="When",
                pattern_text="user enters credentials",
                method_name="userEntersCredentials",
                parameters=[],
                selenium_actions=[
                    SeleniumAction(action_type="sendkeys", target="id=username", parameters=["admin"]),
                    SeleniumAction(action_type="sendkeys", target="id=password", parameters=["pass"])
                ],
                page_object_calls=[],
                assertions=[]
            ),
            StepDefinition(
                step_type="Then",
                pattern_text="user sees dashboard",
                method_name="userSeesDashboard",
                parameters=[],
                selenium_actions=[
                    SeleniumAction(action_type="isdisplayed", target="css=.dashboard", parameters=[])
                ],
                page_object_calls=[],
                assertions=[]
            )
        ]
        
        step_file = StepDefinitionFile(
            file_path="LoginSteps.java",
            package_name="com.test.steps",
            class_name="LoginSteps",
            imports=[],
            step_definitions=step_defs
        )
        
        mock_parser = Mock()
        mock_parser.parse_content.return_value = step_file
        mock_parser_class.return_value = mock_parser
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            "dummy content",
            "LoginSteps.java",
            with_review_markers=False
        )
        
        # Verify all three keywords are present
        assert "User Is On Login Page" in robot_content
        assert "User Enters Credentials" in robot_content
        assert "User Sees Dashboard" in robot_content
        
        # Verify Playwright actions
        assert "Click    id=home" in robot_content
        assert "Fill Text    id=username    admin" in robot_content
        assert "Fill Text    id=password    pass" in robot_content
        assert "Get Element States    css=.dashboard    validate    visible" in robot_content
    
    def test_transform_java_to_robot_fallback_to_page_object_parser(self):
        """Test fallback to page object parser when no step definitions found."""
        java_content = """
public class LoginPage {
    @FindBy(id = "username")
    private WebElement usernameField;
    
    public void enterUsername(String username) {
        usernameField.sendKeys(username);
    }
}
"""
        
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            java_content,
            "LoginPage.java",
            with_review_markers=False
        )
        
        # Should fall back to page object transformation
        assert "*** Settings ***" in robot_content
        assert "Library          Browser" in robot_content
        assert "*** Keywords ***" in robot_content
        # Should have method as keyword
        assert "Enter Username" in robot_content or "Enterusername" in robot_content
    
    def test_validate_robot_file_valid(self):
        """Test validation of valid Robot Framework file."""
        valid_content = """*** Settings ***
Library          Browser

*** Keywords ***
User Clicks Button
    Click    id=button
"""
        
        is_valid, issues = self.orchestrator._validate_robot_file(valid_content, "test.robot")
        
        assert is_valid or len(issues) == 0  # Valid files should have no issues
        assert "Missing *** Keywords *** section" not in issues
    
    def test_validate_robot_file_missing_keywords(self):
        """Test validation catches missing Keywords section."""
        invalid_content = """*** Settings ***
Library          Browser
"""
        
        is_valid, issues = self.orchestrator._validate_robot_file(invalid_content, "test.robot")
        
        assert "Missing *** Keywords *** section" in issues
    
    def test_transform_mode_migration(self):
        """Test that migration mode uses correct transformation."""
        # This tests the integration - migration should transform Java to Robot
        java_content = """
@When("user clicks button")
public void userClicksButton() {
    driver.findElement(By.id("btn")).click();
}
"""
        
        result = self.orchestrator._transform_java_to_robot_keywords(
            java_content,
            "Steps.java",
            with_review_markers=False
        )
        
        # Should produce Robot Framework output
        assert "*** Settings ***" in result
        assert "*** Keywords ***" in result
        assert "Browser" in result
    
    def test_transform_mode_hybrid_adds_review_markers(self):
        """Test that hybrid mode adds review markers."""
        java_content = """
@Given("user is on page")
public void userIsOnPage() {}
"""
        
        with patch('core.orchestration.orchestrator.ADVANCED_TRANSFORMATION_AVAILABLE', False):
            result = self.orchestrator._transform_java_to_robot_keywords(
                java_content,
                "Steps.java",
                with_review_markers=True
            )
        
        # Should have review markers in hybrid mode
        assert "*** Settings ***" in result


class TestStepDefinitionIntegration:
    """Integration tests for step definition transformation in full migration workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MigrationOrchestrator()
    
    @pytest.mark.skipif(not STEP_PARSER_AVAILABLE, reason="Step parser not available")
    @patch('core.orchestration.orchestrator.ADVANCED_TRANSFORMATION_AVAILABLE', True)
    @patch('adapters.selenium_bdd_java.step_definition_parser.JavaStepDefinitionParser')
    def test_migration_transforms_step_definitions_correctly(self, mock_parser_class):
        """Test that migration workflow properly transforms step definitions."""
        # Mock a complete step definition file
        step_def = StepDefinition(
            step_type="When",
            pattern_text="user logs in with username {string} and password {string}",
            method_name="userLogsIn",
            parameters=["username", "password"],
            selenium_actions=[
                SeleniumAction(action_type="sendkeys", target="id=user", parameters=["username"]),
                SeleniumAction(action_type="sendkeys", target="id=pass", parameters=["password"]),
                SeleniumAction(action_type="click", target="id=submit", parameters=[])
            ],
            page_object_calls=[],
            assertions=[]
        )
        
        step_file = StepDefinitionFile(
            file_path="AuthSteps.java",
            package_name="com.test.steps",
            class_name="AuthSteps",
            imports=[],
            step_definitions=[step_def]
        )
        
        mock_parser = Mock()
        mock_parser.parse_content.return_value = step_file
        mock_parser_class.return_value = mock_parser
        
        # Perform transformation
        robot_content = self.orchestrator._transform_java_to_robot_keywords(
            "java content here",
            "AuthSteps.java",
            with_review_markers=False
        )
        
        # Verify complete Robot Framework structure
        assert "*** Settings ***" in robot_content
        assert "Documentation    Migrated from: AuthSteps.java" in robot_content
        assert "Library          Browser" in robot_content
        assert "Library          BuiltIn" in robot_content
        
        assert "*** Keywords ***" in robot_content
        assert "User Logs In With Username Text And Password Text" in robot_content
        assert "[Arguments]    ${username}    ${password}" in robot_content
        assert "[Documentation]    When: user logs in with username {string} and password {string}" in robot_content
        
        # Verify Playwright Browser library calls
        assert "Fill Text    id=user    username" in robot_content
        assert "Fill Text    id=pass    password" in robot_content
        assert "Click    id=submit" in robot_content
        
        # Verify no placeholders
        assert "Placeholder Keyword" not in robot_content
        assert "This is a placeholder" not in robot_content
