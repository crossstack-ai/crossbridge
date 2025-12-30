"""
Unit tests for coverage mapping models.
"""

import pytest
from datetime import datetime
from pathlib import Path

from core.coverage.models import (
    CoveredCodeUnit,
    TestCoverageMapping,
    ScenarioCoverageMapping,
    CoverageConfidenceCalculator,
    CoverageImpactQuery,
    CoverageType,
    CoverageSource,
    ExecutionMode
)


class TestCoveredCodeUnit:
    """Tests for CoveredCodeUnit model."""
    
    def test_create_basic_unit(self):
        """Test creating a basic code unit."""
        unit = CoveredCodeUnit(
            class_name="com.example.LoginService",
            method_name="authenticate"
        )
        
        assert unit.class_name == "com.example.LoginService"
        assert unit.method_name == "authenticate"
        assert unit.file_path is None
        assert unit.covered_branches == 0
        assert unit.total_branches == 0
    
    def test_create_unit_with_coverage(self):
        """Test creating a unit with coverage metrics."""
        unit = CoveredCodeUnit(
            class_name="com.example.LoginService",
            method_name="authenticate",
            instruction_coverage=0.9,
            line_coverage=0.85,
            line_numbers=[10, 11, 12, 15, 16]
        )
        
        assert unit.instruction_coverage == 0.9
        assert unit.line_coverage == 0.85
        assert len(unit.line_numbers) == 5
        assert 10 in unit.line_numbers
    
    def test_unit_with_file_path(self):
        """Test unit with file path."""
        unit = CoveredCodeUnit(
            class_name="com.example.service.LoginService",
            file_path="src/main/java/com/example/service/LoginService.java",
            branch_coverage=0.75
        )
        
        assert unit.file_path == "src/main/java/com/example/service/LoginService.java"
        assert unit.class_name == "com.example.service.LoginService"
        assert unit.branch_coverage == 0.75
    
    def test_unit_equality(self):
        """Test unit equality comparison."""
        unit1 = CoveredCodeUnit(
            class_name="com.example.Service",
            method_name="method1"
        )
        
        unit2 = CoveredCodeUnit(
            class_name="com.example.Service",
            method_name="method1"
        )
        
        # Same class and method should be equal
        assert unit1 == unit2
        assert unit1.class_name == unit2.class_name
        assert unit1.method_name == unit2.method_name


class TestTestCoverageMapping:
    """Tests for TestCoverageMapping model."""
    
    def test_create_basic_mapping(self):
        """Test creating a basic test coverage mapping."""
        mapping = TestCoverageMapping(
            test_id="LoginTest.testSuccess",
            test_name="testSuccess",
            test_framework="junit",
            covered_classes={"com.example.LoginService"},
            covered_methods={"com.example.LoginService.authenticate"},
            covered_code_units=[],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED
        )
        
        assert mapping.test_id == "LoginTest.testSuccess"
        assert mapping.test_framework == "junit"
        assert len(mapping.covered_classes) == 1
        assert len(mapping.covered_methods) == 1
        assert mapping.coverage_source == CoverageSource.JACOCO
        assert mapping.execution_mode == ExecutionMode.ISOLATED
    
    def test_mapping_with_code_units(self):
        """Test mapping with code units."""
        units = [
            CoveredCodeUnit(
                class_name="com.example.LoginService",
                method_name="authenticate",
                line_coverage=0.8,
                line_numbers=[1, 2, 3, 4, 5]
            ),
            CoveredCodeUnit(
                class_name="com.example.UserService",
                method_name="getUser",
                line_coverage=0.75,
                line_numbers=[10, 11, 12]
            )
        ]
        
        mapping = TestCoverageMapping(
            test_id="LoginTest.testSuccess",
            test_name="testSuccess",
            test_framework="junit",
            covered_classes={"com.example.LoginService", "com.example.UserService"},
            covered_methods={"com.example.LoginService.authenticate", "com.example.UserService.getUser"},
            covered_code_units=units,
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED
        )
        
        assert len(mapping.covered_code_units) == 2
        assert mapping.covered_code_units[0].line_coverage == 0.8
        assert mapping.covered_code_units[1].line_coverage == 0.75
    
    def test_mapping_confidence_default(self):
        """Test default confidence is calculated."""
        mapping = TestCoverageMapping(
            test_id="test1",
            test_name="test1",
            test_framework="junit",
            covered_classes=set(),
            covered_methods=set(),
            covered_code_units=[],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED
        )
        
        # Should have default confidence
        assert mapping.confidence >= 0.0
        assert mapping.confidence <= 1.0


