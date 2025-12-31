"""
Result Collection & Aggregation Demo

This demo showcases all features of the Result Collection system:
1. Framework normalization (pytest, JUnit, TestNG, Robot)
2. Unified result aggregation
3. Cross-run comparison
4. Historical trend analysis
"""

import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

from core.execution.results import (
    TestResult,
    TestRunResult,
    TestStatus,
    FrameworkType,
    ResultNormalizer,
    UnifiedResultAggregator,
    ResultComparer,
    TrendAnalyzer,
    ComparisonStrategy,
    TrendMetric
)
from core.logging import get_logger

# Setup
logger = get_logger("demo")
logger.info("🚀 Starting Result Collection Demo")


def demo_framework_normalization():
    """Demo 1: Framework Normalization"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 1: Framework Normalization")
    logger.info("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create sample pytest result
        pytest_result = {
            "tests": [
                {
                    "nodeid": "test_example.py::test_success",
                    "outcome": "passed",
                    "duration": 0.5
                },
                {
                    "nodeid": "test_example.py::test_failure",
                    "outcome": "failed",
                    "duration": 0.3
                }
            ],
            "summary": {"passed": 1, "failed": 1}
        }
        
        pytest_file = tmpdir / "pytest_result.json"
        pytest_file.write_text(json.dumps(pytest_result))
        
        # Create sample JUnit XML result
        junit_xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="MyTestSuite" tests="2" failures="1" time="0.8">
    <testcase name="testSuccess" classname="com.example.Test" time="0.5"/>
    <testcase name="testFailure" classname="com.example.Test" time="0.3">
        <failure message="Test failed"/>
    </testcase>
</testsuite>"""
        
        junit_file = tmpdir / "junit_result.xml"
        junit_file.write_text(junit_xml)
        
        # Normalize both
        normalizer = ResultNormalizer()
        
        logger.info("\n📄 Normalizing pytest results...")
        pytest_run = normalizer.normalize(pytest_file)
        logger.success(f"Normalized {len(pytest_run.tests)} pytest results")
        for result in pytest_run.tests:
            status_emoji = "✅" if result.status == TestStatus.PASSED else "❌"
            logger.info(f"  {status_emoji} {result.test_name}: {result.status.value}")
        
        logger.info("\n📄 Normalizing JUnit results...")
        junit_run = normalizer.normalize(junit_file)
        logger.success(f"Normalized {len(junit_run.tests)} JUnit results")
        for result in junit_run.tests:
            status_emoji = "✅" if result.status == TestStatus.PASSED else "❌"
            logger.info(f"  {status_emoji} {result.test_name}: {result.status.value}")


def demo_result_aggregation():
    """Demo 2: Unified Result Aggregation"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 2: Unified Result Aggregation")
    logger.info("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create sample pytest result files
        pytest_result1 = {
            "tests": [
                {
                    "nodeid": "test_example.py::test_login_success",
                    "outcome": "passed",
                    "duration": 1.5
                },
                {
                    "nodeid": "test_example.py::test_login_failure",
                    "outcome": "failed",
                    "duration": 0.8
                },
                {
                    "nodeid": "test_example.py::test_logout",
                    "outcome": "passed",
                    "duration": 0.3
                }
            ],
            "summary": {"passed": 2, "failed": 1}
        }
        
        result_file = tmpdir / "pytest_result.json"
        result_file.write_text(json.dumps(pytest_result1))
        
        aggregator = UnifiedResultAggregator(storage_path=tmpdir)
        
        logger.info("\n📊 Aggregating test run from file...")
        run_result = aggregator.aggregate_run(
            result_files=[result_file],
            run_id="demo_run_1"
        )
        
        logger.success(f"✅ Aggregated run: {run_result.run_id}")
        logger.info(f"  Total tests: {run_result.total_tests}")
        logger.info(f"  Passed: {run_result.passed} ({run_result.pass_rate:.1f}%)")
        logger.info(f"  Failed: {run_result.failed}")
        logger.info(f"  Duration: {run_result.duration:.2f}s")


def demo_cross_run_comparison():
    """Demo 3: Cross-Run Comparison"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 3: Cross-Run Comparison")
    logger.info("="*60)
    
    # Create baseline run
    baseline = TestRunResult(
        run_id="baseline",
        start_time=datetime.now() - timedelta(days=1),
        tests=[
            TestResult("test1", "test_success", status=TestStatus.PASSED, duration=1.0),
            TestResult("test2", "test_failure", status=TestStatus.FAILED, duration=0.5),
            TestResult("test3", "test_slow", status=TestStatus.PASSED, duration=5.0),
        ]
    )
    
    # Create current run with changes
    current = TestRunResult(
        run_id="current",
        start_time=datetime.now(),
        tests=[
            TestResult("test1", "test_success", status=TestStatus.PASSED, duration=1.0),
            TestResult("test2", "test_failure", status=TestStatus.PASSED, duration=0.5),  # Now passing!
            TestResult("test3", "test_slow", status=TestStatus.PASSED, duration=2.0),  # Much faster!
            TestResult("test4", "test_new", status=TestStatus.PASSED, duration=0.3),  # New test
        ]
    )
    
    logger.info("\n🔍 Comparing test runs...")
    comparer = ResultComparer(performance_threshold=0.3)  # 30% threshold
    comparison = comparer.compare(baseline, current)
    
    logger.info("\n📊 Comparison Results:")
    if comparison.new_tests:
        logger.success(f"  ➕ New tests: {len(comparison.new_tests)}")
        for test_id in comparison.new_tests:
            logger.info(f"     • {test_id}")
    
    if comparison.newly_passing:
        logger.success(f"  ✅ Newly passing: {len(comparison.newly_passing)}")
        for test_id in comparison.newly_passing:
            logger.info(f"     • {test_id}")
    
    if comparison.faster_tests:
        logger.success(f"  ⚡ Faster tests: {len(comparison.faster_tests)}")
        for test_id, old_dur, new_dur in comparison.faster_tests:
            change_pct = ((old_dur - new_dur) / old_dur * 100) if old_dur > 0 else 0
            logger.info(f"     • {test_id}: {change_pct:.1f}% faster")
    
    # Generate summary
    summary = comparer.generate_summary(comparison)
    logger.info("\n" + summary)


