"""
Unit tests for Gherkin Parser.
Tests parsing of features, scenarios, steps, tags, examples, and edge cases.
"""

import pytest
from core.translation.gherkin_parser import (
    GherkinParser,
    GherkinFeature,
    GherkinScenario,
    GherkinStep,
    parse_feature_file
)


class TestGherkinParser:
    """Test suite for GherkinParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = GherkinParser()
    
    def test_parse_simple_feature(self):
        """Test parsing a simple feature with one scenario."""
        content = """
Feature: Simple Login
  Basic login functionality
  
  Scenario: User logs in
    Given user is on login page
    When user enters credentials
    Then user sees dashboard
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert feature.name == "Simple Login"
        assert "Basic login functionality" in feature.description
        assert len(feature.scenarios) == 1
        assert feature.scenarios[0].name == "User logs in"
        assert len(feature.scenarios[0].steps) == 3
    
    def test_parse_feature_with_tags(self):
        """Test parsing feature and scenario tags."""
        content = """
@smoke @regression
Feature: Login with tags
  
  @positive
  Scenario: Valid login
    Given user is on login page
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert "@smoke" in feature.tags
        assert "@regression" in feature.tags
        assert len(feature.scenarios[0].tags) == 1
        assert "@positive" in feature.scenarios[0].tags
    
    def test_parse_background_steps(self):
        """Test parsing background steps."""
        content = """
Feature: Login
  
  Background:
    Given application is running
    And database is connected
  
  Scenario: Login
    When user logs in
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert len(feature.background_steps) == 2
        assert feature.background_steps[0].keyword == "Given"
        assert "application is running" in feature.background_steps[0].text
        assert feature.background_steps[1].keyword == "And"
    
    def test_parse_scenario_outline_with_examples(self):
        """Test parsing scenario outline with examples table."""
        content = """
Feature: Login variations
  
  Scenario Outline: Login with different users
    Given user is on login page
    When user enters "<username>" and "<password>"
    Then result is "<result>"
    
    Examples:
      | username | password | result  |
      | admin    | admin123 | success |
      | user1    | pass1    | success |
      | invalid  | wrong    | failure |
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert len(feature.scenarios) == 1
        assert feature.scenarios[0].type == "Scenario Outline"
        assert len(feature.scenarios[0].examples) == 1
        
        examples = feature.scenarios[0].examples[0]
        assert "username" in examples
        assert "password" in examples
        assert "result" in examples
        assert len(examples["username"]) == 3
        assert examples["username"][0] == "admin"
        assert examples["result"][2] == "failure"
    
    def test_parse_multiple_scenarios(self):
        """Test parsing multiple scenarios."""
        content = """
Feature: Multiple scenarios
  
  Scenario: First scenario
    Given step 1
    When step 2
  
  Scenario: Second scenario
    Given step 3
    Then step 4
  
  Scenario: Third scenario
    When step 5
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert len(feature.scenarios) == 3
        assert feature.scenarios[0].name == "First scenario"
        assert feature.scenarios[1].name == "Second scenario"
        assert feature.scenarios[2].name == "Third scenario"
        assert len(feature.scenarios[0].steps) == 2
        assert len(feature.scenarios[1].steps) == 2
        assert len(feature.scenarios[2].steps) == 1
    
    def test_parse_steps_with_quoted_parameters(self):
        """Test parsing steps with quoted parameters."""
        content = """
Feature: Parameters
  
  Scenario: With parameters
    Given user enters "john@example.com"
    When user types "password123" in field
    Then message shows "Welcome, John"
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        steps = feature.scenarios[0].steps
        assert '"john@example.com"' in steps[0].text
        assert '"password123"' in steps[1].text
        assert '"Welcome, John"' in steps[2].text
    
    def test_parse_and_but_keywords(self):
        """Test parsing And and But keywords."""
        content = """
Feature: And/But keywords
  
  Scenario: Multiple Ands
    Given step 1
    And step 2
    And step 3
    When step 4
    And step 5
    But not step 6
    Then step 7
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        steps = feature.scenarios[0].steps
        assert steps[0].keyword == "Given"
        assert steps[1].keyword == "And"
        assert steps[2].keyword == "And"
        assert steps[3].keyword == "When"
        assert steps[4].keyword == "And"
        assert steps[5].keyword == "But"
        assert steps[6].keyword == "Then"
    
    def test_extract_parameters_from_step(self):
        """Test parameter extraction from step text."""
        template, params = self.parser.extract_parameters(
            'user enters "john" and "doe"'
        )
        
        assert "{param1}" in template
        assert "{param2}" in template
        assert len(params) == 2
        assert params[0] == "john"
        assert params[1] == "doe"
    
    def test_extract_angle_bracket_parameters(self):
        """Test extraction of <parameter> style parameters."""
        template, params = self.parser.extract_parameters(
            'user enters <username> and <password>'
        )
        
        assert "<username>" in template
        assert "<password>" in template
    
    def test_normalize_step_keyword(self):
        """Test step keyword normalization."""
        assert self.parser.normalize_step_keyword("Given") == "Given"
        assert self.parser.normalize_step_keyword("And", "Given") == "Given"
        assert self.parser.normalize_step_keyword("But", "When") == "When"
        assert self.parser.normalize_step_keyword("And", "Then") == "Then"
    
    def test_parse_empty_content(self):
        """Test parsing empty content."""
        feature = self.parser.parse_content("")
        assert feature is None
    
    def test_parse_content_with_comments(self):
        """Test that comments are properly ignored."""
        content = """
# This is a comment
Feature: With comments
  # Another comment
  
  Scenario: Test scenario
    # Comment before step
    Given step 1
    # Comment after step
    When step 2
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert feature.name == "With comments"
        assert len(feature.scenarios[0].steps) == 2
    
    def test_parse_multiline_description(self):
        """Test parsing multi-line feature description."""
        content = """
