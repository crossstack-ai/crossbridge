"""
Selenium BDD Java Adapter for CrossBridge.

Supports Cucumber/Gherkin feature file extraction for Java-based BDD tests.
Includes Cucumber JSON report parsing for execution result analysis.

New Features (Production-Ready):
- Structured failure classification (Gap 1)
- Scenario outline expansion support (Gap 2)
- Environment & browser metadata extraction (Gap 3)
"""

from .extractor import SeleniumBDDJavaExtractor
from .config import SeleniumBDDJavaConfig
from .cucumber_json_parser import (
    parse_cucumber_json,
    parse_multiple_cucumber_reports,
    CucumberJsonParseError
)
from .models import (
    FeatureResult,
    ScenarioResult,
    StepResult
)

# Import failure classifier (Gap 1 - Critical)
try:
    from .failure_classifier import (
        FailureClassifier,
        FailureClassification,
        FailureType,
        FailureComponent,
        classify_failure
    )
    _FAILURE_CLASSIFIER_AVAILABLE = True
except ImportError:
    _FAILURE_CLASSIFIER_AVAILABLE = False

# Import metadata extractor (Gap 3 - Critical)
try:
    from .metadata_extractor import (
        MetadataExtractor,
        TestMetadata,
        BrowserMetadata,
        ExecutionContext,
        extract_metadata
    )
    _METADATA_AVAILABLE = True
except ImportError:
    _METADATA_AVAILABLE = False

# Import step definition parser for migration
try:
    from .step_definition_parser import (
        JavaStepDefinitionParser,
        StepDefinitionIntent,
        StepDefinitionMapper,
        SeleniumAction,
        PageObjectCall,
        translate_selenium_to_playwright,
        SELENIUM_TO_PLAYWRIGHT
    )
    _STEP_PARSER_AVAILABLE = True
except ImportError:
    _STEP_PARSER_AVAILABLE = False

__all__ = [
    "SeleniumBDDJavaExtractor",
    "SeleniumBDDJavaConfig",
    "parse_cucumber_json",
    "parse_multiple_cucumber_reports",
    "CucumberJsonParseError",
    "FeatureResult",
    "ScenarioResult",
    "StepResult",
]

if _FAILURE_CLASSIFIER_AVAILABLE:
    __all__.extend([
        "FailureClassifier",
        "FailureClassification",
        "FailureType",
        "FailureComponent",
        "classify_failure"
    ])

if _METADATA_AVAILABLE:
    __all__.extend([
        "MetadataExtractor",
        "TestMetadata",
        "BrowserMetadata",
        "ExecutionContext",
        "extract_metadata"
    ])

if _STEP_PARSER_AVAILABLE:
    __all__.extend([
        "JavaStepDefinitionParser",
        "StepDefinitionIntent",
        "StepDefinitionMapper",
        "SeleniumAction",
        "PageObjectCall",
        "translate_selenium_to_playwright",
        "SELENIUM_TO_PLAYWRIGHT"
    ])

