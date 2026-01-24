"""
Simple Test Data Generator for CrossBridge Database
Generates realistic test data for the new pgvector-only schema.
"""

import uuid
import json
import random
import logging
import sys
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_batch

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FRAMEWORKS = ["pytest", "junit", "testng", "robot", "cypress", "playwright"]
STATUSES = ["passed", "failed", "skipped", "error"]
ENVIRONMENTS = ["dev", "qa", "staging", "production"]


def generate_discovery_run(conn):
    """Generate a discovery run."""
    run_id = str(uuid.uuid4())
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO discovery_run 
            (id, started_at, completed_at, status, total_tests_discovered, new_tests_count, 
             modified_tests_count, framework, git_branch, git_commit, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            run_id,
            datetime.now() - timedelta(minutes=10),
            datetime.now(),
            'completed',
            100,
            10,
            5,
            random.choice(FRAMEWORKS),
            'main',
            f"abc123{random.randint(1000, 9999)}",
            json.dumps({"project": "CrossBridge_Test"})
        ))
    
    conn.commit()
    logger.info(f"Created discovery run: {run_id}")
    return run_id


def generate_test_cases(conn, discovery_run_id, count=100):
    """Generate test cases."""
    test_ids = []
    test_data = []
    
    for i in range(count):
        test_id = str(uuid.uuid4())
        test_ids.append(test_id)
        
        framework = random.choice(FRAMEWORKS)
        test_name = f"test_{framework}_{random.choice(['login', 'checkout', 'search', 'profile', 'payment'])}_{i}"
        
        test_data.append((
            test_id,
            discovery_run_id,
            test_name,
            f"tests/{test_name}.py",
            framework,
            f"{framework}_suite_{random.randint(1, 10)}",
            f"Test {test_name}",
            [random.choice(["smoke", "regression", "api", "ui"])] * random.randint(1, 2),
            random.choice(["high", "medium", "low"]),
            "active",
            datetime.now() - timedelta(days=random.randint(1, 30)),
            datetime.now(),
            json.dumps({"priority": random.choice(["high", "medium", "low"])})
        ))
    
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO test_case 
            (id, discovery_run_id, test_name, test_file_path, framework, suite_name, 
             description, tags, priority, status, first_seen_at, last_seen_at, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (test_name, framework) DO NOTHING
        """, test_data, page_size=100)
    
    conn.commit()
    logger.info(f"Created {len(test_data)} test cases")
    return test_ids


def generate_test_executions(conn, test_ids, days=7, executions_per_day=15):
    """Generate test execution history."""
    execution_data = []
    status_weights = [70, 15, 10, 5]  # passed, failed, skipped, error
    
    for day in range(days):
        exec_time = datetime.now() - timedelta(days=day)
        
        for _ in range(executions_per_day):
            test_id = random.choice(test_ids)
            status = random.choices(STATUSES, weights=status_weights)[0]
            
            execution_data.append((
                str(uuid.uuid4()),
                test_id,
                exec_time - timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59)),
                status,
                random.randint(100, 5000) if status == 'passed' else random.randint(100, 10000),
                f"Error in test" if status == 'failed' else None,
                None,
                f"build_{day}_{random.randint(100, 999)}",
                random.choice(ENVIRONMENTS),
                random.choice(["chrome", "firefox", "safari", None]),
                json.dumps({})
            ))
    
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO test_execution 
            (id, test_id, executed_at, status, duration_ms, error_message, 
             stack_trace, build_id, environment, browser, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, execution_data, page_size=100)
    
    conn.commit()
    logger.info(f"Created {len(execution_data)} test executions")


def generate_flaky_tests(conn, test_ids, flaky_count=20):
    """Generate flaky test records."""
    flaky_data = []
    flaky_test_ids = random.sample(test_ids, min(flaky_count, len(test_ids)))
    
    for test_id in flaky_test_ids:
        total_runs = random.randint(50, 200)
        pass_count = random.randint(30, total_runs - 10)
        fail_count = total_runs - pass_count
        flaky_score = fail_count / total_runs
        
        classification = "persistent" if flaky_score > 0.3 else "intermittent" if flaky_score > 0.15 else "rare"
        severity = "critical" if flaky_score > 0.5 else "high" if flaky_score > 0.3 else "medium"
        
        flaky_data.append((
            str(uuid.uuid4()),
            test_id,
            True,
            flaky_score,
            0.9,
            classification,
            severity,
            total_runs,
            pass_count,
            fail_count,
            0,
            datetime.now() - timedelta(days=random.randint(5, 30)),
            datetime.now(),
            json.dumps({})
        ))
    
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO flaky_test 
            (id, test_id, is_flaky, flaky_score, confidence_level, classification, 
             severity, total_runs, pass_count, fail_count, skip_count, 
             first_detected_at, last_updated_at, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (test_id) DO NOTHING
        """, flaky_data, page_size=100)
    
    conn.commit()
    logger.info(f"Created {len(flaky_data)} flaky tests")
    return flaky_test_ids


