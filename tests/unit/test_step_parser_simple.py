"""
Quick validation tests for Java Step Definition Parser
Run directly: python -m pytest tests/unit/test_step_parser_simple.py -v
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters.selenium_bdd_java.step_definition_parser import (
    JavaStepDefinitionParser,
    translate_selenium_to_playwright,
    SeleniumAction,
)


def test_parser_creation():
    """Test parser can be created"""
    parser = JavaStepDefinitionParser()
    assert parser is not None


def test_parse_simple_given_step():
    """Test parsing a simple @Given step"""
    content = '''
    @Given("user is on login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com");
    }
    '''
    
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(content)
    
    assert len(result.step_definitions) == 1
    step = result.step_definitions[0]
    assert step.step_type == "Given"
    assert step.pattern == "user is on login page"
    assert step.method_name == "userIsOnLoginPage"


def test_parse_when_step_with_parameter():
    """Test parsing @When step with parameter"""
    content = '''
    @When("user enters username {string}")
    public void enterUsername(String username) {
        loginPage.enterUsername(username);
    }
    '''
    
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(content)
    
    assert len(result.step_definitions) == 1
    step = result.step_definitions[0]
    assert step.step_type == "When"
    assert "username" in step.pattern
    assert step.method_name == "enterUsername"


def test_detect_page_object_calls():
    """Test detection of Page Object method calls"""
    content = '''
    @When("user clicks login")
    public void clickLogin() {
        loginPage.clickLoginButton();
    }
    '''
    
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(content)
    
    step = result.step_definitions[0]
    assert len(step.page_object_calls) == 1
    assert step.page_object_calls[0].page_object_name == "loginPage"
    assert step.page_object_calls[0].method_name == "clickLoginButton"


def test_detect_selenium_actions():
    """Test detection of Selenium WebDriver actions"""
    content = '''
    @When("user searches")
    public void search() {
        searchBox.clear();
        searchBox.sendKeys("test");
        searchBtn.click();
    }
    '''
    
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(content)
    
    step = result.step_definitions[0]
    action_types = [a.action_type for a in step.selenium_actions]
    assert "clear" in action_types
    assert "sendKeys" in action_types
    assert "click" in action_types


def test_selenium_to_playwright_translation():
    """Test Selenium to Playwright action translation"""
    
    # Test click
    action = SeleniumAction(action_type="click", target="button", parameters=[])
    result = translate_selenium_to_playwright(action)
    assert result["method"] == "click"
    
    # Test sendKeys -> fill
    action = SeleniumAction(action_type="sendKeys", target="input", parameters=["text"])
    result = translate_selenium_to_playwright(action)
    assert result["method"] == "fill"
    
    # Test getText -> text_content
    action = SeleniumAction(action_type="getText", target="element", parameters=[])
    result = translate_selenium_to_playwright(action)
    assert result["method"] == "text_content"


def test_match_step_to_definition():
    """Test matching Gherkin step text to step definition"""
    content = '''
    @Given("user is on login page")
    public void onLoginPage() {
        driver.get("https://example.com");
    }
    '''
    
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(content)
    
    # Exact match
    matched = parser.match_step_to_definition(
        "user is on login page",
        result.step_definitions
    )
    assert matched is not None
    assert matched.method_name == "onLoginPage"
    
    # No match
    matched = parser.match_step_to_definition(
        "user is on dashboard",
        result.step_definitions
    )
    assert matched is None


def test_step_intent_classification():
    """Test automatic classification of step intent"""
    parser = JavaStepDefinitionParser()
    
    # Setup intent
    content = '''
    @Given("user navigates to page")
    public void navigate() {
        driver.get("https://example.com");
    }
    '''
    result = parser.parse_content(content)
    assert result.step_definitions[0].intent_type == "setup"
    
    # Assertion intent
    content = '''
    @Then("user should see message")
    public void verifyMessage() {
        assert element.getText().equals("Success");
    }
    '''
    result = parser.parse_content(content)
    assert result.step_definitions[0].intent_type == "assertion"


def test_parse_multiple_steps():
    """Test parsing multiple step definitions in one file"""
    content = '''
    package com.example;
    
    import io.cucumber.java.en.*;
    
    public class StepDefs {
        @Given("step one")
        public void stepOne() {
            System.out.println("Step 1");
        }
        
        @When("step two")
        public void stepTwo() {
            System.out.println("Step 2");
        }
        
        @Then("step three")
        public void stepThree() {
            System.out.println("Step 3");
        }
    }
    '''
    
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(content)
    
    assert len(result.step_definitions) == 3
    assert result.step_definitions[0].step_type == "Given"
    assert result.step_definitions[1].step_type == "When"
    assert result.step_definitions[2].step_type == "Then"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
