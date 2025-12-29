"""
Selenium-Java adapter package.

Provides test execution capabilities for Selenium-Java projects using:
- Maven or Gradle build tools
- JUnit 4, JUnit 5, or TestNG frameworks

Key principle: Delegates execution to native Java build tools rather than
reimplementing test execution logic in Python.
"""

from .adapter import SeleniumJavaAdapter, run_selenium_java_tests
from .models import (
    TestExecutionRequest,
    TestExecutionResult,
    BuildToolConfig,
    TestFrameworkConfig
)

__all__ = [
    "SeleniumJavaAdapter",
    "run_selenium_java_tests",
    "TestExecutionRequest",
    "TestExecutionResult",
    "BuildToolConfig",
    "TestFrameworkConfig"
]
