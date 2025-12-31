"""
Unified result aggregator for collecting results from all sources.

Aggregates results from:
- Test executions (pytest, JUnit, TestNG, Robot, etc.)
- Coverage reports (JaCoCo, Coverage.py, etc.)
- Flaky test detection
- Performance metrics
"""

from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import json

from .models import (
    TestResult,
    TestRunResult,
    AggregatedResults,
    TestStatus,
    FrameworkType,
    ResultMetadata,
)
from .normalizer import ResultNormalizer
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.EXECUTION)


class ResultCollector:
    """
    Base result collector interface.
    
    Implementations collect specific types of results.
    """
    
    def collect(self, source: Path) -> List[TestResult]:
        """Collect results from source."""
        raise NotImplementedError


class FlakyTestCollector(ResultCollector):
    """Collects flaky test detection results."""
    
    def collect(self, source: Path) -> List[TestResult]:
        """
        Collect flaky test results.
        
        Args:
            source: Path to flaky test report
            
        Returns:
            List of test results with flaky information
        """
        logger.debug(f"Collecting flaky test results from {source}")
        
        results = []
        
        try:
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for test_id, flaky_data in data.get('flaky_tests', {}).items():
                result = TestResult(
                    test_id=test_id,
                    test_name=flaky_data.get('name', test_id),
                    status=TestStatus.FLAKY,
                    is_flaky=True,
                    flaky_runs=flaky_data.get('runs', []),
                    pass_rate=flaky_data.get('pass_rate', 0.0),
                    framework_data={'flaky_detection': flaky_data}
                )
                results.append(result)
            
            logger.info(f"Collected {len(results)} flaky tests")
            return results
            
        except Exception as e:
            logger.exception(f"Failed to collect flaky test results from {source}")
            return []


class CoverageCollector(ResultCollector):
    """Collects code coverage results."""
    
    def collect_jacoco(self, source: Path) -> Dict[str, float]:
        """
        Collect JaCoCo coverage results.
        
        Args:
            source: Path to JaCoCo XML report
            
        Returns:
            Dict mapping file paths to coverage percentages
        """
        logger.debug(f"Collecting JaCoCo coverage from {source}")
        
        import xml.etree.ElementTree as ET
        
        try:
            tree = ET.parse(source)
            root = tree.getroot()
            
            coverage_by_file = {}
            
            for package in root.findall('.//package'):
                for sourcefile in package.findall('sourcefile'):
                    filename = sourcefile.get('name', '')
                    
                    # Calculate line coverage
                    lines_covered = 0
                    lines_total = 0
                    
                    for counter in sourcefile.findall('counter'):
                        if counter.get('type') == 'LINE':
                            covered = int(counter.get('covered', 0))
                            missed = int(counter.get('missed', 0))
                            lines_covered = covered
                            lines_total = covered + missed
                            break
                    
                    if lines_total > 0:
                        coverage_pct = (lines_covered / lines_total) * 100
                        coverage_by_file[filename] = coverage_pct
            
            logger.info(f"Collected coverage for {len(coverage_by_file)} files")
            return coverage_by_file
            
        except Exception as e:
            logger.exception(f"Failed to collect JaCoCo coverage from {source}")
            return {}
    
    def collect_python_coverage(self, source: Path) -> Dict[str, float]:
        """
        Collect Python coverage.py results.
        
        Args:
            source: Path to coverage.json
            
        Returns:
            Dict mapping file paths to coverage percentages
        """
        logger.debug(f"Collecting Python coverage from {source}")
        
        try:
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            coverage_by_file = {}
            
            for filename, file_data in data.get('files', {}).items():
                summary = file_data.get('summary', {})
                covered = summary.get('covered_lines', 0)
                total = summary.get('num_statements', 0)
                
                if total > 0:
                    coverage_pct = (covered / total) * 100
                    coverage_by_file[filename] = coverage_pct
            
            logger.info(f"Collected coverage for {len(coverage_by_file)} files")
            return coverage_by_file
            
        except Exception as e:
            logger.exception(f"Failed to collect Python coverage from {source}")
            return {}


