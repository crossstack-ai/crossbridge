"""
Framework-agnostic models for flaky test detection.

These models normalize execution data from all test frameworks
(JUnit, Cucumber, Pytest, Robot, etc.) into a common format
suitable for ML-based flaky detection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TestStatus(str, Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ABORTED = "aborted"
    ERROR = "error"


class TestFramework(str, Enum):
    """Supported test frameworks."""
    JUNIT = "junit"
    TESTNG = "testng"
    PYTEST = "pytest"
    ROBOT = "robot"
    CUCUMBER = "cucumber"
    SELENIUM_JAVA = "selenium_java"
    SELENIUM_BDD = "selenium_bdd"
    PLAYWRIGHT = "playwright"
    CYPRESS = "cypress"


@dataclass
class TestExecutionRecord:
    """
    Framework-agnostic test execution record.
    
    This normalizes execution data from all frameworks into a common format
    for flaky detection analysis.
    """
    
    # Required fields
    test_id: str                    # Stable identifier (e.g., class.method, feature:scenario)
    framework: TestFramework        # Source framework
    status: TestStatus              # Execution outcome
    duration_ms: float              # Execution duration in milliseconds
    executed_at: datetime           # When the test was executed
    
    # Optional contextual data
    error_signature: Optional[str] = None   # Normalized error message/type
    error_full: Optional[str] = None        # Full error details
    retry_count: int = 0                    # Number of retries attempted
    git_commit: Optional[str] = None        # Git SHA if available
    environment: str = "unknown"            # local | ci | staging | prod
    build_id: Optional[str] = None          # CI build identifier
    
    # Test metadata
    test_name: Optional[str] = None         # Human-readable name
    test_file: Optional[str] = None         # Source file path
    test_line: Optional[int] = None         # Line number
    tags: List[str] = field(default_factory=list)  # Test tags/labels
    
    # Framework-specific data (optional JSON blob)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize data."""
        if self.duration_ms < 0:
            self.duration_ms = 0.0
        
        if self.retry_count < 0:
            self.retry_count = 0
        
        # Ensure framework and status are enums
        if isinstance(self.framework, str):
            self.framework = TestFramework(self.framework)
        
        if isinstance(self.status, str):
            self.status = TestStatus(self.status)
    
    @property
    def is_failed(self) -> bool:
        """Check if test failed."""
        return self.status in (TestStatus.FAILED, TestStatus.ERROR)
    
    @property
    def is_passed(self) -> bool:
        """Check if test passed."""
        return self.status == TestStatus.PASSED
    
    @property
    def is_skipped(self) -> bool:
        """Check if test was skipped."""
        return self.status == TestStatus.SKIPPED
    
    def get_error_type(self) -> Optional[str]:
        """Extract error type from error signature."""
        if not self.error_signature:
            return None
        
        # Common patterns: "AssertionError: message" or "TimeoutException"
        parts = self.error_signature.split(":")
        return parts[0].strip() if parts else None


