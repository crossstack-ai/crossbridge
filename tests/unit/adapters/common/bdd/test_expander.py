"""
Unit tests for BDD Scenario Outline expansion.

Tests the deterministic expansion of Scenario Outlines with Examples tables
into concrete scenarios with parameter substitution.
"""
import pytest
from adapters.common.bdd.models import ScenarioOutline, ExamplesTable, ExpandedScenario
from adapters.common.bdd.expander import expand_scenario_outline


class TestBasicExpansion:
    """Test basic scenario outline expansion functionality."""
    
    def test_one_outline_two_rows_produces_two_scenarios(self):
        """One outline + two example rows should produce two ExpandedScenario objects."""
        outline = ScenarioOutline(
            name="User logs in",
            steps=("Given user is on login page",
                   "When user logs in with <username> and <password>",
                   "Then login should be <result>"),
            tags=("auth",)
        )
        
        examples = ExamplesTable(
            headers=("username", "password", "result"),
            rows=(("admin", "admin123", "success"),
                  ("user", "wrong123", "failure"))
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert len(scenarios) == 2
        assert all(isinstance(s, ExpandedScenario) for s in scenarios)
    
    def test_placeholders_replaced_correctly(self):
        """Placeholders should be replaced with actual values from examples."""
        outline = ScenarioOutline(
            name="User logs in",
            steps=("login with <username> and <password>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("username", "password"),
            rows=(("admin", "admin123"),)
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert len(scenarios) == 1
        assert scenarios[0].steps[0] == "login with admin and admin123"
    
    def test_scenario_names_include_parameter_values(self):
        """Scenario names should include parameter values in [value1/value2] format."""
        outline = ScenarioOutline(
            name="User logs in",
            steps=("login with <username> and <password>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("username", "password"),
            rows=(("admin", "admin123"),
                  ("user", "wrong123"))
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        # Parameter suffix should be in alphabetical order by key name
        # password comes before username alphabetically
        assert scenarios[0].name == "User logs in [admin123/admin]"
        assert scenarios[1].name == "User logs in [wrong123/user]"
    
    def test_multiple_placeholders_in_single_step(self):
        """Multiple placeholders in a single step should all be replaced."""
        outline = ScenarioOutline(
            name="Test",
            steps=("Step with <param1> and <param2> and <param3>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("param1", "param2", "param3"),
            rows=(("value1", "value2", "value3"),)
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert scenarios[0].steps[0] == "Step with value1 and value2 and value3"
    
    def test_parameters_dict_populated_correctly(self):
        """ExpandedScenario.parameters should contain correct key-value pairs."""
        outline = ScenarioOutline(
            name="User logs in",
            steps=("login with <username> and <password>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("username", "password", "result"),
            rows=(("admin", "admin123", "success"),)
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert scenarios[0].parameters == {
            "username": "admin",
            "password": "admin123",
            "result": "success"
        }
    
    def test_tags_inherited_from_outline(self):
        """Tags from Scenario Outline should be inherited by expanded scenarios."""
        outline = ScenarioOutline(
            name="User logs in",
            steps=("login with <username>",),
            tags=("auth", "smoke")
        )
        
        examples = ExamplesTable(
            headers=("username",),
            rows=(("admin",),)
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert scenarios[0].tags == ("auth", "smoke")


class TestPlaceholderSafety:
    """Test placeholder validation and error handling."""
    
    def test_missing_placeholder_raises_error(self):
        """Step with placeholder not in examples should raise ValueError."""
        outline = ScenarioOutline(
            name="Test",
            steps=("Step with <missing_param>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("username", "password"),
            rows=(("admin", "admin123"),)
        )
        
        with pytest.raises(ValueError) as exc_info:
            expand_scenario_outline(outline, examples)
        
        assert "missing_param" in str(exc_info.value)
        assert "username, password" in str(exc_info.value)
    
    def test_extra_example_columns_allowed(self):
        """Extra example columns that don't appear in steps should be allowed."""
        outline = ScenarioOutline(
            name="Test",
            steps=("login with <username>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("username", "password", "extra_column"),
            rows=(("admin", "admin123", "extra_value"),)
        )
        
        # Should not raise error
        scenarios = expand_scenario_outline(outline, examples)
        
        assert len(scenarios) == 1
        assert scenarios[0].steps[0] == "login with admin"
        # Extra column should still be in parameters
        assert scenarios[0].parameters["extra_column"] == "extra_value"
    
    def test_placeholder_case_sensitivity(self):
        """Placeholder matching should be case-sensitive."""
        outline = ScenarioOutline(
            name="Test",
            steps=("Step with <UserName>",),  # Capital letters
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("username",),  # lowercase
            rows=(("admin",),)
        )
        
        # Should raise error because case doesn't match
        with pytest.raises(ValueError):
            expand_scenario_outline(outline, examples)


class TestDeterminism:
    """Test deterministic behavior of expansion."""
    
    def test_no_mutation_of_input_outline(self):
        """expand_scenario_outline should not mutate input ScenarioOutline."""
        original_steps = ("login with <username> and <password>",)
        outline = ScenarioOutline(
            name="User logs in",
            steps=original_steps,
            tags=("auth",)
        )
        
        examples = ExamplesTable(
            headers=("username", "password"),
            rows=(("admin", "admin123"),)
        )
        
        expand_scenario_outline(outline, examples)
        
        # Original outline should be unchanged
        assert outline.steps == original_steps
        assert outline.steps[0] == "login with <username> and <password>"
    
    def test_example_row_order_preserved(self):
        """Output order should match example row order exactly."""
        outline = ScenarioOutline(
            name="Test",
            steps=("step with <param>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("param",),
            rows=(("first",), ("second",), ("third",), ("fourth",))
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert len(scenarios) == 4
        assert "first" in scenarios[0].name
        assert "second" in scenarios[1].name
        assert "third" in scenarios[2].name
        assert "fourth" in scenarios[3].name
    
    def test_multiple_calls_produce_identical_results(self):
        """Multiple calls with same inputs should produce identical results."""
        outline = ScenarioOutline(
            name="User logs in",
            steps=("login with <username> and <password>",),
            tags=("auth",)
        )
        
        examples = ExamplesTable(
            headers=("username", "password"),
            rows=(("admin", "admin123"), ("user", "user123"))
        )
        
        # Call twice
        scenarios1 = expand_scenario_outline(outline, examples)
        scenarios2 = expand_scenario_outline(outline, examples)
        
        # Results should be identical
        assert len(scenarios1) == len(scenarios2)
        for s1, s2 in zip(scenarios1, scenarios2):
            assert s1.name == s2.name
            assert s1.steps == s2.steps
            assert s1.parameters == s2.parameters
            assert s1.tags == s2.tags


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_examples_table(self):
        """Empty examples table should produce empty list."""
        outline = ScenarioOutline(
            name="Test",
            steps=("step with <param>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("param",),
            rows=()
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert scenarios == []
    
    def test_step_without_placeholders(self):
        """Steps without placeholders should remain unchanged."""
        outline = ScenarioOutline(
            name="Test",
            steps=("static step without placeholders",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("param",),
            rows=(("value",),)
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert scenarios[0].steps[0] == "static step without placeholders"
    
    def test_numeric_parameter_values(self):
        """Numeric parameter values should be converted to strings."""
        outline = ScenarioOutline(
            name="Test",
            steps=("add <num1> and <num2>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("num1", "num2"),
            rows=((5, 10),)
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert scenarios[0].steps[0] == "add 5 and 10"
        assert scenarios[0].parameters["num1"] == 5  # Original type preserved
        assert scenarios[0].parameters["num2"] == 10
    
    def test_original_outline_name_preserved(self):
        """ExpandedScenario should preserve original outline name."""
        outline = ScenarioOutline(
            name="Original Scenario Name",
            steps=("step with <param>",),
            tags=()
        )
        
        examples = ExamplesTable(
            headers=("param",),
            rows=(("value",),)
        )
        
        scenarios = expand_scenario_outline(outline, examples)
        
        assert scenarios[0].original_outline_name == "Original Scenario Name"
