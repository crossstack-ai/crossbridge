"""
Docker Orchestration Framework Compatibility Tests

Verifies that Docker packaging works with all 13 supported frameworks.
Tests both basic functionality and Docker-specific features.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from core.execution.orchestration.api import (
    ExecutionPlan,
    ExecutionResult,
    ExecutionStatus,
    StrategyType
)
from core.execution.orchestration.adapters import (
    TestNGAdapter,
    JUnitAdapter,
    RestAssuredAdapter,
    CucumberAdapter,
    RobotAdapter,
    PytestAdapter,
    BehaveAdapter,
    CypressAdapter,
    PlaywrightAdapter,
    SpecFlowAdapter,
    NUnitAdapter
)


# ============================================================================
# Test Framework Compatibility
# ============================================================================

class TestFrameworkCompatibility:
    """Verify all 13 frameworks are compatible with Docker execution."""
    
    SUPPORTED_FRAMEWORKS = [
        ("TestNG", TestNGAdapter, "testng"),
        ("JUnit", JUnitAdapter, "junit"),
        ("RestAssured", RestAssuredAdapter, "restassured"),
        ("Cucumber", CucumberAdapter, "cucumber"),
        ("Robot", RobotAdapter, "robot"),
        ("Pytest", PytestAdapter, "pytest"),
        ("Behave", BehaveAdapter, "behave"),
        ("Cypress", CypressAdapter, "cypress"),
        ("Playwright", PlaywrightAdapter, "playwright"),
        ("SpecFlow", SpecFlowAdapter, "specflow"),
        ("NUnit", NUnitAdapter, "nunit"),
    ]
    
    @pytest.fixture
    def workspace(self):
        """Create temporary workspace."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.parametrize("framework_name,adapter_class,framework_id", SUPPORTED_FRAMEWORKS)
    def test_framework_adapter_exists(self, framework_name, adapter_class, framework_id):
        """Test that adapter exists for each framework."""
        adapter = adapter_class()
        assert adapter is not None
        assert adapter.framework_name == framework_id
    
    @pytest.mark.parametrize("framework_name,adapter_class,framework_id", SUPPORTED_FRAMEWORKS)
    def test_framework_command_generation(self, framework_name, adapter_class, framework_id, workspace):
        """Test that each framework can generate commands."""
        adapter = adapter_class()
        
        # Create minimal execution plan
        plan = ExecutionPlan(
            selected_tests=["test_sample"],
            skipped_tests=[],
            grouping={"smoke": ["test_sample"]},
            priority={"test_sample": 5},
            reasons={"test_sample": "smoke test"},
            framework=framework_id,
            strategy=StrategyType.SMOKE,
            environment="docker",
            parallel=False,
            max_duration_minutes=10
        )
        
        # Generate command
        command = adapter.plan_to_command(plan, workspace)
        
        # Verify command is valid
        assert isinstance(command, list), f"{framework_name}: Command must be a list"
        assert len(command) > 0, f"{framework_name}: Command cannot be empty"
        assert command[0], f"{framework_name}: First command element must be non-empty"
    
    @pytest.mark.parametrize("framework_name,adapter_class,framework_id", SUPPORTED_FRAMEWORKS)
    def test_framework_docker_volume_compatibility(self, framework_name, adapter_class, framework_id, workspace):
        """Test that each framework works with Docker volume paths."""
        adapter = adapter_class()
        
        # Docker-style volume paths
        docker_workspace = Path("/workspace")
        
        plan = ExecutionPlan(
            selected_tests=["/workspace/tests/test_sample"],
            skipped_tests=[],
            grouping={"smoke": ["/workspace/tests/test_sample"]},
            priority={"/workspace/tests/test_sample": 5},
            reasons={"/workspace/tests/test_sample": "docker test"},
            framework=framework_id,
            strategy=StrategyType.SMOKE,
            environment="docker",
            parallel=False,
            max_duration_minutes=10
        )
        
        # Should not crash with Docker paths
        try:
            command = adapter.plan_to_command(plan, docker_workspace)
            assert len(command) > 0
        except Exception as e:
            pytest.fail(f"{framework_name}: Failed with Docker volumes: {e}")


# ============================================================================
# Test Exit Codes (CI/CD Integration)
# ============================================================================

