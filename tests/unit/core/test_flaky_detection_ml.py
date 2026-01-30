"""
Unit Tests for Phase-2 Flaky Detection Features.

Tests:
- Framework-specific feature extraction
- Step-level detection
- Multi-dimensional confidence calibration
- Per-framework models
"""

import pytest
from datetime import datetime, timedelta

from core.flaky_detection.framework_features import (
    SeleniumFeatureExtractor,
    CucumberFeatureExtractor,
    PytestFeatureExtractor,
    RobotFeatureExtractor,
    SeleniumErrorClassifier,
    PytestErrorClassifier,
    RobotErrorClassifier,
    FrameworkFeatureExtractor
)
from core.flaky_detection.step_detection import (
    StepExecutionRecord,
    StepFeatureEngineer,
    ScenarioFlakinessAggregator,
    StepFlakyResult
)
from core.flaky_detection.confidence_calibration import (
    ConfidenceCalibrator,
    ConfidenceClassifier,
    ConfidenceInputs,
    ConfidenceWeights
)
from core.flaky_detection.models import TestExecutionRecord, TestStatus, TestFramework
from core.flaky_detection.multi_framework_detector import (
    MultiFrameworkFlakyDetector,
    MultiFrameworkDetectorConfig
)


# ============================================================================
# Framework-Specific Feature Extraction Tests
# ============================================================================

class TestSeleniumFeatureExtraction:
    """Test Selenium-specific feature extraction."""
    
    def test_timeout_detection(self):
        """Test detection of timeout errors."""
        executions = [
            TestExecutionRecord(
                test_id="test1",
                framework=TestFramework.SELENIUM_JAVA,
                status=TestStatus.FAILED,
                duration_ms=5000,
                executed_at=datetime.now(),
                error_signature="TimeoutException: Element not found after 10s"
            ),
            TestExecutionRecord(
                test_id="test1",
                framework=TestFramework.SELENIUM_JAVA,
                status=TestStatus.PASSED,
                duration_ms=1000,
                executed_at=datetime.now()
            )
        ]
        
        extractor = SeleniumFeatureExtractor()
        features = extractor.extract(executions)
        
        assert features.timeout_failure_rate == 0.5  # 1 timeout out of 2
        assert features.wait_related_failures == 0.5
    
    def test_stale_element_detection(self):
        """Test detection of stale element errors."""
        executions = [
            TestExecutionRecord(
                test_id="test1",
                framework=TestFramework.SELENIUM_JAVA,
                status=TestStatus.FAILED,
                duration_ms=1000,
                executed_at=datetime.now(),
                error_signature="StaleElementReferenceException: Element is no longer attached"
            )
        ]
        
        extractor = SeleniumFeatureExtractor()
        features = extractor.extract(executions)
        
        assert features.stale_element_rate == 1.0


class TestCucumberFeatureExtraction:
    """Test Cucumber-specific feature extraction."""
    
    def test_hook_failure_detection(self):
        """Test detection of hook failures."""
        executions = [
            TestExecutionRecord(
                test_id="scenario1",
                framework=TestFramework.CUCUMBER,
                status=TestStatus.FAILED,
                duration_ms=100,
                executed_at=datetime.now(),
                error_signature="Before hook failed: Connection timeout"
            ),
            TestExecutionRecord(
                test_id="scenario1",
                framework=TestFramework.CUCUMBER,
                status=TestStatus.PASSED,
                duration_ms=100,
                executed_at=datetime.now()
            )
        ]
        
        extractor = CucumberFeatureExtractor()
        features = extractor.extract(executions)
        
        assert features.hook_failure_rate == 0.5


class TestPytestFeatureExtraction:
    """Test Pytest-specific feature extraction."""
    
    def test_fixture_failure_detection(self):
        """Test detection of fixture failures."""
        executions = [
            TestExecutionRecord(
                test_id="test_login",
                framework=TestFramework.PYTEST,
                status=TestStatus.FAILED,
                duration_ms=50,
                executed_at=datetime.now(),
                error_signature="fixture 'db_session' error: Connection refused"
            ),
            TestExecutionRecord(
                test_id="test_login",
                framework=TestFramework.PYTEST,
                status=TestStatus.PASSED,
                duration_ms=100,
                executed_at=datetime.now()
            )
        ]
        
        extractor = PytestFeatureExtractor()
        features = extractor.extract(executions)
        
        assert features.fixture_failure_rate == 0.5


