# Test Execution Engine

Unified test execution interface for running tests across multiple frameworks with support for parallel execution, retry policies, resource management, and execution strategies.

## Overview

The Test Execution Engine provides a framework-agnostic way to execute tests from various testing frameworks (pytest, Robot Framework, Cypress, Playwright, etc.) through a unified API. It handles:

- **Test Discovery**: Automatic test discovery or explicit test selection
- **Execution Strategies**: Sequential, parallel, batched, and adaptive execution
- **Resource Management**: CPU/memory allocation, worker pools, batch sizing
- **Retry Policies**: Configurable retry for failed tests with flaky test detection
- **Execution Hooks**: Pre/post execution hooks for custom workflows
- **Error Handling**: Comprehensive error capture and reporting

## Architecture

```
┌─────────────────────┐
│  ExecutionRequest   │  ← Define what to run
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   TestExecutor      │  ← Core orchestrator
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
┌────▼────┐ ┌───▼──────┐
│Registry │ │Strategy  │  ← Adapter lookup & Execution mode
└────┬────┘ └───┬──────┘
     │          │
┌────▼──────────▼─────┐
│  Framework Adapter  │  ← pytest, robot, cypress, etc.
└─────────────────────┘
```

## Quick Start

### Basic Usage

```python
from core.execution import (
    TestExecutor,
    TestExecutionRequest,
    ExecutionStrategy,
    ExecutionStatus
)

# Create execution request
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    strategy=ExecutionStrategy.PARALLEL,
    max_workers=4
)

# Execute tests
executor = TestExecutor()
summary = executor.execute(request)

# Check results
print(f"Total: {summary.total_tests}")
print(f"Passed: {summary.passed}")
print(f"Failed: {summary.failed}")
print(f"Success Rate: {summary.success_rate}%")
```

### Run Specific Tests

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    tests=[
        "tests/test_login.py::test_successful_login",
        "tests/test_logout.py::test_logout"
    ]
)

summary = executor.execute(request)
```

### Run with Tags/Filters

```python
request = TestExecutionRequest(
    framework="robot",
    project_root="/path/to/project",
    tags=["smoke", "critical"]
)

summary = executor.execute(request)
```

### Adaptive Strategy (Recommended)

The adaptive strategy automatically selects the best execution mode based on test count:

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    strategy=ExecutionStrategy.ADAPTIVE  # Auto-selects sequential/parallel/batched
)

summary = executor.execute(request)
print(f"Used strategy: {summary.strategy_used}")
```

**Adaptive Strategy Rules**:
- 1 test → Sequential
- 2-10 tests → Sequential (low overhead)
- 11-50 tests → Parallel
- 51+ tests → Batched Parallel

### Retry Failed Tests

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    retry_failed=2  # Retry failed tests up to 2 times
)

summary = executor.execute(request)

# Check for flaky tests
for result in summary.results:
    if result.is_flaky:
        print(f"Flaky test detected: {result.name}")
```

## Execution Strategies

### Sequential

Runs tests one at a time. Best for:
- Small test suites (< 10 tests)
- Tests with shared resources
- Debugging

```python
strategy=ExecutionStrategy.SEQUENTIAL
```

### Parallel

Runs tests concurrently using thread pools. Best for:
- Medium test suites (10-50 tests)
- I/O-bound tests
- Independent tests

```python
strategy=ExecutionStrategy.PARALLEL,
max_workers=4  # Number of parallel workers
```

### Adaptive

Automatically selects the best strategy. **Recommended for most use cases.**

```python
strategy=ExecutionStrategy.ADAPTIVE
```

## Execution Pipeline with Hooks

Add custom logic before/after test execution:

```python
from core.execution import ExecutionPipeline

pipeline = ExecutionPipeline()

# Pre-execution hook
def setup_environment(request):
    print(f"Setting up {request.framework} environment...")
    # Database setup, service initialization, etc.

# Post-execution hook
def cleanup_and_report(summary):
    print(f"Tests completed: {summary.success_rate}% success")
    # Send notifications, cleanup resources, etc.

pipeline.add_pre_execution_hook(setup_environment)
pipeline.add_post_execution_hook(cleanup_and_report)

