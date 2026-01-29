"""
Production Profiling Demo

Demonstrates performance profiling working in production mode with:
- PostgreSQL database integration
- Real-time event collection
- Grafana-compatible data storage
- Multi-framework support
"""

import os
import sys
import time
from datetime import datetime
import psycopg2

# Set environment for profiling
os.environ['CROSSBRIDGE_PROFILING'] = 'true'
os.environ['CROSSBRIDGE_PROFILING_ENABLED'] = 'true'
os.environ['CROSSBRIDGE_DB_HOST'] = '10.60.67.247'
os.environ['CROSSBRIDGE_DB_PORT'] = '5432'
os.environ['CROSSBRIDGE_DB_NAME'] = 'cbridge-unit-test-db'
os.environ['CROSSBRIDGE_DB_USER'] = 'postgres'
os.environ['CROSSBRIDGE_DB_PASSWORD'] = 'admin'

from core.profiling.collector import MetricsCollector
from core.profiling.models import ProfileConfig, StorageBackendType
from core.profiling.storage import PostgresStorageBackend


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def verify_database_connection():
    """Verify PostgreSQL connection"""
    print_header("STEP 1: Verify Database Connection")
    
    try:
        conn = psycopg2.connect(
            host='10.60.67.247',
            port=5432,
            database='cbridge-unit-test-db',
            user='postgres',
            password='admin'
        )
        cursor = conn.cursor()
        
        # Check schema
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'crossbridge'
        """)
        table_count = cursor.fetchone()[0]
        
        print(f"[OK] Connected to PostgreSQL: 10.60.67.247:5432")
        print(f"[OK] Database: cbridge-unit-test-db")
        print(f"[OK] Schema: crossbridge ({table_count} tables)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False


def initialize_profiling():
    """Initialize profiling system"""
    print_header("STEP 2: Initialize Performance Profiling")
    
    config = ProfileConfig(
        enabled=True,
        backend=StorageBackendType.POSTGRES,
        postgres_host='10.60.67.247',
        postgres_port=5432,
        postgres_database='cbridge-unit-test-db',
        postgres_user='postgres',
        postgres_password='admin',
        postgres_schema='crossbridge'
    )
    
    collector = MetricsCollector.get_instance(config)
    success = collector.start()
    
    if success:
        print(f"[OK] Metrics collector started")
        print(f"[OK] Run ID: {collector.current_run_id}")
        print(f"[OK] Storage backend: PostgreSQL")
        print(f"[OK] Mode: Non-blocking, async")
        return collector
    else:
        print("[ERROR] Failed to start metrics collector")
        return None


def simulate_test_execution(collector):
    """Simulate test execution with profiling"""
    print_header("STEP 3: Execute Tests with Profiling")
    
    test_scenarios = [
        {
            'test_id': 'test_user_login_workflow',
            'framework': 'pytest',
            'duration': 1500,
            'status': 'passed',
            'steps': [
                ('Navigate to login page', 300),
                ('Enter credentials', 200),
                ('Click login button', 150),
                ('Verify dashboard loaded', 850)
            ]
        },
        {
            'test_id': 'test_checkout_process',
            'framework': 'selenium_python',
            'duration': 3200,
            'status': 'passed',
            'steps': [
                ('Add item to cart', 500),
                ('Proceed to checkout', 400),
                ('Fill shipping info', 800),
                ('Enter payment details', 700),
                ('Confirm order', 800)
            ]
        },
        {
            'test_id': 'test_api_user_creation',
            'framework': 'restassured',
            'duration': 850,
            'status': 'passed',
            'steps': [
                ('POST /api/users', 450),
                ('Verify response 201', 200),
                ('GET /api/users/{id}', 200)
            ]
        }
    ]
    
    for scenario in test_scenarios:
        test_id = scenario['test_id']
        framework = scenario['framework']
        duration = scenario['duration']
        status = scenario['status']
        steps = scenario.get('steps', [])
        
        print(f"\nExecuting: {test_id} [{framework}]")
        
        # Record test start
        collector.record_test_start(test_id, framework)
        
        # Record steps
        for step_name, step_duration in steps:
            collector.record_step_start(test_id, framework, step_name)
            time.sleep(step_duration / 5000)  # Simulate step execution (5x faster)
            collector.record_step_end(test_id, framework, step_name, step_duration)
            print(f"  - {step_name}: {step_duration}ms")
        
        # Record test end
        time.sleep(duration / 5000)  # Simulate remaining test time
        collector.record_test_end(test_id, framework, duration, status)
        
        print(f"  [OK] Completed in {duration}ms - {status}")
    
    # Flush events to database
    print(f"\n[OK] Flushing events to database...")
    collector.flush()
    time.sleep(2)  # Allow DB writes to complete
    
    stats = collector.get_stats()
    print(f"\n[OK] Profiling Statistics:")
    print(f"     Events collected: {stats['events_collected']}")
    print(f"     Events written: {stats['events_written']}")
    print(f"     Events dropped: {stats['events_dropped']}")
    
    return collector.current_run_id


def query_profiling_data(run_id):
    """Query and display profiling data from database"""
    print_header("STEP 4: Query Profiling Data (Grafana-Ready)")
    
    try:
        conn = psycopg2.connect(
            host='10.60.67.247',
            port=5432,
            database='cbridge-unit-test-db',
            user='postgres',
            password='admin'
        )
        cursor = conn.cursor()
        
        # Query 1: Test summary
        print("Query 1: Test Execution Summary")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                test_id,
                framework,
                duration_ms,
                status,
                created_at
            FROM crossbridge.tests
            WHERE run_id = %s
            ORDER BY created_at
        """, (run_id,))
        
        results = cursor.fetchall()
        print(f"\n{'Test ID':<35} {'Framework':<20} {'Duration':<12} {'Status':<10}")
        print("-" * 80)
        for test_id, framework, duration, status, created_at in results:
            print(f"{test_id:<35} {framework:<20} {duration:<12} {status:<10}")
        
        # Query 2: Step-level profiling
        print("\n\nQuery 2: Step-Level Profiling")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                test_id,
                step_name,
                duration_ms,
                framework
            FROM crossbridge.steps
            WHERE run_id = %s
            ORDER BY test_id, created_at
        """, (run_id,))
        
        results = cursor.fetchall()
        current_test = None
        for test_id, step_name, duration, framework in results:
            if test_id != current_test:
                print(f"\n{test_id} [{framework}]:")
                current_test = test_id
            print(f"  - {step_name}: {duration}ms")
        
        # Query 3: Framework comparison (Grafana-style)
        print("\n\nQuery 3: Framework Performance Comparison (Grafana Dashboard)")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                framework,
                COUNT(*) as test_count,
                AVG(duration_ms)::integer as avg_duration,
                MAX(duration_ms) as max_duration,
                MIN(duration_ms) as min_duration
            FROM crossbridge.tests
            WHERE run_id = %s
            GROUP BY framework
            ORDER BY avg_duration
        """, (run_id,))
        
        results = cursor.fetchall()
        print(f"\n{'Framework':<20} {'Tests':<10} {'Avg (ms)':<12} {'Max (ms)':<12} {'Min (ms)':<12}")
        print("-" * 80)
        for framework, count, avg, max_dur, min_dur in results:
            print(f"{framework:<20} {count:<10} {avg:<12} {max_dur:<12} {min_dur:<12}")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")


