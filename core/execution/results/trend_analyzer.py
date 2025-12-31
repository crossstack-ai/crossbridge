"""
Historical trend analysis for test results.

Analyzes trends over time:
- Pass rate trends
- Coverage trends
- Performance trends
- Flaky test trends
- Test stability
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import statistics

from .models import (
    TestRunResult,
    TrendData,
    TrendPoint,
    AggregatedResults,
)
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.EXECUTION)


class TrendMetric(Enum):
    """Metrics that can be analyzed for trends."""
    PASS_RATE = "pass_rate"
    COVERAGE = "coverage"
    DURATION = "duration"
    FLAKY_TESTS = "flaky_tests"
    TOTAL_TESTS = "total_tests"
    FAILURE_RATE = "failure_rate"


class TrendAnalyzer:
    """
    Analyzes trends in test results over time.
    
    Provides statistical analysis and trend detection.
    """
    
    def __init__(
        self,
        trend_threshold: float = 0.1,  # 10% change for trend detection
        min_data_points: int = 3,
    ):
        """
        Initialize trend analyzer.
        
        Args:
            trend_threshold: Threshold for detecting trends (0.0-1.0)
            min_data_points: Minimum data points needed for trend analysis
        """
        self.trend_threshold = trend_threshold
        self.min_data_points = min_data_points
        self.logger = get_logger(__name__, category=LogCategory.EXECUTION)
    
    def analyze_metric(
        self,
        runs: List[TestRunResult],
        metric: TrendMetric,
    ) -> TrendData:
        """
        Analyze trend for a specific metric.
        
        Args:
            runs: List of test runs ordered by time
            metric: Metric to analyze
            
        Returns:
            TrendData with analysis results
        """
        self.logger.info(f"Analyzing trend for {metric.value}")
        
        # Extract data points
        data_points = []
        
        for run in runs:
            value = self._extract_metric_value(run, metric)
            if value is not None:
                point = TrendPoint(
                    timestamp=run.start_time,
                    value=value,
                    run_id=run.run_id,
                    metadata={
                        'total_tests': run.total_tests,
                        'passed': run.passed,
                        'failed': run.failed,
                    }
                )
                data_points.append(point)
        
        if len(data_points) < self.min_data_points:
            self.logger.warning(
                f"Not enough data points ({len(data_points)}) for trend analysis "
                f"(need {self.min_data_points})"
            )
            return TrendData(metric_name=metric.value, data_points=data_points)
        
        # Create trend data (statistics calculated in __post_init__)
        trend = TrendData(
            metric_name=metric.value,
            data_points=data_points,
        )
        
        # Analyze trend direction
        trend.trend_direction, trend.trend_strength = self._analyze_trend_direction(
            data_points
        )
        
        self.logger.success(
            f"Trend analysis complete: {trend.trend_direction} "
            f"(strength: {trend.trend_strength:.2f})"
        )
        
        return trend
    
    def analyze_all_metrics(
        self,
        runs: List[TestRunResult],
    ) -> Dict[TrendMetric, TrendData]:
        """
        Analyze trends for all metrics.
        
        Args:
            runs: List of test runs
            
        Returns:
            Dict mapping metrics to trend data
        """
        self.logger.info(f"Analyzing trends for all metrics across {len(runs)} runs")
        
        trends = {}
        for metric in TrendMetric:
            trends[metric] = self.analyze_metric(runs, metric)
        
        return trends
    
    def _extract_metric_value(
        self,
        run: TestRunResult,
        metric: TrendMetric,
    ) -> Optional[float]:
        """Extract metric value from run."""
        if metric == TrendMetric.PASS_RATE:
            return run.pass_rate
        elif metric == TrendMetric.COVERAGE:
            return run.overall_coverage
        elif metric == TrendMetric.DURATION:
            return run.duration
        elif metric == TrendMetric.FLAKY_TESTS:
            return float(run.flaky)
        elif metric == TrendMetric.TOTAL_TESTS:
            return float(run.total_tests)
        elif metric == TrendMetric.FAILURE_RATE:
            if run.total_tests > 0:
                return (run.failed / run.total_tests) * 100
            return 0.0
        
        return None
    
    def _analyze_trend_direction(
        self,
        data_points: List[TrendPoint],
    ) -> tuple:
        """
        Analyze trend direction using linear regression.
        
        Returns:
            (direction, strength) where direction is "improving"/"degrading"/"stable"
            and strength is 0.0-1.0
        """
        if len(data_points) < 2:
            return "stable", 0.0
        
        # Simple linear regression
        n = len(data_points)
        
        # Convert timestamps to numeric (seconds since first point)
        x_values = [(p.timestamp - data_points[0].timestamp).total_seconds() 
                   for p in data_points]
        y_values = [p.value for p in data_points]
        
        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return "stable", 0.0
        
        slope = numerator / denominator
        
        # Calculate R² (coefficient of determination)
        y_pred = [y_mean + slope * (x - x_mean) for x in x_values]
        ss_res = sum((y - y_p) ** 2 for y, y_p in zip(y_values, y_pred))
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        strength = max(0.0, min(1.0, r_squared))  # Clamp to [0, 1]
        
        # Determine direction
        if abs(slope) < self.trend_threshold:
            direction = "stable"
        elif slope > 0:
            direction = "improving"
        else:
            direction = "degrading"
        
        return direction, strength
    
    def detect_anomalies(
        self,
        trend: TrendData,
        std_threshold: float = 2.0,
    ) -> List[TrendPoint]:
        """
        Detect anomalous data points.
        
        Args:
            trend: Trend data
            std_threshold: Number of standard deviations for anomaly
            
        Returns:
            List of anomalous data points
        """
        if not trend.data_points or trend.std_deviation == 0:
            return []
        
        anomalies = []
        
        for point in trend.data_points:
            # Calculate z-score
            z_score = abs((point.value - trend.average) / trend.std_deviation)
            
            if z_score > std_threshold:
                anomalies.append(point)
        
        if anomalies:
            self.logger.info(
                f"Detected {len(anomalies)} anomalies in {trend.metric_name}"
            )
        
        return anomalies
    
    def predict_next_value(
        self,
        trend: TrendData,
        days_ahead: int = 7,
    ) -> Optional[float]:
        """
        Predict next value using linear extrapolation.
        
        Args:
            trend: Trend data
            days_ahead: Days to predict ahead
            
        Returns:
            Predicted value or None
        """
        if len(trend.data_points) < 2:
            return None
        
        # Use last two points for simple prediction
        last_point = trend.data_points[-1]
        prev_point = trend.data_points[-2]
        
        time_diff = (last_point.timestamp - prev_point.timestamp).total_seconds()
        value_diff = last_point.value - prev_point.value
        
        if time_diff == 0:
            return last_point.value
        
        # Calculate rate of change per second
        rate = value_diff / time_diff
        
        # Predict value after days_ahead
        seconds_ahead = days_ahead * 24 * 3600
        predicted = last_point.value + (rate * seconds_ahead)
        
        return predicted
    
    def generate_report(
        self,
        trends: Dict[TrendMetric, TrendData],
    ) -> str:
        """
        Generate human-readable trend report.
        
        Args:
            trends: Dict of metric trends
            
        Returns:
            Formatted report string
        """
        lines = [
            "📈 Trend Analysis Report",
            "=" * 60,
            ""
        ]
        
        for metric, trend in trends.items():
            if not trend.data_points:
                continue
            
            lines.extend([
                f"{metric.value.upper().replace('_', ' ')}:",
                f"  • Current: {trend.data_points[-1].value:.2f}",
                f"  • Average: {trend.average:.2f}",
                f"  • Range: {trend.minimum:.2f} - {trend.maximum:.2f}",
                f"  • Trend: {trend.trend_direction} (strength: {trend.trend_strength:.2f})",
                ""
            ])
            
            # Highlight concerning trends
            if metric == TrendMetric.PASS_RATE and trend.is_degrading:
                lines.append("  ⚠️  WARNING: Pass rate is declining!")
            elif metric == TrendMetric.FAILURE_RATE and trend.is_improving:
                lines.append("  ✅ GOOD: Failure rate is decreasing!")
            elif metric == TrendMetric.COVERAGE and trend.is_improving:
                lines.append("  ✅ GOOD: Coverage is increasing!")
            elif metric == TrendMetric.FLAKY_TESTS and trend.is_improving:
                lines.append("  ⚠️  WARNING: Flaky tests are increasing!")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def analyze_time_window(
        self,
        runs: List[TestRunResult],
        window_days: int = 7,
    ) -> Dict[TrendMetric, TrendData]:
        """
        Analyze trends within a specific time window.
        
        Args:
            runs: All test runs
            window_days: Number of days to analyze
            
        Returns:
            Trend analysis for the window
        """
        # Filter runs to time window
        cutoff = datetime.now() - timedelta(days=window_days)
        recent_runs = [r for r in runs if r.start_time >= cutoff]
        
        if not recent_runs:
            self.logger.warning(f"No runs found in last {window_days} days")
            return {}
        
        self.logger.info(
            f"Analyzing {len(recent_runs)} runs from last {window_days} days"
        )
        
        return self.analyze_all_metrics(recent_runs)
    
    def calculate_velocity(
        self,
        trend: TrendData,
    ) -> float:
        """
        Calculate rate of change (velocity) for a trend.
        
        Args:
            trend: Trend data
            
        Returns:
            Velocity (units per day)
        """
        if len(trend.data_points) < 2:
            return 0.0
        
        first = trend.data_points[0]
        last = trend.data_points[-1]
        
        value_change = last.value - first.value
        time_diff_days = (last.timestamp - first.timestamp).days
        
        if time_diff_days == 0:
            return 0.0
        
        return value_change / time_diff_days
