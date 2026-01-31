"""
Selenium .NET Adapter for CrossBridge.

This adapter provides comprehensive support for pure Selenium .NET tests (non-BDD).

Gap Implementations:
- Gap 5.1: Selenium .NET adapter implementation (adapter.py)
- Gap 5.2: Failure classification for .NET Selenium tests (failure_classifier.py)
"""

from .adapter import (
    SeleniumDotNetAdapter,
    SeleniumDotNetExtractor,
    SeleniumDotNetProjectDetector,
    SeleniumDotNetProjectConfig,
    DotNetTestFramework,
)

from .failure_classifier import (
    SeleniumDotNetFailureType,
    SeleniumDotNetFailureClassification,
    classify_selenium_dotnet_failure,
)

__all__ = [
    # Adapter
    'SeleniumDotNetAdapter',
    'SeleniumDotNetExtractor',
    'SeleniumDotNetProjectDetector',
    'SeleniumDotNetProjectConfig',
    'DotNetTestFramework',
    # Failure classification
    'SeleniumDotNetFailureType',
    'SeleniumDotNetFailureClassification',
    'classify_selenium_dotnet_failure',
]
