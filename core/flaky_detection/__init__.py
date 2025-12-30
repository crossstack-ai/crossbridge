"""
Flaky Test Detection Module for CrossBridge.

Framework-agnostic flaky test detection using machine learning (Isolation Forest)
and historical execution analysis.

Phase-1: Base detection with unified model
Phase-2: Per-framework models, step-level detection, calibrated confidence

Supports all test frameworks: JUnit, TestNG, Pytest, Robot, Cucumber, etc.
"""

from .models import (
    TestExecutionRecord,
    FlakyFeatureVector,
    FlakyTestResult,
    TestStatus,
    TestFramework
)
from .detector import FlakyDetector, FlakyDetectionConfig
from .feature_engineering import FeatureEngineer

# Phase-2 exports
from .multi_framework_detector import (
    MultiFrameworkFlakyDetector,
    MultiFrameworkDetectorConfig
)
from .framework_features import (
    FrameworkFeatureExtractor,
    SeleniumFeatures,
    CucumberFeatures,
    PytestFeatures,
    RobotFeatures
)
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
    ConfidenceWeights,
    ConfidenceExplanation,
    create_confidence_explanation
)

__all__ = [
    # Phase-1 (Base)
    "TestExecutionRecord",
    "FlakyFeatureVector",
    "FlakyTestResult",
    "TestStatus",
    "TestFramework",
    "FlakyDetector",
    "FlakyDetectionConfig",
    "FeatureEngineer",
    
    # Phase-2 (Enhanced)
    "MultiFrameworkFlakyDetector",
    "MultiFrameworkDetectorConfig",
    "FrameworkFeatureExtractor",
    "SeleniumFeatures",
    "CucumberFeatures",
    "PytestFeatures",
    "RobotFeatures",
    "StepExecutionRecord",
    "StepFlakyResult",
    "ScenarioFlakyAnalysis",
    "StepFeatureEngineer",
    "ScenarioFlakinessAggregator",
    "ConfidenceCalibrator",
    "ConfidenceClassifier",
    "ConfidenceInputs",
    "ConfidenceWeights",
    "ConfidenceExplanation",
    "create_confidence_explanation",
]

