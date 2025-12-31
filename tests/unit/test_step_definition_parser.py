"""
Tests for Java Step Definition Parser

Tests the extraction and analysis of Cucumber step definitions.
"""
import pytest
from pathlib import Path
from adapters.selenium_bdd_java.step_definition_parser import (
    JavaStepDefinitionParser,
    StepDefinitionIntent,
    StepDefinitionMapper,
    SeleniumAction,
    PageObjectCall,
    translate_selenium_to_playwright,
    SELENIUM_TO_PLAYWRIGHT
)


# Sample Java step definition content
SAMPLE_STEP_DEF = '''
package com.example.stepdefs;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.openqa.selenium.WebDriver;
import com.example.pages.LoginPage;
import com.example.pages.HomePage;

public class LoginStepDefinitions {
    
    private WebDriver driver;
    private LoginPage loginPage;
    private HomePage homePage;
    
    @Given("user is on login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com/login");
        loginPage = new LoginPage(driver);
    }
    
    @When("user enters username {string}")
    public void userEntersUsername(String username) {
        loginPage.enterUsername(username);
    }
    
    @When("^user enters password (.*)$")
    public void userEntersPassword(String password) {
        loginPage.enterPassword(password);
    }
    
    @When("user clicks login button")
    public void userClicksLoginButton() {
        loginPage.clickLoginButton();
    }
    
    @Then("user should see dashboard")
    public void userShouldSeeDashboard() {
        String pageTitle = homePage.getTitle();
        assert pageTitle.equals("Dashboard");
    }
    
    @Then("user should see error message {string}")
    public void userShouldSeeErrorMessage(String expectedMessage) {
        String actualMessage = loginPage.getErrorMessage();
        assertEquals(expectedMessage, actualMessage);
    }
}
'''

SAMPLE_COMPLEX_STEP_DEF = '''
package com.example.stepdefs;

import io.cucumber.java.en.When;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

public class SearchStepDefinitions {
    
    private WebDriver driver;
    
    @When("user searches for {string}")
    public void userSearchesFor(String query) {
        WebElement searchBox = driver.findElement(By.id("search"));
        searchBox.clear();
        searchBox.sendKeys(query);
        
        WebElement submitBtn = driver.findElement(By.cssSelector("#search-btn"));
        submitBtn.click();
        
        // Wait for results
        driver.wait(5000);
    }
    
    @When("user selects result at position {int}")
    public void userSelectsResult(int position) {
        String xpath = "//div[@class='results']/div[" + position + "]";
        WebElement result = driver.findElement(By.xpath(xpath));
        
        if (result.isDisplayed() && result.isEnabled()) {
            result.click();
        }
    }
}
'''


