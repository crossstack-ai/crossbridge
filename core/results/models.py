"""
Data models for result collection and aggregation.

Provides framework-agnostic models for unified result storage,
comparison, and trend analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from enum import Enum


class ResultSource(str, Enum):
    """Source of test result data."""
    EXECUTION = "execution"        # Test execution engine
    COVERAGE = "coverage"          # Coverage collector
    FLAKY_DETECTION = "flaky"      # Flaky detection
    IMPACT_ANALYSIS = "impact"     # Impact analysis
    CUSTOM = "custom"              # Custom source


class TestStatus(str, Enum):
    """Normalized test status across all frameworks."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FLAKY = "flaky"


class TrendDirection(str, Enum):
    """Direction of trend."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


@dataclass
class UnifiedTestResult:
    """
    Unified test result normalized across all frameworks.
    
    This combines data from multiple sources into a single
    comprehensive test result record.
    """
    
    # Core identification
    test_id: str                           # Stable test identifier
    test_name: str                         # Human-readable name
    framework: str                         # Source framework
    
    # Execution details
    status: TestStatus                     # Normalized status
    duration_ms: float                     # Execution duration
    executed_at: datetime                  # Execution timestamp
    
    # Execution metadata
    run_id: Optional[str] = None          # Execution run identifier
    build_id: Optional[str] = None        # CI build ID
    environment: str = "unknown"           # Execution environment
    git_commit: Optional[str] = None      # Git SHA
    
    # Test classification
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    file_path: Optional[str] = None
    
    # Error details
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Coverage data (if available)
    covered_classes: Set[str] = field(default_factory=set)
    covered_methods: Set[str] = field(default_factory=set)
    coverage_percentage: Optional[float] = None
    
    # Flaky detection data (if available)
    is_flaky: bool = False
    flaky_probability: Optional[float] = None
    retry_count: int = 0
    historical_stability: Optional[float] = None
    
    # Impact data (if available)
    impacted_by_changes: bool = False
    change_risk_score: Optional[float] = None
    
    # Data sources
    data_sources: Set[ResultSource] = field(default_factory=set)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedResults:
    """
    Aggregated results from multiple test executions.
    
    Combines results from multiple sources and provides
    unified view with statistics.
    """
    
    # Identification
    aggregation_id: str                    # Unique aggregation ID
    created_at: datetime                   # When aggregation was created
    
    # Time range
    start_time: Optional[datetime] = None  # Earliest result
    end_time: Optional[datetime] = None    # Latest result
    
    # Results
    results: List[UnifiedTestResult] = field(default_factory=list)
    
    # Statistics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    flaky_tests: int = 0
    
    # Timing statistics
    total_duration_ms: float = 0
    avg_duration_ms: float = 0
    median_duration_ms: float = 0
    
    # Coverage statistics (if available)
    avg_coverage: Optional[float] = None
    total_classes_covered: int = 0
    total_methods_covered: int = 0
    
    # Frameworks included
    frameworks: Set[str] = field(default_factory=set)
    environments: Set[str] = field(default_factory=set)
    
    # Data sources
    sources: Set[ResultSource] = field(default_factory=set)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100.0
    
    @property
    def flaky_rate(self) -> float:
        """Calculate flaky test rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.flaky_tests / self.total_tests) * 100.0
    
    def get_results_by_framework(self, framework: str) -> List[UnifiedTestResult]:
        """Get results for specific framework."""
        return [r for r in self.results if r.framework == framework]
    
    def get_results_by_status(self, status: TestStatus) -> List[UnifiedTestResult]:
        """Get results with specific status."""
        return [r for r in self.results if r.status == status]


