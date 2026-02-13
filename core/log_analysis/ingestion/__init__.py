"""
Log Ingestion Module

Structured parsing and correlation of test framework artifacts.
Provides deterministic failure analysis from multiple log sources.
"""

from .log_artifacts import LogArtifacts, StructuredFailure, FailureCategory
from .testng_parser import TestNGParser
from .framework_log_parser import FrameworkLogParser
from .correlation_engine import CorrelationEngine, CorrelatedFailure

__all__ = [
    'LogArtifacts',
    'StructuredFailure',
    'FailureCategory',
    'TestNGParser',
    'FrameworkLogParser',
    'CorrelationEngine',
    'CorrelatedFailure',
]
