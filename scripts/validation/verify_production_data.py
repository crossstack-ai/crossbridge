"""
Verify Production Profiling Data in Database

Queries the database to show profiling data ready for Grafana visualization
"""

import psycopg2
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Create database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'crossbridge_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'admin')
    )


def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def query_recent_test_runs():
    """Show recent test runs"""
    print_section("Recent Test Runs (Last 24 Hours)")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            run_id,
            COUNT(*) as test_count,
            STRING_AGG(DISTINCT framework, ', ') as frameworks,
            MIN(created_at) as run_start,
            MAX(created_at) as run_end
        FROM crossbridge.tests
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY run_id
        ORDER BY run_start DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    print(f"\n{'Run ID':<38} {'Tests':<8} {'Frameworks':<30} {'Timestamp':<25}")
    print("-" * 80)
    
    for run_id, count, frameworks, start, end in results:
        print(f"{str(run_id):<38} {count:<8} {frameworks:<30} {start.strftime('%Y-%m-%d %H:%M:%S'):<25}")
    
    print(f"\nTotal runs in last 24 hours: {len(results)}")
    conn.close()


def query_test_execution_trends():
    """Show test execution trends (Grafana Panel 1)"""
    print_section("Test Execution Trends - Time Series (Grafana Panel)")
    
    conn = psycopg2.connect(
        host='10.60.67.247',
        port=5432,
        database='cbridge-unit-test-db',
        user='postgres',
        password='admin'
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            date_trunc('hour', created_at) AS time_bucket,
            COUNT(*) as test_count,
            AVG(duration_ms)::integer as avg_duration_ms,
            MAX(duration_ms) as max_duration_ms,
            MIN(duration_ms) as min_duration_ms
        FROM crossbridge.tests
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY time_bucket
        ORDER BY time_bucket DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    print(f"\n{'Time Bucket':<25} {'Tests':<10} {'Avg (ms)':<12} {'Max (ms)':<12} {'Min (ms)':<12}")
    print("-" * 80)
    
    for time_bucket, count, avg, max_dur, min_dur in results:
        print(f"{time_bucket.strftime('%Y-%m-%d %H:00'):<25} {count:<10} {avg:<12} {max_dur:<12} {min_dur:<12}")
    
    conn.close()


def query_framework_comparison():
    """Show framework performance comparison (Grafana Panel 2)"""
    print_section("Framework Performance Comparison (Grafana Panel)")
    
    conn = psycopg2.connect(
        host='10.60.67.247',
        port=5432,
        database='cbridge-unit-test-db',
        user='postgres',
        password='admin'
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            framework,
            COUNT(*) as test_count,
            AVG(duration_ms)::integer as avg_duration,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms)::integer as p95_duration,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms)::integer as p99_duration,
            MAX(duration_ms) as max_duration
        FROM crossbridge.tests
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY framework
        ORDER BY avg_duration
    """)
    
    results = cursor.fetchall()
    print(f"\n{'Framework':<20} {'Tests':<10} {'Avg (ms)':<12} {'P95 (ms)':<12} {'P99 (ms)':<12} {'Max (ms)':<12}")
    print("-" * 80)
    
    for framework, count, avg, p95, p99, max_dur in results:
        print(f"{framework:<20} {count:<10} {avg:<12} {p95:<12} {p99:<12} {max_dur:<12}")
    
    conn.close()


def query_slowest_tests():
    """Show slowest tests (Grafana Panel 3)"""
    print_section("Top 10 Slowest Tests (Grafana Panel)")
    
    conn = psycopg2.connect(
        host='10.60.67.247',
        port=5432,
        database='cbridge-unit-test-db',
        user='postgres',
        password='admin'
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            test_id,
            framework,
            AVG(duration_ms)::integer as avg_duration,
            COUNT(*) as execution_count,
            MAX(created_at) as last_run
        FROM crossbridge.tests
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY test_id, framework
        ORDER BY avg_duration DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    print(f"\n{'Test ID':<40} {'Framework':<15} {'Avg (ms)':<12} {'Runs':<8} {'Last Run':<20}")
    print("-" * 80)
    
    for test_id, framework, avg, count, last_run in results:
        test_short = test_id[:37] + '...' if len(test_id) > 40 else test_id
        print(f"{test_short:<40} {framework:<15} {avg:<12} {count:<8} {last_run.strftime('%Y-%m-%d %H:%M'):<20}")
    
    conn.close()


def query_test_success_rate():
    """Show test success rate (Grafana Panel 4)"""
    print_section("Test Success Rate (Grafana Panel)")
    
    conn = psycopg2.connect(
        host='10.60.67.247',
        port=5432,
        database='cbridge-unit-test-db',
        user='postgres',
        password='admin'
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            status,
            COUNT(*) as count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM crossbridge.tests
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY status
        ORDER BY count DESC
    """)
    
    results = cursor.fetchall()
    print(f"\n{'Status':<15} {'Count':<12} {'Percentage':<15}")
    print("-" * 80)
    
    total = sum(row[1] for row in results)
    for status, count, percentage in results:
        bar = '#' * int(percentage / 2)
        print(f"{status:<15} {count:<12} {percentage:>6.2f}% {bar}")
    
    print(f"\nTotal tests: {total}")
    conn.close()


def show_grafana_queries():
    """Show sample Grafana queries"""
    print_section("Sample Grafana Dashboard Queries")
    
    queries = [
        {
            'title': 'Test Execution Trends (Time Series)',
            'query': """SELECT
  date_trunc('hour', created_at) AS time,
  AVG(duration_ms) as avg_duration,
  MAX(duration_ms) as max_duration,
  MIN(duration_ms) as min_duration
FROM crossbridge.tests
WHERE $__timeFilter(created_at)
GROUP BY time
ORDER BY time"""
        },
        {
            'title': 'Framework Comparison (Bar Chart)',
            'query': """SELECT
  framework,
  AVG(duration_ms)::integer as avg_duration
FROM crossbridge.tests
WHERE $__timeFilter(created_at)
GROUP BY framework
ORDER BY avg_duration DESC"""
        },
        {
            'title': 'Test Success Rate (Gauge)',
            'query': """SELECT
  ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM crossbridge.tests
WHERE $__timeFilter(created_at)"""
        },
        {
            'title': 'Flaky Tests Detection (Table)',
            'query': """SELECT
  test_id,
  COUNT(*) as total_runs,
  SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
  ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) / COUNT(*), 2) as failure_rate
FROM crossbridge.tests
WHERE $__timeFilter(created_at)
GROUP BY test_id
HAVING SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) > 0
   AND SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) > 0
ORDER BY failure_rate DESC
LIMIT 10"""
        }
    ]
    
    for i, q in enumerate(queries, 1):
        print(f"\n{i}. {q['title']}")
        print("-" * 80)
        print(q['query'])
        print()


def main():
    print("\n" + "=" * 80)
    print("  PRODUCTION PROFILING DATA VERIFICATION")
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    print(f"  Database: PostgreSQL {db_host}:{db_port}")
    print("  Date: January 25, 2026")
    print("=" * 80)
    
    try:
        query_recent_test_runs()
        query_test_execution_trends()
        query_framework_comparison()
        query_slowest_tests()
        query_test_success_rate()
        show_grafana_queries()
        
        print("\n" + "=" * 80)
        print("  DATA VERIFICATION COMPLETE")
        print("  All profiling data is Grafana-ready!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] Query failed: {e}\n")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
