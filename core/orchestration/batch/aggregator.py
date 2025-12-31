"""
Batch result aggregator for collecting and merging results.

Aggregates results from multiple batch jobs and features, providing
unified reporting and analysis capabilities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.logging import get_logger
from core.orchestration.batch.models import (
    BatchResult,
    BatchJob,
    FeatureType,
    TaskStatus
)


class BatchResultAggregator:
    """
    Aggregates results from batch job executions.
    
    Features:
    - Multi-job result aggregation
    - Feature-specific result extraction
    - Statistical analysis
    - Report generation
    - Result persistence
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize batch result aggregator.
        
        Args:
            storage_dir: Directory to store aggregated results
        """
        self.storage_dir = storage_dir or Path("./batch_results")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = get_logger("core.orchestration.batch.aggregator")
        
        self.logger.info(f"BatchResultAggregator initialized with storage: {self.storage_dir}")
    
    def aggregate_results(self, results: List[BatchResult]) -> Dict[str, Any]:
        """
        Aggregate multiple batch results.
        
        Args:
            results: List of batch results to aggregate
            
        Returns:
            Aggregated statistics and data
        """
        if not results:
            return {}
        
        self.logger.info(f"Aggregating {len(results)} batch results")
        
        aggregated = {
            'total_jobs': len(results),
            'total_tasks': sum(r.total_tasks for r in results),
            'completed_tasks': sum(r.completed_tasks for r in results),
            'failed_tasks': sum(r.failed_tasks for r in results),
            'skipped_tasks': sum(r.skipped_tasks for r in results),
            'total_duration': sum(r.duration for r in results),
            'avg_job_duration': sum(r.duration for r in results) / len(results),
            'avg_success_rate': sum(r.success_rate for r in results) / len(results),
            'jobs': []
        }
        
        # Add individual job summaries
        for result in results:
            aggregated['jobs'].append({
                'job_id': result.job_id,
                'job_name': result.job_name,
                'success_rate': result.success_rate,
                'duration': result.duration,
                'completed_tasks': result.completed_tasks,
                'failed_tasks': result.failed_tasks
            })
        
        # Aggregate feature-specific results
        aggregated['features'] = self._aggregate_feature_results(results)
        
        # Calculate performance metrics
        aggregated['performance'] = self._calculate_performance_metrics(results)
        
        # Identify failures
        aggregated['failures'] = self._collect_failures(results)
        
        self.logger.success(
            f"Aggregated {aggregated['total_jobs']} jobs with "
            f"{aggregated['completed_tasks']}/{aggregated['total_tasks']} tasks completed"
        )
        
        return aggregated
    
    def aggregate_by_feature(
        self,
        results: List[BatchResult],
        feature_type: FeatureType
    ) -> Dict[str, Any]:
        """
        Aggregate results for a specific feature type.
        
        Args:
            results: Batch results to filter
            feature_type: Feature type to aggregate
            
        Returns:
            Feature-specific aggregated results
        """
        self.logger.info(f"Aggregating results for feature: {feature_type.value}")
        
        feature_data = []
        
        for result in results:
            if feature_type in result.feature_results:
                feature_data.extend(result.feature_results[feature_type])
        
        if not feature_data:
            self.logger.warning(f"No results found for feature: {feature_type.value}")
            return {}
        
        aggregated = {
            'feature_type': feature_type.value,
            'total_results': len(feature_data),
            'results': feature_data,
            'summary': self._summarize_feature_data(feature_type, feature_data)
        }
        
        return aggregated
    
    def generate_report(
        self,
        results: List[BatchResult],
        report_format: str = "text"
    ) -> str:
        """
        Generate a human-readable report from batch results.
        
        Args:
            results: Batch results to report on
            report_format: Format (text, json, html)
            
        Returns:
            Formatted report string
        """
        if report_format == "json":
            return json.dumps(self.aggregate_results(results), indent=2, default=str)
        
        # Text format
        aggregated = self.aggregate_results(results)
        
        report_lines = [
            "=" * 80,
            "BATCH EXECUTION REPORT",
            "=" * 80,
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "📊 SUMMARY:",
            f"  • Total Jobs: {aggregated['total_jobs']}",
            f"  • Total Tasks: {aggregated['total_tasks']}",
            f"  • Completed: {aggregated['completed_tasks']} ({aggregated['avg_success_rate']:.1f}%)",
            f"  • Failed: {aggregated['failed_tasks']}",
            f"  • Skipped: {aggregated['skipped_tasks']}",
            f"  • Total Duration: {aggregated['total_duration']:.2f}s",
            f"  • Avg Job Duration: {aggregated['avg_job_duration']:.2f}s",
            "",
        ]
        
        # Job details
        if aggregated['jobs']:
            report_lines.extend([
                "📋 JOBS:",
                ""
            ])
            
            for job in aggregated['jobs']:
                status_emoji = "✅" if job['success_rate'] == 100 else "❌" if job['failed_tasks'] > 0 else "⚠️"
                report_lines.append(
                    f"  {status_emoji} {job['job_name']} - "
                    f"{job['completed_tasks']}/{job['completed_tasks'] + job['failed_tasks']} tasks "
                    f"({job['success_rate']:.1f}%) in {job['duration']:.2f}s"
                )
            
            report_lines.append("")
        
        # Feature results
        if aggregated['features']:
            report_lines.extend([
                "🔧 FEATURES:",
                ""
            ])
            
            for feature, data in aggregated['features'].items():
                report_lines.append(f"  • {feature}: {data.get('count', 0)} results")
            
            report_lines.append("")
        
        # Performance metrics
        if aggregated['performance']:
            perf = aggregated['performance']
            report_lines.extend([
                "⚡ PERFORMANCE:",
                f"  • Fastest Task: {perf.get('fastest_task', 0):.2f}s",
                f"  • Slowest Task: {perf.get('slowest_task', 0):.2f}s",
                f"  • Avg Task Duration: {perf.get('avg_task_duration', 0):.2f}s",
                f"  • Total Retries: {perf.get('total_retries', 0)}",
                ""
            ])
        
        # Failures
        if aggregated['failures']:
            report_lines.extend([
                "❌ FAILURES:",
                ""
            ])
            
            for failure in aggregated['failures'][:10]:  # Show first 10
                report_lines.append(f"  • {failure.get('task', 'Unknown')}: {failure.get('error', 'No details')}")
            
            if len(aggregated['failures']) > 10:
                report_lines.append(f"  ... and {len(aggregated['failures']) - 10} more")
            
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def save_results(
        self,
        results: List[BatchResult],
        filename: Optional[str] = None
    ) -> Path:
        """
        Save aggregated results to file.
        
        Args:
            results: Results to save
            filename: Output filename (generated if None)
            
        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_results_{timestamp}.json"
        
        output_path = self.storage_dir / filename
        
        aggregated = self.aggregate_results(results)
        
        with output_path.open('w') as f:
            json.dump(aggregated, f, indent=2, default=str)
        
        self.logger.success(f"Saved aggregated results to: {output_path}")
        
        return output_path
    
    def _aggregate_feature_results(self, results: List[BatchResult]) -> Dict[str, Any]:
        """Aggregate feature-specific results."""
        feature_aggregation = {}
        
        for result in results:
            for feature_type, feature_data in result.feature_results.items():
                feature_name = feature_type.value
                
                if feature_name not in feature_aggregation:
                    feature_aggregation[feature_name] = {
                        'count': 0,
                        'data': []
                    }
                
                feature_aggregation[feature_name]['count'] += len(feature_data)
                feature_aggregation[feature_name]['data'].extend(feature_data)
        
        return feature_aggregation
    
    def _calculate_performance_metrics(self, results: List[BatchResult]) -> Dict[str, float]:
        """Calculate performance metrics across all results."""
        all_task_durations = []
        total_retries = 0
        
        for result in results:
            for task_data in result.task_results.values():
                if isinstance(task_data, dict) and 'duration' in task_data:
                    all_task_durations.append(task_data['duration'])
            
            total_retries += result.total_retries
        
        if not all_task_durations:
            return {}
        
        return {
            'fastest_task': min(all_task_durations),
            'slowest_task': max(all_task_durations),
            'avg_task_duration': sum(all_task_durations) / len(all_task_durations),
            'total_retries': total_retries
        }
    
    def _collect_failures(self, results: List[BatchResult]) -> List[Dict[str, str]]:
        """Collect all failures from results."""
        failures = []
        
        for result in results:
            failures.extend(result.errors)
        
        return failures
    
    def _summarize_feature_data(
        self,
        feature_type: FeatureType,
        data: List[Any]
    ) -> Dict[str, Any]:
        """Summarize feature-specific data."""
        # Feature-specific summarization logic
        summary = {
            'count': len(data),
            'feature_type': feature_type.value
        }
        
        # Add feature-specific metrics based on type
        if feature_type == FeatureType.FLAKY_DETECTION:
            summary['flaky_tests_found'] = sum(
                d.get('flaky_count', 0) for d in data if isinstance(d, dict)
            )
        elif feature_type == FeatureType.COVERAGE_COLLECTION:
            coverages = [d.get('coverage', 0) for d in data if isinstance(d, dict)]
            if coverages:
                summary['avg_coverage'] = sum(coverages) / len(coverages)
        elif feature_type == FeatureType.TEST_EXECUTION:
            summary['total_tests_run'] = sum(
                d.get('tests_run', 0) for d in data if isinstance(d, dict)
            )
        
        return summary
    
    def compare_results(
        self,
        baseline: BatchResult,
        current: BatchResult
    ) -> Dict[str, Any]:
        """
        Compare two batch results.
        
        Args:
            baseline: Baseline result
            current: Current result to compare
            
        Returns:
            Comparison metrics
        """
        comparison = {
            'baseline': {
                'job_name': baseline.job_name,
                'success_rate': baseline.success_rate,
                'duration': baseline.duration,
                'total_tasks': baseline.total_tasks
            },
            'current': {
                'job_name': current.job_name,
                'success_rate': current.success_rate,
                'duration': current.duration,
                'total_tasks': current.total_tasks
            },
            'changes': {
                'success_rate_delta': current.success_rate - baseline.success_rate,
                'duration_delta': current.duration - baseline.duration,
                'duration_percent_change': (
                    ((current.duration - baseline.duration) / baseline.duration * 100)
                    if baseline.duration > 0 else 0
                ),
                'task_delta': current.total_tasks - baseline.total_tasks
            }
        }
        
        # Determine if there was improvement or regression
        comparison['assessment'] = 'improvement' if (
            comparison['changes']['success_rate_delta'] >= 0 and
            comparison['changes']['duration_percent_change'] <= 10
        ) else 'regression' if (
            comparison['changes']['success_rate_delta'] < 0 or
            comparison['changes']['duration_percent_change'] > 50
        ) else 'neutral'
        
        return comparison
