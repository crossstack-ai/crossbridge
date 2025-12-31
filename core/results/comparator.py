"""
Cross-run result comparison.

Compares test results across different runs to identify improvements,
regressions, new/removed tests, and performance changes.
"""

import uuid
from typing import List, Dict, Set, Optional
from datetime import datetime

from .models import (
    AggregatedResults,
    UnifiedTestResult,
    RunComparison,
    TestStatus
)


class ComparisonReport:
    """
    Detailed comparison report with insights.
    
    Provides human-readable comparison with actionable insights.
    """
    
    def __init__(self, comparison: RunComparison):
        """
        Initialize comparison report.
        
        Args:
            comparison: Run comparison data
        """
        self.comparison = comparison
    
    def get_summary(self) -> str:
        """Get human-readable summary of comparison."""
        lines = []
        lines.append(f"Run Comparison: {self.comparison.run1_id} → {self.comparison.run2_id}")
        lines.append("=" * 70)
        
        # Overall status
        if self.comparison.has_regressions:
            lines.append("❌ REGRESSIONS DETECTED")
        elif self.comparison.has_improvements:
            lines.append("✅ IMPROVEMENTS DETECTED")
        else:
            lines.append("ℹ️  NO SIGNIFICANT CHANGES")
        
        lines.append("")
        
        # Success rate comparison
        lines.append(f"Success Rate:")
        lines.append(f"  Run 1: {self.comparison.run1_success_rate:.1f}%")
        lines.append(f"  Run 2: {self.comparison.run2_success_rate:.1f}%")
        delta_symbol = "📈" if self.comparison.success_rate_delta > 0 else "📉" if self.comparison.success_rate_delta < 0 else "➡️"
        lines.append(f"  Delta: {delta_symbol} {self.comparison.success_rate_delta:+.1f}%")
        lines.append("")
        
        # Test changes
        if self.comparison.new_tests:
            lines.append(f"🆕 New Tests: {len(self.comparison.new_tests)}")
        if self.comparison.removed_tests:
            lines.append(f"🗑️  Removed Tests: {len(self.comparison.removed_tests)}")
        
        # Status changes
        if self.comparison.newly_passing:
            lines.append(f"✅ Newly Passing: {len(self.comparison.newly_passing)}")
            for test in self.comparison.newly_passing[:5]:  # Show first 5
                lines.append(f"   - {test}")
            if len(self.comparison.newly_passing) > 5:
                lines.append(f"   ... and {len(self.comparison.newly_passing) - 5} more")
        
        if self.comparison.newly_failing:
            lines.append(f"❌ Newly Failing: {len(self.comparison.newly_failing)}")
            for test in self.comparison.newly_failing[:5]:
                lines.append(f"   - {test}")
            if len(self.comparison.newly_failing) > 5:
                lines.append(f"   ... and {len(self.comparison.newly_failing) - 5} more")
        
        # Flaky changes
        if self.comparison.newly_flaky:
            lines.append(f"⚠️  Newly Flaky: {len(self.comparison.newly_flaky)}")
        if self.comparison.no_longer_flaky:
            lines.append(f"✨ Fixed Flaky: {len(self.comparison.no_longer_flaky)}")
        
        # Performance changes
        if self.comparison.significantly_slower:
            lines.append(f"🐌 Significantly Slower: {len(self.comparison.significantly_slower)}")
        if self.comparison.significantly_faster:
            lines.append(f"🚀 Significantly Faster: {len(self.comparison.significantly_faster)}")
        
        # Duration comparison
        lines.append("")
        lines.append(f"Total Duration:")
        lines.append(f"  Run 1: {self.comparison.run1_total_duration_ms / 1000:.1f}s")
        lines.append(f"  Run 2: {self.comparison.run2_total_duration_ms / 1000:.1f}s")
        delta_symbol = "📈" if self.comparison.duration_delta_percent > 0 else "📉" if self.comparison.duration_delta_percent < 0 else "➡️"
        lines.append(f"  Delta: {delta_symbol} {self.comparison.duration_delta_percent:+.1f}%")
        
        return "\n".join(lines)
    
    def get_regression_details(self) -> str:
        """Get detailed regression information."""
        if not self.comparison.has_regressions:
            return "No regressions detected."
        
        lines = []
        lines.append("Regression Details")
        lines.append("=" * 70)
        
        if self.comparison.newly_failing:
            lines.append(f"\nNewly Failing Tests ({len(self.comparison.newly_failing)}):")
            for test in self.comparison.newly_failing:
                lines.append(f"  ❌ {test}")
        
        if self.comparison.success_rate_delta < -5.0:
            lines.append(f"\n⚠️  Success rate dropped by {abs(self.comparison.success_rate_delta):.1f}%")
        
        return "\n".join(lines)
    
    def get_improvement_details(self) -> str:
        """Get detailed improvement information."""
        if not self.comparison.has_improvements:
            return "No improvements detected."
        
        lines = []
        lines.append("Improvement Details")
        lines.append("=" * 70)
        
        if self.comparison.newly_passing:
            lines.append(f"\nNewly Passing Tests ({len(self.comparison.newly_passing)}):")
            for test in self.comparison.newly_passing:
                lines.append(f"  ✅ {test}")
        
        if self.comparison.no_longer_flaky:
            lines.append(f"\nFixed Flaky Tests ({len(self.comparison.no_longer_flaky)}):")
            for test in self.comparison.no_longer_flaky:
                lines.append(f"  ✨ {test}")
        
        if self.comparison.success_rate_delta > 5.0:
            lines.append(f"\n🎉 Success rate improved by {self.comparison.success_rate_delta:.1f}%")
        
        return "\n".join(lines)


