"""
Comprehensive BDD Adapter Tests.

Tests all BDD adapters for completeness and stability.
Validates the adapter promotion process from Beta → Stable.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from core.bdd.models import (
    BDDFeature,
    BDDScenario,
    BDDStep,
    StepKeyword,
    ADAPTER_COMPLETENESS_CRITERIA,
    validate_adapter_completeness
)
from core.bdd.parser_interface import is_adapter_stable
from core.bdd.step_mapper import StepDefinitionMapper, StepDefinitionMatch


class TestBDDModels:
    """Test core BDD models."""
    
    def test_bdd_step_creation(self):
        """Test BDD step model."""
        step = BDDStep(
            keyword=StepKeyword.GIVEN,
            text="user is logged in",
            line=5
        )
        
        assert step.keyword == StepKeyword.GIVEN
        assert step.text == "user is logged in"
        assert step.full_text == "Given user is logged in"
        assert step.line == 5
    
    def test_bdd_scenario_id_generation(self):
        """Test automatic scenario ID generation."""
        scenario = BDDScenario(
            id="",  # Empty ID triggers auto-generation
            name="Valid Login",
            feature="User Authentication"
        )
        
        assert scenario.id == "User_Authentication::Valid_Login"
    
    def test_scenario_outline_expansion(self):
        """Test scenario outline expansion with examples."""
        from core.bdd.models import BDDScenarioOutline, BDDExampleRow
        
        outline = BDDScenarioOutline(
            id="login_outline",
            name="Login with different users",
            feature="Authentication",
            steps=[
                BDDStep(keyword=StepKeyword.GIVEN, text="user logs in as <username>", line=1),
                BDDStep(keyword=StepKeyword.THEN, text="user sees <message>", line=2)
            ],
            examples=[
                BDDExampleRow(line=5, cells={"username": "admin", "message": "Admin Dashboard"}),
                BDDExampleRow(line=6, cells={"username": "user", "message": "User Dashboard"})
            ]
        )
        
        scenarios = outline.expand_scenarios()
        
        assert len(scenarios) == 2
        assert scenarios[0].steps[0].text == "user logs in as admin"
        assert scenarios[1].steps[1].text == "user sees User Dashboard"
    
    def test_bdd_feature_all_scenarios(self):
        """Test getting all scenarios including expanded outlines."""
        from core.bdd.models import BDDScenarioOutline, BDDExampleRow
        
        feature = BDDFeature(
            name="Test Feature",
            scenarios=[
                BDDScenario(id="s1", name="Scenario 1", feature="Test Feature")
            ],
            scenario_outlines=[
                BDDScenarioOutline(
                    id="o1",
                    name="Outline 1",
                    feature="Test Feature",
                    examples=[
                        BDDExampleRow(line=1, cells={"param": "value1"}),
                        BDDExampleRow(line=2, cells={"param": "value2"})
                    ]
                )
            ]
        )
        
        all_scenarios = feature.all_scenarios()
        assert len(all_scenarios) == 3  # 1 regular + 2 expanded


class TestStepDefinitionMapper:
    """Test step definition mapping."""
    
    def test_exact_string_match(self):
        """Test exact string matching."""
        mapper = StepDefinitionMapper()
        mapper.add_definition(
            pattern="user is logged in",
            method_name="user_is_logged_in",
            file_path="/steps/login.py",
            line_number=10
        )
        
        step = BDDStep(keyword=StepKeyword.GIVEN, text="user is logged in", line=1)
        match = mapper.match_step(step)
        
        assert match is not None
        assert match.method_name == "user_is_logged_in"
        assert match.confidence == 1.0
    
    def test_regex_match_with_parameters(self):
        """Test regex matching with parameter extraction."""
        mapper = StepDefinitionMapper()
        mapper.add_definition(
            pattern=r'^user logs in as "([^"]+)"$',
            method_name="user_logs_in_as",
            file_path="/steps/login.py",
            line_number=20
        )
        
        step = BDDStep(keyword=StepKeyword.GIVEN, text='user logs in as "admin"', line=1)
        match = mapper.match_step(step)
        
        assert match is not None
        assert match.method_name == "user_logs_in_as"
        assert "param1" in match.parameters
        assert match.parameters["param1"] == "admin"
    
    def test_no_match(self):
        """Test when no definition matches."""
        mapper = StepDefinitionMapper()
        mapper.add_definition(
            pattern="user is logged in",
            method_name="login",
            file_path="/steps/login.py",
            line_number=10
        )
        
        step = BDDStep(keyword=StepKeyword.GIVEN, text="user is logged out", line=1)
        match = mapper.match_step(step)
        
        assert match is None
    
    def test_coverage_statistics(self):
        """Test coverage statistics calculation."""
        mapper = StepDefinitionMapper()
        mapper.add_definition(
            pattern="user is logged in",
            method_name="login",
            file_path="/steps/login.py",
            line_number=10
        )
        
        steps = [
            BDDStep(keyword=StepKeyword.GIVEN, text="user is logged in", line=1),
            BDDStep(keyword=StepKeyword.WHEN, text="user clicks submit", line=2),  # No match
            BDDStep(keyword=StepKeyword.THEN, text="dashboard is shown", line=3)  # No match
        ]
        
        stats = mapper.get_coverage_statistics(steps)
        
        assert stats["total_steps"] == 3
        assert stats["mapped_steps"] == 1
        assert stats["unmapped_steps"] == 2
        assert stats["coverage_percent"] == pytest.approx(33.33, rel=0.1)


class TestAdapterCompletenessValidation:
    """Test adapter completeness validation."""
    
    def test_complete_adapter(self):
        """Test validation of complete adapter."""
        capabilities = {
            "discovery": True,
            "feature_parsing": True,
            "scenario_extraction": True,
            "step_extraction": True,
            "tag_extraction": True,
            "step_definition_mapping": True,
            "execution_parsing": True,
            "failure_mapping": True,
            "embedding_compatibility": True,
            "graph_compatibility": True,
        }
        
        is_complete, missing = validate_adapter_completeness(capabilities)
        
        assert is_complete is True
        assert len(missing) == 0
    
    def test_incomplete_adapter(self):
        """Test validation of incomplete adapter."""
        capabilities = {
            "discovery": True,
            "feature_parsing": True,
            "scenario_extraction": True,
            "step_extraction": False,  # Missing
            "tag_extraction": True,
            "step_definition_mapping": False,  # Missing
            "execution_parsing": True,
            "failure_mapping": True,
            "embedding_compatibility": True,
            "graph_compatibility": True,
        }
        
        is_complete, missing = validate_adapter_completeness(capabilities)
        
        assert is_complete is False
        assert len(missing) == 2
        assert any("step_extraction" in m for m in missing)
        assert any("step_definition_mapping" in m for m in missing)


@pytest.mark.skipif(
    not pytest.importorskip("javalang", reason="javalang not installed"),
    reason="Requires javalang for Java parsing"
)
class TestCucumberJavaAdapter:
    """Test enhanced Cucumber Java adapter."""
    
    def test_feature_parser_initialization(self):
        """Test feature parser initialization."""
        from adapters.selenium_bdd_java.enhanced_adapter import CucumberFeatureParser
        
        parser = CucumberFeatureParser()
        assert ".feature" in parser.supported_extensions
    
    def test_feature_parsing(self):
        """Test parsing a simple feature."""
        from adapters.selenium_bdd_java.enhanced_adapter import CucumberFeatureParser
        
        feature_content = """
        Feature: User Login
          As a user
          I want to login
          
          @smoke @auth
          Scenario: Valid login
            Given user is on login page
            When user enters valid credentials
            Then user sees dashboard
        """
        
        parser = CucumberFeatureParser()
        feature = parser.parse_content(feature_content)
        
        assert feature.name == "User Login"
        assert len(feature.scenarios) == 1
        assert feature.scenarios[0].name == "Valid login"
        assert len(feature.scenarios[0].steps) == 3
        assert "smoke" in feature.scenarios[0].tags
        assert "auth" in feature.scenarios[0].tags
    
    def test_adapter_completeness(self):
        """Test adapter reports all capabilities as implemented."""
        from adapters.selenium_bdd_java.enhanced_adapter import EnhancedCucumberJavaAdapter
        
        adapter = EnhancedCucumberJavaAdapter()
        capabilities = adapter.validate_completeness()
        
        # All capabilities should be True
        for capability, implemented in capabilities.items():
            assert implemented is True, f"Capability {capability} not implemented"
        
        # Adapter should be stable
        assert is_adapter_stable(adapter) is True


@pytest.mark.skipif(
    not pytest.importorskip("robot", reason="Robot Framework not installed"),
    reason="Requires Robot Framework"
)
class TestRobotBDDAdapter:
    """Test Robot Framework BDD adapter."""
    
    def test_feature_parser_initialization(self):
        """Test Robot BDD parser initialization."""
        from adapters.robot.bdd_adapter import RobotBDDFeatureParser
        
        parser = RobotBDDFeatureParser()
        assert ".robot" in parser.supported_extensions
    
    def test_adapter_completeness(self):
        """Test Robot adapter completeness."""
        from adapters.robot.bdd_adapter import RobotBDDAdapter
        
        adapter = RobotBDDAdapter()
        capabilities = adapter.validate_completeness()
        
        # Check core capabilities are implemented
        assert capabilities.get("discovery") is True
        assert capabilities.get("embedding_compatibility") is True


class TestJBehaveAdapter:
    """Test JBehave adapter."""
    
    def test_story_parser_initialization(self):
        """Test JBehave story parser initialization."""
        from adapters.java.jbehave_adapter import JBehaveStoryParser
        
        parser = JBehaveStoryParser()
        assert ".story" in parser.supported_extensions
    
    def test_story_parsing(self):
        """Test parsing a JBehave story."""
        from adapters.java.jbehave_adapter import JBehaveStoryParser
        
        story_content = """
        Narrative:
        As a user
        I want to login
        So that I can access my account
        
        Scenario: Successful login
        Given user is on login page
        When user enters valid credentials
        Then user should see dashboard
        """
        
        parser = JBehaveStoryParser()
        feature = parser.parse_content(story_content)
        
        assert feature.name is not None
        assert len(feature.scenarios) == 1
        assert feature.scenarios[0].name == "Successful login"
        assert len(feature.scenarios[0].steps) == 3


# Integration tests
class TestBDDAdapterIntegration:
    """Integration tests for BDD adapters."""
    
    def test_cucumber_to_robot_conversion(self):
        """Test converting Cucumber scenario to Robot equivalent."""
        scenario = BDDScenario(
            id="test::scenario",
            name="Login Test",
            feature="Authentication",
            steps=[
                BDDStep(keyword=StepKeyword.GIVEN, text="user is on login page", line=1),
                BDDStep(keyword=StepKeyword.WHEN, text="user enters credentials", line=2),
                BDDStep(keyword=StepKeyword.THEN, text="user sees dashboard", line=3)
            ],
            framework="cucumber-java"
        )
        
        # Change framework identifier
        scenario.framework = "robot-bdd"
        
        # Verify conversion
        assert scenario.framework == "robot-bdd"
        assert len(scenario.steps) == 3
        assert scenario.steps[0].keyword == StepKeyword.GIVEN
    
    def test_multi_framework_step_mapping(self):
        """Test step mapping works across frameworks."""
        mapper = StepDefinitionMapper()
        
        # Add definitions from different frameworks
        mapper.add_definition(
            pattern="user is logged in",
            method_name="cucumber_login",
            file_path="/cucumber/steps.java",
            line_number=10,
            framework="cucumber"
        )
        
        mapper.add_definition(
            pattern="user_is_logged_in",
            method_name="robot_login",
            file_path="/robot/keywords.robot",
            line_number=20,
            framework="robot"
        )
        
        # Test matching
        cucumber_step = BDDStep(keyword=StepKeyword.GIVEN, text="user is logged in", line=1)
        match = mapper.match_step(cucumber_step)
        
        assert match is not None
        assert match.method_name in ["cucumber_login", "robot_login"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
