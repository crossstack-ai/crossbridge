"""
Isolation Forest-based flaky test detector.

Machine learning engine for detecting flaky tests using
historical execution patterns.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

from .models import FlakyFeatureVector, FlakyTestResult, TestFramework
from .feature_engineering import FeatureEngineer


@dataclass
class FlakyDetectionConfig:
    """Configuration for flaky detection."""
    
    # Isolation Forest parameters
    n_estimators: int = 200             # Number of trees
    contamination: float = 0.1          # Expected ratio of flaky tests
    random_state: int = 42              # For reproducibility
    
    # Confidence thresholds
    min_executions_reliable: int = 15   # Minimum for reliable detection
    min_executions_confident: int = 30  # For full confidence
    min_confidence_threshold: float = 0.5  # Minimum confidence to classify
    
    # Feature engineering
    execution_window_size: int = 50     # Number of recent executions to analyze
    recent_window_size: int = 10        # For temporal features
    
    # Model management
    model_version: str = "1.0.0"
    auto_retrain: bool = True
    retrain_threshold: int = 100        # Retrain after N new tests


class FlakyDetector:
    """
    ML-based flaky test detector using Isolation Forest.
    
    Detects flaky tests by analyzing execution patterns across
    all test frameworks.
    """
    
    def __init__(self, config: Optional[FlakyDetectionConfig] = None):
        """
        Initialize flaky detector.
        
        Args:
            config: Detection configuration (uses defaults if None)
        """
        self.config = config or FlakyDetectionConfig()
        self.model: Optional[IsolationForest] = None
        self.feature_engineer = FeatureEngineer(
            window_size=self.config.execution_window_size,
            recent_window=self.config.recent_window_size
        )
        self.is_trained = False
        self.training_date: Optional[datetime] = None
        self.training_sample_count: int = 0
    
    def train(self, feature_vectors: List[FlakyFeatureVector]) -> None:
        """
        Train the Isolation Forest model.
        
        Args:
            feature_vectors: List of feature vectors from test history
        
        Raises:
            ValueError: If insufficient training data
        """
        if len(feature_vectors) < 10:
            raise ValueError(
                f"Insufficient training data: {len(feature_vectors)} tests. "
                "Need at least 10 tests with execution history."
            )
        
        # Convert feature vectors to numpy array
        X = np.array([fv.to_array() for fv in feature_vectors])
        
        # Initialize and train model
        self.model = IsolationForest(
            n_estimators=self.config.n_estimators,
            contamination=self.config.contamination,
            random_state=self.config.random_state,
            n_jobs=-1  # Use all CPU cores
        )
        
        self.model.fit(X)
        
        self.is_trained = True
        self.training_date = datetime.now()
        self.training_sample_count = len(feature_vectors)
    
    def detect(
        self,
        features: FlakyFeatureVector,
        framework: TestFramework,
        test_name: Optional[str] = None
    ) -> FlakyTestResult:
        """
        Detect if a test is flaky based on its features.
        
        Args:
            features: Feature vector for the test
            framework: Test framework
            test_name: Human-readable test name
        
        Returns:
            FlakyTestResult with classification and scores
        
        Raises:
            RuntimeError: If model is not trained
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError(
                "Model not trained. Call train() first or load a trained model."
            )
        
        # Convert features to array
        X = np.array([features.to_array()])
        
        # Get anomaly score (lower = more anomalous = more flaky)
        anomaly_score = self.model.decision_function(X)[0]
        
        # Get binary prediction (-1 = anomaly/flaky, 1 = normal)
        prediction = self.model.predict(X)[0]
        is_flaky_raw = prediction == -1
        
        # Apply confidence gating
        confidence = features.confidence
        is_flaky = is_flaky_raw and confidence >= self.config.min_confidence_threshold
        
        # Identify primary indicators
        indicators = self._identify_indicators(features)
        
        return FlakyTestResult(
            test_id=features.test_id,
            test_name=test_name,
            framework=framework,
            flaky_score=anomaly_score,
            is_flaky=is_flaky,
            confidence=confidence,
            features=features,
            detected_at=datetime.now(),
            model_version=self.config.model_version,
            primary_indicators=indicators
        )
    
    def detect_batch(
        self,
        feature_map: Dict[str, FlakyFeatureVector],
        framework_map: Dict[str, TestFramework],
        name_map: Optional[Dict[str, str]] = None
    ) -> Dict[str, FlakyTestResult]:
        """
        Detect flaky tests in batch.
        
        Args:
            feature_map: Map of test_id to feature vector
            framework_map: Map of test_id to framework
            name_map: Optional map of test_id to test name
        
        Returns:
            Map of test_id to detection result
        """
        results = {}
        name_map = name_map or {}
        
        for test_id, features in feature_map.items():
            framework = framework_map.get(test_id, TestFramework.JUNIT)
            test_name = name_map.get(test_id)
            
            result = self.detect(features, framework, test_name)
            results[test_id] = result
        
        return results
    
    def _identify_indicators(self, features: FlakyFeatureVector) -> List[str]:
        """
        Identify primary indicators of flakiness.
        
        Returns human-readable reasons why a test might be flaky.
        """
        indicators = []
        
        # High failure rate but not always failing
        if 0.1 < features.failure_rate < 0.9:
            indicators.append(
                f"Inconsistent failures ({features.failure_rate:.1%} failure rate)"
            )
        
        # Frequent status changes
        if features.pass_fail_switch_rate > 0.3:
            indicators.append(
                f"Frequent pass/fail switching ({features.pass_fail_switch_rate:.1%})"
            )
        
        # High duration variance
        if features.duration_cv > 0.5:
            indicators.append(
                f"Unstable execution time (CV: {features.duration_cv:.2f})"
            )
        
        # Multiple error types
        if features.unique_error_count > 2:
            indicators.append(
                f"Multiple error types ({features.unique_error_count} different errors)"
            )
        
        # Retry dependency
        if features.retry_success_rate > 0.5:
            indicators.append(
                f"Often succeeds on retry ({features.retry_success_rate:.1%})"
            )
        
        # Recent failures
        if features.recent_failure_rate > 0.3 and features.recent_failure_rate < 1.0:
            indicators.append(
                f"Recent intermittent failures ({features.recent_failure_rate:.1%})"
            )
        
        # Same commit failures
        if features.same_commit_failure_rate > 0.2 and features.same_commit_failure_rate < 0.8:
            indicators.append(
                "Fails intermittently on same commit"
            )
        
        return indicators
    
    def save_model(self, path: Path) -> None:
        """
        Save trained model to disk.
        
        Args:
            path: Path to save model file
        """
        if not self.is_trained:
            raise RuntimeError("No trained model to save")
        
        model_data = {
            "model": self.model,
            "config": self.config,
            "training_date": self.training_date,
            "training_sample_count": self.training_sample_count,
            "model_version": self.config.model_version
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, path: Path) -> None:
        """
        Load trained model from disk.
        
        Args:
            path: Path to model file
        
        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data["model"]
        self.config = model_data["config"]
        self.training_date = model_data["training_date"]
        self.training_sample_count = model_data["training_sample_count"]
        self.is_trained = True
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores (approximation).
        
        Isolation Forest doesn't provide direct feature importance,
        but we can estimate it by analyzing the trees.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            return {}
        
        feature_names = [
            "failure_rate",
            "pass_fail_switch_rate",
            "duration_variance",
            "duration_cv",
            "retry_success_rate",
            "avg_retry_count",
            "unique_error_count",
            "error_diversity_ratio",
            "same_commit_failure_rate",
            "recent_failure_rate"
        ]
        
        # Note: This is a simplified importance calculation
        # For production, consider using permutation importance
        return {name: 1.0 / len(feature_names) for name in feature_names}


def create_flaky_report(
    results: Dict[str, FlakyTestResult],
    include_stable: bool = False
) -> dict:
    """
    Create a summary report of flaky test detection.
    
    Args:
        results: Detection results by test_id
        include_stable: Whether to include stable tests in report
    
    Returns:
        Dictionary with summary statistics and test details
    """
    all_tests = list(results.values())
    flaky_tests = [r for r in all_tests if r.is_flaky]
    suspected_tests = [
        r for r in all_tests
        if r.classification == "suspected_flaky"
    ]
    insufficient_data = [
        r for r in all_tests
        if r.classification == "insufficient_data"
    ]
    stable_tests = [
        r for r in all_tests
        if r.classification == "stable"
    ]
    
    # Group by severity
    critical_flaky = [r for r in flaky_tests if r.severity == "critical"]
    high_flaky = [r for r in flaky_tests if r.severity == "high"]
    medium_flaky = [r for r in flaky_tests if r.severity == "medium"]
    low_flaky = [r for r in flaky_tests if r.severity == "low"]
    
    report = {
        "summary": {
            "total_tests": len(all_tests),
            "flaky_tests": len(flaky_tests),
            "suspected_flaky": len(suspected_tests),
            "stable_tests": len(stable_tests),
            "insufficient_data": len(insufficient_data),
            "flaky_percentage": len(flaky_tests) / len(all_tests) * 100 if all_tests else 0
        },
        "severity_breakdown": {
            "critical": len(critical_flaky),
            "high": len(high_flaky),
            "medium": len(medium_flaky),
            "low": len(low_flaky)
        },
        "flaky_tests": [r.to_dict() for r in flaky_tests],
        "suspected_tests": [r.to_dict() for r in suspected_tests]
    }
    
    if include_stable:
        report["stable_tests"] = [r.to_dict() for r in stable_tests]
    
    return report
