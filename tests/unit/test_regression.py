"""
Unit Tests for Regression Detection and Enhanced Analysis

Tests the new analysis features:
- Regression detection (new vs recurring failures)
- Confidence scoring
- AI output sanitization
- Structured JSON output
- Triage mode
"""

import pytest
from core.log_analysis.regression import (
    compare_with_previous,
    compute_confidence_score,
    sanitize_ai_output,
    load_previous_run,
    RegressionAnalysis,
    ConfidenceScore
)
from core.log_analysis.structured_output import (
    create_structured_output,
    create_triage_output,
    generate_recommended_actions,
    build_cluster_output,
    ClusterOutput,
    AnalysisSummary
)
from core.log_analysis.clustering import (
    FailureCluster,
    ClusteredFailure,
    FailureSeverity,
    FailureDomain
)


class TestRegressionDetection:
    """Test regression detection functionality."""
    
    def test_compare_no_previous_failures(self):
        """Test comparison when previous run had no failures."""
        current = [{"fingerprint": "abc", "error": "Error A"}]
        previous = []
        
        analysis = compare_with_previous(current, previous)
        
        assert len(analysis.new_failures) == 1
        assert len(analysis.recurring_failures) == 0
        assert len(analysis.resolved_failures) == 0
        assert analysis.regression_rate == 100.0
    
    def test_compare_all_recurring(self):
        """Test comparison when all failures are recurring."""
        current = [
            {"fingerprint": "abc", "error": "Error A"},
            {"fingerprint": "def", "error": "Error B"}
        ]
        previous = [
            {"fingerprint": "abc", "error": "Error A"},
            {"fingerprint": "def", "error": "Error B"}
        ]
        
        analysis = compare_with_previous(current, previous)
        
        assert len(analysis.new_failures) == 0
        assert len(analysis.recurring_failures) == 2
        assert "abc" in analysis.recurring_failures
        assert "def" in analysis.recurring_failures
        assert analysis.regression_rate == 0.0
    
    def test_compare_mixed_scenario(self):
        """Test comparison with new, recurring, and resolved failures."""
        current = [
            {"fingerprint": "abc", "error": "Error A"},  # Recurring
            {"fingerprint": "new1", "error": "New Error"}  # New
        ]
        previous = [
            {"fingerprint": "abc", "error": "Error A"},  # Recurring
            {"fingerprint": "fixed", "error": "Fixed Error"}  # Resolved
        ]
        
        analysis = compare_with_previous(current, previous)
        
        assert len(analysis.new_failures) == 1
        assert "new1" in analysis.new_failures
        assert len(analysis.recurring_failures) == 1
        assert "abc" in analysis.recurring_failures
        assert len(analysis.resolved_failures) == 1
        assert "fixed" in analysis.resolved_failures
        assert analysis.regression_rate == 50.0  # 1 new out of 2 total
    
    def test_compare_with_root_cause_fallback(self):
        """Test comparison using root_cause when fingerprint not available."""
        current = [{"root_cause": "ElementNotFound"}]
        previous = [{"root_cause": "TimeoutError"}]
        
        analysis = compare_with_previous(current, previous, fingerprint_key="fingerprint")
        
        # Should use root_cause as fallback
        assert len(analysis.new_failures) == 1
        assert len(analysis.resolved_failures) == 1
    
    def test_regression_rate_calculation(self):
        """Test regression rate calculation."""
        current = [
            {"fingerprint": "new1"},
            {"fingerprint": "new2"},
            {"fingerprint": "new3"},
            {"fingerprint": "recurring1"}
        ]
        previous = [{"fingerprint": "recurring1"}]
        
        analysis = compare_with_previous(current, previous)
        
        # 3 new out of 4 total = 75%
        assert analysis.regression_rate == 75.0
    
    def test_empty_current_run(self):
        """Test comparison when current run has no failures."""
        current = []
        previous = [{"fingerprint": "abc"}]
        
        analysis = compare_with_previous(current, previous)
        
        assert len(analysis.new_failures) == 0
        assert len(analysis.recurring_failures) == 0
        assert len(analysis.resolved_failures) == 1
        assert analysis.regression_rate == 0.0


