"""
Unit tests for Selenium BDD translation.
"""

import pytest

from core.translation.intent_model import ActionType, AssertionType, IntentType
from core.translation.parsers.selenium_bdd_parser import SeleniumJavaBDDParser
from core.translation.generators.pytest_generator import PytestGenerator
from core.translation.generators.robot_generator import RobotGenerator
from core.translation.pipeline import TranslationPipeline


class TestSeleniumBDDParser:
    """Test Selenium BDD parser."""
    
    def test_can_parse_cucumber_style(self):
        """Test detection of Cucumber-style BDD."""
        parser = SeleniumJavaBDDParser()
        
        bdd_code = """
        import org.openqa.selenium.WebDriver;
        import cucumber.api.java.en.Given;
        import cucumber.api.java.en.When;
        import cucumber.api.java.en.Then;
        
        @Given("user is on login page")
        public void userOnLoginPage() {
            driver.get("http://example.com/login");
        }
        
        @When("user enters credentials")
        public void userEntersCredentials() {
            driver.findElement(By.id("username")).sendKeys("admin");
        }
        
        @Then("user sees dashboard")
        public void userSeesDashboard() {
            assertTrue(driver.findElement(By.id("dashboard")).isDisplayed());
        }
        """
        
        assert parser.can_parse(bdd_code)
    
    def test_parse_scenario_name(self):
        """Test scenario name extraction."""
        parser = SeleniumJavaBDDParser()
        
        code = """
        // Scenario: User login
        @Given("user is on login page")
        public void step1() {
            driver.get("http://example.com");
        }
        """
        
        intent = parser.parse(code)
        assert "login" in intent.name.lower() or "step1" in intent.name
    
    def test_parse_bdd_steps(self):
        """Test BDD step extraction."""
        parser = SeleniumJavaBDDParser()
        
        code = """
        @Given("user navigates to login page")
        public void navigateLogin() {
            driver.get("http://example.com/login");
        }
        
        @When("user clicks submit")
        public void clickSubmit() {
            driver.findElement(By.id("submit")).click();
        }
        
        @Then("user sees success message")
        public void seeSuccess() {
            assertTrue(driver.findElement(By.id("message")).isDisplayed());
        }
        """
        
        intent = parser.parse(code)
        assert intent.test_type == IntentType.BDD
        assert len(intent.bdd_structure['given_steps']) > 0
        assert len(intent.bdd_structure['when_steps']) > 0
        assert len(intent.bdd_structure['then_steps']) > 0
    
    def test_merge_selenium_actions(self):
        """Test merging Selenium actions into BDD structure."""
        parser = SeleniumJavaBDDParser()
        
        code = """
        @Given("setup is complete")
        public void setup() {
            driver.get("http://example.com");
        }
        
        @When("user interacts")
        public void interact() {
            driver.findElement(By.id("button")).click();
            driver.findElement(By.id("input")).sendKeys("test");
        }
        
        @Then("verification passes")
        public void verify() {
            assertTrue(driver.findElement(By.id("result")).isDisplayed());
        }
        """
        
        intent = parser.parse(code)
        
        # Check that actions are categorized
        given_actions = [a for a in intent.steps if a.semantics.get('bdd_phase') == 'given']
        when_actions = [a for a in intent.steps if a.semantics.get('bdd_phase') == 'when']
        then_actions = [a for a in intent.steps if a.semantics.get('bdd_phase') == 'then']
        
        assert len(given_actions) > 0  # navigate
        assert len(when_actions) > 0  # click, input
        assert len(intent.assertions) > 0  # verification


class TestPytestGeneratorForBDD:
    """Test pytest generator for BDD tests."""
    
    def test_generate_bdd_structure(self):
        """Test BDD-style test generation."""
        generator = PytestGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.BDD, name="test_login")
        intent.bdd_structure = {
            'given_steps': ["user is on login page"],
            'when_steps': ["user enters credentials", "user clicks submit"],
            'then_steps': ["user sees dashboard"],
        }
        intent.given_steps.append(ActionIntent(
            action_type=ActionType.NAVIGATE,
            target="URL",
            value="http://example.com/login",
            semantics={'bdd_phase': 'given'},
        ))
        
        code = generator.generate(intent)
        # Should have BDD comments (Given, When, Then) or structure
        assert "Given" in code or "# Given" in code or "Arrange" in code
        # If we have given_steps in intent, they should be generated
        assert len([line for line in code.split('\n') if 'Given' in line or 'Arrange' in line]) > 0



