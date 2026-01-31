"""
Comprehensive tests for SpecFlow Scenario Outline expansion (Gap 3.1).

Tests cover:
- Scenario Outline parsing
- Examples table extraction
- Parameter replacement
- Tag inheritance
- Multiple Examples tables
- Edge cases (no examples, empty tables)
"""

import pytest
from adapters.selenium_specflow_dotnet.outline_expander import (
    ScenarioOutlineExpander,
    expand_scenario_outlines,
    ScenarioOutline,
    ExamplesTable,
)


class TestScenarioOutlineParsing:
    """Test parsing of Scenario Outlines from feature files"""
    
    def test_parse_simple_outline(self):
        """Test parsing basic Scenario Outline"""
        content = """
Feature: User Login

  Scenario Outline: Login with different credentials
    Given I am on the login page
    When I enter username "<username>"
    And I enter password "<password>"
    Then I should see "<result>"
    
    Examples:
      | username | password | result  |
      | admin    | secret   | success |
      | user     | wrong    | error   |
"""
        
        expander = ScenarioOutlineExpander()
        parsed = expander.parse_feature_file(content)
        
        assert len(parsed) == 1
        assert parsed[0]['type'] == 'outline'
        
        outline = parsed[0]['data']
        assert outline.name == "Login with different credentials"
        assert len(outline.steps) == 4
        assert len(outline.examples) == 1
        assert len(outline.examples[0].rows) == 2
    
    def test_parse_outline_with_tags(self):
        """Test parsing outline with tags"""
        content = """
  @smoke @login
  Scenario Outline: Tagged login test
    Given I am logged in as "<user>"
    
    Examples:
      | user  |
      | admin |
"""
        
        expander = ScenarioOutlineExpander()
        parsed = expander.parse_feature_file(content)
        
        outline = parsed[0]['data']
        assert 'smoke' in outline.tags
        assert 'login' in outline.tags
    
    def test_parse_multiple_examples_tables(self):
        """Test outline with multiple Examples tables"""
        content = """
  Scenario Outline: Multiple data sets
    When I test with "<value>"
    
    Examples: Valid values
      | value |
      | yes   |
      | true  |
    
    Examples: Invalid values
      | value |
      | no    |
      | false |
"""
        
        expander = ScenarioOutlineExpander()
        parsed = expander.parse_feature_file(content)
        
        outline = parsed[0]['data']
        assert len(outline.examples) == 2
        assert len(outline.examples[0].rows) == 2
        assert len(outline.examples[1].rows) == 2
    
    def test_parse_examples_with_tags(self):
        """Test Examples tables with their own tags"""
        content = """
  Scenario Outline: Test
    Given step with "<param>"
    
    @positive
    Examples:
      | param |
      | good  |
    
    @negative
    Examples:
      | param |
      | bad   |
"""
        
        expander = ScenarioOutlineExpander()
        parsed = expander.parse_feature_file(content)
        
        outline = parsed[0]['data']
        assert 'positive' in outline.examples[0].tags
        assert 'negative' in outline.examples[1].tags


