"""
Generate sample test data for API Change Intelligence Grafana Dashboard.

This script populates the crossbridge_test database with:
- Sample API change events
- Alert history records  
- Grafana metrics for testing

Usage:
    python populate_api_change_test_data.py
"""

import psycopg2
from datetime import datetime, timedelta
import random
import sys

# Database configuration
DB_CONFIG = {
    "host": "10.60.67.247",
    "port": 5432,
    "database": "crossbridge_test",
    "user": "postgres",
    "password": "admin",
}

# Sample data
CHANGE_TYPES = ["ADDED", "MODIFIED", "REMOVED"]
ENTITY_TYPES = ["ENDPOINT", "SCHEMA", "PARAMETER", "RESPONSE", "SECURITY", "HEADER"]
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITIES = ["info", "low", "medium", "high", "critical"]

SAMPLE_APIS = [
    "/api/v1/users",
    "/api/v1/products",
    "/api/v1/orders",
    "/api/v1/payments",
    "/api/v1/auth",
    "/api/v2/users",
    "/api/v2/customers",
    "/api/v2/inventory",
]

SAMPLE_ENTITIES = [
    "User.email",
    "Product.price",
    "Order.status",
    "Payment.method",
    "Auth.token",
    "Customer.address",
    "Inventory.quantity",
]


def generate_api_changes(cursor, count=50):
    """Generate sample API change events."""
    print(f"\nGenerating {count} API change events...")
    
    base_time = datetime.now()
    inserted = 0
    
    for i in range(count):
        # Generate timestamp (last 7 days)
        hours_ago = random.randint(0, 7 * 24)
        detected_at = base_time - timedelta(hours=hours_ago)
        
        # Generate change data
        change_type = random.choice(CHANGE_TYPES)
        entity_type = random.choice(ENTITY_TYPES)
        entity_name = random.choice(SAMPLE_ENTITIES)
        path = random.choice(SAMPLE_APIS)
        http_method = random.choice(HTTP_METHODS)
        risk_level = random.choice(RISK_LEVELS)
        
        # Breaking changes are more likely for REMOVED and CRITICAL
        breaking = (
            change_type == "REMOVED" or 
            risk_level == "CRITICAL" or 
            random.random() < 0.3
        )
        
        try:
            cursor.execute("""
                INSERT INTO api_changes 
                (change_id, change_type, entity_type, entity_name, path, http_method, 
                 breaking, risk_level, detected_at, old_value, new_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                f"sample_{i}_{int(detected_at.timestamp())}",
                change_type,
                entity_type,
                entity_name,
                path,
                http_method,
                breaking,
                risk_level,
                detected_at,
                f"old_value_{i}",
                f"new_value_{i}"
            ))
            inserted += 1
        except psycopg2.errors.UniqueViolation:
            # Change ID already exists, skip
            pass
    
    print(f"✅ Inserted {inserted} API change events")
    return inserted


def generate_alert_history(cursor, count=20):
    """Generate sample alert history records."""
    print(f"\nGenerating {count} alert history records...")
    
    base_time = datetime.now()
    inserted = 0
    
    for i in range(count):
        # Generate timestamp (last 7 days)
        hours_ago = random.randint(0, 7 * 24)
        sent_at = base_time - timedelta(hours=hours_ago)
        
        # Generate alert data
        severity = random.choice(SEVERITIES)
        notifiers_sent = random.randint(1, 3)  # Email, Slack, Confluence
        
        title = f"API Change Alert: {random.choice(CHANGE_TYPES)} in {random.choice(SAMPLE_APIS)}"
        message = f"Sample alert message {i}"
        source = "API Change Intelligence"
        
        try:
            cursor.execute("""
                INSERT INTO alert_history 
                (alert_id, title, message, severity, source, sent_at, notifiers_sent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                f"alert_{i}_{int(sent_at.timestamp())}",
                title,
                message,
                severity,
                source,
                sent_at,
                notifiers_sent
            ))
            inserted += 1
        except psycopg2.errors.UniqueViolation:
            # Alert ID already exists, skip
            pass
    
    print(f"✅ Inserted {inserted} alert history records")
    return inserted


