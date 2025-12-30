"""Test intent_mapper with resolver integration."""
import pytest
from adapters.common.bdd.intent_mapper import map_expanded_scenario_to_intent
from adapters.common.bdd.models import ExpandedScenario
from adapters.common.mapping import (
    StepSignal,
    SignalType,
    StepSignalRegistry,
    StepMappingResolver,
)


class TestIntentMapperWithResolver:
    """Test intent mapper with step-to-code resolver integration."""
    
    def test_intent_mapper_without_resolver(self):
        """Intent mapper works without resolver (backward compatibility)."""
        scenario = ExpandedScenario(
            name="User Login Test [admin/admin123]",
            steps=(
                "Given user is on login page",
                "When user logs in with admin and admin123",
                "Then user should see dashboard"
            ),
            parameters={"username": "admin", "password": "admin123"},
            original_outline_name="User Login Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario)
        
        assert intent.test_name == "User Login Test [admin/admin123]"
        assert intent.intent == "User Login Test"
        assert len(intent.steps) == 3
        assert intent.code_paths == []  # No resolver, no code paths
    
    def test_intent_mapper_with_resolver_populates_code_paths(self):
        """Intent mapper populates code_paths when resolver is provided."""
        # Setup registry with signals
        registry = StepSignalRegistry()
        registry.register_signal(
            "user is on login page",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.open"
            )
        )
        registry.register_signal(
            "user logs in",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.login"
            )
        )
        registry.register_signal(
            "should see dashboard",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/dashboard_page.py::DashboardPage.is_visible"
            )
        )
        
        resolver = StepMappingResolver(registry)
        
        scenario = ExpandedScenario(
            name="User Login Test [admin/admin123]",
            steps=(
                "Given user is on login page",
                "When user logs in with admin and admin123",
                "Then user should see dashboard"
            ),
            parameters={"username": "admin", "password": "admin123"},
            original_outline_name="User Login Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario, resolver)
        
        assert intent.test_name == "User Login Test [admin/admin123]"
        assert len(intent.code_paths) == 3
        assert "pages/login_page.py::LoginPage.open" in intent.code_paths
        assert "pages/login_page.py::LoginPage.login" in intent.code_paths
        assert "pages/dashboard_page.py::DashboardPage.is_visible" in intent.code_paths
    
    def test_code_paths_are_unique(self):
        """Code paths are deduplicated across steps."""
        registry = StepSignalRegistry()
        # Register same code path for multiple step patterns
        registry.register_signal(
            "user is on page",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/base_page.py::BasePage.wait"
            )
        )
        registry.register_signal(
            "user clicks",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/base_page.py::BasePage.wait"
            )
        )
        
        resolver = StepMappingResolver(registry)
        
        scenario = ExpandedScenario(
            name="Test",
            steps=(
                "Given user is on page",
                "When user clicks button"
            ),
            parameters={},
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario, resolver)
        
        # Should only have one instance of the code path
        assert len(intent.code_paths) == 1
        assert intent.code_paths[0] == "pages/base_page.py::BasePage.wait"
    
    def test_code_paths_preserve_order(self):
        """Code paths maintain order of first appearance."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "step one",
            StepSignal(type=SignalType.CODE_PATH, value="path1.py::Class1.method1")
        )
        registry.register_signal(
            "step two",
            StepSignal(type=SignalType.CODE_PATH, value="path2.py::Class2.method2")
        )
        registry.register_signal(
            "step three",
            StepSignal(type=SignalType.CODE_PATH, value="path3.py::Class3.method3")
        )
        
        resolver = StepMappingResolver(registry)
        
        scenario = ExpandedScenario(
            name="Test",
            steps=("Given step one", "When step two", "Then step three"),
            parameters={},
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario, resolver)
        
        assert intent.code_paths == [
            "path1.py::Class1.method1",
            "path2.py::Class2.method2",
            "path3.py::Class3.method3"
        ]
    
    def test_steps_without_signals_dont_break(self):
        """Steps without registered signals don't cause errors."""
        registry = StepSignalRegistry()
        # Only register signal for one step
        registry.register_signal(
            "user logs in",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.login"
            )
        )
        
        resolver = StepMappingResolver(registry)
        
        scenario = ExpandedScenario(
            name="Test",
            steps=(
                "Given user is on unknown page",  # No signal
                "When user logs in",               # Has signal
                "Then something happens"           # No signal
            ),
            parameters={},
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario, resolver)
        
        # Only the step with a signal contributes code paths
        assert len(intent.code_paths) == 1
        assert intent.code_paths[0] == "pages/login_page.py::LoginPage.login"
    
    def test_multiple_signals_per_step(self):
        """Multiple signals per step all contribute code paths."""
        registry = StepSignalRegistry()
        # Register multiple signals for same pattern
        registry.register_signal(
            "user creates order",
            StepSignal(type=SignalType.CODE_PATH, value="pages/order_page.py::OrderPage.create")
        )
        registry.register_signal(
            "creates order",
            StepSignal(type=SignalType.CODE_PATH, value="api/order_api.py::OrderAPI.post_order")
        )
        
        resolver = StepMappingResolver(registry)
        
        scenario = ExpandedScenario(
            name="Test",
            steps=("When user creates order",),
            parameters={},
            original_outline_name="Test"
        )
        
        intent = map_expanded_scenario_to_intent(scenario, resolver)
        
        assert len(intent.code_paths) == 2
        assert "pages/order_page.py::OrderPage.create" in intent.code_paths
        assert "api/order_api.py::OrderAPI.post_order" in intent.code_paths
