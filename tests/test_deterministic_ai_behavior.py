"""
Comprehensive tests for Deterministic + AI Behavior System.

Tests cover:
1. Deterministic classifier (all rules)
2. AI enrichment (success and failure cases)
3. Fallback behavior
4. Configuration
5. Metrics
6. End-to-end integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from core.intelligence.deterministic_classifier import (
    DeterministicClassifier,
    SignalData,
    DeterministicResult,
    ClassificationLabel
)
from core.intelligence.ai_enricher import (
    AIEnricher,
    AIEnricherConfig,
    AIResult,
    FinalResult,
    safe_ai_enrich,
    merge_results
)
from core.intelligence.intelligence_engine import (
    IntelligenceEngine,
    classify_test
)
from core.intelligence.intelligence_config import (
    IntelligenceConfig,
    DeterministicConfig,
    AIBehaviorConfig
)
from core.intelligence.intelligence_metrics import (
    IntelligenceMetrics,
    MetricsTracker,
    MetricNames
)


# ============================================================================
# Deterministic Classifier Tests
# ============================================================================


class TestDeterministicClassifier:
    """Test deterministic classification rules."""
    
    def test_new_test_no_history(self):
        """Test: New test with no historical data."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_login",
            test_status="pass",
            total_runs=0
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.NEW_TEST
        assert result.confidence == 1.0
        assert "No historical" in result.reasons[0]
        assert "new_test" in result.applied_rules
    
    def test_new_test_limited_history(self):
        """Test: New test with very limited history."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_login",
            test_status="pass",
            total_runs=2
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.NEW_TEST
        assert result.confidence == 0.8
        assert "Limited history" in result.reasons[0]
    
    def test_flaky_with_retry(self):
        """Test: Flaky test detected via retry behavior."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_search",
            test_status="fail",
            retry_count=2,
            final_status="pass",
            total_runs=10
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.FLAKY
        assert result.confidence >= 0.8
        assert "retries" in result.reasons[0].lower()
        assert "flaky_retry" in result.applied_rules
    
    def test_regression_code_change_failure(self):
        """Test: Regression detected when code changes and test fails."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_checkout",
            test_status="fail",
            code_changed=True,
            consecutive_passes=10,
            total_runs=15
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.REGRESSION
        assert result.confidence >= 0.7
        assert "Code changed" in result.reasons[0]
        assert "regression" in result.applied_rules[0]
    
    def test_unstable_high_failure_rate(self):
        """Test: Unstable test with high failure rate."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_payment",
            test_status="fail",
            historical_failure_rate=0.5,  # 50% failure rate
            total_runs=20
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.UNSTABLE
        assert result.confidence >= 0.6
        assert "High failure rate" in result.reasons[0]
        assert "unstable" in result.applied_rules[0]
    
    def test_flaky_moderate_failure_rate(self):
        """Test: Flaky test with moderate failure rate."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_api",
            test_status="pass",
            historical_failure_rate=0.15,  # 15% failure rate
            total_runs=20
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.FLAKY
        assert result.confidence >= 0.65
        assert "Intermittent" in result.reasons[0]
        assert "flaky" in result.applied_rules[0]
    
    def test_stable_low_failure_rate(self):
        """Test: Stable test with low failure rate."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_homepage",
            test_status="pass",
            historical_failure_rate=0.02,  # 2% failure rate
            total_runs=50
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.STABLE
        assert result.confidence >= 0.75
        assert "low failure" in result.reasons[0].lower()
        assert "stable" in result.applied_rules[0]
    
    def test_stable_perfect_pass_rate(self):
        """Test: Stable test with perfect pass rate."""
        classifier = DeterministicClassifier()
        signal = SignalData(
            test_name="test_homepage",
            test_status="pass",
            historical_failure_rate=0.0,
            total_runs=100
        )
        
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.STABLE
        assert result.confidence >= 0.75
        assert "Perfect" in result.reasons[0] or "consecutive" in result.reasons[0].lower()
    
    def test_batch_classify(self):
        """Test: Batch classification of multiple tests."""
        classifier = DeterministicClassifier()
        signals = [
            SignalData(test_name="test1", test_status="pass", total_runs=0),
            SignalData(test_name="test2", test_status="pass", retry_count=1, final_status="pass", total_runs=5),
            SignalData(test_name="test3", test_status="pass", historical_failure_rate=0.5, total_runs=10),
        ]
        
        results = classifier.batch_classify(signals)
        
        assert len(results) == 3
        assert results[0].label == ClassificationLabel.NEW_TEST
        assert results[1].label == ClassificationLabel.FLAKY
        assert results[2].label == ClassificationLabel.UNSTABLE
    
    def test_custom_thresholds(self):
        """Test: Classifier with custom threshold configuration."""
        config = {
            'flaky_threshold': 0.2,  # 20% instead of default 10%
            'unstable_threshold': 0.5,  # 50% instead of default 40%
        }
        classifier = DeterministicClassifier(config=config)
        
        # Should be stable (below 20%)
        signal = SignalData(
            test_name="test",
            test_status="pass",
            historical_failure_rate=0.15,
            total_runs=20
        )
        
        result = classifier.classify(signal)
        assert result.label == ClassificationLabel.STABLE


