"""
Unified test executor.

Framework-agnostic test execution engine that delegates to specific adapters.
"""

import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path

from adapters.common.base import BaseTestAdapter, TestResult
from .models import (
    TestExecutionRequest,
    TestExecutionResult,
    ExecutionSummary,
    ExecutionStatus,
    ExecutionStrategy,
    ResourceAllocation,
    ExecutionContext
)
from .adapter_registry import AdapterRegistry


class TestExecutor:
    """
    Unified test executor.
    
    Executes tests using appropriate framework adapters with support for
    parallel execution, retries, and resource management.
    """
    __test__ = False  # Tell pytest not to collect this class
    
    def __init__(
        self,
        resource_allocation: Optional[ResourceAllocation] = None,
        context: Optional[ExecutionContext] = None
    ):
        """
        Initialize test executor.
        
        Args:
            resource_allocation: Resource allocation configuration
            context: Execution context (auto-detected if not provided)
        """
        self.resource_allocation = resource_allocation or ResourceAllocation.auto_detect()
        self.context = context or ExecutionContext.detect()
        self.adapter_registry = AdapterRegistry()
    
    def execute(self, request: TestExecutionRequest) -> ExecutionSummary:
        """
        Execute tests based on request.
        
        Args:
            request: Test execution request
            
        Returns:
            Execution summary with results
        """
        summary = ExecutionSummary(
            status=ExecutionStatus.PENDING,
            start_time=datetime.now(),
            strategy_used=request.strategy
        )
        
        try:
            # Get appropriate adapter
            adapter = self._get_adapter(request)
            
            # Discover tests if not specified
            if request.tests is None:
                print(f"Discovering tests in {request.framework}...")
                discovered = adapter.discover_tests()
                request.tests = discovered
                print(f"Found {len(discovered)} tests")
            
            if not request.tests:
                summary.status = ExecutionStatus.SKIPPED
                summary.warnings.append("No tests to execute")
                return summary
            
            # Execute based on strategy
            if request.strategy == ExecutionStrategy.SEQUENTIAL:
                results = self._execute_sequential(adapter, request)
            elif request.strategy == ExecutionStrategy.PARALLEL:
                results = self._execute_parallel(adapter, request)
            elif request.strategy == ExecutionStrategy.ADAPTIVE:
                # Choose strategy based on test count
                if len(request.tests) > 10:
                    results = self._execute_parallel(adapter, request)
                    summary.strategy_used = ExecutionStrategy.PARALLEL
                else:
                    results = self._execute_sequential(adapter, request)
                    summary.strategy_used = ExecutionStrategy.SEQUENTIAL
            else:
                raise ValueError(f"Unsupported strategy: {request.strategy}")
            
            # Add results to summary
            for result in results:
                summary.add_result(result)
            
            # Handle retries for failed tests
            if request.retry_failed > 0:
                failed_tests = [r for r in results if r.status == ExecutionStatus.FAILED]
                if failed_tests:
                    print(f"\nRetrying {len(failed_tests)} failed tests...")
                    retry_results = self._retry_failed_tests(
                        adapter, request, failed_tests
                    )
                    for result in retry_results:
                        summary.add_result(result)
            
            # Determine overall status
            if summary.errors > 0:
                summary.status = ExecutionStatus.ERROR
            elif summary.failed > 0:
                summary.status = ExecutionStatus.FAILED
            elif summary.passed > 0:
                summary.status = ExecutionStatus.PASSED
            else:
                summary.status = ExecutionStatus.SKIPPED
        
        except Exception as e:
            summary.status = ExecutionStatus.ERROR
            summary.execution_errors.append(f"Execution failed: {str(e)}")
        
        finally:
            summary.end_time = datetime.now()
            if summary.start_time:
                duration = (summary.end_time - summary.start_time).total_seconds()
                summary.total_duration_ms = int(duration * 1000)
        
        return summary
    
    def _get_adapter(self, request: TestExecutionRequest) -> BaseTestAdapter:
        """Get adapter for framework."""
        try:
            return self.adapter_registry.get_adapter(
                request.framework,
                request.project_root
            )
        except Exception as e:
            raise ValueError(
                f"Failed to load adapter for {request.framework}: {str(e)}"
            )
    
    def _execute_sequential(
        self,
        adapter: BaseTestAdapter,
        request: TestExecutionRequest
    ) -> List[TestExecutionResult]:
        """Execute tests sequentially."""
        results = []
        
        print(f"\nExecuting {len(request.tests)} tests sequentially...")
        
        # Execute all tests through adapter
        adapter_results = adapter.run_tests(
            tests=request.tests,
            tags=request.tags
        )
        
        # Convert adapter results to execution results
        for adapter_result in adapter_results:
            result = self._convert_adapter_result(
                adapter_result,
                request.framework
            )
            results.append(result)
            
            # Print progress
            status_symbol = "✓" if result.status == ExecutionStatus.PASSED else "✗"
            print(f"  {status_symbol} {result.name} ({result.duration_ms}ms)")
        
        return results
    
    def _execute_parallel(
        self,
        adapter: BaseTestAdapter,
        request: TestExecutionRequest
    ) -> List[TestExecutionResult]:
        """Execute tests in parallel using thread pool."""
        results = []
        max_workers = min(
            request.max_workers or self.resource_allocation.max_workers,
            len(request.tests)
        )
        
        print(f"\nExecuting {len(request.tests)} tests in parallel "
              f"(workers: {max_workers})...")
        
        # For most adapters, we need to run all tests together
        # (they handle parallelization internally or don't support per-test execution)
        # So we just run the full suite, but with parallelization hints
        
        adapter_results = adapter.run_tests(
            tests=request.tests,
            tags=request.tags
        )
        
        for adapter_result in adapter_results:
            result = self._convert_adapter_result(
                adapter_result,
                request.framework
            )
            results.append(result)
            
            status_symbol = "✓" if result.status == ExecutionStatus.PASSED else "✗"
            print(f"  {status_symbol} {result.name} ({result.duration_ms}ms)")
        
        return results
    
    def _retry_failed_tests(
        self,
        adapter: BaseTestAdapter,
        request: TestExecutionRequest,
        failed_results: List[TestExecutionResult]
    ) -> List[TestExecutionResult]:
        """Retry failed tests."""
        retry_results = []
        
        # Extract test names from failed results
        failed_test_names = [r.test_id for r in failed_results]
        
        for attempt in range(request.retry_failed):
            print(f"  Retry attempt {attempt + 1}/{request.retry_failed}...")
            
            # Wait before retry if configured
            if self.resource_allocation.retry_delay > 0:
                time.sleep(self.resource_allocation.retry_delay)
            
            # Re-run failed tests
            adapter_results = adapter.run_tests(
                tests=failed_test_names,
                tags=request.tags
            )
            
            for adapter_result in adapter_results:
                result = self._convert_adapter_result(
                    adapter_result,
                    request.framework
                )
                result.retry_count = attempt + 1
                
                # Check if test now passes
                if result.status == ExecutionStatus.PASSED:
                    result.is_flaky = True
                    print(f"  ✓ {result.name} passed on retry {attempt + 1}")
                
                retry_results.append(result)
        
        return retry_results
    
    def _convert_adapter_result(
        self,
        adapter_result: TestResult,
        framework: str
    ) -> TestExecutionResult:
        """Convert adapter TestResult to ExecutionResult."""
        # Map adapter status to execution status
        status_map = {
            'pass': ExecutionStatus.PASSED,
            'fail': ExecutionStatus.FAILED,
            'skip': ExecutionStatus.SKIPPED,
            'error': ExecutionStatus.ERROR
        }
        
        status = status_map.get(
            adapter_result.status.lower(),
            ExecutionStatus.ERROR
        )
        
        return TestExecutionResult(
            test_id=adapter_result.name,
            name=adapter_result.name,
            status=status,
            duration_ms=adapter_result.duration_ms,
            message=adapter_result.message,
            framework=framework
        )