class TestScenarioExpansion:
    """Test expansion of outlines into individual scenarios"""
    
    def test_expand_simple_outline(self):
        """Test basic expansion"""
        outline = ScenarioOutline(
            name="Login test",
            steps=[
                "Given I enter username '<username>'",
                "When I enter password '<password>'",
                "Then I see '<result>'"
            ],
            tags=['smoke'],
            examples=[
                ExamplesTable(
                    headers=['username', 'password', 'result'],
                    rows=[
                        ['admin', 'secret', 'success'],
                        ['user', 'wrong', 'error']
                    ]
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        assert len(expanded) == 2
        
        # First scenario
        assert 'admin' in expanded[0].name
        assert expanded[0].steps[0] == "Given I enter username 'admin'"
        assert expanded[0].steps[1] == "When I enter password 'secret'"
        assert expanded[0].steps[2] == "Then I see 'success'"
        assert expanded[0].example_data == {'username': 'admin', 'password': 'secret', 'result': 'success'}
        assert expanded[0].example_index == 0
        
        # Second scenario
        assert 'user' in expanded[1].name
        assert expanded[1].steps[0] == "Given I enter username 'user'"
        assert expanded[1].example_data == {'username': 'user', 'password': 'wrong', 'result': 'error'}
        assert expanded[1].example_index == 1
    
    def test_expand_with_tag_inheritance(self):
        """Test that tags are inherited correctly"""
        outline = ScenarioOutline(
            name="Test",
            steps=["Given step '<param>'"],
            tags=['outline_tag'],
            examples=[
                ExamplesTable(
                    headers=['param'],
                    rows=[['value']],
                    tags=['example_tag']
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        assert 'outline_tag' in expanded[0].tags
        assert 'example_tag' in expanded[0].tags
    
    def test_expand_multiple_examples_tables(self):
        """Test expansion with multiple Examples tables"""
        outline = ScenarioOutline(
            name="Test",
            steps=["Given step '<value>'"],
            tags=[],
            examples=[
                ExamplesTable(
                    headers=['value'],
                    rows=[['a'], ['b']]
                ),
                ExamplesTable(
                    headers=['value'],
                    rows=[['x'], ['y'], ['z']]
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        # Should have 2 + 3 = 5 scenarios
        assert len(expanded) == 5
        
        # Check examples_table_index
        assert expanded[0].examples_table_index == 0
        assert expanded[1].examples_table_index == 0
        assert expanded[2].examples_table_index == 1
        assert expanded[3].examples_table_index == 1
        assert expanded[4].examples_table_index == 1
    
    def test_expand_with_multiple_parameters(self):
        """Test expansion with multiple parameters per step"""
        outline = ScenarioOutline(
            name="Complex test",
            steps=[
                "Given user '<user>' with role '<role>'",
                "When action '<action>' is performed",
                "Then result is '<result>'"
            ],
            tags=[],
            examples=[
                ExamplesTable(
                    headers=['user', 'role', 'action', 'result'],
                    rows=[
                        ['john', 'admin', 'delete', 'success'],
                        ['jane', 'user', 'delete', 'forbidden']
                    ]
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        assert expanded[0].steps[0] == "Given user 'john' with role 'admin'"
        assert expanded[0].steps[1] == "When action 'delete' is performed"
        assert expanded[1].steps[0] == "Given user 'jane' with role 'user'"
        assert expanded[1].steps[2] == "Then result is 'forbidden'"


class TestFullExpansion:
    """Test end-to-end expansion of feature files"""
    
    def test_expand_all_outlines(self):
        """Test expanding all outlines in a feature file"""
        content = """
Feature: Login Feature

  Scenario: Regular login
    Given I am on login page
    When I login
    Then I see dashboard
  
  Scenario Outline: Data-driven login
    Given I enter "<username>"
    When I enter "<password>"
    Then I see "<result>"
    
    Examples:
      | username | password | result |
      | admin    | pass     | ok     |
      | user     | wrong    | error  |
"""
        
        result = expand_scenario_outlines(content)
        
        assert result['total_regular'] == 1
        assert result['total_expanded'] == 2
        assert result['total_scenarios'] == 3
        
        # Check regular scenario
        assert result['regular_scenarios'][0]['name'] == "Regular login"
        
        # Check expanded scenarios
        expanded = result['expanded_scenarios']
        assert len(expanded) == 2
        assert 'admin' in expanded[0]['name']
        assert expanded[0]['source_outline'] == "Data-driven login"
        assert expanded[0]['example_data']['username'] == 'admin'
    
    def test_expand_with_mixed_scenarios(self):
        """Test feature with both regular and outline scenarios"""
        content = """
Feature: Mixed scenarios

  @smoke
  Scenario: First regular
    Given step 1

  @regression
  Scenario Outline: First outline
    Given step "<param>"
    
    Examples:
      | param |
      | a     |
      | b     |
  
  Scenario: Second regular
    Given step 2
  
  Scenario Outline: Second outline
    When I use "<value>"
    
    Examples:
      | value |
      | x     |
"""
        
        result = expand_scenario_outlines(content)
        
        assert result['total_regular'] == 2
        assert result['total_expanded'] == 3  # 2 from first outline + 1 from second
        assert result['total_scenarios'] == 5


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_outline_without_examples(self):
        """Test outline with no Examples table"""
        content = """
  Scenario Outline: No examples
    Given step "<param>"
"""
        
        expander = ScenarioOutlineExpander()
        parsed = expander.parse_feature_file(content)
        
        if parsed:
            outline = parsed[0]['data']
            expanded = expander.expand_outline(outline)
            assert len(expanded) == 0  # No examples = no expanded scenarios
    
    def test_empty_examples_table(self):
        """Test Examples table with no data rows"""
        outline = ScenarioOutline(
            name="Test",
            steps=["Given step '<param>'"],
            tags=[],
            examples=[
                ExamplesTable(
                    headers=['param'],
                    rows=[]  # No data rows
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        assert len(expanded) == 0
    
    def test_parameter_not_in_steps(self):
        """Test when Examples has parameter not used in steps"""
        outline = ScenarioOutline(
            name="Test",
            steps=["Given step '<used>'"],
            tags=[],
            examples=[
                ExamplesTable(
                    headers=['used', 'unused'],
                    rows=[['value1', 'value2']]
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        # Should still expand, just unused parameter won't be replaced
        assert len(expanded) == 1
        assert expanded[0].steps[0] == "Given step 'value1'"
        assert 'unused' in expanded[0].example_data
    
    def test_empty_feature_file(self):
        """Test empty or whitespace-only feature file"""
        content = "\n\n   \n\n"
        
        result = expand_scenario_outlines(content)
        
        assert result['total_scenarios'] == 0
        assert result['total_regular'] == 0
        assert result['total_expanded'] == 0


class TestScenarioNaming:
    """Test generated names for expanded scenarios"""
    
    def test_name_includes_parameters(self):
        """Test that generated name includes parameter values"""
        outline = ScenarioOutline(
            name="Original name",
            steps=["Given step '<a>'"],
            tags=[],
            examples=[
                ExamplesTable(
                    headers=['a'],
                    rows=[['value1']]
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        assert 'Original name' in expanded[0].name
        assert 'value1' in expanded[0].name
    
    def test_name_with_multiple_parameters(self):
        """Test name generation with multiple parameters"""
        outline = ScenarioOutline(
            name="Test",
            steps=["Given '<a>' and '<b>'"],
            tags=[],
            examples=[
                ExamplesTable(
                    headers=['a', 'b', 'c'],
                    rows=[['val1', 'val2', 'val3']]
                )
            ]
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        # Should include first few parameters in name
        name = expanded[0].name
        assert 'val1' in name
        assert 'val2' in name


class TestSerialization:
    """Test conversion to dictionaries for storage"""
    
    def test_expanded_scenario_to_dict(self):
        """Test ExpandedScenario.to_dict()"""
        outline = ScenarioOutline(
            name="Test",
            steps=["Given '<param>'"],
            tags=['tag1'],
            examples=[
                ExamplesTable(
                    headers=['param'],
                    rows=[['value']]
                )
            ],
            line_number=10
        )
        
        expander = ScenarioOutlineExpander()
        expanded = expander.expand_outline(outline)
        
        result_dict = expanded[0].to_dict()
        
        assert result_dict['type'] == 'expanded_scenario'
        assert result_dict['original_name'] == 'Test'
        assert result_dict['source_outline'] == 'Test'
        assert result_dict['example_data'] == {'param': 'value'}
        assert result_dict['example_index'] == 0
        assert result_dict['line_number'] == 10
        assert 'tag1' in result_dict['tags']