class ResultComparator:
    """
    Compares test results across different runs.
    
    Identifies changes, regressions, and improvements between runs.
    """
    
    def __init__(self):
        """Initialize result comparator."""
        pass
    
    def compare_runs(
        self,
        run1: AggregatedResults,
        run2: AggregatedResults,
        duration_threshold: float = 50.0  # % change to be considered significant
    ) -> RunComparison:
        """
        Compare two test runs.
        
        Args:
            run1: First run (baseline)
            run2: Second run (comparison)
            duration_threshold: Percentage change threshold for duration significance
            
        Returns:
            Run comparison with detailed changes
        """
        comparison_id = str(uuid.uuid4())
        
        comparison = RunComparison(
            comparison_id=comparison_id,
            run1_id=run1.aggregation_id,
            run2_id=run2.aggregation_id,
            compared_at=datetime.now()
        )
        
        # Build test ID sets
        run1_test_ids = {r.test_id for r in run1.results}
        run2_test_ids = {r.test_id for r in run2.results}
        
        # Find new and removed tests
        comparison.new_tests = list(run2_test_ids - run1_test_ids)
        comparison.removed_tests = list(run1_test_ids - run2_test_ids)
        
        # Build test result maps
        run1_results = {r.test_id: r for r in run1.results}
        run2_results = {r.test_id: r for r in run2.results}
        
        # Compare common tests
        common_tests = run1_test_ids & run2_test_ids
        
        for test_id in common_tests:
            result1 = run1_results[test_id]
            result2 = run2_results[test_id]
            
            # Status changes
            self._compare_status(result1, result2, comparison)
            
            # Flaky changes
            self._compare_flaky(result1, result2, comparison)
            
            # Performance changes
            self._compare_performance(result1, result2, comparison, duration_threshold)
        
        # Calculate statistics
        comparison.improvement_count = len(comparison.newly_passing) + len(comparison.no_longer_flaky)
        comparison.regression_count = len(comparison.newly_failing) + len(comparison.newly_flaky)
        
        # Success rate comparison
        comparison.run1_success_rate = run1.success_rate
        comparison.run2_success_rate = run2.success_rate
        comparison.success_rate_delta = run2.success_rate - run1.success_rate
        
        # Duration comparison
        comparison.run1_total_duration_ms = run1.total_duration_ms
        comparison.run2_total_duration_ms = run2.total_duration_ms
        
        if run1.total_duration_ms > 0:
            comparison.duration_delta_percent = (
                (run2.total_duration_ms - run1.total_duration_ms) /
                run1.total_duration_ms * 100.0
            )
        
        return comparison
    
    def compare_multiple_runs(
        self,
        runs: List[AggregatedResults]
    ) -> List[RunComparison]:
        """
        Compare multiple sequential runs.
        
        Args:
            runs: List of aggregated results in chronological order
            
        Returns:
            List of pairwise comparisons
        """
        comparisons = []
        
        for i in range(len(runs) - 1):
            comparison = self.compare_runs(runs[i], runs[i + 1])
            comparisons.append(comparison)
        
        return comparisons
    
    def find_persistent_failures(
        self,
        runs: List[AggregatedResults],
        min_consecutive: int = 3
    ) -> List[str]:
        """
        Find tests that have failed persistently across multiple runs.
        
        Args:
            runs: List of aggregated results
            min_consecutive: Minimum consecutive failures to be considered persistent
            
        Returns:
            List of test IDs with persistent failures
        """
        if len(runs) < min_consecutive:
            return []
        
        # Track consecutive failures for each test
        failure_counts: Dict[str, int] = {}
        
        for run in runs:
            # Get failed tests in this run
            failed_tests = {
                r.test_id for r in run.results
                if r.status in [TestStatus.FAILED, TestStatus.ERROR]
            }
            
            # Update counts
            for test_id in failed_tests:
                failure_counts[test_id] = failure_counts.get(test_id, 0) + 1
            
            # Reset count for tests that didn't fail
            all_tests = {r.test_id for r in run.results}
            for test_id in all_tests - failed_tests:
                failure_counts[test_id] = 0
        
        # Return tests with >= min_consecutive failures
        return [
            test_id for test_id, count in failure_counts.items()
            if count >= min_consecutive
        ]
    
    def find_intermittent_failures(
        self,
        runs: List[AggregatedResults],
        failure_threshold: float = 0.2  # 20% failure rate
    ) -> Dict[str, float]:
        """
        Find tests with intermittent failures (potential flaky tests).
        
        Args:
            runs: List of aggregated results
            failure_threshold: Minimum failure rate to be considered intermittent
            
        Returns:
            Dictionary mapping test ID to failure rate
        """
        # Track pass/fail for each test
        test_records: Dict[str, List[bool]] = {}
        
        for run in runs:
            for result in run.results:
                if result.test_id not in test_records:
                    test_records[result.test_id] = []
                
                passed = result.status == TestStatus.PASSED
                test_records[result.test_id].append(passed)
        
        # Calculate failure rates
        intermittent = {}
        
        for test_id, records in test_records.items():
            if len(records) < 2:
                continue
            
            failure_rate = 1.0 - (sum(records) / len(records))
            
            # Intermittent if sometimes passes and sometimes fails
            if 0 < failure_rate < 1.0 and failure_rate >= failure_threshold:
                intermittent[test_id] = failure_rate
        
        return intermittent
    
    def _compare_status(
        self,
        result1: UnifiedTestResult,
        result2: UnifiedTestResult,
        comparison: RunComparison
    ):
        """Compare test status between runs."""
        status1 = result1.status
        status2 = result2.status
        
        # Passed -> Failed
        if status1 == TestStatus.PASSED and status2 in [TestStatus.FAILED, TestStatus.ERROR]:
            comparison.newly_failing.append(result1.test_id)
        
        # Failed -> Passed
        elif status1 in [TestStatus.FAILED, TestStatus.ERROR] and status2 == TestStatus.PASSED:
            comparison.newly_passing.append(result1.test_id)
        
        # Still passing
        elif status1 == TestStatus.PASSED and status2 == TestStatus.PASSED:
            comparison.still_passing.append(result1.test_id)
        
        # Still failing
        elif status1 in [TestStatus.FAILED, TestStatus.ERROR] and status2 in [TestStatus.FAILED, TestStatus.ERROR]:
            comparison.still_failing.append(result1.test_id)
    
    def _compare_flaky(
        self,
        result1: UnifiedTestResult,
        result2: UnifiedTestResult,
        comparison: RunComparison
    ):
        """Compare flaky status between runs."""
        flaky1 = result1.is_flaky or result1.status == TestStatus.FLAKY
        flaky2 = result2.is_flaky or result2.status == TestStatus.FLAKY
        
        # Became flaky
        if not flaky1 and flaky2:
            comparison.newly_flaky.append(result1.test_id)
        
        # No longer flaky
        elif flaky1 and not flaky2:
            comparison.no_longer_flaky.append(result1.test_id)
    
    def _compare_performance(
        self,
        result1: UnifiedTestResult,
        result2: UnifiedTestResult,
        comparison: RunComparison,
        threshold: float
    ):
        """Compare performance between runs."""
        if result1.duration_ms == 0:
            return
        
        percent_change = (
            (result2.duration_ms - result1.duration_ms) /
            result1.duration_ms * 100.0
        )
        
        # Significantly slower
        if percent_change > threshold:
            comparison.significantly_slower.append(result1.test_id)
        
        # Significantly faster
        elif percent_change < -threshold:
            comparison.significantly_faster.append(result1.test_id)
