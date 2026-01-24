#!/usr/bin/env python3
"""
Populate sample test data for Grafana Performance Profiling Dashboard
Generates realistic test execution data across multiple frameworks and time periods
"""

import psycopg2
from datetime import datetime, timedelta
import random
import uuid

# Database configuration
DB_CONFIG = {
    'host': '10.60.67.247',
    'port': 5432,
    'database': 'cbridge-unit-test-db',
    'user': 'postgres',
    'password': 'admin'
}

# Frameworks to simulate
FRAMEWORKS = [
    'pytest',
    'robot',
    'playwright',
    'cypress',
    'testng',
    'restassured',
    'selenium_python',
    'nunit'
]

# Sample test names
TEST_NAMES = [
    'test_user_login',
    'test_user_registration',
    'test_product_search',
    'test_add_to_cart',
    'test_checkout_process',
    'test_payment_validation',
    'test_order_confirmation',
    'test_user_profile_update',
    'test_password_reset',
    'test_api_authentication',
    'test_api_create_resource',
    'test_api_update_resource',
    'test_api_delete_resource',
    'test_api_list_resources',
    'test_database_connection',
    'test_cache_operations',
    'test_file_upload',
    'test_data_export',
    'test_email_notification',
    'test_report_generation'
]

# Sample step names
STEP_NAMES = [
    'Open browser',
    'Navigate to login page',
    'Enter credentials',
    'Click login button',
    'Verify dashboard',
    'Search for product',
    'Select product',
    'Add to cart',
    'Proceed to checkout',
    'Enter shipping details',
    'Enter payment details',
    'Confirm order',
    'Verify order confirmation',
    'Close browser',
    'Connect to database',
    'Execute query',
    'Validate response',
    'Click element',
    'Wait for element',
    'Take screenshot'
]

# HTTP endpoints
HTTP_ENDPOINTS = [
    ('/api/v1/auth/login', 'POST'),
    ('/api/v1/auth/logout', 'POST'),
    ('/api/v1/users', 'GET'),
    ('/api/v1/users', 'POST'),
    ('/api/v1/users/{id}', 'GET'),
    ('/api/v1/users/{id}', 'PUT'),
    ('/api/v1/users/{id}', 'DELETE'),
    ('/api/v1/products', 'GET'),
    ('/api/v1/products/{id}', 'GET'),
    ('/api/v1/orders', 'POST'),
    ('/api/v1/orders/{id}', 'GET'),
    ('/api/v1/cart', 'GET'),
    ('/api/v1/cart/items', 'POST'),
    ('/api/v1/payment/process', 'POST'),
    ('/api/v1/reports/sales', 'GET')
]

def create_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG)

def generate_run_id():
    """Generate unique run ID"""
    return str(uuid.uuid4())

def generate_test_data(framework, test_name, recorded_at, run_id):
    """Generate realistic test data"""
    # Determine test status (80% pass, 15% fail, 5% skip)
    rand = random.random()
    if rand < 0.80:
        status = 'passed'
        duration_base = random.randint(500, 3000)
    elif rand < 0.95:
        status = 'failed'
        duration_base = random.randint(1000, 5000)
    else:
        status = 'skipped'
        duration_base = random.randint(50, 200)
    
    # Add some variance to duration
    duration = duration_base + random.randint(-200, 500)
    duration = max(10, duration)  # Ensure minimum duration
    
    test_id = f"{framework}_{test_name}_{recorded_at.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}"
    
    return {
        'test_id': test_id,
        'run_id': run_id,
        'framework': framework,
        'status': status,
        'duration_ms': duration,
        'created_at': recorded_at
    }

def generate_step_data(test_id, test_start_time, framework, run_id):
    """Generate step-level data for a test"""
    num_steps = random.randint(3, 8)
    steps = []
    current_time = test_start_time
    
    for i in range(num_steps):
        step_name = random.choice(STEP_NAMES)
        duration = random.randint(50, 800)
        event_type = 'step_end'
        
        steps.append({
            'run_id': run_id,
            'test_id': test_id,
            'step_name': step_name,
            'framework': framework,
            'duration_ms': duration,
            'event_type': event_type,
            'created_at': current_time
        })
        
        current_time += timedelta(milliseconds=duration)
    
    return steps

def generate_http_call_data(test_id, test_start_time, run_id):
    """Generate HTTP call data for API tests"""
    # Not all tests make HTTP calls
    if random.random() > 0.4:
        return []
    
    num_calls = random.randint(1, 5)
    calls = []
    current_time = test_start_time
    
    for i in range(num_calls):
        endpoint, method = random.choice(HTTP_ENDPOINTS)
        duration = random.randint(50, 500)
        status_code = random.choice([200, 200, 200, 201, 204, 400, 404, 500])
        
        calls.append({
            'run_id': run_id,
            'test_id': test_id,
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'duration_ms': duration,
            'created_at': current_time
        })
        
        current_time += timedelta(milliseconds=duration)
    
    return calls

