"""
Result Collection & Aggregation System for CrossStack-AI CrossBridge.

Provides unified result collection, aggregation, comparison, and trend analysis
across all test frameworks (pytest, JUnit, TestNG, Robot Framework, etc.).
"""

from .models import (
    TestResult,
    TestRunResult,
    TestStatus,
    FrameworkType,
    ResultMetadata,
    AggregatedResults,
    TrendData,
    ComparisonResult,
)
from .result_collector import (
    ResultCollector,
    UnifiedResultAggregator,
)
from .result_comparer import (
    ResultComparer,
    ComparisonStrategy,
)
from .trend_analyzer import (
    TrendAnalyzer,
    TrendMetric,
)
from .normalizer import (
    ResultNormalizer,
    FrameworkAdapter,
)

__all__ = [
    # Models
    'TestResult',
    'TestRunResult',
    'TestStatus',
    'FrameworkType',
    'ResultMetadata',
    'AggregatedResults',
    'TrendData',
    'ComparisonResult',
    
    # Collectors
    'ResultCollector',
    'UnifiedResultAggregator',
    
    # Comparison
    'ResultComparer',
    'ComparisonStrategy',
    
    # Trend Analysis
    'TrendAnalyzer',
    'TrendMetric',
    
    # Normalization
    'ResultNormalizer',
    'FrameworkAdapter',
]

__version__ = '1.0.0'
