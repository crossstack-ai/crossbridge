"""
Unit tests for Result Collection & Aggregation system.

Tests:
- Result models
- Normalization across frameworks
- Result collection and aggregation
- Cross-run comparison
- Trend analysis
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile

from core.execution.results.models import (
    TestResult,
    TestRunResult,
    TestStatus,
    FrameworkType,
    ResultMetadata,
    AggregatedResults,
    ComparisonResult,
    TrendData,
    TrendPoint,
)
from core.execution.results.normalizer import (
    ResultNormalizer,
    PytestAdapter,
    JUnitAdapter,
    TestNGAdapter,
)
from core.execution.results.result_collector import (
    UnifiedResultAggregator,
    FlakyTestCollector,
    CoverageCollector,
)
from core.execution.results.result_comparer import (
    ResultComparer,
    ComparisonStrategy,
)
from core.execution.results.trend_analyzer import (
    TrendAnalyzer,
    TrendMetric,
)


class TestModels:
    """Test data models."""
    
    def test_test_result_creation(self):
        """Test creating a test result."""
        result = TestResult(
            test_id="test_example",
            test_name="test_example",
            status=TestStatus.PASSED,
            duration=1.5,
        )
        
        assert result.test_id == "test_example"
        assert result.status == TestStatus.PASSED
        assert result.duration == 1.5
        assert not result.is_flaky
    
    def test_test_run_result_statistics(self):
        """Test run result calculates statistics."""
        tests = [
            TestResult("test1", "test1", status=TestStatus.PASSED, duration=1.0),
            TestResult("test2", "test2", status=TestStatus.PASSED, duration=1.0),
            TestResult("test3", "test3", status=TestStatus.FAILED, duration=1.0),
            TestResult("test4", "test4", status=TestStatus.SKIPPED, duration=0.0),
        ]
        
        run = TestRunResult(
            run_id="run1",
            start_time=datetime.now(),
            tests=tests,
        )
        
        assert run.total_tests == 4
        assert run.passed == 2
        assert run.failed == 1
        assert run.skipped == 1
        assert run.pass_rate == 50.0
    
    def test_aggregated_results(self):
        """Test aggregated results calculation."""
        run1 = TestRunResult(
            run_id="run1",
            start_time=datetime.now(),
            tests=[
                TestResult("test1", "test1", status=TestStatus.PASSED),
                TestResult("test2", "test2", status=TestStatus.FAILED),
            ],
        )
        
        run2 = TestRunResult(
            run_id="run2",
            start_time=datetime.now(),
            tests=[
                TestResult("test1", "test1", status=TestStatus.PASSED),
                TestResult("test3", "test3", status=TestStatus.PASSED),
            ],
        )
        
        agg = AggregatedResults(runs=[run1, run2])
        
        assert agg.total_runs == 2
        assert agg.total_tests == 4
        assert agg.unique_tests == 3  # test1, test2, test3


class TestNormalizer:
    """Test result normalization."""
    
    def test_pytest_normalizer(self):
        """Test pytest result normalization."""
        pytest_data = {
            "pytest_version": "7.0.0",
            "python_version": "3.10",
            "created": datetime.now().timestamp(),
            "duration": 10.5,
            "tests": [
                {
                    "nodeid": "tests/test_example.py::test_function",
                    "name": "test_function",
                    "file": "tests/test_example.py",
                    "function": "test_function",
                    "outcome": "passed",
                    "duration": 1.5,
                    "markers": ["unit"],
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pytest_data, f)
            temp_file = Path(f.name)
        
        try:
            adapter = PytestAdapter()
            result = adapter.parse_results(temp_file)
            
            assert result.tests[0].test_name == "test_function"
            assert result.tests[0].status == TestStatus.PASSED
            assert result.tests[0].duration == 1.5
        finally:
            temp_file.unlink()
    
    def test_status_normalization(self):
        """Test status normalization across frameworks."""
        pytest_adapter = PytestAdapter()
        assert pytest_adapter.normalize_status("passed") == TestStatus.PASSED
        assert pytest_adapter.normalize_status("failed") == TestStatus.FAILED
        assert pytest_adapter.normalize_status("skipped") == TestStatus.SKIPPED
        
        junit_adapter = JUnitAdapter()
        assert junit_adapter.normalize_status("success") == TestStatus.PASSED
        assert junit_adapter.normalize_status("failure") == TestStatus.FAILED
    
    def test_framework_detection(self):
        """Test automatic framework detection."""
        normalizer = ResultNormalizer()
        
        # Create pytest JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"pytest_version": "7.0.0", "tests": []}, f)
            pytest_file = Path(f.name)
        
        try:
            framework = normalizer.detect_framework(pytest_file)
            assert framework == FrameworkType.PYTEST
        finally:
            pytest_file.unlink()


class TestResultCollector:
    """Test result collection and aggregation."""
    
    def test_flaky_collector(self):
        """Test flaky test collection."""
        flaky_data = {
            "flaky_tests": {
                "test_example": {
                    "name": "test_example",
                    "runs": ["passed", "failed", "passed"],
                    "pass_rate": 66.7,
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(flaky_data, f)
            temp_file = Path(f.name)
        
        try:
            collector = FlakyTestCollector()
            results = collector.collect(temp_file)
            
            assert len(results) == 1
            assert results[0].is_flaky
            assert results[0].pass_rate == 66.7
        finally:
            temp_file.unlink()
    
    def test_unified_aggregator(self):
        """Test unified result aggregation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir)
            aggregator = UnifiedResultAggregator(storage_path=storage_path)
            
            # Create sample pytest result
            pytest_data = {
                "pytest_version": "7.0.0",
                "created": datetime.now().timestamp(),
                "duration": 5.0,
                "tests": [
                    {
                        "nodeid": "test_example",
                        "name": "test_example",
                        "outcome": "passed",
                        "duration": 1.0,
                    }
                ]
            }
            
            result_file = storage_path / "results.json"
            with open(result_file, 'w') as f:
                json.dump(pytest_data, f)
            
            # Aggregate
            result = aggregator.aggregate_run(
                result_files=[result_file],
                framework=FrameworkType.PYTEST,
                run_id="test_run"
            )
            
            assert result.run_id == "test_run"
            assert len(result.tests) == 1
            assert result.passed == 1


