"""
Selenium BDD Java Adapter for CrossBridge AI.

Supports Cucumber/Gherkin feature file extraction for Java-based BDD tests.
"""

from .extractor import SeleniumBDDJavaExtractor
from .config import SeleniumBDDJavaConfig

__all__ = ["SeleniumBDDJavaExtractor", "SeleniumBDDJavaConfig"]
