"""
Multi-Dimensional Confidence Calibration for Flaky Detection.

Phase-2 confidence goes beyond simple execution count, incorporating:
- Execution volume (how many test runs)
- Time span (over what period)
- Environment diversity (CI, local, different configs)
- Model consistency (stable predictions over time)

This builds trust by never over-claiming certainty.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter


@dataclass
class ConfidenceInputs:
    """
    Raw inputs for confidence calculation.
    
    Collected from execution history and model predictions.
    """
    
    # Execution volume
    total_executions: int               # Total test runs
    
    # Time span
    first_execution: datetime           # Earliest execution
    last_execution: datetime            # Latest execution
    
    # Environment diversity
    unique_environments: int            # Number of unique environments
    total_environment_runs: int         # Total runs (for ratio)
    
    # Model consistency
    prediction_history: List[bool]      # Historical predictions (flaky/stable)
    confidence_history: List[float]     # Historical confidence scores
    
    # Data quality
    has_error_signatures: bool          # Error messages available
    has_duration_data: bool             # Timing data available
    has_git_commits: bool               # Commit tracking available


@dataclass
class ConfidenceWeights:
    """
    Weights for confidence calculation.
    
    Tunable parameters for balancing different confidence factors.
    """
    
    execution_volume_weight: float = 0.35      # Importance of data volume
    time_span_weight: float = 0.25             # Importance of time coverage
    environment_weight: float = 0.20           # Importance of env diversity
    model_consistency_weight: float = 0.20     # Importance of stable predictions
    
    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = (
            self.execution_volume_weight +
            self.time_span_weight +
            self.environment_weight +
            self.model_consistency_weight
        )
        
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class ConfidenceCalibrator:
    """
    Calculate multi-dimensional confidence scores.
    
    Confidence indicates how much we trust the flakiness classification.
    """
    
    def __init__(
        self,
        min_executions_reliable: int = 15,
        min_executions_confident: int = 30,
        min_days_reliable: int = 7,
        min_days_confident: int = 14,
        min_environments: int = 2,
        weights: Optional[ConfidenceWeights] = None
    ):
        """
        Args:
            min_executions_reliable: Minimum for any confidence > 0
            min_executions_confident: Minimum for full confidence from volume
            min_days_reliable: Minimum time span for reliable data
            min_days_confident: Minimum time span for full confidence
            min_environments: Minimum environments for full env confidence
            weights: Custom confidence weights (uses default if None)
        """
        self.min_executions_reliable = min_executions_reliable
        self.min_executions_confident = min_executions_confident
        self.min_days_reliable = min_days_reliable
        self.min_days_confident = min_days_confident
        self.min_environments = min_environments
        self.weights = weights or ConfidenceWeights()
    
    def calculate_confidence(self, inputs: ConfidenceInputs) -> float:
        """
        Calculate overall confidence score (0-1).
        
        Args:
            inputs: Confidence calculation inputs
            
        Returns:
            Confidence score between 0 and 1
        """
        # Calculate individual component scores
        volume_score = self._calculate_execution_volume_score(inputs)
        time_span_score = self._calculate_time_span_score(inputs)
        environment_score = self._calculate_environment_score(inputs)
        consistency_score = self._calculate_model_consistency_score(inputs)
        
        # Weighted combination
        confidence = (
            self.weights.execution_volume_weight * volume_score +
            self.weights.time_span_weight * time_span_score +
            self.weights.environment_weight * environment_score +
            self.weights.model_consistency_weight * consistency_score
        )
        
        # Apply data quality penalty
        quality_multiplier = self._calculate_quality_multiplier(inputs)
        confidence *= quality_multiplier
        
        return min(1.0, max(0.0, confidence))
    
    def _calculate_execution_volume_score(self, inputs: ConfidenceInputs) -> float:
        """
        Calculate confidence from execution volume.
        
        Linear scaling from min_executions_reliable to min_executions_confident.
        """
        if inputs.total_executions < self.min_executions_reliable:
            return 0.0
        
        if inputs.total_executions >= self.min_executions_confident:
            return 1.0
        
        # Linear interpolation
        range_size = self.min_executions_confident - self.min_executions_reliable
        executions_above_min = inputs.total_executions - self.min_executions_reliable
        
        return executions_above_min / range_size
    
    def _calculate_time_span_score(self, inputs: ConfidenceInputs) -> float:
        """
        Calculate confidence from time span.
        
        Longer time span = more confidence (captures different conditions).
        """
        if not inputs.first_execution or not inputs.last_execution:
            return 0.5  # Unknown time span, moderate confidence
        
        time_span = inputs.last_execution - inputs.first_execution
        days = time_span.total_seconds() / (24 * 3600)
        
        if days < self.min_days_reliable:
            # Too short, data might not capture variability
            return days / self.min_days_reliable * 0.5
        
        if days >= self.min_days_confident:
            return 1.0
        
        # Linear interpolation
        range_size = self.min_days_confident - self.min_days_reliable
        days_above_min = days - self.min_days_reliable
        
        return 0.5 + (days_above_min / range_size) * 0.5
    
    def _calculate_environment_score(self, inputs: ConfidenceInputs) -> float:
        """
        Calculate confidence from environment diversity.
        
        More environments = better coverage of failure modes.
        """
        if inputs.total_environment_runs == 0:
            return 0.5  # No environment data, moderate confidence
        
        if inputs.unique_environments == 0:
            return 0.5  # Unknown environments
        
        if inputs.unique_environments >= self.min_environments:
            return 1.0
        
        # Linear scaling
        return inputs.unique_environments / self.min_environments
    
    def _calculate_model_consistency_score(self, inputs: ConfidenceInputs) -> float:
        """
        Calculate confidence from model prediction consistency.
        
        If predictions flip frequently, lower confidence.
        If predictions are stable, higher confidence.
        """
        if not inputs.prediction_history or len(inputs.prediction_history) < 3:
            return 0.8  # Not enough history, default to high confidence
        
        # Calculate prediction stability (how often predictions stay the same)
        changes = sum(
            1 for i in range(1, len(inputs.prediction_history))
            if inputs.prediction_history[i] != inputs.prediction_history[i-1]
        )
        
        stability = 1.0 - (changes / (len(inputs.prediction_history) - 1))
        
        # Also consider confidence score variance
        if inputs.confidence_history and len(inputs.confidence_history) >= 2:
            mean_conf = sum(inputs.confidence_history) / len(inputs.confidence_history)
            variance = sum(
                (c - mean_conf) ** 2 for c in inputs.confidence_history
            ) / len(inputs.confidence_history)
            
            # Lower variance = more consistent = higher confidence
            variance_penalty = min(1.0, variance * 5)  # Scale variance
            stability *= (1.0 - variance_penalty * 0.3)  # Up to 30% penalty
        
        return stability
    
    def _calculate_quality_multiplier(self, inputs: ConfidenceInputs) -> float:
        """
        Calculate data quality multiplier.
        
        Missing data reduces confidence.
        """
        quality_score = 0.6  # Base quality
        
        if inputs.has_error_signatures:
            quality_score += 0.15
        
        if inputs.has_duration_data:
            quality_score += 0.15
        
        if inputs.has_git_commits:
            quality_score += 0.10
        
        return quality_score
    
    def calculate_confidence_from_history(
        self,
        executions: List,  # List[TestExecutionRecord]
        prediction_history: Optional[List[bool]] = None,
        confidence_history: Optional[List[float]] = None
    ) -> float:
        """
        Convenience method to calculate confidence from execution records.
        
        Args:
            executions: List of TestExecutionRecord objects
            prediction_history: Optional historical predictions
            confidence_history: Optional historical confidence scores
            
        Returns:
            Confidence score (0-1)
        """
        if not executions:
            return 0.0
        
        # Extract confidence inputs
        sorted_execs = sorted(executions, key=lambda e: e.execution_time)
        
        environments = [e.environment for e in executions if e.environment]
        unique_envs = len(set(environments))
        
        inputs = ConfidenceInputs(
            total_executions=len(executions),
            first_execution=sorted_execs[0].execution_time,
            last_execution=sorted_execs[-1].execution_time,
            unique_environments=unique_envs,
            total_environment_runs=len(executions),
            prediction_history=prediction_history or [],
            confidence_history=confidence_history or [],
            has_error_signatures=any(e.error_signature for e in executions),
            has_duration_data=any(e.duration_ms > 0 for e in executions),
            has_git_commits=any(e.git_commit for e in executions),
        )
        
        return self.calculate_confidence(inputs)


class ConfidenceClassifier:
    """
    Classify flakiness with confidence thresholds.
    
    Never label without sufficient confidence.
    """
    
    def __init__(
        self,
        confident_threshold: float = 0.7,
        suspected_threshold: float = 0.5,
        insufficient_threshold: float = 0.3
    ):
        """
        Args:
            confident_threshold: Minimum confidence for "flaky" label
            suspected_threshold: Minimum confidence for "suspected_flaky"
            insufficient_threshold: Below this, label as "insufficient_data"
        """
        self.confident_threshold = confident_threshold
        self.suspected_threshold = suspected_threshold
        self.insufficient_threshold = insufficient_threshold
    
    def classify(
        self,
        is_flaky_prediction: bool,
        flaky_score: float,
        confidence: float
    ) -> str:
        """
        Classify flakiness with confidence gating.
        
        Args:
            is_flaky_prediction: Binary ML prediction (flaky or not)
            flaky_score: Anomaly score from model
            confidence: Confidence in prediction (0-1)
            
        Returns:
            Classification: "flaky", "suspected_flaky", "stable", "insufficient_data"
        """
        # Insufficient data check
        if confidence < self.insufficient_threshold:
            return "insufficient_data"
        
        # Not predicted as flaky
        if not is_flaky_prediction:
            return "stable"
        
        # Predicted as flaky, check confidence
        if confidence >= self.confident_threshold:
            return "flaky"
        elif confidence >= self.suspected_threshold:
            return "suspected_flaky"
        else:
            return "insufficient_data"
    
    def classify_severity(
        self,
        classification: str,
        failure_rate: float,
        confidence: float
    ) -> str:
        """
        Classify severity based on failure rate and confidence.
        
        Args:
            classification: Flakiness classification
            failure_rate: Test failure rate (0-1)
            confidence: Confidence score (0-1)
            
        Returns:
            Severity: "critical", "high", "medium", "low", "none"
        """
        if classification not in ("flaky", "suspected_flaky"):
            return "none"
        
        # Critical: high failure rate + high confidence
        if failure_rate > 0.7 and confidence > self.confident_threshold:
            return "critical"
        
        # High: moderate-high failure rate + high confidence
        if failure_rate > 0.5 and confidence > self.confident_threshold:
            return "high"
        
        # Medium: moderate failure rate + moderate confidence
        if failure_rate > 0.3 and confidence > self.suspected_threshold:
            return "medium"
        
        # Low: all other flaky tests
        return "low"


# ============================================================================
# Confidence Explanation
# ============================================================================

@dataclass
class ConfidenceExplanation:
    """
    Human-readable explanation of confidence score.
    
    Helps users understand why confidence is high/low.
    """
    
    overall_confidence: float
    volume_score: float
    time_span_score: float
    environment_score: float
    consistency_score: float
    
    # Raw data
    total_executions: int
    time_span_days: float
    unique_environments: int
    
    # Data quality
    has_error_signatures: bool
    has_duration_data: bool
    has_git_commits: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_confidence": round(self.overall_confidence, 2),
            "components": {
                "execution_volume": {
                    "score": round(self.volume_score, 2),
                    "executions": self.total_executions,
                },
                "time_span": {
                    "score": round(self.time_span_score, 2),
                    "days": round(self.time_span_days, 1),
                },
                "environment_diversity": {
                    "score": round(self.environment_score, 2),
                    "unique_environments": self.unique_environments,
                },
                "model_consistency": {
                    "score": round(self.consistency_score, 2),
                },
            },
            "data_quality": {
                "has_error_signatures": self.has_error_signatures,
                "has_duration_data": self.has_duration_data,
                "has_git_commits": self.has_git_commits,
            }
        }
    
    def __str__(self) -> str:
        """Human-readable explanation."""
        lines = [
            f"Confidence: {self.overall_confidence:.1%}",
            "",
            "Contributing factors:",
            f"  • Execution volume: {self.volume_score:.1%} ({self.total_executions} runs)",
            f"  • Time span: {self.time_span_score:.1%} ({self.time_span_days:.0f} days)",
            f"  • Environment diversity: {self.environment_score:.1%} ({self.unique_environments} environments)",
            f"  • Model consistency: {self.consistency_score:.1%}",
        ]
        
        # Data quality notes
        quality_notes = []
        if not self.has_error_signatures:
            quality_notes.append("missing error signatures")
        if not self.has_duration_data:
            quality_notes.append("missing duration data")
        if not self.has_git_commits:
            quality_notes.append("missing git commit data")
        
        if quality_notes:
            lines.append("")
            lines.append(f"Data quality: {', '.join(quality_notes)}")
        
        return "\n".join(lines)


def create_confidence_explanation(
    calibrator: ConfidenceCalibrator,
    inputs: ConfidenceInputs
) -> ConfidenceExplanation:
    """
    Create detailed confidence explanation.
    
    Args:
        calibrator: Confidence calibrator instance
        inputs: Confidence inputs
        
    Returns:
        Detailed explanation of confidence score
    """
    overall_confidence = calibrator.calculate_confidence(inputs)
    
    volume_score = calibrator._calculate_execution_volume_score(inputs)
    time_span_score = calibrator._calculate_time_span_score(inputs)
    environment_score = calibrator._calculate_environment_score(inputs)
    consistency_score = calibrator._calculate_model_consistency_score(inputs)
    
    time_span_days = 0.0
    if inputs.first_execution and inputs.last_execution:
        time_span = inputs.last_execution - inputs.first_execution
        time_span_days = time_span.total_seconds() / (24 * 3600)
    
    return ConfidenceExplanation(
        overall_confidence=overall_confidence,
        volume_score=volume_score,
        time_span_score=time_span_score,
        environment_score=environment_score,
        consistency_score=consistency_score,
        total_executions=inputs.total_executions,
        time_span_days=time_span_days,
        unique_environments=inputs.unique_environments,
        has_error_signatures=inputs.has_error_signatures,
        has_duration_data=inputs.has_duration_data,
        has_git_commits=inputs.has_git_commits,
    )