class TestJavaStepDefinitionParser:
    """Test step definition parsing"""
    
    @pytest.fixture
    def parser(self):
        return JavaStepDefinitionParser()
    
    def test_parse_content_basic(self, parser):
        """Test basic parsing of step definitions"""
        result = parser.parse_content(SAMPLE_STEP_DEF, "LoginStepDefinitions.java")
        
        assert result.class_name == "LoginStepDefinitions"
        assert result.file_path == "LoginStepDefinitions.java"
        assert len(result.step_definitions) == 6
    
    def test_extract_imports(self, parser):
        """Test import extraction"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        assert "io.cucumber.java.en.Given" in result.imports
        assert "io.cucumber.java.en.When" in result.imports
        assert "io.cucumber.java.en.Then" in result.imports
        assert "com.example.pages.LoginPage" in result.imports
    
    def test_extract_page_object_fields(self, parser):
        """Test page object field extraction"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        assert "loginPage" in result.page_object_fields
        assert result.page_object_fields["loginPage"] == "LoginPage"
        assert "homePage" in result.page_object_fields
        assert result.page_object_fields["homePage"] == "HomePage"
    
    def test_parse_step_annotations(self, parser):
        """Test parsing of different annotation formats"""
        test_cases = [
            ('@Given("user is on login page")', ("Given", "user is on login page")),
            ('@When("^user clicks (.*)$")', ("When", "^user clicks (.*)$")),
            ('@Then("user should see {string}")', ("Then", "user should see {string}")),
        ]
        
        for line, expected in test_cases:
            step_type, pattern = parser._parse_step_annotation(line)
            assert (step_type, pattern) == expected
    
    def test_regex_to_text_conversion(self, parser):
        """Test regex pattern to human-readable text"""
        test_cases = [
            ("^user clicks (.*) button$", "user clicks {param} button"),
            ('user enters "([^"]*)"', "user enters {param}"),
            ("user logs in", "user logs in"),
        ]
        
        for regex, expected_text in test_cases:
            result = parser._regex_to_text(regex)
            assert result == expected_text
    
    def test_extract_given_step(self, parser):
        """Test extraction of @Given step"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        given_steps = [s for s in result.step_definitions if s.step_type == "Given"]
        assert len(given_steps) == 1
        
        step = given_steps[0]
        assert step.pattern == "user is on login page"
        assert step.method_name == "userIsOnLoginPage"
        assert "driver.get" in step.method_body
    
    def test_extract_when_step(self, parser):
        """Test extraction of @When step"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        when_steps = [s for s in result.step_definitions if s.step_type == "When"]
        assert len(when_steps) == 3
        
        # Check username step
        username_step = when_steps[0]
        assert username_step.pattern == "user enters username {string}"
        assert username_step.method_name == "userEntersUsername"
    
    def test_extract_then_step(self, parser):
        """Test extraction of @Then step"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        then_steps = [s for s in result.step_definitions if s.step_type == "Then"]
        assert len(then_steps) == 2
        
        # Check dashboard step
        dashboard_step = then_steps[0]
        assert dashboard_step.pattern == "user should see dashboard"
        assert "assert" in dashboard_step.method_body.lower()
    
    def test_extract_page_object_calls(self, parser):
        """Test extraction of page object method calls"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        # Find step that calls loginPage.enterUsername
        username_step = next(
            s for s in result.step_definitions 
            if "enterUsername" in s.method_body
        )
        
        assert len(username_step.page_object_calls) == 1
        
        call = username_step.page_object_calls[0]
        assert call.page_object_name == "loginPage"
        assert call.method_name == "enterUsername"
        assert len(call.parameters) == 1
    
    def test_extract_multiple_page_object_calls(self, parser):
        """Test extraction when multiple PO calls in one step"""
        content = '''
        @When("user completes form")
        public void completeForm() {
            formPage.enterName("John");
            formPage.enterEmail("john@example.com");
            formPage.clickSubmit();
        }
        '''
        
        result = parser.parse_content(content)
        assert len(result.step_definitions) == 1
        
        step = result.step_definitions[0]
        assert len(step.page_object_calls) == 3
        assert all(call.page_object_name == "formPage" for call in step.page_object_calls)
    
    def test_extract_selenium_actions(self, parser):
        """Test extraction of direct Selenium calls"""
        result = parser.parse_content(SAMPLE_COMPLEX_STEP_DEF)
        
        search_step = result.step_definitions[0]
        
        # Should find click, sendKeys, clear
        actions = search_step.selenium_actions
        action_types = [a.action_type for a in actions]
        
        assert "clear" in action_types
        assert "sendKeys" in action_types
        assert "click" in action_types
    
    def test_extract_assertions(self, parser):
        """Test extraction of assertion statements"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        # Find assertion step
        assertion_steps = [
            s for s in result.step_definitions 
            if s.assertions
        ]
        
        assert len(assertion_steps) >= 1
    
    def test_classify_step_intent(self, parser):
        """Test automatic classification of step intent"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        # Given step should be 'setup'
        given_step = next(s for s in result.step_definitions if s.step_type == "Given")
        assert given_step.intent_type == "setup"
        
        # When step should be 'action'
        when_step = next(
            s for s in result.step_definitions 
            if s.step_type == "When" and "login" in s.pattern
        )
        assert when_step.intent_type == "action"
        
        # Then step should be 'assertion'
        then_step = next(s for s in result.step_definitions if s.step_type == "Then")
        assert then_step.intent_type == "assertion"
    
    def test_match_step_to_definition_exact(self, parser):
        """Test matching Gherkin step to definition (exact match)"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        step_text = "user is on login page"
        matched = parser.match_step_to_definition(step_text, result.step_definitions)
        
        assert matched is not None
        assert matched.method_name == "userIsOnLoginPage"
    
    def test_match_step_to_definition_with_param(self, parser):
        """Test matching step with parameter"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        # Step with {string} parameter
        step_text = 'user enters username "testuser"'
        matched = parser.match_step_to_definition(step_text, result.step_definitions)
        
        assert matched is not None
        assert "enterUsername" in matched.method_name
    
    def test_match_step_to_definition_regex(self, parser):
        """Test matching step with regex pattern"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        # Regex pattern: ^user enters password (.*)$
        step_text = "user enters password secret123"
        matched = parser.match_step_to_definition(step_text, result.step_definitions)
        
        assert matched is not None
        assert "enterPassword" in matched.method_name
    
    def test_match_step_not_found(self, parser):
        """Test matching returns None for undefined step"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        step_text = "user does something completely undefined"
        matched = parser.match_step_to_definition(step_text, result.step_definitions)
        
        assert matched is None


