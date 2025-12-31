"""
Selenium + Behave adapter for CrossBridge.

This adapter supports Selenium WebDriver tests written with Behave (Python BDD framework).
"""

from .adapter import (
    SeleniumBehaveAdapter,
    SeleniumBehaveExtractor,
    SeleniumBehaveDetector
)

__all__ = [
    'SeleniumBehaveAdapter',
    'SeleniumBehaveExtractor',
    'SeleniumBehaveDetector',
]
