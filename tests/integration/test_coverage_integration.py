"""
Integration test for behavioral coverage with PostgreSQL database.

Tests the complete flow:
1. Parse coverage reports
2. Collect behavioral coverage
3. Store in database
4. Query coverage data
"""

import pytest
import psycopg2
import psycopg2.extras
import uuid
from datetime import datetime
from pathlib import Path
import tempfile
import json

# Register UUID adapter for psycopg2
psycopg2.extras.register_uuid()

# Database connection (from user's environment)
DB_CONN = "postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation"


@pytest.fixture(scope="module")
def db_connection():
    """Provide database connection for tests."""
    conn = psycopg2.connect(DB_CONN)
    yield conn
    conn.close()


@pytest.fixture
def clean_test_data(db_connection):
    """Clean up test data before and after each test."""
    cursor = db_connection.cursor()
    test_id_prefix = 'integration_test_%'
    
    # Cleanup before test
    cursor.execute("DELETE FROM api_endpoint_coverage WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM ui_component_coverage WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM network_capture WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM contract_coverage WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM test_case WHERE method_name LIKE %s", (test_id_prefix,))
    db_connection.commit()
    
    yield
    
    # Cleanup after test
    cursor.execute("DELETE FROM api_endpoint_coverage WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM ui_component_coverage WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM network_capture WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM contract_coverage WHERE test_case_id IN (SELECT id FROM test_case WHERE method_name LIKE %s)", (test_id_prefix,))
    cursor.execute("DELETE FROM test_case WHERE method_name LIKE %s", (test_id_prefix,))
    db_connection.commit()
    cursor.close()