# ============================================================================
# AI Enrichment Tests
# ============================================================================


class TestAIEnricher:
    """Test AI enrichment layer."""
    
    def test_enrichment_disabled(self):
        """Test: AI enrichment disabled via config."""
        config = AIEnricherConfig(config={'enabled': False})
        enricher = AIEnricher(config=config)
        
        det_result = DeterministicResult(
            label=ClassificationLabel.FLAKY,
            confidence=0.8,
            reasons=["Test required retries"]
        )
        signal = SignalData(test_name="test", test_status="pass")
        
        ai_result = enricher.enrich(det_result, signal)
        
        assert ai_result is None
    
    def test_enrichment_no_analyzer(self):
        """Test: No AI analyzer configured."""
        enricher = AIEnricher(ai_analyzer=None)
        
        det_result = DeterministicResult(
            label=ClassificationLabel.FLAKY,
            confidence=0.8,
            reasons=["Test required retries"]
        )
        signal = SignalData(test_name="test", test_status="pass")
        
        ai_result = enricher.enrich(det_result, signal)
        
        assert ai_result is None
    
    def test_safe_ai_enrich_handles_exception(self):
        """Test: safe_ai_enrich handles exceptions gracefully."""
        mock_enricher = Mock()
        mock_enricher.enrich.side_effect = Exception("AI service down")
        
        det_result = DeterministicResult(
            label=ClassificationLabel.FLAKY,
            confidence=0.8,
            reasons=[]
        )
        signal = SignalData(test_name="test", test_status="pass")
        
        # Should NOT raise exception
        result = safe_ai_enrich(det_result, signal, mock_enricher)
        
        assert result is None
    
    def test_merge_results_deterministic_only(self):
        """Test: Merge with only deterministic result (no AI)."""
        det_result = DeterministicResult(
            label=ClassificationLabel.STABLE,
            confidence=0.9,
            reasons=["Low failure rate"]
        )
        signal = SignalData(test_name="test_login", test_status="pass")
        
        final = merge_results(det_result, signal, ai_result=None)
        
        assert final.label == "stable"
        assert final.deterministic_confidence == 0.9
        assert final.ai_enrichment is None
        assert final.test_name == "test_login"
    
    def test_merge_results_with_ai(self):
        """Test: Merge with both deterministic and AI results."""
        det_result = DeterministicResult(
            label=ClassificationLabel.FLAKY,
            confidence=0.8,
            reasons=["Intermittent failures"]
        )
        ai_result = AIResult(
            insights=["Possible timeout issue"],
            suggested_actions=["Increase timeout"],
            confidence=0.7
        )
        signal = SignalData(test_name="test_api", test_status="pass")
        
        final = merge_results(det_result, signal, ai_result)
        
        assert final.label == "flaky"
        assert final.deterministic_confidence == 0.8
        assert final.ai_enrichment is not None
        assert len(final.ai_enrichment.insights) > 0
    
    def test_enrichment_metrics_tracking(self):
        """Test: Enrichment tracks metrics correctly."""
        enricher = AIEnricher(ai_analyzer=None)
        
        det_result = DeterministicResult(
            label=ClassificationLabel.FLAKY,
            confidence=0.8,
            reasons=[]
        )
        signal = SignalData(test_name="test", test_status="pass")
        
        # Call multiple times
        for _ in range(3):
            enricher.enrich(det_result, signal)
        
        metrics = enricher.get_metrics()
        assert metrics['attempted'] == 3


