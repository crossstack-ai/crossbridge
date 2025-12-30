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
]
