"""
Historical trend analysis.

Analyzes test result trends over time to identify patterns,
predict future outcomes, and provide statistical insights.
"""

import math
import statistics
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from .models import (
    AggregatedResults,
    UnifiedTestResult,
    TrendMetrics,
    TrendDirection,
    StatisticalMetrics,
    TestStatus
)


class StatisticalAnalyzer:
    """
    Provides statistical analysis of test results.
    
    Calculates advanced metrics like confidence intervals,
    percentiles, and quality scores.
    """
    
    @staticmethod
    def analyze_test(
        test_id: str,
        results: List[UnifiedTestResult]
    ) -> StatisticalMetrics:
        """
        Analyze statistics for a specific test.
        
        Args:
            test_id: Test identifier
            results: List of results for this test
            
        Returns:
            Statistical metrics
        """
        metrics = StatisticalMetrics(
            test_id=test_id,
            analysis_date=datetime.now(),
            sample_size=len(results)
        )
        
        if not results:
            return metrics
        
        # Success metrics
        passed_count = sum(1 for r in results if r.status == TestStatus.PASSED)
        metrics.success_rate = passed_count / len(results) * 100.0
        
        # Calculate confidence interval for success rate
        ci_low, ci_high = StatisticalAnalyzer._binomial_confidence_interval(
            passed_count, len(results)
        )
        metrics.success_rate_ci_low = ci_low * 100.0
        metrics.success_rate_ci_high = ci_high * 100.0
        
        # Duration metrics
        durations = [r.duration_ms for r in results]
        metrics.avg_duration_ms = statistics.mean(durations)
        
        sorted_durations = sorted(durations)
        metrics.duration_p50 = StatisticalAnalyzer._percentile(sorted_durations, 50)
        metrics.duration_p90 = StatisticalAnalyzer._percentile(sorted_durations, 90)
        metrics.duration_p99 = StatisticalAnalyzer._percentile(sorted_durations, 99)
        
        if len(durations) > 1:
            metrics.duration_std = statistics.stdev(durations)
        
        # Stability metrics
        metrics.stability_score = StatisticalAnalyzer._calculate_stability_score(results)
        metrics.flaky_probability = StatisticalAnalyzer._calculate_flaky_probability(results)
        
        # Consecutive passes/failures
        metrics.consecutive_passes = StatisticalAnalyzer._count_consecutive_at_end(
            results, TestStatus.PASSED
        )
        metrics.consecutive_failures = StatisticalAnalyzer._count_consecutive_at_end(
            results, TestStatus.FAILED
        )
        
        # Reliability metrics
        metrics.failure_rate = (len(results) - passed_count) / len(results)
        metrics.mean_time_between_failures = StatisticalAnalyzer._calculate_mtbf(results)
        
        # Quality score (0-100)
        metrics.quality_score = StatisticalAnalyzer._calculate_quality_score(metrics)
        metrics.reliability_grade = StatisticalAnalyzer._grade_reliability(metrics.quality_score)
        
        return metrics
    
    @staticmethod
    def analyze_suite(results: List[UnifiedTestResult]) -> StatisticalMetrics:
        """
        Analyze statistics for entire test suite.
        
        Args:
            results: List of all test results
            
        Returns:
            Suite-wide statistical metrics
        """
        return StatisticalAnalyzer.analyze_test(None, results)  # None = suite-wide
    
    @staticmethod
    def _binomial_confidence_interval(
        successes: int,
        trials: int,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate binomial confidence interval (Wilson score)."""
        if trials == 0:
            return (0.0, 0.0)
        
        p = successes / trials
        z = 1.96  # 95% confidence
        
        denominator = 1 + z**2 / trials
        center = (p + z**2 / (2 * trials)) / denominator
        margin = z * math.sqrt((p * (1 - p) / trials + z**2 / (4 * trials**2))) / denominator
        
        return (max(0.0, center - margin), min(1.0, center + margin))
    
    @staticmethod
    def _percentile(sorted_values: List[float], p: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0
        
        k = (len(sorted_values) - 1) * p / 100.0
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return sorted_values[int(k)]
        
        d0 = sorted_values[int(f)] * (c - k)
        d1 = sorted_values[int(c)] * (k - f)
        
        return d0 + d1
    
    @staticmethod
    def _calculate_stability_score(results: List[UnifiedTestResult]) -> float:
        """Calculate stability score (0-1, higher = more stable)."""
        if len(results) < 2:
            return 1.0
        
        # Count status changes
        changes = 0
        for i in range(1, len(results)):
            if results[i].status != results[i-1].status:
                changes += 1
        
        # Stability inversely proportional to changes
        stability = 1.0 - (changes / (len(results) - 1))
        
        return max(0.0, min(1.0, stability))
    
    @staticmethod
    def _calculate_flaky_probability(results: List[UnifiedTestResult]) -> float:
        """Calculate probability test is flaky based on result patterns."""
        if len(results) < 3:
            return 0.0
        
        # Check for alternating pass/fail patterns
        alternations = 0
        for i in range(1, len(results)):
            prev_passed = results[i-1].status == TestStatus.PASSED
            curr_passed = results[i].status == TestStatus.PASSED
            if prev_passed != curr_passed:
                alternations += 1
        
        # High alternation rate suggests flakiness
        alternation_rate = alternations / (len(results) - 1)
        
        # Check explicit flaky indicators
        explicit_flaky = sum(1 for r in results if r.is_flaky)
        explicit_flaky_rate = explicit_flaky / len(results)
        
        # Combine indicators
        probability = max(alternation_rate * 0.7, explicit_flaky_rate)
        
        return min(1.0, probability)
    
    @staticmethod
    def _count_consecutive_at_end(
        results: List[UnifiedTestResult],
        status: TestStatus
    ) -> int:
        """Count consecutive occurrences of status at end of results."""
        count = 0
        for result in reversed(results):
            if result.status == status:
                count += 1
            else:
                break
        return count
    
    @staticmethod
    def _calculate_mtbf(results: List[UnifiedTestResult]) -> Optional[float]:
        """Calculate mean time between failures."""
        failures = [i for i, r in enumerate(results) if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
        
        if len(failures) < 2:
            return None
        
        intervals = [failures[i+1] - failures[i] for i in range(len(failures) - 1)]
        
        return statistics.mean(intervals) if intervals else None
    
    @staticmethod
    def _calculate_quality_score(metrics: StatisticalMetrics) -> float:
        """Calculate overall quality score (0-100)."""
        # Weight different factors
        success_weight = 0.5
        stability_weight = 0.3
        flaky_weight = 0.2
        
        score = (
            metrics.success_rate * success_weight +
            metrics.stability_score * 100.0 * stability_weight +
            (1.0 - metrics.flaky_probability) * 100.0 * flaky_weight
        )
        
        return max(0.0, min(100.0, score))
    
    @staticmethod
    def _grade_reliability(quality_score: float) -> str:
        """Convert quality score to letter grade."""
        if quality_score >= 90:
            return "A"
        elif quality_score >= 80:
            return "B"
        elif quality_score >= 70:
            return "C"
        elif quality_score >= 60:
            return "D"
        else:
            return "F"


class TrendAnalyzer:
    """
    Analyzes trends in test results over time.
    
    Identifies patterns, calculates trend direction and strength,
    and provides forecasting when possible.
    """
    
    def __init__(self):
        """Initialize trend analyzer."""
        self.statistical_analyzer = StatisticalAnalyzer()
    
    def analyze_success_rate_trend(
        self,
        runs: List[AggregatedResults],
        metric_name: str = "success_rate"
    ) -> TrendMetrics:
        """
        Analyze success rate trend over multiple runs.
        
        Args:
            runs: List of aggregated results in chronological order
            metric_name: Name for the metric
            
        Returns:
            Trend metrics for success rate
        """
        if not runs:
            return TrendMetrics(
                metric_name=metric_name,
                metric_type="success_rate",
                start_date=datetime.now(),
                end_date=datetime.now(),
                data_points=0
            )
        
        # Extract values and timestamps
        values = [run.success_rate for run in runs]
        timestamps = [run.start_time or datetime.now() for run in runs]
        
        return self._analyze_trend(
            metric_name=metric_name,
            metric_type="success_rate",
            values=values,
            timestamps=timestamps
        )
    
    def analyze_duration_trend(
        self,
        runs: List[AggregatedResults],
        metric_name: str = "avg_duration"
    ) -> TrendMetrics:
        """
        Analyze duration trend over multiple runs.
        
        Args:
            runs: List of aggregated results in chronological order
            metric_name: Name for the metric
            
        Returns:
            Trend metrics for duration
        """
        if not runs:
            return TrendMetrics(
                metric_name=metric_name,
                metric_type="duration",
                start_date=datetime.now(),
                end_date=datetime.now(),
                data_points=0
            )
        
        values = [run.avg_duration_ms for run in runs]
        timestamps = [run.start_time or datetime.now() for run in runs]
        
        return self._analyze_trend(
            metric_name=metric_name,
            metric_type="duration",
            values=values,
            timestamps=timestamps
        )
    
    def analyze_flaky_rate_trend(
        self,
        runs: List[AggregatedResults],
        metric_name: str = "flaky_rate"
    ) -> TrendMetrics:
        """
        Analyze flaky test rate trend over multiple runs.
        
        Args:
            runs: List of aggregated results in chronological order
            metric_name: Name for the metric
            
        Returns:
            Trend metrics for flaky rate
        """
        if not runs:
            return TrendMetrics(
                metric_name=metric_name,
                metric_type="flaky_rate",
                start_date=datetime.now(),
                end_date=datetime.now(),
                data_points=0
            )
        
        values = [run.flaky_rate for run in runs]
        timestamps = [run.start_time or datetime.now() for run in runs]
        
        return self._analyze_trend(
            metric_name=metric_name,
            metric_type="flaky_rate",
            values=values,
            timestamps=timestamps
        )
    
    def analyze_test_trend(
        self,
        test_id: str,
        results: List[UnifiedTestResult],
        metric_name: str = "test_success_rate"
    ) -> TrendMetrics:
        """
        Analyze trend for a specific test.
        
        Args:
            test_id: Test identifier
            results: List of results for this test over time
            metric_name: Name for the metric
            
        Returns:
            Trend metrics for the test
        """
        if not results:
            return TrendMetrics(
                metric_name=metric_name,
                metric_type="test_metric",
                start_date=datetime.now(),
                end_date=datetime.now(),
                data_points=0
            )
        
        # Convert results to success/failure binary
        values = [100.0 if r.status == TestStatus.PASSED else 0.0 for r in results]
        timestamps = [r.executed_at for r in results]
        
        return self._analyze_trend(
            metric_name=f"{metric_name}_{test_id}",
            metric_type="test_metric",
            values=values,
            timestamps=timestamps
        )
    
    def _analyze_trend(
        self,
        metric_name: str,
        metric_type: str,
        values: List[float],
        timestamps: List[datetime]
    ) -> TrendMetrics:
        """
        Analyze trend from values and timestamps.
        
        Args:
            metric_name: Name of metric
            metric_type: Type of metric
            values: List of values
            timestamps: List of timestamps
            
        Returns:
            Trend metrics
        """
        if not values:
            # Return empty metrics for empty data
            return TrendMetrics(
                metric_name=metric_name,
                metric_type=metric_type,
                start_date=datetime.now(),
                end_date=datetime.now(),
                data_points=0,
                values=[],
                timestamps=[]
            )
        
        # Time range
        start_date = min(timestamps)
        end_date = max(timestamps)
        
        metrics = TrendMetrics(
            metric_name=metric_name,
            metric_type=metric_type,
            values=values,
            timestamps=timestamps,
            data_points=len(values),
            start_date=start_date,
            end_date=end_date
        )
        
        # Basic statistics
        metrics.current_value = values[-1]
        metrics.min_value = min(values)
        metrics.max_value = max(values)
        metrics.avg_value = statistics.mean(values)
        
        if len(values) > 1:
            metrics.median_value = statistics.median(values)
            metrics.std_deviation = statistics.stdev(values)
        else:
            metrics.median_value = values[0]
            metrics.std_deviation = 0.0
        
        # Trend direction
        metrics.trend_direction = self._determine_trend_direction(values)
        metrics.trend_strength = self._calculate_trend_strength(values)
        
        # Volatility (coefficient of variation)
        if metrics.avg_value != 0:
            metrics.volatility = metrics.std_deviation / metrics.avg_value
        
        # Change detection
        if len(values) >= 2:
            change = values[-1] - values[0]
            metrics.change_percentage = (change / values[0] * 100.0) if values[0] != 0 else 0.0
            metrics.significant_change = abs(metrics.change_percentage) > 10.0
        
        # Simple forecasting (linear extrapolation)
        if len(values) >= 3:
            predicted = self._simple_forecast(values)
            if predicted is not None:
                metrics.predicted_next_value = predicted
                # Simple confidence interval (±2 std dev)
                metrics.confidence_interval_low = predicted - 2 * metrics.std_deviation
                metrics.confidence_interval_high = predicted + 2 * metrics.std_deviation
        
        return metrics
    
    def _determine_trend_direction(self, values: List[float]) -> TrendDirection:
        """Determine trend direction from values."""
        if len(values) < 3:
            return TrendDirection.STABLE
        
        # Compare first third to last third
        third = len(values) // 3
        first_third_avg = statistics.mean(values[:third])
        last_third_avg = statistics.mean(values[-third:])
        
        if first_third_avg == 0:
            return TrendDirection.STABLE
        
        change_pct = (last_third_avg - first_third_avg) / first_third_avg * 100.0
        
        # Check volatility
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        avg = statistics.mean(values)
        cv = std_dev / avg if avg != 0 else 0
        
        if cv > 0.5:  # High volatility
            return TrendDirection.VOLATILE
        elif change_pct > 10.0:
            return TrendDirection.IMPROVING
        elif change_pct < -10.0:
            return TrendDirection.DEGRADING
        else:
            return TrendDirection.STABLE
    
    def _calculate_trend_strength(self, values: List[float]) -> float:
        """Calculate trend strength (0-1)."""
        if len(values) < 3:
            return 0.0
        
        # Use linear regression R²
        n = len(values)
        x = list(range(n))
        y = values
        
        # Calculate means
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        # Calculate correlation
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator_x = math.sqrt(sum((x[i] - x_mean) ** 2 for i in range(n)))
        denominator_y = math.sqrt(sum((y[i] - y_mean) ** 2 for i in range(n)))
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        r = numerator / (denominator_x * denominator_y)
        r_squared = r ** 2
        
        return min(1.0, abs(r_squared))
    
    def _simple_forecast(self, values: List[float]) -> Optional[float]:
        """Simple linear forecast for next value."""
        if len(values) < 2:
            return None
        
        # Use last 5 values or all if less
        recent_values = values[-5:]
        n = len(recent_values)
        
        # Calculate linear trend
        x = list(range(n))
        y = recent_values
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return recent_values[-1]
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Predict next value
        next_x = n
        predicted = slope * next_x + intercept
        
        return predicted


class HistoricalAnalyzer:
    """
    Analyzes historical test data for long-term patterns.
    
    Provides insights into test suite health over extended periods.
    """
    
    def __init__(self):
        """Initialize historical analyzer."""
        self.trend_analyzer = TrendAnalyzer()
        self.statistical_analyzer = StatisticalAnalyzer()
    
    def analyze_health_metrics(
        self,
        runs: List[AggregatedResults]
    ) -> Dict[str, TrendMetrics]:
        """
        Analyze overall health metrics over time.
        
        Args:
            runs: List of aggregated results over time
            
        Returns:
            Dictionary of trend metrics for various health indicators
        """
        metrics = {}
        
        # Success rate trend
        metrics['success_rate'] = self.trend_analyzer.analyze_success_rate_trend(runs)
        
        # Duration trend
        metrics['duration'] = self.trend_analyzer.analyze_duration_trend(runs)
        
        # Flaky rate trend
        metrics['flaky_rate'] = self.trend_analyzer.analyze_flaky_rate_trend(runs)
        
        # Test count trend
        if runs:
            test_counts = [run.total_tests for run in runs]
            timestamps = [run.start_time or datetime.now() for run in runs]
            metrics['test_count'] = self.trend_analyzer._analyze_trend(
                "test_count",
                "count",
                test_counts,
                timestamps
            )
        
        return metrics
    
    def identify_problem_tests(
        self,
        runs: List[AggregatedResults],
        quality_threshold: float = 60.0
    ) -> List[Tuple[str, StatisticalMetrics]]:
        """
        Identify tests with persistent quality problems.
        
        Args:
            runs: List of aggregated results
            quality_threshold: Quality score threshold below which tests are problematic
            
        Returns:
            List of (test_id, metrics) tuples for problematic tests
        """
        # Collect all results by test
        test_results: Dict[str, List[UnifiedTestResult]] = {}
        
        for run in runs:
            for result in run.results:
                if result.test_id not in test_results:
                    test_results[result.test_id] = []
                test_results[result.test_id].append(result)
        
        # Analyze each test
        problem_tests = []
        
        for test_id, results in test_results.items():
            if len(results) < 3:  # Need minimum data
                continue
            
            metrics = self.statistical_analyzer.analyze_test(test_id, results)
            
            if metrics.quality_score < quality_threshold:
                problem_tests.append((test_id, metrics))
        
        # Sort by quality score (worst first)
        problem_tests.sort(key=lambda x: x[1].quality_score)
        
        return problem_tests
    
    def generate_health_report(
        self,
        runs: List[AggregatedResults]
    ) -> str:
        """
        Generate comprehensive health report.
        
        Args:
            runs: List of aggregated results over time
            
        Returns:
            Human-readable health report
        """
        lines = []
        lines.append("Test Suite Health Report")
        lines.append("=" * 70)
        lines.append(f"Analysis Period: {len(runs)} runs")
        
        if runs:
            start = runs[0].start_time
            end = runs[-1].end_time
            if start and end:
                duration = (end - start).days
                lines.append(f"Date Range: {start.date()} to {end.date()} ({duration} days)")
        
        lines.append("")
        
        # Analyze metrics
        metrics = self.analyze_health_metrics(runs)
        
        # Success rate
        if 'success_rate' in metrics:
            sr = metrics['success_rate']
            lines.append(f"Success Rate Trend:")
            lines.append(f"  Current: {sr.current_value:.1f}%")
            lines.append(f"  Average: {sr.avg_value:.1f}%")
            lines.append(f"  Direction: {sr.trend_direction.value}")
            if sr.significant_change:
                lines.append(f"  ⚠️  Significant change: {sr.change_percentage:+.1f}%")
            lines.append("")
        
        # Duration
        if 'duration' in metrics:
            dur = metrics['duration']
            lines.append(f"Duration Trend:")
            lines.append(f"  Current: {dur.current_value / 1000:.1f}s")
            lines.append(f"  Average: {dur.avg_value / 1000:.1f}s")
            lines.append(f"  Direction: {dur.trend_direction.value}")
            lines.append("")
        
        # Flaky rate
        if 'flaky_rate' in metrics:
            fr = metrics['flaky_rate']
            lines.append(f"Flaky Test Rate:")
            lines.append(f"  Current: {fr.current_value:.1f}%")
            lines.append(f"  Average: {fr.avg_value:.1f}%")
            if fr.current_value > 5.0:
                lines.append(f"  ⚠️  High flaky rate detected!")
            lines.append("")
        
        # Problem tests
        problem_tests = self.identify_problem_tests(runs)
        if problem_tests:
            lines.append(f"Problem Tests: {len(problem_tests)}")
            for test_id, test_metrics in problem_tests[:10]:  # Show top 10
                lines.append(f"  ❌ {test_id}")
                lines.append(f"     Quality: {test_metrics.quality_score:.0f} ({test_metrics.reliability_grade})")
                lines.append(f"     Success Rate: {test_metrics.success_rate:.1f}%")
        
        return "\n".join(lines)
