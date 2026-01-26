"""
Unit tests for Performance Benchmark (Phase 4).
"""

import pytest
from core.benchmarking.performance import PerformanceBenchmark


class TestPerformanceBenchmark:
    """Test performance benchmarking."""
    
    def test_measure_execution_time(self):
        """Test execution time measurement."""
        benchmark = PerformanceBenchmark()
        
        def sample_func():
            return sum(range(1000))
        
        result = benchmark.measure_execution_time(sample_func)
        
        assert result['success'] is True
        assert result['duration'] > 0
    
    def test_benchmark_adapter(self):
        """Test adapter benchmarking."""
        benchmark = PerformanceBenchmark()
        
        def sample_operation():
            return [i * 2 for i in range(100)]
        
        result = benchmark.benchmark_adapter(
            'test_adapter',
            sample_operation,
            iterations=5
        )
        
        assert result['adapter'] == 'test_adapter'
        assert result['iterations'] == 5
        assert result['avg_duration'] > 0
    
    def test_get_performance_insights(self):
        """Test performance insights."""
        benchmark = PerformanceBenchmark()
        
        benchmark.benchmarks = [
            {
                'adapter': 'fast',
                'avg_duration': 0.1,
                'avg_memory_mb': 10,
                'failed_runs': 0,
                'iterations': 10,
            },
            {
                'adapter': 'slow',
                'avg_duration': 1.0,
                'avg_memory_mb': 50,
                'failed_runs': 0,
                'iterations': 10,
            },
        ]
        
        insights = benchmark.get_performance_insights()
        
        assert len(insights) > 0
