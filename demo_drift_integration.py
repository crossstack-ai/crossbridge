"""
Demo: Drift Detection Integration with IntelligenceEngine

This script demonstrates how drift detection is automatically tracked
when using the IntelligenceEngine for test classification.
"""

import time
from datetime import datetime, timedelta
from core.intelligence.intelligence_engine import IntelligenceEngine
from core.intelligence.deterministic_classifier import SignalData
from core.intelligence.drift_persistence import DriftPersistenceManager


def demo_automatic_drift_tracking():
    """Demonstrate automatic drift tracking during classification."""
    print("=" * 80)
    print("DRIFT DETECTION INTEGRATION DEMO")
    print("=" * 80)
    print()
    
    # Initialize engine with drift tracking enabled
    print("1. Initializing IntelligenceEngine with drift tracking...")
    engine = IntelligenceEngine(enable_drift_tracking=True)
    
    # Verify drift tracking is enabled
    health = engine.get_health()
    print(f"   Drift tracking enabled: {health['drift_tracking']['enabled']}")
    print(f"   Drift manager available: {health['drift_tracking']['manager_available']}")
    print()
    
    # Simulate a test with changing confidence over time
    test_name = "test_payment_processing"
    print(f"2. Simulating test classifications for: {test_name}")
    print()
    
    # Day 1-5: Stable high confidence
    print("   Days 1-5: Stable performance (high confidence)")
    for day in range(5):
        signal = SignalData(
            test_name=test_name,
            test_status='pass',
            retry_count=0,
            historical_failure_rate=0.05,
            total_runs=100
        )
        result = engine.classify(signal)
        print(f"     Day {day+1}: {result.label} (confidence: {result.deterministic_confidence:.2f})")
        time.sleep(0.1)  # Small delay to space out timestamps
    
    print()
    
    # Day 6-10: Gradual decline (simulating drift)
    print("   Days 6-10: Performance degradation (declining confidence)")
    for day in range(5, 10):
        # Increase failure rate to simulate degradation
        failure_rate = 0.05 + (day - 4) * 0.05
        signal = SignalData(
            test_name=test_name,
            test_status='pass' if day < 8 else 'fail',
            retry_count=day - 5 if day >= 6 else 0,
            historical_failure_rate=failure_rate,
            total_runs=100 + day * 10
        )
        result = engine.classify(signal)
        print(f"     Day {day+1}: {result.label} (confidence: {result.deterministic_confidence:.2f}, "
              f"failure_rate: {failure_rate:.2f})")
        time.sleep(0.1)
    
    print()
    
    # Query drift data
    print("3. Checking drift detection results...")
    print()
    
    if engine.drift_manager and engine.drift_detector:
        # Get measurements from database
        measurements = engine.drift_manager.get_measurements(test_name=test_name)
        print(f"   Total measurements stored: {len(measurements)}")
        
        # Analyze drift using detector
        drift_analysis = engine.drift_detector.detect_drift(test_name)
        
        if drift_analysis:
            print(f"\n   Drift Analysis:")
            print(f"     Severity: {drift_analysis.severity.value}")
            print(f"     Direction: {drift_analysis.direction.value}")
            print(f"     Drift percentage: {drift_analysis.drift_percentage:+.1f}%")
            print(f"     Current confidence: {drift_analysis.current_confidence:.2f}")
            print(f"     Baseline confidence: {drift_analysis.baseline_confidence:.2f}")
            print(f"     Measurements: {drift_analysis.measurements_count}")
            print(f"     Trend: {drift_analysis.trend}")
        else:
            print("\n   Drift Analysis: Insufficient data")
        
        # Check for alerts from database
        alerts = engine.drift_manager.get_alerts(
            test_name=test_name
        )
        
        print(f"\n   Total Alerts: {len(alerts)}")
        for alert in alerts:
            severity = alert.get('severity', 'unknown')
            direction = alert.get('direction', 'unknown')
            message = alert.get('message', '')
            print(f"     - {severity.upper()}: {alert.get('test_name')}")
            print(f"       Direction: {direction}")
            print(f"       Message: {message}")
            print()
    
    print()
    print("=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


def demo_with_custom_backend():
    """Demonstrate using IntelligenceEngine with custom drift backend."""
    print("\n" + "=" * 80)
    print("CUSTOM BACKEND DEMO")
    print("=" * 80)
    print()
    
    # Create custom drift manager (PostgreSQL example)
    print("1. Creating drift manager with SQLite backend...")
    drift_manager = DriftPersistenceManager(
        backend='sqlite',
        db_path='data/demo_drift.db'
    )
    print("   ✓ Drift manager initialized")
    print()
    
    # Initialize engine with custom manager
    print("2. Initializing IntelligenceEngine with custom drift manager...")
    engine = IntelligenceEngine(
        drift_manager=drift_manager,
        enable_drift_tracking=True
    )
    print("   ✓ Engine initialized")
    print()
    
    # Run a classification
    print("3. Running test classification...")
    signal = SignalData(
        test_name="test_custom_backend_demo",
        test_status='pass',
        retry_count=0,
        historical_failure_rate=0.1,
        total_runs=50
    )
    
    result = engine.classify(signal)
    print(f"   Classification: {result.label}")
    print(f"   Confidence: {result.deterministic_confidence:.2f}")
    print()
    
    # Verify data was stored
    print("4. Verifying drift data was stored...")
    measurements = drift_manager.get_measurements(test_name="test_custom_backend_demo")
    print(f"   Measurements stored: {len(measurements)}")
    if measurements:
        print(f"   Latest measurement: confidence={measurements[0].confidence:.2f}, "
              f"category={measurements[0].category}")
    
    print()
    print("=" * 80)


def demo_drift_disabled():
    """Demonstrate engine with drift tracking disabled."""
    print("\n" + "=" * 80)
    print("DRIFT TRACKING DISABLED DEMO")
    print("=" * 80)
    print()
    
    print("1. Initializing IntelligenceEngine with drift tracking disabled...")
    engine = IntelligenceEngine(enable_drift_tracking=False)
    
    health = engine.get_health()
    print(f"   Drift tracking enabled: {health['drift_tracking']['enabled']}")
    print(f"   Drift manager available: {health['drift_tracking']['manager_available']}")
    print()
    
    print("2. Running classification (no drift tracking)...")
    signal = SignalData(
        test_name="test_no_drift",
        test_status='pass',
        retry_count=0,
        historical_failure_rate=0.0,
        total_runs=10
    )
    
    result = engine.classify(signal)
    print(f"   Classification: {result.label}")
    print(f"   Confidence: {result.deterministic_confidence:.2f}")
    print(f"   Drift tracking: No data stored")
    print()
    
    print("=" * 80)


if __name__ == '__main__':
    # Run all demos
    demo_automatic_drift_tracking()
    demo_with_custom_backend()
    demo_drift_disabled()
    
    print("\n✓ All demos completed successfully!")
    print("\nNext steps:")
    print("  - View drift data: python -m cli.main drift status")
    print("  - Analyze specific test: python -m cli.main drift analyze <test_name>")
    print("  - Check alerts: python -m cli.main drift alerts")
    print("  - View statistics: python -m cli.main drift stats")
