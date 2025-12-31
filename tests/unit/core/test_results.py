"""
Unit tests for result collection and aggregation.

Tests cover:
- Result normalization across frameworks
- Result aggregation from multiple sources
- Cross-run comparison
- Trend analysis
- Statistical analysis
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from core.results import (
    # Models
    UnifiedTestResult,
    AggregatedResults,
    RunComparison,
    TrendMetrics,
    StatisticalMetrics,
    TestStatus,
    ResultSource,
    TrendDirection,
    
    # Aggregator
    ResultAggregator,
    ResultNormalizer,
    
    # Comparator
    ResultComparator,
    ComparisonReport,
    
    # Analyzer
    TrendAnalyzer,
    HistoricalAnalyzer,
    StatisticalAnalyzer,
)

from core.execution.models import (
    ExecutionSummary,
    TestExecutionResult,
    ExecutionStatus
)


class TestResultModels:
    """Test result data models."""
    
    def test_unified_result_creation(self):
        """Test creating unified test result."""
        result = UnifiedTestResult(
            test_id="test_login",
            test_name="Test Login",
            framework="pytest",
            status=TestStatus.PASSED,
            duration_ms=150.0,
            executed_at=datetime.now()
        )
        
        assert result.test_id == "test_login"
        assert result.test_name == "Test Login"
        assert result.framework == "pytest"
        assert result.status == TestStatus.PASSED
        assert result.duration_ms == 150.0
        assert not result.is_flaky
        assert ResultSource.EXECUTION not in result.data_sources  # Empty by default
    
    def test_aggregated_results_success_rate(self):
        """Test aggregated results success rate calculation."""
        aggregated = AggregatedResults(
            aggregation_id="test_agg",
            created_at=datetime.now(),
            total_tests=10,
            passed_tests=8,
            failed_tests=2
        )
        
        assert aggregated.success_rate == 80.0
    
    def test_aggregated_results_flaky_rate(self):
        """Test aggregated results flaky rate calculation."""
        aggregated = AggregatedResults(
            aggregation_id="test_agg",
            created_at=datetime.now(),
            total_tests=10,
            flaky_tests=2
        )
        
        assert aggregated.flaky_rate == 20.0
    
    def test_run_comparison_has_regressions(self):
        """Test regression detection in run comparison."""
        comparison = RunComparison(
            comparison_id="comp1",
            run1_id="run1",
            run2_id="run2",
            compared_at=datetime.now(),
            newly_failing=["test1", "test2"],
            success_rate_delta=-10.0
        )
        
        assert comparison.has_regressions is True
    
    def test_run_comparison_has_improvements(self):
        """Test improvement detection in run comparison."""
        comparison = RunComparison(
            comparison_id="comp1",
            run1_id="run1",
            run2_id="run2",
            compared_at=datetime.now(),
            newly_passing=["test3", "test4"],
            success_rate_delta=15.0
        )
        
        assert comparison.has_improvements is True


class TestResultNormalizer:
    """Test result normalization."""
    
    def test_normalize_execution_result(self):
        """Test normalizing execution result."""
        exec_result = TestExecutionResult(
            test_id="test_example",
            name="Example Test",
            status=ExecutionStatus.PASSED,
            duration_ms=100,
            start_time=datetime.now(),
            framework="pytest",
            tags=["smoke", "api"]
        )
        
        normalizer = ResultNormalizer()
        unified = normalizer.normalize_execution_result(
            exec_result,
            run_id="run123",
            build_id="build456"
        )
        
        assert unified.test_id == "test_example"
        assert unified.test_name == "Example Test"
        assert unified.status == TestStatus.PASSED
        assert unified.duration_ms == 100
        assert unified.framework == "pytest"
        assert unified.run_id == "run123"
        assert unified.build_id == "build456"
        assert unified.tags == ["smoke", "api"]
        assert ResultSource.EXECUTION in unified.data_sources
    
    def test_normalize_flaky_result(self):
        """Test normalizing flaky execution result."""
        exec_result = TestExecutionResult(
            test_id="test_flaky",
            name="Flaky Test",
            status=ExecutionStatus.PASSED,
            duration_ms=200,
            start_time=datetime.now(),
            is_flaky=True,
            retry_count=2,
            framework="robot"
        )
        
        normalizer = ResultNormalizer()
        unified = normalizer.normalize_execution_result(exec_result)
        
        assert unified.status == TestStatus.FLAKY  # Override to FLAKY
        assert unified.is_flaky is True
        assert unified.retry_count == 2


class TestResultAggregator:
    """Test result aggregation."""
    
    def test_aggregator_initialization(self):
        """Test aggregator initialization."""
        aggregator = ResultAggregator()
        
        assert len(aggregator.results) == 0
        assert len(aggregator.coverage_data) == 0
        assert aggregator.normalizer is not None
    
    def test_add_execution_summary(self):
        """Test adding execution summary."""
        aggregator = ResultAggregator()
        
        # Create mock execution summary
        summary = ExecutionSummary(
            status=ExecutionStatus.PASSED,
            total_tests=2,
            passed=2
        )
        
        summary.results = [
            TestExecutionResult(
                test_id="test1",
                name="Test 1",
                status=ExecutionStatus.PASSED,
                duration_ms=100,
                start_time=datetime.now(),
                framework="pytest"
            ),
            TestExecutionResult(
                test_id="test2",
                name="Test 2",
                status=ExecutionStatus.FAILED,
                duration_ms=150,
                start_time=datetime.now(),
                framework="pytest"
            )
        ]
        
        aggregator.add_execution_summary(
            summary,
            run_id="run123",
            build_id="build456"
        )
        
        assert len(aggregator.results) == 2
        assert aggregator.results[0].test_id == "test1"
        assert aggregator.results[0].run_id == "run123"
        assert aggregator.results[1].test_id == "test2"
    
    def test_get_aggregated_results(self):
        """Test getting aggregated results with statistics."""
        aggregator = ResultAggregator()
        
        # Add some results
        now = datetime.now()
        aggregator.results = [
            UnifiedTestResult(
                test_id="test1",
                test_name="Test 1",
                framework="pytest",
                status=TestStatus.PASSED,
                duration_ms=100.0,
                executed_at=now,
                data_sources={ResultSource.EXECUTION}
            ),
            UnifiedTestResult(
                test_id="test2",
                test_name="Test 2",
                framework="pytest",
                status=TestStatus.FAILED,
                duration_ms=200.0,
                executed_at=now,
                data_sources={ResultSource.EXECUTION}
            ),
            UnifiedTestResult(
                test_id="test3",
                test_name="Test 3",
                framework="robot",
                status=TestStatus.PASSED,
                duration_ms=150.0,
                executed_at=now,
                is_flaky=True,
                data_sources={ResultSource.EXECUTION, ResultSource.FLAKY_DETECTION}
            )
        ]
        
        aggregated = aggregator.get_aggregated_results()
        
        assert aggregated.total_tests == 3
        assert aggregated.passed_tests == 2
        assert aggregated.failed_tests == 1
        assert aggregated.flaky_tests == 1
        assert aggregated.success_rate == pytest.approx(66.67, abs=0.1)
        assert aggregated.total_duration_ms == 450.0
        assert aggregated.avg_duration_ms == 150.0
        assert len(aggregated.frameworks) == 2
        assert "pytest" in aggregated.frameworks
        assert "robot" in aggregated.frameworks
        assert ResultSource.EXECUTION in aggregated.sources
        assert ResultSource.FLAKY_DETECTION in aggregated.sources
    
    def test_mark_impacted_tests(self):
        """Test marking impacted tests."""
        aggregator = ResultAggregator()
        
        aggregator.results = [
            UnifiedTestResult(
                test_id="test1",
                test_name="Test 1",
                framework="pytest",
                status=TestStatus.PASSED,
                duration_ms=100.0,
                executed_at=datetime.now()
            )
        ]
        
        aggregator.mark_impacted_tests(
            ["test1"],
            risk_scores={"test1": 0.85}
        )
        
        assert aggregator.results[0].impacted_by_changes is True
        assert aggregator.results[0].change_risk_score == 0.85
        assert ResultSource.IMPACT_ANALYSIS in aggregator.results[0].data_sources


class TestResultComparator:
    """Test result comparison."""
    
    def test_comparator_initialization(self):
        """Test comparator initialization."""
        comparator = ResultComparator()
        assert comparator is not None
    
    def test_compare_runs_basic(self):
        """Test basic run comparison."""
        now = datetime.now()
        
        # Run 1: 3 tests, 2 passed
        run1 = AggregatedResults(
            aggregation_id="run1",
            created_at=now,
            total_tests=3,
            passed_tests=2,
            failed_tests=1,
            total_duration_ms=1000.0,
            results=[
                UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 100.0, now),
                UnifiedTestResult("test2", "Test 2", "pytest", TestStatus.FAILED, 200.0, now),
                UnifiedTestResult("test3", "Test 3", "pytest", TestStatus.PASSED, 300.0, now),
            ]
        )
        
        # Run 2: 3 tests, 3 passed (test2 now passes)
        run2 = AggregatedResults(
            aggregation_id="run2",
            created_at=now,
            total_tests=3,
            passed_tests=3,
            failed_tests=0,
            total_duration_ms=900.0,
            results=[
                UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 100.0, now),
                UnifiedTestResult("test2", "Test 2", "pytest", TestStatus.PASSED, 150.0, now),
                UnifiedTestResult("test3", "Test 3", "pytest", TestStatus.PASSED, 300.0, now),
            ]
        )
        
        comparator = ResultComparator()
        comparison = comparator.compare_runs(run1, run2)
        
        assert comparison.run1_id == "run1"
        assert comparison.run2_id == "run2"
        assert len(comparison.newly_passing) == 1
        assert "test2" in comparison.newly_passing
        assert len(comparison.newly_failing) == 0
        assert comparison.success_rate_delta > 0
        assert comparison.has_improvements is True
        assert comparison.has_regressions is False
    
    def test_compare_runs_with_regressions(self):
        """Test run comparison with regressions."""
        now = datetime.now()
        
        run1 = AggregatedResults(
            aggregation_id="run1",
            created_at=now,
            total_tests=2,
            passed_tests=2,
            results=[
                UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 100.0, now),
                UnifiedTestResult("test2", "Test 2", "pytest", TestStatus.PASSED, 200.0, now),
            ]
        )
        
        run2 = AggregatedResults(
            aggregation_id="run2",
            created_at=now,
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            results=[
                UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 100.0, now),
                UnifiedTestResult("test2", "Test 2", "pytest", TestStatus.FAILED, 200.0, now),
            ]
        )
        
        comparator = ResultComparator()
        comparison = comparator.compare_runs(run1, run2)
        
        assert len(comparison.newly_failing) == 1
        assert "test2" in comparison.newly_failing
        assert comparison.has_regressions is True
    
    def test_compare_runs_performance_changes(self):
        """Test performance change detection."""
        now = datetime.now()
        
        run1 = AggregatedResults(
            aggregation_id="run1",
            created_at=now,
            results=[
                UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 100.0, now),
            ]
        )
        
        # Test1 is now 2x slower (100% increase)
        run2 = AggregatedResults(
            aggregation_id="run2",
            created_at=now,
            results=[
                UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 200.0, now),
            ]
        )
        
        comparator = ResultComparator()
        comparison = comparator.compare_runs(run1, run2, duration_threshold=50.0)
        
        assert "test1" in comparison.significantly_slower
        assert len(comparison.significantly_faster) == 0
    
    def test_find_persistent_failures(self):
        """Test finding persistent failures."""
        now = datetime.now()
        
        runs = [
            AggregatedResults(
                aggregation_id=f"run{i}",
                created_at=now,
                results=[
                    UnifiedTestResult("test_always_fails", "Always Fails", "pytest", TestStatus.FAILED, 100.0, now),
                    UnifiedTestResult("test_sometimes_fails", "Sometimes Fails", "pytest", 
                                    TestStatus.FAILED if i % 2 == 0 else TestStatus.PASSED, 100.0, now),
                ]
            )
            for i in range(5)
        ]
        
        comparator = ResultComparator()
        persistent = comparator.find_persistent_failures(runs, min_consecutive=3)
        
        # test_always_fails should be detected (fails in all 5 runs)
        assert "test_always_fails" in persistent
    
    def test_find_intermittent_failures(self):
        """Test finding intermittent failures."""
        now = datetime.now()
        
        runs = [
            AggregatedResults(
                aggregation_id=f"run{i}",
                created_at=now,
                results=[
                    # Fails 40% of time (2/5)
                    UnifiedTestResult("test_flaky", "Flaky", "pytest",
                                    TestStatus.FAILED if i < 2 else TestStatus.PASSED, 100.0, now),
                ]
            )
            for i in range(5)
        ]
        
        comparator = ResultComparator()
        intermittent = comparator.find_intermittent_failures(runs, failure_threshold=0.2)
        
        assert "test_flaky" in intermittent
        assert intermittent["test_flaky"] == pytest.approx(0.4, abs=0.01)


class TestComparisonReport:
    """Test comparison report generation."""
    
    def test_report_summary(self):
        """Test generating comparison summary."""
        comparison = RunComparison(
            comparison_id="comp1",
            run1_id="run1",
            run2_id="run2",
            compared_at=datetime.now(),
            newly_passing=["test1", "test2"],
            newly_failing=["test3"],
            run1_success_rate=70.0,
            run2_success_rate=75.0,
            success_rate_delta=5.0
        )
        
        report = ComparisonReport(comparison)
        summary = report.get_summary()
        
        assert "run1" in summary
        assert "run2" in summary
        assert "70.0%" in summary
        assert "75.0%" in summary
        assert "Newly Passing: 2" in summary
        assert "Newly Failing: 1" in summary


class TestStatisticalAnalyzer:
    """Test statistical analysis."""
    
    def test_analyze_test_basic(self):
        """Test basic test analysis."""
        now = datetime.now()
        
        results = [
            UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 100.0, now),
            UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 110.0, now),
            UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.FAILED, 120.0, now),
            UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 105.0, now),
        ]
        
        analyzer = StatisticalAnalyzer()
        metrics = analyzer.analyze_test("test1", results)
        
        assert metrics.test_id == "test1"
        assert metrics.sample_size == 4
        assert metrics.success_rate == 75.0  # 3/4 passed
        assert metrics.avg_duration_ms == pytest.approx(108.75, abs=0.1)
        assert metrics.stability_score > 0
        assert metrics.flaky_probability >= 0
        assert metrics.quality_score > 0
        assert metrics.reliability_grade in ["A", "B", "C", "D", "F"]
    
    def test_analyze_suite(self):
        """Test suite-wide analysis."""
        now = datetime.now()
        
        results = [
            UnifiedTestResult("test1", "Test 1", "pytest", TestStatus.PASSED, 100.0, now),
            UnifiedTestResult("test2", "Test 2", "pytest", TestStatus.PASSED, 150.0, now),
            UnifiedTestResult("test3", "Test 3", "pytest", TestStatus.FAILED, 200.0, now),
        ]
        
        analyzer = StatisticalAnalyzer()
        metrics = analyzer.analyze_suite(results)
        
        assert metrics.sample_size == 3
        assert metrics.success_rate == pytest.approx(66.67, abs=0.1)
        assert metrics.avg_duration_ms == 150.0


class TestTrendAnalyzer:
    """Test trend analysis."""
    
    def test_analyze_success_rate_trend(self):
        """Test success rate trend analysis."""
        now = datetime.now()
        
        runs = [
            AggregatedResults(
                aggregation_id=f"run{i}",
                created_at=now - timedelta(days=10-i),
                start_time=now - timedelta(days=10-i),
                total_tests=10,
                passed_tests=5 + i,  # Improving trend
                results=[]
            )
            for i in range(5)
        ]
        
        analyzer = TrendAnalyzer()
        trend = analyzer.analyze_success_rate_trend(runs)
        
        assert trend.metric_name == "success_rate"
        assert trend.metric_type == "success_rate"
        assert trend.data_points == 5
        assert trend.trend_direction in [TrendDirection.IMPROVING, TrendDirection.STABLE]
        assert trend.current_value > trend.values[0]  # Latest > first
    
    def test_analyze_duration_trend(self):
        """Test duration trend analysis."""
        now = datetime.now()
        
        runs = [
            AggregatedResults(
                aggregation_id=f"run{i}",
                created_at=now - timedelta(days=10-i),
                start_time=now - timedelta(days=10-i),
                avg_duration_ms=1000.0 + i * 100,  # Getting slower
                results=[]
            )
            for i in range(5)
        ]
        
        analyzer = TrendAnalyzer()
        trend = analyzer.analyze_duration_trend(runs)
        
        assert trend.metric_type == "duration"
        assert trend.data_points == 5
        assert trend.current_value > trend.values[0]


class TestHistoricalAnalyzer:
    """Test historical analysis."""
    
    def test_analyze_health_metrics(self):
        """Test health metrics analysis."""
        now = datetime.now()
        
        runs = [
            AggregatedResults(
                aggregation_id=f"run{i}",
                created_at=now - timedelta(days=10-i),
                start_time=now - timedelta(days=10-i),
                total_tests=10,
                passed_tests=8,
                failed_tests=2,
                flaky_tests=1,
                avg_duration_ms=1000.0,
                results=[]
            )
            for i in range(5)
        ]
        
        analyzer = HistoricalAnalyzer()
        metrics = analyzer.analyze_health_metrics(runs)
        
        assert "success_rate" in metrics
        assert "duration" in metrics
        assert "flaky_rate" in metrics
        assert "test_count" in metrics
    
    def test_identify_problem_tests(self):
        """Test problem test identification."""
        now = datetime.now()
        
        # Create runs with one consistently failing test
        runs = [
            AggregatedResults(
                aggregation_id=f"run{i}",
                created_at=now,
                results=[
                    UnifiedTestResult("test_bad", "Bad Test", "pytest", TestStatus.FAILED, 100.0, now),
                    UnifiedTestResult("test_good", "Good Test", "pytest", TestStatus.PASSED, 100.0, now),
                ]
            )
            for i in range(5)
        ]
        
        analyzer = HistoricalAnalyzer()
        problems = analyzer.identify_problem_tests(runs, quality_threshold=60.0)
        
        # test_bad should be identified
        problem_ids = [test_id for test_id, metrics in problems]
        assert "test_bad" in problem_ids
    
    def test_generate_health_report(self):
        """Test health report generation."""
        now = datetime.now()
        
        runs = [
            AggregatedResults(
                aggregation_id=f"run{i}",
                created_at=now - timedelta(days=i),
                start_time=now - timedelta(days=i),
                end_time=now - timedelta(days=i) + timedelta(minutes=10),
                total_tests=10,
                passed_tests=8,
                results=[]
            )
            for i in range(3)
        ]
        
        analyzer = HistoricalAnalyzer()
        report = analyzer.generate_health_report(runs)
        
        assert "Test Suite Health Report" in report
        assert "Success Rate Trend" in report
        assert "Duration Trend" in report


class TestIntegration:
    """Integration tests."""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from aggregation to analysis."""
        now = datetime.now()
        
        # Step 1: Aggregate results
        aggregator = ResultAggregator()
        
        summary = ExecutionSummary(status=ExecutionStatus.PASSED)
        summary.results = [
            TestExecutionResult(
                test_id="test1",
                name="Test 1",
                status=ExecutionStatus.PASSED,
                duration_ms=100,
                start_time=now,
                framework="pytest"
            ),
            TestExecutionResult(
                test_id="test2",
                name="Test 2",
                status=ExecutionStatus.FAILED,
                duration_ms=200,
                start_time=now,
                framework="pytest"
            )
        ]
        
        aggregator.add_execution_summary(summary, run_id="run1")
        run1 = aggregator.get_aggregated_results()
        
        # Step 2: Create second run
        aggregator.clear()
        summary2 = ExecutionSummary(status=ExecutionStatus.PASSED)
        summary2.results = [
            TestExecutionResult(
                test_id="test1",
                name="Test 1",
                status=ExecutionStatus.PASSED,
                duration_ms=95,
                start_time=now,
                framework="pytest"
            ),
            TestExecutionResult(
                test_id="test2",
                name="Test 2",
                status=ExecutionStatus.PASSED,  # Now passes
                duration_ms=180,
                start_time=now,
                framework="pytest"
            )
        ]
        
        aggregator.add_execution_summary(summary2, run_id="run2")
        run2 = aggregator.get_aggregated_results()
        
        # Step 3: Compare runs
        comparator = ResultComparator()
        comparison = comparator.compare_runs(run1, run2)
        
        assert comparison.newly_passing == ["test2"]
        assert comparison.has_improvements is True
        
        # Step 4: Analyze trends
        analyzer = TrendAnalyzer()
        trend = analyzer.analyze_success_rate_trend([run1, run2])
        
        assert trend.data_points == 2
        assert trend.current_value > run1.success_rate
        
        # Step 5: Generate report
        report = ComparisonReport(comparison)
        summary_text = report.get_summary()
        
        # Check for key elements (aggregation IDs are UUIDs, not "run1")
        assert "Run Comparison:" in summary_text
        assert "IMPROVEMENTS DETECTED" in summary_text
        assert "Newly Passing: 1" in summary_text
        assert "test2" in summary_text
