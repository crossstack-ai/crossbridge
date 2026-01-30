"""
Tests for PostgreSQL drift storage backend.

These tests require a PostgreSQL database to be available.
Set environment variables to configure test database:
- POSTGRES_TEST_HOST (default: localhost)
- POSTGRES_TEST_PORT (default: 5432)
- POSTGRES_TEST_DB (default: crossbridge_test)
- POSTGRES_TEST_USER (default: crossbridge)
- POSTGRES_TEST_PASSWORD (default: test)

To run with Docker:
docker run -d --name crossbridge-test-pg \
  -e POSTGRES_DB=crossbridge_test \
  -e POSTGRES_USER=crossbridge \
  -e POSTGRES_PASSWORD=test \
  -p 5433:5432 \
  postgres:15

Then run: POSTGRES_TEST_PORT=5433 pytest tests/intelligence/test_drift_storage_postgres.py
"""

import os
import pytest
from datetime import datetime, timedelta
from typing import Optional

from core.intelligence.confidence_drift import (
    ConfidenceRecord,
    DriftAnalysis,
    DriftAlert,
    DriftSeverity,
    DriftDirection
)
from core.intelligence.drift_storage import PostgresDriftStorage


# Test configuration from environment
TEST_CONFIG = {
    'host': os.getenv('POSTGRES_TEST_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_TEST_PORT', '5432')),
    'database': os.getenv('POSTGRES_TEST_DB', 'crossbridge_test'),
    'user': os.getenv('POSTGRES_TEST_USER', 'crossbridge'),
    'password': os.getenv('POSTGRES_TEST_PASSWORD', 'test'),
    'schema': 'drift_test'
}


