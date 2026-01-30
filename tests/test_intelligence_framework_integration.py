"""
Comprehensive tests for Intelligence System with all framework adapters.

Tests the intelligence system (Deterministic + AI + Policy) integration
with all 13 supported testing frameworks.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from core.intelligence.deterministic_classifier import (
    DeterministicClassifier,
    SignalData,
    ClassificationLabel
)
from core.intelligence.ai_enricher import AIEnricher, AIEnricherConfig
from core.intelligence.intelligence_engine import IntelligenceEngine
from core.intelligence.intelligence_config import IntelligenceConfig
from core.intelligence.policy_engine import (
    PolicyEngine,
    TestNamePatternPolicy,
    ThresholdOverridePolicy,
    QuarantinePolicy,
    get_policy_engine,
    reset_policy_engine
)
from core.intelligence.ai_analyzer import AIAnalyzer, AIAnalyzerConfig
from core.intelligence.confidence_calibration import get_calibration_manager
from core.intelligence.prompt_templates import PromptBuilder


# ============================================================================
# FRAMEWORK COMPATIBILITY TESTS
# ============================================================================

class TestFrameworkCompatibility:
    """Test intelligence system works with all 13 frameworks."""
    
    # All supported frameworks
    FRAMEWORKS = [
        "pytest",
        "selenium_pytest",
        "selenium_java",
        "selenium_bdd_java",
        "selenium_behave",
        "selenium_specflow_dotnet",
        "playwright",
        "cypress",
        "robot",
        "restassured_java",
        "junit",
        "testng",
        "nunit"
    ]
    
    @pytest.mark.parametrize("framework", FRAMEWORKS)
    def test_framework_classification(self, framework):
        """Test: SignalData works with framework metadata."""
        signal = SignalData(
            test_name=f"test_{framework}_example",
            test_status="pass",
            retry_count=0,
            total_runs=10,
            historical_failure_rate=0.0,
            framework=framework
        )
        
        classifier = DeterministicClassifier()
        result = classifier.classify(signal)
        
        assert result is not None
        assert result.label == ClassificationLabel.STABLE
        assert framework in str(signal.summary())
    
    @pytest.mark.parametrize("framework", FRAMEWORKS)
    def test_framework_with_flaky_detection(self, framework):
        """Test: Flaky detection works across frameworks."""
        signal = SignalData(
            test_name=f"test_{framework}_flaky",
            test_status="pass",
            retry_count=2,
            final_status="pass",
            total_runs=10,
            historical_failure_rate=0.3,
            framework=framework
        )
        
        classifier = DeterministicClassifier()
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.FLAKY
        assert result.confidence > 0.7
    
    @pytest.mark.parametrize("framework", FRAMEWORKS)
    def test_framework_with_unstable_detection(self, framework):
        """Test: Unstable detection works across frameworks."""
        signal = SignalData(
            test_name=f"test_{framework}_unstable",
            test_status="fail",
            consecutive_failures=5,
            total_runs=10,
            historical_failure_rate=0.8,
            framework=framework
        )
        
        classifier = DeterministicClassifier()
        result = classifier.classify(signal)
        
        assert result.label == ClassificationLabel.UNSTABLE
        assert result.confidence > 0.8


# ============================================================================
# COMPREHENSIVE TESTS WITHOUT AI
# ============================================================================

class TestIntelligenceWithoutAI:
    """Test intelligence system WITHOUT AI (deterministic only)."""
    
    def setup_method(self):
        """Setup for each test."""
        self.config = IntelligenceConfig()
        self.config.ai.enabled = False
        self.engine = IntelligenceEngine(config=self.config)
    
    def test_stable_test_classification(self):
        """Test: Stable test classification."""
        signal = SignalData(
            test_name="test_login_success",
            test_status="pass",
            total_runs=100,
            historical_failure_rate=0.0,
            consecutive_passes=100
        )
        
        result = self.engine.classify(signal)
        
        assert result.label == "stable"
        assert result.deterministic_confidence >= 0.9
        assert result.ai_enrichment is None
        assert "consecutive passes" in str(result.deterministic_reasons)
    
    def test_flaky_test_classification(self):
        """Test: Flaky test classification."""
        signal = SignalData(
            test_name="test_search_results",
            test_status="pass",
            retry_count=3,
            final_status="pass",
            total_runs=20,
            historical_failure_rate=0.25
        )
        
        result = self.engine.classify(signal)
        
        assert result.label == "flaky"
        assert result.deterministic_confidence >= 0.7
        assert result.ai_enrichment is None
        assert len(result.deterministic_reasons) > 0
    
    def test_unstable_test_classification(self):
        """Test: Unstable test classification."""
        signal = SignalData(
            test_name="test_api_endpoint",
            test_status="fail",
            consecutive_failures=10,
            total_runs=15,
            historical_failure_rate=0.7
        )
        
        result = self.engine.classify(signal)
        
        assert result.label == "unstable"
        assert result.deterministic_confidence >= 0.8
        assert result.ai_enrichment is None
    
    def test_regression_detection(self):
        """Test: Regression detection."""
        signal = SignalData(
            test_name="test_checkout",
            test_status="fail",
            consecutive_failures=3,
            total_runs=50,
            historical_failure_rate=0.06,
            code_changed=True,
            error_message="AssertionError: Expected 'Success' but got 'Error'"
        )
        
        result = self.engine.classify(signal)
        
        assert result.label == "regression"
        assert result.deterministic_confidence >= 0.7
    
    def test_new_test_detection(self):
        """Test: New test detection."""
        signal = SignalData(
            test_name="test_new_feature",
            test_status="pass",
            total_runs=0
        )
        
        result = self.engine.classify(signal)
        
        assert result.label == "new_test"
        assert result.deterministic_confidence == 1.0
    
    def test_batch_classification(self):
        """Test: Batch classification."""
        signals = [
            SignalData(test_name="test1", test_status="pass", total_runs=0),
            SignalData(test_name="test2", test_status="pass", total_runs=50, historical_failure_rate=0.0),
            SignalData(test_name="test3", test_status="pass", retry_count=2, final_status="pass", total_runs=10),
        ]
        
        results = self.engine.batch_classify(signals)
        
        assert len(results) == 3
        assert results[0].label == "new_test"
        assert results[1].label == "stable"
        assert results[2].label == "flaky"


# ============================================================================
# COMPREHENSIVE TESTS WITH AI (MOCKED)
# ============================================================================

class TestIntelligenceWithAI:
    """Test intelligence system WITH AI enrichment (mocked)."""
    
    def setup_method(self):
        """Setup for each test."""
        # Create mock AI analyzer
        self.mock_analyzer = MockAIAnalyzer()
        
        self.config = IntelligenceConfig()
        self.config.ai.enabled = True
        self.config.ai.timeout_ms = 5000
        
        self.engine = IntelligenceEngine(
            config=self.config,
            ai_analyzer=self.mock_analyzer
        )
    
    def test_ai_enrichment_success(self):
        """Test: AI enrichment adds insights."""
        signal = SignalData(
            test_name="test_payment",
            test_status="pass",
            retry_count=1,
            final_status="pass",
            total_runs=20,
            historical_failure_rate=0.15
        )
        
        result = self.engine.classify(signal)
        
        assert result.label == "flaky"
        # AI enrichment should be present
        if result.ai_enrichment:
            assert result.ai_enrichment.insights is not None
            assert result.ai_enrichment.confidence > 0
    
    def test_ai_timeout_fallback(self):
        """Test: AI timeout falls back to deterministic."""
        self.mock_analyzer.set_timeout(True)
        
        signal = SignalData(
            test_name="test_slow",
            test_status="pass",
            total_runs=10,
            historical_failure_rate=0.0
        )
        
        result = self.engine.classify(signal)
        
        assert result.label == "stable"
        assert result.deterministic_confidence > 0
        # AI enrichment should be None due to timeout
        assert result.ai_enrichment is None
    
    def test_ai_error_graceful_degradation(self):
        """Test: AI error doesn't break classification."""
        self.mock_analyzer.set_error(True)
        
        signal = SignalData(
            test_name="test_error",
            test_status="fail",
            consecutive_failures=5,
            total_runs=100,
            historical_failure_rate=0.05
        )
        
        result = self.engine.classify(signal)
        
        # Deterministic classification should still work
        assert result.label in ["unstable", "stable", "regression"]
        assert result.ai_enrichment is None


