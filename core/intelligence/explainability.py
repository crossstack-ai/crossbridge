"""
Confidence Explanation System for Deterministic Failure Classification.

This module provides standardized explainability for failure classifications:
- Rule influence: Why specific rules contributed to the classification
- Signal quality: How reliable the input signals were
- Evidence context: What data supported the decision

Design Principles:
- Classification and explanation are decoupled but linked
- Never recompute logic during explanation
- Framework-agnostic signal normalization
- CI-friendly JSON output
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# CORE MODELS
# ============================================================================

class FailureCategory(Enum):
    """Standard failure categories (framework-agnostic)."""
    TIMEOUT = "timeout"
    ASSERTION = "assertion"
    INFRASTRUCTURE = "infrastructure"
    DATA_ISSUE = "data_issue"
    FLAKY = "flaky"
    REGRESSION = "regression"
    UNKNOWN = "unknown"


@dataclass
class FailureClassification:
    """
    Baseline failure classification output.
    
    This is the normalized structure all frameworks must return.
    """
    failure_id: str
    category: str  # FailureCategory value
    confidence: float  # 0.0 - 1.0
    primary_rule: str
    signals_used: List[str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RuleInfluence:
    """
    Explains why a specific rule contributed to the classification.
    
    Attributes:
        rule_name: Name of the classification rule
        weight: Rule's base weight (0.0 - 1.0)
        matched: Whether the rule matched
        contribution: Normalized contribution to final confidence (0.0 - 1.0)
        explanation: Human-readable explanation of why the rule matched
    """
    rule_name: str
    weight: float
    matched: bool
    contribution: float  # Normalized: weight * match_strength / total
    explanation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SignalQuality:
    """
    Explains the reliability of input signals.
    
    Framework-agnostic signal quality scoring:
    - stacktrace_presence: Is there a stacktrace?
    - error_message_stability: Is error message consistent?
    - retry_consistency: Does failure reproduce on retry?
    - historical_frequency: How often has this failed before?
    - cross_test_correlation: Do related tests show similar failures?
    
    Attributes:
        signal_name: Name of the signal
        quality_score: Reliability score (0.0 - 1.0)
        evidence: Supporting evidence for the quality score
    """
    signal_name: str
    quality_score: float  # 0.0 - 1.0
    evidence: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EvidenceContext:
    """
    Supporting evidence for the classification decision.
    
    Guidelines:
    - NO raw logs (summaries only)
    - NO full stack traces (summaries only)
    - Deterministic formatting
    - Short and actionable
    """
    stacktrace_summary: Optional[str] = None
    error_message_summary: Optional[str] = None
    similar_failures: List[str] = field(default_factory=list)
    related_tests: List[str] = field(default_factory=list)
    logs_summary: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence computation."""
    rule_score: float  # Weighted rule contribution
    signal_score: float  # Signal quality average
    final_confidence: float  # Computed confidence
    formula: str = "0.7 * rule_score + 0.3 * signal_score"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ConfidenceExplanation:
    """
    Complete explanation of failure classification confidence.
    
    This is the main output consumed by CI systems, dashboards, and humans.
    """
    failure_id: str
    final_confidence: float
    category: str
    primary_rule: str
    
    # Detailed explanations
    rule_influence: List[RuleInfluence]
    signal_quality: List[SignalQuality]
    evidence_context: EvidenceContext
    confidence_breakdown: ConfidenceBreakdown
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    framework: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "failure_id": self.failure_id,
            "final_confidence": self.final_confidence,
            "category": self.category,
            "primary_rule": self.primary_rule,
            "rule_influence": [r.to_dict() for r in self.rule_influence],
            "signal_quality": [s.to_dict() for s in self.signal_quality],
            "evidence_context": self.evidence_context.to_dict(),
            "confidence_breakdown": self.confidence_breakdown.to_dict(),
            "timestamp": self.timestamp,
            "framework": self.framework
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save_to_file(self, filepath: str):
        """Save explanation to JSON file (CI artifact)."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())
        logger.info(f"Saved explanation to {filepath}")
    
    def to_ci_summary(self) -> str:
        """
        Generate CI-friendly text summary.
        
        Example output:
        Failure: Timeout (Confidence: 82%)
        
        Primary Rule:
        - TimeoutRule (65%)
        
        Strong Signals:
        - Retry consistency (90%)
        
        Evidence:
        - Timeout waiting for LoginButton.click()
        """
        lines = [
            f"Failure: {self.category} (Confidence: {self.final_confidence:.0%})",
            "",
            "Primary Rule:"
        ]
        
        # Top contributing rules
        top_rules = sorted(self.rule_influence, key=lambda r: r.contribution, reverse=True)[:3]
        for rule in top_rules:
            if rule.matched:
                lines.append(f"- {rule.rule_name} ({rule.contribution:.0%})")
        
        # Strong signals (>70% quality)
        strong_signals = [s for s in self.signal_quality if s.quality_score >= 0.7]
        if strong_signals:
            lines.append("")
            lines.append("Strong Signals:")
            for signal in strong_signals:
                lines.append(f"- {signal.signal_name.replace('_', ' ').title()} ({signal.quality_score:.0%})")
        
        # Evidence summary
        if self.evidence_context.stacktrace_summary or self.evidence_context.error_message_summary:
            lines.append("")
            lines.append("Evidence:")
            if self.evidence_context.stacktrace_summary:
                lines.append(f"- {self.evidence_context.stacktrace_summary}")
            if self.evidence_context.error_message_summary:
                lines.append(f"- {self.evidence_context.error_message_summary}")
        
        return "\n".join(lines)


# ============================================================================
# CONFIDENCE COMPUTATION
# ============================================================================

def compute_confidence(rule_score: float, signal_score: float) -> float:
    """
    Standardized confidence computation formula.
    
    Formula: 0.7 * rule_score + 0.3 * signal_score
    
    This formula is used consistently across all frameworks.
    
    Args:
        rule_score: Weighted average of rule contributions (0.0 - 1.0)
        signal_score: Average signal quality (0.0 - 1.0)
        
    Returns:
        Final confidence score (0.0 - 1.0)
    """
    return min(1.0, 0.7 * rule_score + 0.3 * signal_score)


def aggregate_rule_influence(influences: List[RuleInfluence]) -> List[RuleInfluence]:
    """
    Normalize rule contributions to sum to 1.0.
    
    Args:
        influences: List of rule influences with raw contributions
        
    Returns:
        Normalized influences where contributions sum to 1.0
    """
    total = sum(r.contribution for r in influences if r.matched)
    
    if total > 0:
        for influence in influences:
            if influence.matched:
                influence.contribution = influence.contribution / total
            else:
                influence.contribution = 0.0
    
    return influences


# ============================================================================
# SIGNAL QUALITY EVALUATION
# ============================================================================

class SignalEvaluator:
    """
    Framework-agnostic signal quality evaluator.
    
    Evaluates standard signals across all frameworks:
    - stacktrace_presence
    - error_message_stability
    - retry_consistency
    - historical_frequency
    - cross_test_correlation
    """
    
    @staticmethod
    def evaluate_stacktrace_presence(
        has_stacktrace: bool,
        stacktrace_lines: int = 0
    ) -> SignalQuality:
        """Evaluate stacktrace signal quality."""
        if has_stacktrace and stacktrace_lines > 3:
            return SignalQuality(
                signal_name="stacktrace_presence",
                quality_score=0.9,
                evidence=f"Complete stacktrace with {stacktrace_lines} lines"
            )
        elif has_stacktrace:
            return SignalQuality(
                signal_name="stacktrace_presence",
                quality_score=0.6,
                evidence="Partial stacktrace available"
            )
        else:
            return SignalQuality(
                signal_name="stacktrace_presence",
                quality_score=0.3,
                evidence="No stacktrace available"
            )
    
    @staticmethod
    def evaluate_error_message_stability(
        error_message: Optional[str],
        is_consistent: bool = True
    ) -> SignalQuality:
        """Evaluate error message signal quality."""
        if error_message and is_consistent:
            return SignalQuality(
                signal_name="error_message_stability",
                quality_score=0.85,
                evidence="Consistent error message across failures"
            )
        elif error_message:
            return SignalQuality(
                signal_name="error_message_stability",
                quality_score=0.5,
                evidence="Error message present but varies"
            )
        else:
            return SignalQuality(
                signal_name="error_message_stability",
                quality_score=0.2,
                evidence="No error message available"
            )
    
    @staticmethod
    def evaluate_retry_consistency(
        retry_count: int,
        failure_reproduced: bool
    ) -> SignalQuality:
        """
        Evaluate retry consistency signal quality.
        
        Framework mapping:
        - Selenium → retries
        - Pytest → reruns
        - Robot → retry keyword
        All map to retry_consistency.
        """
        if retry_count > 0 and failure_reproduced:
            return SignalQuality(
                signal_name="retry_consistency",
                quality_score=0.9,
                evidence=f"Failure reproduced across {retry_count} retries"
            )
        elif retry_count > 0:
            return SignalQuality(
                signal_name="retry_consistency",
                quality_score=0.4,
                evidence=f"Failure not consistent across {retry_count} retries"
            )
        else:
            return SignalQuality(
                signal_name="retry_consistency",
                quality_score=0.5,
                evidence="No retry data available"
            )
    
    @staticmethod
    def evaluate_historical_frequency(
        historical_failure_rate: float,
        total_runs: int
    ) -> SignalQuality:
        """Evaluate historical frequency signal quality."""
        if total_runs >= 10:
            return SignalQuality(
                signal_name="historical_frequency",
                quality_score=0.8,
                evidence=f"Based on {total_runs} historical runs ({historical_failure_rate:.1%} failure rate)"
            )
        elif total_runs >= 5:
            return SignalQuality(
                signal_name="historical_frequency",
                quality_score=0.6,
                evidence=f"Limited history: {total_runs} runs"
            )
        else:
            return SignalQuality(
                signal_name="historical_frequency",
                quality_score=0.3,
                evidence="Insufficient historical data"
            )
    
    @staticmethod
    def evaluate_cross_test_correlation(
        similar_failure_count: int,
        related_test_count: int
    ) -> SignalQuality:
        """Evaluate cross-test correlation signal quality."""
        if similar_failure_count >= 3:
            return SignalQuality(
                signal_name="cross_test_correlation",
                quality_score=0.85,
                evidence=f"Pattern found in {similar_failure_count} related tests"
            )
        elif similar_failure_count >= 1:
            return SignalQuality(
                signal_name="cross_test_correlation",
                quality_score=0.6,
                evidence=f"Similar pattern in {similar_failure_count} test(s)"
            )
        else:
            return SignalQuality(
                signal_name="cross_test_correlation",
                quality_score=0.4,
                evidence="No cross-test patterns detected"
            )


# ============================================================================
# EVIDENCE EXTRACTION
# ============================================================================

class EvidenceExtractor:
    """Extract and summarize evidence from failure data."""
    
    MAX_STACKTRACE_LINES = 3
    MAX_ERROR_MESSAGE_LENGTH = 150
    MAX_LOG_LINES = 5
    
    @staticmethod
    def summarize_stacktrace(stacktrace: Optional[str]) -> Optional[str]:
        """
        Summarize stacktrace (NO full traces).
        
        Rules:
        - Extract last meaningful line
        - Include method/file name
        - Max 150 characters
        """
        if not stacktrace:
            return None
        
        lines = stacktrace.strip().split('\n')
        # Get last meaningful line (often the error location)
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('File') and len(line) > 10:
                summary = line[:EvidenceExtractor.MAX_ERROR_MESSAGE_LENGTH]
                return summary
        
        # Fallback: first line
        return lines[0][:EvidenceExtractor.MAX_ERROR_MESSAGE_LENGTH] if lines else None
    
    @staticmethod
    def summarize_error_message(error_message: Optional[str]) -> Optional[str]:
        """
        Summarize error message (NO raw dumps).
        
        Rules:
        - Max 150 characters
        - Remove timestamps/IDs
        - Extract meaningful part
        """
        if not error_message:
            return None
        
        # Clean up common noise
        message = error_message.strip()
        
        # Remove common prefixes
        for prefix in ['ERROR:', 'FAIL:', 'Exception:', 'Error:']:
            if message.startswith(prefix):
                message = message[len(prefix):].strip()
        
        # Truncate
        if len(message) > EvidenceExtractor.MAX_ERROR_MESSAGE_LENGTH:
            message = message[:EvidenceExtractor.MAX_ERROR_MESSAGE_LENGTH] + "..."
        
        return message
    
    @staticmethod
    def summarize_logs(logs: List[str]) -> List[str]:
        """
        Summarize logs (NO raw logs).
        
        Rules:
        - Max 5 lines
        - Extract ERROR/WARN level only
        - Remove timestamps
        """
        if not logs:
            return []
        
        # Filter for ERROR/WARN
        important_logs = []
        for log in logs:
            if 'ERROR' in log.upper() or 'WARN' in log.upper():
                # Remove timestamp (common patterns)
                cleaned = log.split(']', 1)[-1].strip() if ']' in log else log
                important_logs.append(cleaned[:EvidenceExtractor.MAX_ERROR_MESSAGE_LENGTH])
                
                if len(important_logs) >= EvidenceExtractor.MAX_LOG_LINES:
                    break
        
        return important_logs


# ============================================================================
# EXPLAINABILITY API
# ============================================================================

def explain_failure(
    failure_classification: FailureClassification,
    rule_influences: List[RuleInfluence],
    signal_qualities: List[SignalQuality],
    evidence_context: EvidenceContext,
    framework: Optional[str] = None
) -> ConfidenceExplanation:
    """
    Generate complete confidence explanation for a failure.
    
    This is the main API that ties everything together.
    
    Args:
        failure_classification: The baseline classification
        rule_influences: List of rule contributions
        signal_qualities: List of signal quality assessments
        evidence_context: Supporting evidence
        framework: Optional framework name
        
    Returns:
        Complete confidence explanation
    """
    # Normalize rule influences
    normalized_influences = aggregate_rule_influence(rule_influences)
    
    # Compute scores
    rule_score = sum(r.contribution for r in normalized_influences if r.matched)
    signal_score = sum(s.quality_score for s in signal_qualities) / max(len(signal_qualities), 1)
    final_confidence = compute_confidence(rule_score, signal_score)
    
    # Create confidence breakdown
    breakdown = ConfidenceBreakdown(
        rule_score=rule_score,
        signal_score=signal_score,
        final_confidence=final_confidence
    )
    
    # Build explanation
    explanation = ConfidenceExplanation(
        failure_id=failure_classification.failure_id,
        final_confidence=final_confidence,
        category=failure_classification.category,
        primary_rule=failure_classification.primary_rule,
        rule_influence=normalized_influences,
        signal_quality=signal_qualities,
        evidence_context=evidence_context,
        confidence_breakdown=breakdown,
        framework=framework
    )
    
    return explanation


# ============================================================================
# CI INTEGRATION HELPERS
# ============================================================================

def save_ci_artifacts(
    explanation: ConfidenceExplanation,
    output_dir: str = "."
) -> str:
    """
    Save explanation as CI artifact.
    
    Creates: {output_dir}/ci-artifacts/failure_explanations/
    
    Args:
        explanation: The confidence explanation
        output_dir: Base directory to save artifacts
        
    Returns:
        Path to saved JSON artifact
    """
    import os
    
    # Create directory structure
    artifacts_dir = os.path.join(output_dir, "ci-artifacts", "failure_explanations")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    # Save JSON
    json_path = os.path.join(artifacts_dir, f"{explanation.failure_id}.json")
    explanation.save_to_file(json_path)
    
    # Save text summary
    text_path = os.path.join(artifacts_dir, f"{explanation.failure_id}.txt")
    with open(text_path, 'w') as f:
        f.write(explanation.to_ci_summary())
    
    logger.info(f"Saved CI artifacts to {artifacts_dir}")
    return json_path


def generate_pr_comment(explanation: ConfidenceExplanation) -> str:
    """
    Generate markdown comment for PR.
    
    Returns:
        Markdown-formatted comment
    """
    return f"""
## 🔍 Failure Analysis: {explanation.failure_id}

**Category**: {explanation.category}  
**Confidence**: {explanation.final_confidence:.0%}

### Primary Contributing Rule
{explanation.primary_rule}

### Rule Influence
{chr(10).join(f"- **{r.rule_name}**: {r.contribution:.0%} - {r.explanation}" for r in explanation.rule_influence if r.matched)[:3]}

### Signal Quality
{chr(10).join(f"- **{s.signal_name}**: {s.quality_score:.0%} - {s.evidence}" for s in explanation.signal_quality if s.quality_score >= 0.7)}

### Evidence
{explanation.evidence_context.error_message_summary or 'No error message'}

---
<details>
<summary>Detailed Breakdown</summary>

**Confidence Computation**:
- Rule Score: {explanation.confidence_breakdown.rule_score:.2f}
- Signal Score: {explanation.confidence_breakdown.signal_score:.2f}
- Formula: {explanation.confidence_breakdown.formula}

</details>
"""