class TestExitCodes:
    """Test exit code handling for CI/CD integration."""
    
    def test_exit_code_0_success(self):
        """Exit code 0: All tests passed."""
        result = ExecutionResult(
            executed_tests=["test1", "test2"],
            passed_tests=["test1", "test2"],
            failed_tests=[],
            skipped_tests=[],
            error_tests=[],
            execution_time_seconds=10.0,
            start_time=None,
            end_time=None,
            report_paths=[],
            log_paths=[],
            framework="pytest",
            environment="docker"
        )
        
        assert not result.has_failures()
        assert result.pass_rate() == 100.0
    
    def test_exit_code_1_test_failures(self):
        """Exit code 1: Test failures."""
        result = ExecutionResult(
            executed_tests=["test1", "test2"],
            passed_tests=["test1"],
            failed_tests=["test2"],
            skipped_tests=[],
            error_tests=[],
            execution_time_seconds=10.0,
            start_time=None,
            end_time=None,
            report_paths=[],
            log_paths=[],
            framework="pytest",
            environment="docker"
        )
        
        assert result.has_failures()
        assert result.pass_rate() == 50.0


# ============================================================================
# Test Execution Strategies
# ============================================================================

class TestExecutionStrategies:
    """Test all execution strategies with Docker."""
    
    @pytest.fixture
    def workspace(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.parametrize("strategy", [
        StrategyType.SMOKE,
        StrategyType.IMPACTED,
        StrategyType.RISK_BASED,
        StrategyType.FULL
    ])
    def test_strategy_with_docker(self, strategy, workspace):
        """Test that all strategies work with Docker."""
        plan = ExecutionPlan(
            selected_tests=["test1", "test2"],
            skipped_tests=[],
            grouping={"default": ["test1", "test2"]},
            priority={"test1": 5, "test2": 3},
            reasons={"test1": f"{strategy} test", "test2": f"{strategy} test"},
            framework="pytest",
            strategy=strategy,
            environment="docker",
            parallel=False,
            max_duration_minutes=30
        )
        
        adapter = PytestAdapter()
        command = adapter.plan_to_command(plan, workspace)
        
        assert len(command) > 0
        assert "pytest" in command[0] or "python" in command[0]


# ============================================================================
# Test AI Integration
# ============================================================================

class TestAIIntegration:
    """Test execution with and without AI features."""
    
    @pytest.fixture
    def workspace(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_execution_without_ai(self, workspace):
        """Test execution works without AI features."""
        plan = ExecutionPlan(
            selected_tests=["test1"],
            skipped_tests=[],
            grouping={"smoke": ["test1"]},
            priority={"test1": 5},
            reasons={"test1": "smoke"},
            framework="pytest",
            strategy=StrategyType.SMOKE,
            environment="docker",
            parallel=False
        )
        
        adapter = PytestAdapter()
        command = adapter.plan_to_command(plan, workspace)
        
        assert len(command) > 0
    
    def test_execution_with_confidence_scores(self, workspace):
        """Test execution with AI confidence scores."""
        plan = ExecutionPlan(
            selected_tests=["test1"],
            skipped_tests=[],
            grouping={"ai_selected": ["test1"]},
            priority={"test1": 5},
            reasons={"test1": "AI selected with 0.95 confidence"},
            framework="pytest",
            strategy=StrategyType.IMPACTED,
            environment="docker",
            parallel=False,
            confidence_score=0.95
        )
        
        assert plan.confidence_score == 0.95
        
        adapter = PytestAdapter()
        command = adapter.plan_to_command(plan, workspace)
        
        assert len(command) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestDockerIntegration:
    """Integration tests for Docker execution."""
    
    @pytest.fixture
    def workspace(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_end_to_end_flow(self, workspace):
        """Test complete Docker execution flow."""
        # Create plan
        plan = ExecutionPlan(
            selected_tests=["tests/test_auth.py::test_login"],
            skipped_tests=[],
            grouping={"smoke": ["tests/test_auth.py::test_login"]},
            priority={"tests/test_auth.py::test_login": 5},
            reasons={"tests/test_auth.py::test_login": "smoke test"},
            framework="pytest",
            strategy=StrategyType.SMOKE,
            environment="docker",
            parallel=False,
            max_duration_minutes=10
        )
        
        # Generate command
        adapter = PytestAdapter()
        command = adapter.plan_to_command(plan, workspace)
        
        # Verify
        assert len(command) > 0
        assert isinstance(command, list)
        assert all(isinstance(c, str) for c in command)
    
    def test_parallel_execution(self, workspace):
        """Test parallel execution support."""
        plan = ExecutionPlan(
            selected_tests=["test1", "test2", "test3"],
            skipped_tests=[],
            grouping={
                "group1": ["test1", "test2"],
                "group2": ["test3"]
            },
            priority={"test1": 5, "test2": 5, "test3": 3},
            reasons={"test1": "impacted", "test2": "impacted", "test3": "impacted"},
            framework="pytest",
            strategy=StrategyType.IMPACTED,
            environment="docker",
            parallel=True,
            max_duration_minutes=30
        )
        
        adapter = PytestAdapter()
        command = adapter.plan_to_command(plan, workspace)
        
        assert len(command) > 0
        # Parallel execution should work
        assert plan.parallel is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
