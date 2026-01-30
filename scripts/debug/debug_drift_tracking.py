"""
Debug: Test IntelligenceEngine drift tracking
"""

import logging
from core.intelligence.intelligence_engine import IntelligenceEngine
from core.intelligence.deterministic_classifier import SignalData

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

print("=" * 80)
print("DEBUGGING DRIFT TRACKING")
print("=" * 80)
print()

# Create engine with drift tracking
print("1. Creating IntelligenceEngine...")
engine = IntelligenceEngine(enable_drift_tracking=True)
print(f"   Drift manager: {engine.drift_manager is not None}")
print(f"   Drift detector: {engine.drift_detector is not None}")
print()

# Classify a test
print("2. Classifying a test...")
signal = SignalData(
    test_name="test_debug",
    test_status='pass',
    retry_count=0,
    historical_failure_rate=0.1,
    total_runs=100
)

result = engine.classify(signal)
print(f"   Result: {result.label} (confidence: {result.deterministic_confidence:.2f})")
print()

# Check if data was stored
print("3. Checking if data was stored...")
if engine.drift_manager:
    measurements = engine.drift_manager.get_measurements(test_name="test_debug")
    print(f"   Measurements in DB: {len(measurements)}")
    
    if measurements:
        print("   ✅ Data was stored!")
    else:
        print("   ❌ Data was NOT stored!")
        
        # Check if drift_detector has the data
        if engine.drift_detector and "test_debug" in engine.drift_detector._history:
            print(f"   BUT drift_detector has {len(engine.drift_detector._history['test_debug'])} measurements")
        else:
            print("   AND drift_detector also has no data")
else:
    print("   No drift manager!")

print()
print("=" * 80)
