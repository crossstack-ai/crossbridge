"""
Integration test to populate PostgreSQL with sample data for Grafana dashboards.

This test generates realistic sample data for:
1. AI Intelligence Dashboard (ai_intelligence_dashboard.json)
2. Execution Intelligence Dashboard (execution_intelligence_dashboard.json)
3. Test Execution & Trend Analysis Dashboard (test_execution_trends_dashboard.json)

Database Tables Populated:
- test_runs: Test execution metadata with framework, status, duration
- failure_clusters: AI-analyzed failures with regression/flaky detection
- ai_metrics: Detailed AI performance metrics (confidence, cost, tokens)
- analysis_summary: CI/CD decision data

Run this test to populate the database:
    pytest tests/integration/test_populate_dashboard_data.py -v
"""

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import random
import uuid


# Database connection details
DB_CONFIG = {
    "host": "10.60.67.247",
    "port": 5432,
    "database": "cbridge-sidecar-stage1-unit-test",
    "user": "postgres",
    "password": "admin"
}

# Test data configuration
FRAMEWORKS = ["pytest", "selenium_pytest", "robot", "jest", "playwright", "cypress", "junit"]
TEST_STATUSES = ["passed", "failed", "skipped"]
FAILURE_DOMAINS = ["Product", "Infrastructure", "Test Code"]
AI_MODELS = ["gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"]
SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

# Sample test names
TEST_NAMES = [
    "test_login_successful",
    "test_user_registration", 
    "test_api_response_time",
    "test_database_connection",
    "test_payment_processing",
    "test_search_functionality",
    "test_file_upload",
    "test_dashboard_loads",
    "test_notification_system",
    "test_user_profile_update",
    "test_authentication_token",
    "test_password_reset",
    "test_data_validation",
    "test_pagination",
    "test_filter_functionality",
    "test_export_data",
    "test_user_permissions",
    "test_api_authentication",
    "test_cache_invalidation",
    "test_session_management"
]

# Failure patterns for realistic data
FAILURE_PATTERNS = [
    ("Connection timeout", "Infrastructure", False, True),  # (message, domain, is_regression, is_flaky)
    ("Element not found", "Test Code", False, True),
    ("Assertion failed", "Product", True, False),
    ("Database connection refused", "Infrastructure", False, True),
    ("API returned 500 error", "Infrastructure", False, False),
    ("Login credentials invalid", "Product", True, False),
    ("Memory leak detected", "Product", True, False),
    ("Network unreachable", "Infrastructure", False, True),
    ("Timeout waiting for element", "Test Code", False, True),
    ("Unexpected response format", "Product", False, False)
]


@pytest.fixture
def db_connection():
    """Create database connection and setup tables if needed."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    
    try:
        with conn.cursor() as cur:
            # Create tables if they don't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS test_runs (
                    id SERIAL PRIMARY KEY,
                    test_name VARCHAR(255) NOT NULL,
                    framework VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    duration_ms INTEGER,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    environment VARCHAR(50),
                    branch VARCHAR(100)
                );
                
                CREATE INDEX IF NOT EXISTS idx_test_runs_created_at ON test_runs(created_at);
                CREATE INDEX IF NOT EXISTS idx_test_runs_framework ON test_runs(framework);
                CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs(status);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS failure_clusters (
                    id SERIAL PRIMARY KEY,
                    test_run_id INTEGER REFERENCES test_runs(id),
                    cluster_id VARCHAR(100),
                    failure_message TEXT,
                    root_cause TEXT,
                    domain VARCHAR(50),
                    severity VARCHAR(20),
                    confidence_score FLOAT,
                    is_regression BOOLEAN DEFAULT FALSE,
                    is_flaky BOOLEAN DEFAULT FALSE,
                    is_fixed BOOLEAN DEFAULT FALSE,
                    ai_model VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_created_at ON failure_clusters(created_at);
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_domain ON failure_clusters(domain);
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_regression ON failure_clusters(is_regression);
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_flaky ON failure_clusters(is_flaky);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_metrics (
                    id SERIAL PRIMARY KEY,
                    cluster_id VARCHAR(100),
                    ai_model VARCHAR(50),
                    confidence_score FLOAT,
                    response_time_ms INTEGER,
                    tokens_used INTEGER,
                    cost_usd FLOAT,
                    cache_hit BOOLEAN DEFAULT FALSE,
                    error_occurred BOOLEAN DEFAULT FALSE,
                    framework VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_ai_metrics_created_at ON ai_metrics(created_at);
                CREATE INDEX IF NOT EXISTS idx_ai_metrics_model ON ai_metrics(ai_model);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analysis_summary (
                    id SERIAL PRIMARY KEY,
                    framework VARCHAR(50),
                    total_failures INTEGER,
                    should_fail_ci BOOLEAN,
                    confidence_score FLOAT,
                    infrastructure_count INTEGER,
                    product_count INTEGER,
                    test_code_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_analysis_summary_created_at ON analysis_summary(created_at);
            """)
            
        conn.commit()
        yield conn
        
    finally:
        conn.close()