class TestResultComparer:
    """Test cross-run comparison."""
    
    def test_compare_runs(self):
        """Test comparing two test runs."""
        baseline = TestRunResult(
            run_id="baseline",
            start_time=datetime.now(),
            tests=[
                TestResult("test1", "test1", status=TestStatus.PASSED, duration=1.0),
                TestResult("test2", "test2", status=TestStatus.FAILED, duration=2.0),
            ],
            overall_coverage=80.0,
        )
        
        current = TestRunResult(
            run_id="current",
            start_time=datetime.now(),
            tests=[
                TestResult("test1", "test1", status=TestStatus.PASSED, duration=0.5),
                TestResult("test2", "test2", status=TestStatus.PASSED, duration=2.0),
                TestResult("test3", "test3", status=TestStatus.PASSED, duration=1.0),
            ],
            overall_coverage=85.0,
        )
        
        comparer = ResultComparer(performance_threshold=0.3)
        comparison = comparer.compare(baseline, current)
        
        assert len(comparison.new_tests) == 1
        assert comparison.new_tests[0].test_id == "test3"
        assert len(comparison.newly_passing) == 1
        assert comparison.newly_passing[0].test_id == "test2"
        assert comparison.coverage_improved
        assert comparison.coverage_delta == 5.0
    
    def test_performance_changes(self):
        """Test performance change detection."""
        baseline = TestRunResult(
            run_id="baseline",
            start_time=datetime.now(),
            tests=[
                TestResult("test1", "test1", status=TestStatus.PASSED, duration=1.0),
            ],
        )
        
        current = TestRunResult(
            run_id="current",
            start_time=datetime.now(),
            tests=[
                TestResult("test1", "test1", status=TestStatus.PASSED, duration=2.0),
            ],
        )
        
        comparer = ResultComparer(performance_threshold=0.5)
        comparison = comparer.compare(baseline, current)
        
        assert len(comparison.slower_tests) == 1
        assert comparison.slower_tests[0][0] == "test1"
    
    def test_comparison_summary(self):
        """Test comparison summary generation."""
        comparison = ComparisonResult(
            run1_id="run1",
            run2_id="run2",
            newly_passing=[TestResult("test1", "test1", status=TestStatus.PASSED)],
            newly_failing=[TestResult("test2", "test2", status=TestStatus.FAILED)],
        )
        
        comparer = ResultComparer()
        summary = comparer.generate_summary(comparison)
        
        assert "run1" in summary
        assert "run2" in summary
        assert "Newly passing: 1" in summary
        assert "Newly failing: 1" in summary


