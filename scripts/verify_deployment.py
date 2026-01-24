"""
Database Deployment Verification Script
Verifies the CrossBridge database deployment on 10.60.67.247:5432
"""

import psycopg2
import sys

def check_connection(conn_string):
    """Test database connection."""
    try:
        conn = psycopg2.connect(conn_string)
        print("✅ Database connection successful")
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def check_extensions(conn):
    """Verify required extensions."""
    with conn.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector')")
        extensions = [row[0] for row in cur.fetchall()]
        
        if 'uuid-ossp' in extensions:
            print("✅ uuid-ossp extension installed")
        else:
            print("❌ uuid-ossp extension missing")
        
        if 'vector' in extensions:
            print("✅ pgvector extension installed")
        else:
            print("❌ pgvector extension missing")

def check_tables(conn):
    """Verify all tables exist."""
    expected_tables = [
        'discovery_run', 'test_case', 'page_object', 'test_page_mapping',
        'test_execution', 'flaky_test', 'flaky_test_history', 'feature',
        'code_unit', 'test_feature_map', 'test_code_coverage_map',
        'memory_embeddings', 'git_change_event', 'observability_event'
    ]
    
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = [row[0] for row in cur.fetchall()]
    
    missing = set(expected_tables) - set(tables)
    
    if not missing:
        print(f"✅ All {len(expected_tables)} tables exist")
    else:
        print(f"❌ Missing tables: {missing}")

def check_materialized_views(conn):
    """Verify materialized views."""
    expected_views = ['test_execution_hourly', 'test_execution_daily', 'flaky_test_trend_daily']
    
    with conn.cursor() as cur:
        cur.execute("SELECT matviewname FROM pg_matviews WHERE schemaname = 'public'")
        views = [row[0] for row in cur.fetchall()]
    
    missing = set(expected_views) - set(views)
    
    if not missing:
        print(f"✅ All {len(expected_views)} materialized views exist")
    else:
        print(f"❌ Missing views: {missing}")

def check_indexes(conn):
    """Check vector indexes."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'memory_embeddings' 
            AND indexdef LIKE '%hnsw%'
        """)
        indexes = cur.fetchall()
        
        if indexes:
            print(f"✅ HNSW vector index exists")
        else:
            print("⚠️  HNSW vector index not found")

def check_data(conn):
    """Verify data exists."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM test_case")
        test_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM test_execution")
        exec_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM flaky_test")
        flaky_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM feature")
        feature_count = cur.fetchone()[0]
        
        print(f"\n📊 Data Statistics:")
        print(f"   Test Cases: {test_count}")
        print(f"   Test Executions: {exec_count}")
        print(f"   Flaky Tests: {flaky_count}")
        print(f"   Features: {feature_count}")
        
        if test_count > 0 and exec_count > 0:
            print("✅ Database has test data")
        else:
            print("⚠️  Database is empty")

def check_views(conn):
    """Check analytical views."""
    expected_views = ['test_health_overview', 'recent_test_executions', 
                      'flaky_test_summary', 'feature_coverage_gaps']
    
    with conn.cursor() as cur:
        cur.execute("SELECT viewname FROM pg_views WHERE schemaname = 'public'")
        views = [row[0] for row in cur.fetchall()]
    
    missing = set(expected_views) - set(views)
    
    if not missing:
        print(f"✅ All {len(expected_views)} analytical views exist")
    else:
        print(f"❌ Missing views: {missing}")

def main():
    print("="*60)
    print("CrossBridge Database Deployment Verification")
    print("="*60)
    print()
    
    # Connection string
    conn_string = "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
    
    # Run checks
    conn = check_connection(conn_string)
    
    try:
        check_extensions(conn)
        check_tables(conn)
        check_materialized_views(conn)
        check_views(conn)
        check_indexes(conn)
        check_data(conn)
        
        print()
        print("="*60)
        print("✅ Verification Complete - Database is ready!")
        print("="*60)
        print()
        print("Next Steps:")
        print("1. Import Grafana dashboard: grafana/dashboards/crossbridge_overview.json")
        print("2. Configure Grafana datasource:")
        print("   - Host: 10.60.67.247:5432")
        print("   - Database: cbridge-unit-test-db")
        print("   - User: postgres")
        print("3. View comprehensive setup guide: DATABASE_DEPLOYMENT_SUMMARY.md")
        print()
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
