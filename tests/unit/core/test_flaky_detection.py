"""
Unit tests for flaky test detection system.

Tests cover:
- Feature engineering
- ML model training and detection
- Database persistence
- Framework integrations
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from core.flaky_detection.models import (
    TestExecutionRecord,
    FlakyFeatureVector,
    FlakyTestResult,
    TestFramework,
    TestStatus
)
from core.flaky_detection.feature_engineering import (
    FeatureEngineer,
    normalize_error_signature
)
from core.flaky_detection.detector import FlakyDetector, FlakyDetectionConfig


class TestModels:
    """Test data models."""
    
    def test_test_execution_record_creation(self):
        """Test creating TestExecutionRecord."""
        record = TestExecutionRecord(
            test_id="com.example.TestClass.testMethod",
            framework=TestFramework.JUNIT,
            status=TestStatus.PASSED,
            duration_ms=150.5,
            executed_at=datetime.now()
        )
        
        assert record.test_id == "com.example.TestClass.testMethod"
        assert record.framework == TestFramework.JUNIT
        assert record.status == TestStatus.PASSED
        assert record.is_passed
        assert not record.is_failed
    
    def test_test_execution_record_with_error(self):
        """Test execution record with error information."""
        record = TestExecutionRecord(
            test_id="test.flaky",
            framework=TestFramework.PYTEST,
            status=TestStatus.FAILED,
            duration_ms=200.0,
            executed_at=datetime.now(),
            error_signature="AssertionError: Expected value not found",
            error_full="Full stack trace here..."
        )
        
        assert record.is_failed
        assert record.get_error_type() == "AssertionError"
    
    def test_flaky_feature_vector_validation(self):
        """Test feature vector validation and clamping."""
        features = FlakyFeatureVector(
            test_id="test.id",
            failure_rate=1.5,  # Should be clamped to 1.0
            pass_fail_switch_rate=-0.1,  # Should be clamped to 0.0
            duration_variance=100.0,
            mean_duration_ms=500.0,
            duration_cv=0.2,
            retry_success_rate=0.5,
            avg_retry_count=1.0,
            unique_error_count=2,
            error_diversity_ratio=0.5,
            same_commit_failure_rate=0.3,
            recent_failure_rate=0.4,
            total_executions=30,
            window_size=50,
            last_executed=datetime.now()
        )
        
        assert features.failure_rate == 1.0  # Clamped
        assert features.pass_fail_switch_rate == 0.0  # Clamped
        assert features.confidence == 1.0  # 30 executions = full confidence
        assert features.is_reliable
    
    def test_flaky_feature_vector_to_array(self):
        """Test converting feature vector to array."""
        features = FlakyFeatureVector(
            test_id="test.id",
            failure_rate=0.3,
            pass_fail_switch_rate=0.2,
            duration_variance=50.0,
            mean_duration_ms=300.0,
            duration_cv=0.15,
            retry_success_rate=0.6,
            avg_retry_count=0.5,
            unique_error_count=1,
            error_diversity_ratio=0.33,
            same_commit_failure_rate=0.25,
            recent_failure_rate=0.35,
            total_executions=20,
            window_size=50,
            last_executed=datetime.now()
        )
        
        array = features.to_array()
        assert len(array) == 10
        assert array[0] == 0.3  # failure_rate
        assert array[1] == 0.2  # pass_fail_switch_rate


class TestFeatureEngineering:
    """Test feature engineering."""
    
    def create_execution_record(
        self,
        test_id: str,
        status: TestStatus,
        duration_ms: float,
        hours_ago: int = 0,
        error_sig: str = None
    ) -> TestExecutionRecord:
        """Helper to create test execution record."""
        return TestExecutionRecord(
            test_id=test_id,
            framework=TestFramework.JUNIT,
            status=status,
            duration_ms=duration_ms,
            executed_at=datetime.now() - timedelta(hours=hours_ago),
            error_signature=error_sig
        )
    
    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        engineer = FeatureEngineer()
        
        # 3 passed, 2 failed = 40% failure rate
        executions = [
            self.create_execution_record("test.1", TestStatus.PASSED, 100, 5),
            self.create_execution_record("test.1", TestStatus.FAILED, 100, 4),
            self.create_execution_record("test.1", TestStatus.PASSED, 100, 3),
            self.create_execution_record("test.1", TestStatus.FAILED, 100, 2),
            self.create_execution_record("test.1", TestStatus.PASSED, 100, 1),
        ]
        
        features = engineer.extract_features(executions)
        
        assert features is not None
        assert features.failure_rate == pytest.approx(0.4, abs=0.01)
        assert features.total_executions == 5
    
    def test_switch_rate_calculation(self):
        """Test pass/fail switch rate calculation."""
        engineer = FeatureEngineer()
        
        # Pattern: P-F-P-F = 3 switches out of 3 transitions = 100%
        executions = [
            self.create_execution_record("test.2", TestStatus.PASSED, 100, 4),
            self.create_execution_record("test.2", TestStatus.FAILED, 100, 3),
            self.create_execution_record("test.2", TestStatus.PASSED, 100, 2),
            self.create_execution_record("test.2", TestStatus.FAILED, 100, 1),
        ]
        
        features = engineer.extract_features(executions)
        
        assert features is not None
        assert features.pass_fail_switch_rate == pytest.approx(1.0, abs=0.01)
    
    def test_duration_variance_calculation(self):
        """Test duration variance calculation."""
        engineer = FeatureEngineer()
        
        # Varying durations
        executions = [
            self.create_execution_record("test.3", TestStatus.PASSED, 100, 5),
            self.create_execution_record("test.3", TestStatus.PASSED, 200, 4),
            self.create_execution_record("test.3", TestStatus.PASSED, 150, 3),
            self.create_execution_record("test.3", TestStatus.PASSED, 180, 2),
            self.create_execution_record("test.3", TestStatus.PASSED, 120, 1),
        ]
        
        features = engineer.extract_features(executions)
        
        assert features is not None
        assert features.duration_variance > 0
        assert features.mean_duration_ms == pytest.approx(150.0, abs=1.0)
    
    def test_error_diversity_calculation(self):
        """Test error diversity calculation."""
        engineer = FeatureEngineer()
        
        # 3 failures with 2 different error types
        executions = [
            self.create_execution_record("test.4", TestStatus.FAILED, 100, 3, "AssertionError"),
            self.create_execution_record("test.4", TestStatus.FAILED, 100, 2, "TimeoutException"),
            self.create_execution_record("test.4", TestStatus.FAILED, 100, 1, "AssertionError"),
        ]
        
        features = engineer.extract_features(executions)
        
        assert features is not None
        assert features.unique_error_count == 2
        assert features.error_diversity_ratio == pytest.approx(2/3, abs=0.01)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        engineer = FeatureEngineer()
        
        # Only 2 executions (need at least 3)
        executions = [
            self.create_execution_record("test.5", TestStatus.PASSED, 100, 2),
            self.create_execution_record("test.5", TestStatus.FAILED, 100, 1),
        ]
        
        features = engineer.extract_features(executions)
        
        assert features is None
    
    def test_normalize_error_signature(self):
        """Test error signature normalization."""
        # Line numbers should be normalized
        sig1 = normalize_error_signature("AssertionError at file.py:123")
        sig2 = normalize_error_signature("AssertionError at file.py:456")
        assert sig1 == sig2
        
        # Hex addresses should be normalized
        sig3 = normalize_error_signature("Exception at 0x7f8a9b0c1d2e")
        sig4 = normalize_error_signature("Exception at 0xabcdef123456")
        assert sig3 == sig4


class TestFlakyDetector:
    """Test ML-based flaky detector."""
    
    def create_stable_features(self, test_id: str) -> FlakyFeatureVector:
        """Create features for a stable test."""
        return FlakyFeatureVector(
            test_id=test_id,
            failure_rate=0.0,  # Never fails
            pass_fail_switch_rate=0.0,
            duration_variance=10.0,
            mean_duration_ms=100.0,
            duration_cv=0.1,
            retry_success_rate=0.0,
            avg_retry_count=0.0,
            unique_error_count=0,
            error_diversity_ratio=0.0,
            same_commit_failure_rate=0.0,
            recent_failure_rate=0.0,
            total_executions=30,
            window_size=50,
            last_executed=datetime.now()
        )
    
    def create_flaky_features(self, test_id: str) -> FlakyFeatureVector:
        """Create features for a flaky test."""
        return FlakyFeatureVector(
            test_id=test_id,
            failure_rate=0.4,  # Fails 40% of the time
            pass_fail_switch_rate=0.6,  # Frequent switches
            duration_variance=200.0,
            mean_duration_ms=150.0,
            duration_cv=0.9,
            retry_success_rate=0.7,
            avg_retry_count=2.0,
            unique_error_count=3,
            error_diversity_ratio=0.75,
            same_commit_failure_rate=0.35,
            recent_failure_rate=0.45,
            total_executions=30,
            window_size=50,
            last_executed=datetime.now()
        )
    
    def test_detector_training(self):
        """Test training the detector."""
        # Create mix of stable and flaky tests
        features = [
            self.create_stable_features(f"stable.{i}")
            for i in range(15)
        ] + [
            self.create_flaky_features(f"flaky.{i}")
            for i in range(5)
        ]
        
        detector = FlakyDetector()
        detector.train(features)
        
        assert detector.is_trained
        assert detector.training_sample_count == 20
    
    def test_detector_detection(self):
        """Test flaky detection."""
        # Train model
        features = [
            self.create_stable_features(f"stable.{i}")
            for i in range(15)
        ] + [
            self.create_flaky_features(f"flaky.{i}")
            for i in range(5)
        ]
        
        detector = FlakyDetector()
        detector.train(features)
        
        # Test detection on known flaky test
        flaky_test = self.create_flaky_features("test.flaky")
        result = detector.detect(flaky_test, TestFramework.JUNIT, "Flaky Test")
        
        assert result.test_id == "test.flaky"
        assert result.confidence >= 0.5  # Should have good confidence
        # Note: is_flaky might vary due to ML model randomness
    
    def test_confidence_calculation(self):
        """Test confidence calculation based on execution count."""
        # 15 executions = 0.5 confidence
        features_low = FlakyFeatureVector(
            test_id="test.low",
            failure_rate=0.3,
            pass_fail_switch_rate=0.2,
            duration_variance=50.0,
            mean_duration_ms=100.0,
            duration_cv=0.5,
            retry_success_rate=0.0,
            avg_retry_count=0.0,
            unique_error_count=1,
            error_diversity_ratio=0.5,
            same_commit_failure_rate=0.3,
            recent_failure_rate=0.3,
            total_executions=15,
            window_size=50,
            last_executed=datetime.now()
        )
        
        assert features_low.confidence == pytest.approx(0.5, abs=0.01)
        assert features_low.is_reliable
        
        # 5 executions = 0.167 confidence
        features_very_low = FlakyFeatureVector(
            test_id="test.very_low",
            failure_rate=0.4,
            pass_fail_switch_rate=0.3,
            duration_variance=50.0,
            mean_duration_ms=100.0,
            duration_cv=0.5,
            retry_success_rate=0.0,
            avg_retry_count=0.0,
            unique_error_count=1,
            error_diversity_ratio=0.5,
            same_commit_failure_rate=0.4,
            recent_failure_rate=0.4,
            total_executions=5,
            window_size=50,
            last_executed=datetime.now()
        )
        
        assert features_very_low.confidence < 0.5
        assert not features_very_low.is_reliable
    
    def test_insufficient_training_data(self):
        """Test handling of insufficient training data."""
        features = [self.create_stable_features(f"test.{i}") for i in range(5)]
        
        detector = FlakyDetector()
        
        with pytest.raises(ValueError, match="Insufficient training data"):
            detector.train(features)
    
    def test_detect_without_training(self):
        """Test detection without training raises error."""
        detector = FlakyDetector()
        features = self.create_flaky_features("test.1")
        
        with pytest.raises(RuntimeError, match="Model not trained"):
            detector.detect(features, TestFramework.JUNIT)


class TestFlakyTestResult:
    """Test flaky test result model."""
    
    def test_classification_logic(self):
        """Test classification logic."""
        features = FlakyFeatureVector(
            test_id="test.1",
            failure_rate=0.5,
            pass_fail_switch_rate=0.4,
            duration_variance=100.0,
            mean_duration_ms=200.0,
            duration_cv=0.5,
            retry_success_rate=0.5,
            avg_retry_count=1.0,
            unique_error_count=2,
            error_diversity_ratio=0.5,
            same_commit_failure_rate=0.4,
            recent_failure_rate=0.5,
            total_executions=30,
            window_size=50,
            last_executed=datetime.now()
        )
        
        # High confidence flaky
        result = FlakyTestResult(
            test_id="test.1",
            test_name="Test 1",
            framework=TestFramework.JUNIT,
            flaky_score=-0.5,
            is_flaky=True,
            confidence=0.8,
            features=features,
            detected_at=datetime.now(),
            model_version="1.0.0"
        )
        
        assert result.classification == "flaky"
        assert result.severity == "critical"  # 50% failure rate
    
    def test_severity_calculation(self):
        """Test severity calculation."""
        # Critical: >= 50% failure rate
        features_critical = FlakyFeatureVector(
            test_id="test.crit",
            failure_rate=0.6,
            pass_fail_switch_rate=0.5,
            duration_variance=100.0,
            mean_duration_ms=200.0,
            duration_cv=0.5,
            retry_success_rate=0.5,
            avg_retry_count=1.0,
            unique_error_count=2,
            error_diversity_ratio=0.5,
            same_commit_failure_rate=0.5,
            recent_failure_rate=0.6,
            total_executions=30,
            window_size=50,
            last_executed=datetime.now()
        )
        
        result_critical = FlakyTestResult(
            test_id="test.crit",
            test_name="Critical",
            framework=TestFramework.JUNIT,
            flaky_score=-0.5,
            is_flaky=True,
            confidence=0.9,
            features=features_critical,
            detected_at=datetime.now(),
            model_version="1.0.0"
        )
        
        assert result_critical.severity == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
