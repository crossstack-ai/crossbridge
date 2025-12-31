"""
Execution models for unified test execution engine.

Defines data structures for test execution requests, results, and configuration.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ExecutionStatus(str, Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionStrategy(str, Enum):
    """Test execution strategy."""
    SEQUENTIAL = "sequential"  # Run tests one at a time
    PARALLEL = "parallel"      # Run tests in parallel (thread pool)
    DISTRIBUTED = "distributed"  # Distribute across multiple machines
    ADAPTIVE = "adaptive"      # Automatically choose best strategy


@dataclass
class TestExecutionRequest:
    """Request for test execution."""
    __test__ = False  # Tell pytest not to collect this class
    
    # Framework and project info
    framework: str  # pytest, robot, cypress, playwright, etc.
    project_root: str
    
    # Test selection
    tests: Optional[List[str]] = None  # Specific tests to run (None = all)
    tags: Optional[List[str]] = None   # Tags to filter by
    patterns: Optional[List[str]] = None  # File patterns to match
    
    # Execution configuration
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    max_workers: Optional[int] = None  # Max parallel workers
    timeout: int = 300  # Timeout per test in seconds
    retry_failed: int = 0  # Number of retries for failed tests
    
    # Framework-specific options
    framework_options: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    
    # Reporting options
    collect_coverage: bool = False
    generate_report: bool = True
    report_format: str = "json"  # json, xml, html, junit


@dataclass
class TestExecutionResult:
    """Result of a single test execution."""
    __test__ = False  # Tell pytest not to collect this class
    
    test_id: str  # Unique test identifier
    name: str     # Human-readable test name
    status: ExecutionStatus
    
    # Timing information
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    
    # Result details
    message: str = ""
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Metadata
    framework: str = ""
    file_path: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Retry information
    retry_count: int = 0
    is_flaky: bool = False
    
    # Coverage (if collected)
    coverage_data: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionSummary:
    """Summary of test execution batch."""
    
    # Overall status
    status: ExecutionStatus
    
    # Counts
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration_ms: int = 0
    
    # Execution info
    strategy_used: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    workers_used: int = 1
    
    # Results
    results: List[TestExecutionResult] = field(default_factory=list)
    
    # Errors and warnings
    execution_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_result(self, result: TestExecutionResult):
        """Add a test result and update counts."""
        self.results.append(result)
        self.total_tests += 1
        
        if result.status == ExecutionStatus.PASSED:
            self.passed += 1
        elif result.status == ExecutionStatus.FAILED:
            self.failed += 1
        elif result.status == ExecutionStatus.SKIPPED:
            self.skipped += 1
        elif result.status == ExecutionStatus.ERROR:
            self.errors += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100.0
    
    @property
    def is_successful(self) -> bool:
        """Check if execution was successful (no failures or errors)."""
        return self.failed == 0 and self.errors == 0 and self.total_tests > 0


@dataclass
class ResourceAllocation:
    """Resource allocation configuration for test execution."""
    
    # CPU resources
    max_workers: int = 1
    cpu_affinity: Optional[List[int]] = None
    
    # Memory limits
    max_memory_mb: Optional[int] = None
    
    # Time constraints
    max_execution_time: Optional[int] = None  # seconds
    
    # Queue management
    queue_size: int = 100
    batch_size: int = 10
    
    # Retry policy
    max_retries: int = 0
    retry_delay: int = 0  # seconds
    
    @classmethod
    def auto_detect(cls) -> 'ResourceAllocation':
        """Auto-detect optimal resource allocation based on system."""
        import os
        import multiprocessing
        
        cpu_count = multiprocessing.cpu_count()
        
        # Use 75% of CPUs, leaving some for system
        max_workers = max(1, int(cpu_count * 0.75))
        
        return cls(
            max_workers=max_workers,
            queue_size=max_workers * 10,
            batch_size=max_workers * 2
        )


@dataclass
class ExecutionContext:
    """Context information for test execution."""
    
    # Environment
    platform: str = ""
    python_version: str = ""
    node_version: Optional[str] = None
    java_version: Optional[str] = None
    dotnet_version: Optional[str] = None
    
    # CI/CD info
    is_ci: bool = False
    ci_provider: Optional[str] = None
    build_id: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    
    # Execution metadata
    executor_version: str = ""
    execution_id: str = ""
    
    @classmethod
    def detect(cls) -> 'ExecutionContext':
        """Detect execution context from environment."""
        import sys
        import platform
        import os
        import uuid
        
        # Detect CI environment
        is_ci = any([
            os.getenv('CI'),
            os.getenv('GITHUB_ACTIONS'),
            os.getenv('JENKINS_HOME'),
            os.getenv('GITLAB_CI'),
            os.getenv('CIRCLECI'),
        ])
        
        ci_provider = None
        if os.getenv('GITHUB_ACTIONS'):
            ci_provider = 'github_actions'
        elif os.getenv('JENKINS_HOME'):
            ci_provider = 'jenkins'
        elif os.getenv('GITLAB_CI'):
            ci_provider = 'gitlab'
        elif os.getenv('CIRCLECI'):
            ci_provider = 'circle_ci'
        
        return cls(
            platform=platform.platform(),
            python_version=sys.version.split()[0],
            is_ci=is_ci,
            ci_provider=ci_provider,
            build_id=os.getenv('BUILD_ID') or os.getenv('GITHUB_RUN_ID'),
            branch=os.getenv('BRANCH_NAME') or os.getenv('GITHUB_REF_NAME'),
            commit_sha=os.getenv('GIT_COMMIT') or os.getenv('GITHUB_SHA'),
            execution_id=str(uuid.uuid4())
        )
