"""
RestAssured + TestNG adapter for CrossBridge.

Supports REST API testing with RestAssured and TestNG framework.
"""

from .adapter import RestAssuredTestNGAdapter
from .extractor import RestAssuredExtractor
from .detector import RestAssuredDetector
from .config import RestAssuredConfig

__all__ = [
    'RestAssuredTestNGAdapter',
    'RestAssuredExtractor',
    'RestAssuredDetector',
    'RestAssuredConfig',
]