# Execute with hooks
summary = pipeline.execute(request)
```

## Resource Allocation

Control execution resources:

```python
from core.execution import ResourceAllocation

# Auto-detect resources
allocation = ResourceAllocation.auto_detect()

# Or specify manually
allocation = ResourceAllocation(
    max_workers=8,
    max_memory_mb=2048,
    queue_size=100,
    batch_size=10
)

executor = TestExecutor(resource_allocation=allocation)
```

## Execution Context

Access environment information:

```python
from core.execution import ExecutionContext

context = ExecutionContext.detect()

print(f"Platform: {context.platform}")
print(f"Python: {context.python_version}")
print(f"CI: {context.is_ci}")
if context.is_ci:
    print(f"CI Provider: {context.ci_provider}")
    print(f"Branch: {context.branch}")
```

## Adapter Registry

The adapter registry manages framework adapters:

```python
from core.execution import list_adapters, get_adapter

# List all available frameworks
frameworks = list_adapters()
print(f"Available: {frameworks}")

# Get specific adapter
adapter = get_adapter("pytest", "/path/to/project")
```

### Registering Custom Adapters

```python
from core.execution import register_adapter
from adapters.common.base import BaseAdapter

class MyCustomAdapter(BaseAdapter):
    def discover_tests(self):
        # Implementation
        pass
    
    def run_tests(self, tests):
        # Implementation
        pass

# Register
register_adapter("my-framework", MyCustomAdapter)
```

## Error Handling

```python
summary = executor.execute(request)

if summary.status == ExecutionStatus.ERROR:
    print("Execution failed:")
    for error in summary.execution_errors:
        print(f"  - {error}")

if summary.status == ExecutionStatus.FAILED:
    print(f"{summary.failed} test(s) failed")
    for result in summary.results:
        if result.status == ExecutionStatus.FAILED:
            print(f"  {result.name}: {result.error_message}")
```

## Execution Results

Each test execution returns detailed results:

```python
for result in summary.results:
    print(f"Test: {result.name}")
    print(f"  Status: {result.status}")
    print(f"  Duration: {result.duration_ms}ms")
    
    if result.error_message:
        print(f"  Error: {result.error_message}")
    
    if result.retry_count > 0:
        print(f"  Retries: {result.retry_count}")
    
    if result.is_flaky:
        print(f"  ⚠️  Flaky test detected")
```

## Framework-Specific Options

Pass options to framework adapters:

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    framework_options={
        "verbose": True,
        "capture": "no",
        "markers": "not slow"
    }
)
```

## Environment Variables

Set environment variables for test execution:

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    environment={
        "TEST_ENV": "staging",
        "API_URL": "https://staging.example.com"
    }
)
```

## Coverage Collection

Enable coverage collection:

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    collect_coverage=True
)

summary = executor.execute(request)

# Access coverage data
for result in summary.results:
    if result.coverage_data:
        print(f"Coverage for {result.name}: {result.coverage_data}")
```

## Timeouts

Set per-test timeout:

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    timeout=60  # 60 seconds per test
)
```

## Report Generation

Configure report output:

```python
request = TestExecutionRequest(
    framework="pytest",
    project_root="/path/to/project",
    generate_report=True,
    report_format="junit"  # json, xml, html, junit
)
```

## CLI Integration

The execution engine integrates with the CLI:

```bash
# Run all tests with adaptive strategy
crossbridge execute --framework pytest --strategy adaptive

# Run specific tests with parallelism
crossbridge execute --framework pytest --tests test_login.py test_logout.py --workers 4

# Run with retry
crossbridge execute --framework robot --retry 2 --tags smoke
```

## API Reference

### TestExecutionRequest

```python
@dataclass
class TestExecutionRequest:
    framework: str
    project_root: str
    tests: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    patterns: Optional[List[str]] = None
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    max_workers: Optional[int] = None
    timeout: int = 300
    retry_failed: int = 0
    framework_options: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    collect_coverage: bool = False
    generate_report: bool = True
    report_format: str = "json"
```

### TestExecutionResult

```python
@dataclass
class TestExecutionResult:
    test_id: str
    name: str
    status: ExecutionStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    retry_count: int = 0
    is_flaky: bool = False
    coverage_data: Optional[Dict] = None
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### ExecutionSummary