class TestStepDefinitionMapper:
    """Test scenario to implementation mapping"""
    
    @pytest.fixture
    def parser(self):
        return JavaStepDefinitionParser()
    
    @pytest.fixture
    def mapper(self, parser):
        return StepDefinitionMapper(parser)
    
    def test_create_scenario_mapping_complete(self, parser, mapper):
        """Test mapping all steps of a scenario"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        scenario_steps = [
            ("Given", "user is on login page"),
            ("When", 'user enters username "testuser"'),
            ("When", "user enters password secret123"),
            ("When", "user clicks login button"),
            ("Then", "user should see dashboard"),
        ]
        
        mapping = mapper.create_scenario_mapping(scenario_steps, result.step_definitions)
        
        # All steps should be mapped
        assert len(mapping) == 5
        
        # Check specific mappings
        assert mapping["user is on login page"].method_name == "userIsOnLoginPage"
        assert "enterPassword" in mapping["user enters password secret123"].method_name
    
    def test_create_scenario_mapping_with_unmapped(self, parser, mapper, capsys):
        """Test handling of unmapped steps"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        
        scenario_steps = [
            ("Given", "user is on login page"),
            ("When", "user does something undefined"),  # Not defined
            ("Then", "user should see dashboard"),
        ]
        
        mapping = mapper.create_scenario_mapping(scenario_steps, result.step_definitions)
        
        # Only 2 should be mapped
        assert len(mapping) == 2
        
        # Check warning was printed
        captured = capsys.readouterr()
        assert "Unmapped step" in captured.out


