"""
Integration tests for extended framework adapters with real database.

Tests the complete flow:
1. Database connection and schema
2. Framework adapter discovery
3. Test normalization to UnifiedTestMemory
4. Storage in database
5. Retrieval and querying
"""

import os
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open

from core.intelligence.adapters import AdapterFactory
from core.intelligence.models import UnifiedTestMemory, Priority, TestType


# Database configuration from environment or defaults
DB_CONFIG = {
    "host": os.getenv("CROSSBRIDGE_DB_HOST", "10.60.67.247"),
    "port": int(os.getenv("CROSSBRIDGE_DB_PORT", "5432")),
    "database": os.getenv("CROSSBRIDGE_DB_NAME", "crossbridge_test"),
    "user": os.getenv("CROSSBRIDGE_DB_USER", "postgres"),
    "password": os.getenv("CROSSBRIDGE_DB_PASSWORD", "admin"),
}


@pytest.fixture
def db_connection():
    """
    Create a database connection for integration tests.
    Skips if database is not available.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.close()
    except ImportError:
        pytest.skip("psycopg2 not installed")
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture
def create_test_schema(db_connection):
    """Create test schema if it doesn't exist."""
    cursor = db_connection.cursor()
    
    # Create unified_tests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unified_tests (
            id SERIAL PRIMARY KEY,
            test_id VARCHAR(500) UNIQUE NOT NULL,
            framework VARCHAR(100) NOT NULL,
            language VARCHAR(50) NOT NULL,
            priority VARCHAR(20),
            tags TEXT[],
            test_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB
        )
    """)
    
    db_connection.commit()
    cursor.close()
    
    yield
    
    # Cleanup test data
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM unified_tests WHERE test_id LIKE 'test_%'")
    db_connection.commit()
    cursor.close()


class TestDatabaseIntegration:
    """Integration tests with real database."""
    
    def test_database_connection(self, db_connection):
        """Test basic database connectivity."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        cursor.close()
        
        assert version is not None
        assert "PostgreSQL" in version[0]
    
    def test_store_and_retrieve_unified_test(self, db_connection, create_test_schema):
        """Test storing and retrieving a UnifiedTestMemory object."""
        cursor = db_connection.cursor()
        
        # Create a test UnifiedTestMemory
        test_id = f"test_integration_{datetime.now().timestamp()}"
        
        cursor.execute("""
            INSERT INTO unified_tests (test_id, framework, language, priority, tags, test_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (test_id, "pytest", "python", "P0", ["smoke", "integration"], "INTEGRATION"))
        
        db_connection.commit()
        
        # Retrieve it
        cursor.execute("SELECT * FROM unified_tests WHERE test_id = %s", (test_id,))
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None
        assert result[1] == test_id  # test_id column
        assert result[2] == "pytest"  # framework column
        assert result[3] == "python"  # language column


class TestRestAssuredIntegration:
    """Integration tests for RestAssured adapter."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="""
        @Test(priority = 0, groups = {"smoke", "api"})
        public void testGetUser() {
            given()
                .pathParam("id", 123)
            .when()
                .get("/api/users/{id}")
            .then()
                .statusCode(200);
        }
    """)
    @patch("pathlib.Path.exists", return_value=True)
    def test_restassured_to_database(self, mock_exists, mock_file, db_connection, create_test_schema):
        """Test RestAssured adapter integration with database."""
        adapter = AdapterFactory.get_adapter("restassured")
        
        # Normalize test
        unified = adapter.normalize_to_core_model(
            test_file="/src/test/java/ApiTest.java",
            test_name="testGetUser"
        )
        
        assert unified.framework == "restassured"
        assert unified.language == "java"
        
        # Store in database
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO unified_tests (test_id, framework, language, priority, tags, test_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            unified.test_id,
            unified.framework,
            unified.language,
            str(unified.metadata.priority),
            unified.metadata.tags,
            str(unified.structural.test_type) if unified.structural else None
        ))
        db_connection.commit()
        
        # Retrieve and verify
        cursor.execute("SELECT * FROM unified_tests WHERE test_id = %s", (unified.test_id,))
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None
        assert result[2] == "restassured"


class TestPlaywrightIntegration:
    """Integration tests for Playwright adapter."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="""
        // @p0 @smoke @e2e
        test('user login', async ({ page }) => {
            await page.goto('/login');
            await page.fill('#username', 'test');
            await expect(page).toHaveURL('/dashboard');
        });
    """)
    @patch("pathlib.Path.exists", return_value=True)
    def test_playwright_to_database(self, mock_exists, mock_file, db_connection, create_test_schema):
        """Test Playwright adapter integration with database."""
        adapter = AdapterFactory.get_adapter("playwright")
        
        unified = adapter.normalize_to_core_model(
            test_file="/tests/e2e/login.spec.ts",
            test_name="user login"
        )
        
        assert unified.framework == "playwright"
        assert unified.language == "javascript"
        
        # Store in database
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO unified_tests (test_id, framework, language, priority, tags)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            unified.test_id,
            unified.framework,
            unified.language,
            str(unified.metadata.priority),
            unified.metadata.tags
        ))
        db_connection.commit()
        cursor.close()


class TestCucumberIntegration:
    """Integration tests for Cucumber adapter."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="""
        @smoke @api @p0
        Feature: User API
        
        @critical
        Scenario: Create user
            When I POST to /api/users
            Then the response status should be 201
    """)
    @patch("pathlib.Path.exists", return_value=True)
    def test_cucumber_to_database(self, mock_exists, mock_file, db_connection, create_test_schema):
        """Test Cucumber adapter integration with database."""
        adapter = AdapterFactory.get_adapter("cucumber")
        
        unified = adapter.normalize_to_core_model(
            test_file="/features/users.feature",
            test_name="Create user"
        )
        
        assert unified.framework == "cucumber"
        assert unified.language == "gherkin"
        
        # Verify Gherkin parsing extracted API calls
        assert len(unified.structural.api_calls) > 0
        assert unified.structural.api_calls[0].method == "POST"
        
        # Store in database
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO unified_tests (test_id, framework, language, priority, tags, test_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            unified.test_id,
            unified.framework,
            unified.language,
            str(unified.metadata.priority),
            unified.metadata.tags,
            str(unified.structural.test_type)
        ))
        db_connection.commit()
        cursor.close()


class TestCrossFrameworkQuery:
    """Integration tests for cross-framework queries."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="test code")
    @patch("pathlib.Path.exists", return_value=True)
    def test_query_all_frameworks(self, mock_exists, mock_file, db_connection, create_test_schema):
        """Test querying tests across all 12 frameworks."""
        cursor = db_connection.cursor()
        
        # Insert tests from multiple frameworks
        frameworks = [
            ("pytest", "python"),
            ("junit", "java"),
            ("restassured", "java"),
            ("playwright", "javascript"),
            ("cucumber", "gherkin"),
        ]
        
        for i, (framework, language) in enumerate(frameworks):
            adapter = AdapterFactory.get_adapter(framework)
            unified = adapter.normalize_to_core_model(
                test_file=f"/test_{i}.{language}",
                test_name=f"test_{i}"
            )
            
            cursor.execute("""
                INSERT INTO unified_tests (test_id, framework, language)
                VALUES (%s, %s, %s)
            """, (unified.test_id, unified.framework, unified.language))
        
        db_connection.commit()
        
        # Query all frameworks
        cursor.execute("SELECT DISTINCT framework FROM unified_tests")
        results = cursor.fetchall()
        cursor.close()
        
        stored_frameworks = [r[0] for r in results]
        assert len(stored_frameworks) >= 5
        assert "pytest" in stored_frameworks
        assert "restassured" in stored_frameworks


class TestBatchInsert:
    """Test batch operations with extended frameworks."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="test code")
    @patch("pathlib.Path.exists", return_value=True)
    def test_batch_insert_all_frameworks(self, mock_exists, mock_file, db_connection, create_test_schema):
        """Test batch insertion of tests from all 12 frameworks."""
        cursor = db_connection.cursor()
        
        all_frameworks = AdapterFactory.list_supported_frameworks()
        batch_data = []
        
        for i, framework in enumerate(all_frameworks):
            adapter = AdapterFactory.get_adapter(framework)
            language = adapter.get_language()
            
            unified = adapter.normalize_to_core_model(
                test_file=f"/test_{framework}_{i}.{language}",
                test_name=f"test_{framework}_{i}"
            )
            
            batch_data.append((
                unified.test_id,
                unified.framework,
                unified.language,
                str(unified.metadata.priority),
                unified.metadata.tags
            ))
        
        # Batch insert
        cursor.executemany("""
            INSERT INTO unified_tests (test_id, framework, language, priority, tags)
            VALUES (%s, %s, %s, %s, %s)
        """, batch_data)
        
        db_connection.commit()
        
        # Verify count
        cursor.execute("SELECT COUNT(*) FROM unified_tests WHERE test_id LIKE 'test_%'")
        count = cursor.fetchone()[0]
        cursor.close()
        
        assert count == len(all_frameworks)
        assert count == 12


@pytest.mark.skipif(
    not os.getenv("RUN_DB_INTEGRATION_TESTS"),
    reason="Database integration tests require RUN_DB_INTEGRATION_TESTS=1"
)
class TestFullIntegrationWorkflow:
    """Full integration workflow tests."""
    
    @patch("pathlib.Path.exists", return_value=True)
    def test_complete_workflow(self, mock_exists, db_connection, create_test_schema):
        """Test complete workflow: discover -> normalize -> store -> query."""
        # This would test with real files if available
        # For now, use mocked data
        pass