@dataclass
class FlakyFeatureVector:
    """
    Numerical features extracted from test execution history.
    
    These features are used by the Isolation Forest model to detect
    flaky tests based on their execution patterns.
    """
    
    test_id: str
    
    # Statistical features
    failure_rate: float                     # failures / total_runs
    pass_fail_switch_rate: float           # status changes / (total_runs - 1)
    duration_variance: float                # variance of execution durations
    mean_duration_ms: float                 # average execution duration
    duration_cv: float                      # coefficient of variation (std/mean)
    
    # Retry features
    retry_success_rate: float               # successful retries / total_retries
    avg_retry_count: float                  # average retries per execution
    
    # Error diversity features
    unique_error_count: int                 # number of distinct error types
    error_diversity_ratio: float            # unique errors / total failures
    
    # Temporal features
    same_commit_failure_rate: float         # failures on same commit / total on commit
    recent_failure_rate: float              # failures in last N runs / N
    
    # Supporting metadata
    total_executions: int                   # total number of executions
    window_size: int                        # size of analysis window
    last_executed: datetime                 # most recent execution
    
    def __post_init__(self):
        """Validate feature values."""
        # Clamp rates to [0, 1]
        self.failure_rate = max(0.0, min(1.0, self.failure_rate))
        self.pass_fail_switch_rate = max(0.0, min(1.0, self.pass_fail_switch_rate))
        self.retry_success_rate = max(0.0, min(1.0, self.retry_success_rate))
        self.same_commit_failure_rate = max(0.0, min(1.0, self.same_commit_failure_rate))
        self.recent_failure_rate = max(0.0, min(1.0, self.recent_failure_rate))
        self.error_diversity_ratio = max(0.0, min(1.0, self.error_diversity_ratio))
        
        # Ensure non-negative values
        self.duration_variance = max(0.0, self.duration_variance)
        self.mean_duration_ms = max(0.0, self.mean_duration_ms)
        self.duration_cv = max(0.0, self.duration_cv)
        self.unique_error_count = max(0, self.unique_error_count)
        self.total_executions = max(0, self.total_executions)
    
    def to_array(self) -> List[float]:
        """Convert to numerical array for ML model."""
        return [
            self.failure_rate,
            self.pass_fail_switch_rate,
            self.duration_variance,
            self.duration_cv,
            self.retry_success_rate,
            self.avg_retry_count,
            float(self.unique_error_count),
            self.error_diversity_ratio,
            self.same_commit_failure_rate,
            self.recent_failure_rate,
        ]
    
    @property
    def confidence(self) -> float:
        """
        Calculate confidence in flaky detection based on data availability.
        
        Confidence increases with more executions, capped at 1.0.
        Minimum 15 executions for reliable detection.
        """
        return min(1.0, self.total_executions / 30.0)
    
    @property
    def is_reliable(self) -> bool:
        """Check if we have enough data for reliable classification."""
        return self.total_executions >= 15


@dataclass
class FlakyTestResult:
    """
    Result of flaky test detection for a single test.
    """
    
    test_id: str
    test_name: Optional[str]
    framework: TestFramework
    
    # Flakiness scores
    flaky_score: float              # Isolation Forest anomaly score (lower = more flaky)
    is_flaky: bool                  # Binary classification
    confidence: float               # Confidence in classification (0-1)
    
    # Supporting data
    features: FlakyFeatureVector    # Features used for detection
    detected_at: datetime           # When analysis was performed
    model_version: str              # ML model version
    
    # Classification reasoning
    primary_indicators: List[str] = field(default_factory=list)  # Why it's flaky
    
    @property
    def classification(self) -> str:
        """Get human-readable classification."""
        if not self.features.is_reliable:
            return "insufficient_data"
        elif self.is_flaky and self.confidence >= 0.7:
            return "flaky"
        elif self.is_flaky and self.confidence >= 0.5:
            return "suspected_flaky"
        else:
            return "stable"
    
    @property
    def severity(self) -> str:
        """Estimate severity based on failure rate and confidence."""
        if not self.is_flaky:
            return "none"
        
        if self.confidence < 0.5:
            return "low"
        
        failure_rate = self.features.failure_rate
        
        if failure_rate >= 0.5:
            return "critical"
        elif failure_rate >= 0.3:
            return "high"
        elif failure_rate >= 0.15:
            return "medium"
        else:
            return "low"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "framework": self.framework.value,
            "flaky_score": self.flaky_score,
            "is_flaky": self.is_flaky,
            "confidence": self.confidence,
            "classification": self.classification,
            "severity": self.severity,
            "failure_rate": self.features.failure_rate,
            "switch_rate": self.features.pass_fail_switch_rate,
            "total_executions": self.features.total_executions,
            "primary_indicators": self.primary_indicators,
            "detected_at": self.detected_at.isoformat(),
            "model_version": self.model_version,
        }
