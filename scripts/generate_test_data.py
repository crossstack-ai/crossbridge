"""
Test Data Generator for CrossBridge Database
Generates realistic test data for unit testing and Grafana dashboard testing.
"""

import uuid
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import execute_batch
import logging

logger = logging.getLogger(__name__)


class TestDataGenerator:
    """Generate realistic test data for CrossBridge database."""
    
    # Test frameworks
    FRAMEWORKS = ["pytest", "junit", "testng", "robot", "cypress", "playwright"]
    
    # Test statuses
    STATUSES = ["passed", "failed", "skipped", "error"]
    
    # Environments
    ENVIRONMENTS = ["dev", "qa", "staging", "production", "local"]
    
    # Error types
    ERROR_TYPES = [
        "AssertionError", "TimeoutException", "ElementNotFoundException",
        "ConnectionError", "NullPointerException", "IndexError"
    ]
    
    # Feature types
    FEATURE_TYPES = ["api", "service", "bdd", "module", "component"]
    
    # Feature sources
    FEATURE_SOURCES = ["cucumber", "jira", "code", "manual", "api_spec"]
    
    def __init__(self, connection_string: str):
        """Initialize with database connection."""
        self.conn_string = connection_string
        self.conn = None
    
    def connect(self):
        """Connect to database."""
        self.conn = psycopg2.connect(self.conn_string)
        logger.info("Connected to database")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def generate_discovery_run(self, project_name: str = "TestProject") -> str:
        """Generate a discovery run and return its ID."""
        run_id = str(uuid.uuid4())
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO discovery_run 
                (id, started_at, completed_at, status, total_tests_discovered, new_tests_count, 
                 modified_tests_count, framework, git_branch, git_commit, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                run_id,
                datetime.now() - timedelta(minutes=10),
                datetime.now(),
                'completed',
                random.randint(50, 500),
                random.randint(5, 50),
                random.randint(0, 20),
                random.choice(self.FRAMEWORKS),
                random.choice(["main", "develop", "feature/new-tests"]),
                f"abc123{random.randint(1000, 9999)}",
                json.dumps({"project": project_name}),
                datetime.now()
            ))
        
        self.conn.commit()
        logger.info(f"Created discovery run: {run_id}")
        return run_id
    
    def generate_test_cases(self, count: int = 100) -> List[str]:
        """Generate test cases and return their IDs."""
        test_ids = []
        
        with self.conn.cursor() as cur:
            for i in range(count):
                test_id = str(uuid.uuid4())
                framework = random.choice(self.FRAMEWORKS)
                
                cur.execute("""
                    INSERT INTO test_case 
                    (id, framework, package, class_name, method_name, file_path, line_number, tags, intent, created_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (framework, package, class_name, method_name) DO NOTHING
                """, (
                    test_id,
                    framework,
                    f"com.example.tests.{random.choice(['auth', 'api', 'ui', 'integration'])}",
                    f"Test{random.choice(['Login', 'Checkout', 'Search', 'Profile', 'Payment'])}",
                    f"test_{random.choice(['valid', 'invalid', 'edge_case'])}_{random.choice(['scenario', 'flow', 'case'])}_{i}",
                    f"tests/{framework}/test_module_{i % 10}.py",
                    random.randint(10, 500),
                    [random.choice(["smoke", "regression", "critical", "sanity"]) for _ in range(random.randint(1, 3))],
                    f"Verify {random.choice(['login', 'checkout', 'search', 'payment'])} functionality",
                    datetime.now(),
                    {"priority": random.choice(["high", "medium", "low"])}
                ))
                
                test_ids.append(test_id)
        
        self.conn.commit()
        logger.info(f"Created {len(test_ids)} test cases")
        return test_ids
    
    def generate_test_executions(self, test_ids: List[str], days: int = 7, executions_per_day: int = 100):
        """Generate test execution history."""
        start_date = datetime.now() - timedelta(days=days)
        
        executions = []
        for day in range(days):
            for _ in range(executions_per_day):
                test_id = random.choice(test_ids)
                executed_at = start_date + timedelta(days=day, hours=random.randint(0, 23), minutes=random.randint(0, 59))
                
                # Simulate realistic pass/fail distribution
                status_weights = [70, 15, 10, 5]  # passed, failed, skipped, error
                status = random.choices(self.STATUSES, weights=status_weights)[0]
                
                execution = (
                    str(uuid.uuid4()),
                    executed_at,
                    test_id,
                    f"test_name_{test_id[:8]}",
                    f"tests/test_file_{random.randint(1, 20)}.py",
                    random.randint(10, 500),
                    random.choice(self.FRAMEWORKS),
                    status,
                    random.uniform(100, 5000),  # duration_ms
                    f"error_sig_{random.randint(1, 10)}" if status == "failed" else None,
                    f"Full error trace\nLine 1\nLine 2\nLine 3" if status in ["failed", "error"] else None,
                    random.choice(self.ERROR_TYPES) if status in ["failed", "error"] else None,
                    random.randint(0, 3),
                    f"commit_{random.randint(1000, 9999)}",
                    random.choice(self.ENVIRONMENTS),
                    f"build_{random.randint(1000, 9999)}",
                    f"job_{random.randint(100, 999)}",
                    "TestProduct",
                    f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
                    [random.choice(["smoke", "regression"]) for _ in range(random.randint(1, 2))],
                    {"execution_id": str(uuid.uuid4())},
                    datetime.now()
                )
                executions.append(execution)
        
        # Batch insert for performance
        with self.conn.cursor() as cur:
            execute_batch(cur, """
                INSERT INTO test_execution 
                (id, executed_at, test_id, test_name, test_file, test_line, framework, status, duration_ms,
                 error_signature, error_full, error_type, retry_count, git_commit, environment, build_id,
                 ci_job_id, product_name, app_version, tags, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, executions, page_size=100)
        
        self.conn.commit()
        logger.info(f"Created {len(executions)} test executions over {days} days")
    
    def generate_flaky_tests(self, test_ids: List[str], flaky_count: int = 20):
        """Generate flaky test detection results."""
        selected_tests = random.sample(test_ids, min(flaky_count, len(test_ids)))
        
        with self.conn.cursor() as cur:
            for test_id in selected_tests:
                # Generate realistic flaky scores
                is_flaky = random.random() < 0.7  # 70% are actually flaky
                flaky_score = random.uniform(0.6, 0.95) if is_flaky else random.uniform(0.1, 0.5)
                confidence = random.uniform(0.7, 0.95)
                
                classification = (
                    "flaky" if is_flaky and flaky_score > 0.7 else
                    "suspected_flaky" if is_flaky else
                    "stable"
                )
                
                severity = (
                    "critical" if flaky_score > 0.85 else
                    "high" if flaky_score > 0.7 else
                    "medium" if flaky_score > 0.5 else
                    "low"
                )
                
                cur.execute("""
                    INSERT INTO flaky_test 
                    (id, test_id, test_name, framework, flaky_score, is_flaky, confidence, classification,
                     severity, failure_rate, switch_rate, duration_variance, unique_error_count, total_executions,
                     primary_indicators, detected_at, model_version, explanation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (test_id) DO NOTHING
                """, (
                    str(uuid.uuid4()),
                    test_id,
                    f"test_name_{test_id[:8]}",
                    random.choice(self.FRAMEWORKS),
                    flaky_score,
                    is_flaky,
                    confidence,
                    classification,
                    severity,
                    random.uniform(0.05, 0.5),  # failure_rate
                    random.uniform(0.1, 0.6),   # switch_rate
                    random.uniform(0.2, 0.8),   # duration_variance
                    random.randint(1, 5),
                    random.randint(50, 200),
                    ["high_failure_rate", "high_switch_rate", "duration_variance"],
                    datetime.now(),
                    "1.0.0",
                    {"reason": "Frequent failure pattern detected", "recommendation": "Investigate test stability"}
                ))
        
        self.conn.commit()
        logger.info(f"Created {len(selected_tests)} flaky test records")
    
    def generate_flaky_history(self, days: int = 30):
        """Generate flaky test history for trend analysis."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT test_id FROM flaky_test WHERE is_flaky = TRUE")
            flaky_test_ids = [row[0] for row in cur.fetchall()]
        
        if not flaky_test_ids:
            logger.warning("No flaky tests found, skipping history generation")
            return
        
        start_date = datetime.now() - timedelta(days=days)
        history = []
        
        for day in range(days):
            for test_id in flaky_test_ids:
                if random.random() < 0.7:  # 70% chance of detection each day
                    detected_at = start_date + timedelta(days=day, hours=random.randint(0, 23))
                    
                    # Simulate improving or degrading flakiness over time
                    trend = random.choice(["improving", "degrading", "stable"])
                    base_score = random.uniform(0.5, 0.9)
                    
                    if trend == "improving":
                        flaky_score = base_score - (day * 0.01)
                    elif trend == "degrading":
                        flaky_score = base_score + (day * 0.01)
                    else:
                        flaky_score = base_score + random.uniform(-0.05, 0.05)
                    
                    flaky_score = max(0.3, min(0.95, flaky_score))  # Clamp to valid range
                    
                    history.append((
                        str(uuid.uuid4()),
                        detected_at,
                        test_id,
                        flaky_score,
                        flaky_score > 0.6,
                        random.uniform(0.7, 0.95),
                        "flaky" if flaky_score > 0.7 else "suspected_flaky",
                        random.uniform(0.1, 0.5),
                        random.uniform(0.1, 0.6),
                        "1.0.0"
                    ))
        
        with self.conn.cursor() as cur:
            execute_batch(cur, """
                INSERT INTO flaky_test_history 
                (id, detected_at, test_id, flaky_score, is_flaky, confidence, classification,
                 failure_rate, switch_rate, model_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, history, page_size=100)
        
        self.conn.commit()
        logger.info(f"Created {len(history)} flaky test history records")
    
    def generate_features(self, count: int = 50) -> List[str]:
        """Generate features for coverage mapping."""
        feature_ids = []
        
        with self.conn.cursor() as cur:
            for i in range(count):
                feature_id = str(uuid.uuid4())
                feature_type = random.choice(self.FEATURE_TYPES)
                
                cur.execute("""
                    INSERT INTO feature 
                    (id, name, type, source, description, status, created_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name, type, source) DO NOTHING
                """, (
                    feature_id,
                    f"Feature_{feature_type}_{i}",
                    feature_type,
                    random.choice(self.FEATURE_SOURCES),
                    f"Description for {feature_type} feature {i}",
                    random.choice(["active", "deprecated", "planned"]),
                    datetime.now(),
                    {"priority": random.choice(["high", "medium", "low"])}
                ))
                
                feature_ids.append(feature_id)
        
        self.conn.commit()
        logger.info(f"Created {len(feature_ids)} features")
        return feature_ids
    
    def generate_test_feature_mappings(self, test_ids: List[str], feature_ids: List[str]):
        """Generate test-to-feature mappings."""
        mappings = []
        
        for test_id in test_ids:
            # Each test covers 1-3 features
            num_features = random.randint(1, 3)
            selected_features = random.sample(feature_ids, min(num_features, len(feature_ids)))
            
            for feature_id in selected_features:
                mappings.append((
                    str(uuid.uuid4()),
                    test_id,
                    feature_id,
                    random.uniform(0.7, 1.0),
                    random.choice(["coverage", "tag", "annotation", "ai"]),
                    None,  # discovery_run_id
                    datetime.now(),
                    {"verified": random.choice([True, False])}
                ))
        
        with self.conn.cursor() as cur:
            execute_batch(cur, """
                INSERT INTO test_feature_map 
                (id, test_case_id, feature_id, confidence, source, discovery_run_id, created_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (test_case_id, feature_id, source) DO NOTHING
            """, mappings, page_size=100)
        
        self.conn.commit()
        logger.info(f"Created {len(mappings)} test-feature mappings")
    
    def generate_observability_events(self, days: int = 7, events_per_day: int = 50):
        """Generate observability events."""
        start_date = datetime.now() - timedelta(days=days)
        
        event_types = ["discovery", "transformation", "execution", "analysis"]
        event_names = {
            "discovery": ["test_discovery", "page_discovery", "feature_discovery"],
            "transformation": ["code_transform", "framework_migration"],
            "execution": ["test_run", "suite_execution"],
            "analysis": ["coverage_analysis", "flaky_detection", "impact_analysis"]
        }
        
        events = []
        for day in range(days):
            for _ in range(events_per_day):
                event_type = random.choice(event_types)
                event_name = random.choice(event_names[event_type])
                event_time = start_date + timedelta(days=day, hours=random.randint(0, 23), minutes=random.randint(0, 59))
                
                status_weights = [60, 30, 10]  # completed, started, failed
                status = random.choices(["completed", "started", "failed"], weights=status_weights)[0]
                
                events.append((
                    str(uuid.uuid4()),
                    event_time,
                    event_type,
                    event_name,
                    status,
                    random.randint(1000, 60000) if status != "started" else None,
                    "TestProject",
                    random.choice(self.FRAMEWORKS),
                    random.choice(self.ENVIRONMENTS),
                    {"tests_processed": random.randint(10, 500), "success_rate": random.uniform(0.8, 1.0)},
                    "Error occurred during processing" if status == "failed" else None,
                    {"trace_id": str(uuid.uuid4())}
                ))
        
        with self.conn.cursor() as cur:
            execute_batch(cur, """
                INSERT INTO observability_event 
                (id, event_time, event_type, event_name, status, duration_ms, project_name,
                 framework, environment, metrics, error_message, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, events, page_size=100)
        
        self.conn.commit()
        logger.info(f"Created {len(events)} observability events")
    
    def generate_all_test_data(self):
        """Generate complete test dataset."""
        logger.info("Starting test data generation...")
        
        # 1. Discovery run
        discovery_run_id = self.generate_discovery_run("CrossBridge_TestProject")
        
        # 2. Test cases
        test_ids = self.generate_test_cases(count=100)
        
        # 3. Test executions (7 days of history)
        self.generate_test_executions(test_ids, days=7, executions_per_day=150)
        
        # 4. Flaky tests
        self.generate_flaky_tests(test_ids, flaky_count=20)
        
        # 5. Flaky test history (30 days)
        self.generate_flaky_history(days=30)
        
        # 6. Features
        feature_ids = self.generate_features(count=50)
        
        # 7. Test-Feature mappings
        self.generate_test_feature_mappings(test_ids, feature_ids)
        
        # 8. Observability events
        self.generate_observability_events(days=7, events_per_day=50)
        
        logger.info("✅ Test data generation completed successfully!")


def main():
    """Main entry point."""
    import sys
    import os
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Get connection string from environment or argument
    conn_string = os.getenv(
        "CROSSBRIDGE_DB_URL",
        "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
    )
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--connection' and len(sys.argv) > 2:
            conn_string = sys.argv[2]
        elif not sys.argv[1].startswith('--'):
            conn_string = sys.argv[1]
    
    logger.info(f"Connecting to database: {conn_string.split('@')[-1]}")
    
    # Generate test data
    generator = TestDataGenerator(conn_string)
    
    try:
        generator.connect()
        generator.generate_all_test_data()
    except Exception as e:
        logger.error(f"Error generating test data: {e}", exc_info=True)
        sys.exit(1)
    finally:
        generator.close()
    
    logger.info("\n" + "="*60)
    logger.info("Test data generation completed!")
    logger.info("You can now connect Grafana to the database and import the dashboard.")
    logger.info("="*60)


if __name__ == "__main__":
    main()
