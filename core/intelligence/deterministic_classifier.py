"""
Deterministic Core Classifier for Test Intelligence.

This module provides guaranteed, rule-based classification that:
- Always produces a result
- Never depends on external AI services
- Uses explainable, debuggable logic
- Provides baseline classification confidence

The deterministic classifier is the PRIMARY source of truth.
AI enrichment is OPTIONAL and SECONDARY.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ClassificationLabel(Enum):
    """Test classification labels (deterministic)."""
    STABLE = "stable"
    FLAKY = "flaky"
    UNSTABLE = "unstable"
    REGRESSION = "regression"
    NEW_TEST = "new_test"
    UNKNOWN = "unknown"


@dataclass
class SignalData:
    """
    Input signals for deterministic classification.
    
    These are observable, measurable facts about test execution.
    """
    test_name: str
    test_status: str  # pass, fail, skip, error
    retry_count: int = 0
    final_status: str = ""
    execution_duration_ms: float = 0.0
    
    # Historical data
    historical_failure_rate: float = 0.0  # 0.0 - 1.0
    total_runs: int = 0
    consecutive_failures: int = 0
    consecutive_passes: int = 0
    
    # Context
    code_changed: bool = False
    environment_changed: bool = False
    dependency_changed: bool = False
    
    # Pattern matching
    known_failure_signature: Optional[str] = None
    error_message: Optional[str] = None
    
    # Metadata
    framework: Optional[str] = None
    test_suite: Optional[str] = None
    
    def summary(self) -> Dict[str, Any]:
        """Get summarized signal data for logging/AI."""
        return {
            "test": self.test_name,
            "status": self.test_status,
            "retries": self.retry_count,
            "failure_rate": f"{self.historical_failure_rate:.1%}",
            "runs": self.total_runs,
            "duration_ms": self.execution_duration_ms,
            "code_changed": self.code_changed,
        }


@dataclass
class DeterministicResult:
    """
    Output from deterministic classifier.
    
    This is the PRIMARY classification result.
    It is GUARANTEED and EXPLAINABLE.
    """
    label: ClassificationLabel
    confidence: float  # 0.0 - 1.0 (rule-based confidence)
    reasons: List[str] = field(default_factory=list)
    
    # Supporting data
    applied_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "label": self.label.value,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "applied_rules": self.applied_rules,
            "metadata": self.metadata,
        }


class DeterministicClassifier:
    """
    Rule-based classifier for test intelligence.
    
    This classifier:
    - Uses only deterministic rules
    - Never depends on AI
    - Always produces output
    - Is fully testable and debuggable
    
    Rules are evaluated in priority order.
    First matching rule determines classification.
    """
    
    # Rule thresholds (configurable)
    FLAKY_THRESHOLD = 0.1  # 10% failure rate
    UNSTABLE_THRESHOLD = 0.4  # 40% failure rate
    MIN_RUNS_FOR_CONFIDENCE = 5
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize classifier with optional configuration.
        
        Args:
            config: Optional configuration overrides for thresholds
        """
        self.config = config or {}
        self._load_thresholds()
        logger.info("DeterministicClassifier initialized with config: %s", self.config)
    
    def _load_thresholds(self):
        """Load threshold values from config."""
        self.flaky_threshold = self.config.get('flaky_threshold', self.FLAKY_THRESHOLD)
        self.unstable_threshold = self.config.get('unstable_threshold', self.UNSTABLE_THRESHOLD)
        self.min_runs = self.config.get('min_runs_for_confidence', self.MIN_RUNS_FOR_CONFIDENCE)
    
    def classify(self, signal: SignalData) -> DeterministicResult:
        """
        Classify test based on deterministic rules.
        
        This is the PRIMARY classification method.
        It ALWAYS returns a result.
        
        Args:
            signal: Test execution signals
            
        Returns:
            DeterministicResult with label, confidence, and reasons
        """
        logger.debug("Classifying test: %s", signal.test_name)
        
        # Rule 1: New test detection (highest priority)
        result = self._rule_new_test(signal)
        if result:
            return result
        
        # Rule 2: Flaky test detection (retry-based)
        result = self._rule_flaky_retry(signal)
        if result:
            return result
        
        # Rule 3: Regression detection (code change + failure)
        result = self._rule_regression(signal)
        if result:
            return result
        
        # Rule 4: Unstable test (high failure rate)
        result = self._rule_unstable(signal)
        if result:
            return result
        
        # Rule 5: Flaky test (moderate failure rate)
        result = self._rule_flaky_history(signal)
        if result:
            return result
        
        # Rule 6: Stable test (low/no failure rate)
        result = self._rule_stable(signal)
        if result:
            return result
        
        # Default: Unknown (should rarely happen)
        return self._rule_unknown(signal)
    
    def _rule_new_test(self, signal: SignalData) -> Optional[DeterministicResult]:
        """Rule: New test (no historical data)."""
        if signal.total_runs == 0:
            return DeterministicResult(
                label=ClassificationLabel.NEW_TEST,
                confidence=1.0,
                reasons=["No historical execution data"],
                applied_rules=["new_test"]
            )
        
        if signal.total_runs < 3:
            return DeterministicResult(
                label=ClassificationLabel.NEW_TEST,
                confidence=0.8,
                reasons=[f"Limited history: only {signal.total_runs} runs"],
                applied_rules=["new_test_limited"]
            )
        
        return None
    
    def _rule_flaky_retry(self, signal: SignalData) -> Optional[DeterministicResult]:
        """Rule: Flaky test detected via retry behavior."""
        if signal.retry_count > 0 and signal.final_status == "pass":
            confidence = min(0.95, 0.7 + (signal.retry_count * 0.1))
            return DeterministicResult(
                label=ClassificationLabel.FLAKY,
                confidence=confidence,
                reasons=[
                    f"Test required {signal.retry_count} retries before passing",
                    "Classic flaky behavior: fail then pass"
                ],
                applied_rules=["flaky_retry"]
            )
        
        return None
    
    def _rule_regression(self, signal: SignalData) -> Optional[DeterministicResult]:
        """Rule: Likely regression (code change + failure)."""
        if signal.code_changed and signal.test_status in ["fail", "error"]:
            # Higher confidence if test was previously stable
            if signal.consecutive_passes >= 5:
                confidence = 0.85
                reasons = [
                    "Code changed and test failed",
                    f"Previously passed {signal.consecutive_passes} times consecutively"
                ]
            else:
                confidence = 0.7
                reasons = [
                    "Code changed and test failed",
                    "Test history shows some instability"
                ]
            
            return DeterministicResult(
                label=ClassificationLabel.REGRESSION,
                confidence=confidence,
                reasons=reasons,
                applied_rules=["regression_code_change"]
            )
        
        return None
    
    def _rule_unstable(self, signal: SignalData) -> Optional[DeterministicResult]:
        """Rule: Unstable test (high failure rate)."""
        if signal.total_runs >= self.min_runs:
            if signal.historical_failure_rate >= self.unstable_threshold:
                confidence = min(0.95, 0.6 + (signal.historical_failure_rate * 0.3))
                return DeterministicResult(
                    label=ClassificationLabel.UNSTABLE,
                    confidence=confidence,
                    reasons=[
                        f"High failure rate: {signal.historical_failure_rate:.1%}",
                        f"Failed {int(signal.total_runs * signal.historical_failure_rate)} out of {signal.total_runs} runs"
                    ],
                    applied_rules=["unstable_high_failure"]
                )
        
        return None
    
    def _rule_flaky_history(self, signal: SignalData) -> Optional[DeterministicResult]:
        """Rule: Flaky test (moderate failure rate)."""
        if signal.total_runs >= self.min_runs:
            if self.flaky_threshold <= signal.historical_failure_rate < self.unstable_threshold:
                confidence = 0.65 + (signal.historical_failure_rate * 0.2)
                return DeterministicResult(
                    label=ClassificationLabel.FLAKY,
                    confidence=confidence,
                    reasons=[
                        f"Intermittent failures: {signal.historical_failure_rate:.1%} failure rate",
                        f"Failed {int(signal.total_runs * signal.historical_failure_rate)} out of {signal.total_runs} runs"
                    ],
                    applied_rules=["flaky_intermittent"]
                )
        
        return None
    
    def _rule_stable(self, signal: SignalData) -> Optional[DeterministicResult]:
        """Rule: Stable test (low/no failure rate)."""
        if signal.total_runs >= self.min_runs:
            if signal.historical_failure_rate < self.flaky_threshold:
                # Higher confidence with more runs
                confidence = min(0.95, 0.75 + (signal.total_runs / 100))
                
                if signal.historical_failure_rate == 0:
                    reasons = [f"Perfect pass rate: {signal.total_runs} consecutive passes"]
                else:
                    reasons = [
                        f"Very low failure rate: {signal.historical_failure_rate:.1%}",
                        "Test shows consistent behavior"
                    ]
                
                return DeterministicResult(
                    label=ClassificationLabel.STABLE,
                    confidence=confidence,
                    reasons=reasons,
                    applied_rules=["stable_low_failure"]
                )
        
        return None
    
    def _rule_unknown(self, signal: SignalData) -> DeterministicResult:
        """Fallback rule: Cannot classify with confidence."""
        return DeterministicResult(
            label=ClassificationLabel.UNKNOWN,
            confidence=0.3,
            reasons=[
                "Insufficient data for confident classification",
                f"Total runs: {signal.total_runs}, Status: {signal.test_status}"
            ],
            applied_rules=["unknown_fallback"]
        )
    
    def batch_classify(self, signals: List[SignalData]) -> List[DeterministicResult]:
        """
        Classify multiple tests efficiently.
        
        Args:
            signals: List of test signals
            
        Returns:
            List of deterministic results (same order as input)
        """
        results = []
        for signal in signals:
            try:
                result = self.classify(signal)
                results.append(result)
            except Exception as e:
                logger.error("Classification failed for %s: %s", signal.test_name, e)
                # Even on error, return a result
                results.append(DeterministicResult(
                    label=ClassificationLabel.UNKNOWN,
                    confidence=0.0,
                    reasons=[f"Classification error: {str(e)}"],
                    applied_rules=["error_fallback"]
                ))
        
        return results