class TestScenarioCoverageMapping:
    """Tests for ScenarioCoverageMapping model."""
    
    def test_create_scenario_mapping(self):
        """Test creating a scenario coverage mapping."""
        mapping = ScenarioCoverageMapping(
            scenario_id="login-scenario-001",
            scenario_name="User logs in successfully",
            feature_name="Login",
            feature_file="features/login.feature",
            step_coverage_mappings=[],
            coverage_source=CoverageSource.JACOCO,
            confidence=0.85,
            execution_time=datetime.now()
        )
        
        assert mapping.scenario_id == "login-scenario-001"
        assert mapping.scenario_name == "User logs in successfully"
        assert mapping.feature_name == "Login"
        assert mapping.confidence == 0.85
    
    def test_aggregate_coverage_from_steps(self):
        """Test aggregating coverage from step mappings."""
        # Create step mappings
        step1 = TestCoverageMapping(
            test_id="step1",
            test_name="Given user on login page",
            test_framework="cucumber",
            covered_classes={"com.example.LoginPage"},
            covered_methods={"com.example.LoginPage.open"},
            covered_code_units=[
                CoveredCodeUnit(
                    class_name="com.example.LoginPage",
                    method_name="open",
                    line_coverage=0.9
                )
            ],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED
        )
        
        step2 = TestCoverageMapping(
            test_id="step2",
            test_name="When user enters credentials",
            test_framework="cucumber",
            covered_classes={"com.example.LoginPage", "com.example.LoginService"},
            covered_methods={"com.example.LoginPage.enterCredentials", "com.example.LoginService.authenticate"},
            covered_code_units=[
                CoveredCodeUnit(
                    class_name="com.example.LoginPage",
                    method_name="enterCredentials",
                    line_coverage=0.5
                ),
                CoveredCodeUnit(
                    class_name="com.example.LoginService",
                    method_name="authenticate",
                    line_coverage=0.95
                )
            ],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED
        )
        
        scenario = ScenarioCoverageMapping(
            scenario_id="scenario1",
            scenario_name="Login scenario",
            step_coverage_mappings=[step1, step2],
            coverage_source=CoverageSource.JACOCO,
            confidence=0.9
        )
        
        # Aggregate coverage
        scenario.aggregate_coverage()
        
        # Should have union of classes
        assert len(scenario.aggregated_classes) == 2
        assert "com.example.LoginPage" in scenario.aggregated_classes
        assert "com.example.LoginService" in scenario.aggregated_classes
        
        # Should have union of methods
        assert len(scenario.aggregated_methods) == 3
        
        # Should have all code units
        assert len(scenario.aggregated_code_units) == 3
    
    def test_aggregate_empty_steps(self):
        """Test aggregating with no step mappings."""
        scenario = ScenarioCoverageMapping(
            scenario_id="scenario1",
            scenario_name="Empty scenario",
            step_coverage_mappings=[],
            coverage_source=CoverageSource.JACOCO,
            confidence=0.5
        )
        
        scenario.aggregate_coverage()
        
        assert len(scenario.aggregated_classes) == 0
        assert len(scenario.aggregated_methods) == 0
        assert len(scenario.aggregated_code_units) == 0


