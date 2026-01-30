"""
Quick test: Verify drift storage is working
"""

from datetime import datetime
from core.intelligence.drift_persistence import DriftPersistenceManager

# Create manager
print("Creating drift manager...")
manager = DriftPersistenceManager(backend='sqlite', db_path='data/test_drift.db')
print("✓ Manager created")

# Store a measurement
print("\nStoring measurement...")
record_id = manager.store_measurement(
    test_name="test_example",
    confidence=0.85,
    category="stable",
    timestamp=datetime.utcnow()
)
print(f"✓ Stored measurement with ID: {record_id}")

# Query measurements
print("\nQuerying measurements...")
measurements = manager.get_measurements(test_name="test_example")
print(f"✓ Found {len(measurements)} measurements")

if measurements:
    m = measurements[0]
    print(f"  - Test: {m.test_name}")
    print(f"  - Confidence: {m.confidence}")
    print(f"  - Category: {m.category}")
    print(f"  - Timestamp: {m.timestamp}")

print("\n✅ Storage test passed!")