# ============================================================================
# Intelligence Engine Tests
# ============================================================================


class TestIntelligenceEngine:
    """Test end-to-end intelligence engine."""
    
    def test_classify_always_returns_result(self):
        """Test: classify() always returns a result."""
        engine = IntelligenceEngine()
        signal = SignalData(
            test_name="test",
            test_status="pass",
            total_runs=10,
            historical_failure_rate=0.0
        )
        
        result = engine.classify(signal)
        
        assert result is not None
        assert result.label is not None
        assert result.deterministic_confidence >= 0
    
    def test_classify_with_ai_disabled(self):
        """Test: Classification works with AI disabled."""
        config = IntelligenceConfig()
        config.ai.enabled = False
        
        engine = IntelligenceEngine(config=config)
        signal = SignalData(
            test_name="test",
            test_status="pass",
            retry_count=1,
            final_status="pass",
            total_runs=5
        )
        
        result = engine.classify(signal)
        
        assert result.label == "flaky"
        assert result.ai_enrichment is None
    
    def test_batch_classify(self):
        """Test: Batch classification."""
        engine = IntelligenceEngine()
        signals = [
            SignalData(test_name="test1", test_status="pass", total_runs=0),
            SignalData(test_name="test2", test_status="pass", total_runs=20, historical_failure_rate=0.0),
        ]
        
        results = engine.batch_classify(signals)
        
        assert len(results) == 2
        assert results[0].label == "new_test"
        assert results[1].label == "stable"
    
    def test_get_health(self):
        """Test: Health check returns status."""
        engine = IntelligenceEngine()
        
        health = engine.get_health()
        
        assert health['status'] == 'operational'
        assert 'deterministic' in health
        assert 'ai_enrichment' in health
        assert health['deterministic']['status'] == 'healthy'
    
    def test_get_metrics(self):
        """Test: Metrics retrieval."""
        engine = IntelligenceEngine()
        
        # Run some classifications
        signal = SignalData(test_name="test", test_status="pass", total_runs=10)
        engine.classify(signal)
        
        metrics = engine.get_metrics()
        
        assert 'total_classifications' in metrics
        assert metrics['total_classifications'] >= 1


# ============================================================================
# Configuration Tests
# ============================================================================


class TestIntelligenceConfig:
    """Test configuration loading and management."""
    
    def test_default_config(self):
        """Test: Default configuration values."""
        config = IntelligenceConfig()
        
        assert config.deterministic.flaky_threshold == 0.1
        assert config.deterministic.unstable_threshold == 0.4
        assert config.ai.enabled is True
        assert config.ai.timeout_ms == 2000
        assert config.ai.fail_open is True
    
    def test_config_to_dict(self):
        """Test: Configuration serialization."""
        config = IntelligenceConfig()
        config_dict = config.to_dict()
        
        assert 'deterministic' in config_dict
        assert 'ai' in config_dict
        assert 'observability' in config_dict
    
    def test_environment_variable_override(self):
        """Test: Environment variables override defaults."""
        import os
        
        os.environ['CROSSBRIDGE_AI_ENABLED'] = 'false'
        os.environ['CROSSBRIDGE_AI_TIMEOUT_MS'] = '5000'
        
        try:
            config = IntelligenceConfig()
            
            assert config.ai.enabled is False
            assert config.ai.timeout_ms == 5000
        finally:
            # Cleanup
            os.environ.pop('CROSSBRIDGE_AI_ENABLED', None)
            os.environ.pop('CROSSBRIDGE_AI_TIMEOUT_MS', None)


