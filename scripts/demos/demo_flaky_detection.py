"""
Demo: Flaky Test Detection in Action

This demo shows how the Isolation Forest-based flaky detection works
with simulated test execution data.
"""

from datetime import datetime, timedelta
from core.flaky_detection.models import (
    TestExecutionRecord, TestStatus, TestFramework
)
from core.flaky_detection.feature_engineering import FeatureEngineer
from core.flaky_detection.detector import FlakyDetector, create_flaky_report


def create_flaky_test_data():
    """Create execution data for a flaky test."""
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    # Flaky test: alternates between pass and fail
    for i in range(40):
        status = TestStatus.PASSED if i % 3 == 0 else TestStatus.FAILED
        duration = 100 + (i % 3) * 50  # Variable duration
        
        executions.append(TestExecutionRecord(
            test_id="test_login",
            framework=TestFramework.PYTEST,
            status=status,
            duration_ms=duration,
            executed_at=base_time + timedelta(hours=i),
            test_name="test_login",
            retry_count=1 if status == TestStatus.PASSED else 0,
            error_signature="AssertionError: element not found" if status == TestStatus.FAILED else None,
            external_test_id="C12345",  # TestRail ID
            external_system="testrail"
        ))
    
    return executions


def create_stable_test_data():
    """Create execution data for a stable test."""
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    # Stable test: always passes with consistent duration
    for i in range(40):
        executions.append(TestExecutionRecord(
            test_id="test_homepage",
            framework=TestFramework.PYTEST,
            status=TestStatus.PASSED,
            duration_ms=50 + i % 5,  # Low variance
            executed_at=base_time + timedelta(hours=i),
            test_name="test_homepage"
        ))
    
    return executions


def create_timing_sensitive_test():
    """Create execution data for a timing-sensitive flaky test."""
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    # Timing-sensitive: fails when it runs too slow
    for i in range(40):
        duration = 100 + (i % 10) * 30  # High variance
        status = TestStatus.FAILED if duration > 200 else TestStatus.PASSED
        
        executions.append(TestExecutionRecord(
            test_id="test_async_operation",
            framework=TestFramework.PYTEST,
            status=status,
            duration_ms=duration,
            executed_at=base_time + timedelta(hours=i),
            test_name="test_async_operation",
            retry_count=2 if status == TestStatus.FAILED else 0,
            error_signature="TimeoutException: operation timed out" if status == TestStatus.FAILED else None,
            external_test_id="C12346",  # TestRail ID
            external_system="testrail"
        ))
    
    return executions


def create_environment_sensitive_test():
    """Create execution data for an environment-sensitive flaky test."""
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    # Environment-sensitive: different errors
    errors = [
        "ConnectionError: database unreachable",
        "NetworkError: timeout connecting to API",
        "AssertionError: data mismatch"
    ]
    
    for i in range(40):
        status = TestStatus.FAILED if i % 4 == 0 else TestStatus.PASSED
        
        executions.append(TestExecutionRecord(
            test_id="test_data_sync",
            framework=TestFramework.PYTEST,
            status=status,
            duration_ms=150 + i % 20,
            executed_at=base_time + timedelta(hours=i),
            test_name="test_data_sync",
            error_signature=errors[i % 3] if status == TestStatus.FAILED else None,
            external_test_id="Z-1234",  # Zephyr ID
            external_system="zephyr"
        ))
    
    return executions