class TestTrendAnalyzer:
    """Test trend analysis."""
    
    def test_analyze_pass_rate_trend(self):
        """Test pass rate trend analysis."""
        runs = []
        base_time = datetime.now() - timedelta(days=10)
        
        # Create runs with improving pass rate
        for i in range(5):
            tests = [
                TestResult(f"test{j}", f"test{j}", 
                          status=TestStatus.PASSED if j < 7 + i else TestStatus.FAILED)
                for j in range(10)
            ]
            run = TestRunResult(
                run_id=f"run{i}",
                start_time=base_time + timedelta(days=i*2),
                tests=tests,
            )
            runs.append(run)
        
        analyzer = TrendAnalyzer()
        trend = analyzer.analyze_metric(runs, TrendMetric.PASS_RATE)
        
        assert trend.metric_name == "pass_rate"
        assert len(trend.data_points) == 5
        assert trend.trend_direction in ["improving", "stable", "degrading"]
    
    def test_detect_anomalies(self):
        """Test anomaly detection."""
        data_points = [
            TrendPoint(datetime.now() - timedelta(days=i), 50.0 + i, f"run{i}")
            for i in range(10)
        ]
        # Add anomaly
        data_points.append(
            TrendPoint(datetime.now(), 100.0, "run_anomaly")
        )
        
        trend = TrendData(
            metric_name="test_metric",
            data_points=data_points,
        )
        
        analyzer = TrendAnalyzer()
        anomalies = analyzer.detect_anomalies(trend, std_threshold=2.0)
        
        assert len(anomalies) > 0
    
    def test_predict_next_value(self):
        """Test value prediction."""
        data_points = [
            TrendPoint(datetime.now() - timedelta(days=2), 50.0, "run1"),
            TrendPoint(datetime.now() - timedelta(days=1), 55.0, "run2"),
        ]
        
        trend = TrendData(
            metric_name="test_metric",
            data_points=data_points,
        )
        
        analyzer = TrendAnalyzer()
        predicted = analyzer.predict_next_value(trend, days_ahead=1)
        
        assert predicted is not None
        assert predicted > 55.0  # Should be higher based on trend
    
    def test_trend_report_generation(self):
        """Test trend report generation."""
        runs = [
            TestRunResult(
                run_id=f"run{i}",
                start_time=datetime.now() - timedelta(days=5-i),
                tests=[
                    TestResult("test1", "test1", status=TestStatus.PASSED)
                    for _ in range(10)
                ],
            )
            for i in range(3)
        ]
        
        analyzer = TrendAnalyzer()
        trends = analyzer.analyze_all_metrics(runs)
        report = analyzer.generate_report(trends)
        
        assert "PASS RATE" in report
        # Coverage is skipped if there's no coverage data, so just check other metrics
        assert "DURATION" in report
        assert "Trend Analysis Report" in report


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from collection to analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir)
            
            # Create aggregator
            aggregator = UnifiedResultAggregator(storage_path=storage_path)
            
            # Create sample results
            pytest_data = {
                "pytest_version": "7.0.0",
                "created": datetime.now().timestamp(),
                "duration": 10.0,
                "tests": [
                    {
                        "nodeid": "test1",
                        "name": "test1",
                        "outcome": "passed",
                        "duration": 1.0,
                    },
                    {
                        "nodeid": "test2",
                        "name": "test2",
                        "outcome": "failed",
                        "duration": 2.0,
                    }
                ]
            }
            
            result_file = storage_path / "results.json"
            with open(result_file, 'w') as f:
                json.dump(pytest_data, f)
            
            # Aggregate
            run_result = aggregator.aggregate_run(
                result_files=[result_file],
                framework=FrameworkType.PYTEST,
            )
            
            assert run_result.total_tests == 2
            assert run_result.passed == 1
            assert run_result.failed == 1
            
            # Create second run for comparison
            pytest_data2 = {
                "pytest_version": "7.0.0",
                "created": datetime.now().timestamp(),
                "duration": 8.0,
                "tests": [
                    {
                        "nodeid": "test1",
                        "name": "test1",
                        "outcome": "passed",
                        "duration": 1.0,
                    },
                    {
                        "nodeid": "test2",
                        "name": "test2",
                        "outcome": "passed",
                        "duration": 1.5,
                    }
                ]
            }
            
            result_file2 = storage_path / "results2.json"
            with open(result_file2, 'w') as f:
                json.dump(pytest_data2, f)
            
            run_result2 = aggregator.aggregate_run(
                result_files=[result_file2],
                framework=FrameworkType.PYTEST,
            )
            
            # Compare
            comparer = ResultComparer()
            comparison = comparer.compare(run_result, run_result2)
            
            assert len(comparison.newly_passing) == 1
            assert comparison.improvements > 0
            
            # Analyze trends
            analyzer = TrendAnalyzer(min_data_points=2)
            trend = analyzer.analyze_metric([run_result, run_result2], TrendMetric.PASS_RATE)
            
            assert len(trend.data_points) == 2
            assert trend.is_improving or trend.trend_direction == "stable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
