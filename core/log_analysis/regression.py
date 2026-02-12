"""
Regression Detection & Analysis

Compares current test run with previous runs to identify:
- New failures (not seen before)
- Recurring failures (seen in previous runs)
- Regression trends
- Confidence scoring for root cause analysis

Integrates with existing clustering module for comprehensive failure analysis.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from core.logging import get_logger, LogCategory
from core.log_analysis.clustering import (
    FailureCluster, 
    ClusteredFailure,
    FailureDomain,
    FailureSeverity
)

# Get logger with EXECUTION category for test analysis
logger = get_logger(__name__, category=LogCategory.EXECUTION)


@dataclass
class RegressionAnalysis:
    """
    Results of comparing current run with previous run(s).
    
    Attributes:
        new_failures: Failures not seen in previous runs
        recurring_failures: Failures that appeared in previous runs
        resolved_failures: Failures from previous run that are now fixed
        regression_rate: Percentage of new failures vs total
        total_current: Total failures in current run
        total_previous: Total failures in previous run
    """
    new_failures: List[str] = field(default_factory=list)
    recurring_failures: List[str] = field(default_factory=list)
    resolved_failures: List[str] = field(default_factory=list)
    regression_rate: float = 0.0
    total_current: int = 0
    total_previous: int = 0
    comparison_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ConfidenceScore:
    """
    Confidence score for a failure cluster analysis.
    
    Combines multiple signals to determine confidence in root cause identification:
    - Cluster size (larger = more confident)
    - Domain classification confidence
    - Pattern matching strength
    - AI signal (if available)
    
    Attributes:
        overall_score: Final confidence score (0.0 to 1.0)
        cluster_signal: Confidence from cluster size
        domain_signal: Confidence from domain classification
        pattern_signal: Confidence from pattern matching
        ai_signal: Confidence from AI analysis (optional)
        components: Breakdown of score components
    """
    overall_score: float
    cluster_signal: float
    domain_signal: float
    pattern_signal: float
    ai_signal: Optional[float] = None
    components: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def compare_with_previous(
    current_failures: List[Dict],
    previous_failures: List[Dict],
    fingerprint_key: str = "fingerprint"
) -> RegressionAnalysis:
    """
    Compare current test run with previous run to detect regressions.
    
    Identifies:
    - New failures (not in previous run)
    - Recurring failures (in both runs)
    - Resolved failures (in previous but not current)
    
    Args:
        current_failures: List of failure dictionaries from current run
        previous_failures: List of failure dictionaries from previous run
        fingerprint_key: Key to use for unique identification (default: "fingerprint")
        
    Returns:
        RegressionAnalysis with comparison results
        
    Examples:
        >>> current = [{"fingerprint": "abc", "error": "Error A"}]
        >>> previous = [{"fingerprint": "xyz", "error": "Error B"}]
        >>> analysis = compare_with_previous(current, previous)
        >>> analysis.new_failures
        ['abc']
        >>> analysis.resolved_failures
        ['xyz']
    """
    logger.debug(
        f"Starting regression analysis: {len(current_failures)} current, "
        f"{len(previous_failures)} previous failures"
    )
    
    # Extract fingerprints or root causes for comparison
    current_set = set()
    previous_set = set()
    
    for failure in current_failures:
        key = failure.get(fingerprint_key) or failure.get("root_cause", str(failure))
        current_set.add(key)
    
    for failure in previous_failures:
        key = failure.get(fingerprint_key) or failure.get("root_cause", str(failure))
        previous_set.add(key)
    
    # Calculate sets
    new_failures = list(current_set - previous_set)
    recurring_failures = list(current_set & previous_set)
    resolved_failures = list(previous_set - current_set)
    
    # Calculate regression rate
    total_current = len(current_set)
    regression_rate = (len(new_failures) / total_current * 100) if total_current > 0 else 0.0
    
    analysis = RegressionAnalysis(
        new_failures=new_failures,
        recurring_failures=recurring_failures,
        resolved_failures=resolved_failures,
        regression_rate=round(regression_rate, 2),
        total_current=total_current,
        total_previous=len(previous_set)
    )
    
    logger.info(
        f"Regression analysis complete: {len(new_failures)} new, "
        f"{len(recurring_failures)} recurring, {len(resolved_failures)} resolved "
        f"(regression rate: {analysis.regression_rate}%)"
    )
    
    return analysis


def load_previous_run(previous_file_path: str) -> Optional[List[Dict]]:
    """
    Load previous run data from JSON file.
    
    Args:
        previous_file_path: Path to previous run JSON file
        
    Returns:
        List of failure dictionaries or None if file not found/invalid
    """
    try:
        path = Path(previous_file_path)
        if not path.exists():
            logger.warning(f"Previous run file not found: {previous_file_path}")
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract failures from different possible structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Try common keys
            for key in ['failures', 'clusters', 'failed_keywords', 'results']:
                if key in data and isinstance(data[key], list):
                    return data[key]
        
        logger.warning(f"Could not extract failures from previous run file: {previous_file_path}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading previous run file: {e}")
        return None


def compute_confidence_score(
    cluster: FailureCluster,
    ai_score: Optional[float] = None,
    pattern_matched: bool = False
) -> ConfidenceScore:
    """
    Compute confidence score for a failure cluster.
    
    Combines multiple signals:
    - Cluster size (more occurrences = higher confidence)
    - Domain classification (known domain = higher confidence)
    - Pattern matching (matched pattern = higher confidence)
    - AI signal (if available)
    
    Args:
        cluster: FailureCluster to score
        ai_score: Optional AI confidence score (0.0 to 1.0)
        pattern_matched: Whether cluster matched a known pattern
        
    Returns:
        ConfidenceScore with breakdown
        
    Examples:
        >>> cluster = FailureCluster(
        ...     fingerprint="abc",
        ...     root_cause="Error",
        ...     severity=FailureSeverity.HIGH,
        ...     failure_count=10
        ... )
        >>> score = compute_confidence_score(cluster)
        >>> score.overall_score >= 0.5
        True
    """
    # Cluster size signal (normalize by max expected size)
    # More failures = more confident this is a real pattern
    cluster_signal = min(cluster.failure_count / 5.0, 1.0)
    
    # Domain signal (higher confidence for known domains)
    domain_confidence_map = {
        FailureDomain.PRODUCT: 0.9,        # Clear product issue
        FailureDomain.INFRA: 0.85,         # Clear infrastructure issue
        FailureDomain.TEST_AUTOMATION: 0.8, # Clear test issue
        FailureDomain.ENVIRONMENT: 0.75,   # Clear environment issue
        FailureDomain.UNKNOWN: 0.3         # Low confidence for unknown
    }
    domain_signal = domain_confidence_map.get(cluster.domain, 0.5)
    
    # Pattern matching signal
    pattern_signal = 0.8 if (pattern_matched or cluster.error_patterns) else 0.4
    
    # Calculate weighted average
    weights = {
        'cluster': 0.3,
        'domain': 0.3,
        'pattern': 0.2,
        'ai': 0.2
    }
    
    # Adjust weights if no AI score
    if ai_score is None:
        weights = {
            'cluster': 0.4,
            'domain': 0.35,
            'pattern': 0.25,
            'ai': 0.0
        }
        ai_signal_value = 0.0
    else:
        ai_signal_value = max(0.0, min(1.0, ai_score))  # Clamp to [0, 1]
    
    overall = (
        cluster_signal * weights['cluster'] +
        domain_signal * weights['domain'] +
        pattern_signal * weights['pattern'] +
        ai_signal_value * weights['ai']
    )
    
    confidence = ConfidenceScore(
        overall_score=round(overall, 2),
        cluster_signal=round(cluster_signal, 2),
        domain_signal=round(domain_signal, 2),
        pattern_signal=round(pattern_signal, 2),
        ai_signal=round(ai_signal_value, 2) if ai_score is not None else None,
        components={
            'cluster_weight': weights['cluster'],
            'domain_weight': weights['domain'],
            'pattern_weight': weights['pattern'],
            'ai_weight': weights['ai']
        }
    )
    
    logger.debug(
        f"Computed confidence score {confidence.overall_score} for cluster "
        f"(size={cluster.failure_count}, domain={cluster.domain.value})"
    )
    
    return confidence


def sanitize_ai_output(text: str) -> str:
    """
    Remove AI disclaimers and redundant phrases from AI-generated text.
    
    Cleans up common AI model artifacts like:
    - Apologies ("I'm sorry")
    - Model disclaimers ("as an AI model")
    - Access limitations ("I don't have access")
    - Redundant repetitions
    
    Args:
        text: Raw AI-generated text
        
    Returns:
        Cleaned text without disclaimers
        
    Examples:
        >>> sanitize_ai_output("I'm sorry, but the error indicates...")
        'The error indicates...'
        
        >>> sanitize_ai_output("As an AI model, I recommend...")
        'I recommend...'
    """
    if not text:
        return text
    
    # Phrases to remove
    blacklist = [
        "I'm sorry",
        "I am sorry",
        "as an AI model",
        "as an AI language model",
        "as an artificial intelligence",
        "I don't have access",
        "I do not have access",
        "I cannot access",
        "I'm unable to access",
        "Unfortunately, I cannot",
        "I apologize",
        "I must clarify",
        "It's important to note that I",
        "Please note that I",
        "I should mention that I"
    ]
    
    cleaned = text
    
    # Remove blacklisted phrases (case-insensitive)
    for phrase in blacklist:
        # Remove phrase and any trailing punctuation/space
        import re
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        cleaned = pattern.sub('', cleaned)
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Clean up spaces before punctuation
    cleaned = re.sub(r'\s+([.,;:!?])', r'\1', cleaned)
    
    # Capitalize first letter if needed
    cleaned = cleaned.strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    
    logger.debug(f"Sanitized AI output: {len(text)} -> {len(cleaned)} chars")
    
    return cleaned
