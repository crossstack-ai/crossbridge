#!/usr/bin/env python3
"""
Test Grafana dashboard queries with the populated data
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

def run_query(cursor, title, query):
    """Run a query and display results"""
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print(f"{'='*60}")
    cursor.execute(query)
    results = cursor.fetchall()
    
    if not results:
        print("  (No results)")
        return
    
    # Get column names
    col_names = [desc[0] for desc in cursor.description]
    
    # Print header
    header = " | ".join(f"{name:15}" for name in col_names)
    print(header)
    print("-" * len(header))
    
    # Print rows
    for row in results[:10]:  # Limit to 10 rows
        print(" | ".join(f"{str(val)[:15]:15}" for val in row))
    
    if len(results) > 10:
        print(f"  ... and {len(results) - 10} more rows")

def main():
    print("🔍 Testing Grafana Dashboard Queries")
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Query 1: Tests in last 24 hours
    run_query(cursor, "Tests (Last 24 Hours)", """
        SELECT COUNT(DISTINCT test_id) as value 
        FROM crossbridge.tests 
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """)
    
    # Query 2: Average test duration
    run_query(cursor, "Average Test Duration (Last 24h)", """
        SELECT ROUND(AVG(duration_ms)::numeric, 2) as "avg_duration_ms" 
        FROM crossbridge.tests 
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """)
    
    # Query 3: Success rate
    run_query(cursor, "Success Rate (Last 24h)", """
        SELECT 
            ROUND((COUNT(*) FILTER (WHERE status = 'passed')::numeric / NULLIF(COUNT(*), 0) * 100), 2) as "success_rate_percent"
        FROM crossbridge.tests 
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """)
    
    # Query 4: Tests by framework
    run_query(cursor, "Tests by Framework (Last 24h)", """
        SELECT framework as metric, COUNT(*) as value 
        FROM crossbridge.tests 
        WHERE created_at >= NOW() - INTERVAL '24 hours' 
        GROUP BY framework 
        ORDER BY value DESC
    """)
    
    # Query 5: Top 10 slowest tests
    run_query(cursor, "Top 10 Slowest Tests (Last 7 Days)", """
        SELECT 
            test_id as "Test Name", 
            framework as "Framework", 
            ROUND(AVG(duration_ms)::numeric, 2) as "Avg Duration (ms)", 
            COUNT(*) as "Executions" 
        FROM crossbridge.tests 
        WHERE created_at >= NOW() - INTERVAL '7 days' 
        GROUP BY test_id, framework 
        ORDER BY AVG(duration_ms) DESC 
        LIMIT 10
    """)
    
    # Query 6: Step performance
    run_query(cursor, "Step Performance Summary (Last 24h)", """
        SELECT 
            step_name as "Step Name", 
            COUNT(*) as "Executions", 
            ROUND(AVG(duration_ms)::numeric, 2) as "Avg Duration (ms)"
        FROM crossbridge.steps 
        WHERE created_at >= NOW() - INTERVAL '24 hours' 
        GROUP BY step_name 
        ORDER BY AVG(duration_ms) DESC 
        LIMIT 10
    """)
    
    # Query 7: HTTP call performance
    run_query(cursor, "HTTP Call Performance (Last 24h)", """
        SELECT 
            CONCAT(method, ' ', endpoint) as "Endpoint", 
            COUNT(*) as "Calls", 
            ROUND(AVG(duration_ms)::numeric, 2) as "Avg Duration (ms)"
        FROM crossbridge.http_calls 
        WHERE created_at >= NOW() - INTERVAL '24 hours' 
        GROUP BY method, endpoint 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """)
    
    # Query 8: Framework performance summary
    run_query(cursor, "Framework Performance (Last 7 Days)", """
        SELECT 
            framework as "Framework", 
            COUNT(*) as "Total Tests", 
            ROUND((COUNT(*) FILTER (WHERE status = 'passed')::numeric / NULLIF(COUNT(*), 0) * 100), 2) as "Success Rate (%)", 
            ROUND(AVG(duration_ms)::numeric, 2) as "Avg Duration (ms)"
        FROM crossbridge.tests 
        WHERE created_at >= NOW() - INTERVAL '7 days' 
        GROUP BY framework 
        ORDER BY COUNT(*) DESC
    """)
    
    # Query 9: Recent test executions
    run_query(cursor, "Recent Test Executions (Last Hour)", """
        SELECT 
            test_id as "Test Name", 
            framework as "Framework", 
            status as "Status", 
            ROUND(duration_ms::numeric, 2) as "Duration (ms)", 
            TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as "Time" 
        FROM crossbridge.tests 
        WHERE created_at >= NOW() - INTERVAL '1 hour' 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("✅ All queries executed successfully!")
    print("="*60)
    print("\n📈 Your Grafana dashboard should now display all these metrics!")
    print("🔗 Import the dashboard from: grafana/performance_profiling_dashboard.json")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