@dataclass
class RunComparison:
    """
    Comparison between two test runs.
    
    Identifies new, fixed, broken, and flaky tests between runs.
    """
    
    # Identification
    comparison_id: str                     # Unique comparison ID
    run1_id: str                           # First run identifier
    run2_id: str                           # Second run identifier
    compared_at: datetime                  # When comparison was made
    
    # Test changes
    new_tests: List[str] = field(default_factory=list)      # Tests in run2 but not run1
    removed_tests: List[str] = field(default_factory=list)  # Tests in run1 but not run2
    
    # Status changes
    newly_passing: List[str] = field(default_factory=list)  # Failed -> Passed
    newly_failing: List[str] = field(default_factory=list)  # Passed -> Failed
    still_passing: List[str] = field(default_factory=list)  # Passed -> Passed
    still_failing: List[str] = field(default_factory=list)  # Failed -> Failed
    
    # Flaky detection
    newly_flaky: List[str] = field(default_factory=list)    # Became flaky in run2
    no_longer_flaky: List[str] = field(default_factory=list) # Fixed flakiness
    
    # Performance changes
    significantly_slower: List[str] = field(default_factory=list)  # >50% slower
    significantly_faster: List[str] = field(default_factory=list)  # >50% faster
    
    # Statistics
    improvement_count: int = 0
    regression_count: int = 0
    
    # Success rate delta
    run1_success_rate: float = 0.0
    run2_success_rate: float = 0.0
    success_rate_delta: float = 0.0
    
    # Duration delta
    run1_total_duration_ms: float = 0.0
    run2_total_duration_ms: float = 0.0
    duration_delta_percent: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_regressions(self) -> bool:
        """Check if there are any regressions."""
        return len(self.newly_failing) > 0 or self.success_rate_delta < -5.0
    
    @property
    def has_improvements(self) -> bool:
        """Check if there are improvements."""
        return len(self.newly_passing) > 0 or self.success_rate_delta > 5.0


@dataclass
class TrendMetrics:
    """
    Trend metrics over time.
    
    Tracks how metrics change over multiple runs.
    """
    
    # Identification
    metric_name: str                       # Name of metric
    metric_type: str                       # Type (success_rate, duration, etc.)
    
    # Time range
    start_date: datetime                   # First data point
    end_date: datetime                     # Last data point
    data_points: int                       # Number of data points
    
    # Values
    values: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    
    # Statistics
    current_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    avg_value: float = 0.0
    median_value: float = 0.0
    std_deviation: float = 0.0
    
    # Trend analysis
    trend_direction: TrendDirection = TrendDirection.STABLE
    trend_strength: float = 0.0            # 0-1, how strong the trend is
    volatility: float = 0.0                # Coefficient of variation
    
    # Change detection
    significant_change: bool = False       # Statistical significance
    change_percentage: float = 0.0         # % change from start to end
    
    # Forecasting (if available)
    predicted_next_value: Optional[float] = None
    confidence_interval_low: Optional[float] = None
    confidence_interval_high: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StatisticalMetrics:
    """
    Statistical analysis of test results.
    
    Provides advanced statistical insights into test behavior.
    """
    
    # Identification
    test_id: Optional[str] = None          # For per-test metrics (None = suite-wide)
    analysis_date: datetime = field(default_factory=datetime.now)
    sample_size: int = 0                   # Number of executions analyzed
    
    # Success metrics
    success_rate: float = 0.0
    success_rate_ci_low: float = 0.0       # 95% confidence interval
    success_rate_ci_high: float = 0.0
    
    # Duration metrics
    avg_duration_ms: float = 0.0
    duration_p50: float = 0.0              # Median
    duration_p90: float = 0.0              # 90th percentile
    duration_p99: float = 0.0              # 99th percentile
    duration_std: float = 0.0              # Standard deviation
    
    # Stability metrics
    stability_score: float = 0.0           # 0-1, higher = more stable
    flaky_probability: float = 0.0         # 0-1, probability test is flaky
    consecutive_passes: int = 0
    consecutive_failures: int = 0
    
    # Pattern detection
    has_time_dependency: bool = False      # Time-based flakiness
    has_order_dependency: bool = False     # Test order dependency
    has_load_dependency: bool = False      # System load dependency
    
    # Reliability metrics
    mean_time_between_failures: Optional[float] = None  # Average time between failures
    failure_rate: float = 0.0              # Failures per execution
    
    # Quality indicators
    quality_score: float = 0.0             # 0-100, overall quality
    reliability_grade: str = "unknown"     # A, B, C, D, F
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