def check_postgres_available() -> bool:
    """Check if PostgreSQL is available for testing."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=TEST_CONFIG['host'],
            port=TEST_CONFIG['port'],
            database=TEST_CONFIG['database'],
            user=TEST_CONFIG['user'],
            password=TEST_CONFIG['password'],
            connect_timeout=3
        )
        conn.close()
        return True
    except Exception:
        return False


# Skip all tests if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    not check_postgres_available(),
    reason="PostgreSQL not available. Set POSTGRES_TEST_* env vars or run with Docker."
)


@pytest.fixture
def storage():
    """Create PostgreSQL storage backend for testing."""
    storage = PostgresDriftStorage(**TEST_CONFIG)
    
    # Initialize schema
    assert storage.initialize(), "Failed to initialize PostgreSQL storage"
    
    yield storage
    
    # Cleanup: Drop test schema
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP SCHEMA IF EXISTS {TEST_CONFIG['schema']} CASCADE")
            conn.commit()
    except Exception as e:
        print(f"Cleanup warning: {e}")


class TestPostgresInitialization:
    """Test PostgreSQL storage initialization."""
    
    def test_initialize_creates_schema(self, storage):
        """Test that initialization creates the schema."""
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s
            """, (TEST_CONFIG['schema'],))
            
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == TEST_CONFIG['schema']
    
    def test_initialize_creates_tables(self, storage):
        """Test that initialization creates all required tables."""
        expected_tables = [
            'confidence_measurements',
            'drift_analysis',
            'drift_alerts',
            'drift_metadata'
        ]
        
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (TEST_CONFIG['schema'],))
            
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} not created"
    
    def test_initialize_creates_indexes(self, storage):
        """Test that initialization creates indexes."""
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = %s
            """, (TEST_CONFIG['schema'],))
            
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Check for some key indexes
            assert any('test_name' in idx or 'test' in idx for idx in indexes)
            assert any('timestamp' in idx for idx in indexes)
            assert any('severity' in idx for idx in indexes)


class TestPostgresMeasurements:
    """Test confidence measurement storage and retrieval."""
    
    def test_store_single_measurement(self, storage):
        """Test storing a single measurement."""
        measurement_id = storage.store_measurement(
            test_name="test_login",
            confidence=0.85,
            category="authentication",
            timestamp=datetime.utcnow(),
            failure_id="F-123",
            rule_score=0.80,
            signal_score=0.90
        )
        
        assert measurement_id > 0
    
    def test_store_bulk_measurements(self, storage):
        """Test bulk measurement insert."""
        now = datetime.utcnow()
        records = [
            ConfidenceRecord(
                test_name=f"test_{i}",
                confidence=0.5 + (i * 0.1),
                category="category_a",
                timestamp=now - timedelta(hours=i)
            )
            for i in range(10)
        ]
        
        count = storage.store_measurements_bulk(records)
        assert count == 10
    
    def test_get_measurements_all(self, storage):
        """Test retrieving all measurements."""
        # Store some measurements
        now = datetime.utcnow()
        for i in range(5):
            storage.store_measurement(
                test_name=f"test_{i}",
                confidence=0.7,
                category="test_category",
                timestamp=now - timedelta(hours=i)
            )
        
        # Retrieve all
        measurements = storage.get_measurements(limit=100)
        assert len(measurements) >= 5
    
    def test_get_measurements_by_test_name(self, storage):
        """Test filtering by test name."""
        now = datetime.utcnow()
        
        storage.store_measurement("test_specific", 0.8, "cat1", now)
        storage.store_measurement("test_other", 0.7, "cat1", now)
        storage.store_measurement("test_specific", 0.9, "cat1", now - timedelta(hours=1))
        
        measurements = storage.get_measurements(test_name="test_specific")
        
        assert len(measurements) == 2
        assert all(m.test_name == "test_specific" for m in measurements)
    
    def test_get_measurements_by_category(self, storage):
        """Test filtering by category."""
        now = datetime.utcnow()
        
        storage.store_measurement("test_1", 0.8, "cat_specific", now)
        storage.store_measurement("test_2", 0.7, "cat_other", now)
        storage.store_measurement("test_3", 0.9, "cat_specific", now)
        
        measurements = storage.get_measurements(category="cat_specific")
        
        assert len(measurements) == 2
        assert all(m.category == "cat_specific" for m in measurements)
    
    def test_get_measurements_by_time_range(self, storage):
        """Test filtering by time range."""
        now = datetime.utcnow()
        
        # Store measurements at different times
        storage.store_measurement("test_1", 0.8, "cat", now - timedelta(days=10))
        storage.store_measurement("test_2", 0.7, "cat", now - timedelta(days=5))
        storage.store_measurement("test_3", 0.9, "cat", now - timedelta(days=1))
        
        # Query last 3 days
        since = now - timedelta(days=3)
        measurements = storage.get_measurements(since=since)
        
        assert len(measurements) == 1
        assert measurements[0].test_name == "test_3"
    
    def test_get_test_history(self, storage):
        """Test getting history for specific test."""
        now = datetime.utcnow()
        test_name = "test_history"
        
        # Store measurements over 40 days
        for i in range(40):
            storage.store_measurement(
                test_name=test_name,
                confidence=0.5 + (i * 0.01),
                category="history_test",
                timestamp=now - timedelta(days=i)
            )
        
        # Get last 30 days
        history = storage.get_test_history(test_name, window=timedelta(days=30))
        
        assert len(history) == 30
        assert all(m.test_name == test_name for m in history)
    
    def test_measurement_uniqueness_constraint(self, storage):
        """Test that duplicate (test_name, timestamp) is handled."""
        now = datetime.utcnow()
        
        # First insert
        storage.store_measurement("test_unique", 0.8, "cat", now)
        
        # Second insert with same test_name and timestamp (should update)
        storage.store_measurement("test_unique", 0.9, "cat", now)
        
        measurements = storage.get_measurements(test_name="test_unique")
        
        # Should have only one measurement with updated confidence
        assert len(measurements) == 1
        assert measurements[0].confidence == 0.9


class TestPostgresDriftAnalysis:
    """Test drift analysis caching."""
    
    def test_store_drift_analysis(self, storage):
        """Test storing drift analysis."""
        analysis = DriftAnalysis(
            test_name="test_analysis",
            current_confidence=0.75,
            baseline_confidence=0.85,
            drift_percentage=-0.12,
            drift_absolute=-0.10,
            severity=DriftSeverity.MODERATE,
            direction=DriftDirection.DECREASING,
            is_drifting=True,
            measurements_count=20,
            time_span=timedelta(days=7),
            trend="decreasing",
            recommendations=["Review test", "Check for changes"],
            timestamp=datetime.utcnow()
        )
        
        analysis_id = storage.store_drift_analysis("test_analysis", analysis)
        assert analysis_id > 0
    
    def test_get_latest_analysis(self, storage):
        """Test retrieving latest analysis."""
        test_name = "test_latest"
        
        # Store multiple analyses
        for i in range(3):
            analysis = DriftAnalysis(
                test_name=test_name,
                current_confidence=0.7 + (i * 0.05),
                baseline_confidence=0.85,
                drift_percentage=-0.10,
                drift_absolute=-0.10,
                severity=DriftSeverity.LOW,
                direction=DriftDirection.STABLE,
                is_drifting=False,
                measurements_count=10,
                time_span=timedelta(days=7),
                trend="stable",
                recommendations=[],
                timestamp=datetime.utcnow() - timedelta(hours=i)
            )
            storage.store_drift_analysis(test_name, analysis)
        
        # Get latest
        latest = storage.get_latest_analysis(test_name)
        
        assert latest is not None
        assert latest.test_name == test_name
        # Latest should have highest confidence (most recent)
        assert latest.current_confidence == pytest.approx(0.70, abs=0.01)


class TestPostgresDriftAlerts:
    """Test drift alert storage and retrieval."""
    
    def test_store_alert(self, storage):
        """Test storing an alert."""
        alert = DriftAlert(
            test_name="test_alert",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.25,
            message="High drift detected",
            recommendations=["Investigate immediately"],
            timestamp=datetime.utcnow()
        )
        
        alert_id = storage.store_alert(alert)
        assert alert_id > 0
    
    def test_get_alerts_all(self, storage):
        """Test retrieving all alerts."""
        # Store multiple alerts
        for i in range(3):
            alert = DriftAlert(
                test_name=f"test_{i}",
                severity=DriftSeverity.MODERATE,
                drift_percentage=0.15,
                message=f"Alert {i}",
                recommendations=[],
                timestamp=datetime.utcnow()
            )
            storage.store_alert(alert)
        
        alerts = storage.get_alerts()
        assert len(alerts) >= 3
    
    def test_get_alerts_by_severity(self, storage):
        """Test filtering alerts by severity."""
        now = datetime.utcnow()
        
        # Store alerts with different severities
        for severity in [DriftSeverity.LOW, DriftSeverity.MODERATE, DriftSeverity.HIGH]:
            alert = DriftAlert(
                test_name="test_severity",
                severity=severity,
                drift_percentage=0.10,
                message=f"{severity.value} alert",
                recommendations=[],
                timestamp=now
            )
            storage.store_alert(alert)
        
        # Get high severity and above
        high_alerts = storage.get_alerts(min_severity=DriftSeverity.HIGH)
        
        assert len(high_alerts) >= 1
        assert all(a['severity'].value in ['high', 'critical'] for a in high_alerts)
    
    def test_get_alerts_by_acknowledgment(self, storage):
        """Test filtering by acknowledgment status."""
        now = datetime.utcnow()
        
        # Store two alerts
        alert1 = DriftAlert("test_1", DriftSeverity.MODERATE, 0.15, "Alert 1", [], now)
        alert2 = DriftAlert("test_2", DriftSeverity.MODERATE, 0.15, "Alert 2", [], now)
        
        id1 = storage.store_alert(alert1)
        id2 = storage.store_alert(alert2)
        
        # Acknowledge first alert
        storage.acknowledge_alert(id1, "test_user")
        
        # Get unacknowledged alerts
        unacked = storage.get_alerts(acknowledged=False)
        
        unacked_ids = [a['id'] for a in unacked]
        assert id2 in unacked_ids
        assert id1 not in unacked_ids
    
    def test_acknowledge_alert(self, storage):
        """Test acknowledging an alert."""
        alert = DriftAlert(
            test_name="test_ack",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.25,
            message="Test alert",
            recommendations=[],
            timestamp=datetime.utcnow()
        )
        
        alert_id = storage.store_alert(alert)
        
        # Acknowledge
        success = storage.acknowledge_alert(alert_id, "test_user")
        assert success
        
        # Verify acknowledgment
        alerts = storage.get_alerts(test_name="test_ack")
        assert len(alerts) == 1
        assert alerts[0]['acknowledged'] is True
        assert alerts[0]['acknowledged_by'] == "test_user"
        assert alerts[0]['acknowledged_at'] is not None


class TestPostgresStatistics:
    """Test statistics and aggregation queries."""
    
    def test_get_drift_statistics(self, storage):
        """Test getting drift statistics."""
        now = datetime.utcnow()
        
        # Store measurements
        for i in range(10):
            storage.store_measurement(
                test_name=f"test_{i}",
                confidence=0.5 + (i * 0.05),
                category="stats_test",
                timestamp=now
            )
        
        stats = storage.get_drift_statistics(category="stats_test")
        
        assert stats['total_tests'] == 10
        assert stats['total_measurements'] == 10
        assert stats['avg_confidence'] is not None
        assert stats['min_confidence'] is not None
        assert stats['max_confidence'] is not None


class TestPostgresMaintenance:
    """Test maintenance operations."""
    
    def test_cleanup_old_data(self, storage):
        """Test cleanup of old data."""
        now = datetime.utcnow()
        
        # Store old measurements
        for i in range(5):
            storage.store_measurement(
                test_name=f"old_test_{i}",
                confidence=0.8,
                category="cleanup_test",
                timestamp=now - timedelta(days=100)
            )
        
        # Store recent measurements
        for i in range(5):
            storage.store_measurement(
                test_name=f"new_test_{i}",
                confidence=0.8,
                category="cleanup_test",
                timestamp=now
            )
        
        # Cleanup (keep 90 days)
        deleted = storage.cleanup_old_data(measurements_days=90)
        
        assert deleted['measurements'] == 5
        
        # Verify only recent measurements remain
        measurements = storage.get_measurements(category="cleanup_test")
        assert all('new_test' in m.test_name for m in measurements)
    
    def test_vacuum(self, storage):
        """Test database vacuum operation."""
        # Should not raise exception
        success = storage.vacuum()
        assert success is True
    
    def test_get_database_size(self, storage):
        """Test getting database size."""
        size = storage.get_database_size()
        
        # Should return a positive number (bytes)
        assert size > 0
    
    def test_export_to_json(self, storage, tmp_path):
        """Test JSON export."""
        now = datetime.utcnow()
        
        # Store some data
        storage.store_measurement("test_export", 0.85, "export_cat", now)
        
        # Export
        output_file = tmp_path / "export.json"
        success = storage.export_to_json(str(output_file))
        
        assert success
        assert output_file.exists()
        
        # Verify JSON content
        import json
        with open(output_file) as f:
            data = json.load(f)
        
        assert 'measurements' in data
        assert len(data['measurements']) >= 1


class TestPostgresConnectionPooling:
    """Test connection pooling behavior."""
    
    def test_concurrent_connections(self, storage):
        """Test that connection pool handles concurrent access."""
        import concurrent.futures
        
        def write_measurement(i):
            storage.store_measurement(
                test_name=f"concurrent_{i}",
                confidence=0.8,
                category="concurrent_test",
                timestamp=datetime.utcnow()
            )
            return i
        
        # Execute concurrent writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_measurement, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 20
        
        # Verify all measurements were stored
        measurements = storage.get_measurements(category="concurrent_test")
        assert len(measurements) == 20


class TestPostgresPerformance:
    """Performance-related tests."""
    
    def test_bulk_insert_performance(self, storage):
        """Test bulk insert is efficient."""
        import time
        
        now = datetime.utcnow()
        records = [
            ConfidenceRecord(
                test_name=f"perf_test_{i}",
                confidence=0.7,
                category="performance",
                timestamp=now - timedelta(hours=i)
            )
            for i in range(1000)
        ]
        
        start = time.time()
        count = storage.store_measurements_bulk(records)
        duration = time.time() - start
        
        assert count == 1000
        # Should complete in reasonable time (< 5 seconds)
        assert duration < 5.0, f"Bulk insert took {duration:.2f}s (should be < 5s)"
    
    def test_indexed_query_performance(self, storage):
        """Test that indexed queries are fast."""
        import time
        
        now = datetime.utcnow()
        
        # Insert data
        for i in range(100):
            storage.store_measurement(
                f"test_{i % 10}",
                0.7,
                "perf_category",
                now - timedelta(hours=i)
            )
        
        # Query by test_name (indexed)
        start = time.time()
        measurements = storage.get_measurements(test_name="test_5")
        duration = time.time() - start
        
        assert len(measurements) == 10
        # Should be fast with index (< 0.5 seconds)
        assert duration < 0.5, f"Query took {duration:.3f}s (should be < 0.5s)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
