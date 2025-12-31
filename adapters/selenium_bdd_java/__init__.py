"""
Selenium BDD Java Adapter for CrossBridge.

Supports Cucumber/Gherkin feature file extraction for Java-based BDD tests.
Includes Cucumber JSON report parsing for execution result analysis.
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
