"""Test database connectivity for integration tests."""
import psycopg2
import sys

DB_CONFIG = {
    "host": "10.60.67.247",
    "port": 5432,
    "database": "crossbridge_test",
    "user": "postgres",
    "password": "admin",
}

try:
    print("Attempting to connect to PostgreSQL...")
    print(f"  Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['database']}")
    print(f"  User: {DB_CONFIG['user']}")
    print()
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("✅ Database connection successful!")
    
    # Get PostgreSQL version
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"✅ PostgreSQL version: {version}")
    
    # Check if tables exist
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('api_changes', 'alert_history', 'grafana_api_metrics')
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    
    print(f"\n✅ Found {len(tables)} integration test tables:")
    for table in tables:
        print(f"   - {table[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Ready to run integration tests!")
    sys.exit(0)
    
except psycopg2.OperationalError as e:
    print(f"❌ Database connection failed: {e}")
    print("\nPlease verify:")
    print("  1. PostgreSQL is running")
    print("  2. Host 10.60.67.247 is accessible")
    print("  3. Database 'crossbridge_test' exists")
    print("  4. Credentials are correct")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