class TestSeleniumToPlaywrightTranslation:
    """Test Selenium to Playwright action translation"""
    
    def test_translate_click(self):
        """Test click action translation"""
        action = SeleniumAction(action_type="click", target="button", parameters=[])
        
        result = translate_selenium_to_playwright(action)
        
        assert result["method"] == "click"
        assert result["parameters"] == []
    
    def test_translate_sendkeys(self):
        """Test sendKeys to fill translation"""
        action = SeleniumAction(
            action_type="sendKeys", 
            target="input", 
            parameters=["username"]
        )
        
        result = translate_selenium_to_playwright(action)
        
        assert result["method"] == "fill"
        assert result["parameters"] == ["username"]
        assert "auto-clears" in result["notes"][0]
    
    def test_translate_gettext(self):
        """Test getText to text_content translation"""
        action = SeleniumAction(action_type="getText", target="element", parameters=[])
        
        result = translate_selenium_to_playwright(action)
        
        assert result["method"] == "text_content"
    
    def test_translate_clear(self):
        """Test clear to fill('') translation"""
        action = SeleniumAction(action_type="clear", target="input", parameters=[])
        
        result = translate_selenium_to_playwright(action)
        
        assert result["method"] == "fill"
        assert result["parameters"] == ['""']
        assert "empty string" in result["notes"][0]
    
    def test_translate_isdisplayed(self):
        """Test isDisplayed to is_visible translation"""
        action = SeleniumAction(action_type="isDisplayed", target="element", parameters=[])
        
        result = translate_selenium_to_playwright(action)
        
        assert result["method"] == "is_visible"
    
    def test_selenium_to_playwright_mapping_completeness(self):
        """Ensure all common Selenium actions are mapped"""
        required_actions = [
            "click", "sendKeys", "getText", "clear", "submit",
            "isDisplayed", "isEnabled", "isSelected",
            "findElement", "findElements"
        ]
        
        for action in required_actions:
            assert action in SELENIUM_TO_PLAYWRIGHT


class TestComplexStepDefinitions:
    """Test parsing of complex real-world step definitions"""
    
    @pytest.fixture
    def parser(self):
        return JavaStepDefinitionParser()
    
    def test_parse_conditional_logic(self, parser):
        """Test parsing steps with conditional logic"""
        content = '''
        @When("user attempts login")
        public void attemptLogin() {
            if (loginPage.isRememberMeVisible()) {
                loginPage.checkRememberMe();
            }
            loginPage.clickLogin();
        }
        '''
        
        result = parser.parse_content(content)
        assert len(result.step_definitions) == 1
        
        step = result.step_definitions[0]
        assert len(step.page_object_calls) >= 2
    
    def test_parse_loops(self, parser):
        """Test parsing steps with loops"""
        content = '''
        @When("user selects multiple items")
        public void selectMultiple() {
            List<WebElement> checkboxes = page.getCheckboxes();
            for (WebElement cb : checkboxes) {
                if (!cb.isSelected()) {
                    cb.click();
                }
            }
        }
        '''
        
        result = parser.parse_content(content)
        assert len(result.step_definitions) == 1
        
        step = result.step_definitions[0]
        # Should detect click and isSelected
        action_types = [a.action_type for a in step.selenium_actions]
        assert "click" in action_types or "isSelected" in action_types
    
    def test_parse_wait_statements(self, parser):
        """Test detection of wait statements"""
        content = '''
        @Then("page should load")
        public void waitForPage() {
            WebDriverWait wait = new WebDriverWait(driver, 10);
            wait.until(ExpectedConditions.visibilityOf(element));
        }
        '''
        
        result = parser.parse_content(content)
        assert len(result.step_definitions) == 1
        
        step = result.step_definitions[0]
        # Wait logic should be in body
        assert "wait" in step.method_body.lower()


class TestIntegrationScenarios:
    """Test complete end-to-end scenarios"""
    
    @pytest.fixture
    def parser(self):
        return JavaStepDefinitionParser()
    
    def test_complete_login_scenario_mapping(self, parser):
        """Test mapping a complete login scenario"""
        result = parser.parse_content(SAMPLE_STEP_DEF)
        mapper = StepDefinitionMapper(parser)
        
        # Complete scenario from .feature file
        scenario_steps = [
            ("Given", "user is on login page"),
            ("When", 'user enters username "admin"'),
            ("And", "user enters password admin123"),
            ("And", "user clicks login button"),
            ("Then", "user should see dashboard"),
        ]
        
        mapping = mapper.create_scenario_mapping(scenario_steps, result.step_definitions)
        
        # All steps should be mapped
        assert len(mapping) == 5
        
        # Verify each step has implementation details
        for step_text, step_def in mapping.items():
            assert step_def.method_name
            assert step_def.method_body
            # Should have either PO calls or Selenium actions
            assert step_def.page_object_calls or step_def.selenium_actions or step_def.assertions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
