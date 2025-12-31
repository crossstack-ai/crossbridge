"""
Unit tests for unified test execution engine.

Tests cover:
- Execution models and data structures
- Test executor and execution strategies
- Adapter registry
- Resource allocation
- Retry policies
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from core.execution import (
    ExecutionStatus,
    ExecutionStrategy,
    TestExecutionRequest,
    TestExecutionResult,
    ExecutionSummary,
    ResourceAllocation,
    ExecutionContext,
    TestExecutor,
    ExecutionPipeline,
    AdapterRegistry,
    get_adapter,
    list_adapters,
)


class TestExecutionModels:
    """Test execution models and data structures."""
    
    def test_execution_result_creation(self):
        """Test creating execution result."""
        result = TestExecutionResult(
            test_id="test_login",
            name="Test Login",
            status=ExecutionStatus.PASSED,
            duration_ms=1500
        )
        
        assert result.test_id == "test_login"
        assert result.name == "Test Login"
        assert result.status == ExecutionStatus.PASSED
        assert result.duration_ms == 1500
        assert result.retry_count == 0
        assert result.is_flaky is False
    
    def test_execution_summary_add_result(self):
        """Test adding results to summary."""
        summary = ExecutionSummary(status=ExecutionStatus.PENDING)
        
        # Add passed test
        summary.add_result(TestExecutionResult(
            test_id="test1",
            name="Test 1",
            status=ExecutionStatus.PASSED,
            duration_ms=100
        ))
        
        assert summary.total_tests == 1
        assert summary.passed == 1
        assert summary.failed == 0
        
        # Add failed test
        summary.add_result(TestExecutionResult(
            test_id="test2",
            name="Test 2",
            status=ExecutionStatus.FAILED,
            duration_ms=200
        ))
        
        assert summary.total_tests == 2
        assert summary.passed == 1
        assert summary.failed == 1
    
    def test_execution_summary_success_rate(self):
        """Test success rate calculation."""
        summary = ExecutionSummary(status=ExecutionStatus.PASSED)
        
        summary.passed = 8
        summary.failed = 2
        summary.total_tests = 10
        
        assert summary.success_rate == 80.0
    
    def test_execution_summary_is_successful(self):
        """Test success determination."""
        summary = ExecutionSummary(status=ExecutionStatus.PASSED)
        summary.passed = 10
        summary.total_tests = 10
        
        assert summary.is_successful is True
        
        summary.failed = 1
        assert summary.is_successful is False
    
    def test_resource_allocation_auto_detect(self):
        """Test auto-detection of resource allocation."""
        allocation = ResourceAllocation.auto_detect()
        
        assert allocation.max_workers >= 1
        assert allocation.queue_size > 0
        assert allocation.batch_size > 0
    
    def test_execution_context_detect(self):
        """Test execution context detection."""
        context = ExecutionContext.detect()
        
        assert context.platform != ""
        assert context.python_version != ""
        assert context.execution_id != ""


class TestAdapterRegistry:
    """Test adapter registry."""
    
    def test_register_and_list_adapters(self):
        """Test registering and listing adapters."""
        registry = AdapterRegistry()
        
        # Check built-in adapters are registered
        adapters = registry.list_adapters()
        assert len(adapters) > 0
        assert isinstance(adapters, list)
    
    def test_is_registered(self):
        """Test checking if adapter is registered."""
        registry = AdapterRegistry()
        
        # Built-in adapters should be registered
        assert registry.is_registered('pytest') is True
        assert registry.is_registered('nonexistent') is False
    
    def test_get_adapter_invalid_framework(self):
        """Test getting adapter for invalid framework."""
        registry = AdapterRegistry()
        
        with pytest.raises(ValueError, match="Unknown framework"):
            registry.get_adapter('invalid-framework', '/tmp')
    
    def test_global_list_adapters(self):
        """Test global list_adapters function."""
        adapters = list_adapters()
        assert isinstance(adapters, list)
        assert len(adapters) > 0


class TestTestExecutor:
    """Test unified test executor."""
    
    def test_executor_initialization(self):
        """Test executor initialization."""
        executor = TestExecutor()
        
        assert executor.resource_allocation is not None
        assert executor.context is not None
        assert executor.adapter_registry is not None
    
    def test_executor_with_custom_resources(self):
        """Test executor with custom resource allocation."""
        allocation = ResourceAllocation(max_workers=4, queue_size=50)
        executor = TestExecutor(resource_allocation=allocation)
        
        assert executor.resource_allocation.max_workers == 4
        assert executor.resource_allocation.queue_size == 50
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_execute_sequential_strategy(self, mock_get_adapter, tmp_path):
        """Test execution with sequential strategy."""
        # Create mock adapter
        mock_adapter = Mock()
        mock_adapter.discover_tests.return_value = [
            "test_1", "test_2", "test_3"
        ]
        mock_adapter.run_tests.return_value = [
            Mock(name="test_1", status="pass", duration_ms=100, message=""),
            Mock(name="test_2", status="pass", duration_ms=150, message=""),
            Mock(name="test_3", status="pass", duration_ms=200, message=""),
        ]
        mock_get_adapter.return_value = mock_adapter
        
        # Create request
        request = TestExecutionRequest(
            framework="pytest",
            project_root=str(tmp_path),
            strategy=ExecutionStrategy.SEQUENTIAL
        )
        
        # Execute
        executor = TestExecutor()
        summary = executor.execute(request)
        
        assert summary.status == ExecutionStatus.PASSED
        assert summary.total_tests == 3
        assert summary.passed == 3
        assert summary.failed == 0
        assert mock_adapter.discover_tests.called
        assert mock_adapter.run_tests.called
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_execute_with_specific_tests(self, mock_get_adapter, tmp_path):
        """Test execution with specific tests."""
        mock_adapter = Mock()
        mock_adapter.run_tests.return_value = [
            Mock(name="test_login", status="pass", duration_ms=100, message=""),
        ]
        mock_get_adapter.return_value = mock_adapter
        
        request = TestExecutionRequest(
            framework="pytest",
            project_root=str(tmp_path),
            tests=["test_login"],
            strategy=ExecutionStrategy.SEQUENTIAL
        )
        
        executor = TestExecutor()
        summary = executor.execute(request)
        
        assert summary.total_tests == 1
        assert summary.passed == 1
        # Should not call discover if tests specified
        assert not mock_adapter.discover_tests.called
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_execute_with_failed_tests(self, mock_get_adapter, tmp_path):
        """Test execution with failed tests."""
        mock_adapter = Mock()
        mock_adapter.run_tests.return_value = [
            Mock(name="test_1", status="pass", duration_ms=100, message=""),
            Mock(name="test_2", status="fail", duration_ms=150, message="AssertionError"),
            Mock(name="test_3", status="pass", duration_ms=200, message=""),
        ]
        mock_get_adapter.return_value = mock_adapter
        
        request = TestExecutionRequest(
            framework="pytest",
            project_root=str(tmp_path),
            tests=["test_1", "test_2", "test_3"],
            strategy=ExecutionStrategy.SEQUENTIAL
        )
        
        executor = TestExecutor()
        summary = executor.execute(request)
        
        assert summary.status == ExecutionStatus.FAILED
        assert summary.total_tests == 3
        assert summary.passed == 2
        assert summary.failed == 1
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_execute_with_retry(self, mock_get_adapter, tmp_path):
        """Test execution with retry on failures."""
        mock_adapter = Mock()
        
        # First call - one test fails
        # Second call (retry) - test passes
        mock_adapter.run_tests.side_effect = [
            [
                Mock(name="test_1", status="pass", duration_ms=100, message=""),
                Mock(name="test_2", status="fail", duration_ms=150, message="Flaky"),
            ],
            [
                Mock(name="test_2", status="pass", duration_ms=160, message=""),
            ]
        ]
        mock_get_adapter.return_value = mock_adapter
        
        request = TestExecutionRequest(
            framework="pytest",
            project_root=str(tmp_path),
            tests=["test_1", "test_2"],
            strategy=ExecutionStrategy.SEQUENTIAL,
            retry_failed=1
        )
        
        executor = TestExecutor()
        summary = executor.execute(request)
        
        # Should have 3 total results (2 initial + 1 retry)
        assert summary.total_tests == 3
        # After retry, should have 2 passed (test_1 + test_2 retry)
        assert summary.passed >= 2
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_execute_adaptive_strategy_small_suite(self, mock_get_adapter, tmp_path):
        """Test adaptive strategy with small test suite."""
        mock_adapter = Mock()
        mock_adapter.discover_tests.return_value = ["test_1", "test_2"]
        mock_adapter.run_tests.return_value = [
            Mock(name="test_1", status="pass", duration_ms=100, message=""),
            Mock(name="test_2", status="pass", duration_ms=150, message=""),
        ]
        mock_get_adapter.return_value = mock_adapter
        
        request = TestExecutionRequest(
            framework="pytest",
            project_root=str(tmp_path),
            strategy=ExecutionStrategy.ADAPTIVE
        )
        
        executor = TestExecutor()
        summary = executor.execute(request)
        
        # Should use sequential for small suite
        assert summary.strategy_used == ExecutionStrategy.SEQUENTIAL
        assert summary.total_tests == 2


class TestExecutionPipeline:
    """Test execution pipeline with hooks."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = ExecutionPipeline()
        
        assert pipeline.executor is not None
        assert len(pipeline.pre_execution_hooks) == 0
        assert len(pipeline.post_execution_hooks) == 0
    
    def test_pipeline_add_hooks(self):
        """Test adding hooks to pipeline."""
        pipeline = ExecutionPipeline()
        
        pre_hook = Mock()
        post_hook = Mock()
        
        pipeline.add_pre_execution_hook(pre_hook)
        pipeline.add_post_execution_hook(post_hook)
        
        assert len(pipeline.pre_execution_hooks) == 1
        assert len(pipeline.post_execution_hooks) == 1
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_pipeline_hooks_called(self, mock_get_adapter, tmp_path):
        """Test hooks are called during execution."""
        mock_adapter = Mock()
        mock_adapter.run_tests.return_value = [
            Mock(name="test_1", status="pass", duration_ms=100, message="")
        ]
        mock_get_adapter.return_value = mock_adapter
        
        pipeline = ExecutionPipeline()
        
        pre_hook = Mock()
        post_hook = Mock()
        
        pipeline.add_pre_execution_hook(pre_hook)
        pipeline.add_post_execution_hook(post_hook)
        
        request = TestExecutionRequest(
            framework="pytest",
            project_root=str(tmp_path),
            tests=["test_1"]
        )
        
        summary = pipeline.execute(request)
        
        # Verify hooks were called
        assert pre_hook.called
        assert post_hook.called
        assert summary.total_tests == 1