```python
@dataclass
class ExecutionSummary:
    status: ExecutionStatus
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    results: List[TestExecutionResult] = field(default_factory=list)
    execution_errors: List[str] = field(default_factory=list)
    strategy_used: Optional[ExecutionStrategy] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100
    
    @property
    def is_successful(self) -> bool:
        """Check if all tests passed."""
        return self.failed == 0 and self.errors == 0
```

### ResourceAllocation

```python
@dataclass
class ResourceAllocation:
    max_workers: int = 4
    cpu_affinity: Optional[List[int]] = None
    max_memory_mb: int = 2048
    queue_size: int = 100
    batch_size: int = 10
    max_retries: int = 3
    
    @classmethod
    def auto_detect(cls) -> 'ResourceAllocation':
        """Auto-detect optimal resource allocation."""
        import os
        cpu_count = os.cpu_count() or 4
        return cls(
            max_workers=max(1, cpu_count - 1),
            queue_size=cpu_count * 25,
            batch_size=max(1, cpu_count // 2)
        )
```

## Supported Frameworks

The execution engine supports:

- **pytest**: Python unit/integration tests
- **robot**: Robot Framework tests
- **cypress**: Cypress E2E tests
- **playwright**: Playwright tests
- **specflow**: SpecFlow BDD tests (via .NET)

## Best Practices

1. **Use Adaptive Strategy**: Let the engine choose the best execution mode
2. **Set Appropriate Timeouts**: Prevent hanging tests
3. **Enable Retry for Flaky Tests**: Catch intermittent failures
4. **Use Hooks for Setup/Teardown**: Keep test code clean
5. **Monitor Resource Usage**: Adjust `max_workers` based on system load
6. **Collect Coverage in CI**: Enable coverage in CI pipelines
7. **Generate Reports**: Use structured reports for integration with other tools

## Examples

### Example 1: CI/CD Pipeline

```python
from core.execution import TestExecutor, TestExecutionRequest, ExecutionStrategy

def run_ci_tests():
    request = TestExecutionRequest(
        framework="pytest",
        project_root="/app",
        strategy=ExecutionStrategy.ADAPTIVE,
        retry_failed=1,  # Retry once in CI
        collect_coverage=True,
        generate_report=True,
        report_format="junit"
    )
    
    executor = TestExecutor()
    summary = executor.execute(request)
    
    # Exit with non-zero code if tests failed
    if not summary.is_successful:
        sys.exit(1)
    
    return summary
```

### Example 2: Local Development

```python
def run_local_tests(test_pattern):
    request = TestExecutionRequest(
        framework="pytest",
        project_root=".",
        patterns=[test_pattern],
        strategy=ExecutionStrategy.SEQUENTIAL,  # Easier debugging
        retry_failed=0  # No retry for fast feedback
    )
    
    executor = TestExecutor()
    return executor.execute(request)

# Run tests matching pattern
summary = run_local_tests("test_*_integration.py")
```

### Example 3: Smoke Tests

```python
def run_smoke_tests():
    request = TestExecutionRequest(
        framework="robot",
        project_root="/tests",
        tags=["smoke"],
        strategy=ExecutionStrategy.PARALLEL,
        max_workers=8,
        timeout=30  # Quick tests
    )
    
    executor = TestExecutor()
    summary = executor.execute(request)
    
    # Send notification on failure
    if not summary.is_successful:
        send_alert(f"Smoke tests failed: {summary.failed}/{summary.total_tests}")
    
    return summary
```

## Troubleshooting

### Tests Not Discovered

- Check `project_root` is correct
- Verify framework adapter is registered
- Check file patterns match test files

### Parallel Execution Issues

- Reduce `max_workers`
- Check for shared resources between tests
- Use sequential strategy for debugging

### High Memory Usage

- Reduce `batch_size`
- Reduce `max_workers`
- Set `max_memory_mb` limit

### Flaky Tests

- Enable retry: `retry_failed=2`
- Check for timing issues
- Review tests marked as `is_flaky`

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines on extending the execution engine.