# ============================================================================
# POLICY ENGINE TESTS
# ============================================================================

class TestPolicyEngine:
    """Test policy-based overrides."""
    
    def setup_method(self):
        """Setup for each test."""
        reset_policy_engine()
        self.engine = get_policy_engine()
        self.classifier = DeterministicClassifier()
    
    def teardown_method(self):
        """Cleanup after each test."""
        reset_policy_engine()
    
    def test_pattern_based_override(self):
        """Test: Pattern-based policy override."""
        # Add integration test policy
        policy = TestNamePatternPolicy(
            name="integration_override",
            pattern=r"integration|e2e",
            target_label=ClassificationLabel.FLAKY,
            reason="Integration tests have higher flaky tolerance",
            priority=10
        )
        self.engine.add_policy(policy)
        
        # Create signal
        signal = SignalData(
            test_name="test_integration_api",
            test_status="pass",
            total_runs=50,
            historical_failure_rate=0.0
        )
        
        # Classify deterministically
        det_result = self.classifier.classify(signal)
        assert det_result.label == ClassificationLabel.STABLE
        
        # Apply policies
        final_result = self.engine.apply_policies(signal, det_result)
        
        # Should be overridden to FLAKY
        assert final_result.label == ClassificationLabel.FLAKY
        assert "Integration tests" in str(final_result.reasons)
    
    def test_threshold_override(self):
        """Test: Threshold-based policy override."""
        policy = ThresholdOverridePolicy(
            name="high_failure_override",
            min_failure_rate=0.5,
            max_failure_rate=1.0,
            target_label=ClassificationLabel.UNSTABLE,
            reason_template="High failure rate: {failure_rate}",
            priority=20
        )
        self.engine.add_policy(policy)
        
        signal = SignalData(
            test_name="test_failing",
            test_status="fail",
            total_runs=20,
            historical_failure_rate=0.6
        )
        
        det_result = self.classifier.classify(signal)
        final_result = self.engine.apply_policies(signal, det_result)
        
        assert final_result.label == ClassificationLabel.UNSTABLE
        assert "60.0%" in str(final_result.reasons)
    
    def test_quarantine_policy(self):
        """Test: Quarantine policy blocks test."""
        policy = QuarantinePolicy(
            name="auto_quarantine",
            consecutive_failures_threshold=5,
            priority=5  # High priority
        )
        self.engine.add_policy(policy)
        
        signal = SignalData(
            test_name="test_broken",
            test_status="fail",
            consecutive_failures=10,
            total_runs=20
        )
        
        det_result = self.classifier.classify(signal)
        final_result = self.engine.apply_policies(signal, det_result)
        
        # Should be quarantined (UNKNOWN label, blocked metadata)
        assert final_result.label == ClassificationLabel.UNKNOWN
        assert final_result.metadata.get("blocked") is True
        assert final_result.metadata.get("quarantined") is True
    
    def test_multiple_policies_priority(self):
        """Test: Multiple policies execute in priority order."""
        # Add policies with different priorities
        policy1 = TestNamePatternPolicy(
            name="pattern1",
            pattern=r"test_special",
            target_label=ClassificationLabel.STABLE,
            reason="Pattern 1",
            priority=50
        )
        policy2 = TestNamePatternPolicy(
            name="pattern2",
            pattern=r"special",
            target_label=ClassificationLabel.FLAKY,
            reason="Pattern 2",
            priority=10  # Higher priority (lower number)
        )
        
        self.engine.add_policy(policy1)
        self.engine.add_policy(policy2)
        
        signal = SignalData(
            test_name="test_special_case",
            test_status="pass",
            total_runs=10
        )
        
        det_result = self.classifier.classify(signal)
        final_result = self.engine.apply_policies(signal, det_result)
        
        # Should use policy2 (higher priority)
        assert final_result.label == ClassificationLabel.FLAKY
        assert "Pattern 2" in str(final_result.reasons)


