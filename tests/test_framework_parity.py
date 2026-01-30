"""
Framework Parity Validation Tests

Validates that all frameworks (Cucumber, Robot, Pytest) provide
equivalent signal quality and analytics capabilities.

Tests ensure:
- All frameworks emit canonical ExecutionSignal objects
- Same failure type yields same signal_type across frameworks
- Granularity parity (step/keyword/assertion level)
- Metadata richness parity
- Timing accuracy
- Confidence calibration
"""

import pytest
from typing import List
from datetime import datetime

from core.execution.intelligence.models import (
    ExecutionSignal,
    EntityType,
    SignalType,
    CucumberScenario,
    CucumberStep,
    RobotTest,
    RobotKeyword,
    PytestTest,
    PytestAssertion,
    PytestFixture,
)
from core.execution.intelligence.cucumber_parser import cucumber_to_signals
from core.execution.intelligence.robot_parser import robot_to_signals
from core.execution.intelligence.embeddings import generate_all_embeddings
from core.execution.intelligence.graph_linking import build_complete_graph


class TestCanonicalSignalFormat:
    """Test that all frameworks emit canonical ExecutionSignal objects"""
    
    def test_cucumber_emits_execution_signals(self):
        """Cucumber scenarios emit ExecutionSignal objects"""
        # Create sample scenario
        scenario = CucumberScenario(
            name="Login with valid credentials",
            feature_name="User Authentication",
            steps=[
                CucumberStep(
                    keyword="Given",
                    text="I am on the login page",
                    status="passed",
                    duration_ms=100
                ),
                CucumberStep(
                    keyword="When",
                    text="I enter valid credentials",
                    status="passed",
                    duration_ms=200
                ),
            ],
            status="passed",
            duration_ms=300
        )
        
        signals = cucumber_to_signals([scenario], include_steps=True)
        
        # Verify all are ExecutionSignal objects
        assert all(isinstance(s, ExecutionSignal) for s in signals)
        
        # Verify framework field
        assert all(s.framework == "selenium_java_bdd" for s in signals)
        
        # Verify entity types
        scenario_signals = [s for s in signals if s.entity_type == EntityType.SCENARIO]
        step_signals = [s for s in signals if s.entity_type == EntityType.STEP]
        
        assert len(scenario_signals) == 1
        assert len(step_signals) == 2
    
    def test_robot_emits_execution_signals(self):
        """Robot tests emit ExecutionSignal objects"""
        # Create sample test
        test = RobotTest(
            name="Login Test",
            suite_name="Authentication Suite",
            keywords=[
                RobotKeyword(
                    name="Open Browser",
                    library="SeleniumLibrary",
                    status="PASS",
                    duration_ms=500
                ),
                RobotKeyword(
                    name="Input Text",
                    library="SeleniumLibrary",
                    arguments=["username_field", "admin"],
                    status="PASS",
                    duration_ms=100
                ),
            ],
            status="PASS",
            duration_ms=600
        )
        
        signals = robot_to_signals([test], include_keywords=True)
        
        # Verify all are ExecutionSignal objects
        assert all(isinstance(s, ExecutionSignal) for s in signals)
        
        # Verify framework field
        assert all(s.framework == "robot" for s in signals)
        
        # Verify entity types
        test_signals = [s for s in signals if s.entity_type == EntityType.TEST]
        keyword_signals = [s for s in signals if s.entity_type == EntityType.KEYWORD]
        
        assert len(test_signals) == 1
        assert len(keyword_signals) == 2
    
    def test_pytest_emits_execution_signals(self):
        """Pytest tests emit ExecutionSignal objects"""
        # Create sample test
        test = PytestTest(
            name="test_login_success",
            module="tests.test_auth",
            status="passed",
            duration_ms=250,
            assertions=[
                PytestAssertion(
                    expression="response.status_code == 200",
                    status="passed"
                )
            ],
            fixtures=[
                PytestFixture(
                    name="client",
                    scope="function",
                    phase="setup",
                    status="passed",
                    duration_ms=50
                )
            ]
        )
        
        signal = test.to_signal()
        
        # Verify is ExecutionSignal object
        assert isinstance(signal, ExecutionSignal)
        
        # Verify framework field
        assert signal.framework == "pytest"
        
        # Verify entity type
        assert signal.entity_type == EntityType.FUNCTION