# ============================================================================
# Metrics Tests
# ============================================================================


class TestIntelligenceMetrics:
    """Test metrics collection."""
    
    def test_increment_counter(self):
        """Test: Counter increment."""
        metrics = IntelligenceMetrics()
        
        metrics.increment("test.counter")
        metrics.increment("test.counter")
        metrics.increment("test.counter", value=3)
        
        assert metrics.get_counter("test.counter") == 5
    
    def test_record_latency(self):
        """Test: Latency recording and percentiles."""
        metrics = IntelligenceMetrics()
        
        for i in range(100):
            metrics.record_latency("test.latency", float(i))
        
        p50 = metrics.get_latency_percentile("test.latency", 50)
        p95 = metrics.get_latency_percentile("test.latency", 95)
        
        assert p50 is not None
        assert p95 is not None
        assert p95 > p50
    
    def test_metrics_with_labels(self):
        """Test: Metrics with labels."""
        metrics = IntelligenceMetrics()
        
        metrics.increment("classifications", labels={"label": "flaky"})
        metrics.increment("classifications", labels={"label": "stable"})
        metrics.increment("classifications", labels={"label": "flaky"})
        
        flaky_count = metrics.get_counter("classifications", labels={"label": "flaky"})
        stable_count = metrics.get_counter("classifications", labels={"label": "stable"})
        
        assert flaky_count == 2
        assert stable_count == 1
    
    def test_metrics_tracker(self):
        """Test: High-level metrics tracker."""
        tracker = MetricsTracker()
        
        tracker.track_deterministic_classification("flaky", 0.8, 10.5)
        tracker.track_deterministic_classification("stable", 0.9, 8.2)
        
        summary = tracker.get_summary()
        
        assert summary['total_classifications'] == 2


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_classification_pipeline(self):
        """Test: Complete classification flow."""
        # Create engine with custom config
        config = IntelligenceConfig()
        config.ai.enabled = False  # Disable AI for predictable testing
        
        engine = IntelligenceEngine(config=config)
        
        # Classify various test scenarios
        test_cases = [
            (SignalData(test_name="new_test", test_status="pass", total_runs=0), "new_test"),
            (SignalData(test_name="flaky", test_status="pass", retry_count=1, final_status="pass", total_runs=5), "flaky"),
            (SignalData(test_name="stable", test_status="pass", historical_failure_rate=0.0, total_runs=50), "stable"),
            (SignalData(test_name="unstable", test_status="fail", historical_failure_rate=0.6, total_runs=20), "unstable"),
        ]
        
        for signal, expected_label in test_cases:
            result = engine.classify(signal)
            assert result.label == expected_label, f"Expected {expected_label}, got {result.label}"
            assert result.deterministic_confidence > 0
            assert len(result.deterministic_reasons) > 0
    
    def test_convenience_function(self):
        """Test: Convenience classify_test function."""
        result = classify_test(
            test_name="test_login",
            test_status="pass",
            retry_count=2,
            final_status="pass",
            total_runs=10
        )
        
        assert result.label == "flaky"
        assert result.test_name == "test_login"
    
    def test_ai_failure_does_not_block(self):
        """Test: AI failure does not prevent classification."""
        # Create mock AI analyzer that always fails
        mock_analyzer = Mock()
        mock_analyzer.analyze.side_effect = Exception("AI service unavailable")
        
        config = IntelligenceConfig()
        config.ai.enabled = True
        config.ai.fail_open = True
        
        engine = IntelligenceEngine(config=config, ai_analyzer=mock_analyzer)
        signal = SignalData(
            test_name="test",
            test_status="pass",
            total_runs=10,
            historical_failure_rate=0.0
        )
        
        # Should still get deterministic result
        result = engine.classify(signal)
        
        assert result is not None
        assert result.label == "stable"
        assert result.ai_enrichment is None
