"""Create crossbridge_test database and schema for integration tests."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# Connect to postgres database to create our test database
ADMIN_CONFIG = {
    "host": "10.60.67.247",
    "port": 5432,
    "database": "postgres",  # Connect to default postgres database
    "user": "postgres",
    "password": "admin",
}

DB_NAME = "crossbridge_test"

try:
    print("Connecting to PostgreSQL server...")
    conn = psycopg2.connect(**ADMIN_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
    exists = cursor.fetchone()
    
    if exists:
        print(f"✅ Database '{DB_NAME}' already exists")
    else:
        print(f"Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"✅ Database '{DB_NAME}' created successfully")
    
    cursor.close()
    conn.close()
    
    # Now connect to the new database and create schema
    print(f"\nConnecting to '{DB_NAME}' to create schema...")
    TEST_CONFIG = {**ADMIN_CONFIG, "database": DB_NAME}
    conn = psycopg2.connect(**TEST_CONFIG)
    cursor = conn.cursor()
    
    # Create api_changes table
    print("Creating api_changes table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_changes (
            id SERIAL PRIMARY KEY,
            change_id VARCHAR(500) UNIQUE NOT NULL,
            change_type VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            entity_name VARCHAR(500),
            path VARCHAR(500),
            http_method VARCHAR(10),
            breaking BOOLEAN DEFAULT FALSE,
            risk_level VARCHAR(20),
            old_value TEXT,
            new_value TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB,
            recommended_tests TEXT[]
        )
    """)
    print("✅ api_changes table created")
    
    # Create alert_history table
    print("Creating alert_history table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id SERIAL PRIMARY KEY,
            alert_id VARCHAR(500) UNIQUE NOT NULL,
            title VARCHAR(500) NOT NULL,
            message TEXT,
            severity VARCHAR(20) NOT NULL,
            source VARCHAR(200),
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notifiers_sent INTEGER DEFAULT 0,
            details JSONB,
            tags TEXT[]
        )
    """)
    print("✅ alert_history table created")
    
    # Create grafana_api_metrics table
    print("Creating grafana_api_metrics table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grafana_api_metrics (
            id SERIAL PRIMARY KEY,
            metric_time TIMESTAMP NOT NULL,
            change_type VARCHAR(100),
            entity_type VARCHAR(100),
            severity VARCHAR(20),
            risk_level VARCHAR(20),
            breaking_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 1,
            metadata JSONB
        )
    """)
    print("✅ grafana_api_metrics table created")
    
    # Create index for better query performance
    print("Creating indexes...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_changes_detected_at 
        ON api_changes(detected_at DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_history_sent_at 
        ON alert_history(sent_at DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_grafana_metrics_time 
        ON grafana_api_metrics(metric_time DESC)
    """)
    print("✅ Indexes created")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Database setup complete!")
    print(f"✅ Ready to run integration tests!")
    sys.exit(0)
    
except psycopg2.OperationalError as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
