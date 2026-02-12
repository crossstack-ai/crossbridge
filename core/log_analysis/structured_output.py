"""
Structured JSON Output Schema

Provides enterprise-grade structured output for test analysis results.
Includes clusters, severity, domain, confidence, and recommended actions.

Supports multiple output formats:
- Full detailed analysis
- Triage mode (top issues only)
- Summary only
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from core.log_analysis.clustering import FailureCluster, FailureSeverity, FailureDomain
from core.log_analysis.regression import ConfidenceScore, RegressionAnalysis
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.EXECUTION)


@dataclass
class ClusterOutput:
    """
    Structured output for a single failure cluster.
    
    Attributes:
        id: Unique cluster identifier
        root_cause: Root cause description
        occurrences: Number of failures in cluster
        severity: Severity level (critical/high/medium/low)
        domain: Failure domain (infra/environment/test_automation/product)
        confidence: Confidence score (0.0 to 1.0)
        affected_tests: List of affected test names
        affected_keywords: List of affected keywords
        error_patterns: Identified error patterns
        recommended_actions: List of recommended actions
        is_regression: Whether this is a new failure
        sample_error: Sample error message
    """
    id: str
    root_cause: str
    occurrences: int
    severity: str
    domain: str
    confidence: float
    affected_tests: List[str] = field(default_factory=list)
    affected_keywords: List[str] = field(default_factory=list)
    error_patterns: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    is_regression: bool = False
    sample_error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AnalysisSummary:
    """
    Summary statistics for the analysis.
    
    Attributes:
        total_tests: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        unique_issues: Number of unique root causes
        systemic: Whether systemic patterns detected
        regression_rate: Percentage of new failures
        analysis_timestamp: When analysis was performed
        test_duration: Test execution duration (if available)
    """
    total_tests: int
    passed: int
    failed: int
    skipped: int = 0
    unique_issues: int = 0
    systemic: bool = False
    regression_rate: Optional[float] = None
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    test_duration: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class StructuredAnalysisOutput:
    """
    Complete structured output for test analysis.
    
    Attributes:
        summary: High-level statistics
        clusters: List of failure clusters
        regression_analysis: Regression detection results (if available)
        systemic_patterns: List of systemic patterns detected
        top_recommendations: Top 3 recommended actions
        metadata: Additional metadata (version, config, etc.)
    """
    summary: AnalysisSummary
    clusters: List[ClusterOutput] = field(default_factory=list)
    regression_analysis: Optional[Dict] = None
    systemic_patterns: List[str] = field(default_factory=list)
    top_recommendations: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'summary': self.summary.to_dict(),
            'clusters': [c.to_dict() for c in self.clusters],
            'regression_analysis': self.regression_analysis,
            'systemic_patterns': self.systemic_patterns,
            'top_recommendations': self.top_recommendations,
            'metadata': self.metadata
        }


def generate_recommended_actions(
    cluster: FailureCluster,
    confidence: ConfidenceScore
) -> List[str]:
    """
    Generate recommended actions based on cluster characteristics.
    
    Args:
        cluster: FailureCluster to analyze
        confidence: ConfidenceScore for the cluster
        
    Returns:
        List of recommended action strings
    """
    actions = []
    
    # Domain-specific recommendations
    if cluster.domain == FailureDomain.INFRA:
        actions.append("Check infrastructure health and connectivity")
        actions.append("Verify SSH access and network configuration")
        if cluster.failure_count > 5:
            actions.append("This appears to be a widespread infra issue - escalate to DevOps team")
    
    elif cluster.domain == FailureDomain.ENVIRONMENT:
        actions.append("Verify environment configuration and dependencies")
        actions.append("Check config files and environment variables")
        if "module" in cluster.root_cause.lower() or "import" in cluster.root_cause.lower():
            actions.append("Install missing Python packages or dependencies")
    
    elif cluster.domain == FailureDomain.TEST_AUTOMATION:
        actions.append("Review test code for bugs or assertion issues")
        if "element" in cluster.root_cause.lower():
            actions.append("Update element locators or add explicit waits")
        if "index" in cluster.root_cause.lower() or "key" in cluster.root_cause.lower():
            actions.append("Fix test data access logic (IndexError/KeyError)")
    
    elif cluster.domain == FailureDomain.PRODUCT:
        actions.append("Investigate application code and business logic")
        if "http" in cluster.root_cause.lower() or "api" in cluster.root_cause.lower():
            actions.append("Check API endpoint health and backend services")
        if cluster.severity == FailureSeverity.CRITICAL:
            actions.append("URGENT: Critical product defect - assign to development team immediately")
    
    # Severity-based recommendations
    if cluster.severity == FailureSeverity.CRITICAL and not actions:
        actions.append("CRITICAL issue requires immediate attention")
        actions.append("Halt deployment until resolved")
    
    # Confidence-based recommendations
    if confidence.overall_score < 0.5:
        actions.append("Low confidence - requires manual investigation")
    
    # Use cluster's suggested fix if available
    if cluster.suggested_fix and cluster.suggested_fix not in actions:
        actions.append(cluster.suggested_fix)
    
    return actions[:5]  # Limit to top 5 actions


def build_cluster_output(
    cluster: FailureCluster,
    cluster_id: str,
    confidence: ConfidenceScore,
    is_regression: bool = False
) -> ClusterOutput:
    """
    Convert FailureCluster to structured ClusterOutput.
    
    Args:
        cluster: FailureCluster to convert
        cluster_id: Unique identifier for this cluster
        confidence: ConfidenceScore for the cluster
        is_regression: Whether this is a new failure
        
    Returns:
        ClusterOutput with structured data
    """
    # Generate recommended actions
    recommended_actions = generate_recommended_actions(cluster, confidence)
    
    # Get sample error
    sample_error = None
    if cluster.failures:
        first_failure = cluster.failures[0]
        error_msg = first_failure.error_message
        # Truncate if too long
        if len(error_msg) > 200:
            sample_error = error_msg[:197] + "..."
        else:
            sample_error = error_msg
    
    return ClusterOutput(
        id=cluster_id,
        root_cause=cluster.root_cause,
        occurrences=cluster.failure_count,
        severity=cluster.severity.value,
        domain=cluster.domain.value,
        confidence=confidence.overall_score,
        affected_tests=sorted(list(cluster.tests))[:10],  # Limit to 10
        affected_keywords=sorted(list(cluster.keywords))[:10],  # Limit to 10
        error_patterns=cluster.error_patterns,
        recommended_actions=recommended_actions,
        is_regression=is_regression,
        sample_error=sample_error
    )


def create_structured_output(
    clusters: Dict[str, FailureCluster],
    confidence_scores: Dict[str, ConfidenceScore],
    test_stats: Dict,
    regression_analysis: Optional[RegressionAnalysis] = None,
    systemic_patterns: Optional[List[str]] = None,
    metadata: Optional[Dict] = None
) -> StructuredAnalysisOutput:
    """
    Create complete structured output from analysis results.
    
    Args:
        clusters: Dictionary of failure clusters
        confidence_scores: Dictionary of confidence scores per cluster
        test_stats: Test statistics (total, passed, failed, etc.)
        regression_analysis: Optional regression analysis results
        systemic_patterns: Optional list of systemic patterns
        metadata: Optional metadata to include
        
    Returns:
        StructuredAnalysisOutput ready for JSON serialization
    """
    logger.debug(f"Creating structured output for {len(clusters)} clusters")
    
    # Create summary
    summary = AnalysisSummary(
        total_tests=test_stats.get('total_tests', 0),
        passed=test_stats.get('passed', 0),
        failed=test_stats.get('failed', 0),
        skipped=test_stats.get('skipped', 0),
        unique_issues=len(clusters),
        systemic=bool(systemic_patterns and len(systemic_patterns) > 0),
        regression_rate=regression_analysis.regression_rate if regression_analysis else None,
        test_duration=test_stats.get('duration')
    )
    
    # Convert clusters to structured output
    cluster_outputs = []
    new_failure_fingerprints = set()
    
    if regression_analysis:
        new_failure_fingerprints = set(regression_analysis.new_failures)
    
    for idx, (fingerprint, cluster) in enumerate(sorted(
        clusters.items(),
        key=lambda x: (
            {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[x[1].severity.value],
            -x[1].failure_count
        )
    ), 1):
        cluster_id = f"cluster_{idx}"
        confidence = confidence_scores.get(fingerprint, ConfidenceScore(
            overall_score=0.5,
            cluster_signal=0.5,
            domain_signal=0.5,
            pattern_signal=0.5
        ))
        
        is_regression = fingerprint in new_failure_fingerprints
        
        cluster_output = build_cluster_output(
            cluster=cluster,
            cluster_id=cluster_id,
            confidence=confidence,
            is_regression=is_regression
        )
        cluster_outputs.append(cluster_output)
    
    # Generate top recommendations (from top 3 clusters)
    top_recommendations = []
    for cluster_output in cluster_outputs[:3]:
        if cluster_output.recommended_actions:
            top_recommendations.extend(cluster_output.recommended_actions[:2])
    
    # Deduplicate and limit
    top_recommendations = list(dict.fromkeys(top_recommendations))[:5]
    
    # Add metadata
    output_metadata = metadata or {}
    output_metadata.update({
        'crossbridge_version': '0.2.1',
        'analysis_features': [
            'clustering',
            'severity_detection',
            'domain_classification',
            'confidence_scoring',
            'regression_detection'
        ]
    })
    
    return StructuredAnalysisOutput(
        summary=summary,
        clusters=cluster_outputs,
        regression_analysis=regression_analysis.to_dict() if regression_analysis else None,
        systemic_patterns=systemic_patterns or [],
        top_recommendations=top_recommendations,
        metadata=output_metadata
    )


def create_triage_output(
    structured_output: StructuredAnalysisOutput,
    max_clusters: int = 3
) -> Dict:
    """
    Create condensed triage output for CI dashboards.
    
    Shows only:
    - Top N root causes
    - Severity
    - Domain (ownership)
    - Recommended action
    
    Args:
        structured_output: Full structured output
        max_clusters: Maximum number of clusters to show
        
    Returns:
        Condensed dictionary for triage
    """
    triage = {
        'status': 'FAILED' if structured_output.summary.failed > 0 else 'PASSED',
        'total_tests': structured_output.summary.total_tests,
        'failed': structured_output.summary.failed,
        'unique_issues': structured_output.summary.unique_issues,
        'top_issues': []
    }
    
    for cluster in structured_output.clusters[:max_clusters]:
        issue = {
            'root_cause': cluster.root_cause,
            'severity': cluster.severity,
            'ownership': cluster.domain,
            'occurrences': cluster.occurrences,
            'recommended_action': cluster.recommended_actions[0] if cluster.recommended_actions else 'Investigate manually'
        }
        triage['top_issues'].append(issue)
    
    logger.info(f"Created triage output with {len(triage['top_issues'])} top issues")
    
    return triage
