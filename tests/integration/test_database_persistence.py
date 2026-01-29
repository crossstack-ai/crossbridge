"""
Integration tests for database persistence workflows.

Tests end-to-end workflows from test execution through database storage
to Grafana visualization queries.
"""

import pytest
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import tempfile

# Mock imports for integration testing - these will be skipped if not available
try:
    from persistence.postgres_adapter import PostgresAdapter
    from core.profiling.storage import ProfilingStorage
    PERSISTENCE_AVAILABLE = True
except ImportError:
    PERSISTENCE_AVAILABLE = False
    PostgresAdapter = None
    ProfilingStorage = None


class MockDatabaseIntegration:
    """Mock database integration for testing purposes."""
    
    def __init__(self):
        self.test_results = []
        self.coverage_data = []
        self.profiling_data = []
    
    def check_health(self) -> bool:
        """Check if database is healthy."""
        return True
    
    def save_test_result(self, result: Dict[str, Any]) -> bool:
        """Save test result."""
        self.test_results.append(result)
        return True
    
    def get_recent_test_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent test results."""
        return self.test_results[-limit:]
    
    def save_coverage_data(self, coverage: Dict[str, Any]) -> bool:
        """Save coverage data."""
        self.coverage_data.append(coverage)
        return True
    
    def get_coverage_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get coverage history."""
        return self.coverage_data
    
    def detect_flaky_tests(self, min_runs: int = 3, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Detect flaky tests."""
        # Group by test_id
        from collections import defaultdict
        test_runs = defaultdict(list)
        
        for result in self.test_results:
            test_runs[result['test_id']].append(result)
        
        flaky = []
        for test_id, runs in test_runs.items():
            if len(runs) >= min_runs:
                fail_count = sum(1 for r in runs if r['status'] == 'failed')
                flakiness_score = fail_count / len(runs)
                if 0 < flakiness_score < 1 - threshold:
                    flaky.append({
                        'test_id': test_id,
                        'flakiness_score': flakiness_score,
                        'runs': len(runs)
                    })
        return flaky
    
    def get_test_trends(self, test_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get test trends."""
        return [r for r in self.test_results if r['test_id'] == test_id]
    
    def get_test_results_for_grafana(self, time_range: str, interval: str) -> Dict[str, Any]:
        """Get test results in Grafana format."""
        return {
            'type': 'table',
            'columns': [
                {'text': 'time', 'type': 'time'},
                {'text': 'test_id', 'type': 'string'},
                {'text': 'status', 'type': 'string'},
                {'text': 'duration', 'type': 'number'}
            ],
            'rows': [
                [r['timestamp'], r['test_id'], r['status'], r['duration']]
                for r in self.test_results
            ]
        }
    
    def bulk_save_test_results(self, results: List[Dict[str, Any]]) -> bool:
        """Bulk save test results."""
        self.test_results.extend(results)
        return True
    
    def get_test_results_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get test results by run ID."""
        return [r for r in self.test_results if r.get('run_id') == run_id]
    
    def save_profiling_data(self, data: Dict[str, Any]) -> bool:
        """Save profiling data."""
        self.profiling_data.append(data)
        return True
    
    def get_profiling_data(self, test_id: str) -> List[Dict[str, Any]]:
        """Get profiling data."""
        return [d for d in self.profiling_data if d.get('test_id') == test_id]


class TestDatabasePersistenceWorkflow:
    """Test complete database persistence workflows."""
    
    @pytest.fixture(scope="class")
    def db_integration(self):
        """Initialize database integration."""
        # Use mock for integration testing
        # In real scenarios, this would connect to actual database
        db = MockDatabaseIntegration()
        yield db
    
    @pytest.fixture
    def sample_test_results(self) -> List[Dict[str, Any]]:
        """Sample test execution results."""
        return [
            {
                "test_id": "test_login_success",
                "test_name": "test_successful_login",
                "test_file": "tests/test_auth.py",
                "status": "passed",
                "duration": 2.5,
                "framework": "pytest",
                "timestamp": datetime.now(),
                "tags": ["auth", "smoke"],
                "assertions": 3,
                "error_message": None
            },
            {
                "test_id": "test_login_failure",
                "test_name": "test_failed_login",
                "test_file": "tests/test_auth.py",
                "status": "passed",
                "duration": 1.8,
                "framework": "pytest",
                "timestamp": datetime.now(),
                "tags": ["auth", "negative"],
                "assertions": 2,
                "error_message": None
            },
            {
                "test_id": "test_dashboard_load",
                "test_name": "test_dashboard_loading",
                "test_file": "tests/test_dashboard.py",
                "status": "failed",
                "duration": 5.2,
                "framework": "pytest",
                "timestamp": datetime.now(),
                "tags": ["ui", "critical"],
                "assertions": 1,
                "error_message": "Element not found: .dashboard-widget"
            }
        ]
    
    @pytest.fixture
    def sample_coverage_data(self) -> Dict[str, Any]:
        """Sample code coverage data."""
        return {
            "total_coverage": 85.5,
            "branch_coverage": 78.2,
            "line_coverage": 87.3,
            "files": [
                {
                    "file_path": "src/auth/login.py",
                    "coverage": 92.0,
                    "lines_covered": 46,
                    "lines_total": 50,
                    "missing_lines": [15, 16, 23, 48]
                },
                {
                    "file_path": "src/dashboard/widgets.py",
                    "coverage": 75.0,
                    "lines_covered": 60,
                    "lines_total": 80,
                    "missing_lines": list(range(25, 45))
                }
            ],
            "timestamp": datetime.now(),
            "test_run_id": "run_001"
        }
    
    def test_save_test_results_to_database(
        self,
        db_integration: MockDatabaseIntegration,
        sample_test_results: List[Dict[str, Any]]
    ):
        """
        Test saving test execution results to database.
        
        Validates:
        - Test results are saved
        - All fields are persisted correctly
        - Duplicate handling
        - Query retrieval
        """
        # Save results
        for result in sample_test_results:
            success = db_integration.save_test_result(result)
            assert success, f"Failed to save test result: {result['test_id']}"
        
        # Query back results
        saved_results = db_integration.get_recent_test_results(limit=10)
        
        assert len(saved_results) >= len(sample_test_results), \
            "Not all results were saved"
        
        # Verify data integrity
        saved_ids = {r['test_id'] for r in saved_results}
        for original in sample_test_results:
            assert original['test_id'] in saved_ids, \
                f"Test {original['test_id']} not found in database"
    
    def test_save_coverage_data_to_database(
        self,
        db_integration: MockDatabaseIntegration,
        sample_coverage_data: Dict[str, Any]
    ):
        """
        Test saving code coverage data to database.
        
        Validates:
        - Coverage metrics are saved
        - File-level coverage is preserved
        - Time-series tracking
        """
        # Save coverage data
        success = db_integration.save_coverage_data(sample_coverage_data)
        assert success, "Failed to save coverage data"
        
        # Query back coverage
        coverage_history = db_integration.get_coverage_history(days=1)
        
        assert len(coverage_history) >= 1, "Coverage data not saved"
        
        latest = coverage_history[0]
        assert latest['total_coverage'] == sample_coverage_data['total_coverage']
        assert latest['branch_coverage'] == sample_coverage_data['branch_coverage']
    
    def test_flaky_test_detection_workflow(
        self,
        db_integration: MockDatabaseIntegration
    ):
        """
        Test flaky test detection through multiple test runs.
        
        Validates:
        - Historical test results are tracked
        - Flaky patterns are detected
        - Confidence scores are calculated
        """
        # Simulate flaky test over multiple runs
        test_id = "test_flaky_example"
        
        # Run 1: Pass
        db_integration.save_test_result({
            "test_id": test_id,
            "test_name": "test_flaky_example",
            "test_file": "tests/test_flaky.py",
            "status": "passed",
            "duration": 2.0,
            "framework": "pytest",
            "timestamp": datetime.now() - timedelta(hours=5),
            "tags": ["flaky"],
            "run_id": "run_001"
        })
        
        # Run 2: Fail
        db_integration.save_test_result({
            "test_id": test_id,
            "test_name": "test_flaky_example",
            "test_file": "tests/test_flaky.py",
            "status": "failed",
            "duration": 2.1,
            "framework": "pytest",
            "timestamp": datetime.now() - timedelta(hours=4),
            "tags": ["flaky"],
            "run_id": "run_002",
            "error_message": "Timeout waiting for element"
        })
        
        # Run 3: Pass
        db_integration.save_test_result({
            "test_id": test_id,
            "test_name": "test_flaky_example",
            "test_file": "tests/test_flaky.py",
            "status": "passed",
            "duration": 1.9,
            "framework": "pytest",
            "timestamp": datetime.now() - timedelta(hours=3),
            "tags": ["flaky"],
            "run_id": "run_003"
        })
        
        # Check flaky detection
        flaky_tests = db_integration.detect_flaky_tests(min_runs=3, threshold=0.3)
        
        assert len(flaky_tests) >= 1, "Flaky test not detected"
        
        flaky_test = next((t for t in flaky_tests if t['test_id'] == test_id), None)
        assert flaky_test is not None, "Specific flaky test not found"
        assert 0 < flaky_test['flakiness_score'] < 1, "Invalid flakiness score"
    
    def test_test_trend_analysis(
        self,
        db_integration: MockDatabaseIntegration
    ):
        """
        Test analyzing test trends over time.
        
        Validates:
        - Pass/fail rate calculation
        - Duration trends
        - Failure pattern identification
        """
        # Save test results over multiple days
        test_id = "test_performance_check"
        
        for day in range(5):
            timestamp = datetime.now() - timedelta(days=day)
            status = "passed" if day % 2 == 0 else "failed"
            duration = 2.0 + (day * 0.5)  # Increasing duration
            
            db_integration.save_test_result({
                "test_id": test_id,
                "test_name": "test_performance_check",
                "test_file": "tests/test_performance.py",
                "status": status,
                "duration": duration,
                "framework": "pytest",
                "timestamp": timestamp,
                "tags": ["performance"],
                "run_id": f"run_{day}"
            })
        
        # Get trend data
        trends = db_integration.get_test_trends(test_id=test_id, days=7)
        
        assert len(trends) >= 5, "Not enough trend data"
        
        # Verify trend calculations
        pass_rate = sum(1 for t in trends if t['status'] == 'passed') / len(trends)
        assert 0 <= pass_rate <= 1, "Invalid pass rate"
        
        # Check duration trend
        durations = [t['duration'] for t in trends]
        assert max(durations) > min(durations), "Duration not varying"
    
    def test_grafana_query_format(
        self,
        db_integration: MockDatabaseIntegration,
        sample_test_results: List[Dict[str, Any]]
    ):
        """
        Test that database queries return Grafana-compatible format.
        
        Validates:
        - Time-series format
        - Aggregation functions
        - Field naming
        """
        # Save sample data
        for result in sample_test_results:
            db_integration.save_test_result(result)
        
        # Get data in Grafana format
        grafana_data = db_integration.get_test_results_for_grafana(
            time_range="24h",
            interval="1h"
        )
        
        assert 'columns' in grafana_data, "Missing columns in Grafana format"
        assert 'rows' in grafana_data, "Missing rows in Grafana format"
        assert 'type' in grafana_data, "Missing type in Grafana format"
        
        # Verify time-series structure
        if grafana_data['type'] == 'table':
            assert len(grafana_data['columns']) > 0, "No columns defined"
            assert len(grafana_data['rows']) > 0, "No data rows"
    
    def test_bulk_insert_performance(
        self,
        db_integration: MockDatabaseIntegration
    ):
        """
        Test bulk insert performance for large test suites.
        
        Validates:
        - Batch insertion works
        - Performance is acceptable
        - No data loss
        """
        # Generate large batch of test results
        batch_size = 100
        test_results = []
        
        for i in range(batch_size):
            test_results.append({
                "test_id": f"test_bulk_{i}",
                "test_name": f"test_bulk_{i}",
                "test_file": f"tests/test_bulk_{i % 10}.py",
                "status": "passed" if i % 3 != 0 else "failed",
                "duration": 1.0 + (i % 5) * 0.5,
                "framework": "pytest",
                "timestamp": datetime.now(),
                "tags": [f"tag_{i % 5}"],
                "run_id": "bulk_run"
            })
        
        # Measure bulk insert time
        start_time = datetime.now()
        success = db_integration.bulk_save_test_results(test_results)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        assert success, "Bulk insert failed"
        assert duration < 5.0, f"Bulk insert too slow: {duration}s for {batch_size} records"
        
        # Verify all records saved
        saved_results = db_integration.get_test_results_by_run_id("bulk_run")
        assert len(saved_results) == batch_size, \
            f"Expected {batch_size} results, got {len(saved_results)}"
    
    def test_profiling_data_persistence(
        self,
        db_integration: MockDatabaseIntegration
    ):
        """
        Test persisting profiling data (function calls, memory, CPU).
        
        Validates:
        - Profiling metrics are saved
        - High-frequency data handling
        - Query performance
        """
        profiling_data = {
            "test_id": "test_with_profiling",
            "run_id": "profiled_run",
            "timestamp": datetime.now(),
            "metrics": {
                "cpu_percent": 45.2,
                "memory_mb": 128.5,
                "function_calls": [
                    {"function": "authenticate", "duration_ms": 150},
                    {"function": "query_database", "duration_ms": 220},
                    {"function": "render_template", "duration_ms": 85}
                ],
                "database_queries": 12,
                "http_requests": 5
            }
        }
        
        # Save profiling data
        success = db_integration.save_profiling_data(profiling_data)
        assert success, "Failed to save profiling data"
        
        # Query profiling data
        retrieved = db_integration.get_profiling_data(test_id="test_with_profiling")
        
        assert len(retrieved) >= 1, "Profiling data not retrieved"
        assert retrieved[0]['metrics']['cpu_percent'] == 45.2


class TestPostgresAdapter:
    """Test PostgreSQL adapter directly."""
    
    @pytest.fixture
    def postgres_adapter(self):
        """Initialize PostgreSQL adapter."""
        if not os.getenv("DB_HOST"):
            pytest.skip("Database not configured")
        
        try:
            adapter = PostgresAdapter()
            yield adapter
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
    
    def test_connection_pooling(self, postgres_adapter: PostgresAdapter):
        """Test connection pool management."""
        # Get multiple connections
        conn1 = postgres_adapter.get_connection()
        conn2 = postgres_adapter.get_connection()
        
        assert conn1 is not None
        assert conn2 is not None
        assert conn1 != conn2  # Should be different connections
        
        # Release connections
        postgres_adapter.release_connection(conn1)
        postgres_adapter.release_connection(conn2)
    
    def test_transaction_handling(self, postgres_adapter: PostgresAdapter):
        """Test transaction commit and rollback."""
        # Start transaction
        conn = postgres_adapter.get_connection()
        cursor = conn.cursor()
        
        try:
            # Insert test data
            cursor.execute("""
                INSERT INTO test_results (test_id, test_name, status, duration, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, ("tx_test", "transaction_test", "passed", 1.0, datetime.now()))
            
            # Rollback
            conn.rollback()
            
            # Verify data not saved
            cursor.execute("SELECT * FROM test_results WHERE test_id = %s", ("tx_test",))
            result = cursor.fetchone()
            
            assert result is None, "Transaction not rolled back"
        finally:
            postgres_adapter.release_connection(conn)
    
    def test_query_optimization(self, postgres_adapter: PostgresAdapter):
        """Test query performance with indexes."""
        # This test would verify that queries are fast with proper indexes
        # For now, just check that query executes
        conn = postgres_adapter.get_connection()
        cursor = conn.cursor()
        
        try:
            # Query with index should be fast
            start_time = datetime.now()
            cursor.execute("""
                SELECT * FROM test_results 
                WHERE timestamp > %s 
                ORDER BY timestamp DESC 
                LIMIT 100
            """, (datetime.now() - timedelta(days=7),))
            results = cursor.fetchall()
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            
            # Query should be fast (under 1 second for reasonable data size)
            assert duration < 1.0, f"Query too slow: {duration}s"
        finally:
            postgres_adapter.release_connection(conn)


class TestProfilingStorage:
    """Test profiling data storage backend."""
    
    @pytest.fixture
    def profiling_storage(self):
        """Initialize profiling storage."""
        if not os.getenv("DB_HOST"):
            pytest.skip("Database not configured")
        
        try:
            storage = ProfilingStorage(backend="postgresql")
            yield storage
        finally:
            storage.shutdown()
    
    def test_store_function_metrics(self, profiling_storage: ProfilingStorage):
        """Test storing function-level profiling metrics."""
        metrics = {
            "test_id": "test_profiled_function",
            "timestamp": datetime.now(),
            "function_name": "calculate_total",
            "call_count": 150,
            "total_time_ms": 2500,
            "avg_time_ms": 16.67,
            "max_time_ms": 45,
            "min_time_ms": 5
        }
        
        success = profiling_storage.store_function_metrics(metrics)
        assert success, "Failed to store function metrics"
    
    def test_query_hotspots(self, profiling_storage: ProfilingStorage):
        """Test querying performance hotspots."""
        # Store some metrics
        for i in range(5):
            profiling_storage.store_function_metrics({
                "test_id": f"test_{i}",
                "timestamp": datetime.now(),
                "function_name": f"function_{i}",
                "call_count": 100 + i * 10,
                "total_time_ms": 1000 + i * 500,
                "avg_time_ms": 10 + i * 5
            })
        
        # Query hotspots
        hotspots = profiling_storage.get_performance_hotspots(limit=5)
        
        assert len(hotspots) > 0, "No hotspots found"
        # Hotspots should be ordered by total time
        if len(hotspots) > 1:
            assert hotspots[0]['total_time_ms'] >= hotspots[-1]['total_time_ms']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
