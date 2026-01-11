"""
Pytest configuration for transformation unit tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_gherkin_feature():
    """Fixture providing sample Gherkin content."""
    return """
@smoke @regression
Feature: User Login
  As a user
  I want to login to the application
  
  Background:
    Given application is running
  
  Scenario: Successful login
    Given user is on login page
    When user enters "testuser" and "password123"
    Then user sees dashboard
"""


@pytest.fixture
def sample_java_step_definition():
    """Fixture providing sample Java step definition."""
    return '''
public class LoginSteps {
    @Given("user is on login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com/login");
    }
    
    @When("user enters {string} and {string}")
    public void userEntersCredentials(String username, String password) {
        driver.findElement(By.id("username")).sendKeys(username);
        driver.findElement(By.id("password")).sendKeys(password);
    }
}
'''


@pytest.fixture
def sample_page_object():
    """Fixture providing sample page object with locators."""
    return '''
public class LoginPage {
    @FindBy(id = "username")
    private WebElement usernameField;
    
    @FindBy(id = "password")
    private WebElement passwordField;
    
    @FindBy(xpath = "//button[@type='submit']")
    private WebElement submitButton;
    
    public void login(String user, String pass) {
        usernameField.sendKeys(user);
        passwordField.sendKeys(pass);
        submitButton.click();
    }
}
'''
