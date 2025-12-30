"""
Step-Level Flakiness Detection for BDD and Keyword-Based Frameworks.

Detects flaky steps/keywords within scenarios/test cases, providing:
- Root cause identification (which step is flaky)
- Repair targeting (fix specific steps, not entire scenarios)
- Better explainability for teams

Supports:
- Cucumber steps
- Robot Framework keywords
- Pytest parametrized steps (optional)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

from .models import TestStatus, TestFramework


# ============================================================================
# Step-Level Models
# ============================================================================

@dataclass
class StepExecutionRecord:
    """
    Records a single step/keyword execution within a test.
    
    This is the atomic unit for step-level flakiness analysis.
    """
    
    # Identifiers
    step_id: str                        # Unique step identifier
    scenario_id: str                    # Parent scenario/test ID
    test_id: str                        # Top-level test ID
    step_text: str                      # Human-readable step text
    step_index: int                     # Position in scenario (0-based)
    
    # Execution details
    status: TestStatus                  # passed, failed, skipped
    duration_ms: float                  # Execution time
    execution_time: datetime            # When it executed
    
    # Error information
    error_signature: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Context
    framework: TestFramework = TestFramework.CUCUMBER
    environment: Optional[str] = None
    git_commit: Optional[str] = None
    
    # Step-specific metadata
    retry_count: int = 0                # How many retries
    is_background: bool = False         # Background step (Cucumber)
    is_hook: bool = False               # Before/After hook
    keyword_type: Optional[str] = None  # Robot: keyword type (setup, teardown, etc.)


@dataclass
class StepFlakyFeatureVector:
    """
    Feature vector for step-level flakiness detection.
    
    Similar to test-level features but focused on step behavior.
    """
    
    # Core flakiness indicators
    step_failure_rate: float            # Failures / total executions
    step_pass_fail_switch_rate: float   # Status change frequency
    step_duration_variance: float       # Execution time variance
    step_duration_cv: float             # Coefficient of variation
    
    # Error patterns
    unique_error_count: int             # Number of distinct errors
    error_diversity_ratio: float        # Unique errors / total failures
    
    # Context-based features
    position_sensitivity: float         # Fails differently based on position
    preceding_step_correlation: float   # Correlation with previous step failures
    
    # Retry behavior
    retry_success_rate: float           # Successful retries / total retries
    avg_retry_count: float              # Average retries per execution
    
    # Metadata
    execution_count: int                # Total executions
    is_reliable: bool = False           # Has enough data (≥10 executions)
    
    def to_array(self) -> List[float]:
        """Convert to numpy-compatible array for ML model."""
        return [
            self.step_failure_rate,
            self.step_pass_fail_switch_rate,
            self.step_duration_variance,
            self.step_duration_cv,
            float(self.unique_error_count),
            self.error_diversity_ratio,
            self.position_sensitivity,
            self.preceding_step_correlation,
            self.retry_success_rate,
            self.avg_retry_count,
        ]


@dataclass
class StepFlakyResult:
    """
    Result of step-level flakiness detection.
    
    Indicates if a specific step is flaky and why.
    """
    
    step_id: str
    step_text: str
    scenario_id: str
    framework: TestFramework
    
    # Flakiness scores
    flaky_score: float              # Isolation Forest anomaly score
    is_flaky: bool                  # Binary classification
    confidence: float               # Confidence in classification (0-1)
    
    # Supporting data
    features: StepFlakyFeatureVector
    detected_at: datetime
    model_version: str
    
    # Reasoning
    primary_indicators: List[str] = field(default_factory=list)
    
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
        if not self.is_flaky or not self.features.is_reliable:
            return "none"
        
        failure_rate = self.features.step_failure_rate
        
        if failure_rate > 0.7 and self.confidence > 0.7:
            return "critical"
        elif failure_rate > 0.5 and self.confidence > 0.7:
            return "high"
        elif failure_rate > 0.3 and self.confidence > 0.5:
            return "medium"
        else:
            return "low"


@dataclass
class ScenarioFlakyAnalysis:
    """
    Aggregated flakiness analysis for a scenario.
    
    Combines step-level results to determine scenario flakiness.
    """
    
    scenario_id: str
    scenario_name: str
    framework: TestFramework
    
    # Scenario-level scores
    scenario_flaky_score: float     # Aggregated from steps
    is_scenario_flaky: bool         # Binary classification
    confidence: float               # Overall confidence
    
    # Step-level details
    total_steps: int
    flaky_steps: List[StepFlakyResult]
    suspected_flaky_steps: List[StepFlakyResult]
    stable_steps: List[StepFlakyResult]
    
    # Root cause
    root_cause_step: Optional[StepFlakyResult] = None  # Most flaky step
    
    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def explanation(self) -> str:
        """Generate human-readable explanation."""
        if not self.is_scenario_flaky:
            return f"Scenario is stable (all {self.total_steps} steps stable)"
        
        if self.root_cause_step:
            return (
                f"Scenario is flaky due to step '{self.root_cause_step.step_text}' "
                f"({self.root_cause_step.severity} severity, "
                f"{self.root_cause_step.features.step_failure_rate:.1%} failure rate)"
            )
        
        return (
            f"Scenario is flaky ({len(self.flaky_steps)} unstable steps out of "
            f"{self.total_steps})"
        )
    
    @property
    def severity(self) -> str:
        """Overall scenario severity (max of step severities)."""
        if not self.is_scenario_flaky:
            return "none"
        
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        
        max_severity = "none"
        for step in self.flaky_steps:
            if severity_order.get(step.severity, 0) > severity_order.get(max_severity, 0):
                max_severity = step.severity
        
        return max_severity


# ============================================================================
# Step Feature Engineering
# ============================================================================

class StepFeatureEngineer:
    """Extract features from step execution history."""
    
    def __init__(self, min_executions_reliable: int = 10):
        """
        Args:
            min_executions_reliable: Minimum executions for reliable classification
        """
        self.min_executions_reliable = min_executions_reliable
    
    def extract_features(
        self,
        step_executions: List[StepExecutionRecord]
    ) -> StepFlakyFeatureVector:
        """
        Extract flakiness features for a single step.
        
        Args:
            step_executions: All executions of this step
            
        Returns:
            Feature vector for ML model
        """
        if not step_executions:
            return self._empty_features()
        
        execution_count = len(step_executions)
        is_reliable = execution_count >= self.min_executions_reliable
        
        # Sort by execution time
        sorted_execs = sorted(step_executions, key=lambda e: e.execution_time)
        
        # Calculate failure rate
        failures = [e for e in sorted_execs if e.status == TestStatus.FAILED]
        failure_count = len(failures)
        failure_rate = failure_count / execution_count if execution_count > 0 else 0.0
        
        # Calculate pass/fail switch rate
        switch_rate = self._calculate_switch_rate(sorted_execs)
        
        # Calculate duration variance
        duration_variance, duration_cv = self._calculate_duration_variance(sorted_execs)
        
        # Calculate error diversity
        unique_errors, error_diversity = self._calculate_error_diversity(failures)
        
        # Calculate position sensitivity
        position_sensitivity = self._calculate_position_sensitivity(sorted_execs)
        
        # Calculate preceding step correlation
        preceding_correlation = self._calculate_preceding_correlation(sorted_execs)
        
        # Calculate retry metrics
        retry_success_rate, avg_retry_count = self._calculate_retry_metrics(sorted_execs)
        
        return StepFlakyFeatureVector(
            step_failure_rate=failure_rate,
            step_pass_fail_switch_rate=switch_rate,
            step_duration_variance=duration_variance,
            step_duration_cv=duration_cv,
            unique_error_count=unique_errors,
            error_diversity_ratio=error_diversity,
            position_sensitivity=position_sensitivity,
            preceding_step_correlation=preceding_correlation,
            retry_success_rate=retry_success_rate,
            avg_retry_count=avg_retry_count,
            execution_count=execution_count,
            is_reliable=is_reliable,
        )
    
    def extract_batch_features(
        self,
        all_executions: Dict[str, List[StepExecutionRecord]]
    ) -> Dict[str, StepFlakyFeatureVector]:
        """
        Extract features for multiple steps in batch.
        
        Args:
            all_executions: Map of step_id -> list of executions
            
        Returns:
            Map of step_id -> feature vector
        """
        return {
            step_id: self.extract_features(executions)
            for step_id, executions in all_executions.items()
        }
    
    def _empty_features(self) -> StepFlakyFeatureVector:
        """Return empty feature vector for no data."""
        return StepFlakyFeatureVector(
            step_failure_rate=0.0,
            step_pass_fail_switch_rate=0.0,
            step_duration_variance=0.0,
            step_duration_cv=0.0,
            unique_error_count=0,
            error_diversity_ratio=0.0,
            position_sensitivity=0.0,
            preceding_step_correlation=0.0,
            retry_success_rate=0.0,
            avg_retry_count=0.0,
            execution_count=0,
            is_reliable=False,
        )
    
    def _calculate_switch_rate(
        self,
        executions: List[StepExecutionRecord]
    ) -> float:
        """Calculate pass/fail switch rate."""
        if len(executions) < 2:
            return 0.0
        
        switches = sum(
            1 for i in range(1, len(executions))
            if executions[i].status != executions[i-1].status
        )
        
        return switches / (len(executions) - 1)
    
    def _calculate_duration_variance(
        self,
        executions: List[StepExecutionRecord]
    ) -> tuple:
        """Calculate duration variance and coefficient of variation."""
        durations = [e.duration_ms for e in executions if e.duration_ms > 0]
        
        if len(durations) < 2:
            return 0.0, 0.0
        
        mean_duration = sum(durations) / len(durations)
        variance = sum((d - mean_duration) ** 2 for d in durations) / len(durations)
        
        # Coefficient of variation (normalized variance)
        cv = (variance ** 0.5) / mean_duration if mean_duration > 0 else 0.0
        
        return variance, cv
    
    def _calculate_error_diversity(self, failures: List[StepExecutionRecord]) -> tuple:
        """Calculate error diversity metrics."""
        if not failures:
            return 0, 0.0
        
        error_signatures = [f.error_signature for f in failures if f.error_signature]
        unique_errors = len(set(error_signatures))
        error_diversity = unique_errors / len(failures) if failures else 0.0
        
        return unique_errors, error_diversity
    
    def _calculate_position_sensitivity(
        self,
        executions: List[StepExecutionRecord]
    ) -> float:
        """
        Calculate position sensitivity.
        
        Does the step fail more often when it's in a different position?
        """
        if len(executions) < 5:
            return 0.0
        
        # Group by position
        position_groups: Dict[int, List[TestStatus]] = {}
        for e in executions:
            if e.step_index not in position_groups:
                position_groups[e.step_index] = []
            position_groups[e.step_index].append(e.status)
        
        # If only one position, no sensitivity
        if len(position_groups) <= 1:
            return 0.0
        
        # Calculate variance in failure rates across positions
        failure_rates = []
        for statuses in position_groups.values():
            fail_count = sum(1 for s in statuses if s == TestStatus.FAILED)
            failure_rates.append(fail_count / len(statuses))
        
        if len(failure_rates) < 2:
            return 0.0
        
        mean_rate = sum(failure_rates) / len(failure_rates)
        variance = sum((r - mean_rate) ** 2 for r in failure_rates) / len(failure_rates)
        
        return variance
    
    def _calculate_preceding_correlation(
        self,
        executions: List[StepExecutionRecord]
    ) -> float:
        """
        Calculate correlation with preceding step failures.
        
        Does this step fail more often after the previous step fails?
        Note: Requires metadata about preceding steps (not implemented yet).
        """
        # TODO: Implement when we have step order metadata
        return 0.0
    
    def _calculate_retry_metrics(
        self,
        executions: List[StepExecutionRecord]
    ) -> tuple:
        """Calculate retry success rate and average retry count."""
        retries = [e for e in executions if e.retry_count > 0]
        
        if not retries:
            return 0.0, 0.0
        
        # Retry success rate: retries that eventually passed
        successful_retries = sum(
            1 for e in retries
            if e.status == TestStatus.PASSED
        )
        retry_success_rate = successful_retries / len(retries) if retries else 0.0
        
        # Average retry count
        avg_retry_count = sum(e.retry_count for e in executions) / len(executions)
        
        return retry_success_rate, avg_retry_count


# ============================================================================
# Scenario Aggregation
# ============================================================================

class ScenarioFlakinessAggregator:
    """
    Aggregate step-level flakiness results to scenario level.
    
    Implements the key logic:
    scenario_flaky_score = max(step_scores) * 0.7 + mean(step_scores) * 0.3
    """
    
    def aggregate(
        self,
        scenario_id: str,
        scenario_name: str,
        step_results: List[StepFlakyResult],
        framework: TestFramework
    ) -> ScenarioFlakyAnalysis:
        """
        Aggregate step results to scenario level.
        
        Args:
            scenario_id: Scenario identifier
            scenario_name: Human-readable name
            step_results: Flakiness results for all steps
            framework: Test framework
            
        Returns:
            Aggregated scenario analysis
        """
        if not step_results:
            return ScenarioFlakyAnalysis(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                framework=framework,
                scenario_flaky_score=0.0,
                is_scenario_flaky=False,
                confidence=0.0,
                total_steps=0,
                flaky_steps=[],
                suspected_flaky_steps=[],
                stable_steps=[],
            )
        
        # Categorize steps
        flaky_steps = [s for s in step_results if s.classification == "flaky"]
        suspected_steps = [s for s in step_results if s.classification == "suspected_flaky"]
        stable_steps = [s for s in step_results if s.classification == "stable"]
        
        # Calculate scenario flaky score
        # Formula: max(step_scores) * 0.7 + mean(step_scores) * 0.3
        step_scores = [s.flaky_score for s in step_results]
        max_score = max(step_scores) if step_scores else 0.0
        mean_score = sum(step_scores) / len(step_scores) if step_scores else 0.0
        
        scenario_score = max_score * 0.7 + mean_score * 0.3
        
        # Determine if scenario is flaky
        # Scenario is flaky if:
        # 1. At least one step is highly flaky (max_score indicates anomaly)
        # 2. OR multiple steps are moderately flaky
        is_scenario_flaky = (
            len(flaky_steps) >= 1 or
            len(suspected_steps) >= 2
        )
        
        # Calculate overall confidence (average of step confidences)
        confidences = [s.confidence for s in step_results if s.features.is_reliable]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Identify root cause (most flaky step)
        root_cause = None
        if flaky_steps:
            root_cause = max(flaky_steps, key=lambda s: s.flaky_score)
        
        return ScenarioFlakyAnalysis(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            framework=framework,
            scenario_flaky_score=scenario_score,
            is_scenario_flaky=is_scenario_flaky,
            confidence=overall_confidence,
            total_steps=len(step_results),
            flaky_steps=flaky_steps,
            suspected_flaky_steps=suspected_steps,
            stable_steps=stable_steps,
            root_cause_step=root_cause,
        )
