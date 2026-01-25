"""
Execution strategies for test execution.

Implements different strategies for running tests including sequential,
parallel, and adaptive execution.
"""

from typing import List, Callable, Optional
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time

from core.logging import get_logger, LogCategory
from .models import (
    TestExecutionRequest,
    TestExecutionResult,
    ExecutionStrategy as StrategyType,
    ResourceAllocation
)

logger = get_logger(__name__, category=LogCategory.EXECUTION)


class ExecutionStrategy(ABC):
    """Base class for execution strategies."""
    
    def __init__(self, resource_allocation: ResourceAllocation):
        """Initialize strategy."""
        self.resource_allocation = resource_allocation
    
    @abstractmethod
    def execute(
        self,
        tests: List[str],
        executor_func: Callable[[str], TestExecutionResult],
        timeout: int = 300
    ) -> List[TestExecutionResult]:
        """
        Execute tests using strategy.
        
        Args:
            tests: List of test identifiers
            executor_func: Function to execute a single test
            timeout: Timeout per test in seconds
            
        Returns:
            List of test results
        """
        pass


class SequentialStrategy(ExecutionStrategy):
    """Sequential test execution (one at a time)."""
    
    def execute(
        self,
        tests: List[str],
        executor_func: Callable[[str], TestExecutionResult],
        timeout: int = 300
    ) -> List[TestExecutionResult]:
        """Execute tests sequentially."""
        results = []
        
        for test in tests:
            try:
                result = executor_func(test)
                results.append(result)
            except Exception as e:
                # Create error result for failed test
                from .models import ExecutionStatus
                from datetime import datetime
                
                results.append(TestExecutionResult(
                    test_id=test,
                    name=test,
                    status=ExecutionStatus.ERROR,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(e)
                ))
        
        return results


class ParallelStrategy(ExecutionStrategy):
    """Parallel test execution using thread pool."""
    
    def execute(
        self,
        tests: List[str],
        executor_func: Callable[[str], TestExecutionResult],
        timeout: int = 300
    ) -> List[TestExecutionResult]:
        """Execute tests in parallel."""
        results = []
        max_workers = min(
            self.resource_allocation.max_workers,
            len(tests)
        )
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tests
            future_to_test = {
                executor.submit(executor_func, test): test
                for test in tests
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_test, timeout=timeout):
                test = future_to_test[future]
                
                try:
                    result = future.result(timeout=timeout)
                    results.append(result)
                except Exception as e:
                    from .models import ExecutionStatus
                    from datetime import datetime
                    
                    results.append(TestExecutionResult(
                        test_id=test,
                        name=test,
                        status=ExecutionStatus.ERROR,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        error_message=str(e)
                    ))
        
        return results


class BatchedParallelStrategy(ExecutionStrategy):
    """
    Parallel execution with batching.
    
    Divides tests into batches and executes batches in parallel.
    Good for large test suites.
    """
    
    def execute(
        self,
        tests: List[str],
        executor_func: Callable[[str], TestExecutionResult],
        timeout: int = 300
    ) -> List[TestExecutionResult]:
        """Execute tests in batched parallel mode."""
        results = []
        batch_size = self.resource_allocation.batch_size
        
        # Divide tests into batches
        batches = [
            tests[i:i + batch_size]
            for i in range(0, len(tests), batch_size)
        ]
        
        max_workers = min(
            self.resource_allocation.max_workers,
            len(batches)
        )
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Execute each batch
            for batch in batches:
                future_to_test = {
                    executor.submit(executor_func, test): test
                    for test in batch
                }
                
                for future in as_completed(future_to_test, timeout=timeout):
                    test = future_to_test[future]
                    
                    try:
                        result = future.result(timeout=timeout)
                        results.append(result)
                    except Exception as e:
                        from .models import ExecutionStatus
                        from datetime import datetime
                        
                        results.append(TestExecutionResult(
                            test_id=test,
                            name=test,
                            status=ExecutionStatus.ERROR,
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            error_message=str(e)
                        ))
        
        return results