class ExecutionPipeline:
    """
    Test execution pipeline with pre/post hooks.
    
    Allows customization of execution workflow with hooks for setup,
    cleanup, reporting, etc.
    """
    
    def __init__(self, executor: Optional[TestExecutor] = None):
        """Initialize execution pipeline."""
        self.executor = executor or TestExecutor()
        self.pre_execution_hooks = []
        self.post_execution_hooks = []
        self.per_test_hooks = []
    
    def add_pre_execution_hook(self, hook):
        """Add hook to run before execution."""
        self.pre_execution_hooks.append(hook)
    
    def add_post_execution_hook(self, hook):
        """Add hook to run after execution."""
        self.post_execution_hooks.append(hook)
    
    def add_per_test_hook(self, hook):
        """Add hook to run after each test."""
        self.per_test_hooks.append(hook)
    
    def execute(self, request: TestExecutionRequest) -> ExecutionSummary:
        """Execute with hooks."""
        # Run pre-execution hooks
        for hook in self.pre_execution_hooks:
            try:
                hook(request)
            except Exception as e:
                print(f"Warning: Pre-execution hook failed: {e}")
        
        # Execute tests
        summary = self.executor.execute(request)
        
        # Run post-execution hooks
        for hook in self.post_execution_hooks:
            try:
                hook(request, summary)
            except Exception as e:
                print(f"Warning: Post-execution hook failed: {e}")
        
        return summary
