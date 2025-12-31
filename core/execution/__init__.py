"""
Unified test execution engine for CrossBridge.

Provides framework-agnostic test execution with support for:
- Multiple execution strategies (sequential, parallel, adaptive)
- Resource allocation and management
- Retry policies and flaky test handling
- Execution hooks and customization
- Framework adapter registry

Example Usage:
    from core.execution import TestExecutor, TestExecutionRequest, ExecutionStrategy
    
    # Create execution request
    request = TestExecutionRequest(
        framework="pytest",
        project_root="/path/to/project",
        tests=["test_login.py::test_valid_credentials"],
        strategy=ExecutionStrategy.PARALLEL,
        max_workers=4
    )
    
    # Execute tests
    executor = TestExecutor()
    summary = executor.execute(request)
    
    # Check results
    print(f"Passed: {summary.passed}/{summary.total_tests}")
    print(f"Success rate: {summary.success_rate:.1f}%")
"""

from .models import (
    ExecutionStatus,
    ExecutionStrategy,
    TestExecutionRequest,
    TestExecutionResult,
    ExecutionSummary,
    ResourceAllocation,
    ExecutionContext
)

from .executor import (
    TestExecutor,
    ExecutionPipeline
)

from .adapter_registry import (
    AdapterRegistry,
    get_adapter,
    register_adapter,
    list_adapters
)

from .strategies import (
    SequentialStrategy,
    ParallelStrategy,
    BatchedParallelStrategy,
    AdaptiveStrategy,
    FailFastStrategy,
    RetryStrategy,
    get_strategy
)

__all__ = [
    # Models
    'ExecutionStatus',
    'ExecutionStrategy',
    'TestExecutionRequest',
    'TestExecutionResult',
    'ExecutionSummary',
    'ResourceAllocation',
    'ExecutionContext',
    
    # Executor
    'TestExecutor',
    'ExecutionPipeline',
    
    # Registry
    'AdapterRegistry',
    'get_adapter',
    'register_adapter',
    'list_adapters',
    
    # Strategies
    'SequentialStrategy',
    'ParallelStrategy',
    'BatchedParallelStrategy',
    'AdaptiveStrategy',
    'FailFastStrategy',
    'RetryStrategy',
    'get_strategy',
]