def generate_test_runs(conn, num_days=30, runs_per_day=50):
    """Generate realistic test run data spanning multiple days."""
    test_run_ids = []
    
    with conn.cursor() as cur:
        print(f"    Generating {num_days} days x {runs_per_day} runs/day...")
        
        for day_offset in range(num_days):
            base_date = datetime.now() - timedelta(days=day_offset)
            day_run_ids = []
            
            for _ in range(runs_per_day):
                # Randomly distribute throughout the day
                random_hour = random.randint(0, 23)
                random_minute = random.randint(0, 59)
                run_time = base_date.replace(hour=random_hour, minute=random_minute)
                
                framework = random.choice(FRAMEWORKS)
                test_name = random.choice(TEST_NAMES)
                
                # Pass rate degrades slightly over time (simulating code decay)
                pass_probability = 0.85 - (day_offset * 0.005)
                status = random.choices(
                    TEST_STATUSES, 
                    weights=[pass_probability, 1-pass_probability-0.05, 0.05]
                )[0]
                
                # Duration varies by framework and status
                base_duration = {
                    "pytest": 1500,
                    "selenium_pytest": 8000,
                    "robot": 6000,
                    "jest": 800,
                    "playwright": 3000,
                    "cypress": 4000,
                    "junit": 2000
                }[framework]
                
                # Failed tests tend to take longer
                duration_multiplier = 1.5 if status == "failed" else 1.0
                duration_ms = int(base_duration * duration_multiplier * random.uniform(0.5, 2.0))
                
                error_message = None
                if status == "failed":
                    error_message = random.choice(FAILURE_PATTERNS)[0]
                
                environment = random.choice(["qa", "stage", "prod", "local"])
                branch = random.choice(["main", "develop", "feature/test", "release/1.0"])
                
                cur.execute("""
                    INSERT INTO test_runs 
                    (test_name, framework, status, duration_ms, error_message, created_at, environment, branch)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (test_name, framework, status, duration_ms, error_message, run_time, environment, branch))
                
                test_run_id = cur.fetchone()[0]
                if status == "failed":
                    day_run_ids.append((test_run_id, run_time, framework, error_message))
            
            # Commit after each day to avoid long transactions
            conn.commit()
            test_run_ids.extend(day_run_ids)
            print(f"    Day {day_offset + 1}/{num_days} complete - {len(day_run_ids)} failures")
    
    return test_run_ids


def generate_failure_clusters(conn, test_run_ids):
    """Generate failure cluster data with AI analysis, regressions, and flaky tests."""
    cluster_ids = []
    
    with conn.cursor() as cur:
        for test_run_id, run_time, framework, error_message in test_run_ids:
            # Generate cluster ID (multiple failures can share same cluster)
            cluster_id = str(uuid.uuid4())[:8]
            
            # Select failure pattern
            failure_msg, domain, is_regression, is_flaky = random.choice(FAILURE_PATTERNS)
            
            # Some failures are fixed
            is_fixed = random.random() < 0.3  # 30% fixed rate
            
            # AI model selection
            ai_model = random.choice(AI_MODELS)
            
            # Confidence varies by model and domain
            base_confidence = {
                "gpt-4": 0.92,
                "gpt-3.5-turbo": 0.78,
                "claude-3-opus": 0.90,
                "claude-3-sonnet": 0.85
            }[ai_model]
            
            confidence_score = base_confidence + random.uniform(-0.15, 0.08)
            confidence_score = max(0.5, min(1.0, confidence_score))
            
            severity = random.choices(
                SEVERITY_LEVELS,
                weights=[0.2, 0.4, 0.3, 0.1]
            )[0]
            
            root_cause = f"{failure_msg} - Root cause: {domain} issue"
            
            cur.execute("""
                INSERT INTO failure_clusters
                (test_run_id, cluster_id, failure_message, root_cause, domain, severity,
                 confidence_score, is_regression, is_flaky, is_fixed, ai_model, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (test_run_id, cluster_id, failure_msg, root_cause, domain, severity,
                  confidence_score, is_regression, is_flaky, is_fixed, ai_model, run_time))
            
            cluster_ids.append((cluster_id, run_time, framework, ai_model, confidence_score))
        
        conn.commit()
    
    return cluster_ids


def generate_ai_metrics(conn, cluster_ids):
    """Generate detailed AI performance metrics."""
    
    with conn.cursor() as cur:
        batch_size = 50
        for idx, (cluster_id, run_time, framework, ai_model, confidence_score) in enumerate(cluster_ids):
            # Response time varies by model
            base_response_time = {
                "gpt-4": 3500,
                "gpt-3.5-turbo": 1200,
                "claude-3-opus": 3200,
                "claude-3-sonnet": 1800
            }[ai_model]
            
            response_time_ms = int(base_response_time * random.uniform(0.7, 1.5))
            
            # Token usage varies by model
            base_tokens = {
                "gpt-4": 1500,
                "gpt-3.5-turbo": 1200,
                "claude-3-opus": 1800,
                "claude-3-sonnet": 1400
            }[ai_model]
            
            tokens_used = int(base_tokens * random.uniform(0.8, 1.3))
            
            # Cost calculation (per 1K tokens)
            cost_per_1k = {
                "gpt-4": 0.03,
                "gpt-3.5-turbo": 0.002,
                "claude-3-opus": 0.015,
                "claude-3-sonnet": 0.003
            }[ai_model]
            
            cost_usd = (tokens_used / 1000) * cost_per_1k
            
            # Cache hit probability increases over time
            cache_hit = random.random() < 0.35  # 35% cache hit rate
            
            # Error occurrence
            error_occurred = random.random() < 0.05  # 5% error rate
            
            cur.execute("""
                INSERT INTO ai_metrics
                (cluster_id, ai_model, confidence_score, response_time_ms, tokens_used,
                 cost_usd, cache_hit, error_occurred, framework, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (cluster_id, ai_model, confidence_score, response_time_ms, tokens_used,
                  cost_usd, cache_hit, error_occurred, framework, run_time))
            
            # Commit every batch_size records
            if (idx + 1) % batch_size == 0:
                conn.commit()
                print(f"    Progress: {idx + 1}/{len(cluster_ids)} AI metrics")
        
        conn.commit()
        print(f"    Completed: {len(cluster_ids)} AI metrics")


def generate_analysis_summaries(conn, num_days=30):
    """Generate CI/CD decision summary data."""
    
    with conn.cursor() as cur:
        for day_offset in range(num_days):
            base_date = datetime.now() - timedelta(days=day_offset)
            
            # Generate 3-5 summaries per day
            for _ in range(random.randint(3, 5)):
                random_hour = random.randint(0, 23)
                summary_time = base_date.replace(hour=random_hour, minute=random.randint(0, 59))
                
                framework = random.choice(FRAMEWORKS)
                total_failures = random.randint(0, 20)
                
                # Distribution across domains
                infrastructure_count = random.randint(0, total_failures)
                product_count = random.randint(0, total_failures - infrastructure_count)
                test_code_count = total_failures - infrastructure_count - product_count
                
                # Should fail CI if there are product regressions
                should_fail_ci = product_count > 2
                
                confidence_score = random.uniform(0.7, 0.95)
                
                cur.execute("""
                    INSERT INTO analysis_summary
                    (framework, total_failures, should_fail_ci, confidence_score,
                     infrastructure_count, product_count, test_code_count, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (framework, total_failures, should_fail_ci, confidence_score,
                      infrastructure_count, product_count, test_code_count, summary_time))
        
        conn.commit()


def verify_data(conn):
    """Verify that data was inserted correctly."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Check test_runs
        cur.execute("SELECT COUNT(*) as count FROM test_runs")
        test_runs_count = cur.fetchone()['count']
        print(f"\n[+] test_runs: {test_runs_count} records")
        
        # Check failure_clusters
        cur.execute("SELECT COUNT(*) as count FROM failure_clusters")
        clusters_count = cur.fetchone()['count']
        print(f"[+] failure_clusters: {clusters_count} records")
        
        # Check ai_metrics
        cur.execute("SELECT COUNT(*) as count FROM ai_metrics")
        metrics_count = cur.fetchone()['count']
        print(f"[+] ai_metrics: {metrics_count} records")
        
        # Check analysis_summary
        cur.execute("SELECT COUNT(*) as count FROM analysis_summary")
        summary_count = cur.fetchone()['count']
        print(f"[+] analysis_summary: {summary_count} records")
        
        # Sample queries for dashboard validation
        print("\n[STATS] Sample Dashboard Queries:")
        
        # Pass rate (Test Execution Dashboard)
        cur.execute("""
            SELECT 
                (COUNT(*) FILTER (WHERE status = 'passed') * 100.0 / NULLIF(COUNT(*), 0)) as pass_rate
            FROM test_runs 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        pass_rate = cur.fetchone()['pass_rate']
        print(f"  - Pass Rate (24h): {pass_rate:.2f}%")
        
        # Regression count (AI Intelligence Dashboard)
        cur.execute("""
            SELECT COUNT(*) as regression_count 
            FROM failure_clusters 
            WHERE is_regression = true AND created_at >= NOW() - INTERVAL '24 hours'
        """)
        regression_count = cur.fetchone()['regression_count']
        print(f"  - New Regressions (24h): {regression_count}")
        
        # Flaky test count (AI Intelligence Dashboard)
        cur.execute("""
            SELECT COUNT(*) as flaky_count 
            FROM failure_clusters 
            WHERE is_flaky = true AND created_at >= NOW() - INTERVAL '24 hours'
        """)
        flaky_count = cur.fetchone()['flaky_count']
        print(f"  - Flaky Tests (24h): {flaky_count}")
        
        # Average AI confidence (AI Intelligence Dashboard)
        cur.execute("""
            SELECT AVG(confidence_score) as avg_confidence 
            FROM ai_metrics 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        avg_confidence = cur.fetchone()['avg_confidence']
        print(f"  - Avg AI Confidence: {avg_confidence:.3f}")
        
        # Total AI cost (AI Intelligence Dashboard)
        cur.execute("""
            SELECT SUM(cost_usd) as total_cost 
            FROM ai_metrics 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        total_cost = cur.fetchone()['total_cost']
        print(f"  - Total AI Cost (24h): ${total_cost:.2f}")
        
        # Framework distribution (Test Execution Dashboard)
        cur.execute("""
            SELECT framework, COUNT(*) as count 
            FROM test_runs 
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY framework 
            ORDER BY count DESC 
            LIMIT 5
        """)
        print("\n  Top Frameworks (7 days):")
        for row in cur.fetchall():
            print(f"    - {row['framework']}: {row['count']} runs")


@pytest.mark.integration
def test_populate_dashboard_data(db_connection):
    """
    Main test to populate all dashboard data.
    
    This test:
    1. Generates 7 days of test execution data
    2. Creates AI analysis data with regressions and flaky tests
    3. Populates AI performance metrics
    4. Creates CI/CD decision summaries
    5. Verifies data integrity
    """
    print("\n[*] Starting dashboard data population...")
    
    # Generate test runs (7 days, 30 runs/day = 210 total)
    print("  [*] Generating test runs...")
    test_run_ids = generate_test_runs(db_connection, num_days=7, runs_per_day=30)
    print(f"  [+] Generated {len(test_run_ids)} failed test runs")
    
    # Generate failure clusters
    print("  [*] Generating failure clusters with AI analysis...")
    cluster_ids = generate_failure_clusters(db_connection, test_run_ids)
    print(f"  [+] Generated {len(cluster_ids)} failure clusters")
    
    # Generate AI metrics
    print("  [*] Generating AI performance metrics...")
    generate_ai_metrics(db_connection, cluster_ids)
    print(f"  [+] Generated AI metrics for {len(cluster_ids)} analyses")
    
    # Generate analysis summaries
    print("  [*] Generating CI/CD decision summaries...")
    generate_analysis_summaries(db_connection, num_days=7)
    print("  [+] Generated analysis summaries")
    
    # Verify data
    print("\n[*] Verifying data integrity...")
    verify_data(db_connection)
    
    print("\n[SUCCESS] Dashboard data population complete!")
    print("\n[INFO] You can now view the dashboards in Grafana:")
    print("  1. AI Intelligence Dashboard")
    print("  2. Execution Intelligence Dashboard")
    print("  3. Test Execution & Trend Analysis Dashboard")


if __name__ == "__main__":
    """Allow running directly without pytest for quick testing."""
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    
    try:
        # Create tables first (replicating the fixture logic)
        with conn.cursor() as cur:
            # Create tables if they don't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS test_runs (
                    id SERIAL PRIMARY KEY,
                    test_name VARCHAR(255) NOT NULL,
                    framework VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    duration_ms INTEGER,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    environment VARCHAR(50),
                    branch VARCHAR(100)
                );
                
                CREATE INDEX IF NOT EXISTS idx_test_runs_created_at ON test_runs(created_at);
                CREATE INDEX IF NOT EXISTS idx_test_runs_framework ON test_runs(framework);
                CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs(status);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS failure_clusters (
                    id SERIAL PRIMARY KEY,
                    test_run_id INTEGER REFERENCES test_runs(id),
                    cluster_id VARCHAR(100),
                    failure_message TEXT,
                    root_cause TEXT,
                    domain VARCHAR(50),
                    severity VARCHAR(20),
                    confidence_score FLOAT,
                    is_regression BOOLEAN DEFAULT FALSE,
                    is_flaky BOOLEAN DEFAULT FALSE,
                    is_fixed BOOLEAN DEFAULT FALSE,
                    ai_model VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_created_at ON failure_clusters(created_at);
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_domain ON failure_clusters(domain);
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_regression ON failure_clusters(is_regression);
                CREATE INDEX IF NOT EXISTS idx_failure_clusters_flaky ON failure_clusters(is_flaky);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_metrics (
                    id SERIAL PRIMARY KEY,
                    cluster_id VARCHAR(100),
                    ai_model VARCHAR(50),
                    confidence_score FLOAT,
                    response_time_ms INTEGER,
                    tokens_used INTEGER,
                    cost_usd FLOAT,
                    cache_hit BOOLEAN DEFAULT FALSE,
                    error_occurred BOOLEAN DEFAULT FALSE,
                    framework VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_ai_metrics_created_at ON ai_metrics(created_at);
                CREATE INDEX IF NOT EXISTS idx_ai_metrics_model ON ai_metrics(ai_model);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analysis_summary (
                    id SERIAL PRIMARY KEY,
                    framework VARCHAR(50),
                    total_failures INTEGER,
                    should_fail_ci BOOLEAN,
                    confidence_score FLOAT,
                    infrastructure_count INTEGER,
                    product_count INTEGER,
                    test_code_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_analysis_summary_created_at ON analysis_summary(created_at);
            """)
            
        conn.commit()
        print("Tables created/verified successfully\n")
        
        test_populate_dashboard_data(conn)
    finally:
        conn.close()