class TestCoverageConfidenceCalculator:
    """Tests for CoverageConfidenceCalculator."""
    
    def test_isolated_execution_high_confidence(self):
        """Test isolated execution gives high confidence."""
        calculator = CoverageConfidenceCalculator()
        
        confidence = calculator.calculate(
            execution_mode=ExecutionMode.ISOLATED,
            has_source_paths=True
        )
        
        assert confidence >= 0.90
        assert confidence <= 0.95
    
    def test_small_batch_medium_confidence(self):
        """Test small batch execution gives medium confidence."""
        calculator = CoverageConfidenceCalculator()
        
        confidence = calculator.calculate(
            execution_mode=ExecutionMode.SMALL_BATCH,
            has_source_paths=True
        )
        
        assert confidence >= 0.60
        assert confidence <= 0.75
    
    def test_full_suite_low_confidence(self):
        """Test full suite execution gives lower confidence."""
        calculator = CoverageConfidenceCalculator()
        
        confidence = calculator.calculate(
            execution_mode=ExecutionMode.FULL_SUITE,
            has_source_paths=True
        )
        
        assert confidence >= 0.40
        assert confidence <= 0.50
    
    def test_no_source_paths_penalty(self):
        """Test that missing source paths reduces confidence."""
        calculator = CoverageConfidenceCalculator()
        
        with_source = calculator.calculate(
            execution_mode=ExecutionMode.ISOLATED,
            has_source_paths=True
        )
        
        without_source = calculator.calculate(
            execution_mode=ExecutionMode.ISOLATED,
            has_source_paths=False
        )
        
        assert without_source < with_source
    
    def test_batch_size_penalty(self):
        """Test that larger batch size reduces confidence."""
        calculator = CoverageConfidenceCalculator()
        
        small_batch = calculator.calculate(
            execution_mode=ExecutionMode.SMALL_BATCH,
            batch_size=5
        )
        
        large_batch = calculator.calculate(
            execution_mode=ExecutionMode.SMALL_BATCH,
            batch_size=50
        )
        
        assert large_batch < small_batch


class TestCoverageImpactQuery:
    """Tests for CoverageImpactQuery model."""
    
    def test_create_impact_query(self):
        """Test creating an impact query."""
        query = CoverageImpactQuery(
            changed_classes={"com.example.LoginService", "com.example.UserService"},
            changed_methods={"com.example.LoginService.authenticate"},
            min_confidence=0.7
        )
        
        assert len(query.changed_classes) == 2
        assert len(query.changed_methods) == 1
        assert query.min_confidence == 0.7
        assert query.affected_tests == []
    
    def test_query_with_results(self):
        """Test query with results populated."""
        query = CoverageImpactQuery(
            changed_classes={"com.example.LoginService"},
            changed_methods=set(),
            min_confidence=0.5
        )
        
        query.affected_tests = ["LoginTest.test1", "LoginTest.test2", "UserTest.test1"]
        
        assert len(query.affected_tests) == 3


class TestEnums:
    """Tests for coverage enums."""
    
    def test_coverage_type_enum(self):
        """Test CoverageType enum values."""
        assert CoverageType.INSTRUCTION.value == "instruction"
        assert CoverageType.LINE.value == "line"
        assert CoverageType.BRANCH.value == "branch"
        assert CoverageType.METHOD.value == "method"
    
    def test_coverage_source_enum(self):
        """Test CoverageSource enum values."""
        assert CoverageSource.JACOCO.value == "jacoco"
        assert CoverageSource.COVERAGE_PY.value == "coverage.py"
        assert CoverageSource.ISTANBUL.value == "istanbul"
    
    def test_execution_mode_enum(self):
        """Test ExecutionMode enum values."""
        assert ExecutionMode.ISOLATED.value == "isolated"
        assert ExecutionMode.SMALL_BATCH.value == "small_batch"
        assert ExecutionMode.FULL_SUITE.value == "full_suite"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
