"""
Unit tests for Robot Framework Generator.
Tests generation of test files, keywords, resources, and templates.
"""

import pytest
from core.translation.gherkin_parser import (
    GherkinFeature,
    GherkinScenario,
    GherkinStep
)
from core.translation.robot_generator import (
    RobotFrameworkGenerator,
    generate_robot_test_from_feature
)


class TestRobotFrameworkGenerator:
    """Test suite for RobotFrameworkGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = RobotFrameworkGenerator()
    
    def test_generate_simple_test_file(self):
        """Test generating a simple test file."""
        feature = GherkinFeature(
            name="Simple Login",
            description="Login functionality",
            scenarios=[
                GherkinScenario(
                    name="User logs in",
                    type="Scenario",
                    steps=[
                        GherkinStep(keyword="Given", text="user is on login page"),
                        GherkinStep(keyword="When", text="user enters credentials"),
                        GherkinStep(keyword="Then", text="user sees dashboard")
                    ]
                )
            ]
        )
        
        content = self.generator.generate_test_file(
            feature,
            "features/login.feature"
        )
        
        assert "*** Settings ***" in content
        assert "Documentation    Simple Login" in content
        assert "Library          Browser" in content
        assert "*** Test Cases ***" in content
        assert "User Logs In" in content
        assert "User Is On Login Page" in content
        assert "User Enters Credentials" in content
        assert "User Sees Dashboard" in content
    
    def test_generate_test_with_feature_tags(self):
        """Test that feature tags become test tags."""
        feature = GherkinFeature(
            name="Tagged Feature",
            description="",
            tags=["@smoke", "@regression"],
            scenarios=[
                GherkinScenario(
                    name="Test",
                    type="Scenario",
                    steps=[GherkinStep(keyword="Given", text="step")]
                )
            ]
        )
        
        content = self.generator.generate_test_file(feature, "test.feature")
        
        assert "Test Tags        smoke    regression" in content
    
    def test_generate_test_with_scenario_tags(self):
        """Test that scenario tags are preserved."""
        feature = GherkinFeature(
            name="Feature",
            description="",
            scenarios=[
                GherkinScenario(
                    name="Tagged Scenario",
                    type="Scenario",
                    tags=["@critical", "@positive"],
                    steps=[GherkinStep(keyword="Given", text="step")]
                )
            ]
        )
        
        content = self.generator.generate_test_file(feature, "test.feature")
        
        assert "[Tags]    critical    positive" in content
    
    def test_generate_test_with_background(self):
        """Test that background steps are included in test cases."""
        feature = GherkinFeature(
            name="Feature",
            description="",
            background_steps=[
                GherkinStep(keyword="Given", text="application is running"),
                GherkinStep(keyword="And", text="database is connected")
            ],
            scenarios=[
                GherkinScenario(
                    name="Test",
                    type="Scenario",
                    steps=[GherkinStep(keyword="When", text="user logs in")]
                )
            ]
        )
        
        content = self.generator.generate_test_file(feature, "test.feature")
        
        # Background steps should appear in test case
        assert "Application Is Running" in content
        assert "Database Is Connected" in content
        assert "User Logs In" in content
    
    def test_generate_scenario_outline_with_template(self):
        """Test generating scenario outline with test template."""
        feature = GherkinFeature(
            name="Feature",
            description="",
            scenarios=[
                GherkinScenario(
                    name="Login with users",
                    type="Scenario Outline",
                    steps=[
                        GherkinStep(keyword="When", text="user enters <username>"),
                        GherkinStep(keyword="Then", text="result is <result>")
                    ],
                    examples=[{
                        "username": ["admin", "user1"],
                        "result": ["success", "failure"]
                    }]
                )
            ]
        )
        
        content = self.generator.generate_test_file(feature, "test.feature")
        
        assert "[Template]" in content
        assert "admin" in content
        assert "user1" in content
        assert "success" in content
        assert "failure" in content
    
    def test_convert_step_to_keyword_simple(self):
        """Test converting simple step to keyword."""
        step = GherkinStep(keyword="Given", text="user is on login page")
        keyword = self.generator._convert_step_to_keyword(step)
        
        assert keyword == "User Is On Login Page"
    
    def test_convert_step_to_keyword_with_parameters(self):
        """Test converting step with parameters to keyword call."""
        step = GherkinStep(
            keyword="When",
            text='user enters "testuser" and "password123"'
        )
        keyword = self.generator._convert_step_to_keyword(step)
        
        # Should include parameters
        assert "testuser" in keyword
        assert "password123" in keyword
    
    def test_sanitize_name(self):
        """Test name sanitization."""
        assert self.generator._sanitize_name("Test-Name_123") == "Test-Name_123"
        assert self.generator._sanitize_name("Test@Name#") == "TestName"
        assert self.generator._sanitize_name("Test  Name") == "Test Name"
    
    def test_add_locator(self):
        """Test adding locator variable."""
        self.generator.add_locator("LOGIN_BUTTON", "id=login-btn")
        
        assert "LOGIN_BUTTON" in self.generator.locators
        assert self.generator.locators["LOGIN_BUTTON"] == "id=login-btn"
    
    def test_generate_resource_file(self):
        """Test generating a resource file (page object)."""
        keywords = {
            "Open Login Page": [
                "[Documentation]    Opens the login page",
                "New Page    ${LOGIN_URL}"
            ]
        }
        
        locators = {
            "LOGIN_URL": "https://example.com/login",
            "USERNAME_FIELD": "id=username"
        }
        
        content = self.generator.generate_resource_file(
            "Login Page",
            keywords,
            locators
        )
        
        assert "*** Settings ***" in content
        assert "*** Variables ***" in content
        assert "${LOGIN_URL}" in content
        assert "*** Keywords ***" in content
        assert "Open Login Page" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
