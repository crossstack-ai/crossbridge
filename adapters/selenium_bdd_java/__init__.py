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
