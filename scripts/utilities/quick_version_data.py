"""
Quick version-aware data generator for Grafana

Directly inserts test events with version tracking into the database.
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import random
import uuid

# Register UUID
psycopg2.extras.register_uuid()

DB_CONN = "postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation"

print("=" * 70)
print("Generating Version-Aware Test Data for Grafana")
print("=" * 70)
print()

try:
    conn = psycopg2.connect(DB_CONN)
    conn.set_session(autocommit=False)
    cursor = conn.cursor()
    
    # Ensure table exists
    print("🔧 Creating table if needed...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_execution_event (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type TEXT NOT NULL,
            framework TEXT NOT NULL,
            test_id TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            status TEXT,
            duration_ms INTEGER,
            error_message TEXT,
            stack_trace TEXT,
            metadata JSONB DEFAULT '{}',
            schema_version TEXT DEFAULT '1.0',
            application_version TEXT,
            product_name TEXT,
            environment TEXT,
            created_at TIMESTAMP DEFAULT now()
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_version ON test_execution_event(application_version)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_name ON test_execution_event(product_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_environment ON test_execution_event(environment)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON test_execution_event(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON test_execution_event(timestamp)")
    
    conn.commit()
    print("✓ Table ready\n")
    
    # Define scenarios
    scenarios = [
        ("MyWebApp", "1.0.0", "production", 0.95, 20),
        ("MyWebApp", "2.0.0", "staging", 0.80, 25),
        ("MyWebApp", "2.1.0", "dev", 0.70, 30),
        ("PaymentAPI", "3.2.0", "production", 0.98, 15),
    ]
    
    test_names = [
        "test_user_login", "test_checkout", "test_payment",
        "test_search", "test_filter", "test_cart"
    ]
    
    total = 0
    
    for product, version, env, pass_rate, count in scenarios:
        print(f"📦 {product} v{version} ({env}) - {int(pass_rate*100)}% pass rate")
        
        for i in range(count):
            test_name = random.choice(test_names)
            test_id = f"pytest::tests/{test_name}.py::{test_name}"
            passed = random.random() < pass_rate
            status = "passed" if passed else "failed"
            duration = random.randint(100, 3000)
            ts = datetime.now() - timedelta(minutes=random.randint(0, 10080))  # Within last week
            
            # Insert test_end event (most important for coverage)
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
        print(f"   ✓ Generated {count} test events\n")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("=" * 70)
    print(f"✅ Success! Generated {total} test events")
    print()
    print("🎯 View in Grafana:")
    print("   1. Open: http://10.55.12.99:3000/")
    print("   2. Import: grafana/dashboard_version_aware.json")
    print("   3. See version-based coverage charts!")
    print()
    print("📊 Verify in database:")
    print("   psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation")
    print("   SELECT application_version, product_name, environment, COUNT(*)")
    print("   FROM test_execution_event")
    print("   GROUP BY application_version, product_name, environment;")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
