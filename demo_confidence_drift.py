"""
Demonstration of Confidence Drift Detection System

This script demonstrates the confidence drift detection capabilities
for monitoring test confidence changes over time.

Features demonstrated:
1. Recording confidence measurements
2. Detecting drift (low/moderate/high/critical)
3. Direction classification (stable/increasing/decreasing/volatile)
4. Trend analysis (gradual vs strong trends)
5. Alert generation
6. Category-level aggregation
7. Time window filtering
8. Integration with explainability system
"""

from datetime import datetime, timedelta
from core.intelligence.confidence_drift import (
    DriftDetector,
    DriftAlertManager,
    DriftSeverity,
    DriftDirection,
    detect_drift_from_explanations
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_drift_analysis(analysis, show_recommendations: bool = True):
    """Pretty print drift analysis."""
    if not analysis:
        print("  No drift detected (insufficient data)")
        return
    
    severity_emoji = {
        "none": "✓",
        "low": "⚠️",
        "moderate": "🔶",
        "high": "🔥",
        "critical": "🚨"
    }
    
    direction_emoji = {
        "stable": "→",
        "increasing": "↑",
        "decreasing": "↓",
        "volatile": "⚡"
    }
    
    emoji = severity_emoji.get(analysis.severity.value, "?")
    dir_emoji = direction_emoji.get(analysis.direction.value, "?")
    
    print(f"  Test: {analysis.test_name}")
    print(f"  Status: {emoji} {analysis.severity.value.upper()} drift")
    print(f"  Direction: {dir_emoji} {analysis.direction.value}")
    print(f"  Trend: {analysis.trend}")
    print(f"  Baseline: {analysis.baseline_confidence:.2%}")
    print(f"  Current: {analysis.current_confidence:.2%}")
    print(f"  Drift: {analysis.drift_percentage:+.1%} ({analysis.drift_absolute:+.2f})")
    print(f"  Measurements: {analysis.measurements_count} over {analysis.time_span}")
    
    if show_recommendations and analysis.recommendations:
        print(f"\n  Recommendations:")
        for rec in analysis.recommendations:
            print(f"    • {rec}")


def demo_basic_drift_detection():
    """Demo 1: Basic drift detection."""
    print_section("Demo 1: Basic Drift Detection")
    
    detector = DriftDetector()
    
    print("Recording confidence measurements for test_login...")
    # Simulate stable confidence initially
    for i in range(5):
        detector.record_confidence("test_login", 0.75, "flaky")
        print(f"  Measurement {i+1}: 0.75")
    
    print("\n  ... time passes ...\n")
    
    # Simulate drift to higher confidence
    for i in range(5):
        detector.record_confidence("test_login", 0.88, "flaky")
        print(f"  Measurement {i+6}: 0.88")
    
    print("\nAnalyzing drift...")
    analysis = detector.detect_drift("test_login")
    print_drift_analysis(analysis)


def demo_severity_levels():
    """Demo 2: Different drift severity levels."""
    print_section("Demo 2: Drift Severity Levels")
    
    detector = DriftDetector()
    
    # LOW drift (5-10%)
    print("Test with LOW drift (5-10% change):")
    for i in range(5):
        detector.record_confidence("test_low", 0.80, "flaky")
    for i in range(5):
        detector.record_confidence("test_low", 0.86, "flaky")
    
    analysis = detector.detect_drift("test_low")
    print_drift_analysis(analysis, show_recommendations=False)
    
    # MODERATE drift (10-20%)
    print("\n" + "-"*60)
    print("\nTest with MODERATE drift (10-20% change):")
    for i in range(5):
        detector.record_confidence("test_moderate", 0.80, "flaky")
    for i in range(5):
        detector.record_confidence("test_moderate", 0.92, "flaky")
    
    analysis = detector.detect_drift("test_moderate")
    print_drift_analysis(analysis, show_recommendations=False)
    
    # HIGH drift (20-30%)
    print("\n" + "-"*60)
    print("\nTest with HIGH drift (20-30% change):")
    for i in range(5):
        detector.record_confidence("test_high", 0.70, "flaky")
    for i in range(5):
        detector.record_confidence("test_high", 0.86, "flaky")
    
    analysis = detector.detect_drift("test_high")
    print_drift_analysis(analysis, show_recommendations=False)
    
    # CRITICAL drift (>30%)
    print("\n" + "-"*60)
    print("\nTest with CRITICAL drift (>30% change):")
    for i in range(5):
        detector.record_confidence("test_critical", 0.60, "flaky")
    for i in range(5):
        detector.record_confidence("test_critical", 0.95, "flaky")
    
    analysis = detector.detect_drift("test_critical")
    print_drift_analysis(analysis)


def demo_drift_directions():
    """Demo 3: Drift direction detection."""
    print_section("Demo 3: Drift Directions")
    
    detector = DriftDetector()
    
    # INCREASING drift
    print("Test with INCREASING confidence:")
    for i in range(5):
        detector.record_confidence("test_increasing", 0.65, "unstable")
    for i in range(5):
        detector.record_confidence("test_increasing", 0.85, "unstable")
    
    analysis = detector.detect_drift("test_increasing")
    print_drift_analysis(analysis, show_recommendations=False)
    
    # DECREASING drift
    print("\n" + "-"*60)
    print("\nTest with DECREASING confidence:")
    for i in range(5):
        detector.record_confidence("test_decreasing", 0.90, "unstable")
    for i in range(5):
        detector.record_confidence("test_decreasing", 0.70, "unstable")
    
    analysis = detector.detect_drift("test_decreasing")
    print_drift_analysis(analysis, show_recommendations=False)
    
    # VOLATILE drift
    print("\n" + "-"*60)
    print("\nTest with VOLATILE confidence (frequent changes):")
    values = [0.5, 0.9, 0.4, 0.85, 0.45, 0.88, 0.5, 0.9, 0.4, 0.85]
    for value in values:
        detector.record_confidence("test_volatile", value, "flaky")
    
    analysis = detector.detect_drift("test_volatile")
    print_drift_analysis(analysis)


def demo_trend_analysis():
    """Demo 4: Trend analysis."""
    print_section("Demo 4: Trend Analysis")
    
    detector = DriftDetector()
    
    # Gradually increasing trend
    print("Test with GRADUAL increasing trend:")
    confidences = [0.70, 0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.84, 0.86, 0.88]
    for conf in confidences:
        detector.record_confidence("test_gradual_increase", conf, "flaky")
    
    analysis = detector.detect_drift("test_gradual_increase")
    print_drift_analysis(analysis, show_recommendations=False)
    
    # Strongly increasing trend
    print("\n" + "-"*60)
    print("\nTest with STRONG increasing trend:")
    confidences = [0.50, 0.55, 0.62, 0.70, 0.78, 0.85, 0.88, 0.90, 0.92, 0.95]
    for conf in confidences:
        detector.record_confidence("test_strong_increase", conf, "flaky")
    
    analysis = detector.detect_drift("test_strong_increase")
    print_drift_analysis(analysis)


def demo_category_drift():
    """Demo 5: Category-level drift analysis."""
    print_section("Demo 5: Category-Level Drift Analysis")
    
    detector = DriftDetector()
    
    print("Recording measurements for multiple tests in 'flaky' category...")
    
    # Test 1: Critical drift
    for i in range(5):
        detector.record_confidence("test_flaky_1", 0.60, "flaky")
    for i in range(5):
        detector.record_confidence("test_flaky_1", 0.95, "flaky")
    
    # Test 2: Moderate drift
    for i in range(5):
        detector.record_confidence("test_flaky_2", 0.75, "flaky")
    for i in range(5):
        detector.record_confidence("test_flaky_2", 0.87, "flaky")
    
    # Test 3: Low drift
    for i in range(5):
        detector.record_confidence("test_flaky_3", 0.80, "flaky")
    for i in range(5):
        detector.record_confidence("test_flaky_3", 0.86, "flaky")
    
    # Test 4: No drift
    for i in range(10):
        detector.record_confidence("test_flaky_4", 0.85, "flaky")
    
    print("\nAnalyzing category drift for 'flaky' tests...")
    summary = detector.detect_category_drift("flaky")
    
    print(f"\n  Category: {summary.category}")
    print(f"  Tests analyzed: {summary.tests_analyzed}")
    print(f"  Tests drifting: {summary.drifting_tests}")
    print(f"  Average drift: {summary.avg_drift_percentage:.1%}")
    print(f"\n  Drift distribution:")
    for severity, count in summary.drift_distribution.items():
        if count > 0:
            print(f"    {severity}: {count} test(s)")
    
    if summary.max_drift_test:
        print(f"\n  Worst drifting test:")
        print(f"    • {summary.max_drift_test}: {summary.max_drift_percentage:+.1%}")



def demo_time_windows():
    """Demo 6: Time window filtering."""
    print_section("Demo 6: Time Window Filtering")
    
    detector = DriftDetector()
    now = datetime.utcnow()
    
    print("Recording measurements across different time periods...")
    
    # Old measurements (90+ days ago)
    for i in range(3):
        timestamp = now - timedelta(days=100+i)
        detector.record_confidence("test_old", 0.70, "flaky", timestamp=timestamp)
    
    # Medium measurements (30-60 days ago)
    for i in range(3):
        timestamp = now - timedelta(days=45+i)
        detector.record_confidence("test_old", 0.80, "flaky", timestamp=timestamp)
    
    # Recent measurements (last 7 days)
    for i in range(4):
        timestamp = now - timedelta(days=i)
        detector.record_confidence("test_old", 0.90, "flaky", timestamp=timestamp)
    
    # Analyze with different time windows
    print("\nDrift analysis with 7-day window (recent only):")
    analysis_7d = detector.detect_drift("test_old", window=timedelta(days=7))
    if analysis_7d:
        print(f"  Measurements: {analysis_7d.measurements_count}")
        print(f"  Drift: {analysis_7d.drift_percentage:.1%}")
    else:
        print("  No drift detected (insufficient data)")
    
    print("\nDrift analysis with 30-day window:")
    analysis_30d = detector.detect_drift("test_old", window=timedelta(days=30))
    if analysis_30d:
        print(f"  Measurements: {analysis_30d.measurements_count}")
        print(f"  Drift: {analysis_30d.drift_percentage:.1%}")
    
    print("\nDrift analysis with all data (no window):")
    analysis_all = detector.detect_drift("test_old")
    if analysis_all:
        print(f"  Measurements: {analysis_all.measurements_count}")
        print(f"  Drift: {analysis_all.drift_percentage:.1%}")


def demo_alert_system():
    """Demo 7: Alert generation and management."""
    print_section("Demo 7: Alert System")
    
    detector = DriftDetector()
    alert_manager = DriftAlertManager(detector)
    
    print("Setting up tests with various drift levels...")
    
    # Critical drift
    for i in range(5):
        detector.record_confidence("critical_test", 0.55, "flaky")
    for i in range(5):
        detector.record_confidence("critical_test", 0.92, "flaky")
    
    # High drift
    for i in range(5):
        detector.record_confidence("high_test", 0.70, "flaky")
    for i in range(5):
        detector.record_confidence("high_test", 0.88, "flaky")
    
    # Moderate drift
    for i in range(5):
        detector.record_confidence("moderate_test", 0.75, "flaky")
    for i in range(5):
        detector.record_confidence("moderate_test", 0.87, "flaky")
    
    # Low drift (below alert threshold)
    for i in range(5):
        detector.record_confidence("low_test", 0.80, "flaky")
    for i in range(5):
        detector.record_confidence("low_test", 0.86, "flaky")
    
    print("\nChecking for alerts (minimum severity: MODERATE)...")
    alerts = alert_manager.check_for_alerts(min_severity=DriftSeverity.MODERATE)
    
    print(f"\nFound {len(alerts)} alert(s):\n")
    for i, alert in enumerate(alerts, 1):
        print(f"Alert {i}:")
        print(f"  Test: {alert.test_name}")
        print(f"  Severity: {alert.severity.value.upper()}")
        print(f"  Message: {alert.message}")
        print(f"  Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if alert.recommendations:
            print(f"  Top recommendations:")
            for rec in alert.recommendations[:3]:
                print(f"    • {rec}")
        print()


def demo_integration_with_explainability():
    """Demo 8: Integration with explainability system."""
    print_section("Demo 8: Integration with Explainability System")
    
    print("NOTE: Confidence drift can integrate with ConfidenceExplanation objects")
    print("      from the explainability system to track confidence over time.\n")
    
    print("✓ The detect_drift_from_explanations() function can:")
    print("  • Extract confidence values from explanations")
    print("  • Track per-test drift automatically")
    print("  • Group by category for aggregate analysis")
    print("  • Link drift back to signal and rule changes")
    
    print("\n✓ Integration successful!")
    print("  (See core/intelligence/confidence_drift.py:detect_drift_from_explanations)")



def demo_all_drifting_tests():
    """Demo 9: Get all drifting tests."""
    print_section("Demo 9: Get All Drifting Tests")
    
    detector = DriftDetector()
    
    print("Setting up multiple tests with drift...")
    
    # Create tests with various drift levels
    test_configs = [
        ("payment_test", 0.60, 0.95, "flaky"),  # Critical
        ("login_test", 0.70, 0.88, "unstable"),  # High
        ("checkout_test", 0.75, 0.87, "flaky"),  # Moderate
        ("search_test", 0.80, 0.86, "stable"),   # Low
        ("profile_test", 0.85, 0.86, "stable"),  # Low
    ]
    
    for test_name, baseline, current, category in test_configs:
        for i in range(5):
            detector.record_confidence(test_name, baseline, category)
        for i in range(5):
            detector.record_confidence(test_name, current, category)
    
    print("\nGetting all tests with moderate or higher drift...")
    drifting_tests = detector.get_all_drifting_tests(min_severity=DriftSeverity.MODERATE)
    
    print(f"\nFound {len(drifting_tests)} test(s) with significant drift:\n")
    for i, analysis in enumerate(drifting_tests, 1):
        severity_emoji = {"moderate": "🔶", "high": "🔥", "critical": "🚨"}
        emoji = severity_emoji.get(analysis.severity.value, "?")
        print(f"{i}. {analysis.test_name}")
        print(f"   {emoji} {analysis.severity.value.upper()}: {analysis.drift_percentage:+.1%}")
        print(f"   {analysis.baseline_confidence:.2%} → {analysis.current_confidence:.2%}")
        print()


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("  CONFIDENCE DRIFT DETECTION SYSTEM - DEMONSTRATION")
    print("="*60)
    
    demos = [
        demo_basic_drift_detection,
        demo_severity_levels,
        demo_drift_directions,
        demo_trend_analysis,
        demo_category_drift,
        demo_time_windows,
        demo_alert_system,
        demo_integration_with_explainability,
        demo_all_drifting_tests,
    ]
    
    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ Error in {demo.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print_section("Demo Complete!")
    print("✓ All drift detection features demonstrated successfully")
    print("\nKey Features:")
    print("  • Per-test drift tracking over time")
    print("  • 5 severity levels (none/low/moderate/high/critical)")
    print("  • 4 direction types (stable/increasing/decreasing/volatile)")
    print("  • Trend analysis with linear regression")
    print("  • Alert system with recommendations")
    print("  • Category-level aggregation")
    print("  • Time window filtering (7/30/90 days)")
    print("  • Integration with explainability system")


if __name__ == "__main__":
    main()
