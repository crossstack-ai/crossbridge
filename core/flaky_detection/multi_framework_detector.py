"""
Multi-Framework Flaky Detection System.

Implements per-framework Isolation Forest models with:
- Framework-specific feature extraction
- Separate models per framework for better separation
- Step-level detection for BDD/keyword frameworks
- Enhanced confidence calibration

This is the main entry point for multi-framework flaky detection.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

from core.logging import get_logger, LogCategory
from .models import (
    TestExecutionRecord,
    FlakyFeatureVector,
    FlakyTestResult,
    TestFramework,
    TestStatus
)
from .feature_engineering import FeatureEngineer
from .framework_features import FrameworkFeatureExtractor

logger = get_logger(__name__, category=LogCategory.TESTING)
from .step_detection import (
    StepExecutionRecord,
    StepFlakyResult,
    ScenarioFlakyAnalysis,
    StepFeatureEngineer,
    ScenarioFlakinessAggregator
)
from .confidence_calibration import (
    ConfidenceCalibrator,
    ConfidenceClassifier,
    ConfidenceInputs,
    create_confidence_explanation
)


@dataclass
class MultiFrameworkDetectorConfig:
    """Configuration for multi-framework detector."""
    
    # Isolation Forest parameters (per framework)
    n_estimators: int = 200
    contamination: float = 0.1
    random_state: int = 42
    
    # Confidence calibration
    min_executions_reliable: int = 15
    min_executions_confident: int = 30
    min_days_reliable: int = 7
    min_days_confident: int = 14
    min_environments: int = 2
    
    # Thresholds
    confident_threshold: float = 0.7
    suspected_threshold: float = 0.5
    
    # Step-level detection
    enable_step_detection: bool = True
    min_step_executions: int = 10
    
    # Model management
    model_version: str = "2.0.0"
    models_dir: Optional[Path] = None


class MultiFrameworkFlakyDetector:
    """
    Phase-2 flaky detector with per-framework models.
    
    Key improvements over Phase-1:
    - Separate Isolation Forest per framework
    - Framework-specific features
    - Step-level detection for BDD
    - Multi-dimensional confidence
    """
    
    def __init__(self, config: Optional[MultiFrameworkDetectorConfig] = None):
        """Initialize multi-framework detector."""
        self.config = config or MultiFrameworkDetectorConfig()
        
        # Per-framework models
        self.models: Dict[TestFramework, IsolationForest] = {}
        
        # Feature extractors
        self.base_feature_engineer = FeatureEngineer()
        self.framework_feature_extractor = FrameworkFeatureExtractor()
        
        # Step-level components
        self.step_feature_engineer = StepFeatureEngineer(
            min_executions_reliable=self.config.min_step_executions
        )
        self.scenario_aggregator = ScenarioFlakinessAggregator()
        
        # Confidence components
        self.confidence_calibrator = ConfidenceCalibrator(
            min_executions_reliable=self.config.min_executions_reliable,
            min_executions_confident=self.config.min_executions_confident,
            min_days_reliable=self.config.min_days_reliable,
            min_days_confident=self.config.min_days_confident,
            min_environments=self.config.min_environments
        )
        self.confidence_classifier = ConfidenceClassifier(
            confident_threshold=self.config.confident_threshold,
            suspected_threshold=self.config.suspected_threshold
        )
        
        # Training state
        self.is_trained: Dict[TestFramework, bool] = {}
    
    def train(
        self,
        all_executions: Dict[str, List[TestExecutionRecord]],
        framework_map: Dict[str, TestFramework]
    ):
        """
        Train per-framework models.
        
        Args:
            all_executions: Map of test_id -> execution history
            framework_map: Map of test_id -> framework
        """
        # Group tests by framework
        framework_groups: Dict[TestFramework, Dict[str, List[TestExecutionRecord]]] = {}
        
        for test_id, executions in all_executions.items():
            framework = framework_map.get(test_id)
            if not framework:
                continue
            
            if framework not in framework_groups:
                framework_groups[framework] = {}
            
            framework_groups[framework][test_id] = executions
        
        # Train one model per framework
        for framework, tests in framework_groups.items():
            self._train_framework_model(framework, tests)
    
    def _train_framework_model(
        self,
        framework: TestFramework,
        test_executions: Dict[str, List[TestExecutionRecord]]
    ):
        """Train Isolation Forest for specific framework."""
        # Extract features for all tests
        feature_vectors = []
        
        for test_id, executions in test_executions.items():
            # Base features
            base_features = self.base_feature_engineer.extract_features(executions)
            
            # Framework-specific features
            framework_features = self.framework_feature_extractor.extract(
                executions, framework
            )
            
            # Combine features
            combined_features = base_features.to_array() + framework_features
            feature_vectors.append(combined_features)
        
        if not feature_vectors:
            return
        
        # Convert to numpy array
        X = np.array(feature_vectors)
        
        # Train Isolation Forest
        model = IsolationForest(
            n_estimators=self.config.n_estimators,
            contamination=self.config.contamination,
            random_state=self.config.random_state,
            n_jobs=-1
        )
        
        model.fit(X)
        
        # Store model
        self.models[framework] = model
        self.is_trained[framework] = True
    
    def detect(
        self,
        test_id: str,
        executions: List[TestExecutionRecord],
        framework: TestFramework
    ) -> FlakyTestResult:
        """
        Detect flakiness for a single test.
        
        Args:
            test_id: Test identifier
            executions: Execution history
            framework: Test framework
            
        Returns:
            Flakiness detection result
        """
        # Extract features
        base_features = self.base_feature_engineer.extract_features(executions)
        framework_features_array = self.framework_feature_extractor.extract(
            executions, framework
        )
        
        # Combine features
        combined_features = base_features.to_array() + framework_features_array
        X = np.array([combined_features])
        
        # Get model for this framework
        model = self.models.get(framework)
        
        if not model or not self.is_trained.get(framework, False):
            # No model trained, return insufficient data
            return self._create_insufficient_result(
                test_id, executions, base_features, framework
            )
        
        # Predict
        anomaly_score = model.decision_function(X)[0]
        is_anomaly = model.predict(X)[0] == -1
        
        # Calculate confidence
        confidence = self.confidence_calibrator.calculate_confidence_from_history(
            executions
        )
        
        # Classify with confidence
        classification = self.confidence_classifier.classify(
            is_flaky_prediction=is_anomaly,
            flaky_score=anomaly_score,
            confidence=confidence
        )
        
        # Determine severity
        severity = self.confidence_classifier.classify_severity(
            classification=classification,
            failure_rate=base_features.failure_rate,
            confidence=confidence
        )
        
        # Identify indicators
        indicators = self._identify_indicators(base_features, framework_features_array)
        
        return FlakyTestResult(
            test_id=test_id,
            test_name=executions[0].test_name if executions else None,
            framework=framework,
            flaky_score=float(anomaly_score),
            is_flaky=(classification in ("flaky", "suspected_flaky")),
            confidence=confidence,
            features=base_features,
            detected_at=datetime.now(),
            model_version=self.config.model_version,
            primary_indicators=indicators
        )
    
    def detect_batch(
        self,
        all_executions: Dict[str, List[TestExecutionRecord]],
        framework_map: Dict[str, TestFramework]
    ) -> Dict[str, FlakyTestResult]:
        """
        Detect flakiness for multiple tests.
        
        Args:
            all_executions: Map of test_id -> execution history
            framework_map: Map of test_id -> framework
            
        Returns:
            Map of test_id -> detection result
        """
        results = {}
        
        for test_id, executions in all_executions.items():
            framework = framework_map.get(test_id, TestFramework.UNKNOWN)
            results[test_id] = self.detect(test_id, executions, framework)
        
        return results
    
    def detect_steps(
        self,
        scenario_id: str,
        scenario_name: str,
        step_executions: Dict[str, List[StepExecutionRecord]],
        framework: TestFramework
    ) -> ScenarioFlakyAnalysis:
        """
        Detect flakiness at step level (for BDD/keyword frameworks).
        
        Args:
            scenario_id: Scenario identifier
            scenario_name: Human-readable name
            step_executions: Map of step_id -> execution history
            framework: Test framework
            
        Returns:
            Scenario-level analysis with step-level details
        """
        if not self.config.enable_step_detection:
            raise ValueError("Step detection is disabled in config")
        
        # Extract features for each step
        step_features = self.step_feature_engineer.extract_batch_features(
            step_executions
        )
        
        # Train step-level model (if not already trained)
        # For simplicity, we use the framework's model or train a new one
        step_model = self._get_or_train_step_model(step_features, framework)
        
        # Detect flakiness for each step
        step_results = []
        
        for step_id, features in step_features.items():
            if not features.is_reliable:
                # Skip steps with insufficient data
                continue
            
            # Predict
            X = np.array([features.to_array()])
            anomaly_score = step_model.decision_function(X)[0]
            is_anomaly = step_model.predict(X)[0] == -1
            
            # Calculate confidence
            executions = step_executions[step_id]
            confidence = self.confidence_calibrator.calculate_confidence_from_history(
                executions  # type: ignore
            )
            
            # Classify
            classification = self.confidence_classifier.classify(
                is_flaky_prediction=is_anomaly,
                flaky_score=anomaly_score,
                confidence=confidence
            )
            
            # Create result
            step_result = StepFlakyResult(
                step_id=step_id,
                step_text=executions[0].step_text if executions else "",
                scenario_id=scenario_id,
                framework=framework,
                flaky_score=float(anomaly_score),
                is_flaky=(classification in ("flaky", "suspected_flaky")),
                confidence=confidence,
                features=features,
                detected_at=datetime.now(),
                model_version=self.config.model_version,
                primary_indicators=self._identify_step_indicators(features)
            )
            
            step_results.append(step_result)
        
        # Aggregate to scenario level
        return self.scenario_aggregator.aggregate(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            step_results=step_results,
            framework=framework
        )
    
    def _get_or_train_step_model(
        self,
        step_features: Dict[str, 'StepFlakyFeatureVector'],
        framework: TestFramework
    ) -> IsolationForest:
        """Get or train step-level model."""
        # For now, reuse framework model or create new one
        if framework in self.models:
            return self.models[framework]
        
        # Train new model
        feature_vectors = [
            f.to_array() for f in step_features.values()
            if f.is_reliable
        ]
        
        if not feature_vectors:
            # Create dummy model
            return IsolationForest(
                n_estimators=self.config.n_estimators,
                contamination=self.config.contamination,
                random_state=self.config.random_state
            )
        
        X = np.array(feature_vectors)
        
        model = IsolationForest(
            n_estimators=self.config.n_estimators // 2,  # Smaller model for steps
            contamination=0.15,  # Higher contamination for steps
            random_state=self.config.random_state,
            n_jobs=-1
        )
        
        model.fit(X)
        return model
    
    def _create_insufficient_result(
        self,
        test_id: str,
        executions: List[TestExecutionRecord],
        features: FlakyFeatureVector,
        framework: TestFramework
    ) -> FlakyTestResult:
        """Create result for insufficient data."""
        return FlakyTestResult(
            test_id=test_id,
            test_name=executions[0].test_name if executions else None,
            framework=framework,
            flaky_score=0.0,
            is_flaky=False,
            confidence=0.0,
            features=features,
            detected_at=datetime.now(),
            model_version=self.config.model_version,
            primary_indicators=[]
        )
    
    def _identify_indicators(
        self,
        base_features: FlakyFeatureVector,
        framework_features: List[float]
    ) -> List[str]:
        """Identify primary flakiness indicators."""
        indicators = []
        
        # Base features
        if base_features.failure_rate > 0.3 and base_features.failure_rate < 0.7:
            indicators.append(
                f"Inconsistent failures ({base_features.failure_rate:.1%})"
            )
        
        if base_features.pass_fail_switch_rate > 0.3:
            indicators.append(
                f"Frequent pass/fail switching ({base_features.pass_fail_switch_rate:.1%})"
            )
        
        if base_features.unique_error_count > 2:
            indicators.append(
                f"Multiple error types ({base_features.unique_error_count})"
            )
        
        if base_features.duration_cv > 0.5:
            indicators.append(
                f"High duration variance (CV={base_features.duration_cv:.2f})"
            )
        
        if base_features.retry_success_rate > 0.5:
            indicators.append(
                f"Often passes on retry ({base_features.retry_success_rate:.1%})"
            )
        
        # Limit to top 3 indicators
        return indicators[:3]
    
    def _identify_step_indicators(
        self,
        features: 'StepFlakyFeatureVector'
    ) -> List[str]:
        """Identify primary flakiness indicators for a step."""
        indicators = []
        
        if features.step_failure_rate > 0.3:
            indicators.append(
                f"High step failure rate ({features.step_failure_rate:.1%})"
            )
        
        if features.step_pass_fail_switch_rate > 0.3:
            indicators.append(
                f"Frequent switching ({features.step_pass_fail_switch_rate:.1%})"
            )
        
        if features.step_duration_cv > 0.5:
            indicators.append(
                f"Unstable execution time (CV={features.step_duration_cv:.2f})"
            )
        
        if features.position_sensitivity > 0.2:
            indicators.append("Position-dependent failures")
        
        return indicators[:3]
    
    def save_models(self, directory: Path):
        """Save all trained models to disk."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        for framework, model in self.models.items():
            model_file = directory / f"model_{framework.value}.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
    
    def load_models(self, directory: Path):
        """Load trained models from disk."""
        directory = Path(directory)
        
        for framework in TestFramework:
            model_file = directory / f"model_{framework.value}.pkl"
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    self.models[framework] = pickle.load(f)
                    self.is_trained[framework] = True