def demo_trend_analysis():
    """Demo 4: Historical Trend Analysis"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 4: Historical Trend Analysis")
    logger.info("="*60)
    
    # Create historical runs showing improvement over time
    runs = []
    base_date = datetime.now() - timedelta(days=10)
    
    for i in range(10):
        # Simulate improving pass rate
        num_tests = 100
        num_passed = 70 + i * 3  # Gradually improving
        num_failed = num_tests - num_passed
        
        tests = (
            [TestResult(f"test{j}", f"test{j}", status=TestStatus.PASSED, duration=0.5)
             for j in range(num_passed)] +
            [TestResult(f"test{j}", f"test{j}", status=TestStatus.FAILED, duration=0.5)
             for j in range(num_passed, num_tests)]
        )
        
        run = TestRunResult(
            run_id=f"run_{i}",
            start_time=base_date + timedelta(days=i),
            tests=tests
        )
        runs.append(run)
    
    logger.info(f"\n📈 Analyzing trends across {len(runs)} runs...")
    analyzer = TrendAnalyzer()
    
    # Analyze pass rate trend
    pass_rate_trend = analyzer.analyze_metric(runs, TrendMetric.PASS_RATE)
    logger.success(f"✅ Pass Rate Analysis:")
    if pass_rate_trend.data_points:
        current = pass_rate_trend.data_points[-1].value
        logger.info(f"  Current: {current:.1f}%")
        logger.info(f"  Average: {pass_rate_trend.average:.1f}%")
        logger.info(f"  Trend: {pass_rate_trend.trend_direction} (strength: {pass_rate_trend.trend_strength:.2f})")
        
        if len(pass_rate_trend.data_points) > 1:
            first = pass_rate_trend.data_points[0].value
            change_pct = ((current - first) / first * 100) if first > 0 else 0
            logger.info(f"  Change: {change_pct:+.1f}%")
    
    # Generate full report
    all_trends = analyzer.analyze_all_metrics(runs)
    report = analyzer.generate_report(all_trends)
    logger.info("\n" + "="*60)
    logger.info("FULL TREND REPORT")
    logger.info("="*60)
    print(report)


def demo_complete_workflow():
    """Demo 5: Complete End-to-End Workflow"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 5: Complete End-to-End Workflow")
    logger.info("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Step 1: Create test result files
        logger.info("\n📝 Step 1: Creating test result files...")
        
        pytest_result_v1 = {
            "tests": [
                {
                    "nodeid": f"test_example.py::test_{i}",
                    "outcome": "passed" if i % 3 != 0 else "failed",
                    "duration": 0.5
                }
                for i in range(20)
            ],
            "summary": {"passed": 14, "failed": 6}
        }
        
        result_file1 = tmpdir / "pytest_result_v1.json"
        result_file1.write_text(json.dumps(pytest_result_v1))
        
        # Step 2: Aggregate results
        logger.info("\n📊 Step 2: Aggregating first run...")
        aggregator = UnifiedResultAggregator(storage_path=tmpdir)
        run1 = aggregator.aggregate_run([result_file1], run_id="workflow_run1")
        logger.success(f"Aggregated: {run1.total_tests} tests, {run1.pass_rate:.1f}% pass rate")
        
        # Step 3: Create improved second run
        logger.info("\n🔍 Step 3: Creating improved second run...")
        pytest_result_v2 = {
            "tests": [
                {
                    "nodeid": f"test_example.py::test_{i}",
                    "outcome": "passed" if i % 4 != 0 else "failed",
                    "duration": 0.4  # Faster
                }
                for i in range(20)
            ],
            "summary": {"passed": 15, "failed": 5}
        }
        
        result_file2 = tmpdir / "pytest_result_v2.json"
        result_file2.write_text(json.dumps(pytest_result_v2))
        run2 = aggregator.aggregate_run([result_file2], run_id="workflow_run2")
        
        # Step 4: Compare runs
        comparer = ResultComparer()
        comparison = comparer.compare(run1, run2)
        logger.success(f"Comparison: {len(comparison.newly_passing)} newly passing, "
                      f"{len(comparison.faster_tests)} faster")
        
        # Step 5: Analyze trends
        logger.info("\n📈 Step 4: Analyzing trends...")
        runs = [run1, run2]
        analyzer = TrendAnalyzer(min_data_points=2)
        trends = analyzer.analyze_all_metrics(runs)
        
        for metric, trend in trends.items():
            if trend and trend.data_points:
                direction_emoji = "📈" if trend.trend_direction == "improving" else "📉" if trend.trend_direction == "degrading" else "➡️"
                logger.info(f"  {direction_emoji} {metric.value}: {trend.data_points[-1].value:.1f} ({trend.trend_direction})")
        
        logger.success("\n✅ Workflow complete!")


def main():
    """Run all demos"""
    try:
        demo_framework_normalization()
        demo_result_aggregation()
        demo_cross_run_comparison()
        demo_trend_analysis()
        demo_complete_workflow()
        
        logger.info("\n" + "="*60)
        logger.success("🎉 All demos completed successfully!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
