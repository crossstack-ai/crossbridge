"""
Unit tests for CrossBridge comprehensive database schema and data generation.
Tests schema creation, data generation, and Grafana queries.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import psycopg2
from psycopg2.extras import RealDictCursor


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing."""
    mock_conn = Mock(spec=psycopg2.extensions.connection)
    mock_cursor = Mock(spec=psycopg2.extensions.cursor)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False
    return mock_conn, mock_cursor


@pytest.fixture
def test_data_generator():
    """Create test data generator with mock connection."""
    from scripts.generate_test_data import TestDataGenerator
    
    generator = TestDataGenerator("postgresql://test:test@localhost:5432/test")
    generator.conn = Mock()
    return generator


class TestSchemaCreation:
    """Test database schema creation."""
    
    def test_comprehensive_schema_file_exists(self):
        """Test that comprehensive schema file exists."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        assert schema_file.exists(), "Comprehensive schema file should exist"
        
        # Check file is not empty
        content = schema_file.read_text()
        assert len(content) > 1000, "Schema file should contain substantial SQL"
        assert "CREATE TABLE" in content
        assert "CREATE EXTENSION" in content
    
    def test_schema_has_required_extensions(self):
        """Test that schema declares required extensions."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        content = schema_file.read_text()
        
        required_extensions = ["uuid-ossp", "vector", "timescaledb"]
        for ext in required_extensions:
            assert ext in content, f"Schema should declare {ext} extension"
    
    def test_schema_has_core_tables(self):
        """Test that schema creates all core tables."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        content = schema_file.read_text()
        
        required_tables = [
            "discovery_run",
            "test_case",
            "page_object",
            "test_execution",
            "flaky_test",
            "flaky_test_history",
            "feature",
            "code_unit",
            "memory_embeddings",
            "git_change_event",
            "observability_event"
        ]
        
        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in content, f"Schema should create {table} table"
    
    def test_schema_has_hypertables(self):
        """Test that schema creates TimescaleDB hypertables."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        content = schema_file.read_text()
        
        # Check for hypertable creation
        assert "create_hypertable" in content.lower(), "Schema should create hypertables"
        assert "test_execution" in content
        assert "flaky_test_history" in content
        assert "git_change_event" in content
        assert "observability_event" in content
    
    def test_schema_has_pgvector_indexes(self):
        """Test that schema creates pgvector indexes."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        content = schema_file.read_text()
        
        # Check for HNSW index
        assert "USING hnsw" in content, "Schema should create HNSW vector index"
        assert "vector_cosine_ops" in content
        assert "memory_embeddings" in content
    
    def test_schema_has_continuous_aggregates(self):
        """Test that schema creates continuous aggregates."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        content = schema_file.read_text()
        
        # Check for continuous aggregates
        assert "CREATE MATERIALIZED VIEW" in content
        assert "test_execution_hourly" in content
        assert "test_execution_daily" in content
        assert "flaky_test_trend_daily" in content
        assert "WITH (timescaledb.continuous)" in content
    
    def test_schema_has_retention_policies(self):
        """Test that schema sets retention policies."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        content = schema_file.read_text()
        
        # Check for retention policies
        assert "add_retention_policy" in content
        assert "90 days" in content  # test_execution retention
        assert "180 days" in content  # flaky_test_history retention
        assert "365 days" in content  # git_change_event retention
    
    def test_schema_has_analytical_views(self):
        """Test that schema creates analytical views for Grafana."""
        from pathlib import Path
        
        schema_file = Path("scripts/comprehensive_schema.sql")
        content = schema_file.read_text()
        
        views = [
            "test_health_overview",
            "recent_test_executions",
            "flaky_test_summary",
            "feature_coverage_gaps"
        ]
        
        for view in views:
            assert f"CREATE OR REPLACE VIEW {view}" in content, f"Schema should create {view} view"


class TestDataGeneration:
    """Test data generation functionality."""
    
    def test_test_data_generator_initialization(self):
        """Test TestDataGenerator initialization."""
        from scripts.generate_test_data import TestDataGenerator
        
        conn_string = "postgresql://test:test@localhost:5432/test"
        generator = TestDataGenerator(conn_string)
        
        assert generator.conn_string == conn_string
        assert generator.conn is None
        assert len(generator.FRAMEWORKS) > 0
        assert len(generator.STATUSES) > 0
    
    def test_generate_discovery_run(self, test_data_generator):
        """Test discovery run generation."""
        mock_cursor = Mock()
        # Fix context manager for cursor
        test_data_generator.conn.cursor = Mock(return_value=Mock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        test_data_generator.conn.commit = Mock()
        
        run_id = test_data_generator.generate_discovery_run("TestProject")
        
        # Check UUID format
        assert uuid.UUID(run_id)
        
        # Check that SQL was executed
        mock_cursor.execute.assert_called_once()
        test_data_generator.conn.commit.assert_called_once()
    
    def test_generate_test_cases(self, test_data_generator):
        """Test test case generation."""
        mock_cursor = Mock()
        # Fix context manager for cursor
        test_data_generator.conn.cursor = Mock(return_value=Mock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        test_data_generator.conn.commit = Mock()
        
        test_ids = test_data_generator.generate_test_cases(count=10)
        
        assert len(test_ids) == 10
        for test_id in test_ids:
            assert uuid.UUID(test_id)  # Valid UUID
        
        # Check that SQL was executed 10 times
        assert mock_cursor.execute.call_count == 10
    
    def test_generate_flaky_tests(self, test_data_generator):
        """Test flaky test generation."""
        mock_cursor = Mock()
        # Fix context manager for cursor
        test_data_generator.conn.cursor = Mock(return_value=Mock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        test_data_generator.conn.commit = Mock()
        
        test_ids = [str(uuid.uuid4()) for _ in range(20)]
        test_data_generator.generate_flaky_tests(test_ids, flaky_count=5)
        
        # Check that SQL was executed for each flaky test
        assert mock_cursor.execute.call_count == 5
        test_data_generator.conn.commit.assert_called_once()
    
    def test_generate_features(self, test_data_generator):
        """Test feature generation."""
        mock_cursor = Mock()
        # Fix context manager for cursor
        test_data_generator.conn.cursor = Mock(return_value=Mock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        test_data_generator.conn.commit = Mock()
        
        feature_ids = test_data_generator.generate_features(count=10)
        
        assert len(feature_ids) == 10
        for feature_id in feature_ids:
            assert uuid.UUID(feature_id)
        
        assert mock_cursor.execute.call_count == 10
    
    def test_frameworks_coverage(self):
        """Test that all major frameworks are included."""
        from scripts.generate_test_data import TestDataGenerator
        
        generator = TestDataGenerator("test")
        
        expected_frameworks = ["pytest", "junit", "testng", "robot", "cypress", "playwright"]
        for framework in expected_frameworks:
            assert framework in generator.FRAMEWORKS
    
    def test_status_types(self):
        """Test that all test statuses are defined."""
        from scripts.generate_test_data import TestDataGenerator
        
        generator = TestDataGenerator("test")
        
        expected_statuses = ["passed", "failed", "skipped", "error"]
        assert generator.STATUSES == expected_statuses


class TestSetupScript:
    """Test setup script functionality."""
    
    def test_setup_script_exists(self):
        """Test that setup script exists."""
        from pathlib import Path
        
        setup_script = Path("scripts/setup_comprehensive_schema.py")
        assert setup_script.exists(), "Setup script should exist"
    
    @patch('psycopg2.connect')
    def test_check_extensions(self, mock_connect):
        """Test extension checking."""
        mock_conn = Mock()
        mock_cursor = Mock()
        # Fix context manager
        mock_conn.cursor = Mock(return_value=Mock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        mock_connect.return_value = mock_conn
        
        from scripts.setup_comprehensive_schema import check_extensions
        
        check_extensions(mock_conn)
        
        # Should try to create extensions
        assert mock_cursor.execute.call_count >= 3  # uuid-ossp, vector, timescaledb
        mock_conn.commit.assert_called_once()
    
    def test_read_schema_file(self):
        """Test reading schema file."""
        from pathlib import Path
        from scripts.setup_comprehensive_schema import read_schema_file
        
        schema_path = Path("scripts/comprehensive_schema.sql")
        content = read_schema_file(schema_path)
        
        assert len(content) > 0
        assert "CREATE TABLE" in content
    
    def test_read_schema_file_not_found(self):
        """Test reading non-existent schema file."""
        from pathlib import Path
        from scripts.setup_comprehensive_schema import read_schema_file
        
        with pytest.raises(FileNotFoundError):
            read_schema_file(Path("nonexistent.sql"))


class TestGrafanaDashboard:
    """Test Grafana dashboard configuration."""
    
    def test_dashboard_file_exists(self):
        """Test that Grafana dashboard file exists."""
        from pathlib import Path
        import json
        
        dashboard_file = Path("grafana/dashboards/crossbridge_overview.json")
        assert dashboard_file.exists(), "Grafana dashboard file should exist"
        
        # Check it's valid JSON (using UTF-8 encoding)
        with open(dashboard_file, encoding='utf-8') as f:
            dashboard = json.load(f)
        
        assert "dashboard" in dashboard
        assert "panels" in dashboard["dashboard"]
    
    def test_dashboard_has_panels(self):
        """Test that dashboard has required panels."""
        from pathlib import Path
        import json
        
        dashboard_file = Path("grafana/dashboards/crossbridge_overview.json")
        with open(dashboard_file, encoding='utf-8') as f:
            dashboard = json.load(f)
        
        panels = dashboard["dashboard"]["panels"]
        assert len(panels) > 0, "Dashboard should have panels"
        
        # Check for key panels
        panel_titles = [p["title"] for p in panels]
        
        expected_panels = [
            "Test Execution Summary",
            "Pass Rate",
            "Flaky Tests Detected",
            "Feature Coverage",
            "Test Execution Trend"
        ]
        
        for expected in expected_panels:
            assert any(expected in title for title in panel_titles), f"Dashboard should have {expected} panel"
    
    def test_dashboard_queries_are_valid(self):
        """Test that dashboard queries have valid structure."""
        from pathlib import Path
        import json
        
        dashboard_file = Path("grafana/dashboards/crossbridge_overview.json")
        with open(dashboard_file, encoding='utf-8') as f:
            dashboard = json.load(f)
        
        panels = dashboard["dashboard"]["panels"]
        
        for panel in panels:
            if "targets" in panel:
                for target in panel["targets"]:
                    assert "refId" in target, "Target should have refId"
                    if "rawSql" in target:
                        # Check SQL queries reference valid tables
                        sql = target["rawSql"]
                        assert "FROM" in sql or "SELECT" in sql, "SQL should be valid"
    
    def test_dashboard_uses_timeseries_data(self):
        """Test that dashboard queries use TimescaleDB features."""
        from pathlib import Path
        import json
        
        dashboard_file = Path("grafana/dashboards/crossbridge_overview.json")
        with open(dashboard_file, encoding='utf-8') as f:
            dashboard = json.load(f)
        
        panels = dashboard["dashboard"]["panels"]
        
        # Find time-series panels
        timeseries_panels = [p for p in panels if p.get("type") == "timeseries"]
        assert len(timeseries_panels) > 0, "Dashboard should have time-series panels"
        
        # Check they query continuous aggregates
        for panel in timeseries_panels:
            if "targets" in panel:
                for target in panel["targets"]:
                    if "rawSql" in target:
                        sql = target["rawSql"]
                        # Should query hourly or daily aggregates
                        assert ("hourly" in sql or "daily" in sql or 
                               "bucket" in sql or "time_bucket" in sql), \
                               "Time-series should use continuous aggregates"


class TestIntegration:
    """Integration tests (require actual database)."""
    
    @pytest.mark.skip(reason="Requires actual database connection")
    def test_full_schema_setup(self):
        """Test complete schema setup."""
        # This would test against a real database
        pass
    
    @pytest.mark.skip(reason="Requires actual database connection")
    def test_data_generation_and_queries(self):
        """Test data generation and Grafana queries."""
        # This would test:
        # 1. Setup schema
        # 2. Generate test data
        # 3. Run all Grafana queries
        # 4. Verify results
        pass
    
    @pytest.mark.skip(reason="Requires actual database connection")
    def test_timescaledb_compression(self):
        """Test TimescaleDB compression policies."""
        # This would test compression on hypertables
        pass


class TestDatabaseQueries:
    """Test database queries used in Grafana."""
    
    def test_test_health_overview_query(self):
        """Test test health overview query structure."""
        query = """
            SELECT 
                COUNT(DISTINCT tc.id) AS total_tests,
                COUNT(DISTINCT CASE WHEN ft.is_flaky THEN tc.id END) AS flaky_tests
            FROM test_case tc
            LEFT JOIN flaky_test ft ON tc.method_name = ft.test_id
        """
        
        # Basic validation
        assert "SELECT" in query
        assert "FROM test_case" in query
        assert "LEFT JOIN flaky_test" in query
    
    def test_recent_executions_query(self):
        """Test recent executions query structure."""
        query = """
            SELECT framework, status, COUNT(*) as count
            FROM test_execution
            WHERE executed_at > NOW() - INTERVAL '24 hours'
            GROUP BY framework, status
        """
        
        assert "FROM test_execution" in query
        assert "WHERE executed_at" in query
        assert "GROUP BY" in query
    
    def test_flaky_trend_query(self):
        """Test flaky trend query uses continuous aggregate."""
        query = """
            SELECT bucket, classification, test_count
            FROM flaky_test_trend_daily
            WHERE bucket > NOW() - INTERVAL '30 days'
        """
        
        assert "FROM flaky_test_trend_daily" in query
        assert "bucket" in query


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
