#!/usr/bin/env python3
"""
Debug Grafana data issues - test queries with different formats
"""

import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': '10.60.67.247',
    'port': 5432,
    'database': 'cbridge-unit-test-db',
    'user': 'postgres',
    'password': 'admin'
}

def test_query(cursor, title, query):
    """Test a query and show results"""
    print(f"\n{'='*60}")
    print(f"Testing: {title}")
    print(f"{'='*60}")
    print(f"Query:\n{query}\n")
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]
        
        print(f"Columns: {col_names}")
        print(f"Results: {results}")
        print(f"Row count: {len(results)}")
        
        if results:
            print("✅ Query returned data")
        else:
            print("⚠️  Query returned no data")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")

def main():
    print("🔍 Debugging Grafana Dashboard Queries")
    print(f"⏰ Current time: {datetime.now()}\n")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Test 1: Simple count
    test_query(cursor, "Simple count of all tests", 
        "SELECT COUNT(*) as value FROM crossbridge.tests")
    
    # Test 2: Count with time filter (24h)
    test_query(cursor, "Tests in last 24 hours",
        "SELECT COUNT(DISTINCT test_id) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours'")
    
    # Test 3: Check time range
    test_query(cursor, "Date range of test data",
        "SELECT MIN(created_at) as min_date, MAX(created_at) as max_date FROM crossbridge.tests")
    
    # Test 4: Time series format (what Grafana expects)
    test_query(cursor, "Time series format for Grafana",
        "SELECT created_at as time, COUNT(*) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY created_at ORDER BY created_at LIMIT 5")
    
    # Test 5: Framework breakdown for pie chart
    test_query(cursor, "Framework breakdown (pie chart format)",
        "SELECT framework as metric, COUNT(*) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours' GROUP BY framework ORDER BY value DESC")
    
    # Test 6: Time series with date_trunc
    test_query(cursor, "Time series with hourly aggregation",
        "SELECT DATE_TRUNC('hour', created_at) as time, framework, ROUND(AVG(duration_ms)::numeric, 2) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY time, framework ORDER BY time LIMIT 10")
    
    # Test 7: Check table format for stat panel
    test_query(cursor, "Stat panel format (single value)",
        "SELECT ROUND(AVG(duration_ms)::numeric, 2) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours'")
    
    # Test 8: Check timezone
    cursor.execute("SHOW timezone")
    tz = cursor.fetchone()[0]
    print(f"\n{'='*60}")
    print(f"Database timezone: {tz}")
    print(f"{'='*60}")
    
    # Test 9: Check actual data timestamps
    test_query(cursor, "Sample of recent test timestamps",
        "SELECT test_id, framework, created_at, NOW() - created_at as age FROM crossbridge.tests ORDER BY created_at DESC LIMIT 5")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("🔧 Troubleshooting Tips:")
    print("="*60)
    print("1. Check Grafana datasource connection to 10.60.67.247:5432")
    print("2. Verify datasource user has SELECT permissions on crossbridge schema")
    print("3. Check Grafana time range picker matches data range")
    print("4. Verify timezone settings in Grafana match database")
    print("5. Check Grafana query inspector for actual SQL being executed")
    print("6. Try using 'Table' format instead of 'Time series' for testing")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
