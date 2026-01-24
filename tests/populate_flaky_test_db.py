"""
Populate database with sample flaky test data for Grafana visualization.

This script generates realistic test execution history and stores it in PostgreSQL,
then runs flaky detection to populate all tables for Grafana dashboards.

Usage:
    python tests/populate_flaky_test_db.py
    
Environment:
    CROSSBRIDGE_DB_URL must be set to PostgreSQL connection string
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.flaky_detection.models import (
    TestExecutionRecord, 
    FlakyTestResult,
    TestFramework, 
    TestStatus
)
from core.flaky_detection.persistence import FlakyDetectionRepository
from core.flaky_detection.feature_engineering import FeatureEngineer
from core.flaky_detection.detector import FlakyDetector


def load_db_config_from_yaml():
    """Load database configuration from crossbridge.yml"""
    config_path = Path(__file__).parent.parent / "crossbridge.yml"
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            
        # Replace environment variable syntax with actual values
        import re
        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2)
            return os.environ.get(var_name, default_value)
        
        # Pattern: ${VAR_NAME:-default_value}
        content = re.sub(r'\$\{([^:]+):-([^}]+)\}', replace_env_var, content)
        
        config = yaml.safe_load(content)
        
        db_config = config.get('crossbridge', {}).get('database', {})
        if not db_config or not db_config.get('enabled', False):
            return None
        
        # Extract values
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        database = db_config.get('database', 'crossbridge')
        user = db_config.get('user', 'postgres')
        password = db_config.get('password', '')
        
        # Build connection string
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return db_url
    
    except Exception as e:
        print(f"⚠️  Warning: Could not parse crossbridge.yml: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_flaky_test_pattern(
    test_id: str,
    test_name: str,
    framework: TestFramework,
    num_executions: int = 50,
    failure_rate: float = 0.6,
    base_duration: int = 150
) -> list[TestExecutionRecord]:
    """Generate flaky test execution pattern with intermittent failures."""
    
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(num_executions):
        # Flaky pattern: alternating pass/fail with some randomness
        if random.random() < failure_rate:
            status = TestStatus.FAILED
            error_types = [
                "AssertionError: Expected 200, got 500",
                "TimeoutException: Element not found",
                "ConnectionError: Database connection lost",
                "StaleElementReferenceException: Element no longer attached"
            ]
            error = random.choice(error_types)
            error_sig = error.split(":")[0]
        else:
            status = TestStatus.PASSED
            error = None
            error_sig = None
        
        # Variable duration (flaky tests often have timing issues)
        duration = base_duration + random.randint(-50, 100)
        
        # Sometimes needs retry
        retry_count = random.choice([0, 0, 0, 1, 1, 2])
        
        # Simulate different commits
        commit_hash = f"abc{i % 5}def"
        
        record = TestExecutionRecord(
            test_id=test_id,
            test_name=test_name,
            framework=framework,
            status=status,
            duration_ms=duration,
            executed_at=base_time + timedelta(hours=i * 2),
            error_signature=error_sig,
            error_full=error,
            retry_count=retry_count,
            git_commit=commit_hash,
            environment="ci",
            build_id=f"build-{1000 + i}",
            external_test_id=f"C{12345 + hash(test_id) % 1000}" if "login" in test_id else None,
            external_system="testrail" if "login" in test_id else None
        )
        executions.append(record)
    
    return executions


def generate_stable_test_pattern(
    test_id: str,
    test_name: str,
    framework: TestFramework,
    num_executions: int = 50,
    base_duration: int = 100
) -> list[TestExecutionRecord]:
    """Generate stable test execution pattern (mostly passing)."""
    
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(num_executions):
        # Stable pattern: 95% pass rate
        if random.random() < 0.05:
            status = TestStatus.FAILED
            error = "AssertionError: Legitimate test failure"
            error_sig = "AssertionError"
        else:
            status = TestStatus.PASSED
            error = None
            error_sig = None
        
        # Consistent duration (stable tests have low variance)
        duration = base_duration + random.randint(-5, 5)
        
        commit_hash = f"abc{i % 5}def"
        
        record = TestExecutionRecord(
            test_id=test_id,
            test_name=test_name,
            framework=framework,
            status=status,
            duration_ms=duration,
            executed_at=base_time + timedelta(hours=i * 2),
            error_signature=error_sig,
            error_full=error,
            retry_count=0,
            git_commit=commit_hash,
            environment="ci",
            build_id=f"build-{1000 + i}"
        )
        executions.append(record)
    
    return executions


def generate_timing_sensitive_pattern(
    test_id: str,
    test_name: str,
    framework: TestFramework,
    num_executions: int = 50
) -> list[TestExecutionRecord]:
    """Generate timing-sensitive test pattern (high duration variance)."""
    
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(num_executions):
        # Sometimes slow, sometimes fast
        if random.random() < 0.3:
            # Slow execution - often fails due to timeout
            duration = 300 + random.randint(0, 200)
            status = TestStatus.FAILED if random.random() < 0.7 else TestStatus.PASSED
            error = "TimeoutException: Operation timed out" if status == TestStatus.FAILED else None
            error_sig = "TimeoutException" if status == TestStatus.FAILED else None
        else:
            # Fast execution - usually passes
            duration = 100 + random.randint(-20, 20)
            status = TestStatus.PASSED
            error = None
            error_sig = None
        
        record = TestExecutionRecord(
            test_id=test_id,
            test_name=test_name,
            framework=framework,
            status=status,
            duration_ms=duration,
            executed_at=base_time + timedelta(hours=i * 2),
            error_signature=error_sig,
            error_full=error,
            retry_count=random.choice([0, 1, 1, 2]),
            git_commit=f"abc{i % 5}def",
            environment="ci",
            build_id=f"build-{1000 + i}",
            external_test_id=f"Z-{5000 + hash(test_id) % 100}",
            external_system="zephyr"
        )
        executions.append(record)
    
    return executions


def main():
    """Generate sample data and populate database."""
    
    # Try to get database URL from multiple sources
    db_url = os.environ.get('CROSSBRIDGE_DB_URL')
    
    if not db_url:
        print("📝 No CROSSBRIDGE_DB_URL environment variable found")
        print("   Attempting to read from crossbridge.yml...")
        db_url = load_db_config_from_yaml()
    
    if not db_url:
        print("\n❌ Error: Could not determine database connection")
        print("\nOptions:")
        print("  1. Set CROSSBRIDGE_DB_URL environment variable:")
        print("     export CROSSBRIDGE_DB_URL='postgresql://user:pass@host:5432/dbname'")
        print("\n  2. Configure database in crossbridge.yml:")
        print("     crossbridge:")
        print("       database:")
        print("         enabled: true")
        print("         host: localhost")
        print("         port: 5432")
        print("         database: crossbridge")
        print("         user: postgres")
        print("         password: admin")
        sys.exit(1)
    
    print("=" * 80)
    print("🔬 POPULATING FLAKY TEST DATABASE")
    print("=" * 80)
    print()
    print(f"📍 Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print()
    
    # Initialize repository
    try:
        print("📊 Connecting to database...")
        repo = FlakyDetectionRepository(db_url)
        
        # Create tables if they don't exist
        print("   Creating tables if needed...")
        repo.create_tables()
        print("   ✅ Connected to database")
        print()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Generate test data
    print("📦 Generating sample test execution data...")
    
    all_test_data = []
    
    # 1. Critical flaky test - login (high failure rate, alternating)
    print("   Generating: test_login (FLAKY - Critical)")
    all_test_data.extend(generate_flaky_test_pattern(
        "tests/auth/test_login.py::test_user_login",
        "test_user_login",
        TestFramework.PYTEST,
        num_executions=60,
        failure_rate=0.75,
        base_duration=150
    ))
    
    # 2. High severity flaky test - payment processing
    print("   Generating: test_payment (FLAKY - High)")
    all_test_data.extend(generate_flaky_test_pattern(
        "tests/payment/test_checkout.py::test_payment_processing",
        "test_payment_processing",
        TestFramework.PYTEST,
        num_executions=55,
        failure_rate=0.65,
        base_duration=200
    ))
    
    # 3. Medium severity - API endpoint
    print("   Generating: test_api_endpoint (FLAKY - Medium)")
    all_test_data.extend(generate_flaky_test_pattern(
        "tests/api/test_endpoints.py::test_get_user_profile",
        "test_get_user_profile",
        TestFramework.PYTEST,
        num_executions=50,
        failure_rate=0.50,
        base_duration=80
    ))
    
    # 4. Low severity - data validation
    print("   Generating: test_validation (FLAKY - Low)")
    all_test_data.extend(generate_flaky_test_pattern(
        "tests/validation/test_data.py::test_email_validation",
        "test_email_validation",
        TestFramework.PYTEST,
        num_executions=45,
        failure_rate=0.35,
        base_duration=50
    ))
    
    # 5. Timing-sensitive test
    print("   Generating: test_async_operation (FLAKY - Timing)")
    all_test_data.extend(generate_timing_sensitive_pattern(
        "tests/async/test_operations.py::test_async_data_fetch",
        "test_async_data_fetch",
        TestFramework.PYTEST,
        num_executions=50
    ))
    
    # 6-10. Stable tests
    for i in range(1, 6):
        print(f"   Generating: test_stable_{i} (STABLE)")
        all_test_data.extend(generate_stable_test_pattern(
            f"tests/stable/test_core.py::test_stable_function_{i}",
            f"test_stable_function_{i}",
            TestFramework.PYTEST,
            num_executions=50,
            base_duration=100 + i * 10
        ))
    
    # 11-15. More framework variety
    print("   Generating: test_junit_login (JUNIT - FLAKY)")
    all_test_data.extend(generate_flaky_test_pattern(
        "com.example.auth.LoginTest::testUserAuthentication",
        "testUserAuthentication",
        TestFramework.JUNIT,
        num_executions=55,
        failure_rate=0.60,
        base_duration=180
    ))
    
    print("   Generating: test_junit_stable (JUNIT - STABLE)")
    all_test_data.extend(generate_stable_test_pattern(
        "com.example.core.CoreTest::testDataProcessing",
        "testDataProcessing",
        TestFramework.JUNIT,
        num_executions=50,
        base_duration=120
    ))
    
    print()
    print(f"   ✅ Generated {len(all_test_data)} test execution records")
    print()
    
    # Store in database
    print("💾 Storing test executions in database...")
    try:
        repo.save_executions_batch(all_test_data)
        print(f"   ✅ Stored {len(all_test_data)} records")
    except Exception as e:
        print(f"   ❌ Error storing data: {e}")
        sys.exit(1)
    
    print()
    
    # Run flaky detection
    print("🤖 Running flaky detection analysis...")
    
    # Group by test_id
    from collections import defaultdict
    test_groups = defaultdict(list)
    for record in all_test_data:
        test_groups[record.test_id].append(record)
    
    print(f"   Analyzing {len(test_groups)} unique tests...")
    
    # Extract features
    feature_engineer = FeatureEngineer()
    features = {}
    framework_map = {}
    name_map = {}
    external_id_map = {}
    external_system_map = {}
    
    for test_id, executions in test_groups.items():
        fv = feature_engineer.extract_features(executions)
        if fv:
            features[test_id] = fv
            framework_map[test_id] = executions[0].framework
            name_map[test_id] = executions[0].test_name
            
            # Collect external IDs
            ext_ids = set()
            ext_systems = set()
            for exec_rec in executions:
                if exec_rec.external_test_id:
                    ext_ids.add(exec_rec.external_test_id)
                    ext_systems.add(exec_rec.external_system)
            
            if ext_ids:
                external_id_map[test_id] = list(ext_ids)
                external_system_map[test_id] = list(ext_systems)
    
    # Train detector
    detector = FlakyDetector()
    detector.train(list(features.values()))
    
    # Detect flaky tests
    results = detector.detect_batch(
        features,
        framework_map,
        name_map,
        external_id_map,
        external_system_map
    )
    
    print(f"   ✅ Detection complete")
    print()
    
    # Store results
    print("💾 Storing flaky detection results...")
    for test_id, result in results.items():
        try:
            repo.save_flaky_result(result)
        except Exception as e:
            print(f"   ⚠️  Error saving {test_id}: {e}")
    
    print(f"   ✅ Stored {len(results)} detection results")
    print()
    
    # Display summary
    print("=" * 80)
    print("📊 DATABASE POPULATION COMPLETE")
    print("=" * 80)
    print()
    
    flaky_count = sum(1 for r in results.values() if r.is_flaky)
    stable_count = len(results) - flaky_count
    
    print(f"Total Tests Analyzed:     {len(results)}")
    print(f"Flaky Tests Detected:     {flaky_count}")
    print(f"Stable Tests:             {stable_count}")
    print()
    
    # Show flaky tests
    if flaky_count > 0:
        print("🔴 Detected Flaky Tests:")
        print()
        
        flaky_tests = [(test_id, r) for test_id, r in results.items() if r.is_flaky]
        flaky_tests.sort(key=lambda x: x[1].flaky_score, reverse=True)
        
        for test_id, result in flaky_tests:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(result.severity, "⚪")
            
            external_ids = ""
            if result.external_test_ids:
                refs = [f"{sys}:{id}" for sys, id in zip(result.external_systems, result.external_test_ids)]
                external_ids = f" ({', '.join(refs)})"
            
            print(f"   {severity_emoji} {result.test_name}{external_ids}")
            print(f"      Severity: {result.severity.upper()}")
            print(f"      Score: {result.flaky_score:.3f}")
            print(f"      Failure Rate: {result.features.failure_rate:.1%}")
            print()
    
    print("=" * 80)
    print("✅ SUCCESS!")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("   1. Open Grafana dashboard")
    print("   2. Import: grafana/flaky_test_dashboard.json")
    print("   3. Configure PostgreSQL datasource")
    print("   4. View flaky test trends and metrics")
    print()
    print("Database Tables Populated:")
    print("   • test_execution - Test execution history")
    print("   • flaky_test - Current flaky test results")
    print("   • flaky_test_history - Historical detection data")
    print()


if __name__ == "__main__":
    main()
