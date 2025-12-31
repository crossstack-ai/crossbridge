"""
Data models for test results across all frameworks.

Provides unified data structures for collecting and storing test results
from pytest, JUnit, TestNG, Robot Framework, Cypress, Playwright, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pathlib import Path


class TestStatus(Enum):
    """
    Unified test status across all frameworks.
    
    Maps various framework-specific statuses to common statuses.
    """
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    XFAIL = "xfail"           # Expected failure (pytest)
    XPASS = "xpass"           # Unexpected pass (pytest)
    FLAKY = "flaky"           # Flaky test detected
    TIMEOUT = "timeout"        # Test timed out
    BLOCKED = "blocked"        # Test blocked/cannot run
    UNKNOWN = "unknown"        # Unknown status


class FrameworkType(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    JUNIT4 = "junit4"
    JUNIT5 = "junit5"
    TESTNG = "testng"
    ROBOT = "robot"
    CYPRESS = "cypress"
    PLAYWRIGHT = "playwright"
    REST_ASSURED = "restassured"
    SELENIUM = "selenium"
    UNKNOWN = "unknown"


@dataclass
class ResultMetadata:
    """
    Metadata about test execution environment and configuration.
    """
    framework: FrameworkType
    framework_version: Optional[str] = None
    python_version: Optional[str] = None
    java_version: Optional[str] = None
    os_platform: Optional[str] = None
    hostname: Optional[str] = None
    ci_build_number: Optional[str] = None
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """
    Unified test result from any framework.
    
    Normalized representation of a single test execution.
    """
    # Core identification
    test_id: str                          # Unique test identifier
    test_name: str                        # Test name/title
    test_file: Optional[Path] = None      # Source file path
    test_class: Optional[str] = None      # Test class/suite name
    test_method: Optional[str] = None     # Test method name
    
    # Execution results
    status: TestStatus = TestStatus.UNKNOWN
    duration: float = 0.0                 # Duration in seconds
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    stacktrace: Optional[str] = None
    
    # Test details
    description: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    markers: Set[str] = field(default_factory=set)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Flaky detection
    is_flaky: bool = False
    flaky_runs: List[TestStatus] = field(default_factory=list)
    pass_rate: Optional[float] = None
    
    # Coverage
    coverage_percentage: Optional[float] = None
    covered_lines: Optional[int] = None
    total_lines: Optional[int] = None
    
    # Framework-specific data
    framework_data: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.test_id)
    
    def __eq__(self, other):
        if not isinstance(other, TestResult):
            return False
        return self.test_id == other.test_id


@dataclass
class TestRunResult:
    """
    Complete results from a test run.
    
    Aggregates all test results from a single execution.
    """
    run_id: str                           # Unique run identifier
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0                 # Total duration in seconds
    
    # Test results
    tests: List[TestResult] = field(default_factory=list)
    
    # Summary statistics
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    flaky: int = 0
    
    # Coverage summary
    overall_coverage: Optional[float] = None
    coverage_by_file: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    metadata: Optional[ResultMetadata] = None
    
    # Exit code
    exit_code: int = 0
    
    def __post_init__(self):
        """Calculate summary statistics."""
        if self.tests:
            self.total_tests = len(self.tests)
            self.passed = sum(1 for t in self.tests if t.status == TestStatus.PASSED)
            self.failed = sum(1 for t in self.tests if t.status == TestStatus.FAILED)
            self.skipped = sum(1 for t in self.tests if t.status == TestStatus.SKIPPED)
            self.errors = sum(1 for t in self.tests if t.status == TestStatus.ERROR)
            self.flaky = sum(1 for t in self.tests if t.is_flaky)
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100
    
    @property
    def is_successful(self) -> bool:
        """Check if run was successful (no failures or errors)."""
        return self.failed == 0 and self.errors == 0


@dataclass
class AggregatedResults:
    """
    Aggregated results across multiple test runs.
    
    Provides unified view of results from multiple runs.
    """
    runs: List[TestRunResult] = field(default_factory=list)
    
    # Aggregated statistics
    total_runs: int = 0
    total_tests: int = 0
    unique_tests: int = 0
    
    # Overall statistics
    overall_pass_rate: float = 0.0
    overall_coverage: Optional[float] = None
    
    # Test stability
    stable_tests: Set[str] = field(default_factory=set)
    flaky_tests: Set[str] = field(default_factory=set)
    failing_tests: Set[str] = field(default_factory=set)
    
    # Time range
    earliest_run: Optional[datetime] = None
    latest_run: Optional[datetime] = None
    
    def __post_init__(self):
        """Calculate aggregated statistics."""
        if not self.runs:
            return
        
        self.total_runs = len(self.runs)
        self.total_tests = sum(run.total_tests for run in self.runs)
        
        # Collect unique tests
        unique = set()
        for run in self.runs:
            unique.update(t.test_id for t in run.tests)
        self.unique_tests = len(unique)
        
        # Calculate overall pass rate
        total_passed = sum(run.passed for run in self.runs)
        if self.total_tests > 0:
            self.overall_pass_rate = (total_passed / self.total_tests) * 100
        
        # Calculate overall coverage
        coverages = [run.overall_coverage for run in self.runs if run.overall_coverage]
        if coverages:
            self.overall_coverage = sum(coverages) / len(coverages)
        
        # Find time range
        self.earliest_run = min(run.start_time for run in self.runs)
        latest_ends = [run.end_time for run in self.runs if run.end_time]
        if latest_ends:
            self.latest_run = max(latest_ends)


@dataclass
class ComparisonResult:
    """
    Results from comparing two test runs.
    """
    run1_id: str
    run2_id: str
    comparison_time: datetime = field(default_factory=datetime.now)
    
    # New results
    new_tests: List[TestResult] = field(default_factory=list)
    removed_tests: List[str] = field(default_factory=list)
    
    # Status changes
    newly_passing: List[TestResult] = field(default_factory=list)
    newly_failing: List[TestResult] = field(default_factory=list)
    newly_flaky: List[TestResult] = field(default_factory=list)
    
    # Performance changes
    faster_tests: List[tuple] = field(default_factory=list)  # (test_id, old_duration, new_duration)
    slower_tests: List[tuple] = field(default_factory=list)
    
    # Coverage changes
    coverage_improved: bool = False
    coverage_degraded: bool = False
    coverage_delta: float = 0.0
    
    # Summary
    total_changes: int = 0
    improvements: int = 0
    regressions: int = 0
    
    def __post_init__(self):
        """Calculate summary statistics."""
        self.total_changes = (
            len(self.new_tests) + 
            len(self.removed_tests) +
            len(self.newly_passing) +
            len(self.newly_failing) +
            len(self.newly_flaky)
        )
        self.improvements = len(self.newly_passing)
        self.regressions = len(self.newly_failing) + len(self.newly_flaky)


@dataclass
class TrendPoint:
    """Single data point in a trend."""
    timestamp: datetime
    value: float
    run_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendData:
    """
    Trend data for a specific metric over time.
    """
    metric_name: str
    data_points: List[TrendPoint] = field(default_factory=list)
    
    # Statistics
    average: float = 0.0
    minimum: float = 0.0
    maximum: float = 0.0
    std_deviation: float = 0.0
    
    # Trend analysis
    trend_direction: str = "stable"  # "improving", "degrading", "stable"
    trend_strength: float = 0.0      # 0.0 to 1.0
    
    def __post_init__(self):
        """Calculate statistics."""
        if not self.data_points:
            return
        
        values = [p.value for p in self.data_points]
        self.average = sum(values) / len(values)
        self.minimum = min(values)
        self.maximum = max(values)
        
        # Calculate standard deviation
        if len(values) > 1:
            variance = sum((x - self.average) ** 2 for x in values) / len(values)
            self.std_deviation = variance ** 0.5
    
    @property
    def is_improving(self) -> bool:
        """Check if trend is improving."""
        return self.trend_direction == "improving"
    
    @property
    def is_degrading(self) -> bool:
        """Check if trend is degrading."""
        return self.trend_direction == "degrading"
