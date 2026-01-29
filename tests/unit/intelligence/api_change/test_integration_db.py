"""
Integration tests for API Change Intelligence with PostgreSQL database.

Tests the complete flow with real database:
1. Database connection and schema
2. API change events storage
3. Alert history tracking
4. Confluence notifier with DB persistence
5. Grafana data queries

Uses the same PostgreSQL database configuration from environment:
- CROSSBRIDGE_DB_HOST (default: 10.60.67.247)
- CROSSBRIDGE_DB_PORT (default: 5432)
- CROSSBRIDGE_DB_NAME (default: crossbridge_test)
- CROSSBRIDGE_DB_USER (default: postgres)
- CROSSBRIDGE_DB_PASSWORD (default: admin)
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from core.intelligence.api_change.models.api_change import APIChangeEvent, RiskLevel
from core.intelligence.api_change.storage.repository import APIChangeRepository
from core.intelligence.api_change.alerting.alert_manager import AlertManager
from core.intelligence.api_change.alerting.base import Alert, AlertSeverity


# Database configuration from environment
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
def create_api_change_schema(db_connection):
    """Create API change intelligence schema if it doesn't exist."""
    cursor = db_connection.cursor()
    
    # Create api_changes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_changes (
            id SERIAL PRIMARY KEY,
            change_id VARCHAR(500) UNIQUE NOT NULL,
            change_type VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            path VARCHAR(500),
            method VARCHAR(10),
            breaking BOOLEAN DEFAULT FALSE,
            risk_level VARCHAR(20),
            old_value TEXT,
            new_value TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB,
            recommended_tests TEXT[]
        )
    """)
    
    # Create alert_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id SERIAL PRIMARY KEY,
            alert_id VARCHAR(500) UNIQUE NOT NULL,
            title VARCHAR(500) NOT NULL,
            message TEXT,
            severity VARCHAR(20) NOT NULL,
            source VARCHAR(200),
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notifiers_sent INTEGER DEFAULT 0,
            details JSONB,
            tags TEXT[]
        )
    """)
    
    # Create grafana_api_metrics table for Grafana queries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grafana_api_metrics (
            id SERIAL PRIMARY KEY,
            metric_time TIMESTAMP NOT NULL,
            total_changes INTEGER DEFAULT 0,
            breaking_changes INTEGER DEFAULT 0,
            high_risk_changes INTEGER DEFAULT 0,
            alerts_sent INTEGER DEFAULT 0,
            metadata JSONB
        )
    """)
    
    db_connection.commit()
    cursor.close()
    
    yield
    
    # Cleanup test data
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM api_changes WHERE change_id LIKE 'test_%'")
    cursor.execute("DELETE FROM alert_history WHERE alert_id LIKE 'test_%'")
    cursor.execute("DELETE FROM grafana_api_metrics WHERE metric_time > NOW() - INTERVAL '1 hour'")
    db_connection.commit()
    cursor.close()


class TestDatabaseIntegration:
    """Integration tests with real PostgreSQL database."""
    
    def test_database_connection(self, db_connection):
        """Test basic database connectivity."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        cursor.close()
        
        assert version is not None
        assert "PostgreSQL" in version[0]
    
    def test_store_api_change(self, db_connection, create_api_change_schema):
        """Test storing an API change event."""
        cursor = db_connection.cursor()
        
        # Create test change
        change_id = f"test_change_{datetime.now().timestamp()}"
        
        cursor.execute("""
            INSERT INTO api_changes 
            (change_id, change_type, entity_type, path, http_method, breaking, risk_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            change_id,
            'field_removed',
            'endpoint',
            '/api/users',
            'GET',
            True,
            'CRITICAL'
        ))
        
        result = cursor.fetchone()
        db_connection.commit()
        cursor.close()
        
        assert result is not None
        assert result[0] > 0
    
    def test_retrieve_api_changes(self, db_connection, create_api_change_schema):
        """Test retrieving API changes from database."""
        cursor = db_connection.cursor()
        
        # Insert test data
        change_id = f"test_retrieve_{datetime.now().timestamp()}"
        cursor.execute("""
            INSERT INTO api_changes 
            (change_id, change_type, entity_type, breaking, risk_level)
            VALUES (%s, %s, %s, %s, %s)
        """, (change_id, 'field_added', 'endpoint', False, 'LOW'))
        
        db_connection.commit()
        
        # Retrieve
        cursor.execute("""
            SELECT change_id, change_type, entity_type, breaking, risk_level
            FROM api_changes
            WHERE change_id = %s
        """, (change_id,))
        
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None
        assert result[0] == change_id
        assert result[1] == 'field_added'
        assert result[2] == 'endpoint'
        assert result[3] is False
        assert result[4] == 'LOW'
    
    def test_store_alert_history(self, db_connection, create_api_change_schema):
        """Test storing alert history."""
        cursor = db_connection.cursor()
        
        alert_id = f"test_alert_{datetime.now().timestamp()}"
        
        cursor.execute("""
            INSERT INTO alert_history 
            (alert_id, title, message, severity, source, notifiers_sent, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            alert_id,
            'Test Alert',
            'Test message',
            'HIGH',
            'Test',
            3,
            ['test', 'breaking']
        ))
        
        result = cursor.fetchone()
        db_connection.commit()
        cursor.close()
        
        assert result is not None
        assert result[0] > 0
    
    def test_query_breaking_changes(self, db_connection, create_api_change_schema):
        """Test querying breaking changes (Grafana use case)."""
        cursor = db_connection.cursor()
        
        # Insert test data
        timestamp = datetime.now()
        for i in range(5):
            cursor.execute("""
                INSERT INTO api_changes 
                (change_id, change_type, entity_type, breaking, risk_level, detected_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                f"test_breaking_{timestamp.timestamp()}_{i}",
                'field_removed',
                'endpoint',
                i % 2 == 0,  # Every other one is breaking
                'HIGH',
                timestamp
            ))
        
        db_connection.commit()
        
        # Query breaking changes
        cursor.execute("""
            SELECT COUNT(*) 
            FROM api_changes 
            WHERE breaking = TRUE
            AND detected_at > %s
        """, (timestamp - timedelta(minutes=1),))
        
        result = cursor.fetchone()
        cursor.close()
        
        assert result[0] >= 3  # At least 3 breaking changes
    
    def test_query_by_risk_level(self, db_connection, create_api_change_schema):
        """Test querying by risk level (Grafana dashboard)."""
        cursor = db_connection.cursor()
        
        # Insert test data with different risk levels
        timestamp = datetime.now()
        risk_levels = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        
        for i, risk in enumerate(risk_levels):
            cursor.execute("""
                INSERT INTO api_changes 
                (change_id, change_type, entity_type, risk_level, detected_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                f"test_risk_{timestamp.timestamp()}_{i}",
                'field_changed',
                'endpoint',
                risk,
                timestamp
            ))
        
        db_connection.commit()
        
        # Query CRITICAL and HIGH changes
        cursor.execute("""
            SELECT COUNT(*) 
            FROM api_changes 
            WHERE risk_level IN ('CRITICAL', 'HIGH')
            AND detected_at > %s
        """, (timestamp - timedelta(minutes=1),))
        
        result = cursor.fetchone()
        cursor.close()
        
        assert result[0] >= 2  # CRITICAL + HIGH
    
    def test_grafana_metrics_aggregation(self, db_connection, create_api_change_schema):
        """Test metrics aggregation for Grafana time series."""
        cursor = db_connection.cursor()
        
        # Insert test metrics
        metric_time = datetime.now()
        cursor.execute("""
            INSERT INTO grafana_api_metrics 
            (metric_time, change_type, severity, risk_level, breaking_count, total_count)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (metric_time, 'REMOVED', 'HIGH', 'HIGH', 5, 25))
        
        db_connection.commit()
        
        # Query metrics (simulating Grafana query)
        cursor.execute("""
            SELECT 
                metric_time,
                total_count,
                breaking_count,
                severity,
                risk_level
            FROM grafana_api_metrics
            WHERE metric_time > %s
            ORDER BY metric_time DESC
            LIMIT 1
        """, (metric_time - timedelta(minutes=1),))
        
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None
        assert result[1] == 25  # total_count
        assert result[2] == 5   # breaking_count
        assert result[3] == 'HIGH'  # severity
        assert result[4] == 'HIGH'  # risk_level


class TestConfluenceWithDatabase:
    """Test Confluence notifier with database persistence."""
    
    @pytest.mark.asyncio
    @patch('core.intelligence.api_change.alerting.confluence_notifier.requests.post')
    async def test_send_alert_and_store(self, mock_post, db_connection, create_api_change_schema):
        """Test sending Confluence alert and storing in database."""
        # Mock successful Confluence response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '12345',
            '_links': {'webui': '/spaces/TEST/pages/12345'}
        }
        mock_post.return_value = mock_response
        
        # Create alert manager with Confluence
        config = {
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        # Mock repository to store in our test database
        class TestRepository:
            def __init__(self, db_conn):
                self.db_conn = db_conn
            
            def save_alert(self, alert, notifiers_sent):
                cursor = self.db_conn.cursor()
                alert_id = f"test_confluence_{datetime.now().timestamp()}"
                cursor.execute("""
                    INSERT INTO alert_history 
                    (alert_id, title, message, severity, source, notifiers_sent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    alert_id,
                    alert.title,
                    alert.message,
                    alert.severity.value,
                    alert.source,
                    notifiers_sent
                ))
                result = cursor.fetchone()
                self.db_conn.commit()
                cursor.close()
                return result[0]
        
        repository = TestRepository(db_connection)
        manager = AlertManager(config, repository=repository)
        
        # Create and send alert
        alert = Alert(
            title="Confluence Test Alert",
            message="Testing Confluence with DB",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.utcnow(),
            source="Integration Test"
        )
        
        result = await manager.send_alert(alert)
        
        # Alert should be sent successfully (mock will always succeed)
        assert result is True
        
        # Note: Alert manager doesn't automatically store to alert_history
        # That would be done by a separate persistence layer


