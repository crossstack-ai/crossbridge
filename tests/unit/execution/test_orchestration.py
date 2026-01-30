"""
Tests for Execution Orchestration

Comprehensive tests for the execution orchestration system including:
- Execution API data models
- Execution strategies (Smoke, Impacted, Risk, Full)
- Framework adapters (TestNG, Robot, Pytest)
- Execution orchestrator
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from core.execution.orchestration import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionPlan,
    ExecutionStatus,
    ExecutionContext,
    StrategyType,
    SmokeStrategy,
    ImpactedStrategy,
    RiskBasedStrategy,
    FullStrategy,
    create_strategy,
    ExecutionOrchestrator,
    create_orchestrator,
)


# ═════════════════════════════════════════════════════════════════════════
# API MODELS TESTS
# ═════════════════════════════════════════════════════════════════════════

class TestExecutionRequest:
    """Test ExecutionRequest model"""
    
    def test_create_basic_request(self):
        """Test creating a basic execution request"""
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.SMOKE,
            environment="dev"
        )
        
        assert request.framework == "pytest"
        assert request.strategy == StrategyType.SMOKE
        assert request.environment == "dev"
        assert request.ci_mode is False
        assert request.dry_run is False
    
    def test_request_with_string_strategy(self):
        """Test creating request with string strategy (auto-converted)"""
        request = ExecutionRequest(
            framework="testng",
            strategy="impacted",
            environment="staging"
        )
        
        assert request.strategy == StrategyType.IMPACTED
    
    def test_request_with_constraints(self):
        """Test request with various constraints"""
        request = ExecutionRequest(
            framework="robot",
            strategy=StrategyType.RISK_BASED,
            environment="prod",
            max_tests=50,
            max_duration_minutes=30,
            tags=["critical", "api"],
            exclude_tags=["slow"],
            include_flaky=False
        )
        
        assert request.max_tests == 50
        assert request.max_duration_minutes == 30
        assert "critical" in request.tags
        assert "slow" in request.exclude_tags
        assert request.include_flaky is False


class TestExecutionPlan:
    """Test ExecutionPlan model"""
    
    def test_create_plan(self):
        """Test creating an execution plan"""
        plan = ExecutionPlan(
            selected_tests=["test1", "test2", "test3"],
            skipped_tests=["test4", "test5"],
            grouping={"group1": ["test1", "test2"], "group2": ["test3"]},
            priority={"test1": 5, "test2": 4, "test3": 3},
            reasons={"test1": "Critical test", "test2": "Recent failure"},
            framework="pytest",
            strategy=StrategyType.RISK_BASED,
            environment="staging",
            parallel=True
        )
        
        assert plan.total_tests() == 3
        assert plan.framework == "pytest"
        assert plan.parallel is True
    
    def test_reduction_percentage(self):
        """Test calculation of test reduction"""
        plan = ExecutionPlan(
            selected_tests=["test1", "test2"],
            skipped_tests=["test3", "test4", "test5", "test6", "test7", "test8"],
            grouping={},
            priority={},
            reasons={},
            framework="testng",
            strategy=StrategyType.IMPACTED,
            environment="dev",
            parallel=False
        )
        
        # 2 selected out of 10 total = 80% reduction
        reduction = plan.reduction_percentage(10)
        assert reduction == 80.0


class TestExecutionResult:
    """Test ExecutionResult model"""
    
    def test_create_result(self):
        """Test creating an execution result"""
        result = ExecutionResult(
            executed_tests=["test1", "test2", "test3"],
            passed_tests=["test1", "test2"],
            failed_tests=["test3"],
            skipped_tests=[],
            error_tests=[],
            execution_time_seconds=120.5,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=["report.xml"],
            log_paths=["log.txt"],
            framework="pytest",
            environment="dev"
        )
        
        assert len(result.executed_tests) == 3
        assert result.has_failures() is True
    
    def test_pass_rate_calculation(self):
        """Test pass rate calculation"""
        result = ExecutionResult(
            executed_tests=["t1", "t2", "t3", "t4", "t5"],
            passed_tests=["t1", "t2", "t3"],
            failed_tests=["t4", "t5"],
            skipped_tests=[],
            error_tests=[],
            execution_time_seconds=100,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[],
            log_paths=[],
            framework="robot",
            environment="qa"
        )
        
        assert result.pass_rate() == 60.0  # 3/5 = 60%
        assert result.failure_rate() == 40.0


# ═════════════════════════════════════════════════════════════════════════
# STRATEGY TESTS
# ═════════════════════════════════════════════════════════════════════════

class TestSmokeStrategy:
    """Test smoke test strategy"""
    
    def test_smoke_strategy_selects_tagged_tests(self):
        """Test that smoke strategy selects tests with smoke tags"""
        strategy = SmokeStrategy()
        
        # Create context with mixed tests
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.SMOKE,
            environment="dev"
        )
        
        context = ExecutionContext(
            request=request,
            available_tests=["test1", "test2", "test3", "test4"],
            test_metadata={
                "test1": {"tags": ["smoke", "api"]},
                "test2": {"tags": ["integration"]},
                "test3": {"tags": ["critical"]},
                "test4": {"tags": ["slow"]},
            }
        )
        
        plan = strategy.select_tests(context)
        
        # Should select test1 (smoke) and test3 (critical)
        assert "test1" in plan.selected_tests
        assert "test3" in plan.selected_tests
        assert "test2" not in plan.selected_tests
        assert "test4" not in plan.selected_tests
        
        # Check reasons
        assert "smoke" in plan.reasons["test1"].lower()
        assert plan.priority["test1"] == 5


class TestImpactedStrategy:
    """Test impacted test strategy"""
    
    def test_impacted_strategy_selects_covered_tests(self):
        """Test that impacted strategy selects tests covering changed files"""
        strategy = ImpactedStrategy()
        
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.IMPACTED,
            environment="staging"
        )
        
        context = ExecutionContext(
            request=request,
            available_tests=["test1", "test2", "test3"],
            test_metadata={},
            changed_files=["src/auth.py", "src/api.py"],
            test_to_code_mapping={
                "test1": ["src/auth.py", "src/utils.py"],
                "test2": ["src/database.py"],
                "test3": ["src/api.py"],
            }
        )
        
        plan = strategy.select_tests(context)
        
        # Should select test1 (covers auth.py) and test3 (covers api.py)
        assert "test1" in plan.selected_tests
        assert "test3" in plan.selected_tests
        assert "test2" not in plan.selected_tests
        
        # Check reasons mention the files
        assert "auth.py" in plan.reasons["test1"]
        assert "api.py" in plan.reasons["test3"]
    
    def test_impacted_strategy_fallback_to_smoke(self):
        """Test fallback to smoke when no files changed"""
        strategy = ImpactedStrategy()
        
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.IMPACTED,
            environment="dev"
        )
        
        context = ExecutionContext(
            request=request,
            available_tests=["test1", "test2"],
            test_metadata={
                "test1": {"tags": ["smoke"]},
                "test2": {"tags": []},
            },
            changed_files=[],  # No changes
        )
        
        plan = strategy.select_tests(context)
        
        # Should fall back to smoke
        assert "test1" in plan.selected_tests
        assert len(plan.selected_tests) >= 1


class TestRiskBasedStrategy:
    """Test risk-based strategy"""
    
    def test_risk_strategy_ranks_by_failure_rate(self):
        """Test that risk strategy ranks tests by failure rate"""
        strategy = RiskBasedStrategy()
        
        request = ExecutionRequest(
            framework="testng",
            strategy=StrategyType.RISK_BASED,
            environment="prod",
            max_tests=2
        )
        
        context = ExecutionContext(
            request=request,
            available_tests=["test1", "test2", "test3"],
            test_metadata={},
            failure_rates={
                "test1": 0.5,  # 50% failure rate
                "test2": 0.1,  # 10% failure rate
                "test3": 0.8,  # 80% failure rate
            }
        )
        
        plan = strategy.select_tests(context)
        
        # Should select top 2 risky tests
        assert len(plan.selected_tests) == 2
        assert "test3" in plan.selected_tests  # Highest risk
        assert "test1" in plan.selected_tests  # Second highest
        assert "test2" not in plan.selected_tests  # Lowest risk
    
    def test_risk_strategy_considers_criticality(self):
        """Test that risk strategy considers criticality tags"""
        strategy = RiskBasedStrategy()
        
        request = ExecutionRequest(
            framework="robot",
            strategy=StrategyType.RISK_BASED,
            environment="prod"
        )
        
        context = ExecutionContext(
            request=request,
            available_tests=["test1", "test2"],
            test_metadata={
                "test1": {"tags": ["critical"]},
                "test2": {"tags": []},
            },
            failure_rates={
                "test1": 0.1,
                "test2": 0.5,  # Higher failure rate but not critical
            }
        )
        
        plan = strategy.select_tests(context)
        
        # test1 should rank higher despite lower failure rate (critical tag)
        assert plan.priority["test1"] >= plan.priority.get("test2", 0)


class TestFullStrategy:
    """Test full strategy"""
    
    def test_full_strategy_selects_all_tests(self):
        """Test that full strategy selects all available tests"""
        strategy = FullStrategy()
        
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.FULL,
            environment="prod"
        )
        
        context = ExecutionContext(
            request=request,
            available_tests=["test1", "test2", "test3", "test4", "test5"],
            test_metadata={}
        )
        
        plan = strategy.select_tests(context)
        
        assert len(plan.selected_tests) == 5
        assert set(plan.selected_tests) == set(context.available_tests)


class TestStrategyFactory:
    """Test strategy factory"""
    
    def test_create_smoke_strategy(self):
        """Test creating smoke strategy via factory"""
        strategy = create_strategy(StrategyType.SMOKE)
        assert isinstance(strategy, SmokeStrategy)
    
    def test_create_impacted_strategy(self):
        """Test creating impacted strategy via factory"""
        strategy = create_strategy(StrategyType.IMPACTED)
        assert isinstance(strategy, ImpactedStrategy)
    
    def test_create_risk_strategy(self):
        """Test creating risk strategy via factory"""
        strategy = create_strategy(StrategyType.RISK_BASED)
        assert isinstance(strategy, RiskBasedStrategy)
    
    def test_create_full_strategy(self):
        """Test creating full strategy via factory"""
        strategy = create_strategy(StrategyType.FULL)
        assert isinstance(strategy, FullStrategy)


# ═════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR TESTS
# ═════════════════════════════════════════════════════════════════════════

class TestExecutionOrchestrator:
    """Test execution orchestrator"""
    
    @pytest.fixture
    def workspace(self, tmp_path):
        """Create temporary workspace"""
        return tmp_path
    
    @pytest.fixture
    def orchestrator(self, workspace):
        """Create orchestrator instance"""
        return ExecutionOrchestrator(workspace, config={})
    
    def test_create_orchestrator(self, workspace):
        """Test creating orchestrator"""
        orchestrator = ExecutionOrchestrator(workspace)
        assert orchestrator.workspace == workspace
        assert orchestrator.config == {}
    
    def test_plan_execution(self, orchestrator, monkeypatch):
        """Test generating execution plan"""
        # Mock test discovery
        monkeypatch.setattr(
            orchestrator,
            "_discover_tests",
            lambda fw: ["test1", "test2", "test3"]
        )
        
        monkeypatch.setattr(
            orchestrator,
            "_load_test_metadata",
            lambda fw: {
                "test1": {"tags": ["smoke"]},
                "test2": {"tags": []},
                "test3": {"tags": ["critical"]},
            }
        )
        
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.SMOKE,
            environment="dev"
        )
        
        plan = orchestrator.plan(request)
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.selected_tests) > 0
    
    def test_dry_run_execution(self, orchestrator, monkeypatch):
        """Test dry-run execution (plan only)"""
        monkeypatch.setattr(
            orchestrator,
            "_discover_tests",
            lambda fw: ["test1", "test2"]
        )
        
        monkeypatch.setattr(
            orchestrator,
            "_load_test_metadata",
            lambda fw: {"test1": {"tags": ["smoke"]}, "test2": {"tags": []}}
        )
        
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.SMOKE,
            environment="dev",
            dry_run=True
        )
        
        result = orchestrator.execute(request)
        
        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.executed_tests) == 0  # Dry run doesn't execute


class TestOrchestratorFactory:
    """Test orchestrator factory"""
    
    def test_create_orchestrator_with_defaults(self):
        """Test creating orchestrator with defaults"""
        orchestrator = create_orchestrator()
        assert isinstance(orchestrator, ExecutionOrchestrator)
        assert orchestrator.workspace == Path.cwd()
    
    def test_create_orchestrator_with_workspace(self, tmp_path):
        """Test creating orchestrator with specific workspace"""
        orchestrator = create_orchestrator(workspace=tmp_path)
        assert orchestrator.workspace == tmp_path


# ═════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═════════════════════════════════════════════════════════════════════════

class TestExecutionIntegration:
    """Integration tests for full execution flow"""
    
    def test_smoke_execution_flow(self, tmp_path, monkeypatch):
        """Test complete smoke execution flow"""
        orchestrator = create_orchestrator(workspace=tmp_path)
        
        # Mock discovery
        monkeypatch.setattr(
            orchestrator,
            "_discover_tests",
            lambda fw: ["smoke_test", "slow_test", "critical_test"]
        )
        
        monkeypatch.setattr(
            orchestrator,
            "_load_test_metadata",
            lambda fw: {
                "smoke_test": {"tags": ["smoke"]},
                "slow_test": {"tags": ["slow"]},
                "critical_test": {"tags": ["critical"]},
            }
        )
        
        # Create request
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.SMOKE,
            environment="dev",
            dry_run=True  # Don't actually execute
        )
        
        # Execute
        result = orchestrator.execute(request)
        
        # Verify
        assert result.status == ExecutionStatus.COMPLETED
    
    def test_impacted_execution_with_git_changes(self, tmp_path, monkeypatch):
        """Test impacted execution with git changes"""
        orchestrator = create_orchestrator(workspace=tmp_path)
        
        # Mock discovery
        monkeypatch.setattr(
            orchestrator,
            "_discover_tests",
            lambda fw: ["test_auth", "test_api", "test_database"]
        )
        
        monkeypatch.setattr(
            orchestrator,
            "_load_test_metadata",
            lambda fw: {}
        )
        
        monkeypatch.setattr(
            orchestrator,
            "_load_coverage_mapping",
            lambda: {
                "test_auth": ["src/auth.py"],
                "test_api": ["src/api.py"],
                "test_database": ["src/db.py"],
            }
        )
        
        # Create request with changed files
        request = ExecutionRequest(
            framework="pytest",
            strategy=StrategyType.IMPACTED,
            environment="staging",
            changed_files=["src/auth.py", "src/api.py"],
            dry_run=True
        )
        
        # Execute
        result = orchestrator.execute(request)
        
        # Verify
        assert result.status == ExecutionStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
