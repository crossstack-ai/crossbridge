"""
Result Collection & Aggregation Module.

Provides unified result aggregation, cross-run comparison, and historical
trend analysis for test execution results across all frameworks.

Key Features:
- Unified result aggregation from multiple sources
- Cross-run result comparison
- Historical trend analysis
- Result normalization across frameworks
- Statistical analysis (flaky detection, success rates, duration trends)

Example Usage:
    from core.results import ResultAggregator, ResultComparator, TrendAnalyzer
    
    # Aggregate results from multiple runs
    aggregator = ResultAggregator()
    aggregator.add_execution_result(summary1)
    aggregator.add_coverage_data(coverage1)
    aggregator.add_flaky_data(flaky1)
    
    unified = aggregator.get_unified_results()
    
    # Compare across runs
    comparator = ResultComparator()
    comparison = comparator.compare_runs(run1, run2)
    
    # Analyze trends
    analyzer = TrendAnalyzer()
    trends = analyzer.analyze_trends(historical_data)
"""

from .models import (
    UnifiedTestResult,
    ResultSource,
    AggregatedResults,
    RunComparison,
    TrendMetrics,
    StatisticalMetrics,
    TestStatus,
    TrendDirection
)

from .aggregator import (
    ResultAggregator,
    ResultNormalizer
)

from .comparator import (
    ResultComparator,
    ComparisonReport
)

from .analyzer import (
    TrendAnalyzer,
    HistoricalAnalyzer,
    StatisticalAnalyzer
)

__all__ = [
    # Models
    'UnifiedTestResult',
    'ResultSource',
    'AggregatedResults',
    'RunComparison',
    'TrendMetrics',
    'StatisticalMetrics',
    'TestStatus',
    'TrendDirection',
    
    # Aggregation
    'ResultAggregator',
    'ResultNormalizer',
    
    # Comparison
    'ResultComparator',
    'ComparisonReport',
    
    # Analysis
    'TrendAnalyzer',
    'HistoricalAnalyzer',
    'StatisticalAnalyzer',
]