def main():
    print("=" * 80)
    print("🔬 FLAKY TEST DETECTION DEMO")
    print("=" * 80)
    print()
    
    # Create test execution data
    print("📊 Generating sample test execution data...")
    test_data = {
        "test_login": create_flaky_test_data(),
        "test_homepage": create_stable_test_data(),
        "test_async_operation": create_timing_sensitive_test(),
        "test_data_sync": create_environment_sensitive_test()
    }
    
    # Add more stable tests to reach minimum training size
    for i in range(6):
        base_time = datetime.now() - timedelta(days=30)
        executions = []
        for j in range(40):
            executions.append(TestExecutionRecord(
                test_id=f"test_stable_{i+1}",
                framework=TestFramework.PYTEST,
                status=TestStatus.PASSED,
                duration_ms=100 + j % 10,
                executed_at=base_time + timedelta(hours=j),
                test_name=f"test_stable_{i+1}"
            ))
        test_data[f"test_stable_{i+1}"] = executions
    
    for test_id, executions in test_data.items():
        passes = sum(1 for e in executions if e.status == TestStatus.PASSED)
        fails = sum(1 for e in executions if e.status == TestStatus.FAILED)
        print(f"   {test_id}: {len(executions)} runs ({passes} pass, {fails} fail)")
    
    print()
    
    # Extract features
    print("🔧 Extracting features from execution history...")
    feature_engineer = FeatureEngineer()
    features = {}
    
    for test_id, executions in test_data.items():
        fv = feature_engineer.extract_features(executions)
        if fv:
            features[test_id] = fv
            print(f"   {test_id}:")
            print(f"      Failure rate: {fv.failure_rate:.2%}")
            print(f"      Switch rate: {fv.pass_fail_switch_rate:.2%}")
            print(f"      Duration CV: {fv.duration_cv:.3f}")
            print(f"      Avg retries: {fv.avg_retry_count:.1f}")
    
    print()
    
    # Train detector
    print("🤖 Training Isolation Forest model...")
    detector = FlakyDetector()
    detector.train(list(features.values()))
    print(f"   Model trained on {len(features)} tests")
    print(f"   Trees: {detector.config.n_estimators}")
    print(f"   Contamination: {detector.config.contamination}")
    print()
    
    # Detect flaky tests
    print("🎯 Running flaky detection...")
    framework_map = {test_id: TestFramework.PYTEST for test_id in features.keys()}
    name_map = {test_id: test_id for test_id in features.keys()}
    
    # Build external ID maps from execution records
    external_id_map = {}
    external_system_map = {}
    for test_id, executions in test_data.items():
        # Collect unique external IDs from execution records
        ext_ids = set()
        ext_systems = set()
        for exec in executions:
            if exec.external_test_id:
                ext_ids.add(exec.external_test_id)
                ext_systems.add(exec.external_system)
        
        if ext_ids:
            external_id_map[test_id] = list(ext_ids)
            external_system_map[test_id] = list(ext_systems)
    
    results = detector.detect_batch(
        features, 
        framework_map, 
        name_map,
        external_id_map,
        external_system_map
    )
    print(f"   Analyzed {len(results)} tests")
    print()
    
    # Generate report
    report = create_flaky_report(results, include_stable=True)
    
    # Display summary
    print("=" * 80)
    print("📋 DETECTION RESULTS")
    print("=" * 80)
    print()
    
    print("Summary Statistics:")
    print(f"   Total tests:      {report['summary']['total_tests']}")
    print(f"   Flaky detected:   {report['summary']['flaky_tests']} "
          f"({report['summary']['flaky_percentage']:.1f}%)")
    print(f"   Suspected flaky:  {report['summary']['suspected_flaky']}")
    print(f"   Stable tests:     {report['summary']['stable_tests']}")
    print()
    
    if report['severity_breakdown']:
        print("Severity Breakdown:")
        for severity, count in report['severity_breakdown'].items():
            if count > 0:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                print(f"   {emoji.get(severity, '⚪')} {severity.upper():8} {count} test(s)")
        print()
    
    # Show detailed results for each test
    print("=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    print()
    
    for test_id, result in results.items():
        status_emoji = "❌" if result.is_flaky else "✅"
        print(f"{status_emoji} {test_id}")
        print(f"   Classification: {result.classification.upper()}")
        print(f"   Flaky Score:    {result.flaky_score:.3f}")
        print(f"   Confidence:     {result.confidence:.2f}")
        
        # Show external test case IDs if available
        if result.external_test_ids:
            external_refs = [f"{sys}:{id}" for sys, id in zip(result.external_systems, result.external_test_ids)]
            print(f"   External IDs:   {', '.join(external_refs)}")
        
        if result.is_flaky:
            print(f"   Severity:       {result.severity.upper()}")
            print(f"   Failure Rate:   {result.features.failure_rate:.1%}")
            
            if result.primary_indicators:
                print(f"   Indicators:")
                for indicator in result.primary_indicators:
                    print(f"      • {indicator}")
        
        print()
    
    # Show feature comparison
    print("=" * 80)
    print("FEATURE COMPARISON")
    print("=" * 80)
    print()
    
    print(f"{'Test':<25} {'Fail%':<8} {'Switch%':<10} {'Dur.CV':<8} {'Retries':<8} {'Status':<10}")
    print("-" * 80)
    
    for test_id, fv in features.items():
        result = results[test_id]
        status = "🔴 FLAKY" if result.is_flaky else "✅ STABLE"
        
        print(f"{test_id:<25} "
              f"{fv.failure_rate*100:<7.1f}% "
              f"{fv.pass_fail_switch_rate*100:<9.1f}% "
              f"{fv.duration_cv:<7.3f} "
              f"{fv.avg_retry_count:<7.1f} "
              f"{status}")
    
    print()
    print("=" * 80)
    print("✅ DEMO COMPLETE!")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("   • Flaky tests show high switch rates (pass/fail alternation)")
    print("   • Timing-sensitive tests have high duration variance")
    print("   • Environment-sensitive tests show multiple error types")
    print("   • Stable tests have consistent patterns")
    print()
    print("Next Steps:")
    print("   • Integrate with your CI/CD pipeline")
    print("   • Store results in PostgreSQL database")
    print("   • View trends in Grafana dashboards")
    print("   • Use CLI commands: 'crossbridge flaky detect'")
    print()


if __name__ == "__main__":
    main()