def generate_grafana_metrics(cursor, count=100):
    """Generate sample Grafana metrics."""
    print(f"\nGenerating {count} Grafana metrics records...")
    
    base_time = datetime.now()
    inserted = 0
    
    for i in range(count):
        # Generate timestamp (last 7 days, hourly)
        hours_ago = random.randint(0, 7 * 24)
        metric_time = base_time - timedelta(hours=hours_ago)
        
        # Generate metrics data
        change_type = random.choice(CHANGE_TYPES)
        entity_type = random.choice(ENTITY_TYPES)
        severity = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        risk_level = random.choice(RISK_LEVELS)
        
        total_count = random.randint(1, 50)
        breaking_count = random.randint(0, total_count // 2)
        
        try:
            cursor.execute("""
                INSERT INTO grafana_api_metrics 
                (metric_time, change_type, entity_type, severity, risk_level, 
                 breaking_count, total_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                metric_time,
                change_type,
                entity_type,
                severity,
                risk_level,
                breaking_count,
                total_count
            ))
            inserted += 1
        except Exception as e:
            # Skip if error
            pass
    
    print(f"✅ Inserted {inserted} Grafana metrics records")
    return inserted


def main():
    """Main execution function."""
    print("=" * 60)
    print("API Change Intelligence - Test Data Generator")
    print("=" * 60)
    
    try:
        print("\n🔌 Connecting to PostgreSQL...")
        print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"   Database: {DB_CONFIG['database']}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ Database connection successful!")
        
        # Check current counts
        print("\n📊 Current Data Counts:")
        cursor.execute("SELECT COUNT(*) FROM api_changes")
        api_changes_count = cursor.fetchone()[0]
        print(f"   api_changes: {api_changes_count} rows")
        
        cursor.execute("SELECT COUNT(*) FROM alert_history")
        alerts_count = cursor.fetchone()[0]
        print(f"   alert_history: {alerts_count} rows")
        
        cursor.execute("SELECT COUNT(*) FROM grafana_api_metrics")
        metrics_count = cursor.fetchone()[0]
        print(f"   grafana_api_metrics: {metrics_count} rows")
        
        # Generate test data
        api_inserted = generate_api_changes(cursor, count=50)
        alert_inserted = generate_alert_history(cursor, count=20)
        metrics_inserted = generate_grafana_metrics(cursor, count=100)
        
        # Commit changes
        conn.commit()
        
        # Show final counts
        print("\n" + "=" * 60)
        print("📊 Final Data Counts:")
        cursor.execute("SELECT COUNT(*) FROM api_changes")
        print(f"   api_changes: {cursor.fetchone()[0]} rows (+{api_inserted})")
        
        cursor.execute("SELECT COUNT(*) FROM alert_history")
        print(f"   alert_history: {cursor.fetchone()[0]} rows (+{alert_inserted})")
        
        cursor.execute("SELECT COUNT(*) FROM grafana_api_metrics")
        print(f"   grafana_api_metrics: {cursor.fetchone()[0]} rows (+{metrics_inserted})")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Test data generation complete!")
        print("\n📌 Next Steps:")
        print("   1. Open Grafana: http://10.55.12.99:3000")
        print("   2. Import dashboard: grafana/dashboards/api_change_intelligence_v2.json")
        print("   3. Select time range: Last 7 days")
        print("   4. Verify all panels show data")
        print("=" * 60)
        
        sys.exit(0)
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database connection failed: {e}")
        print("\nPlease verify:")
        print("  1. PostgreSQL is running")
        print("  2. Host 10.60.67.247 is accessible")
        print("  3. Database 'crossbridge_test' exists")
        print("  4. Credentials are correct")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
