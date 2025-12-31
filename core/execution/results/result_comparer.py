"""
Cross-run result comparison.

Compares test results between runs to identify:
- New/removed tests
- Status changes (newly passing/failing)
- Performance changes
- Coverage changes
- Flaky test detection
"""

from typing import List, Dict, Set, Optional
from enum import Enum
from datetime import datetime

from .models import (
    TestResult,
    TestRunResult,
    ComparisonResult,
    TestStatus,
)
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.EXECUTION)


class ComparisonStrategy(Enum):
    """Strategy for comparing test runs."""
    STRICT = "strict"           # All differences matter
    STATUS_ONLY = "status_only"  # Only status changes
    PERFORMANCE = "performance"  # Focus on performance
    COVERAGE = "coverage"        # Focus on coverage


class ResultComparer:
    """
    Compares test results between runs.
    
    Identifies changes, regressions, and improvements.
    """
    
    def __init__(
        self,
        performance_threshold: float = 0.2,  # 20% change
        coverage_threshold: float = 1.0,      # 1% change
    ):
        """
        Initialize comparer.
        
        Args:
            performance_threshold: Threshold for performance changes (0.0-1.0)
            coverage_threshold: Threshold for coverage changes (percentage points)
        """
        self.performance_threshold = performance_threshold
        self.coverage_threshold = coverage_threshold
        self.logger = get_logger(__name__, category=LogCategory.EXECUTION)
    
    def compare(
        self,
        baseline: TestRunResult,
        current: TestRunResult,
        strategy: ComparisonStrategy = ComparisonStrategy.STRICT,
    ) -> ComparisonResult:
        """
        Compare two test runs.
        
        Args:
            baseline: Baseline (old) run
            current: Current (new) run
            strategy: Comparison strategy
            
        Returns:
            ComparisonResult with all differences
        """
        self.logger.info(f"Comparing {current.run_id} against baseline {baseline.run_id}")
        
        # Create test maps
        baseline_tests = {t.test_id: t for t in baseline.tests}
        current_tests = {t.test_id: t for t in current.tests}
        
        baseline_ids = set(baseline_tests.keys())
        current_ids = set(current_tests.keys())
        
        # Find new and removed tests
        new_test_ids = current_ids - baseline_ids
        removed_test_ids = baseline_ids - current_ids
        common_ids = baseline_ids & current_ids
        
        new_tests = [current_tests[tid] for tid in new_test_ids]
        removed_tests = list(removed_test_ids)
        
        self.logger.debug(
            f"New: {len(new_tests)}, Removed: {len(removed_tests)}, "
            f"Common: {len(common_ids)}"
        )
        
        # Analyze status changes
        newly_passing = []
        newly_failing = []
        newly_flaky = []
        
        for test_id in common_ids:
            baseline_test = baseline_tests[test_id]
            current_test = current_tests[test_id]
            
            # Status changes
            if baseline_test.status != TestStatus.PASSED and current_test.status == TestStatus.PASSED:
                newly_passing.append(current_test)
            elif baseline_test.status == TestStatus.PASSED and current_test.status == TestStatus.FAILED:
                newly_failing.append(current_test)
            
            # Flaky detection
            if not baseline_test.is_flaky and current_test.is_flaky:
                newly_flaky.append(current_test)
        
        # Performance comparison
        faster_tests = []
        slower_tests = []
        
        if strategy in [ComparisonStrategy.STRICT, ComparisonStrategy.PERFORMANCE]:
            for test_id in common_ids:
                baseline_test = baseline_tests[test_id]
                current_test = current_tests[test_id]
                
                if baseline_test.duration == 0 or current_test.duration == 0:
                    continue
                
                # Calculate percentage change
                change_pct = (current_test.duration - baseline_test.duration) / baseline_test.duration
                
                if abs(change_pct) >= self.performance_threshold:
                    if change_pct < 0:  # Faster
                        faster_tests.append((
                            test_id,
                            baseline_test.duration,
                            current_test.duration
                        ))
                    else:  # Slower
                        slower_tests.append((
                            test_id,
                            baseline_test.duration,
                            current_test.duration
                        ))
        
        # Coverage comparison
        coverage_improved = False
        coverage_degraded = False
        coverage_delta = 0.0
        
        if baseline.overall_coverage and current.overall_coverage:
            coverage_delta = current.overall_coverage - baseline.overall_coverage
            
            if abs(coverage_delta) >= self.coverage_threshold:
                if coverage_delta > 0:
                    coverage_improved = True
                else:
                    coverage_degraded = True
        
        # Create comparison result
        result = ComparisonResult(
            run1_id=baseline.run_id,
            run2_id=current.run_id,
            new_tests=new_tests,
            removed_tests=removed_tests,
            newly_passing=newly_passing,
            newly_failing=newly_failing,
            newly_flaky=newly_flaky,
            faster_tests=faster_tests,
            slower_tests=slower_tests,
            coverage_improved=coverage_improved,
            coverage_degraded=coverage_degraded,
            coverage_delta=coverage_delta,
        )
        
        self.logger.success(
            f"Comparison complete: {result.improvements} improvements, "
            f"{result.regressions} regressions, {result.total_changes} total changes"
        )
        
        return result
    
    def compare_multiple(
        self,
        runs: List[TestRunResult],
        strategy: ComparisonStrategy = ComparisonStrategy.STRICT,
    ) -> List[ComparisonResult]:
        """
        Compare multiple runs sequentially.
        
        Args:
            runs: List of runs ordered by time
            strategy: Comparison strategy
            
        Returns:
            List of comparison results (run[i] vs run[i+1])
        """
        if len(runs) < 2:
            self.logger.warning("Need at least 2 runs for comparison")
            return []
        
        self.logger.info(f"Comparing {len(runs)} runs sequentially")
        
        comparisons = []
        for i in range(len(runs) - 1):
            comparison = self.compare(runs[i], runs[i + 1], strategy)
            comparisons.append(comparison)
        
        return comparisons
    
    def find_regression_candidates(
        self,
        comparison: ComparisonResult,
        min_duration: float = 0.1,  # seconds
    ) -> List[TestResult]:
        """
        Find tests that are likely regressions.
        
        Args:
            comparison: Comparison result
            min_duration: Minimum duration to consider
            
        Returns:
            List of tests that are regression candidates
        """
        candidates = []
        
        # Newly failing tests are regressions
        candidates.extend(comparison.newly_failing)
        
        # Newly flaky tests might be regressions
        candidates.extend(comparison.newly_flaky)
        
        # Significantly slower tests might be regressions
        for test_id, old_duration, new_duration in comparison.slower_tests:
            if new_duration >= min_duration:
                # Find the test result
                # (This is simplified - in practice, need to look up from current run)
                pass
        
        self.logger.info(f"Found {len(candidates)} regression candidates")
        return candidates
    
    def generate_summary(self, comparison: ComparisonResult) -> str:
        """
        Generate human-readable comparison summary.
        
        Args:
            comparison: Comparison result
            
        Returns:
            Formatted summary string
        """
        lines = [
            f"Comparison: {comparison.run1_id} → {comparison.run2_id}",
            f"",
            f"📊 Test Changes:",
            f"  • New tests: {len(comparison.new_tests)}",
            f"  • Removed tests: {len(comparison.removed_tests)}",
            f"",
            f"✅ Improvements:",
            f"  • Newly passing: {len(comparison.newly_passing)}",
            f"  • Faster tests: {len(comparison.faster_tests)}",
        ]
        
        if comparison.coverage_improved:
            lines.append(f"  • Coverage improved: +{comparison.coverage_delta:.2f}%")
        
        lines.extend([
            f"",
            f"❌ Regressions:",
            f"  • Newly failing: {len(comparison.newly_failing)}",
            f"  • Newly flaky: {len(comparison.newly_flaky)}",
            f"  • Slower tests: {len(comparison.slower_tests)}",
        ])
        
        if comparison.coverage_degraded:
            lines.append(f"  • Coverage degraded: {comparison.coverage_delta:.2f}%")
        
        lines.extend([
            f"",
            f"📈 Summary:",
            f"  • Total changes: {comparison.total_changes}",
            f"  • Improvements: {comparison.improvements}",
            f"  • Regressions: {comparison.regressions}",
        ])
        
        return "\n".join(lines)
