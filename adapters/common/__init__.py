"""
Common adapters package.

Shared utilities and models for all test framework adapters.
"""
from .base import BaseTestExtractor, TestFrameworkAdapter
from .models import (
    TestMetadata,
    TestStep,
    Assertion,
    AssertionType,
    IntentModel,
    TestStatus,
    ExecutionResult,
    CoverageData
)
from .normalizer import UniversalTestNormalizer
from .memory_integration import (
    MemoryIntegrationMixin,
    add_memory_support_to_adapter,
    cypress_to_memory,
    playwright_to_memory,
    robot_to_memory,
    pytest_to_memory,
    junit_to_memory,
    testng_to_memory,
    restassured_to_memory,
    selenium_to_memory,
    cucumber_to_memory,
    behave_to_memory,
    specflow_to_memory,
)

__all__ = [
    'BaseTestExtractor',
    'TestFrameworkAdapter',
    'TestMetadata',
    'TestStep',
    'Assertion',
    'AssertionType',
    'IntentModel',
    'TestStatus',
    'ExecutionResult',
    'CoverageData',
    # Memory & Embedding Integration
    'UniversalTestNormalizer',
    'MemoryIntegrationMixin',
    'add_memory_support_to_adapter',
    # Framework-specific converters
    'cypress_to_memory',
    'playwright_to_memory',
    'robot_to_memory',
    'pytest_to_memory',
    'junit_to_memory',
    'testng_to_memory',
    'restassured_to_memory',
    'selenium_to_memory',
    'cucumber_to_memory',
    'behave_to_memory',
    'specflow_to_memory',
]