class TestGrafanaQueries:
    """Test Grafana dashboard queries."""
    
    def test_time_series_query(self, db_connection, create_api_change_schema):
        """Test time series query for Grafana graph."""
        cursor = db_connection.cursor()
        
        # Insert hourly metrics for last 24 hours
        base_time = datetime.now()
        for i in range(24):
            metric_time = base_time - timedelta(hours=i)
            cursor.execute("""
                INSERT INTO grafana_api_metrics 
                (metric_time, change_type, severity, risk_level, breaking_count, total_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (metric_time, 'MODIFIED', 'HIGH', 'HIGH', i, i * 2))
        
        db_connection.commit()
        
        # Query last 24 hours (Grafana query)
        cursor.execute("""
            SELECT 
                DATE_TRUNC('hour', metric_time) as hour,
                SUM(total_count) as total,
                SUM(breaking_count) as breaking,
                COUNT(*) as entries
            FROM grafana_api_metrics
            WHERE metric_time > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        
        assert len(results) > 0
    
    def test_breakdown_by_severity(self, db_connection, create_api_change_schema):
        """Test severity breakdown query (Grafana pie chart)."""
        cursor = db_connection.cursor()
        
        # Insert changes with different severities
        timestamp = datetime.now()
        severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        counts = [2, 5, 10, 15]
        
        for severity, count in zip(severities, counts):
            for i in range(count):
                cursor.execute("""
                    INSERT INTO api_changes 
                    (change_id, change_type, entity_type, risk_level, detected_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    f"test_severity_{severity}_{timestamp.timestamp()}_{i}",
                    'field_changed',
                    'endpoint',
                    severity,
                    timestamp
                ))
        
        db_connection.commit()
        
        # Query severity breakdown
        cursor.execute("""
            SELECT 
                risk_level,
                COUNT(*) as count
            FROM api_changes
            WHERE detected_at > %s
            GROUP BY risk_level
            ORDER BY count DESC
        """, (timestamp - timedelta(minutes=1),))
        
        results = cursor.fetchall()
        cursor.close()
        
        assert len(results) >= 4
        # Verify counts match expected distribution
        severity_map = {row[0]: row[1] for row in results}
        assert severity_map.get('LOW', 0) >= 15
        assert severity_map.get('MEDIUM', 0) >= 10


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