class AdaptiveStrategy(ExecutionStrategy):
    """
    Adaptive execution strategy.
    
    Automatically chooses between sequential and parallel based on:
    - Number of tests
    - System resources
    - Test execution time
    """
    
    def __init__(self, resource_allocation: ResourceAllocation):
        """Initialize adaptive strategy."""
        super().__init__(resource_allocation)
        self.sequential = SequentialStrategy(resource_allocation)
        self.parallel = ParallelStrategy(resource_allocation)
        self.batched = BatchedParallelStrategy(resource_allocation)
    
    def execute(
        self,
        tests: List[str],
        executor_func: Callable[[str], TestExecutionResult],
        timeout: int = 300
    ) -> List[TestExecutionResult]:
        """Execute tests using adaptive strategy."""
        test_count = len(tests)
        
        # Choose strategy based on test count
        if test_count == 1:
            # Single test - sequential
            return self.sequential.execute(tests, executor_func, timeout)
        elif test_count <= 10:
            # Small suite - sequential (lower overhead)
            return self.sequential.execute(tests, executor_func, timeout)
        elif test_count <= 50:
            # Medium suite - parallel
            return self.parallel.execute(tests, executor_func, timeout)
        else:
            # Large suite - batched parallel
            return self.batched.execute(tests, executor_func, timeout)


class FailFastStrategy(ExecutionStrategy):
    """
    Fail-fast execution strategy.
    
    Stops execution on first failure.
    """
    
    def execute(
        self,
        tests: List[str],
        executor_func: Callable[[str], TestExecutionResult],
        timeout: int = 300
    ) -> List[TestExecutionResult]:
        """Execute tests with fail-fast."""
        from .models import ExecutionStatus
        
        results = []
        
        for test in tests:
            try:
                result = executor_func(test)
                results.append(result)
                
                # Stop on first failure
                if result.status in [ExecutionStatus.FAILED, ExecutionStatus.ERROR]:
                    print(f"\nFail-fast: Stopping execution after {test} failed")
                    break
            except Exception as e:
                from datetime import datetime
                
                result = TestExecutionResult(
                    test_id=test,
                    name=test,
                    status=ExecutionStatus.ERROR,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(e)
                )
                results.append(result)
                break
        
        return results


class RetryStrategy:
    """
    Retry strategy for flaky tests.
    
    Automatically retries failed tests with configurable policy.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: int = 1,
        exponential_backoff: bool = False
    ):
        """
        Initialize retry strategy.
        
        Args:
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            exponential_backoff: Use exponential backoff for delays
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
    
    def execute_with_retry(
        self,
        test: str,
        executor_func: Callable[[str], TestExecutionResult]
    ) -> TestExecutionResult:
        """
        Execute test with retry logic.
        
        Args:
            test: Test identifier
            executor_func: Function to execute test
            
        Returns:
            Test result (last attempt)
        """
        from .models import ExecutionStatus
        
        last_result = None
        
        for attempt in range(self.max_retries + 1):
            result = executor_func(test)
            last_result = result
            
            # Success - no retry needed
            if result.status == ExecutionStatus.PASSED:
                if attempt > 0:
                    result.is_flaky = True
                    result.retry_count = attempt
                return result
            
            # Failed - retry if attempts remaining
            if attempt < self.max_retries:
                delay = self.retry_delay
                if self.exponential_backoff:
                    delay = self.retry_delay * (2 ** attempt)
                
                print(f"  Retrying {test} after {delay}s (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(delay)
        
        # All retries failed
        if last_result:
            last_result.retry_count = self.max_retries
        
        return last_result


def get_strategy(
    strategy_type: StrategyType,
    resource_allocation: ResourceAllocation
) -> ExecutionStrategy:
    """
    Get execution strategy instance.
    
    Args:
        strategy_type: Type of strategy
        resource_allocation: Resource allocation config
        
    Returns:
        Strategy instance
    """
    if strategy_type == StrategyType.SEQUENTIAL:
        return SequentialStrategy(resource_allocation)
    elif strategy_type == StrategyType.PARALLEL:
        return ParallelStrategy(resource_allocation)
    elif strategy_type == StrategyType.ADAPTIVE:
        return AdaptiveStrategy(resource_allocation)
    else:
        raise ValueError(f"Unknown strategy: {strategy_type}")