class UnifiedResultAggregator:
    """
    Main aggregator that collects and unifies all results.
    
    Features:
    - Normalizes results from all frameworks
    - Collects coverage data
    - Aggregates flaky test information
    - Persists aggregated results
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize aggregator.
        
        Args:
            storage_path: Path to store aggregated results
        """
        self.storage_path = storage_path or Path("test_results")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.normalizer = ResultNormalizer()
        self.flaky_collector = FlakyTestCollector()
        self.coverage_collector = CoverageCollector()
        
        self.logger = get_logger(__name__, category=LogCategory.EXECUTION)
    
    def aggregate_run(
        self,
        result_files: List[Path],
        coverage_files: Optional[List[Path]] = None,
        flaky_report: Optional[Path] = None,
        framework: Optional[FrameworkType] = None,
        run_id: Optional[str] = None,
    ) -> TestRunResult:
        """
        Aggregate results from a single test run.
        
        Args:
            result_files: Test result files to aggregate
            coverage_files: Coverage report files
            flaky_report: Flaky test detection report
            framework: Test framework type (auto-detected if None)
            run_id: Custom run ID (generated if None)
            
        Returns:
            Aggregated TestRunResult
        """
        self.logger.info(f"Aggregating results from {len(result_files)} files")
        
        # Generate run ID if not provided
        if run_id is None:
            run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Normalize test results
        normalized_runs = self.normalizer.normalize_batch(result_files, framework)
        
        if not normalized_runs:
            self.logger.error("No results could be normalized")
            return TestRunResult(
                run_id=run_id,
                start_time=datetime.now(),
            )
        
        # Merge all test results
        all_tests: Dict[str, TestResult] = {}
        earliest_start = datetime.now()
        latest_end = datetime.now()
        total_duration = 0.0
        
        for run in normalized_runs:
            if run.start_time < earliest_start:
                earliest_start = run.start_time
            if run.end_time and run.end_time > latest_end:
                latest_end = run.end_time
            total_duration += run.duration
            
            for test in run.tests:
                if test.test_id in all_tests:
                    # Merge duplicate test results (take latest)
                    existing = all_tests[test.test_id]
                    if test.end_time and existing.end_time:
                        if test.end_time > existing.end_time:
                            all_tests[test.test_id] = test
                else:
                    all_tests[test.test_id] = test
        
        tests = list(all_tests.values())
        
        # Collect flaky test information
        if flaky_report and flaky_report.exists():
            self.logger.info("Collecting flaky test information")
            flaky_tests = self.flaky_collector.collect(flaky_report)
            
            # Merge flaky information into test results
            flaky_map = {t.test_id: t for t in flaky_tests}
            for test in tests:
                if test.test_id in flaky_map:
                    flaky_info = flaky_map[test.test_id]
                    test.is_flaky = True
                    test.flaky_runs = flaky_info.flaky_runs
                    test.pass_rate = flaky_info.pass_rate
        
        # Collect coverage information
        coverage_by_file: Dict[str, float] = {}
        if coverage_files:
            self.logger.info(f"Collecting coverage from {len(coverage_files)} files")
            for coverage_file in coverage_files:
                if not coverage_file.exists():
                    continue
                
                # Detect coverage format and collect
                if 'jacoco' in coverage_file.name.lower() or coverage_file.suffix == '.xml':
                    coverage_by_file.update(
                        self.coverage_collector.collect_jacoco(coverage_file)
                    )
                elif coverage_file.suffix == '.json':
                    coverage_by_file.update(
                        self.coverage_collector.collect_python_coverage(coverage_file)
                    )
        
        # Calculate overall coverage
        overall_coverage = None
        if coverage_by_file:
            overall_coverage = sum(coverage_by_file.values()) / len(coverage_by_file)
            self.logger.info(f"Overall coverage: {overall_coverage:.2f}%")
        
        # Create aggregated result
        result = TestRunResult(
            run_id=run_id,
            start_time=earliest_start,
            end_time=latest_end,
            duration=total_duration,
            tests=tests,
            overall_coverage=overall_coverage,
            coverage_by_file=coverage_by_file,
            metadata=normalized_runs[0].metadata if normalized_runs else None,
        )
        
        # Persist result
        self._save_result(result)
        
        self.logger.success(
            f"Aggregated {len(tests)} tests, "
            f"{result.passed} passed, {result.failed} failed, "
            f"{result.flaky} flaky"
        )
        
        return result
    
    def aggregate_multiple_runs(
        self,
        run_ids: Optional[List[str]] = None,
        time_range: Optional[tuple] = None,
    ) -> AggregatedResults:
        """
        Aggregate results from multiple test runs.
        
        Args:
            run_ids: Specific run IDs to aggregate (all if None)
            time_range: (start_time, end_time) to filter runs
            
        Returns:
            AggregatedResults across all runs
        """
        # Load all runs
        runs = self._load_runs(run_ids, time_range)
        
        if not runs:
            self.logger.warning("No runs found for aggregation")
            return AggregatedResults()
        
        self.logger.info(f"Aggregating {len(runs)} runs")
        
        # Create aggregated results
        aggregated = AggregatedResults(runs=runs)
        
        # Analyze test stability across runs
        test_statuses: Dict[str, List[TestStatus]] = {}
        
        for run in runs:
            for test in run.tests:
                if test.test_id not in test_statuses:
                    test_statuses[test.test_id] = []
                test_statuses[test.test_id].append(test.status)
        
        # Classify tests
        for test_id, statuses in test_statuses.items():
            passed_count = statuses.count(TestStatus.PASSED)
            failed_count = statuses.count(TestStatus.FAILED)
            total_count = len(statuses)
            
            if passed_count == total_count:
                aggregated.stable_tests.add(test_id)
            elif failed_count == total_count:
                aggregated.failing_tests.add(test_id)
            elif passed_count > 0 and failed_count > 0:
                aggregated.flaky_tests.add(test_id)
        
        self.logger.success(
            f"Aggregated {aggregated.total_runs} runs, "
            f"{aggregated.unique_tests} unique tests, "
            f"{len(aggregated.flaky_tests)} flaky"
        )
        
        return aggregated
    
    def _save_result(self, result: TestRunResult) -> None:
        """Save result to storage."""
        result_file = self.storage_path / f"{result.run_id}.json"
        
        try:
            data = {
                'run_id': result.run_id,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'duration': result.duration,
                'total_tests': result.total_tests,
                'passed': result.passed,
                'failed': result.failed,
                'skipped': result.skipped,
                'errors': result.errors,
                'flaky': result.flaky,
                'overall_coverage': result.overall_coverage,
                'pass_rate': result.pass_rate,
                'tests': [
                    {
                        'test_id': t.test_id,
                        'test_name': t.test_name,
                        'status': t.status.value,
                        'duration': t.duration,
                        'is_flaky': t.is_flaky,
                        'coverage_percentage': t.coverage_percentage,
                    }
                    for t in result.tests
                ],
                'coverage_by_file': result.coverage_by_file,
                'metadata': {
                    'framework': result.metadata.framework.value if result.metadata else None,
                } if result.metadata else None,
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Saved result to {result_file}")
            
        except Exception as e:
            self.logger.exception(f"Failed to save result {result.run_id}")
    
    def _load_runs(
        self,
        run_ids: Optional[List[str]] = None,
        time_range: Optional[tuple] = None,
    ) -> List[TestRunResult]:
        """Load runs from storage."""
        runs = []
        
        # Get all result files
        result_files = list(self.storage_path.glob("*.json"))
        
        for result_file in result_files:
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Filter by run_ids if specified
                if run_ids and data['run_id'] not in run_ids:
                    continue
                
                # Filter by time_range if specified
                if time_range:
                    start_time = datetime.fromisoformat(data['start_time'])
                    if not (time_range[0] <= start_time <= time_range[1]):
                        continue
                
                # Reconstruct TestRunResult (simplified)
                from .models import TestResult
                
                tests = [
                    TestResult(
                        test_id=t['test_id'],
                        test_name=t['test_name'],
                        status=TestStatus(t['status']),
                        duration=t['duration'],
                        is_flaky=t.get('is_flaky', False),
                        coverage_percentage=t.get('coverage_percentage'),
                    )
                    for t in data.get('tests', [])
                ]
                
                run = TestRunResult(
                    run_id=data['run_id'],
                    start_time=datetime.fromisoformat(data['start_time']),
                    end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
                    duration=data['duration'],
                    tests=tests,
                    overall_coverage=data.get('overall_coverage'),
                )
                
                runs.append(run)
                
            except Exception as e:
                self.logger.error(f"Failed to load result from {result_file}: {e}")
                continue
        
        return runs
