"""
Unit tests for Cucumber coverage aggregation.
"""

import pytest
from pathlib import Path
from datetime import datetime

from core.coverage.cucumber_coverage import (
    CucumberCoverageAggregator,
    StepDefinitionMapper,
    CucumberCoverageCollector
)
from core.coverage.models import (
    TestCoverageMapping,
    CoveredCodeUnit,
    CoverageType,
    CoverageSource,
    ExecutionMode
)
from adapters.selenium_bdd_java import ScenarioResult, StepResult


@pytest.fixture
def sample_scenario():
    """Create a sample Cucumber scenario."""
    scenario = ScenarioResult(
        id="login-scenario-1",
        name="User logs in successfully",
        status="passed",
        duration=1500,
        steps=[
            StepResult(
                keyword="Given",
                name="user is on login page",
                status="passed",
                duration=300
            ),
            StepResult(
                keyword="When",
                name="user enters valid credentials",
                status="passed",
                duration=500
            ),
            StepResult(
                keyword="Then",
                name="user should see dashboard",
                status="passed",
                duration=700
            )
        ]
    )
    return scenario


@pytest.fixture
def sample_coverage_mapping():
    """Create a sample coverage mapping."""
    units = [
        CoveredCodeUnit(
            class_name="com.example.LoginPage",
            method_name="open",
            line_coverage=0.9
        ),
        CoveredCodeUnit(
            class_name="com.example.LoginService",
            method_name="authenticate",
            line_coverage=0.95
        )
    ]
    
    mapping = TestCoverageMapping(
        test_id="test1",
        test_name="test1",
        test_framework="cucumber",
        covered_classes={"com.example.LoginPage", "com.example.LoginService"},
        covered_methods={"com.example.LoginPage.open", "com.example.LoginService.authenticate"},
        covered_code_units=units,
        coverage_source=CoverageSource.JACOCO,
        execution_mode=ExecutionMode.ISOLATED,
        confidence=0.92
    )
    return mapping


class TestCucumberCoverageAggregator:
    """Tests for CucumberCoverageAggregator."""
    
    def test_create_aggregator(self):
        """Test creating a coverage aggregator."""
        aggregator = CucumberCoverageAggregator()
        assert aggregator is not None
        assert aggregator.jacoco_parser is not None
    
    def test_aggregate_scenario_without_step_map(self, sample_scenario, sample_coverage_mapping, tmp_path):
        """Test aggregating scenario coverage without step-to-method mapping."""
        # Create a fake JaCoCo XML
        jacoco_xml = tmp_path / "jacoco.xml"
        jacoco_content = """<?xml version="1.0" encoding="UTF-8"?>
<report name="Test Coverage">
    <package name="com/example">
        <class name="com/example/LoginPage">
            <method name="open" desc="()V">
                <counter type="LINE" missed="0" covered="10"/>
            </method>
            <counter type="LINE" missed="0" covered="10"/>
        </class>
        <class name="com/example/LoginService">
            <method name="authenticate" desc="(Ljava/lang/String;)Z">
                <counter type="LINE" missed="5" covered="25"/>
            </method>
            <counter type="LINE" missed="5" covered="25"/>
        </class>
    </package>
</report>
"""
        jacoco_xml.write_text(jacoco_content)
        
        aggregator = CucumberCoverageAggregator()
        
        scenario_mapping = aggregator.aggregate_scenario_coverage(
            scenario=sample_scenario,
            jacoco_xml_path=jacoco_xml,
            step_to_method_map=None,
            execution_mode=ExecutionMode.ISOLATED
        )
        
        assert scenario_mapping.scenario_id == "login-scenario-1"
        assert scenario_mapping.scenario_name == "User logs in successfully"
        assert len(scenario_mapping.aggregated_classes) > 0
        assert scenario_mapping.confidence > 0.0
    
    def test_aggregate_with_step_mapping(self, sample_scenario, tmp_path):
        """Test aggregating with step-to-method mapping."""
        jacoco_xml = tmp_path / "jacoco.xml"
        jacoco_content = """<?xml version="1.0" encoding="UTF-8"?>
<report name="Test Coverage">
    <package name="com/example">
        <class name="com/example/LoginPage">
            <method name="open" desc="()V">
                <counter type="LINE" missed="0" covered="10"/>
            </method>
            <counter type="LINE" missed="0" covered="10"/>
        </class>
    </package>
</report>
"""
        jacoco_xml.write_text(jacoco_content)
        
        # Create step-to-method map
        step_map = {
            "given user is on login page": {"com.example.LoginPage.open"}
        }
        
        aggregator = CucumberCoverageAggregator()
        
        scenario_mapping = aggregator.aggregate_scenario_coverage(
            scenario=sample_scenario,
            jacoco_xml_path=jacoco_xml,
            step_to_method_map=step_map,
            execution_mode=ExecutionMode.ISOLATED
        )
        
        assert scenario_mapping is not None
        assert len(scenario_mapping.step_coverage_mappings) <= len(sample_scenario.steps)
    
    def test_normalize_step_text(self):
        """Test step text normalization."""
        aggregator = CucumberCoverageAggregator()
        
        normalized = aggregator._normalize_step_text("Given user is on login page")
        assert normalized == "given user is on login page"
        
        normalized = aggregator._normalize_step_text("  When  user enters credentials  ")
        assert normalized == "when  user enters credentials"