class TestApiEndpointCoverageIntegration:
    """Test API endpoint coverage end-to-end."""
    
    def test_api_coverage_workflow(self, db_connection, clean_test_data):
        """Test complete workflow: collect → store → query API coverage."""
        from core.coverage.behavioral_collectors import ApiEndpointCollector
        
        cursor = db_connection.cursor()
        
        # 1. Create test case in database
        test_id = uuid.uuid4()
        cursor.execute("""
            INSERT INTO test_case (id, framework, package, class_name, method_name, file_path, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            test_id,
            'pytest',
            'tests.api',
            'TestOrders',
            'integration_test_api_endpoint_coverage',
            'tests/api/test_orders.py',
            ['api', 'integration']
        ))
        db_connection.commit()
        
        # 2. Collect API endpoint coverage
        collector = ApiEndpointCollector()
        coverage1 = collector.record_api_call(
            test_case_id=test_id,
            endpoint_path="/api/v1/orders/12345",
            http_method="GET",
            status_code=200,
            request_body='{}',
            response_body='{"order_id": 12345, "status": "shipped"}'
        )
        
        coverage2 = collector.record_api_call(
            test_case_id=test_id,
            endpoint_path="/api/v1/orders",
            http_method="POST",
            status_code=201,
            request_body='{"customer_id": 789, "items": []}',
            response_body='{"order_id": 54321}'
        )
        
        # 3. Store in database
        cursor.execute("""
            INSERT INTO api_endpoint_coverage 
            (id, test_case_id, endpoint_path, http_method, status_code, request_schema, response_schema, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            coverage1.id,
            coverage1.test_case_id,
            coverage1.endpoint_path,
            coverage1.http_method,
            coverage1.status_code,
            json.dumps(coverage1.request_schema) if coverage1.request_schema else None,
            json.dumps(coverage1.response_schema) if coverage1.response_schema else None,
            json.dumps(coverage1.metadata) if coverage1.metadata else None,
            coverage1.created_at
        ))
        
        cursor.execute("""
            INSERT INTO api_endpoint_coverage 
            (id, test_case_id, endpoint_path, http_method, status_code, request_schema, response_schema, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            coverage2.id,
            coverage2.test_case_id,
            coverage2.endpoint_path,
            coverage2.http_method,
            coverage2.status_code,
            json.dumps(coverage2.request_schema) if coverage2.request_schema else None,
            json.dumps(coverage2.response_schema) if coverage2.response_schema else None,
            json.dumps(coverage2.metadata) if coverage2.metadata else None,
            coverage2.created_at
        ))
        
        db_connection.commit()
        
        # 4. Query back and verify
        cursor.execute("""
            SELECT endpoint_path, http_method, status_code
            FROM api_endpoint_coverage
            WHERE test_case_id = %s
            ORDER BY http_method, endpoint_path
        """, (test_id,))
        
        results = cursor.fetchall()
        assert len(results) == 2
        
        # Verify GET /api/v1/orders/{id}
        assert results[0][1] == "GET"
        assert results[0][0] == "/api/v1/orders/{id}"  # Normalized path
        assert results[0][2] == 200
        
        # Verify POST /api/v1/orders
        assert results[1][1] == "POST"
        assert results[1][0] == "/api/v1/orders"
        assert results[1][2] == 201
        
        cursor.close()


class TestUiComponentCoverageIntegration:
    """Test UI component coverage end-to-end."""
    
    def test_ui_coverage_workflow(self, db_connection, clean_test_data):
        """Test complete workflow: collect → store → query UI coverage."""
        from core.coverage.behavioral_collectors import UiComponentCollector
        
        cursor = db_connection.cursor()
        
        # 1. Create test case
        test_id = uuid.uuid4()
        cursor.execute("""
            INSERT INTO test_case (id, framework, package, class_name, method_name, file_path, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            test_id,
            'selenium',
            'tests.ui',
            'TestLogin',
            'integration_test_ui_component_coverage',
            'tests/ui/test_login.py',
            ['ui', 'integration']
        ))
        db_connection.commit()
        
        # 2. Collect UI coverage
        collector = UiComponentCollector()
        coverage1 = collector.record_interaction(
            test_case_id=test_id,
            component_name="username_input",
            component_type="input",
            interaction_type="type",
            selector="#username",
            page_url="https://app.example.com/login"
        )
        
        coverage2 = collector.record_interaction(
            test_case_id=test_id,
            component_name="login_button",
            component_type="button",
            interaction_type="click",
            selector="button[type='submit']",
            page_url="https://app.example.com/login"
        )
        
        # 3. Store in database
        for coverage in [coverage1, coverage2]:
            cursor.execute("""
                INSERT INTO ui_component_coverage 
                (id, test_case_id, component_name, component_type, selector, page_url, interaction_type, interaction_count, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                coverage.id,
                coverage.test_case_id,
                coverage.component_name,
                coverage.component_type,
                coverage.selector,
                coverage.page_url,
                coverage.interaction_type,
                coverage.interaction_count,
                json.dumps(coverage.metadata) if coverage.metadata else None,
                coverage.created_at
            ))
        
        db_connection.commit()
        
        # 4. Query and verify
        cursor.execute("""
            SELECT component_name, component_type, interaction_type, interaction_count
            FROM ui_component_coverage
            WHERE test_case_id = %s
            ORDER BY component_name
        """, (test_id,))
        
        results = cursor.fetchall()
        assert len(results) == 2
        assert results[0][0] == "login_button"
        assert results[0][1] == "button"
        assert results[0][2] == "click"
        assert results[1][0] == "username_input"
        assert results[1][1] == "input"
        assert results[1][2] == "type"
        
        cursor.close()


class TestDatabaseSchema:
    """Verify database schema is correctly applied."""
    
    def test_required_tables_exist(self, db_connection):
        """Verify all required tables exist."""
        cursor = db_connection.cursor()
        
        required_tables = [
            'test_case',
            'feature',
            'code_unit',
            'external_test_case',
            'test_case_external_map',
            'test_feature_map',
            'test_code_coverage_map',
            'git_change_event',
            'git_change_impact',
            'api_endpoint_coverage',
            'ui_component_coverage',
            'network_capture',
            'contract_coverage'
        ]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = ANY(%s)
        """, (required_tables,))
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            assert table in existing_tables, f"Table {table} not found in database"
        
        cursor.close()
    
    def test_required_views_exist(self, db_connection):
        """Verify all required views exist."""
        cursor = db_connection.cursor()
        
        required_views = [
            'functional_coverage_map',
            'test_to_feature_coverage',
            'change_impact_surface',
            'api_endpoint_summary',
            'ui_component_summary',
            'functional_surface_coverage'
        ]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name = ANY(%s)
        """, (required_views,))
        
        existing_views = [row[0] for row in cursor.fetchall()]
        
        for view in required_views:
            assert view in existing_views, f"View {view} not found in database"
        
        cursor.close()


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_coverage_integration.py -v
    pytest.main([__file__, "-v", "--tb=short"])