def generate_flaky_history(conn, flaky_test_ids, days=30):
    """Generate flaky test history."""
    history_data = []
    
    for test_id in flaky_test_ids:
        for day in range(days):
            recorded_at = datetime.now() - timedelta(days=day)
            total_runs = random.randint(5, 20)
            pass_count = random.randint(3, total_runs)
            fail_count = total_runs - pass_count
            flaky_score = fail_count / total_runs if total_runs > 0 else 0
            
            classification = "persistent" if flaky_score > 0.3 else "intermittent" if flaky_score > 0.15 else "rare"
            
            history_data.append((
                str(uuid.uuid4()),
                test_id,
                recorded_at,
                flaky_score,
                pass_count,
                fail_count,
                0,
                classification,
                0.9,
                json.dumps({})
            ))
    
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO flaky_test_history 
            (id, test_id, recorded_at, flaky_score, pass_count, fail_count, 
             skip_count, classification, confidence_level, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, history_data, page_size=100)
    
    conn.commit()
    logger.info(f"Created {len(history_data)} flaky history records")


def generate_features(conn, count=50):
    """Generate features."""
    feature_ids = []
    feature_data = []
    
    feature_types = ["api", "service", "bdd", "module", "component"]
    
    for i in range(count):
        feature_id = str(uuid.uuid4())
        feature_ids.append(feature_id)
        
        feature_data.append((
            feature_id,
            f"Feature_{random.choice(['Authentication', 'Payment', 'Search', 'Profile', 'Cart'])}_{i}",
            random.choice(feature_types),
            f"Description for feature {i}",
            random.choice(["high", "medium", "low"]),
            "active",
            [random.choice(["backend", "frontend", "api", "ui"])] * random.randint(1, 2),
            json.dumps({})
        ))
    
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO feature 
            (id, feature_name, feature_type, description, priority, status, tags, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (feature_name) DO NOTHING
        """, feature_data, page_size=100)
    
    conn.commit()
    logger.info(f"Created {len(feature_data)} features")
    return feature_ids


def generate_test_feature_mappings(conn, test_ids, feature_ids):
    """Map tests to features."""
    mapping_data = []
    
    for test_id in test_ids:
        # Map each test to 1-3 random features
        selected_features = random.sample(feature_ids, min(random.randint(1, 3), len(feature_ids)))
        
        for feature_id in selected_features:
            mapping_data.append((
                str(uuid.uuid4()),
                test_id,
                feature_id,
                random.choice(["unit", "integration", "e2e"]),
                1.0,
                json.dumps({})
            ))
    
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO test_feature_map 
            (id, test_id, feature_id, coverage_type, confidence, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (test_id, feature_id) DO NOTHING
        """, mapping_data, page_size=100)
    
    conn.commit()
    logger.info(f"Created {len(mapping_data)} test-feature mappings")


def generate_observability_events(conn, days=7, events_per_day=50):
    """Generate observability events."""
    event_data = []
    event_types = ["test_run", "system_alert", "performance_metric", "error_detected"]
    severities = ["info", "warning", "error", "critical"]
    
    for day in range(days):
        event_time = datetime.now() - timedelta(days=day)
        
        for _ in range(events_per_day):
            event_data.append((
                str(uuid.uuid4()),
                event_time - timedelta(hours=random.randint(0, 23)),
                random.choice(event_types),
                random.choice(severities),
                "crossbridge",
                f"Event message {random.randint(1000, 9999)}",
                json.dumps({"detail": "event_detail"})
            ))
    
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO observability_event 
            (id, event_time, event_type, severity, source, message, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, event_data, page_size=100)
    
    conn.commit()
    logger.info(f"Created {len(event_data)} observability events")


def refresh_materialized_views(conn):
    """Refresh all materialized views."""
    try:
        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW test_execution_hourly")
            cur.execute("REFRESH MATERIALIZED VIEW test_execution_daily")
            cur.execute("REFRESH MATERIALIZED VIEW flaky_test_trend_daily")
        conn.commit()
        logger.info("Refreshed all materialized views")
    except Exception as e:
        logger.warning(f"Could not refresh materialized views: {e}")


def main():
    # Parse args
    conn_string = "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--connection' and len(sys.argv) > 2:
            conn_string = sys.argv[2]
        elif not sys.argv[1].startswith('--'):
            conn_string = sys.argv[1]
    
    logger.info(f"Connecting to database: {conn_string.split('@')[-1]}")
    
    # Connect
    conn = psycopg2.connect(conn_string)
    
    try:
        logger.info("Starting test data generation...")
        
        # Generate data
        discovery_run_id = generate_discovery_run(conn)
        test_ids = generate_test_cases(conn, discovery_run_id, count=100)
        generate_test_executions(conn, test_ids, days=7, executions_per_day=15)
        flaky_test_ids = generate_flaky_tests(conn, test_ids, flaky_count=20)
        generate_flaky_history(conn, flaky_test_ids, days=30)
        feature_ids = generate_features(conn, count=50)
        generate_test_feature_mappings(conn, test_ids, feature_ids)
        generate_observability_events(conn, days=7, events_per_day=50)
        
        # Refresh views
        refresh_materialized_views(conn)
        
        logger.info("\n" + "="*60)
        logger.info("✅ Test data generation completed successfully!")
        logger.info(f"   - 1 discovery run")
        logger.info(f"   - {len(test_ids)} test cases")
        logger.info(f"   - ~{len(test_ids) * 7 * 15} test executions")
        logger.info(f"   - {len(flaky_test_ids)} flaky tests")
        logger.info(f"   - ~{len(flaky_test_ids) * 30} flaky history records")
        logger.info(f"   - {len(feature_ids)} features")
        logger.info(f"   - ~350 observability events")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