class TestConfidenceScoring:
    """Test confidence score calculation."""
    
    def test_high_confidence_large_cluster(self):
        """Test high confidence for large cluster with known domain."""
        cluster = FailureCluster(
            fingerprint="abc",
            root_cause="HTTP 500 Error",
            severity=FailureSeverity.CRITICAL,
            domain=FailureDomain.PRODUCT,
            failure_count=10,
            error_patterns=["Internal Server Error"]
        )
        
        confidence = compute_confidence_score(cluster, pattern_matched=True)
        
        assert confidence.overall_score >= 0.7  # High confidence
        assert confidence.cluster_signal >= 0.8  # Large cluster (10/5 = 2.0, capped at 1.0)
        assert confidence.domain_signal == 0.9  # Product domain
        assert confidence.pattern_signal == 0.8  # Pattern matched
    
    def test_low_confidence_unknown_domain(self):
        """Test low confidence for small cluster with unknown domain."""
        cluster = FailureCluster(
            fingerprint="xyz",
            root_cause="Generic Error",
            severity=FailureSeverity.LOW,
            domain=FailureDomain.UNKNOWN,
            failure_count=1
        )
        
        confidence = compute_confidence_score(cluster)
        
        assert confidence.overall_score <= 0.5  # Low confidence
        assert confidence.domain_signal == 0.3  # Unknown domain
    
    def test_confidence_with_ai_signal(self):
        """Test confidence calculation with AI signal."""
        cluster = FailureCluster(
            fingerprint="abc",
            root_cause="Error",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.PRODUCT,
            failure_count=3
        )
        
        confidence = compute_confidence_score(cluster, ai_score=0.95)
        
        assert confidence.ai_signal == 0.95
        assert confidence.overall_score > 0.5  # AI should boost confidence
    
    def test_confidence_domain_weights(self):
        """Test that different domains produce different confidence scores."""
        base_cluster = {
            "fingerprint": "abc",
            "root_cause": "Error",
            "severity": FailureSeverity.HIGH,
            "failure_count": 5
        }
        
        product_cluster = FailureCluster(**base_cluster, domain=FailureDomain.PRODUCT)
        unknown_cluster = FailureCluster(**base_cluster, domain=FailureDomain.UNKNOWN)
        
        product_score = compute_confidence_score(product_cluster)
        unknown_score = compute_confidence_score(unknown_cluster)
        
        assert product_score.overall_score > unknown_score.overall_score
        assert product_score.domain_signal > unknown_score.domain_signal
    
    def test_cluster_size_impact(self):
        """Test that cluster size impacts confidence score."""
        small_cluster = FailureCluster(
            fingerprint="abc",
            root_cause="Error",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.PRODUCT,
            failure_count=1
        )
        
        large_cluster = FailureCluster(
            fingerprint="def",
            root_cause="Error",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.PRODUCT,
            failure_count=10
        )
        
        small_score = compute_confidence_score(small_cluster)
        large_score = compute_confidence_score(large_cluster)
        
        assert large_score.cluster_signal > small_score.cluster_signal
        assert large_score.overall_score > small_score.overall_score


class TestAISanitizer:
    """Test AI output sanitization."""
    
    def test_remove_apology(self):
        """Test removal of AI apologies."""
        text = "I'm sorry, but the error indicates a network issue."
        cleaned = sanitize_ai_output(text)
        
        assert "I'm sorry" not in cleaned
        assert "error indicates" in cleaned.lower()
    
    def test_remove_ai_model_reference(self):
        """Test removal of AI model references."""
        text = "As an AI model, I recommend checking the logs."
        cleaned = sanitize_ai_output(text)
        
        assert "as an AI model" not in cleaned.lower()
        assert "recommend" in cleaned.lower()
    
    def test_remove_access_disclaimer(self):
        """Test removal of access disclaimers."""
        text = "I don't have access to your system, but based on the error..."
        cleaned = sanitize_ai_output(text)
        
        assert "I don't have access" not in cleaned
        assert "error" in cleaned.lower()
    
    def test_capitalize_first_letter(self):
        """Test that first letter is capitalized after cleanup."""
        text = "I'm sorry, the issue seems to be..."
        cleaned = sanitize_ai_output(text)
        
        # The sanitizer capitalizes first letter after removing phrases
        # Expected: "The issue seems to be..."
        assert len(cleaned) > 0
        assert cleaned[0].isupper() or not cleaned[0].isalpha()  # Allow non-alpha first char
    
    def test_multiple_phrases_removed(self):
        """Test removal of multiple blacklisted phrases."""
        text = "I'm sorry, but as an AI model, I cannot access your logs. However, the error suggests..."
        cleaned = sanitize_ai_output(text)
        
        assert "I'm sorry" not in cleaned
        assert "as an AI model" not in cleaned.lower()
        assert "cannot access" not in cleaned
        assert "error suggests" in cleaned.lower()
    
    def test_preserve_useful_content(self):
        """Test that useful content is preserved."""
        text = "The error indicates a database connection timeout. Check connection pool settings."
        cleaned = sanitize_ai_output(text)
        
        assert "database connection timeout" in cleaned
        assert "connection pool settings" in cleaned
    
    def test_empty_input(self):
        """Test handling of empty input."""
        assert sanitize_ai_output("") == ""
        assert sanitize_ai_output(None) is None


