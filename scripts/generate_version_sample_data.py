"""
Generate Version-Aware Sample Data

Creates sample test execution events with version tracking to demonstrate
coverage analysis across different product versions in Grafana.

Usage:
    python scripts/generate_version_sample_data.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import random
import uuid

# Register UUID adapter
psycopg2.extras.register_uuid()

# Database connection
DB_CONN = "postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation"

def get_connection():
    """Get database connection"""
    return psycopg2.connect(DB_CONN)

def generate_version_aware_data():
    """Generate test execution events with version tracking"""
    
    print("=" * 70)
    print("Generating Version-Aware Sample Data for CrossBridge")
    print("=" * 70)
    print()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Ensure table exists first
    print("🔧 Ensuring test_execution_event table exists...")
    try:
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
                metadata JSONB,
                schema_version TEXT DEFAULT '1.0',
                application_version TEXT,
                product_name TEXT,
                environment TEXT,
                created_at TIMESTAMP DEFAULT now()
            );
            
            CREATE INDEX IF NOT EXISTS idx_event_framework ON test_execution_event(framework);
            CREATE INDEX IF NOT EXISTS idx_event_test_id ON test_execution_event(test_id);
            CREATE INDEX IF NOT EXISTS idx_event_type ON test_execution_event(event_type);
            CREATE INDEX IF NOT EXISTS idx_event_timestamp ON test_execution_event(timestamp);
            CREATE INDEX IF NOT EXISTS idx_event_status ON test_execution_event(status);
            CREATE INDEX IF NOT EXISTS idx_app_version ON test_execution_event(application_version);
            CREATE INDEX IF NOT EXISTS idx_product_name ON test_execution_event(product_name);
            CREATE INDEX IF NOT EXISTS idx_environment ON test_execution_event(environment);
        """)
        conn.commit()
        print("✓ Table and indexes ready")
        print()
    except Exception as e:
        print(f"⚠️  Warning: {e}")
        print("   Continuing anyway...")
    
    # Product versions to simulate
    versions = [
        ("MyWebApp", "1.0.0", "production", 0.95, 50),   # Old stable version
        ("MyWebApp", "1.5.0", "production", 0.92, 60),   # Previous version
        ("MyWebApp", "2.0.0", "staging", 0.78, 80),      # New version in staging (lower coverage)
        ("MyWebApp", "2.1.0", "dev", 0.65, 100),         # Latest dev (even lower coverage)
        ("PaymentAPI", "3.2.0", "production", 0.98, 30), # Different product
        ("PaymentAPI", "3.3.0", "staging", 0.85, 40),
    ]
    
    test_names = [
        "test_user_login",
        "test_user_registration",
        "test_checkout_flow",
        "test_payment_processing",
        "test_order_confirmation",
        "test_search_functionality",
        "test_filter_products",
        "test_add_to_cart",
        "test_remove_from_cart",
        "test_update_profile",
        "test_reset_password",
        "test_api_authentication",
        "test_api_rate_limiting",
        "test_database_connection",
        "test_email_notification"
    ]
    
    frameworks = ["pytest", "robot", "playwright"]
    
    total_events = 0
    
    for product_name, version, environment, pass_rate, test_count in versions:
        print(f"\n📦 Generating data for: {product_name} v{version} ({environment})")
        print(f"   Pass Rate: {pass_rate*100}% | Tests: {test_count}")
        
        # Generate tests over last 7 days
        for day in range(7):
            tests_today = test_count // 7 + random.randint(-5, 5)
            
            for i in range(tests_today):
                test_name = random.choice(test_names)
                framework = random.choice(frameworks)
                timestamp = datetime.now() - timedelta(days=day, hours=random.randint(0, 23))
                
                # Determine test status based on pass rate
                passed = random.random() < pass_rate
                status = "passed" if passed else random.choice(["failed", "failed", "error"])
                
                duration_ms = random.randint(100, 5000) if passed else random.randint(200, 10000)
                
                # Test start event
                cursor.execute("""
                    INSERT INTO test_execution_event (
                        id, event_type, framework, test_id, timestamp,
                        status, duration_ms, error_message, stack_trace,
                        metadata, schema_version,
                        application_version, product_name, environment
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    uuid.uuid4(),
                    "test_start",
                    framework,
                    f"{framework}::tests/{test_name}.py::{test_name}",
                    timestamp - timedelta(milliseconds=duration_ms),
                    None,  # No status at start
                    None,
                    None,
                    None,
                    '{}',
                    '1.0',
                    version,
                    product_name,
                    environment
                ))
                
                # Test end event
                cursor.execute("""
                    INSERT INTO test_execution_event (
                        id, event_type, framework, test_id, timestamp,
                        status, duration_ms, error_message, stack_trace,
                        metadata, schema_version,
                        application_version, product_name, environment
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    uuid.uuid4(),
                    "test_end",
                    framework,
                    f"{framework}::tests/{test_name}.py::{test_name}",
                    timestamp,
                    status,
                    duration_ms,
                    f"AssertionError: Expected result not found" if status == "failed" else None,
                    "Traceback..." if status in ["failed", "error"] else None,
                    '{}',
                    '1.0',
                    version,
                    product_name,
                    environment
                ))
                
                total_events += 2
                
                # Commit every 50 events to avoid long transactions
                if total_events % 50 == 0:
                    conn.commit()
        
        print(f"   ✓ Generated {tests_today * 7 * 2} events")
        conn.commit()  # Commit after each version
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Successfully generated {total_events} events across {len(versions)} versions")
    print()
    print("🎯 Next Steps:")
    print("   1. Open Grafana: http://10.55.12.99:3000/")
    print("   2. Import dashboard: grafana/dashboard_version_aware.json")
    print("   3. Explore version-based coverage analytics!")
    print()
    print("📊 You should see:")
    print("   • Coverage trends by version")
    print("   • Pass rate comparison across versions")
    print("   • Version-to-version delta analysis")
    print("   • Multi-product tracking")
    print("=" * 70)

if __name__ == "__main__":
    try:
        generate_version_aware_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