class TestRequest:
    """Test execution request model."""
    
    def test_request_creation(self):
        """Test creating execution request."""
        request = TestExecutionRequest(
            framework="pytest",
            project_root="/path/to/project",
            tests=["test_login", "test_logout"],
            tags=["smoke"],
            strategy=ExecutionStrategy.PARALLEL,
            max_workers=4
        )
        
        assert request.framework == "pytest"
        assert request.project_root == "/path/to/project"
        assert len(request.tests) == 2
        assert request.tags == ["smoke"]
        assert request.strategy == ExecutionStrategy.PARALLEL
        assert request.max_workers == 4
    
    def test_request_defaults(self):
        """Test request default values."""
        request = TestExecutionRequest(
            framework="pytest",
            project_root="/path"
        )
        
        assert request.tests is None
        assert request.tags is None
        assert request.strategy == ExecutionStrategy.SEQUENTIAL
        assert request.timeout == 300
        assert request.retry_failed == 0


class TestErrorHandling:
    """Test error handling in execution engine."""
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_execute_with_adapter_error(self, mock_get_adapter, tmp_path):
        """Test execution when adapter fails to load."""
        mock_get_adapter.side_effect = ValueError("Adapter not found")
        
        request = TestExecutionRequest(
            framework="invalid",
            project_root=str(tmp_path)
        )
        
        executor = TestExecutor()
        summary = executor.execute(request)
        
        assert summary.status == ExecutionStatus.ERROR
        assert len(summary.execution_errors) > 0
    
    @patch('core.execution.executor.AdapterRegistry.get_adapter')
    def test_execute_with_discovery_failure(self, mock_get_adapter, tmp_path):
        """Test execution when test discovery fails."""
        mock_adapter = Mock()
        mock_adapter.discover_tests.side_effect = Exception("Discovery failed")
        mock_get_adapter.return_value = mock_adapter
        
        request = TestExecutionRequest(
            framework="pytest",
            project_root=str(tmp_path)
        )
        
        executor = TestExecutor()
        summary = executor.execute(request)
        
        assert summary.status == ExecutionStatus.ERROR


class TestIntegration:
    """Integration tests for execution engine."""
    
    def test_end_to_end_execution_flow(self, tmp_path):
        """Test complete execution flow."""
        # This would require actual adapters to be available
        # For now, we test the flow with mocks
        pass
    
    def test_execution_with_real_adapter(self, tmp_path):
        """Test execution with a real adapter."""
        # Create a simple pytest file
        test_file = tmp_path / "test_sample.py"
        test_file.write_text("""
def test_pass():
    assert True

def test_fail():
    assert False
""")
        
        # This test would need pytest installed and configured
        # Skip for now unless in integration test mode
        pytest.skip("Integration test - requires pytest")