class TestStructuredOutput:
    """Test structured output generation."""
    
    def test_create_cluster_output(self):
        """Test creating structured cluster output."""
        from core.log_analysis.clustering import FailureCluster, ClusteredFailure
        
        cluster = FailureCluster(
            fingerprint="abc123",
            root_cause="HTTP 500 Internal Server Error",
            severity=FailureSeverity.CRITICAL,
            domain=FailureDomain.PRODUCT
        )
        cluster.failure_count = 5
        cluster.error_patterns = ["Internal Server Error", "HTTP 500"]
        cluster.suggested_fix = "Check backend service health"
        cluster.tests.add("Test Login")
        cluster.tests.add("Test Checkout")
        cluster.keywords.add("API Call")
        
        # Add sample failure
        cluster.failures.append(ClusteredFailure(
            test_name="Test Login",
            error_message="HTTP 500 Internal Server Error from /api/login",
            domain=FailureDomain.PRODUCT
        ))
        
        confidence = ConfidenceScore(
            overall_score=0.85,
            cluster_signal=0.9,
            domain_signal=0.9,
            pattern_signal=0.8
        )
        
        output = build_cluster_output(cluster, "cluster_1", confidence, is_regression=True)
        
        assert output.id == "cluster_1"
        assert output.root_cause == "HTTP 500 Internal Server Error"
        assert output.occurrences == 5
        assert output.severity == "critical"
        assert output.domain == "product"
        assert output.confidence == 0.85
        assert output.is_regression is True
        assert len(output.recommended_actions) > 0
        assert output.sample_error is not None
    
    def test_generate_recommended_actions_product(self):
        """Test recommended actions for product domain."""
        cluster = FailureCluster(
            fingerprint="abc",
            root_cause="HTTP 500 error",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.PRODUCT
        )
        cluster.failure_count = 3
        
        confidence = ConfidenceScore(0.8, 0.8, 0.8, 0.8)
        actions = generate_recommended_actions(cluster, confidence)
        
        assert len(actions) > 0
        assert any("application code" in action.lower() or "api" in action.lower() for action in actions)
    
    def test_generate_recommended_actions_infra(self):
        """Test recommended actions for infrastructure domain."""
        cluster = FailureCluster(
            fingerprint="abc",
            root_cause="SSH connection refused",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.INFRA
        )
        cluster.failure_count = 10
        
        confidence = ConfidenceScore(0.8, 0.8, 0.8, 0.8)
        actions = generate_recommended_actions(cluster, confidence)
        
        assert len(actions) > 0
        assert any("infrastructure" in action.lower() or "devops" in action.lower() for action in actions)
    
    def test_create_summary(self):
        """Test creating analysis summary."""
        summary = AnalysisSummary(
            total_tests=100,
            passed=90,
            failed=8,
            skipped=2,
            unique_issues=3,
            systemic=True,
            regression_rate=25.0
        )
        
        assert summary.total_tests == 100
        assert summary.failed == 8
        assert summary.unique_issues == 3
        assert summary.systemic is True
        assert summary.regression_rate == 25.0
    
    def test_create_triage_output(self):
        """Test creating triage output."""
        # Create mock structured output
        from core.log_analysis.structured_output import StructuredAnalysisOutput
        
        summary = AnalysisSummary(
            total_tests=50,
            passed=45,
            failed=5,
            unique_issues=2
        )
        
        cluster1 = ClusterOutput(
            id="cluster_1",
            root_cause="API Error",
            occurrences=3,
            severity="high",
            domain="product",
            confidence=0.9,
            recommended_actions=["Check API health", "Review logs"]
        )
        
        cluster2 = ClusterOutput(
            id="cluster_2",
            root_cause="Element not found",
            occurrences=2,
            severity="medium",
            domain="test_automation",
            confidence=0.7,
            recommended_actions=["Update locators"]
        )
        
        structured_output = StructuredAnalysisOutput(
            summary=summary,
            clusters=[cluster1, cluster2]
        )
        
        triage = create_triage_output(structured_output, max_clusters=2)
        
        assert triage['status'] == 'FAILED'
        assert triage['total_tests'] == 50
        assert triage['failed'] == 5
        assert triage['unique_issues'] == 2
        assert len(triage['top_issues']) == 2
        assert triage['top_issues'][0]['root_cause'] == "API Error"
        assert triage['top_issues'][0]['ownership'] == "product"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_confidence_score_bounds(self):
        """Test that confidence scores are bounded [0, 1]."""
        cluster = FailureCluster(
            fingerprint="abc",
            root_cause="Error",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.PRODUCT,
            failure_count=100  # Very large
        )
        
        confidence = compute_confidence_score(cluster, ai_score=1.5)  # Out of bounds
        
        assert 0.0 <= confidence.overall_score <= 1.0
        assert 0.0 <= confidence.cluster_signal <= 1.0
        assert confidence.ai_signal == 1.0  # Should be clamped
    
    def test_empty_cluster_list(self):
        """Test handling of empty cluster list."""
        analysis = compare_with_previous([], [])
        
        assert analysis.total_current == 0
        assert analysis.total_previous == 0
        assert analysis.regression_rate == 0.0
    
    def test_sanitize_preserves_newlines(self):
        """Test that sanitizer preserves useful formatting."""
        text = "Error details:\nLine 1: Issue A\nLine 2: Issue B"
        cleaned = sanitize_ai_output(text)
        
        # Should preserve structure
        assert "Error details" in cleaned
        assert "Issue A" in cleaned
        assert "Issue B" in cleaned
