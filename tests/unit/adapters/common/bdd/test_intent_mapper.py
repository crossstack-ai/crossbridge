"""
Unit tests for BDD intent mapping.

Tests conversion of ExpandedScenario to IntentModel for migration pipeline.
"""
import pytest
from adapters.common.models import IntentModel, TestStep, Assertion, AssertionType
from adapters.common.bdd.models import ExpandedScenario
from adapters.common.bdd.intent_mapper import map_expanded_scenario_to_intent


class TestIntentMapping:
    """Test mapping of ExpandedScenario to IntentModel."""
    
    def test_test_name_populated_correctly(self):
        """IntentModel.test_name should match ExpandedScenario.name."""
        scenario = ExpandedScenario(
            name="User logs in [admin/admin123]",
            steps=("Given user is on login page",),
            parameters={"username": "admin", "password": "admin123"},
            tags=("auth",),
            original_outline_name="User logs in"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.test_name == "User logs in [admin/admin123]"
    
    def test_intent_extracted_from_original_outline_name(self):
        """IntentModel.intent should be the original outline name without parameters."""
        scenario = ExpandedScenario(
            name="User logs in [admin/admin123]",
            steps=("Given user is on login page",),
            parameters={"username": "admin", "password": "admin123"},
            tags=("auth",),
            original_outline_name="User logs in"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.intent == "User logs in"
    
    def test_intent_extracted_when_no_original_outline_name(self):
        """IntentModel.intent should be derived from name if original_outline_name missing."""
        scenario = ExpandedScenario(
            name="User logs in [admin/admin123]",
            steps=("Given user is on login page",),
            parameters={"username": "admin", "password": "admin123"},
            tags=("auth",),
            original_outline_name=""
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.intent == "User logs in"
    
    def test_steps_parsed_into_test_steps(self):
        """BDD steps should be parsed into TestStep objects."""
        scenario = ExpandedScenario(
            name="User logs in [admin/admin123]",
            steps=(
                "Given user is on login page",
                "When user logs in with admin and admin123",
                "Then login should be success"
            ),
            parameters={"username": "admin", "password": "admin123", "result": "success"},
            tags=(),
            original_outline_name="User logs in"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert len(intent.steps) == 3
        assert all(isinstance(step, TestStep) for step in intent.steps)
    
    def test_given_step_parsed_correctly(self):
        """Given steps should have correct action and description."""
        scenario = ExpandedScenario(
            name="Test",
            steps=("Given user is on login page",),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps[0].action == "Given"
        assert intent.steps[0].description == "Given user is on login page"
        assert intent.steps[0].target == "login page"
    
    def test_when_step_parsed_correctly(self):
        """When steps should have correct action and description."""
        scenario = ExpandedScenario(
            name="Test",
            steps=("When user logs in with admin and admin123",),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps[0].action == "When"
        assert intent.steps[0].description == "When user logs in with admin and admin123"
    
    def test_then_step_parsed_correctly(self):
        """Then steps should have correct action and description."""
        scenario = ExpandedScenario(
            name="Test",
            steps=("Then login should be success",),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps[0].action == "Then"
        assert intent.steps[0].description == "Then login should be success"
    
    def test_and_step_parsed_correctly(self):
        """And steps should have correct action."""
        scenario = ExpandedScenario(
            name="Test",
            steps=("And user sees welcome message",),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps[0].action == "And"
    
    def test_but_step_parsed_correctly(self):
        """But steps should have correct action."""
        scenario = ExpandedScenario(
            name="Test",
            steps=("But user does not see error",),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps[0].action == "But"
    
    def test_assertions_extracted_from_then_steps(self):
        """Then steps should be converted to assertions."""
        scenario = ExpandedScenario(
            name="Test",
            steps=(
                "Given user is on login page",
                "When user logs in",
                "Then login should be success",
                "Then user sees dashboard"
            ),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert len(intent.assertions) == 2
        assert all(isinstance(assertion, Assertion) for assertion in intent.assertions)
    
    def test_step_without_keyword_handled(self):
        """Steps without BDD keywords should still be parsed."""
        scenario = ExpandedScenario(
            name="Test",
            steps=("user performs an action",),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert len(intent.steps) == 1
        assert intent.steps[0].action == "Step"
        assert intent.steps[0].description == "user performs an action"
    
    def test_target_extraction_from_quoted_text(self):
        """Target should be extracted from quoted text in step."""
        scenario = ExpandedScenario(
            name="Test",
            steps=('When user clicks "Login" button',),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps[0].target == "Login"
    
    def test_target_extraction_from_page_reference(self):
        """Target should be extracted from 'on <page>' pattern."""
        scenario = ExpandedScenario(
            name="Test",
            steps=("Given user is on login page",),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps[0].target == "login page"
    
    def test_empty_steps_produces_empty_lists(self):
        """Scenario with no steps should produce empty steps and assertions."""
        scenario = ExpandedScenario(
            name="Test",
            steps=(),
            parameters={},
            tags=(),
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.steps == []
        assert intent.assertions == []
    
    def test_intent_model_structure_complete(self):
        """IntentModel should have all required fields populated."""
        scenario = ExpandedScenario(
            name="User logs in [admin/admin123]",
            steps=(
                "Given user is on login page",
                "When user logs in with admin and admin123",
                "Then login should be success"
            ),
            parameters={"username": "admin", "password": "admin123", "result": "success"},
            tags=("auth", "smoke"),
            original_outline_name="User logs in"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        # Verify all IntentModel fields are populated
        assert isinstance(intent, IntentModel)
        assert isinstance(intent.test_name, str)
        assert isinstance(intent.intent, str)
        assert isinstance(intent.steps, list)
        assert isinstance(intent.assertions, list)
        assert intent.test_name != ""
        assert intent.intent != ""


class TestComplexScenarios:
    """Test mapping of complex real-world scenarios."""
    
    def test_login_scenario_with_multiple_steps(self):
        """Complex login scenario should map correctly."""
        scenario = ExpandedScenario(
            name="User logs in [admin/admin123]",
            steps=(
                "Given user is on login page",
                "And login form is visible",
                "When user enters admin into username field",
                "And user enters admin123 into password field",
                "And user clicks Login button",
                "Then login should be success",
                "And user sees dashboard"
            ),
            parameters={"username": "admin", "password": "admin123"},
            tags=("auth", "critical"),
            original_outline_name="User logs in"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert len(intent.steps) == 7
        assert len(intent.assertions) == 1  # One Then assertion ("And" after action steps is not assertion)
        assert intent.intent == "User logs in"
    
    def test_scenario_with_numeric_parameters(self):
        """Scenario with numeric parameters should map correctly."""
        scenario = ExpandedScenario(
            name="Add items to cart [3/5]",
            steps=(
                "Given user has 3 items in cart",
                "When user adds 5 more items",
                "Then cart should contain 8 items"
            ),
            parameters={"initial": 3, "added": 5},
            tags=("cart",),
            original_outline_name="Add items to cart"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.test_name == "Add items to cart [3/5]"
        assert intent.intent == "Add items to cart"
        assert len(intent.steps) == 3
        assert len(intent.assertions) == 1