def show_grafana_instructions():
    """Show Grafana dashboard setup instructions"""
    print_header("STEP 5: Grafana Dashboard Setup")
    
    print("To visualize profiling data in Grafana:\n")
    print("1. Configure PostgreSQL Datasource:")
    print("   - Host: 10.60.67.247:5432")
    print("   - Database: cbridge-unit-test-db")
    print("   - User: postgres")
    print("   - Password: admin")
    print("   - SSL Mode: disable\n")
    
    print("2. Import Dashboard:")
    print("   - File: grafana/dashboards/crossbridge_overview.json")
    print("   - OR: grafana/flaky_dashboard_ready_template.json\n")
    
    print("3. View Real-Time Metrics:")
    print("   - Test Execution Trends")
    print("   - Framework Performance Comparison")
    print("   - Flaky Test Detection")
    print("   - Performance Regression Analysis")
    print("   - HTTP/API Call Duration")
    print("   - Test Success Rate\n")
    
    print("4. Sample Grafana Queries:")
    print("   ```sql")
    print("   -- Time-series test duration")
    print("   SELECT")
    print("       date_trunc('hour', created_at) AS time,")
    print("       AVG(duration_ms) as avg_duration")
    print("   FROM crossbridge.tests")
    print("   WHERE created_at >= NOW() - INTERVAL '24 hours'")
    print("   GROUP BY time")
    print("   ORDER BY time")
    print("   ```\n")


def main():
    """Main production demo"""
    print("\n" + "=" * 80)
    print("  CROSSBRIDGE PERFORMANCE PROFILING - PRODUCTION DEMO")
    print("  Database: PostgreSQL 10.60.67.247:5432")
    print("  Date: January 25, 2026")
    print("=" * 80)
    
    # Step 1: Verify database
    if not verify_database_connection():
        print("\n[ERROR] Cannot proceed without database connection")
        return 1
    
    # Step 2: Initialize profiling
    collector = initialize_profiling()
    if not collector:
        print("\n[ERROR] Cannot proceed without profiling system")
        return 1
    
    # Step 3: Simulate test execution
    run_id = simulate_test_execution(collector)
    
    # Step 4: Query profiling data
    query_profiling_data(run_id)
    
    # Step 5: Show Grafana instructions
    show_grafana_instructions()
    
    # Cleanup
    collector.shutdown()
    
    print("\n" + "=" * 80)
    print("  PRODUCTION DEMO COMPLETE")
    print("  Status: SUCCESS")
    print(f"  Run ID: {run_id}")
    print("  Data stored in: crossbridge.tests, crossbridge.steps")
    print("  Ready for Grafana visualization")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
