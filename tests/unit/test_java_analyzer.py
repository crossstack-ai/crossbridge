"""
Unit tests for Java Code Analyzer.
Tests extraction of step definitions, locators, and conversion logic.
"""

import pytest
from core.translation.java_analyzer import (
    JavaCodeAnalyzer,
    JavaStepDefinition,
    ElementLocator,
    StepDefinitionMapper,
    analyze_java_code
)


class TestJavaCodeAnalyzer:
    """Test suite for JavaCodeAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = JavaCodeAnalyzer()
    
    def test_extract_given_step_definition(self):
        """Test extracting @Given step definition."""
        java_code = '''
public class LoginSteps {
    @Given("user is on login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com/login");
    }
}
'''
        steps = self.analyzer._extract_step_definitions(java_code, "LoginSteps.java")
        
        assert len(steps) == 1
        assert steps[0].annotation == "@Given"
        assert steps[0].pattern == "user is on login page"
        assert steps[0].method_name == "userIsOnLoginPage"
    
    def test_extract_when_step_definition(self):
        """Test extracting @When step definition."""
        java_code = '''
    @When("user enters username {string}")
    public void userEntersUsername(String username) {
        driver.findElement(By.id("username")).sendKeys(username);
    }
'''
        steps = self.analyzer._extract_step_definitions(java_code, "test.java")
        
        assert len(steps) == 1
        assert steps[0].annotation == "@When"
        assert steps[0].pattern == "user enters username {string}"
        assert len(steps[0].parameters) == 1
        assert steps[0].parameters[0] == "username"
    
    def test_extract_then_step_definition(self):
        """Test extracting @Then step definition."""
        java_code = '''
    @Then("user should see message {string}")
    public void userShouldSeeMessage(String message) {
        String actual = driver.findElement(By.id("msg")).getText();
        assertEquals(message, actual);
    }
'''
        steps = self.analyzer._extract_step_definitions(java_code, "test.java")
        
        assert len(steps) == 1
        assert steps[0].annotation == "@Then"
        assert "user should see message" in steps[0].pattern
    
    def test_extract_multiple_step_definitions(self):
        """Test extracting multiple step definitions."""
        java_code = '''
public class Steps {
    @Given("step 1")
    public void step1() { }
    
    @When("step 2")
    public void step2() { }
    
    @Then("step 3")
    public void step3() { }
}
'''
        steps = self.analyzer._extract_step_definitions(java_code, "test.java")
        
        assert len(steps) == 3
        assert steps[0].annotation == "@Given"
        assert steps[1].annotation == "@When"
        assert steps[2].annotation == "@Then"
    
    def test_extract_step_with_multiple_parameters(self):
        """Test extracting step with multiple parameters."""
        java_code = '''
    @When("user enters {string} and {string}")
    public void userEntersCredentials(String username, String password) {
        // code
    }
'''
        steps = self.analyzer._extract_step_definitions(java_code, "test.java")
        
        assert len(steps) == 1
        assert len(steps[0].parameters) == 2
        assert steps[0].parameters[0] == "username"
        assert steps[0].parameters[1] == "password"
    
    def test_extract_locator_by_id(self):
        """Test extracting By.id() locator."""
        java_code = '''
    WebElement loginButton = driver.findElement(By.id("login-btn"));
    loginButton.click();
'''
        locators = self.analyzer._extract_locators(java_code, "test.java")
        
        found = [loc for loc in locators if loc.locator_type == "id"]
        assert len(found) > 0
        assert found[0].value == "login-btn"
    
    def test_extract_locator_by_xpath(self):
        """Test extracting By.xpath() locator."""
        java_code = '''
    driver.findElement(By.xpath("//button[@id='submit']")).click();
'''
        locators = self.analyzer._extract_locators(java_code, "test.java")
        
        found = [loc for loc in locators if loc.locator_type == "xpath"]
        assert len(found) > 0
        assert found[0].value == "//button[@id='submit']"
    
    def test_extract_locator_by_css(self):
        """Test extracting By.cssSelector() locator."""
        java_code = '''
    WebElement element = driver.findElement(By.cssSelector(".btn-primary"));
'''
        locators = self.analyzer._extract_locators(java_code, "test.java")
        
        found = [loc for loc in locators if loc.locator_type == "css"]
        assert len(found) > 0
        assert found[0].value == ".btn-primary"
    
    def test_extract_findby_annotation(self):
        """Test extracting @FindBy annotation."""
        java_code = '''
public class LoginPage {
    @FindBy(id = "username")
    private WebElement usernameField;
    
    @FindBy(xpath = "//button[@type='submit']")
    private WebElement submitButton;
}
'''
        locators = self.analyzer._extract_locators(java_code, "LoginPage.java")
        
        id_locators = [loc for loc in locators if loc.locator_type == "id"]
        xpath_locators = [loc for loc in locators if loc.locator_type == "xpath"]
        
        assert len(id_locators) > 0
        assert id_locators[0].value == "username"
        assert len(xpath_locators) > 0
        assert xpath_locators[0].value == "//button[@type='submit']"
    
    def test_extract_multiple_locators(self):
        """Test extracting multiple locators from same file."""
        java_code = '''
    driver.findElement(By.id("field1"));
    driver.findElement(By.name("field2"));
    driver.findElement(By.className("field3"));
'''
        locators = self.analyzer._extract_locators(java_code, "test.java")
        
        assert len(locators) >= 3
        types = [loc.locator_type for loc in locators]
        assert "id" in types
        assert "name" in types
        assert "className" in types
    
    def test_convert_locator_to_robot_id(self):
        """Test converting id locator to Robot syntax."""
        locator = ElementLocator(
            name="LOGIN_BTN",
            locator_type="id",
            value="login-btn",
            file_path="test.java",
            line_number=10
        )
        
        robot_locator = self.analyzer.convert_locator_to_robot(locator)
        
        assert robot_locator == "id=login-btn"
    
    def test_convert_locator_to_robot_xpath(self):
        """Test converting xpath locator to Robot syntax."""
        locator = ElementLocator(
            name="SUBMIT",
            locator_type="xpath",
            value="//button[@type='submit']",
            file_path="test.java",
            line_number=15
        )
        
        robot_locator = self.analyzer.convert_locator_to_robot(locator)
        
        assert robot_locator == "xpath=//button[@type='submit']"
    
    def test_convert_locator_to_robot_css(self):
        """Test converting css locator to Robot syntax."""
        locator = ElementLocator(
            name="BUTTON",
            locator_type="css",
            value=".btn-primary",
            file_path="test.java",
            line_number=20
        )
        
        robot_locator = self.analyzer.convert_locator_to_robot(locator)
        
        assert robot_locator == "css=.btn-primary"
    
    def test_match_step_pattern_with_string(self):
        """Test matching Gherkin step against Cucumber pattern."""
        pattern = "user enters {string} in field"
        gherkin_step = 'user enters "testuser" in field'
        
        params = self.analyzer.match_step_pattern(gherkin_step, pattern)
        
        assert params is not None
        assert "param1" in params
        assert params["param1"] == "testuser"
    
    def test_match_step_pattern_with_int(self):
        """Test matching step pattern with integer parameter."""
        pattern = "user selects {int} items"
        gherkin_step = "user selects 5 items"
        
        params = self.analyzer.match_step_pattern(gherkin_step, pattern)
        
        assert params is not None
        assert "param1" in params
        assert params["param1"] == "5"
    
    def test_match_step_pattern_no_match(self):
        """Test that non-matching step returns None."""
        pattern = "user clicks button"
        gherkin_step = "user enters text"
        
        params = self.analyzer.match_step_pattern(gherkin_step, pattern)
        
        assert params is None
    
    def test_get_step_by_pattern(self):
        """Test finding step definition by pattern."""
        java_code = '''
    @Given("user is on page")
    public void userIsOnPage() { }
'''
        self.analyzer._extract_step_definitions(java_code, "test.java")
        self.analyzer.step_definitions = self.analyzer._extract_step_definitions(java_code, "test.java")
        
        step = self.analyzer.get_step_by_pattern("user is on page")
        
        assert step is not None
        assert step.pattern == "user is on page"
    
    def test_get_locators_by_file(self):
        """Test getting locators from specific file."""
        locator1 = ElementLocator("LOC1", "id", "val1", "file1.java", 1)
        locator2 = ElementLocator("LOC2", "id", "val2", "file2.java", 1)
        locator3 = ElementLocator("LOC3", "id", "val3", "file1.java", 2)
        
        self.analyzer.locators = [locator1, locator2, locator3]
        
        file1_locators = self.analyzer.get_locators_by_file("file1.java")
        
        assert len(file1_locators) == 2
        assert locator1 in file1_locators
        assert locator3 in file1_locators
    
    def test_extract_complex_step_definition(self):
        """Test extracting complex realistic step definition."""
        java_code = '''
public class APISteps {
    @When("user sends POST request to {string} with JSON:")
    public void userSendsPOSTRequest(String endpoint, String jsonPayload) {
        Response response = RestAssured
            .given()
            .contentType(ContentType.JSON)
            .body(jsonPayload)
            .post(endpoint);
        
        context.setResponse(response);
    }
}
'''
        steps = self.analyzer._extract_step_definitions(java_code, "APISteps.java")
        
        assert len(steps) == 1
        assert "@When" in steps[0].annotation
        assert "POST request" in steps[0].pattern
        assert len(steps[0].parameters) == 2


class TestStepDefinitionMapper:
    """Test suite for StepDefinitionMapper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = JavaCodeAnalyzer()
        self.mapper = StepDefinitionMapper(self.analyzer)
    
    def test_generate_keyword_name_from_step(self):
        """Test generating keyword name from Gherkin step."""
        step = "user is on login page"
        keyword_name = self.mapper._generate_keyword_name(step)
        
        assert keyword_name == "User Is On Login Page"
    
    def test_generate_keyword_name_removes_parameters(self):
        """Test that keyword name removes quoted parameters."""
        step = 'user enters "testuser" in field'
        keyword_name = self.mapper._generate_keyword_name(step)
        
        assert "testuser" not in keyword_name
        assert "User Enters" in keyword_name
    
    def test_map_steps_to_keywords_with_no_match(self):
        """Test mapping steps when no Java match found."""
        steps = ["user does something", "user does another thing"]
        
        mappings = self.mapper.map_steps_to_keywords(steps)
        
        assert len(mappings) == 2
        # Should create placeholders
        for step in steps:
            assert step in mappings
            keyword_name, impl = mappings[step]
            assert "TODO" in ' '.join(impl) or "Log" in ' '.join(impl)
    
    def test_convert_java_to_robot_placeholder(self):
        """Test converting Java step to Robot with no implementation."""
        java_step = JavaStepDefinition(
            annotation="@Given",
            pattern="user is on page",
            method_name="userIsOnPage",
            parameters=[],
            body="{ }",
            file_path="test.java",
            line_number=10
        )
        
        impl_lines = self.mapper._convert_java_to_robot(java_step, {})
        
        assert len(impl_lines) > 0
        assert any("[Documentation]" in line for line in impl_lines)


class TestAnalyzeJavaCode:
    """Test the convenience function analyze_java_code."""
    
    def test_analyze_java_code_directory(self, tmp_path):
        """Test analyzing Java files in a directory."""
        # Create test Java files
        java_file1 = tmp_path / "Test1.java"
        java_file1.write_text('''
    @Given("step 1")
    public void step1() { }
''')
        
        java_file2 = tmp_path / "Test2.java"
        java_file2.write_text('''
    @When("step 2")
    public void step2() { }
''')
        
        analyzer = analyze_java_code(str(tmp_path))
        
        assert len(analyzer.step_definitions) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
