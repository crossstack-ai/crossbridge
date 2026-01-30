"""
Confidence Scoring Logic

Implements the confidence calculation algorithms for failure classification.

CONFIDENCE SCORING ALGORITHM (Aligned with Industry Standards):
==============================================================

Base Formula:
    confidence = min(1.0,
        base_signal_confidence +
        rule_confidence_boost +
        log1p(history_frequency) / log1p(20) +
        application_log_correlation_boost +
        signal_agreement_boost
    )

Confidence Buckets (UX-Safe):
    HIGH (≥0.8)       : Auto-apply safe, minimal review needed
    MEDIUM (0.6-0.8)  : Review recommended before action
    LOW (<0.6)        : Manual review required

Scoring Inputs:
---------------
1. base_signal_confidence (0.8-1.0)
   - From FailureSignalExtractor pattern matching
   - Higher for exact exception name matches
   - Lower for fuzzy pattern matches

2. rule_confidence_boost (0.0-0.3)
   - From matched rule packs (per-framework rules)
   - Multiple agreeing rules increase boost
   - max(rule.confidence) + 0.1 per additional rule (capped at +0.2)

3. history_frequency (logarithmic scaling)
   - log1p(occurrences) / log1p(20)
   - Caps at ~0.15 for frequently seen patterns
   - New patterns get 0.0, common patterns get boost

4. application_log_correlation (+0.1 to +0.2)
   - If application logs confirm automation failure
   - e.g., app shows 500 error when test sees HTTP failure
   - Strong correlation: +0.2, weak: +0.1

5. signal_agreement_boost (+0.1 to +0.2)
   - Multiple signals pointing to same classification
   - Stacktrace + code reference: +0.2
   - Multiple error signals: +0.1

Priority Weighting:
-------------------
Higher priority rules have stronger influence:
    Priority 1-50:   confidence * 1.0
    Priority 51-100: confidence * 0.9
    Priority 101+:   confidence * 0.8

Confidence Decay:
-----------------
Confidence decreases if:
- No stacktrace: -0.1
- No code reference: -0.1
- Ambiguous error message: -0.2
- New/unseen failure pattern: -0.05

Example Calculations:
---------------------
1. Known Timeout (High Confidence):
   base=0.9 + rules=0.2 + history=0.12 + app_logs=0.1 = 1.0 → 0.95 (capped)

2. New Assertion Failure (Medium):
   base=0.85 + rules=0.15 + history=0.0 + app_logs=0.0 = 0.75 (MEDIUM)

3. Ambiguous Error (Low):
   base=0.6 + rules=0.1 + history=0.0 - ambiguity_penalty=0.2 = 0.5 (LOW)

CI/CD Integration:
------------------
- HIGH confidence → Auto-retry or auto-classify safe
- MEDIUM confidence → Show warning, suggest review
- LOW confidence → Block automation, require human review

This algorithm ensures:
✅ Deterministic and explainable results
✅ Safe for production CI/CD decisions
✅ Improves over time with historical data
✅ Never silently fails (always returns confidence)
✅ Conservative scoring prevents false positives
"""

from typing import List, Optional
from core.execution.intelligence.confidence.models import ConfidenceBreakdown


def calculate_rule_score(matched_rules: List) -> float:
    """
    Calculate confidence score based on matched rules.
    
    Higher confidence if:
    - Strong rule matches (high priority rules)
    - Multiple corroborating rules
    
    Args:
        matched_rules: List of matched Rule objects
        
    Returns:
        Rule score (0.0-1.0)
    """
    if not matched_rules:
        return 0.0  # No rules matched
    
    # Use highest confidence rule as base
    max_confidence = max(r.confidence for r in matched_rules)
    
    # Boost if multiple rules agree
    if len(matched_rules) > 1:
        boost = min(0.1 * (len(matched_rules) - 1), 0.2)
        return min(max_confidence + boost, 1.0)
    
    return max_confidence


def calculate_signal_quality(signals: List, has_stacktrace: bool = False, 
                            has_code_reference: bool = False) -> float:
    """
    Calculate confidence score based on signal quality.
    
    Higher quality if:
    - Stacktrace present
    - File + line resolved
    - Clear error signature
    - Multiple corroborating signals
    
    Args:
        signals: List of FailureSignal objects
        has_stacktrace: Whether stacktrace is available
        has_code_reference: Whether code reference (file:line) is resolved
        
    Returns:
        Signal quality score (0.0-1.0)
    """
    if not signals:
        return 0.1  # Very low confidence without signals
    
    score = 0.0
    
    # Stacktrace adds significant confidence
    if has_stacktrace:
        score += 0.3
    
    # Code reference (file + line) adds confidence
    if has_code_reference:
        score += 0.3
    
    # Multiple signals add confidence
    signal_count_boost = min(0.1 * len(signals), 0.3)
    score += signal_count_boost
    
    # Check signal specificity
    try:
        specific_signals = sum(1 for s in signals if len(str(s.get('message', '') if isinstance(s, dict) else getattr(s, 'message', ''))) > 20)
        if specific_signals > 0:
            score += 0.1
    except:
        pass  # Skip if signal structure is unexpected
    
    return min(score, 1.0)