class TestErrorClassifiers:
    """Test error classification."""
    
    def test_selenium_error_classification(self):
        """Test Selenium error patterns."""
        classification = SeleniumErrorClassifier.classify(
            "TimeoutException: Timed out waiting for element"
        )
        
        assert classification["timeout"] is True
        assert classification["stale_element"] is False
    
    def test_pytest_error_classification(self):
        """Test Pytest error patterns."""
        classification = PytestErrorClassifier.classify(
            "fixture 'db' not found"
        )
        
        assert classification["fixture"] is True
        assert classification["xfail"] is False


# ============================================================================
# Step-Level Detection Tests
# ============================================================================

class TestStepFeatureEngineering:
    """Test step-level feature extraction."""
    
    def test_step_failure_rate_calculation(self):
        """Test step failure rate calculation."""
        now = datetime.now()
        executions = [
            StepExecutionRecord(
                step_id="step1",
                scenario_id="scenario1",
                test_id="test1",
                step_text="When user clicks login",
                step_index=0,
                status=TestStatus.FAILED,
                duration_ms=100,
                execution_time=now
            ),
            StepExecutionRecord(
                step_id="step1",
                scenario_id="scenario1",
                test_id="test1",
                step_text="When user clicks login",
                step_index=0,
                status=TestStatus.PASSED,
                duration_ms=100,
                execution_time=now
            )
        ]
        
        engineer = StepFeatureEngineer()
        features = engineer.extract_features(executions)
        
        assert features.step_failure_rate == 0.5
        assert features.execution_count == 2
    
    def test_step_switch_rate_calculation(self):
        """Test step pass/fail switch rate."""
        now = datetime.now()
        executions = [
            StepExecutionRecord(
                step_id="step1",
                scenario_id="scenario1",
                test_id="test1",
                step_text="When user clicks login",
                step_index=0,
                status=TestStatus.PASSED,
                duration_ms=100,
                execution_time=now - timedelta(hours=3)
            ),
            StepExecutionRecord(
                step_id="step1",
                scenario_id="scenario1",
                test_id="test1",
                step_text="When user clicks login",
                step_index=0,
                status=TestStatus.FAILED,
                duration_ms=100,
                execution_time=now - timedelta(hours=2)
            ),
            StepExecutionRecord(
                step_id="step1",
                scenario_id="scenario1",
                test_id="test1",
                step_text="When user clicks login",
                step_index=0,
                status=TestStatus.PASSED,
                duration_ms=100,
                execution_time=now - timedelta(hours=1)
            )
        ]
        
        engineer = StepFeatureEngineer()
        features = engineer.extract_features(executions)
        
        # 2 switches out of 2 transitions
        assert features.step_pass_fail_switch_rate == 1.0


class TestScenarioAggregation:
    """Test scenario-level flakiness aggregation."""
    
    def test_scenario_aggregation_with_flaky_step(self):
        """Test aggregation when scenario has flaky steps."""
        from core.flaky_detection.step_detection import StepFlakyFeatureVector
        
        # Create mock step results
        flaky_step = StepFlakyResult(
            step_id="step1",
            step_text="When user submits form",
            scenario_id="scenario1",
            framework=TestFramework.CUCUMBER,
            flaky_score=-0.5,
            is_flaky=True,
            confidence=0.8,
            features=StepFlakyFeatureVector(
                step_failure_rate=0.6,
                step_pass_fail_switch_rate=0.5,
                step_duration_variance=100.0,
                step_duration_cv=0.6,
                unique_error_count=2,
                error_diversity_ratio=0.5,
                position_sensitivity=0.1,
                preceding_step_correlation=0.0,
                retry_success_rate=0.5,
                avg_retry_count=1.0,
                execution_count=20,
                is_reliable=True
            ),
            detected_at=datetime.now(),
            model_version="2.0.0",
            primary_indicators=["High failure rate"]
        )
        
        stable_step = StepFlakyResult(
            step_id="step2",
            step_text="Then success message is shown",
            scenario_id="scenario1",
            framework=TestFramework.CUCUMBER,
            flaky_score=0.2,
            is_flaky=False,
            confidence=0.9,
            features=StepFlakyFeatureVector(
                step_failure_rate=0.0,
                step_pass_fail_switch_rate=0.0,
                step_duration_variance=10.0,
                step_duration_cv=0.1,
                unique_error_count=0,
                error_diversity_ratio=0.0,
                position_sensitivity=0.0,
                preceding_step_correlation=0.0,
                retry_success_rate=0.0,
                avg_retry_count=0.0,
                execution_count=20,
                is_reliable=True
            ),
            detected_at=datetime.now(),
            model_version="2.0.0",
            primary_indicators=[]
        )
        
        aggregator = ScenarioFlakinessAggregator()
        analysis = aggregator.aggregate(
            scenario_id="scenario1",
            scenario_name="User Login",
            step_results=[flaky_step, stable_step],
            framework=TestFramework.CUCUMBER
        )
        
        assert analysis.is_scenario_flaky is True
        assert len(analysis.flaky_steps) == 1
        assert len(analysis.stable_steps) == 1
        assert analysis.root_cause_step == flaky_step
        assert "When user submits form" in analysis.explanation


