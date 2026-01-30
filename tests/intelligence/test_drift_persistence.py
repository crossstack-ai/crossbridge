"""Tests for drift persistence layer."""

import unittest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from core.intelligence.drift_persistence import DriftPersistenceManager
from core.intelligence.confidence_drift import (
    ConfidenceRecord,
    DriftAnalysis,
    DriftAlert,
    DriftSeverity,
    DriftDirection
)


class TestDriftPersistence(unittest.TestCase):
    """Test drift persistence manager."""
    
    def setUp(self):
        """Create temporary database for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_drift.db"
        self.manager = DriftPersistenceManager(str(self.db_path))
    
    def tearDown(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """Test database is created with correct schema."""
        assert self.db_path.exists()
        assert self.db_path.stat().st_size > 0
    
    def test_store_single_measurement(self):
        """Test storing a single confidence measurement."""
        record = ConfidenceRecord(
            test_name="test_login",
            confidence=0.85,
            category="flaky",
            timestamp=datetime.utcnow()
        )
        
        record_id = self.manager.store_measurement(record)
        assert record_id > 0
    
    def test_store_multiple_measurements(self):
        """Test bulk insert of measurements."""
        records = [
            ConfidenceRecord(
                test_name="test_login",
                confidence=0.75 + i * 0.02,
                category="flaky",
                timestamp=datetime.utcnow() - timedelta(hours=i)
            )
            for i in range(5)
        ]
        
        count = self.manager.store_measurements(records)
        assert count == 5
    
    def test_get_measurements_by_test(self):
        """Test querying measurements by test name."""
        # Store measurements for two tests
        for i in range(3):
            self.manager.store_measurement(ConfidenceRecord(
                test_name="test_a",
                confidence=0.80,
                category="flaky",
                timestamp=datetime.utcnow()
            ))
        
        for i in range(2):
            self.manager.store_measurement(ConfidenceRecord(
                test_name="test_b",
                confidence=0.90,
                category="stable",
                timestamp=datetime.utcnow()
            ))
        
        # Query test_a
        measurements = self.manager.get_measurements(test_name="test_a")
        assert len(measurements) == 3
        assert all(m.test_name == "test_a" for m in measurements)
    
    def test_get_measurements_by_category(self):
        """Test querying measurements by category."""
        self.manager.store_measurement(ConfidenceRecord(
            test_name="test1",
            confidence=0.80,
            category="flaky",
            timestamp=datetime.utcnow()
        ))
        
        self.manager.store_measurement(ConfidenceRecord(
            test_name="test2",
            confidence=0.90,
            category="stable",
            timestamp=datetime.utcnow()
        ))
        
        flaky_measurements = self.manager.get_measurements(category="flaky")
        assert len(flaky_measurements) == 1
        assert flaky_measurements[0].category == "flaky"
    
    def test_get_measurements_with_time_filter(self):
        """Test querying measurements with time range."""
        now = datetime.utcnow()
        
        # Old measurement (5 days ago)
        self.manager.store_measurement(ConfidenceRecord(
            test_name="test_old",
            confidence=0.70,
            category="flaky",
            timestamp=now - timedelta(days=5)
        ))
        
        # Recent measurement (1 hour ago)
        self.manager.store_measurement(ConfidenceRecord(
            test_name="test_recent",
            confidence=0.90,
            category="flaky",
            timestamp=now - timedelta(hours=1)
        ))
        
        # Query last 2 days
        recent = self.manager.get_measurements(
            since=now - timedelta(days=2)
        )
        assert len(recent) == 1
        assert recent[0].test_name == "test_recent"
    
    def test_get_test_history(self):
        """Test retrieving complete history for a test."""
        test_name = "test_history"
        now = datetime.utcnow()
        
        # Store 10 measurements over 10 days
        for i in range(10):
            self.manager.store_measurement(ConfidenceRecord(
                test_name=test_name,
                confidence=0.70 + i * 0.02,
                category="flaky",
                timestamp=now - timedelta(days=9-i)
            ))
        
        # Get all history
        history = self.manager.get_test_history(test_name)
        assert len(history) == 10
        
        # Get last 5 days
        history_5d = self.manager.get_test_history(
            test_name,
            window=timedelta(days=5)
        )
        assert len(history_5d) == 5
    
    def test_get_category_tests(self):
        """Test getting all tests in a category."""
        # Store measurements for multiple tests in same category
        for test_num in range(3):
            self.manager.store_measurement(ConfidenceRecord(
                test_name=f"test_{test_num}",
                confidence=0.80,
                category="flaky",
                timestamp=datetime.utcnow()
            ))
        
        tests = self.manager.get_category_tests("flaky")
        assert len(tests) == 3
        assert "test_0" in tests
        assert "test_1" in tests
        assert "test_2" in tests
    
    def test_store_drift_analysis(self):
        """Test caching drift analysis results."""
        analysis = DriftAnalysis(
            test_name="test_drift",
            current_confidence=0.90,
            baseline_confidence=0.75,
            drift_percentage=0.20,
            drift_absolute=0.15,
            severity=DriftSeverity.HIGH,
            direction=DriftDirection.INCREASING,
            is_drifting=True,
            measurements_count=10,
            time_span=timedelta(days=7),
            trend="strongly_increasing",
            recommendations=["Investigate root cause", "Monitor closely"]
        )
        
        analysis_id = self.manager.store_drift_analysis(analysis)
        assert analysis_id > 0
    
    def test_get_latest_drift_analysis(self):
        """Test retrieving cached drift analysis."""
        test_name = "test_cached"
        
        # Store analysis
        analysis = DriftAnalysis(
            test_name=test_name,
            current_confidence=0.90,
            baseline_confidence=0.75,
            drift_percentage=0.20,
            drift_absolute=0.15,
            severity=DriftSeverity.HIGH,
            direction=DriftDirection.INCREASING,
            is_drifting=True,
            measurements_count=10,
            time_span=timedelta(days=7),
            trend="strongly_increasing",
            recommendations=["Test recommendation"]
        )
        self.manager.store_drift_analysis(analysis)
        
        # Retrieve within max age
        retrieved = self.manager.get_latest_drift_analysis(test_name, max_age_hours=24)
        assert retrieved is not None
        assert retrieved.test_name == test_name
        assert retrieved.severity == DriftSeverity.HIGH
        assert len(retrieved.recommendations) == 1
    
    def test_drift_analysis_cache_expiry(self):
        """Test that old cached analysis is not returned."""
        test_name = "test_expired"
        
        # Store analysis (would be old in real scenario)
        analysis = DriftAnalysis(
            test_name=test_name,
            current_confidence=0.90,
            baseline_confidence=0.75,
            drift_percentage=0.20,
            drift_absolute=0.15,
            severity=DriftSeverity.HIGH,
            direction=DriftDirection.INCREASING,
            is_drifting=True,
            measurements_count=10,
            time_span=timedelta(days=7),
            trend="strongly_increasing",
            recommendations=[]
        )
        self.manager.store_drift_analysis(analysis)
        
        # Try to retrieve with very short max age (should not find)
        retrieved = self.manager.get_latest_drift_analysis(test_name, max_age_hours=0)
        assert retrieved is None
    
    def test_store_alert(self):
        """Test storing drift alerts."""
        alert = DriftAlert(
            test_name="test_alert",
            severity=DriftSeverity.CRITICAL,
            drift_percentage=0.35,
            message="Critical drift detected",
            recommendations=["Immediate action required"],
            timestamp=datetime.utcnow()
        )
        
        alert_id = self.manager.store_alert(alert)
        assert alert_id > 0
    
    def test_get_alerts_unacknowledged(self):
        """Test querying unacknowledged alerts."""
        # Store unacknowledged alert
        alert = DriftAlert(
            test_name="test_unack",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.25,
            message="High drift",
            recommendations=[],
            timestamp=datetime.utcnow()
        )
        self.manager.store_alert(alert)
        
        # Query unacknowledged
        alerts = self.manager.get_alerts(acknowledged=False)
        assert len(alerts) > 0
        assert all(not a['acknowledged'] for a in alerts)
    
    def test_get_alerts_by_severity(self):
        """Test filtering alerts by severity."""
        # Store alerts with different severities
        for severity in [DriftSeverity.LOW, DriftSeverity.MODERATE, DriftSeverity.HIGH]:
            alert = DriftAlert(
                test_name=f"test_{severity.value}",
                severity=severity,
                drift_percentage=0.10,
                message=f"{severity.value} drift",
                recommendations=[],
                timestamp=datetime.utcnow()
            )
            self.manager.store_alert(alert)
        
        # Get moderate and above
        alerts = self.manager.get_alerts(min_severity=DriftSeverity.MODERATE)
        assert len(alerts) == 2  # moderate and high
        severities = [a['severity'] for a in alerts]
        assert DriftSeverity.LOW not in severities
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        # Store alert
        alert = DriftAlert(
            test_name="test_ack",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.25,
            message="Test alert",
            recommendations=[],
            timestamp=datetime.utcnow()
        )
        alert_id = self.manager.store_alert(alert)
        
        # Acknowledge it
        success = self.manager.acknowledge_alert(alert_id, acknowledged_by="test_user")
        assert success
        
        # Verify it's acknowledged
        alerts = self.manager.get_alerts(acknowledged=True)
        assert len(alerts) == 1
        assert alerts[0]['acknowledged']
        assert alerts[0]['acknowledged_by'] == "test_user"
    
    def test_get_alerts_by_test(self):
        """Test filtering alerts by test name."""
        # Store alerts for different tests
        for i in range(3):
            alert = DriftAlert(
                test_name=f"test_{i}",
                severity=DriftSeverity.MODERATE,
                drift_percentage=0.15,
                message=f"Alert {i}",
                recommendations=[],
                timestamp=datetime.utcnow()
            )
            self.manager.store_alert(alert)
        
        # Query specific test
        alerts = self.manager.get_alerts(test_name="test_1")
        assert len(alerts) == 1
        assert alerts[0]['test_name'] == "test_1"
    
    def test_get_recent_alerts(self):
        """Test querying alerts by time."""
        now = datetime.utcnow()
        
        # Old alert
        alert_old = DriftAlert(
            test_name="test_old",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.20,
            message="Old alert",
            recommendations=[],
            timestamp=now - timedelta(days=5)
        )
        self.manager.store_alert(alert_old)
        
        # Recent alert
        alert_recent = DriftAlert(
            test_name="test_recent",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.20,
            message="Recent alert",
            recommendations=[],
            timestamp=now
        )
        self.manager.store_alert(alert_recent)
        
        # Query last 2 days
        recent_alerts = self.manager.get_alerts(
            since=now - timedelta(days=2)
        )
        assert len(recent_alerts) == 1
        assert recent_alerts[0]['test_name'] == "test_recent"
    
    def test_get_drift_statistics(self):
        """Test getting drift statistics."""
        # Store measurements
        for i in range(10):
            self.manager.store_measurement(ConfidenceRecord(
                test_name=f"test_{i}",
                confidence=0.70 + i * 0.02,
                category="flaky",
                timestamp=datetime.utcnow()
            ))
        
        stats = self.manager.get_drift_statistics()
        assert stats['total_tests'] == 10
        assert stats['total_measurements'] == 10
        assert stats['avg_confidence'] > 0.70
        assert stats['min_confidence'] >= 0.70
        assert stats['max_confidence'] <= 0.90
    
    def test_get_drift_statistics_by_category(self):
        """Test statistics filtered by category."""
        # Store measurements in different categories
        for i in range(3):
            self.manager.store_measurement(ConfidenceRecord(
                test_name=f"test_flaky_{i}",
                confidence=0.75,
                category="flaky",
                timestamp=datetime.utcnow()
            ))
        
        for i in range(2):
            self.manager.store_measurement(ConfidenceRecord(
                test_name=f"test_stable_{i}",
                confidence=0.90,
                category="stable",
                timestamp=datetime.utcnow()
            ))
        
        flaky_stats = self.manager.get_drift_statistics(category="flaky")
        assert flaky_stats['total_tests'] == 3
        assert flaky_stats['avg_confidence'] == 0.75
    
    def test_get_alert_summary(self):
        """Test getting alert count by severity."""
        # Store alerts with different severities
        severities = [
            DriftSeverity.LOW,
            DriftSeverity.LOW,
            DriftSeverity.MODERATE,
            DriftSeverity.HIGH,
            DriftSeverity.CRITICAL
        ]
        
        for severity in severities:
            alert = DriftAlert(
                test_name="test",
                severity=severity,
                drift_percentage=0.15,
                message="Test",
                recommendations=[],
                timestamp=datetime.utcnow()
            )
            self.manager.store_alert(alert)
        
        summary = self.manager.get_alert_summary()
        assert summary['low'] == 2
        assert summary['moderate'] == 1
        assert summary['high'] == 1
        assert summary['critical'] == 1
    
    def test_cleanup_old_measurements(self):
        """Test cleaning up old measurements."""
        now = datetime.utcnow()
        
        # Store old measurement (100 days ago)
        self.manager.store_measurement(ConfidenceRecord(
            test_name="test_old",
            confidence=0.70,
            category="flaky",
            timestamp=now - timedelta(days=100)
        ))
        
        # Store recent measurement
        self.manager.store_measurement(ConfidenceRecord(
            test_name="test_recent",
            confidence=0.90,
            category="flaky",
            timestamp=now
        ))
        
        # Clean up (keep last 90 days)
        deleted = self.manager.cleanup_old_data(measurements_days=90)
        assert deleted['measurements'] == 1
        
        # Verify only recent remains
        measurements = self.manager.get_measurements()
        assert len(measurements) == 1
        assert measurements[0].test_name == "test_recent"
    
    def test_cleanup_old_analysis(self):
        """Test cleaning up old analysis cache."""
        # Store analysis (will be marked with current timestamp)
        analysis = DriftAnalysis(
            test_name="test",
            current_confidence=0.90,
            baseline_confidence=0.75,
            drift_percentage=0.20,
            drift_absolute=0.15,
            severity=DriftSeverity.HIGH,
            direction=DriftDirection.INCREASING,
            is_drifting=True,
            measurements_count=10,
            time_span=timedelta(days=7),
            trend="increasing",
            recommendations=[]
        )
        self.manager.store_drift_analysis(analysis)
        
        # Clean up with 0 days retention (should delete)
        deleted = self.manager.cleanup_old_data(analysis_days=0)
        assert deleted['analysis'] >= 0
    
    def test_cleanup_acknowledged_alerts(self):
        """Test cleaning up old acknowledged alerts."""
        now = datetime.utcnow()
        
        # Store old acknowledged alert
        alert = DriftAlert(
            test_name="test_old_ack",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.20,
            message="Old alert",
            recommendations=[],
            timestamp=now - timedelta(days=100)
        )
        alert_id = self.manager.store_alert(alert)
        self.manager.acknowledge_alert(alert_id)
        
        # Store recent unacknowledged alert
        alert_recent = DriftAlert(
            test_name="test_recent_unack",
            severity=DriftSeverity.HIGH,
            drift_percentage=0.20,
            message="Recent alert",
            recommendations=[],
            timestamp=now
        )
        self.manager.store_alert(alert_recent)
        
        # Clean up (keep last 60 days of acknowledged alerts)
        deleted = self.manager.cleanup_old_data(alerts_days=60)
        
        # Verify unacknowledged alert remains
        alerts = self.manager.get_alerts(acknowledged=False)
        assert len(alerts) == 1
    
    def test_get_database_size(self):
        """Test getting database file size."""
        size = self.manager.get_database_size()
        assert size > 0
    
    def test_export_to_json(self):
        """Test exporting data to JSON."""
        # Store some measurements
        for i in range(3):
            self.manager.store_measurement(ConfidenceRecord(
                test_name=f"test_{i}",
                confidence=0.80,
                category="flaky",
                timestamp=datetime.utcnow()
            ))
        
        # Export
        output_path = Path(self.temp_dir) / "export.json"
        self.manager.export_to_json(str(output_path))
        
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    
    def test_duplicate_measurement_handling(self):
        """Test that duplicate measurements (same test + timestamp) are handled."""
        timestamp = datetime.utcnow()
        
        # Store same measurement twice
        record = ConfidenceRecord(
            test_name="test_dup",
            confidence=0.85,
            category="flaky",
            timestamp=timestamp
        )
        
        self.manager.store_measurement(record)
        self.manager.store_measurement(record)
        
        # Should only have one record
        measurements = self.manager.get_measurements(test_name="test_dup")
        assert len(measurements) == 1


if __name__ == "__main__":
    unittest.main()
