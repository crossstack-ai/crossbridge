"""
Robot Framework adapter for CrossBridge.

This adapter supports Robot Framework tests with enhanced features.

Gap Implementations:
- Gap 6.1: Failure classification (failure_classifier.py)
- Gap 6.2: Metadata extraction (metadata_extractor.py)
- Gap 6.3: Static parser for discovery (static_parser.py)
"""

from .robot_adapter import RobotAdapter, RobotExtractor, RobotDetector
from .config import RobotConfig
from .keyword_library_analyzer import KeywordLibraryAnalyzer

# Failure classification (Gap 6.1)
from .failure_classifier import (
    RobotFailureType,
    RobotFailureClassification,
    classify_robot_failure,
)

# Metadata extraction (Gap 6.2)
from .metadata_extractor import (
    RobotMetadata,
    CIMetadata,
    BrowserMetadata,
    ExecutionContext,
    ExecutionEnvironment,
    extract_robot_metadata,
    enrich_test_result_with_metadata,
)

# Static parser (Gap 6.3)
from .static_parser import (
    RobotStaticParser,
    RobotFileParser,
    RobotTest,
    RobotSuite,
    RobotSection,
)

__all__ = [
    'RobotAdapter',
    'RobotExtractor',
    'RobotDetector',
    'RobotConfig',
    'KeywordLibraryAnalyzer',
    # Failure classification
    'RobotFailureType',
    'RobotFailureClassification',
    'classify_robot_failure',
    # Metadata extraction
    'RobotMetadata',
    'CIMetadata',
    'BrowserMetadata',
    'ExecutionContext',
    'ExecutionEnvironment',
    'extract_robot_metadata',
    'enrich_test_result_with_metadata',
    # Static parser
    'RobotStaticParser',
    'RobotFileParser',
    'RobotTest',
    'RobotSuite',
    'RobotSection',
]