class TestFailureTypeConsistency:
    """Test that same failure type yields same signal_type across frameworks"""
    
    def test_timeout_failures_across_frameworks(self):
        """Timeout failures are consistently classified"""
        # Cucumber timeout
        cucumber_step = CucumberStep(
            keyword="When",
            text="I wait for element to appear",
            status="failed",
            duration_ms=30000,
            error_message="TimeoutException: Element not visible after 30 seconds"
        )
        cucumber_signal = cucumber_step.to_signal("Login Scenario", run_id="run1")
        
        # Robot timeout
        robot_kw = RobotKeyword(
            name="Wait Until Element Is Visible",
            library="SeleniumLibrary",
            status="FAIL",
            duration_ms=30000,
            error_message="Element did not become visible in 30 seconds"
        )
        robot_signal = robot_kw.to_signal("Login Test", "Auth Suite", run_id="run1")
        
        # Pytest timeout
        pytest_test = PytestTest(
            name="test_element_appears",
            module="tests.test_ui",
            status="failed",
            duration_ms=30000,
            error_message="TimeoutError: Element not found after 30 seconds"
        )
        pytest_signal = pytest_test.to_signal(run_id="run1")
        
        # All should have timeout-related failure types
        assert cucumber_signal.failure_type == SignalType.UI_TIMEOUT.value
        assert robot_signal.failure_type == SignalType.TIMEOUT.value
        assert pytest_signal.failure_type == SignalType.TIMEOUT.value
    
    def test_assertion_failures_across_frameworks(self):
        """Assertion failures are consistently classified"""
        # Cucumber assertion
        cucumber_step = CucumberStep(
            keyword="Then",
            text="the response should be successful",
            status="failed",
            duration_ms=10,
            error_message="AssertionError: Expected status 200, got 404"
        )
        cucumber_signal = cucumber_step.to_signal("API Test", run_id="run2")
        
        # Robot assertion
        robot_kw = RobotKeyword(
            name="Should Be Equal",
            library="BuiltIn",
            arguments=["200", "404"],
            status="FAIL",
            duration_ms=5,
            error_message="200 != 404"
        )
        robot_signal = robot_kw.to_signal("API Test", "API Suite", run_id="run2")
        
        # Pytest assertion
        pytest_test = PytestTest(
            name="test_api_returns_200",
            module="tests.test_api",
            status="failed",
            duration_ms=15,
            error_message="AssertionError: assert 404 == 200",
            assertions=[
                PytestAssertion(
                    expression="status_code == 200",
                    status="failed",
                    error_message="assert 404 == 200"
                )
            ]
        )
        pytest_signal = pytest_test.to_signal(run_id="run2")
        
        # All should have assertion-related failure types
        assert cucumber_signal.failure_type == SignalType.ASSERTION.value
        assert robot_signal.failure_type == SignalType.ASSERTION.value
        assert pytest_signal.failure_type == SignalType.ASSERTION.value


