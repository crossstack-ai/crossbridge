"""
Generate RECENT version-aware data (last 6 hours)
This will show up in your current dashboard time range
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import random
import uuid

psycopg2.extras.register_uuid()

DB_CONN = "postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation"

print("=" * 70)
print("Generating RECENT Version-Aware Data (Last 6 Hours)")
print("=" * 70)
print()

conn = psycopg2.connect(DB_CONN)
conn.set_session(autocommit=False)
cursor = conn.cursor()

# Clear old version-aware data first
print("🧹 Clearing old version-aware test data...")
cursor.execute("DELETE FROM test_execution_event WHERE application_version IS NOT NULL")
conn.commit()
print("✓ Cleared\n")

scenarios = [
    ("MyWebApp", "1.0.0", "production", 0.95, 25),
    ("MyWebApp", "2.0.0", "staging", 0.80, 30),
    ("MyWebApp", "2.1.0", "dev", 0.70, 35),
    ("PaymentAPI", "3.2.0", "production", 0.98, 20),
]

test_names = [
    "test_user_login", "test_checkout", "test_payment",
    "test_search", "test_filter", "test_cart", "test_api_auth"
]

total = 0
now = datetime.now()

for product, version, env, pass_rate, count in scenarios:
    print(f"📦 {product} v{version} ({env}) - {int(pass_rate*100)}% pass rate")
    
    for i in range(count):
        test_name = random.choice(test_names)
        test_id = f"pytest::tests/{test_name}.py::{test_name}"
        passed = random.random() < pass_rate
        status = "passed" if passed else "failed"
        duration = random.randint(100, 3000)
        
        # IMPORTANT: Generate timestamps within last 6 hours
        minutes_ago = random.randint(0, 360)  # 0-6 hours ago
        ts = now - timedelta(minutes=minutes_ago)
        
        cursor.execute("""
            INSERT INTO test_execution_event (
                id, event_type, framework, test_id, timestamp,
                status, duration_ms, error_message, metadata,
                application_version, product_name, environment, schema_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            uuid.uuid4(),
            'test_end',
            'pytest',
            test_id,
            ts,
            status,
            duration,
            'AssertionError: Test failed' if not passed else None,
            '{}',
            version,
            product,
            env,
            '1.0'
        ))
        
        total += 1
        
        if total % 10 == 0:
            conn.commit()
    
    conn.commit()
    print(f"   ✓ Generated {count} events (within last 6 hours)\n")

conn.commit()
cursor.close()
conn.close()

print("=" * 70)
print(f"✅ Success! Generated {total} RECENT test events")
print()
print("🎯 Now refresh your Grafana dashboard:")
print("   URL: http://10.55.12.99:3000/d/902/cb-dashboard-testing")
print()
print("   Time range is already set to 'Last 6 hours' - PERFECT!")
print("   Just click the Refresh button (circular arrow) ↻")
print()
print("📊 You should now see:")
print("   • MyWebApp: 90 events across 3 versions")
print("   • PaymentAPI: 20 events")
print("   • All data within last 6 hours")
print("=" * 70)
