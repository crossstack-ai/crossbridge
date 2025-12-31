"""
Tests for Robot Framework Code Generator

Tests the generation of Robot Framework resource files and test cases.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from migration.generators.robot_generator import (
    RobotResourceGenerator,
    RobotTestGenerator,
    RobotMigrationOrchestrator,
)
from adapters.selenium_bdd_java.step_definition_parser import (
    StepDefinitionIntent,
    PageObjectCall,
)


def test_resource_generator_creation():
    """Test ResourceGenerator can be created"""
    generator = RobotResourceGenerator()
    assert generator is not None


def test_generate_resource_with_click():
    """Test generating Resource with click keyword"""
    generator = RobotResourceGenerator()
    
    method_calls = [
        PageObjectCall(
            page_object_name="loginPage",
            method_name="clickLoginButton",
            parameters=[]
        )
    ]
    
    resource = generator.generate_resource("LoginPage", method_calls)
    
    assert resource.resource_name == "LoginPage"
    assert "Click Login Button" in resource.keywords
    assert "LOGIN_BUTTON_LOCATOR" in resource.variables


def test_generate_resource_with_input():
    """Test generating Resource with input keyword"""
    generator = RobotResourceGenerator()
    
    method_calls = [
        PageObjectCall(
            page_object_name="loginPage",
            method_name="enterUsername",
            parameters=["username"]
        )
    ]
    
    resource = generator.generate_resource("LoginPage", method_calls)
    
    assert "Enter Username" in resource.keywords
    assert "USERNAME_LOCATOR" in resource.variables
    keyword = resource.keywords["Enter Username"]
    assert "${username}" in keyword.arguments or any("username" in arg for arg in keyword.arguments)


def test_render_resource():
    """Test rendering Resource to Robot Framework file"""
    generator = RobotResourceGenerator()
    
    method_calls = [
        PageObjectCall(
            page_object_name="loginPage",
            method_name="clickLoginButton",
            parameters=[]
        )
    ]
    
    resource = generator.generate_resource("LoginPage", method_calls)
    content = generator.render_resource(resource)
    
    assert "*** Settings ***" in content
    assert "Library    Browser" in content
    assert "*** Variables ***" in content
    assert "*** Keywords ***" in content
    assert "Click Login Button" in content


def test_test_generator_creation():
    """Test TestGenerator can be created"""
    generator = RobotTestGenerator()
    assert generator is not None


def test_generate_test_case():
    """Test generating test case"""
    generator = RobotTestGenerator()
    
    step_def = StepDefinitionIntent(
        step_type="Given",
        pattern="user is on login page",
        pattern_text="user is on login page",
        method_name="userIsOnLoginPage",
        method_body="driver.get('https://example.com')",
        page_object_calls=[],
        selenium_actions=[]
    )
    
    test_case = generator.generate_test_case(step_def, {})
    
    assert test_case.name == "User Is On Login Page"
    assert len(test_case.steps) > 0


def test_generate_test_with_page_object():
    """Test generating test with Page Object call"""
    generator = RobotTestGenerator()
    
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
    
    test_case = generator.generate_test_case(step_def, {"loginpage": "LoginPage"})
    
    assert "Click Login Button" in test_case.steps[0]


def test_robot_orchestrator():
    """Test complete Robot migration orchestration"""
    orchestrator = RobotMigrationOrchestrator()
    
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
        Path("./output")
    )
    
    assert len(suite.test_cases) == 2
    assert len(suite.resources) == 1
    assert suite.resources[0].resource_name == "LoginPage"


def test_locator_inference():
    """Test smart locator inference"""
    generator = RobotResourceGenerator()
    
    # Test username field
    result = generator._infer_locator_variable("enterUsername")
    assert "username" in result["value"].lower()
    
    # Test password field
    result = generator._infer_locator_variable("enterPassword")
    assert "password" in result["value"].lower()
    
    # Test login button
    result = generator._infer_locator_variable("clickLoginButton")
    assert "submit" in result["value"] or "button" in result["value"]


def test_camel_to_title_case():
    """Test camelCase to Title Case conversion"""
    generator = RobotResourceGenerator()
    
    test_cases = [
        ("clickLoginButton", "Click Login Button"),
        ("enterUsername", "Enter Username"),
        ("verifyWelcomeMessage", "Verify Welcome Message"),
    ]
    
    for camel, expected in test_cases:
        result = generator._to_title_case(camel)
        assert result == expected, f"Expected {expected}, got {result}"


def test_locator_variable_naming():
    """Test locator variable naming"""
    generator = RobotResourceGenerator()
    
    test_cases = [
        ("clickLoginButton", "LOGIN_BUTTON_LOCATOR"),
        ("enterUsername", "USERNAME_LOCATOR"),
        ("submitForm", "SUBMIT_FORM_LOCATOR"),  # Fixed: includes 'submit' word
    ]
    
    for method_name, expected in test_cases:
        result = generator._get_locator_var_name(method_name)
        assert result == expected, f"Expected {expected}, got {result}"


def test_multiple_resources():
    """Test migration with multiple resources"""
    orchestrator = RobotMigrationOrchestrator()
    
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
    
    assert len(suite.resources) == 2
    resource_names = [r.resource_name for r in suite.resources]
    assert "LoginPage" in resource_names
    assert "HomePage" in resource_names


def test_render_test_suite():
    """Test rendering complete test suite"""
    orchestrator = RobotMigrationOrchestrator()
    
    java_step_defs = [
        StepDefinitionIntent(
            step_type="Given",
            pattern="user is on login page",
            pattern_text="user is on login page",
            method_name="userIsOnLoginPage",
            method_body="",
            page_object_calls=[],
            selenium_actions=[]
        )
    ]
    
    suite = orchestrator.migrate_step_definitions(
        java_step_defs,
        Path("./output")
    )
    
    content = orchestrator._render_test_suite(suite)
    
    assert "*** Settings ***" in content
    assert "*** Test Cases ***" in content
    assert "User Is On Login Page" in content


def test_keyword_with_multiple_arguments():
    """Test keyword with multiple parameters"""
    generator = RobotResourceGenerator()
    
    method_calls = [
        PageObjectCall(
            page_object_name="loginPage",
            method_name="login",
            parameters=["username", "password"]
        )
    ]
    
    resource = generator.generate_resource("LoginPage", method_calls)
    keyword = resource.keywords.get("Login")
    
    # Keyword should be created (even if generic)
    assert keyword is not None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
