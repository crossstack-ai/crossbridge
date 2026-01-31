"""
RestAssured + Java adapter for CrossBridge.

Supports REST API tests using RestAssured with TestNG or JUnit 5 frameworks.

Enhanced with intelligent failure classification and comprehensive metadata extraction
for API test analysis and CI/CD integration.
"""

from .adapter import RestAssuredJavaAdapter
from .extractor import RestAssuredExtractor
from .detector import RestAssuredDetector
from .config import RestAssuredConfig

# Failure classification (Gap 1.1)
try:
    from .failure_classifier import (
        RestAssuredFailureClassifier,
        APIFailureType,
        APIComponentType,
        classify_api_failure
    )
    _FAILURE_CLASSIFIER_AVAILABLE = True
except ImportError:
    _FAILURE_CLASSIFIER_AVAILABLE = False

# Metadata extraction (Gap 1.2)
try:
    from .metadata_extractor import (
        RestAssuredMetadataExtractor,
        RestAssuredTestMetadata,
        APIMetadata,
        CIMetadata,
        ExecutionContext,
        TestGrouping,
        extract_restassured_metadata
    )
    _METADATA_EXTRACTOR_AVAILABLE = True
except ImportError:
    _METADATA_EXTRACTOR_AVAILABLE = False

__all__ = [
    'RestAssuredJavaAdapter',
    'RestAssuredExtractor',
    'RestAssuredDetector',
    'RestAssuredConfig',
]

# Add failure classifier exports if available
if _FAILURE_CLASSIFIER_AVAILABLE:
    __all__.extend([
        'RestAssuredFailureClassifier',
        'APIFailureType',
        'APIComponentType',
        'classify_api_failure',
    ])

# Add metadata extractor exports if available
if _METADATA_EXTRACTOR_AVAILABLE:
    __all__.extend([
        'RestAssuredMetadataExtractor',
        'RestAssuredTestMetadata',
        'APIMetadata',
        'CIMetadata',
        'ExecutionContext',
        'TestGrouping',
        'extract_restassured_metadata',
    ])