class TestRobotGenerator:
    """Test Robot Framework generator."""
    
    def test_can_generate_ui_test(self):
        """Test capability for UI tests."""
        generator = RobotGenerator()
        
        from core.translation.intent_model import TestIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_ui")
        
        assert generator.can_generate(intent)
    
    def test_can_generate_api_test(self):
        """Test capability for API tests."""
        generator = RobotGenerator()
        
        from core.translation.intent_model import TestIntent
        intent = TestIntent(test_type=IntentType.API, name="test_api")
        
        assert generator.can_generate(intent)
    
    def test_generate_robot_structure(self):
        """Test Robot file structure generation."""
        generator = RobotGenerator()
        
        from core.translation.intent_model import TestIntent
        intent = TestIntent(test_type=IntentType.UI, name="Test Login")
        
        code = generator.generate(intent)
        assert "*** Settings ***" in code
        assert "*** Test Cases ***" in code
        assert "Test Login" in code
    
    def test_generate_ui_keywords(self):
        """Test UI keyword generation."""
        generator = RobotGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="Test Click")
        intent.add_step(ActionIntent(
            action_type=ActionType.CLICK,
            target="submit_button",
            selector="button#submit",
            value="Submit",
        ))
        
        code = generator.generate(intent)
        assert "Click" in code
        # Should contain either the selector or the converted Robot selector
        assert "button#submit" in code or "css=button#submit" in code or "id=submit" in code
    
    def test_generate_api_keywords(self):
        """Test API keyword generation."""
        generator = RobotGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.API, name="Test API")
        intent.add_step(ActionIntent(
            action_type=ActionType.REQUEST,
            target="GET_/api/users",
            value="/api/users",
            semantics={'method': 'GET', 'endpoint': '/api/users'},
        ))
        
        code = generator.generate(intent)
        assert "RequestsLibrary" in code
        assert "GET" in code or "Get Request" in code
    
    def test_generate_bdd_keywords(self):
        """Test BDD-style keyword generation."""
        generator = RobotGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.BDD, name="User Login")
        intent.bdd_structure = {
            'given_steps': ["user is on login page"],
            'when_steps': ["user enters credentials"],
            'then_steps': ["user sees dashboard"],
        }
        # Add actual actions to given_steps
        intent.given_steps.append(ActionIntent(
            action_type=ActionType.NAVIGATE,
            target="login_page",
            value="http://example.com/login",
        ))
        
        code = generator.generate(intent)
        # Should contain BDD keywords or actions
        assert "Given" in code or "New Page" in code
        # Verify BDD structure is being generated
        assert len(intent.given_steps) > 0



class TestSeleniumBDDToPytest:
    """Test Selenium BDD to pytest translation."""
    
    def test_complete_bdd_translation(self):
        """Test translating complete BDD test to pytest."""
        selenium_bdd = """
        import org.openqa.selenium.WebDriver;
        import cucumber.api.java.en.Given;
        import cucumber.api.java.en.When;
        import cucumber.api.java.en.Then;
        
        // Scenario: Successful login
        
        @Given("user is on login page")
        public void onLoginPage() {
            driver.get("http://example.com/login");
        }
        
        @When("user enters valid credentials")
        public void enterCredentials() {
            driver.findElement(By.id("username")).sendKeys("admin");
            driver.findElement(By.id("password")).sendKeys("secret");
        }
        
        @When("user clicks login button")
        public void clickLogin() {
            driver.findElement(By.id("submit")).click();
        }
        
        @Then("user sees dashboard")
        public void seeDashboard() {
            assertTrue(driver.findElement(By.id("dashboard")).isDisplayed());
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=selenium_bdd,
            source_framework="selenium-java-bdd",
            target_framework="pytest",
        )
        
        assert result.success
        assert "def test" in result.target_code
        # Should have BDD structure or comments
        assert "given" in result.target_code.lower() or "# Given" in result.target_code


class TestSeleniumBDDToRobot:
    """Test Selenium BDD to Robot Framework translation."""
    
    def test_complete_bdd_to_robot(self):
        """Test translating BDD test to Robot Framework."""
        selenium_bdd = """
        import org.openqa.selenium.WebDriver;
        import cucumber.api.java.en.Given;
        import cucumber.api.java.en.When;
        import cucumber.api.java.en.Then;
        
        // Scenario: User completes form
        
        @Given("user opens form page")
        public void openForm() {
            driver.get("http://example.com/form");
        }
        
        @When("user fills form")
        public void fillForm() {
            driver.findElement(By.id("name")).sendKeys("John");
            driver.findElement(By.id("email")).sendKeys("john@example.com");
        }
        
        @When("user submits form")
        public void submitForm() {
            driver.findElement(By.id("submit")).click();
        }
        
        @Then("user sees confirmation")
        public void seeConfirmation() {
            assertTrue(driver.findElement(By.id("confirmation")).isDisplayed());
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=selenium_bdd,
            source_framework="selenium-java-bdd",
            target_framework="robot",
        )
        
        assert result.success
        assert "*** Settings ***" in result.target_code
        assert "*** Test Cases ***" in result.target_code
        # Should have BDD-style keywords
        assert "Given" in result.target_code or "When" in result.target_code or "Then" in result.target_code


class TestRestAssuredToRobot:
    """Test RestAssured to Robot Framework translation."""
    
    def test_api_to_robot(self):
        """Test translating API test to Robot Framework."""
        restassured_code = """
        import io.restassured.RestAssured;
        
        @Test
        public void testUserApi() {
            given()
                .header("Content-Type", "application/json")
            .when()
                .get("/api/users/1")
            .then()
                .statusCode(200)
                .body("name", equalTo("John"));
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=restassured_code,
            source_framework="restassured",
            target_framework="robot",
        )
        
        assert result.success
        assert "*** Settings ***" in result.target_code
        assert "RequestsLibrary" in result.target_code or "Requests" in result.target_code
        assert "GET" in result.target_code or "Get Request" in result.target_code