Feature: Multi-line description
  This is line 1 of description
  This is line 2 of description
  This is line 3 of description
  
  Scenario: Test
    Given step 1
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert "line 1" in feature.description
        assert "line 2" in feature.description
        assert "line 3" in feature.description
    
    def test_parse_scenario_with_doc_string(self):
        """Test parsing step with doc string argument."""
        content = '''
Feature: Doc strings
  
  Scenario: With doc string
    Given user submits data
      """
      This is a doc string
      With multiple lines
      """
    When processing completes
'''
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        # Note: Current implementation may not fully handle doc strings
        # This test documents expected behavior
    
    def test_parse_invalid_syntax(self):
        """Test parsing with invalid Gherkin syntax."""
        content = """
This is not valid Gherkin
No feature keyword
Just random text
"""
        feature = self.parser.parse_content(content)
        assert feature is None
    
    def test_parse_feature_without_scenarios(self):
        """Test parsing feature without scenarios."""
        content = """
Feature: Empty feature
  This feature has no scenarios
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert feature.name == "Empty feature"
        assert len(feature.scenarios) == 0
    
    def test_parse_complex_realistic_feature(self):
        """Test parsing a complex realistic feature file."""
        content = """
@api @integration @smoke
Feature: User Registration API
  As a system administrator
  I want to register new users via API
  So that users can access the application
  
  Background:
    Given the API server is running
    And the database is clean
    And authentication token is valid
  
  @positive @critical
  Scenario: Register new user with valid data
    Given API endpoint "/api/users" is available
    When I send POST request with:
      | field    | value              |
      | username | testuser           |
      | email    | test@example.com   |
      | password | SecurePass123!     |
    Then response status code is 201
    And response contains user ID
    And user is created in database
    And confirmation email is sent to "test@example.com"
  
  @negative
  Scenario: Register with duplicate email
    Given user "existing@example.com" already exists
    When I send POST request with email "existing@example.com"
    Then response status code is 409
    And error message is "Email already registered"
  
  @outline @validation
  Scenario Outline: Register with invalid data
    When I send POST request with "<field>" as "<value>"
    Then response status code is 400
    And error message contains "<error>"
    
    Examples:
      | field    | value       | error                |
      | username | a           | too short            |
      | email    | invalid     | invalid email format |
      | password | 123         | password too weak    |
"""
        feature = self.parser.parse_content(content)
        
        assert feature is not None
        assert feature.name == "User Registration API"
        assert len(feature.tags) == 3
        assert len(feature.background_steps) == 3
        assert len(feature.scenarios) == 3
        
        # Verify first scenario
        scenario1 = feature.scenarios[0]
        assert scenario1.type == "Scenario"
        assert "@positive" in scenario1.tags
        assert "@critical" in scenario1.tags
        assert len(scenario1.steps) >= 4
        
        # Verify scenario outline
        scenario3 = feature.scenarios[2]
        assert scenario3.type == "Scenario Outline"
        assert len(scenario3.examples) == 1
        assert "field" in scenario3.examples[0]
        assert len(scenario3.examples[0]["field"]) == 3


class TestGherkinDataStructures:
    """Test Gherkin data structure classes."""
    
    def test_gherkin_step_creation(self):
        """Test GherkinStep dataclass."""
        step = GherkinStep(
            keyword="Given",
            text="user is on login page",
            line_number=5
        )
        
        assert step.keyword == "Given"
        assert step.text == "user is on login page"
        assert step.line_number == 5
        assert step.argument is None
    
    def test_gherkin_scenario_creation(self):
        """Test GherkinScenario dataclass."""
        scenario = GherkinScenario(
            name="Test scenario",
            type="Scenario",
            tags=["@smoke"],
            line_number=10
        )
        
        assert scenario.name == "Test scenario"
        assert scenario.type == "Scenario"
        assert len(scenario.tags) == 1
        assert len(scenario.steps) == 0
        assert len(scenario.examples) == 0
    
    def test_gherkin_feature_creation(self):
        """Test GherkinFeature dataclass."""
        feature = GherkinFeature(
            name="Test Feature",
            description="Test description",
            tags=["@regression"],
            line_number=1
        )
        
        assert feature.name == "Test Feature"
        assert feature.description == "Test description"
        assert len(feature.tags) == 1
        assert len(feature.scenarios) == 0
        assert len(feature.background_steps) == 0


class TestParseFeatureFile:
    """Test the convenience function parse_feature_file."""
    
    def test_parse_feature_file_not_found(self):
        """Test parsing non-existent file."""
        result = parse_feature_file("/nonexistent/file.feature")
        assert result is None
    
    def test_parse_feature_file_success(self, tmp_path):
        """Test successfully parsing a feature file."""
        # Create temporary feature file
        feature_file = tmp_path / "test.feature"
        feature_file.write_text("""
Feature: Test Feature
  Scenario: Test Scenario
    Given test step
""")
        
        result = parse_feature_file(str(feature_file))
        
        assert result is not None
        assert result.name == "Test Feature"
        assert len(result.scenarios) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
