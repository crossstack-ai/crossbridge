"""
Feature engineering for flaky test detection.

Extracts numerical features from test execution history for use
in machine learning-based flaky detection.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter
import statistics

from .models import TestExecutionRecord, FlakyFeatureVector, TestStatus


class FeatureEngineer:
    """
    Extracts features from test execution history for flaky detection.
    
    Computes statistical, temporal, and behavioral features that help
    identify flaky tests across all frameworks.
    """
    
    def __init__(self, window_size: int = 50, recent_window: int = 10):
        """
        Initialize feature engineer.
        
        Args:
            window_size: Maximum number of recent executions to analyze
            recent_window: Number of most recent runs for temporal features
        """
        self.window_size = window_size
        self.recent_window = recent_window
    
    def extract_features(
        self,
        executions: List[TestExecutionRecord]
    ) -> Optional[FlakyFeatureVector]:
        """
        Extract features from test execution history.
        
        Args:
            executions: List of execution records for a single test,
                       sorted by execution time (oldest first)
        
        Returns:
            FlakyFeatureVector if sufficient data, None otherwise
        """
        if not executions:
            return None
        
        # Get test identifier
        test_id = executions[0].test_id
        
        # Limit to window size (most recent)
        executions = executions[-self.window_size:]
        
        if len(executions) < 3:
            # Need minimum data for meaningful features
            return None
        
        # Extract features
        failure_rate = self._compute_failure_rate(executions)
        switch_rate = self._compute_switch_rate(executions)
        duration_stats = self._compute_duration_stats(executions)
        retry_stats = self._compute_retry_stats(executions)
        error_stats = self._compute_error_stats(executions)
        temporal_stats = self._compute_temporal_stats(executions)
        
        return FlakyFeatureVector(
            test_id=test_id,
            failure_rate=failure_rate,
            pass_fail_switch_rate=switch_rate,
            duration_variance=duration_stats["variance"],
            mean_duration_ms=duration_stats["mean"],
            duration_cv=duration_stats["cv"],
            retry_success_rate=retry_stats["success_rate"],
            avg_retry_count=retry_stats["avg_retry_count"],
            unique_error_count=error_stats["unique_count"],
            error_diversity_ratio=error_stats["diversity_ratio"],
            same_commit_failure_rate=temporal_stats["same_commit_failure_rate"],
            recent_failure_rate=temporal_stats["recent_failure_rate"],
            total_executions=len(executions),
            window_size=self.window_size,
            last_executed=executions[-1].executed_at
        )
    
    def extract_batch_features(
        self,
        execution_groups: Dict[str, List[TestExecutionRecord]]
    ) -> Dict[str, FlakyFeatureVector]:
        """
        Extract features for multiple tests in batch.
        
        Args:
            execution_groups: Dictionary mapping test_id to execution records
        
        Returns:
            Dictionary mapping test_id to feature vector
        """
        features = {}
        
        for test_id, executions in execution_groups.items():
            # Sort by execution time
            sorted_executions = sorted(executions, key=lambda e: e.executed_at)
            
            feature_vector = self.extract_features(sorted_executions)
            if feature_vector:
                features[test_id] = feature_vector
        
        return features
    
    def _compute_failure_rate(self, executions: List[TestExecutionRecord]) -> float:
        """Compute failure rate: failures / total executions."""
        if not executions:
            return 0.0
        
        failures = sum(1 for e in executions if e.is_failed)
        return failures / len(executions)
    
    def _compute_switch_rate(self, executions: List[TestExecutionRecord]) -> float:
        """
        Compute pass/fail switch rate.
        
        Measures how often the test status changes between consecutive runs.
        High switch rate indicates flakiness.
        """
        if len(executions) < 2:
            return 0.0
        
        switches = 0
        for i in range(1, len(executions)):
            prev_status = executions[i - 1].status
            curr_status = executions[i].status
            
            # Count transitions between passed and failed/error
            prev_passed = prev_status == TestStatus.PASSED
            curr_passed = curr_status == TestStatus.PASSED
            
            if prev_passed != curr_passed:
                switches += 1
        
        return switches / (len(executions) - 1)
    
    def _compute_duration_stats(self, executions: List[TestExecutionRecord]) -> dict:
        """
        Compute duration statistics.
        
        High variance in duration can indicate timing-sensitive flakiness.
        """
        durations = [e.duration_ms for e in executions]
        
        if not durations:
            return {"mean": 0.0, "variance": 0.0, "cv": 0.0}
        
        mean = statistics.mean(durations)
        
        if len(durations) < 2:
            variance = 0.0
            cv = 0.0
        else:
            variance = statistics.variance(durations)
            cv = (statistics.stdev(durations) / mean) if mean > 0 else 0.0
        
        return {
            "mean": mean,
            "variance": variance,
            "cv": cv
        }
    
    def _compute_retry_stats(self, executions: List[TestExecutionRecord]) -> dict:
        """
        Compute retry statistics.
        
        Tests that require retries are often flaky.
        """
        executions_with_retries = [e for e in executions if e.retry_count > 0]
        
        if not executions_with_retries:
            return {
                "success_rate": 0.0,
                "avg_retry_count": 0.0
            }
        
        # Count successful retries (executions with retries that passed)
        successful_retries = sum(
            1 for e in executions_with_retries
            if e.is_passed
        )
        
        success_rate = (
            successful_retries / len(executions_with_retries)
            if executions_with_retries else 0.0
        )
        
        avg_retry_count = statistics.mean(
            [e.retry_count for e in executions_with_retries]
        )
        
        return {
            "success_rate": success_rate,
            "avg_retry_count": avg_retry_count
        }
    
    def _compute_error_stats(self, executions: List[TestExecutionRecord]) -> dict:
        """
        Compute error diversity statistics.
        
        Flaky tests often fail with different error types.
        """
        failed_executions = [e for e in executions if e.is_failed]
        
        if not failed_executions:
            return {
                "unique_count": 0,
                "diversity_ratio": 0.0
            }
        
        # Count unique error signatures
        error_types = [
            e.get_error_type() or e.error_signature or "Unknown"
            for e in failed_executions
        ]
        
        unique_errors = len(set(error_types))
        diversity_ratio = unique_errors / len(failed_executions)
        
        return {
            "unique_count": unique_errors,
            "diversity_ratio": diversity_ratio
        }
    
    def _compute_temporal_stats(self, executions: List[TestExecutionRecord]) -> dict:
        """
        Compute temporal features.
        
        Includes same-commit failure rate and recent failure trends.
        """
        # Same-commit failure rate
        commit_failures = {}
        commit_totals = {}
        
        for execution in executions:
            if execution.git_commit:
                commit = execution.git_commit
                commit_totals[commit] = commit_totals.get(commit, 0) + 1
                
                if execution.is_failed:
                    commit_failures[commit] = commit_failures.get(commit, 0) + 1
        
        # Calculate average failure rate per commit
        if commit_totals:
            commit_failure_rates = [
                commit_failures.get(c, 0) / total
                for c, total in commit_totals.items()
            ]
            same_commit_failure_rate = statistics.mean(commit_failure_rates)
        else:
            same_commit_failure_rate = 0.0
        
        # Recent failure rate (last N executions)
        recent_executions = executions[-self.recent_window:]
        recent_failures = sum(1 for e in recent_executions if e.is_failed)
        recent_failure_rate = recent_failures / len(recent_executions)
        
        return {
            "same_commit_failure_rate": same_commit_failure_rate,
            "recent_failure_rate": recent_failure_rate
        }


def normalize_error_signature(error_message: str, max_length: int = 200) -> str:
    """
    Normalize error message to create consistent error signatures.
    
    Strips dynamic content like timestamps, IDs, line numbers, etc.
    
    Args:
        error_message: Raw error message
        max_length: Maximum length of normalized signature
    
    Returns:
        Normalized error signature
    """
    if not error_message:
        return "Unknown"
    
    import re
    
    # Get first line (usually contains the error type)
    lines = error_message.strip().split('\n')
    signature = lines[0]
    
    # Remove common dynamic content patterns
    # Line numbers: "file.py:123"
    signature = re.sub(r':\d+', ':N', signature)
    
    # Hex addresses: "0x7f8a9b0c1d2e"
    signature = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', signature)
    
    # UUIDs
    signature = re.sub(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        'UUID',
        signature,
        flags=re.IGNORECASE
    )
    
    # Timestamps
    signature = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', signature)
    signature = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', signature)
    
    # Numbers in error messages
    signature = re.sub(r'\b\d+\b', 'N', signature)
    
    # Truncate to max length
    if len(signature) > max_length:
        signature = signature[:max_length] + "..."
    
    return signature
