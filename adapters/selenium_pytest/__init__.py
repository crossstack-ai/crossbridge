"""
Selenium + Pytest adapter for CrossBridge.

This adapter supports Selenium WebDriver tests written with pytest as the test runner.
"""

from .adapter import (
    SeleniumPytestAdapter,
    SeleniumPytestExtractor,
    SeleniumPytestDetector
)

__all__ = [
    'SeleniumPytestAdapter',
    'SeleniumPytestExtractor',
    'SeleniumPytestDetector',
]
