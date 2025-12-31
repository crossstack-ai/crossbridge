"""
Tests for Playwright Code Generator

Tests the generation of Playwright Page Objects and pytest-bdd steps.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from migration.generators.playwright_generator import (
    PlaywrightPageObjectGenerator,
    PytestBDDStepGenerator,
    PlaywrightFixtureGenerator,
    MigrationOrchestrator,
)
from adapters.selenium_bdd_java.step_definition_parser import (
    StepDefinitionIntent,
    PageObjectCall,
    SeleniumAction,
)


def test_page_object_generator_creation():
    """Test PageObjectGenerator can be created"""
    generator = PlaywrightPageObjectGenerator()
    assert generator is not None


def test_generate_page_object_with_click():
    """Test generating Page Object with click method"""
    generator = PlaywrightPageObjectGenerator()
    
    method_calls = [
        PageObjectCall(
            page_object_name="loginPage",
            method_name="clickLoginButton",
            parameters=[]
        )
    ]
    
    po = generator.generate_page_object("LoginPage", method_calls)
    
    assert po.class_name == "LoginPage"
    assert "click_login_button" in po.methods
    assert "login_button_locator" in po.locators
    assert ".click()" in po.methods["click_login_button"]


def test_generate_page_object_with_input():
    """Test generating Page Object with input/fill method"""
    generator = PlaywrightPageObjectGenerator()
    
    method_calls = [
        PageObjectCall(
            page_object_name="loginPage",
            method_name="enterUsername",
            parameters=["username"]
        )
    ]
    
    po = generator.generate_page_object("LoginPage", method_calls)
    
    assert "enter_username" in po.methods
    assert "username_input" in po.locators
    assert ".fill(username)" in po.methods["enter_username"]


def test_render_page_object():
    """Test rendering Page Object to Python code"""
    generator = PlaywrightPageObjectGenerator()
    
    method_calls = [
        PageObjectCall(
            page_object_name="loginPage",
            method_name="clickLoginButton",
            parameters=[]
        )
    ]
    
    po = generator.generate_page_object("LoginPage", method_calls)
    code = generator.render_page_object(po)
    
    assert "class LoginPage:" in code
    assert "def __init__(self, page: Page):" in code
    assert "def click_login_button(self):" in code
    assert ".click()" in code


def test_step_generator_creation():
    """Test StepGenerator can be created"""
    generator = PytestBDDStepGenerator()
    assert generator is not None


def test_generate_given_step():
    """Test generating @given step"""
    generator = PytestBDDStepGenerator()
    
    step_def = StepDefinitionIntent(
        step_type="Given",
        pattern="user is on login page",
        pattern_text="user is on login page",
        method_name="userIsOnLoginPage",
        method_body="driver.get('https://example.com')",
        page_object_calls=[],
        selenium_actions=[]
    )
    
    step = generator.generate_step_definition(step_def, {})
    
    assert step.keyword == "given"
    assert "user is on login page" in step.pattern
    assert "user_is_on_login_page" in step.function_name


def test_generate_when_step_with_page_object():
    """Test generating @when step with Page Object call"""
    generator = PytestBDDStepGenerator()
    
    step_def = StepDefinitionIntent(
        step_type="When",
        pattern="user clicks login",
        pattern_text="user clicks login",
        method_name="clickLogin",
        method_body="loginPage.clickLoginButton();",
        page_object_calls=[
            PageObjectCall(
                page_object_name="loginPage",
                method_name="clickLoginButton",
                parameters=[]
            )
        ],
        selenium_actions=[]
    )
    
    step = generator.generate_step_definition(step_def, {"loginPage": "LoginPage"})
    
    assert step.keyword == "when"
    assert "login_page" in step.fixtures
    assert "login_page.click_login_button()" in step.function_body


def test_render_step_definition():
    """Test rendering step definition to Python code"""
    generator = PytestBDDStepGenerator()
    
    step_def = StepDefinitionIntent(
        step_type="Given",
        pattern="user is on login page",
        pattern_text="user is on login page",
        method_name="userIsOnLoginPage",
        method_body="",
        page_object_calls=[],
        selenium_actions=[]
    )
    
    step = generator.generate_step_definition(step_def, {})
    code = generator.render_step_definition(step)
    
    assert '@given("user is on login page")' in code
    assert "def user_is_on_login_page(page):" in code


def test_convert_cucumber_pattern_with_string_param():
    """Test converting Cucumber {string} pattern"""
    generator = PytestBDDStepGenerator()
    
    pattern = "user enters username {string}"
    result = generator._convert_cucumber_pattern(pattern)
    
    assert "{username}" in result or "{param" in result


def test_convert_cucumber_pattern_with_regex():
    """Test converting Cucumber regex pattern"""
    generator = PytestBDDStepGenerator()
    
    pattern = "^user enters password (.*)$"
    result = generator._convert_cucumber_pattern(pattern)
    
    assert "{password}" in result or "{param" in result
    assert "^" not in result
    assert "$" not in result


def test_fixture_generator_page_fixtures():
    """Test generating Page Object fixtures"""
    fixtures = PlaywrightFixtureGenerator.generate_page_fixtures(
        ["LoginPage", "HomePage"]
    )
    
    assert len(fixtures) == 2
    assert any("login_page" in f for f in fixtures)
    assert any("home_page" in f for f in fixtures)
    assert all("@pytest.fixture" in f for f in fixtures)


def test_fixture_generator_base_fixtures():
    """Test generating base Playwright fixtures"""
    fixtures = PlaywrightFixtureGenerator.generate_base_fixtures()
    
    assert "@pytest.fixture(scope=\"session\")" in fixtures
    assert "def browser():" in fixtures
    assert "def page(browser):" in fixtures
    assert "sync_playwright" in fixtures


def test_migration_orchestrator():
    """Test complete migration orchestration"""
    orchestrator = MigrationOrchestrator()
    
    java_step_defs = [
        StepDefinitionIntent(
            step_type="Given",
            pattern="user is on login page",
            pattern_text="user is on login page",
            method_name="userIsOnLoginPage",
            method_body="driver.get('https://example.com')",
            page_object_calls=[],
            selenium_actions=[]
        ),
        StepDefinitionIntent(
            step_type="When",
            pattern="user clicks login",
            pattern_text="user clicks login",
            method_name="clickLogin",
            method_body="loginPage.clickLoginButton();",
            page_object_calls=[
                PageObjectCall(
                    page_object_name="loginPage",
                    method_name="clickLoginButton",
                    parameters=[]
                )
            ],
            selenium_actions=[]
        )
    ]
    
    suite = orchestrator.migrate_step_definitions(
        java_step_defs,
        Path("./output"),
        mode="assistive"
    )
    
    assert len(suite.step_definitions) == 2
    assert len(suite.page_objects) == 1
    assert suite.page_objects[0].class_name == "LoginPage"


def test_to_snake_case_conversion():
    """Test camelCase to snake_case conversion"""
    generator = PlaywrightPageObjectGenerator()
    
    test_cases = [
        ("loginPage", "login_page"),
        ("clickLoginButton", "click_login_button"),
        ("getUserName", "get_user_name"),
        ("APIClient", "api_client"),
    ]
    
    for camel, snake in test_cases:
        assert generator._to_snake_case(camel) == snake


def test_infer_locator_common_elements():
    """Test locator inference for common elements"""
    generator = PlaywrightPageObjectGenerator()
    
    # Username field
    locator = generator._infer_locator("enterUsername")
    assert "username" in locator.lower()
    
    # Password field
    locator = generator._infer_locator("enterPassword")
    assert "password" in locator.lower()
    
    # Login button
    locator = generator._infer_locator("clickLoginButton")
    assert "login" in locator.lower()


def test_migration_with_multiple_page_objects():
    """Test migration with multiple Page Objects"""
    orchestrator = MigrationOrchestrator()
    
    java_step_defs = [
        StepDefinitionIntent(
            step_type="When",
            pattern="user logs in",
            pattern_text="user logs in",
            method_name="login",
            method_body="loginPage.clickLogin(); homePage.verifyDashboard();",
            page_object_calls=[
                PageObjectCall(
                    page_object_name="loginPage",
                    method_name="clickLogin",
                    parameters=[]
                ),
                PageObjectCall(
                    page_object_name="homePage",
                    method_name="verifyDashboard",
                    parameters=[]
                )
            ],
            selenium_actions=[]
        )
    ]
    
    suite = orchestrator.migrate_step_definitions(
        java_step_defs,
        Path("./output")
    )
    
    assert len(suite.page_objects) == 2
    po_names = [po.class_name for po in suite.page_objects]
    assert "LoginPage" in po_names
    assert "HomePage" in po_names


def test_step_with_parameters():
    """Test generating step with parameters"""
    generator = PytestBDDStepGenerator()
    
    step_def = StepDefinitionIntent(
        step_type="When",
        pattern="user enters username {string}",
        pattern_text="user enters username {param}",
        method_name="enterUsername",
        method_body="loginPage.enterUsername(username);",
        page_object_calls=[
            PageObjectCall(
                page_object_name="loginPage",
                method_name="enterUsername",
                parameters=["username"]
            )
        ],
        selenium_actions=[]
    )
    
    step = generator.generate_step_definition(step_def, {"loginPage": "LoginPage"})
    code = generator.render_step_definition(step)
    
    assert "parsers.parse" in code
    assert "{username}" in code
    assert "username" in code  # Parameter in function signature


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