# ============================================================================
# Confidence Calibration Tests
# ============================================================================

class TestConfidenceCalibrator:
    """Test multi-dimensional confidence calculation."""
    
    def test_execution_volume_scoring(self):
        """Test confidence increases with execution volume."""
        calibrator = ConfidenceCalibrator(
            min_executions_reliable=15,
            min_executions_confident=30
        )
        
        # Low volume
        inputs_low = ConfidenceInputs(
            total_executions=10,
            first_execution=datetime.now(),
            last_execution=datetime.now(),
            unique_environments=1,
            total_environment_runs=10,
            prediction_history=[],
            confidence_history=[],
            has_error_signatures=True,
            has_duration_data=True,
            has_git_commits=True
        )
        
        # Medium volume
        inputs_mid = ConfidenceInputs(
            total_executions=22,
            first_execution=datetime.now(),
            last_execution=datetime.now(),
            unique_environments=1,
            total_environment_runs=22,
            prediction_history=[],
            confidence_history=[],
            has_error_signatures=True,
            has_duration_data=True,
            has_git_commits=True
        )
        
        # High volume
        inputs_high = ConfidenceInputs(
            total_executions=50,
            first_execution=datetime.now(),
            last_execution=datetime.now(),
            unique_environments=1,
            total_environment_runs=50,
            prediction_history=[],
            confidence_history=[],
            has_error_signatures=True,
            has_duration_data=True,
            has_git_commits=True
        )
        
        conf_low = calibrator.calculate_confidence(inputs_low)
        conf_mid = calibrator.calculate_confidence(inputs_mid)
        conf_high = calibrator.calculate_confidence(inputs_high)
        
        assert conf_low < conf_mid < conf_high
    
    def test_time_span_scoring(self):
        """Test confidence increases with time span."""
        calibrator = ConfidenceCalibrator()
        
        now = datetime.now()
        
        # Short span
        inputs_short = ConfidenceInputs(
            total_executions=30,
            first_execution=now - timedelta(days=3),
            last_execution=now,
            unique_environments=2,
            total_environment_runs=30,
            prediction_history=[],
            confidence_history=[],
            has_error_signatures=True,
            has_duration_data=True,
            has_git_commits=True
        )
        
        # Long span
        inputs_long = ConfidenceInputs(
            total_executions=30,
            first_execution=now - timedelta(days=20),
            last_execution=now,
            unique_environments=2,
            total_environment_runs=30,
            prediction_history=[],
            confidence_history=[],
            has_error_signatures=True,
            has_duration_data=True,
            has_git_commits=True
        )
        
        conf_short = calibrator.calculate_confidence(inputs_short)
        conf_long = calibrator.calculate_confidence(inputs_long)
        
        assert conf_short < conf_long
    
    def test_model_consistency_scoring(self):
        """Test confidence considers prediction stability."""
        calibrator = ConfidenceCalibrator()
        
        now = datetime.now()
        
        # Unstable predictions
        inputs_unstable = ConfidenceInputs(
            total_executions=30,
            first_execution=now - timedelta(days=14),
            last_execution=now,
            unique_environments=2,
            total_environment_runs=30,
            prediction_history=[True, False, True, False, True],  # Flipping
            confidence_history=[0.6, 0.5, 0.6, 0.5, 0.6],
            has_error_signatures=True,
            has_duration_data=True,
            has_git_commits=True
        )
        
        # Stable predictions
        inputs_stable = ConfidenceInputs(
            total_executions=30,
            first_execution=now - timedelta(days=14),
            last_execution=now,
            unique_environments=2,
            total_environment_runs=30,
            prediction_history=[True, True, True, True, True],  # Consistent
            confidence_history=[0.8, 0.8, 0.8, 0.8, 0.8],
            has_error_signatures=True,
            has_duration_data=True,
            has_git_commits=True
        )
        
        conf_unstable = calibrator.calculate_confidence(inputs_unstable)
        conf_stable = calibrator.calculate_confidence(inputs_stable)
        
        assert conf_unstable < conf_stable