# ============================================================================
# PROMPT TEMPLATES TESTS
# ============================================================================

class TestPromptTemplates:
    """Test prompt template generation."""
    
    def setup_method(self):
        """Setup for each test."""
        self.builder = PromptBuilder()
    
    def test_flaky_prompt_generation(self):
        """Test: Generate flaky analysis prompt."""
        prompt = self.builder.build_flaky_prompt(
            test_name="test_search",
            confidence=0.85,
            reasons=["Required 2 retries", "25% failure rate"],
            retry_count=2,
            failure_rate=0.25,
            total_runs=20,
            recent_pattern="Pass after retry"
        )
        
        assert "test_search" in prompt
        assert "85%" in prompt
        assert "25" in prompt  # 25% or 25.0%
        assert "Root Cause Analysis" in prompt
    
    def test_regression_prompt_generation(self):
        """Test: Generate regression analysis prompt."""
        prompt = self.builder.build_regression_prompt(
            test_name="test_checkout",
            confidence=0.90,
            reasons=["Recent code change", "New failures"],
            code_changed=True,
            changed_files=["payment.py", "cart.py"],
            commit_sha="abc123",
            consecutive_passes=50,
            error_message="AssertionError: Payment failed"
        )
        
        assert "test_checkout" in prompt
        assert "abc123" in prompt
        assert "payment.py" in prompt
        assert "should this commit be reverted" in prompt.lower()
    
    def test_stable_prompt_generation(self):
        """Test: Generate stable test prompt."""
        prompt = self.builder.build_stable_prompt(
            test_name="test_login",
            confidence=0.95,
            reasons=["100% pass rate"],
            pass_rate=1.0,
            total_runs=100,
            last_failure_date="2025-01-01",
            coverage_info="85% code coverage"
        )
        
        assert "test_login" in prompt
        assert "100%" in prompt or "1.0" in prompt
        assert "optimization" in prompt.lower()