class TestStepDefinitionMapper:
    """Tests for StepDefinitionMapper."""
    
    def test_create_mapper(self):
        """Test creating a step definition mapper."""
        mapper = StepDefinitionMapper()
        assert mapper is not None
        assert len(mapper.step_map) == 0
    
    def test_add_mapping(self):
        """Test adding a step mapping."""
        mapper = StepDefinitionMapper()
        
        mapper.add_mapping(
            step_pattern="Given user is on login page",
            java_method="com.example.steps.LoginSteps.userIsOnLoginPage"
        )
        
        assert "Given user is on login page" in mapper.step_map
        assert "com.example.steps.LoginSteps.userIsOnLoginPage" in mapper.step_map["Given user is on login page"]
    
    def test_add_multiple_methods_to_step(self):
        """Test adding multiple methods to same step."""
        mapper = StepDefinitionMapper()
        
        mapper.add_mapping("Given user is logged in", "LoginSteps.method1")
        mapper.add_mapping("Given user is logged in", "LoginSteps.method2")
        
        assert len(mapper.step_map["Given user is logged in"]) == 2
    
    def test_get_mapping(self):
        """Test getting the complete mapping."""
        mapper = StepDefinitionMapper()
        
        mapper.add_mapping("step1", "method1")
        mapper.add_mapping("step2", "method2")
        
        mapping = mapper.get_mapping()
        assert len(mapping) == 2
        assert "step1" in mapping
        assert "step2" in mapping
    
    def test_build_from_source_not_implemented(self, tmp_path):
        """Test that build_from_source returns empty map (not implemented)."""
        mapper = StepDefinitionMapper()
        
        result = mapper.build_from_source(tmp_path)
        
        # Should return empty map for now
        assert result == {}
    
    def test_build_from_execution_log_not_implemented(self, tmp_path):
        """Test that build_from_execution_log returns empty map."""
        mapper = StepDefinitionMapper()
        
        log_file = tmp_path / "execution.log"
        log_file.write_text("some log content")
        
        result = mapper.build_from_execution_log(log_file)
        
        # Should return empty map for now
        assert result == {}


class TestCucumberCoverageCollector:
    """Tests for CucumberCoverageCollector."""
    
    def test_create_collector(self):
        """Test creating a coverage collector."""
        collector = CucumberCoverageCollector()
        assert collector is not None
        assert collector.aggregator is not None
        assert collector.step_mapper is not None
    
    def test_collector_has_step_mapper(self):
        """Test that collector has a step mapper."""
        collector = CucumberCoverageCollector()
        
        # Should be able to add mappings
        collector.step_mapper.add_mapping("step1", "method1")
        
        mapping = collector.step_mapper.get_mapping()
        assert "step1" in mapping


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