class TestConfidenceClassifier:
    """Test confidence-based classification."""
    
    def test_classification_with_high_confidence(self):
        """Test classification when confidence is high."""
        classifier = ConfidenceClassifier(
            confident_threshold=0.7,
            suspected_threshold=0.5
        )
        
        # High confidence + flaky prediction
        result = classifier.classify(
            is_flaky_prediction=True,
            flaky_score=-0.5,
            confidence=0.85
        )
        assert result == "flaky"
        
        # High confidence + stable prediction
        result = classifier.classify(
            is_flaky_prediction=False,
            flaky_score=0.2,
            confidence=0.85
        )
        assert result == "stable"
    
    def test_classification_with_low_confidence(self):
        """Test classification when confidence is low."""
        classifier = ConfidenceClassifier()
        
        # Low confidence
        result = classifier.classify(
            is_flaky_prediction=True,
            flaky_score=-0.5,
            confidence=0.2
        )
        assert result == "insufficient_data"
    
    def test_severity_classification(self):
        """Test severity classification logic."""
        classifier = ConfidenceClassifier()
        
        # Critical: high failure rate + high confidence
        severity = classifier.classify_severity(
            classification="flaky",
            failure_rate=0.8,
            confidence=0.9
        )
        assert severity == "critical"
        
        # High: moderate-high failure rate + high confidence
        severity = classifier.classify_severity(
            classification="flaky",
            failure_rate=0.6,
            confidence=0.8
        )
        assert severity == "high"
        
        # None: stable test
        severity = classifier.classify_severity(
            classification="stable",
            failure_rate=0.0,
            confidence=0.9
        )
        assert severity == "none"


# ============================================================================
# Multi-Framework Detector Tests
# ============================================================================

class TestMultiFrameworkDetector:
    """Test per-framework model training and detection."""
    
    def test_per_framework_training(self):
        """Test that separate models are trained per framework."""
        config = MultiFrameworkDetectorConfig(
            n_estimators=10,  # Small for speed
            min_executions_reliable=5
        )
        detector = MultiFrameworkFlakyDetector(config)
        
        now = datetime.now()
        
        # Create executions for different frameworks
        selenium_tests = {
            "test1": [
                TestExecutionRecord(
                    test_id="test1",
                    framework=TestFramework.SELENIUM_JAVA,
                    status=TestStatus.PASSED if i % 2 == 0 else TestStatus.FAILED,
                    duration_ms=100 + (i * 10),
                    executed_at=now - timedelta(hours=i)
                )
                for i in range(20)
            ]
        }
        
        pytest_tests = {
            "test2": [
                TestExecutionRecord(
                    test_id="test2",
                    framework=TestFramework.PYTEST,
                    status=TestStatus.PASSED if i % 3 == 0 else TestStatus.FAILED,
                    duration_ms=50 + (i * 5),
                    executed_at=now - timedelta(hours=i)
                )
                for i in range(20)
            ]
        }
        
        all_tests = {**selenium_tests, **pytest_tests}
        framework_map = {
            "test1": TestFramework.SELENIUM_JAVA,
            "test2": TestFramework.PYTEST
        }
        
        # Train
        detector.train(all_tests, framework_map)
        
        # Check both frameworks have trained models
        assert TestFramework.SELENIUM_JAVA in detector.models
        assert TestFramework.PYTEST in detector.models
        assert detector.is_trained[TestFramework.SELENIUM_JAVA]
        assert detector.is_trained[TestFramework.PYTEST]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
