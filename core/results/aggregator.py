"""
Result aggregation and normalization.

Aggregates results from multiple sources (execution, coverage, flaky detection)
into unified result sets with comprehensive statistics.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from .models import (
    UnifiedTestResult,
    AggregatedResults,
    ResultSource,
    TestStatus
)

# Import from other modules
from core.execution.models import (
    ExecutionSummary,
    TestExecutionResult,
    ExecutionStatus
)
from core.coverage.models import TestCoverageMapping
from core.flaky_detection.models import (
    TestExecutionRecord,
    FlakyTestResult,
    TestStatus as FlakyTestStatus
)


class ResultNormalizer:
    """
    Normalizes results from different frameworks into unified format.
    
    Handles framework-specific differences and creates consistent
    UnifiedTestResult instances.
    """
    
    @staticmethod
    def normalize_execution_result(
        result: TestExecutionResult,
        run_id: Optional[str] = None,
        build_id: Optional[str] = None,
        git_commit: Optional[str] = None
    ) -> UnifiedTestResult:
        """
        Normalize execution result to unified format.
        
        Args:
            result: Execution result from test executor
            run_id: Optional run identifier
            build_id: Optional build identifier
            git_commit: Optional git commit SHA
            
        Returns:
            Unified test result
        """
        # Map execution status to test status
        status_map = {
            ExecutionStatus.PASSED: TestStatus.PASSED,
            ExecutionStatus.FAILED: TestStatus.FAILED,
            ExecutionStatus.SKIPPED: TestStatus.SKIPPED,
            ExecutionStatus.ERROR: TestStatus.ERROR,
            ExecutionStatus.TIMEOUT: TestStatus.TIMEOUT,
            ExecutionStatus.CANCELLED: TestStatus.CANCELLED
        }
        
        status = status_map.get(result.status, TestStatus.ERROR)
        
        # Override with FLAKY if detected
        if result.is_flaky:
            status = TestStatus.FLAKY
        
        return UnifiedTestResult(
            test_id=result.test_id,
            test_name=result.name,
            framework=result.framework or "unknown",
            status=status,
            duration_ms=result.duration_ms,
            executed_at=result.start_time or datetime.now(),
            run_id=run_id,
            build_id=build_id,
            git_commit=git_commit,
            tags=result.tags or [],
            file_path=result.file_path,
            error_message=result.error_message,
            error_type=result.error_type,
            stack_trace=result.stack_trace,
            is_flaky=result.is_flaky,
            retry_count=result.retry_count,
            coverage_percentage=None,  # Will be enriched later
            data_sources={ResultSource.EXECUTION}
        )
    
    @staticmethod
    def normalize_flaky_record(
        record: TestExecutionRecord,
        prediction: Optional[FlakyTestResult] = None
    ) -> UnifiedTestResult:
        """
        Normalize flaky detection record to unified format.
        
        Args:
            record: Flaky detection execution record
            prediction: Optional flaky prediction data
            
        Returns:
            Unified test result
        """
        # Map flaky status to test status
        status_map = {
            FlakyTestStatus.PASSED: TestStatus.PASSED,
            FlakyTestStatus.FAILED: TestStatus.FAILED,
            FlakyTestStatus.SKIPPED: TestStatus.SKIPPED,
            FlakyTestStatus.ABORTED: TestStatus.CANCELLED,
            FlakyTestStatus.ERROR: TestStatus.ERROR
        }
        
        status = status_map.get(record.status, TestStatus.ERROR)
        
        # Extract flaky data from prediction
        flaky_prob = None
        is_flaky = False
        historical_stability = None
        
        if prediction:
            # FlakyTestResult uses flaky_score instead of flaky_probability
            flaky_prob = 1.0 - prediction.flaky_score if hasattr(prediction, 'flaky_score') else None
            is_flaky = prediction.is_flaky
            historical_stability = prediction.confidence
        
        if is_flaky:
            status = TestStatus.FLAKY
        
        return UnifiedTestResult(
            test_id=record.test_id,
            test_name=record.test_id,  # Use test_id as name if no separate name
            framework=record.framework.value,
            status=status,
            duration_ms=record.duration_ms,
            executed_at=record.executed_at,
            build_id=record.build_id,
            environment=record.environment,
            git_commit=record.git_commit,
            error_message=record.error_signature,
            is_flaky=is_flaky,
            flaky_probability=flaky_prob,
            retry_count=record.retry_count,
            historical_stability=prediction.confidence if prediction else None,
            data_sources={ResultSource.FLAKY_DETECTION}
        )
    
    @staticmethod
    def enrich_with_coverage(
        result: UnifiedTestResult,
        coverage: TestCoverageMapping
    ) -> UnifiedTestResult:
        """
        Enrich unified result with coverage data.
        
        Args:
            result: Existing unified result
            coverage: Coverage mapping data
            
        Returns:
            Enriched unified result
        """
        result.covered_classes = {unit.class_name for unit in coverage.covered_units}
        result.covered_methods = {
            f"{unit.class_name}.{unit.method_name}"
            for unit in coverage.covered_units
            if unit.method_name
        }
        
        # Calculate coverage percentage if metrics available
        if hasattr(coverage, 'instruction_count') and hasattr(coverage, 'instructions_covered'):
            if coverage.instruction_count > 0:
                result.coverage_percentage = (
                    coverage.instructions_covered / coverage.instruction_count * 100.0
                )
        
        result.data_sources.add(ResultSource.COVERAGE)
        
        return result


class ResultAggregator:
    """
    Aggregates test results from multiple sources.
    
    Combines execution results, coverage data, flakResultn data,
    and impact analysis into comprehensive aggregated results.
    """
    
    def __init__(self):
        """Initialize result aggregator."""
        self.results: List[UnifiedTestResult] = []
        self.coverage_data: Dict[str, TestCoverageMapping] = {}
        self.flaky_predictions: Dict[str, FlakyTestPrediction] = {}
        self.normalizer = ResultNormalizer()
    
    def add_execution_summary(
        self,
        summary: ExecutionSummary,
        run_id: Optional[str] = None,
        build_id: Optional[str] = None,
        git_commit: Optional[str] = None
    ):
        """
        Add execution summary results.
        
        Args:
            summary: Execution summary from test executor
            run_id: Optional run identifier
            build_id: Optional build identifier
            git_commit: Optional git commit SHA
        """
        for exec_result in summary.results:
            unified = self.normalizer.normalize_execution_result(
                exec_result,
                run_id=run_id,
                build_id=build_id,
                git_commit=git_commit
            )
            self.results.append(unified)
    
    def add_flaky_records(
        self,
        records: List[TestExecutionRecord],
        predictions: Optional[Dict[str, FlakyTestResult]] = None
    ):
        """
        Add flaky detection records.
        
        Args:
            records: List of flaky detection execution records
            predictions: Optional mapping of test_id to flaky predictions
        """
        predictions = predictions or {}
        
        for record in records:
            prediction = predictions.get(record.test_id)
            unified = self.normalizer.normalize_flaky_record(record, prediction)
            
            # Try to merge with existing result
            existing = self._find_existing_result(unified.test_id, unified.executed_at)
            if existing:
                self._merge_results(existing, unified)
            else:
                self.results.append(unified)
    
    def add_coverage_data(self, coverage_mappings: List[TestCoverageMapping]):
        """
        Add coverage data for tests.
        
        Args:
            coverage_mappings: List of test coverage mappings
        """
        for mapping in coverage_mappings:
            self.coverage_data[mapping.test_identifier] = mapping
            
            # Enrich existing results with coverage
            for result in self.results:
                if result.test_id == mapping.test_identifier:
                    self.normalizer.enrich_with_coverage(result, mapping)
    
    def mark_impacted_tests(self, impacted_test_ids: List[str], risk_scores: Optional[Dict[str, float]] = None):
        """
        Mark tests as impacted by changes.
        
        Args:
            impacted_test_ids: List of test IDs impacted by code changes
            risk_scores: Optional mapping of test_id to change risk score
        """
        risk_scores = risk_scores or {}
        
        for result in self.results:
            if result.test_id in impacted_test_ids:
                result.impacted_by_changes = True
                result.change_risk_score = risk_scores.get(result.test_id)
                result.data_sources.add(ResultSource.IMPACT_ANALYSIS)
    
    def get_aggregated_results(self) -> AggregatedResults:
        """
        Get aggregated results with statistics.
        
        Returns:
            Aggregated results with computed statistics
        """
        aggregation_id = str(uuid.uuid4())
        
        # Initialize aggregation
        aggregated = AggregatedResults(
            aggregation_id=aggregation_id,
            created_at=datetime.now()
        )
        
        if not self.results:
            return aggregated
        
        # Add results
        aggregated.results = self.results.copy()
        
        # Calculate time range
        timestamps = [r.executed_at for r in self.results]
        aggregated.start_time = min(timestamps)
        aggregated.end_time = max(timestamps)
        
        # Calculate counts
        aggregated.total_tests = len(self.results)
        aggregated.passed_tests = len([r for r in self.results if r.status == TestStatus.PASSED])
        aggregated.failed_tests = len([r for r in self.results if r.status == TestStatus.FAILED])
        aggregated.skipped_tests = len([r for r in self.results if r.status == TestStatus.SKIPPED])
        aggregated.flaky_tests = len([r for r in self.results if r.is_flaky or r.status == TestStatus.FLAKY])
        
        # Calculate timing statistics
        durations = [r.duration_ms for r in self.results]
        aggregated.total_duration_ms = sum(durations)
        aggregated.avg_duration_ms = sum(durations) / len(durations) if durations else 0
        aggregated.median_duration_ms = self._calculate_median(durations)
        
        # Calculate coverage statistics
        coverage_values = [r.coverage_percentage for r in self.results if r.coverage_percentage is not None]
        if coverage_values:
            aggregated.avg_coverage = sum(coverage_values) / len(coverage_values)
        
        all_classes = set()
        all_methods = set()
        for result in self.results:
            all_classes.update(result.covered_classes)
            all_methods.update(result.covered_methods)
        
        aggregated.total_classes_covered = len(all_classes)
        aggregated.total_methods_covered = len(all_methods)
        
        # Collect frameworks and environments
        aggregated.frameworks = {r.framework for r in self.results}
        aggregated.environments = {r.environment for r in self.results}
        
        # Collect data sources
        for result in self.results:
            aggregated.sources.update(result.data_sources)
        
        return aggregated
    
    def clear(self):
        """Clear all accumulated results."""
        self.results.clear()
        self.coverage_data.clear()
        self.flaky_predictions.clear()
    
    def _find_existing_result(self, test_id: str, timestamp: datetime) -> Optional[UnifiedTestResult]:
        """Find existing result for test at similar timestamp."""
        # Look for results within 1 second
        for result in self.results:
            if result.test_id == test_id:
                time_diff = abs((result.executed_at - timestamp).total_seconds())
                if time_diff < 1.0:
                    return result
        return None
    
    def _merge_results(self, existing: UnifiedTestResult, new: UnifiedTestResult):
        """Merge data from new result into existing."""
        # Merge data sources
        existing.data_sources.update(new.data_sources)
        
        # Update flaky data if new has it
        if new.is_flaky and not existing.is_flaky:
            existing.is_flaky = new.is_flaky
            existing.flaky_probability = new.flaky_probability
            existing.historical_stability = new.historical_stability
        
        # Merge tags and categories
        existing.tags = list(set(existing.tags) | set(new.tags))
        existing.categories = list(set(existing.categories) | set(new.categories))
        
        # Update metadata
        existing.metadata.update(new.metadata)
    
    @staticmethod
    def _calculate_median(values: List[float]) -> float:
        """Calculate median of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]
