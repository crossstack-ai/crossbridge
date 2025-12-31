"""
RestAssured + Java adapter for CrossBridge.

Supports REST API tests using RestAssured with TestNG or JUnit 5 frameworks.
"""

from .adapter import RestAssuredJavaAdapter
from .extractor import RestAssuredExtractor
from .detector import RestAssuredDetector
from .config import RestAssuredConfig

__all__ = [
    'RestAssuredJavaAdapter',
    'RestAssuredExtractor',
    'RestAssuredDetector',
    'RestAssuredConfig',
]