def insert_run(conn, run_data):
    """Insert run record"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crossbridge.runs (run_id, framework, started_at, environment, created_at)
        VALUES (%(run_id)s, %(framework)s, %(started_at)s, %(environment)s, %(created_at)s)
        ON CONFLICT (run_id) DO NOTHING
    """, run_data)
    cursor.close()

def insert_test(conn, test_data):
    """Insert test record"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crossbridge.tests (test_id, run_id, framework, status, duration_ms, created_at)
        VALUES (%(test_id)s, %(run_id)s, %(framework)s, %(status)s, %(duration_ms)s, %(created_at)s)
    """, test_data)
    cursor.close()

def insert_step(conn, step_data):
    """Insert step record"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crossbridge.steps (run_id, test_id, step_name, framework, duration_ms, event_type, created_at)
        VALUES (%(run_id)s, %(test_id)s, %(step_name)s, %(framework)s, %(duration_ms)s, %(event_type)s, %(created_at)s)
    """, step_data)
    cursor.close()

def insert_http_call(conn, http_data):
    """Insert HTTP call record"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crossbridge.http_calls (run_id, test_id, method, endpoint, status_code, duration_ms, created_at)
        VALUES (%(run_id)s, %(test_id)s, %(method)s, %(endpoint)s, %(status_code)s, %(duration_ms)s, %(created_at)s)
    """, http_data)
    cursor.close()

def populate_sample_data():
    """Main function to populate sample data"""
    print("🚀 Starting sample data population for Performance Profiling Dashboard...")
    
    conn = create_connection()
    print("✅ Connected to database")
    
    # Generate data for different time periods
    now = datetime.now()
    time_periods = [
        # Last hour - high frequency
        (now - timedelta(hours=1), now, 10, "last hour"),
        # Last 24 hours - medium frequency
        (now - timedelta(hours=24), now - timedelta(hours=1), 50, "last 24 hours"),
        # Last 7 days - lower frequency
        (now - timedelta(days=7), now - timedelta(hours=24), 100, "last 7 days"),
        # Last 30 days - sparse
        (now - timedelta(days=30), now - timedelta(days=7), 150, "last 30 days")
    ]
    
    total_tests = 0
    total_steps = 0
    total_http_calls = 0
    total_runs = 0
    
    for start_time, end_time, num_tests, period_name in time_periods:
        print(f"\n📊 Generating data for {period_name}...")
        
        # Generate tests spread across the time period
        time_delta = (end_time - start_time).total_seconds()
        
        for i in range(num_tests):
            # Random time within the period
            offset_seconds = random.uniform(0, time_delta)
            recorded_at = start_time + timedelta(seconds=offset_seconds)
            
            # Pick random framework and test
            framework = random.choice(FRAMEWORKS)
            test_name = random.choice(TEST_NAMES)
            
            # Generate run ID (group some tests into runs)
            if i % 5 == 0 or i == 0:
                run_id = generate_run_id()
                run_started = recorded_at
                # Insert run record
                run_data = {
                    'run_id': run_id,
                    'framework': framework,
                    'environment': 'production',
                    'started_at': run_started,
                    'created_at': run_started
                }
                insert_run(conn, run_data)
                total_runs += 1
            
            # Generate test data
            test_data = generate_test_data(framework, test_name, recorded_at, run_id)
            insert_test(conn, test_data)
            total_tests += 1
            
            # Generate step data
            steps = generate_step_data(test_data['test_id'], recorded_at, framework, run_id)
            for step in steps:
                insert_step(conn, step)
                total_steps += 1
            
            # Generate HTTP call data
            http_calls = generate_http_call_data(test_data['test_id'], recorded_at, run_id)
            for call in http_calls:
                insert_http_call(conn, call)
                total_http_calls += 1
            
            if (i + 1) % 20 == 0:
                conn.commit()
                print(f"  ✓ Generated {i + 1}/{num_tests} tests for {period_name}")
        
        conn.commit()
        print(f"✅ Completed {period_name}: {num_tests} tests")
    
    conn.close()
    
    print("\n" + "="*60)
    print("🎉 Sample data population completed successfully!")
    print("="*60)
    print(f"📊 Summary:")
    print(f"   • Total Runs:      {total_runs}")
    print(f"   • Total Tests:     {total_tests}")
    print(f"   • Total Steps:     {total_steps}")
    print(f"   • Total HTTP Calls: {total_http_calls}")
    print("\n📈 Grafana Dashboard should now display data!")
    print(f"   • Time Range: {(now - timedelta(days=30)).strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   • Frameworks: {', '.join(FRAMEWORKS)}")
    print(f"   • Test Scenarios: {len(TEST_NAMES)}")

if __name__ == '__main__':
    try:
        populate_sample_data()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
