"""
Selenium + Behave adapter for CrossBridge.

This adapter supports Selenium WebDriver tests written with Behave (Python BDD framework).
"""

from .adapter import (
    SeleniumBehaveAdapter,
    SeleniumBehaveExtractor,
    SeleniumBehaveDetector
)
from .tag_inheritance_handler import TagInheritanceHandler
from .scenario_outline_handler import ScenarioOutlineHandler

__all__ = [
    'SeleniumBehaveAdapter',
    'SeleniumBehaveExtractor',
    'SeleniumBehaveDetector',
    'TagInheritanceHandler',
    'ScenarioOutlineHandler',
]
