"""
Unit tests for enhanced Java step definition parser with implementation extraction.

Tests the parser's ability to extract:
- Selenium actions with locators
- Page object method calls
- Assertions
- Navigation calls
- Wait/synchronization calls
"""
import pytest
from adapters.selenium_bdd_java.step_definition_parser import (
    JavaStepDefinitionParser,
    SeleniumAction,
    PageObjectCall,
    StepDefinitionIntent
)


class TestEnhancedSeleniumExtraction:
    """Test enhanced Selenium action extraction with locators"""
    
    def setup_method(self):
        self.parser = JavaStepDefinitionParser()
    
    def test_extract_click_with_id_locator(self):
        """Test extracting click action with By.id locator"""
        java_code = '''
        @Given("user clicks login button")
        public void userClicksLoginButton() {
            driver.findElement(By.id("loginBtn")).click();
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        
        assert len(result.step_definitions) == 1
        step_def = result.step_definitions[0]
        
        assert len(step_def.selenium_actions) >= 1
        
        # Find the click action
        click_actions = [a for a in step_def.selenium_actions if a.action_type == 'click']
        assert len(click_actions) > 0
        
        click_action = click_actions[0]
        assert click_action.locator_type == "id"
        assert click_action.locator_value == "loginBtn"
    
    def test_extract_sendkeys_with_css_locator(self):
        """Test extracting sendKeys with cssSelector"""
        java_code = '''
        @When("user enters {string} in username field")
        public void userEntersUsername(String username) {
            driver.findElement(By.cssSelector("#username")).sendKeys(username);
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        sendkeys_actions = [a for a in step_def.selenium_actions if a.action_type == 'sendKeys']
        assert len(sendkeys_actions) > 0
        
        action = sendkeys_actions[0]
        assert action.locator_type == "cssSelector"
        assert action.locator_value == "#username"
        assert "username" in action.parameters[0]
    
    def test_extract_gettext_with_xpath_locator(self):
        """Test extracting getText with xpath locator"""
        java_code = '''
        @Then("error message should be displayed")
        public void errorMessageShouldBeDisplayed() {
            String errorText = driver.findElement(By.xpath("//div[@class='error']")).getText();
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        gettext_actions = [a for a in step_def.selenium_actions if a.action_type == 'getText']
        assert len(gettext_actions) > 0
        
        action = gettext_actions[0]
        assert action.locator_type == "xpath"
        assert action.locator_value == "//div[@class='error']"
        assert action.variable_name == "errorText"


class TestEnhancedPageObjectExtraction:
    """Test enhanced Page Object method call extraction"""
    
    def setup_method(self):
        self.parser = JavaStepDefinitionParser()
    
    def test_extract_page_object_call_simple(self):
        """Test simple page object method call"""
        java_code = '''
        @Given("user is on login page")
        public void userIsOnLoginPage() {
            loginPage.open();
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        assert len(step_def.page_object_calls) == 1
        po_call = step_def.page_object_calls[0]
        
        assert po_call.page_object_name == "loginPage"
        assert po_call.method_name == "open"
        assert len(po_call.parameters) == 0
    
    def test_extract_page_object_call_with_parameters(self):
        """Test page object call with parameters"""
        java_code = '''
        @When("user enters {string} as username")
        public void userEntersUsername(String username) {
            loginPage.enterUsername(username);
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        assert len(step_def.page_object_calls) == 1
        po_call = step_def.page_object_calls[0]
        
        assert po_call.page_object_name == "loginPage"
        assert po_call.method_name == "enterUsername"
        assert "username" in po_call.parameters
    
    def test_extract_page_object_call_with_return_value(self):
        """Test page object call that returns a value"""
        java_code = '''
        @Then("page title should be {string}")
        public void pageTitleShouldBe(String expectedTitle) {
            String actualTitle = homePage.getTitle();
            assertEquals(expectedTitle, actualTitle);
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        po_calls = step_def.page_object_calls
        assert len(po_calls) == 1
        
        po_call = po_calls[0]
        assert po_call.page_object_name == "homePage"
        assert po_call.method_name == "getTitle"
        assert po_call.return_variable == "actualTitle"


class TestNavigationExtraction:
    """Test extraction of WebDriver navigation calls"""
    
    def setup_method(self):
        self.parser = JavaStepDefinitionParser()
    
    def test_extract_driver_get(self):
        """Test driver.get() navigation"""
        java_code = '''
        @Given("user navigates to home page")
        public void userNavigatesToHomePage() {
            driver.get("https://example.com");
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        nav_actions = [a for a in step_def.selenium_actions if a.action_type.startswith('navigate_')]
        assert len(nav_actions) > 0
        
        nav_action = nav_actions[0]
        assert "get" in nav_action.action_type
        assert "https://example.com" in nav_action.parameters[0]
    
    def test_extract_navigate_back(self):
        """Test driver.navigate().back()"""
        java_code = '''
        @When("user clicks back button")
        public void userClicksBackButton() {
            driver.navigate().back();
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        nav_actions = [a for a in step_def.selenium_actions if 'back' in a.action_type]
        assert len(nav_actions) > 0


class TestWaitExtraction:
    """Test extraction of wait/synchronization calls"""
    
    def setup_method(self):
        self.parser = JavaStepDefinitionParser()
    
    def test_extract_explicit_wait(self):
        """Test WebDriverWait extraction"""
        java_code = '''
        @When("user waits for element to appear")
        public void userWaitsForElement() {
            WebDriverWait wait = new WebDriverWait(driver, 10);
            wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("result")));
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        wait_actions = [a for a in step_def.selenium_actions if a.action_type.startswith('wait_')]
        assert len(wait_actions) > 0
    
    def test_extract_thread_sleep(self):
        """Test Thread.sleep() extraction"""
        java_code = '''
        @Given("user waits for 2 seconds")
        public void userWaitsForTwoSeconds() {
            Thread.sleep(2000);
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        wait_actions = [a for a in step_def.selenium_actions if 'sleep' in a.action_type]
        assert len(wait_actions) > 0
        
        sleep_action = wait_actions[0]
        assert "2000" in sleep_action.parameters[0]


class TestAssertionExtraction:
    """Test extraction of assertion statements"""
    
    def setup_method(self):
        self.parser = JavaStepDefinitionParser()
    
    def test_extract_assertequals(self):
        """Test assertEquals extraction"""
        java_code = '''
        @Then("title should be {string}")
        public void titleShouldBe(String expectedTitle) {
            String actualTitle = driver.getTitle();
            assertEquals(expectedTitle, actualTitle);
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        assert len(step_def.assertions) > 0
        assert any("assertEquals" in assertion for assertion in step_def.assertions)
    
    def test_extract_asserttrue(self):
        """Test assertTrue extraction"""
        java_code = '''
        @Then("element should be displayed")
        public void elementShouldBeDisplayed() {
            boolean isDisplayed = element.isDisplayed();
            assertTrue(isDisplayed);
        }
        '''
        
        result = self.parser.parse_content(java_code, "TestSteps.java")
        step_def = result.step_definitions[0]
        
        assert len(step_def.assertions) > 0
        assert any("assertTrue" in assertion for assertion in step_def.assertions)


class TestComplexScenario:
    """Test parsing complex step definitions with multiple actions"""
    
    def setup_method(self):
        self.parser = JavaStepDefinitionParser()
    
    def test_complex_login_scenario(self):
        """Test complete login scenario with multiple actions"""
        java_code = '''
        @When("user logs in with username {string} and password {string}")
        public void userLogsIn(String username, String password) {
            driver.get("https://example.com/login");
            driver.findElement(By.id("username")).sendKeys(username);
            driver.findElement(By.id("password")).sendKeys(password);
            driver.findElement(By.cssSelector("#loginBtn")).click();
            
            WebDriverWait wait = new WebDriverWait(driver, 10);
            wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("dashboard")));
            
            String welcomeText = driver.findElement(By.xpath("//h1[@class='welcome']")).getText();
            assertTrue(welcomeText.contains(username));
        }
        '''
        
        result = self.parser.parse_content(java_code, "LoginSteps.java")
        assert len(result.step_definitions) == 1
        
        step_def = result.step_definitions[0]
        
        # Should have navigation action
        nav_actions = [a for a in step_def.selenium_actions if 'navigate_' in a.action_type]
        assert len(nav_actions) > 0
        
        # Should have sendKeys actions
        sendkeys_actions = [a for a in step_def.selenium_actions if a.action_type == 'sendKeys']
        assert len(sendkeys_actions) >= 2  # username and password
        
        # Should have click action
        click_actions = [a for a in step_def.selenium_actions if a.action_type == 'click']
        assert len(click_actions) > 0
        
        # Should have wait action
        wait_actions = [a for a in step_def.selenium_actions if 'wait_' in a.action_type]
        assert len(wait_actions) > 0
        
        # Should have getText action
        gettext_actions = [a for a in step_def.selenium_actions if a.action_type == 'getText']
        assert len(gettext_actions) > 0
        
        # Should have assertion
        assert len(step_def.assertions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
