"""Simple database connection test for PostgreSQL."""
import psycopg2

DB_CONFIG = {
    "host": "10.60.67.247",
    "port": 5432,
    "database": "cbridge-sidecar-stage1-unit-test",
    "user": "postgres",
    "password": "admin"
}

print("Testing PostgreSQL connection...")
print(f"Host: {DB_CONFIG['host']}")
print(f"Database: {DB_CONFIG['database']}")

try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("[SUCCESS] Connected to PostgreSQL!")
    
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"[INFO] PostgreSQL version: {version[0]}")
        
        # Quick test insert
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_runs (
                id SERIAL PRIMARY KEY,
                test_name VARCHAR(255),
                framework VARCHAR(50),
                status VARCHAR(20),
                duration_ms INTEGER,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                environment VARCHAR(50),
                branch VARCHAR(100)
            )
        """)
        conn.commit()
        print("[SUCCESS] Table test_runs verified/created")
        
        # Count existing records
        cur.execute("SELECT COUNT(*) FROM test_runs")
        count = cur.fetchone()[0]
        print(f"[INFO] Existing test_runs: {count} records")
    
    conn.close()
    print("[SUCCESS] Database test complete")
    
except psycopg2.OperationalError as e:
    print(f"[ERROR] Connection failed: {e}")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