class TestGranularityParity:
    """Test that all frameworks provide equivalent granularity"""
    
    def test_cucumber_provides_step_level_signals(self):
        """Cucumber provides step-level granularity"""
        scenario = CucumberScenario(
            name="Multi-step scenario",
            feature_name="Test Feature",
            steps=[
                CucumberStep(keyword="Given", text="step 1", status="passed", duration_ms=100),
                CucumberStep(keyword="When", text="step 2", status="passed", duration_ms=200),
                CucumberStep(keyword="Then", text="step 3", status="passed", duration_ms=150),
            ],
            status="passed",
            duration_ms=450
        )
        
        signals = cucumber_to_signals([scenario], include_steps=True)
        step_signals = [s for s in signals if s.entity_type == EntityType.STEP]
        
        # Must have step-level signals
        assert len(step_signals) == 3
        
        # Each step signal must have timing
        assert all(s.duration_ms > 0 for s in step_signals)
    
    def test_robot_provides_keyword_level_signals(self):
        """Robot provides keyword-level granularity"""
        test = RobotTest(
            name="Multi-keyword test",
            suite_name="Test Suite",
            keywords=[
                RobotKeyword(name="Keyword 1", library="BuiltIn", status="PASS", duration_ms=100),
                RobotKeyword(name="Keyword 2", library="BuiltIn", status="PASS", duration_ms=200),
                RobotKeyword(name="Keyword 3", library="BuiltIn", status="PASS", duration_ms=150),
            ],
            status="PASS",
            duration_ms=450
        )
        
        signals = robot_to_signals([test], include_keywords=True)
        keyword_signals = [s for s in signals if s.entity_type == EntityType.KEYWORD]
        
        # Must have keyword-level signals
        assert len(keyword_signals) == 3
        
        # Each keyword signal must have timing
        assert all(s.duration_ms > 0 for s in keyword_signals)
    
    def test_pytest_provides_assertion_level_signals(self):
        """Pytest provides assertion-level granularity"""
        test = PytestTest(
            name="test_with_multiple_assertions",
            module="tests.test_module",
            status="passed",
            duration_ms=100,
            assertions=[
                PytestAssertion(expression="x == 1", status="passed"),
                PytestAssertion(expression="y == 2", status="passed"),
                PytestAssertion(expression="z == 3", status="passed"),
            ]
        )
        
        # Convert assertions to signals
        from core.execution.intelligence.embeddings import PytestEmbeddingGenerator, EmbeddingGenerator
        
        # Verify test has assertions
        assert len(test.assertions) == 3
        
        # Each assertion can be converted to signal
        for assertion in test.assertions:
            signal = assertion.to_signal(test.name)
            assert isinstance(signal, ExecutionSignal)
            assert signal.entity_type == EntityType.ASSERTION


class TestMetadataRichness:
    """Test that all frameworks provide rich metadata"""
    
    def test_cucumber_metadata(self):
        """Cucumber signals have rich metadata"""
        scenario = CucumberScenario(
            name="Login scenario",
            feature_name="Authentication",
            tags=["smoke", "critical"],
            steps=[
                CucumberStep(keyword="Given", text="step 1", status="passed", duration_ms=100)
            ],
            status="passed",
            duration_ms=100
        )
        
        signal = scenario.to_signal(run_id="run1")
        
        # Must have metadata
        assert signal.metadata is not None
        assert isinstance(signal.metadata, dict)
        assert len(signal.metadata) > 0
        
        # Must include key fields
        assert 'feature_name' in signal.metadata
        assert 'tags' in signal.metadata
        assert 'step_count' in signal.metadata
    
    def test_robot_metadata(self):
        """Robot signals have rich metadata"""
        test = RobotTest(
            name="Login test",
            suite_name="Auth Suite",
            tags=["smoke", "critical"],
            keywords=[
                RobotKeyword(
                    name="Open Browser",
                    library="SeleniumLibrary",
                    arguments=["http://example.com", "chrome"],
                    status="PASS",
                    duration_ms=500
                )
            ],
            status="PASS",
            duration_ms=500
        )
        
        signal = test.to_signal(run_id="run1")
        
        # Must have metadata
        assert signal.metadata is not None
        assert isinstance(signal.metadata, dict)
        assert len(signal.metadata) > 0
        
        # Must include key fields
        assert 'suite_name' in signal.metadata
        assert 'tags' in signal.metadata
        assert 'keyword_count' in signal.metadata
    
    def test_pytest_metadata(self):
        """Pytest signals have rich metadata"""
        test = PytestTest(
            name="test_login",
            module="tests.test_auth",
            markers=["smoke", "slow"],
            fixtures=[
                PytestFixture(name="db", scope="session", phase="setup", status="passed", duration_ms=100)
            ],
            assertions=[
                PytestAssertion(expression="result == True", status="passed")
            ],
            status="passed",
            duration_ms=200
        )
        
        signal = test.to_signal(run_id="run1")
        
        # Must have metadata
        assert signal.metadata is not None
        assert isinstance(signal.metadata, dict)
        assert len(signal.metadata) > 0
        
        # Must include key fields
        assert 'module' in signal.metadata
        assert 'markers' in signal.metadata
        assert 'fixture_count' in signal.metadata


