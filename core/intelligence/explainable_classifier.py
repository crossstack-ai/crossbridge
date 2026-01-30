"""
Enhanced Deterministic Classifier with Explainability.

This module extends the base deterministic classifier to track rule influence
and provide detailed explanations for classifications.
"""

from typing import Optional, List, Dict, Any, Tuple
import logging

from .deterministic_classifier import (
    DeterministicClassifier,
    DeterministicResult,
    SignalData,
    ClassificationLabel
)
from .explainability import (
    RuleInfluence,
    SignalQuality,
    EvidenceContext,
    ConfidenceExplanation,
    SignalEvaluator,
    EvidenceExtractor,
    FailureClassification,
    explain_failure
)

logger = logging.getLogger(__name__)


class ExplainableClassifier(DeterministicClassifier):
    """
    Deterministic classifier with explainability tracking.
    
    Extends base classifier to track:
    - Rule influence (which rules matched and their contribution)
    - Signal quality (reliability of input signals)
    - Evidence context (supporting data)
    
    Usage:
        classifier = ExplainableClassifier()
        result, explanation = classifier.classify_with_explanation(signal)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize explainable classifier."""
        super().__init__(config)
        self.signal_evaluator = SignalEvaluator()
        self.evidence_extractor = EvidenceExtractor()
        logger.info("ExplainableClassifier initialized")
    
    def classify_with_explanation(
        self,
        signal: SignalData,
        failure_id: Optional[str] = None
    ) -> Tuple[DeterministicResult, ConfidenceExplanation]:
        """
        Classify with full explainability tracking.
        
        Args:
            signal: Test execution signals
            failure_id: Optional failure ID (generated if not provided)
            
        Returns:
            Tuple of (classification_result, confidence_explanation)
        """
        # Run deterministic classification
        result = self.classify(signal)
        
        # Generate failure ID if not provided
        if not failure_id:
            import hashlib
            failure_id = f"F-{hashlib.md5(signal.test_name.encode()).hexdigest()[:8].upper()}"
        
        # Track rule influences
        rule_influences = self._compute_rule_influences(signal, result)
        
        # Evaluate signal quality
        signal_qualities = self._evaluate_signal_quality(signal)
        
        # Extract evidence context
        evidence_context = self._extract_evidence(signal)
        
        # Create failure classification
        failure_classification = FailureClassification(
            failure_id=failure_id,
            category=result.label.value,
            confidence=result.confidence,
            primary_rule=result.applied_rules[0] if result.applied_rules else "unknown",
            signals_used=self._get_signals_used(signal)
        )
        
        # Generate explanation
        explanation = explain_failure(
            failure_classification=failure_classification,
            rule_influences=rule_influences,
            signal_qualities=signal_qualities,
            evidence_context=evidence_context,
            framework=signal.framework
        )
        
        logger.info(
            "Classification complete with explanation: %s (confidence=%.2f)",
            result.label.value, explanation.final_confidence
        )
        
        return result, explanation
    
    def _compute_rule_influences(
        self,
        signal: SignalData,
        result: DeterministicResult
    ) -> List[RuleInfluence]:
        """
        Compute rule influence for all evaluated rules.
        
        This tracks which rules matched and their contribution.
        """
        influences = []
        
        # Rule 1: New Test (highest priority)
        influences.append(self._eval_new_test_influence(signal, result))
        
        # Rule 2: Flaky (retry-based)
        influences.append(self._eval_flaky_retry_influence(signal, result))
        
        # Rule 3: Regression
        influences.append(self._eval_regression_influence(signal, result))
        
        # Rule 4: Unstable
        influences.append(self._eval_unstable_influence(signal, result))
        
        # Rule 5: Flaky (history-based)
        influences.append(self._eval_flaky_history_influence(signal, result))
        
        # Rule 6: Stable
        influences.append(self._eval_stable_influence(signal, result))
        
        return influences
    
    def _eval_new_test_influence(
        self,
        signal: SignalData,
        result: DeterministicResult
    ) -> RuleInfluence:
        """Evaluate new test rule influence."""
        matched = signal.total_runs < 3
        weight = 1.0  # Highest priority rule
        
        if matched:
            if signal.total_runs == 0:
                explanation = "Test has never been executed before"
            else:
                explanation = f"Test has limited execution history ({signal.total_runs} runs)"
        else:
            explanation = f"Test has sufficient execution history ({signal.total_runs} runs)"
        
        return RuleInfluence(
            rule_name="new_test",
            weight=weight,
            matched=matched,
            contribution=weight if matched else 0.0,
            explanation=explanation
        )
    
    def _eval_flaky_retry_influence(
        self,
        signal: SignalData,
        result: DeterministicResult
    ) -> RuleInfluence:
        """Evaluate flaky retry rule influence."""
        matched = signal.retry_count > 0 and signal.final_status == "pass"
        weight = 0.9
        
        if matched:
            explanation = f"Test failed initially but passed after {signal.retry_count} retry(ies)"
        else:
            if signal.retry_count > 0:
                explanation = "Test was retried but did not exhibit flaky pattern"
            else:
                explanation = "Test was not retried"
        
        return RuleInfluence(
            rule_name="flaky_retry",
            weight=weight,
            matched=matched,
            contribution=weight if matched else 0.0,
            explanation=explanation
        )
    
    def _eval_regression_influence(
        self,
        signal: SignalData,
        result: DeterministicResult
    ) -> RuleInfluence:
        """Evaluate regression rule influence."""
        matched = signal.code_changed and signal.test_status in ["fail", "error"]
        weight = 0.85
        
        if matched:
            if signal.consecutive_passes >= 5:
                explanation = f"Code change detected and test failed after {signal.consecutive_passes} consecutive passes"
            else:
                explanation = "Code change detected and test failed, but test history shows instability"
        else:
            if not signal.code_changed:
                explanation = "No code changes detected"
            else:
                explanation = "Code changed but test did not fail"
        
        return RuleInfluence(
            rule_name="regression",
            weight=weight,
            matched=matched,
            contribution=weight if matched else 0.0,
            explanation=explanation
        )
    
    def _eval_unstable_influence(
        self,
        signal: SignalData,
        result: DeterministicResult
    ) -> RuleInfluence:
        """Evaluate unstable rule influence."""
        matched = (
            signal.total_runs >= self.min_runs and
            signal.historical_failure_rate >= self.unstable_threshold
        )
        weight = 0.8
        
        if matched:
            explanation = f"High failure rate ({signal.historical_failure_rate:.1%}) across {signal.total_runs} runs"
        else:
            if signal.total_runs < self.min_runs:
                explanation = "Insufficient runs for unstable classification"
            else:
                explanation = f"Failure rate ({signal.historical_failure_rate:.1%}) below unstable threshold"
        
        return RuleInfluence(
            rule_name="unstable",
            weight=weight,
            matched=matched,
            contribution=weight if matched else 0.0,
            explanation=explanation
        )
    
    def _eval_flaky_history_influence(
        self,
        signal: SignalData,
        result: DeterministicResult
    ) -> RuleInfluence:
        """Evaluate flaky history rule influence."""
        matched = (
            signal.total_runs >= self.min_runs and
            self.flaky_threshold <= signal.historical_failure_rate < self.unstable_threshold
        )
        weight = 0.7
        
        if matched:
            explanation = f"Moderate failure rate ({signal.historical_failure_rate:.1%}) indicating flakiness"
        else:
            explanation = f"Failure rate ({signal.historical_failure_rate:.1%}) outside flaky range"
        
        return RuleInfluence(
            rule_name="flaky_history",
            weight=weight,
            matched=matched,
            contribution=weight if matched else 0.0,
            explanation=explanation
        )
    
    def _eval_stable_influence(
        self,
        signal: SignalData,
        result: DeterministicResult
    ) -> RuleInfluence:
        """Evaluate stable rule influence."""
        matched = (
            signal.total_runs >= self.min_runs and
            signal.historical_failure_rate < self.flaky_threshold
        )
        weight = 0.6
        
        if matched:
            if signal.consecutive_passes >= 10:
                explanation = f"Excellent stability: {signal.consecutive_passes} consecutive passes, {signal.historical_failure_rate:.1%} failure rate"
            else:
                explanation = f"Good stability: {signal.historical_failure_rate:.1%} failure rate over {signal.total_runs} runs"
        else:
            explanation = "Test does not meet stable criteria"
        
        return RuleInfluence(
            rule_name="stable",
            weight=weight,
            matched=matched,
            contribution=weight if matched else 0.0,
            explanation=explanation
        )
    
    def _evaluate_signal_quality(self, signal: SignalData) -> List[SignalQuality]:
        """Evaluate quality of all input signals."""
        qualities = []
        
        # Stacktrace presence
        has_stacktrace = bool(signal.error_message)
        stacktrace_lines = len(signal.error_message.split('\n')) if signal.error_message else 0
        qualities.append(
            self.signal_evaluator.evaluate_stacktrace_presence(
                has_stacktrace=has_stacktrace,
                stacktrace_lines=stacktrace_lines
            )
        )
        
        # Error message stability
        qualities.append(
            self.signal_evaluator.evaluate_error_message_stability(
                error_message=signal.error_message,
                is_consistent=True  # Would need historical comparison
            )
        )
        
        # Retry consistency
        failure_reproduced = signal.retry_count > 0 and signal.final_status != "pass"
        qualities.append(
            self.signal_evaluator.evaluate_retry_consistency(
                retry_count=signal.retry_count,
                failure_reproduced=failure_reproduced
            )
        )
        
        # Historical frequency
        qualities.append(
            self.signal_evaluator.evaluate_historical_frequency(
                historical_failure_rate=signal.historical_failure_rate,
                total_runs=signal.total_runs
            )
        )
        
        # Cross-test correlation (would need additional data)
        qualities.append(
            self.signal_evaluator.evaluate_cross_test_correlation(
                similar_failure_count=0,  # Would need pattern matching
                related_test_count=0
            )
        )
        
        return qualities
    
    def _extract_evidence(self, signal: SignalData) -> EvidenceContext:
        """Extract evidence context from signal data."""
        # Summarize error message
        error_summary = self.evidence_extractor.summarize_error_message(signal.error_message)
        
        # Summarize stacktrace (if available in error_message)
        stacktrace_summary = self.evidence_extractor.summarize_stacktrace(signal.error_message)
        
        # Related tests (would need additional data)
        related_tests = []
        if signal.test_suite:
            related_tests = [f"{signal.test_suite}.*"]
        
        return EvidenceContext(
            stacktrace_summary=stacktrace_summary,
            error_message_summary=error_summary,
            similar_failures=[],  # Would need historical lookup
            related_tests=related_tests,
            logs_summary=[]  # Would need log data
        )
    
    def _get_signals_used(self, signal: SignalData) -> List[str]:
        """Get list of signals used in classification."""
        signals = []
        
        if signal.retry_count > 0:
            signals.append("retry_count")
        
        if signal.total_runs > 0:
            signals.append("historical_failure_rate")
            signals.append("total_runs")
        
        if signal.code_changed:
            signals.append("code_changed")
        
        if signal.consecutive_passes > 0:
            signals.append("consecutive_passes")
        
        if signal.consecutive_failures > 0:
            signals.append("consecutive_failures")
        
        if signal.error_message:
            signals.append("error_message")
        
        return signals


# Convenience function for quick explanation
def classify_and_explain(
    signal: SignalData,
    failure_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Tuple[DeterministicResult, ConfidenceExplanation]:
    """
    Classify a test and generate explanation (one-shot function).
    
    Args:
        signal: Test execution signals
        failure_id: Optional failure ID
        config: Optional classifier configuration
        
    Returns:
        Tuple of (classification_result, confidence_explanation)
    """
    classifier = ExplainableClassifier(config)
    return classifier.classify_with_explanation(signal, failure_id)