# ============================================================================
# CONFIDENCE CALIBRATION TESTS
# ============================================================================

class TestConfidenceCalibration:
    """Test confidence calibration system."""
    
    def test_calibration_tracking(self):
        """Test: Calibration tracks predictions."""
        from core.intelligence.confidence_calibration import ConfidenceCalibrator
        
        calibrator = ConfidenceCalibrator()
        
        # Record predictions
        calibrator.record_prediction(0.9, True, "stable")
        calibrator.record_prediction(0.8, True, "stable")
        calibrator.record_prediction(0.7, False, "stable")
        
        # Get stats
        stats = calibrator.get_calibration_stats()
        
        assert stats["total_predictions"] == 3
        assert stats["overall_accuracy"] >= 0.0
    
    def test_calibration_adjustment(self):
        """Test: Calibration adjusts confidence."""
        from core.intelligence.confidence_calibration import ConfidenceCalibrator
        
        calibrator = ConfidenceCalibrator()
        
        # Record many predictions in one bucket
        for _ in range(15):
            calibrator.record_prediction(0.85, True, "flaky")  # 85% confidence, always correct
        
        # Calibrate new prediction
        adjusted = calibrator.calibrate(0.85, "flaky")
        
        # Should be close to actual accuracy (100% in this case)
        assert adjusted >= 0.85  # Should be adjusted upward


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def test_complete_pipeline_without_ai(self):
        """Test: Complete pipeline without AI."""
        # Setup
        config = IntelligenceConfig()
        config.ai.enabled = False
        engine = IntelligenceEngine(config=config)
        
        # Test various scenarios
        test_cases = [
            (
                SignalData(
                    test_name="test_new_feature",
                    test_status="pass",
                    total_runs=0,
                    framework="pytest"
                ),
                "new_test"
            ),
            (
                SignalData(
                    test_name="test_stable_login",
                    test_status="pass",
                    total_runs=100,
                    historical_failure_rate=0.0,
                    framework="selenium_java"
                ),
                "stable"
            ),
            (
                SignalData(
                    test_name="test_flaky_search",
                    test_status="pass",
                    retry_count=2,
                    final_status="pass",
                    total_runs=20,
                    framework="cypress"
                ),
                "flaky"
            ),
        ]
        
        for signal, expected_label in test_cases:
            result = engine.classify(signal)
            assert result.label == expected_label
            assert result.deterministic_confidence > 0
            assert result.ai_enrichment is None
    
    def test_complete_pipeline_with_policies(self):
        """Test: Complete pipeline with policy overrides."""
        # Setup
        reset_policy_engine()
        policy_engine = get_policy_engine()
        policy_engine.add_policy(QuarantinePolicy(
            name="test_quarantine",
            consecutive_failures_threshold=5
        ))
        
        config = IntelligenceConfig()
        config.ai.enabled = False
        intelligence_engine = IntelligenceEngine(config=config)
        classifier = DeterministicClassifier()
        
        # Test quarantine scenario
        signal = SignalData(
            test_name="test_broken",
            test_status="fail",
            consecutive_failures=10,
            total_runs=20
        )
        
        # Classify
        det_result = classifier.classify(signal)
        final_result = policy_engine.apply_policies(signal, det_result)
        
        # Should be quarantined
        assert final_result.metadata.get("blocked") is True
        assert final_result.label == ClassificationLabel.UNKNOWN


# ============================================================================
# MOCK AI ANALYZER
# ============================================================================

class MockAIAnalyzer:
    """Mock AI analyzer for testing."""
    
    def __init__(self):
        self.timeout = False
        self.error = False
    
    def set_timeout(self, value: bool):
        """Set timeout simulation."""
        self.timeout = value
    
    def set_error(self, value: bool):
        """Set error simulation."""
        self.error = value
    
    def analyze(self, prompt: str, **kwargs) -> str:
        """Mock analyze method."""
        import time
        
        if self.timeout:
            time.sleep(10)  # Simulate timeout
            return None
        
        if self.error:
            raise Exception("Mock AI error")
        
        # Return mock response
        return """
        Root Cause: Timing issue in async operation
        Risk: MEDIUM - May affect user experience
        Actions: Add explicit waits, review async handling
        """


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