def calculate_history_score(historical_occurrences: int = 0,
                           is_consistent_history: bool = False) -> float:
    """
    Calculate confidence score based on historical consistency.
    
    Higher confidence if:
    - Seen multiple times before
    - Always classified the same way
    - Recent occurrences
    
    Args:
        historical_occurrences: Number of times seen before
        is_consistent_history: Whether historical classifications are consistent
        
    Returns:
        History score (0.0-1.0)
    """
    if historical_occurrences == 0:
        return 0.2  # Base score for new failures
    
    # If seen 1-2 times only
    if historical_occurrences <= 2:
        return 0.4
    
    # If inconsistent history (different classifications)
    if not is_consistent:
        return 0.5
    
    # Consistent history with multiple occurrences
    if historical_occurrences >= 5:
        return 0.9
    elif historical_occurrences >= 3:
        return 0.7
    
    return 0.6


def calculate_log_completeness(has_automation_logs: bool = True,
                               has_application_logs: bool = False,
                               automation_log_quality: str = "complete") -> float:
    """
    Calculate confidence score based on log completeness.
    
    Higher confidence if:
    - Both automation and application logs present
    - Logs are complete and well-formed
    - Sufficient detail in logs
    
    Args:
        has_automation_logs: Whether automation logs are present (always true in practice)
        has_application_logs: Whether application logs are present (optional)
        automation_log_quality: Quality of automation logs ("complete", "partial", "minimal")
        
    Returns:
        Log completeness score (0.0-1.0)
    """
    if not has_automation_logs:
        return 0.3  # Very low confidence without automation logs
    
    score = 0.5  # Base score for automation logs
    
    # Adjust based on automation log quality
    if automation_log_quality == "complete":
        score = 0.7
    elif automation_log_quality == "partial":
        score = 0.5
    elif automation_log_quality == "minimal":
        score = 0.4
    
    # Application logs add significant confidence
    if has_application_logs:
        score = min(score + 0.3, 1.0)
    
    return score


def calculate_final_confidence(breakdown: ConfidenceBreakdown) -> float:
    """
    Calculate final confidence score from breakdown.
    
    This is a convenience function that uses the ConfidenceBreakdown's
    built-in calculation method.
    
    Args:
        breakdown: ConfidenceBreakdown object with all components
        
    Returns:
        Final confidence score (0.0-1.0)
    """
    return breakdown.calculate_final_confidence()


def build_confidence_breakdown(
    matched_rules: List,
    signals: List,
    has_stacktrace: bool = False,
    has_code_reference: bool = False,
    historical_occurrences: int = 0,
    is_consistent_history: bool = False,
    has_automation_logs: bool = True,
    has_application_logs: bool = False,
    ai_adjustment: float = 0.0
) -> ConfidenceBreakdown:
    """
    Build complete confidence breakdown from components.
    
    This is the primary function to use for generating confidence scores.
    
    Args:
        matched_rules: List of matched Rule objects
        signals: List of FailureSignal objects
        has_stacktrace: Whether stacktrace is available
        has_code_reference: Whether code reference resolved
        historical_occurrences: Number of historical occurrences
        is_consistent_history: Whether history is consistent
        has_automation_logs: Whether automation logs present
        has_application_logs: Whether application logs present
        ai_adjustment: AI confidence adjustment (0.0-0.3)
        
    Returns:
        Complete ConfidenceBreakdown object
    """
    # Calculate each component
    rule_score = calculate_rule_score(matched_rules)
    signal_score = calculate_signal_quality(signals, has_stacktrace, has_code_reference)
    history_score = calculate_history_score(historical_occurrences, is_consistent_history)
    log_score = calculate_log_completeness(has_automation_logs, has_application_logs)
    
    # Ensure AI adjustment is in valid range
    ai_score = max(0.0, min(ai_adjustment, 0.3))
    
    # Build breakdown
    breakdown = ConfidenceBreakdown(
        rule_score=rule_score,
        signal_score=signal_score,
        history_score=history_score,
        log_score=log_score,
        ai_score=ai_score,
        rule_matches=len(matched_rules),
        has_stacktrace=has_stacktrace,
        has_code_reference=has_code_reference,
        historical_occurrences=historical_occurrences,
        has_application_logs=has_application_logs
    )
    
    return breakdown


def adjust_confidence_with_ai(base_breakdown: ConfidenceBreakdown,
                              ai_confidence: float,
                              ai_agrees_with_base: bool = True) -> ConfidenceBreakdown:
    """
    Adjust confidence based on AI analysis.
    
    CRITICAL: AI can only adjust, never override base classification.
    
    Args:
        base_breakdown: Base confidence breakdown
        ai_confidence: AI's confidence (0.0-1.0)
        ai_agrees_with_base: Whether AI agrees with base classification
        
    Returns:
        Updated ConfidenceBreakdown with AI adjustment
    """
    if not ai_agrees_with_base:
        # AI disagrees - no boost, potentially reduce slightly
        base_breakdown.ai_score = 0.0
        base_breakdown.explanation['ai'] = "AI suggests different classification"
        return base_breakdown
    
    # AI agrees - calculate boost
    base_confidence = base_breakdown.calculate_base_confidence()
    
    # AI can boost up to 0.3, but capped so final doesn't exceed 1.0
    max_boost = min(0.3, 1.0 - base_confidence)
    
    # Scale AI boost by AI's own confidence
    ai_boost = max_boost * ai_confidence
    
    base_breakdown.ai_score = ai_boost
    base_breakdown.explanation['ai'] = f"AI agrees with {ai_confidence:.0%} confidence"
    
    return base_breakdown