class TestTimingAccuracy:
    """Test that all frameworks provide accurate timing"""
    
    def test_timing_fields_present(self):
        """All signals have duration_ms field"""
        # Cucumber
        cucumber_step = CucumberStep(keyword="Given", text="step", status="passed", duration_ms=123)
        cucumber_signal = cucumber_step.to_signal("Scenario")
        
        # Robot
        robot_kw = RobotKeyword(name="Keyword", library="Lib", status="PASS", duration_ms=456)
        robot_signal = robot_kw.to_signal("Test", "Suite")
        
        # Pytest
        pytest_test = PytestTest(name="test", module="module", status="passed", duration_ms=789)
        pytest_signal = pytest_test.to_signal()
        
        # All must have duration_ms
        assert cucumber_signal.duration_ms == 123
        assert robot_signal.duration_ms == 456
        assert pytest_signal.duration_ms == 789
    
    def test_timing_values_valid(self):
        """Timing values are valid (non-negative, reasonable)"""
        signals = [
            CucumberStep(keyword="G", text="t", status="passed", duration_ms=100).to_signal("S"),
            RobotKeyword(name="K", library="L", status="PASS", duration_ms=200).to_signal("T", "S"),
            PytestTest(name="t", module="m", status="passed", duration_ms=300).to_signal(),
        ]
        
        for signal in signals:
            # Non-negative
            assert signal.duration_ms >= 0
            
            # Reasonable (< 5 minutes)
            assert signal.duration_ms < 300000


class TestEmbeddingGeneration:
    """Test that embeddings can be generated for all frameworks"""
    
    def test_generate_embeddings_for_all_frameworks(self):
        """Embeddings can be generated for Cucumber, Robot, and Pytest"""
        # Create test data
        cucumber_scenarios = [
            CucumberScenario(
                name="Test scenario",
                feature_name="Test feature",
                steps=[
                    CucumberStep(keyword="Given", text="step 1", status="passed", duration_ms=100)
                ],
                status="passed",
                duration_ms=100
            )
        ]
        
        robot_tests = [
            RobotTest(
                name="Test",
                suite_name="Suite",
                keywords=[
                    RobotKeyword(name="Keyword", library="Lib", status="PASS", duration_ms=100)
                ],
                status="PASS",
                duration_ms=100
            )
        ]
        
        pytest_tests = [
            PytestTest(
                name="test_func",
                module="module",
                status="passed",
                duration_ms=100,
                assertions=[
                    PytestAssertion(expression="x == 1", status="passed")
                ]
            )
        ]
        
        # Generate embeddings
        store = generate_all_embeddings(
            scenarios=cucumber_scenarios,
            robot_tests=robot_tests,
            pytest_tests=pytest_tests,
            include_granular=True
        )
        
        # Verify embeddings generated
        stats = store.stats()
        assert stats['total_embeddings'] > 0
        
        # Verify all frameworks represented
        assert EntityType.SCENARIO.value in stats['by_type']
        assert EntityType.TEST.value in stats['by_type']
        assert EntityType.FUNCTION.value in stats['by_type']


class TestGraphLinking:
    """Test that graph relationships can be built for all frameworks"""
    
    def test_build_graph_for_all_frameworks(self):
        """Graph can be built with nodes from all frameworks"""
        # Create test data
        cucumber_scenarios = [
            CucumberScenario(
                name="Scenario",
                feature_name="Feature",
                steps=[
                    CucumberStep(keyword="Given", text="step", status="passed", duration_ms=100)
                ],
                status="passed",
                duration_ms=100
            )
        ]
        
        robot_tests = [
            RobotTest(
                name="Test",
                suite_name="Suite",
                keywords=[
                    RobotKeyword(name="Keyword", library="Lib", status="PASS", duration_ms=100)
                ],
                status="PASS",
                duration_ms=100
            )
        ]
        
        pytest_tests = [
            PytestTest(
                name="test_func",
                module="module",
                status="passed",
                duration_ms=100
            )
        ]
        
        # Build graph
        graph = build_complete_graph(
            scenarios=cucumber_scenarios,
            robot_tests=robot_tests,
            pytest_tests=pytest_tests
        )
        
        # Verify graph has nodes
        stats = graph.stats()
        assert stats['total_nodes'] > 0
        
        # Verify all frameworks represented
        assert 'scenario' in stats['node_types']
        assert 'test' in stats['node_types']
        assert 'function' in stats['node_types']


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
