"""
Persistence Layer for Confidence Drift Detection

This module provides database persistence for drift tracking:
- Store confidence measurements in SQLite
- Query historical drift data
- Support for trend analysis over extended periods
- Efficient storage with automatic cleanup

Design Principles:
- Lightweight SQLite storage (no external dependencies)
- Automatic schema creation
- Thread-safe operations
- Configurable retention policies
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict
from contextlib import contextmanager
import json

from core.intelligence.confidence_drift import (
    ConfidenceRecord,
    DriftAnalysis,
    DriftAlert,
    DriftSeverity,
    DriftDirection
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

SCHEMA_VERSION = 1

CREATE_TABLES_SQL = """
-- Confidence measurements table
CREATE TABLE IF NOT EXISTS confidence_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    category TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    failure_id TEXT,
    rule_score REAL,
    signal_score REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_name, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_test_name ON confidence_measurements(test_name);
CREATE INDEX IF NOT EXISTS idx_category ON confidence_measurements(category);
CREATE INDEX IF NOT EXISTS idx_timestamp ON confidence_measurements(timestamp);

-- Drift analysis cache (for performance)
CREATE TABLE IF NOT EXISTS drift_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    baseline_confidence REAL NOT NULL,
    current_confidence REAL NOT NULL,
    drift_percentage REAL NOT NULL,
    drift_absolute REAL NOT NULL,
    severity TEXT NOT NULL,
    direction TEXT NOT NULL,
    trend TEXT NOT NULL,
    measurements_count INTEGER NOT NULL,
    time_span_seconds REAL NOT NULL,
    recommendations TEXT NOT NULL,  -- JSON array
    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_drift_test ON drift_analysis(test_name);
CREATE INDEX IF NOT EXISTS idx_drift_severity ON drift_analysis(severity);
CREATE INDEX IF NOT EXISTS idx_drift_analyzed ON drift_analysis(analyzed_at);

-- Drift alerts table
CREATE TABLE IF NOT EXISTS drift_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    drift_percentage REAL NOT NULL,
    message TEXT NOT NULL,
    recommendations TEXT NOT NULL,  -- JSON array
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_at TEXT,
    acknowledged_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_alert_test ON drift_alerts(test_name);
CREATE INDEX IF NOT EXISTS idx_alert_severity ON drift_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alert_created ON drift_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alert_ack ON drift_alerts(acknowledged);

-- Metadata table for versioning and configuration
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1');
INSERT OR IGNORE INTO metadata (key, value) VALUES ('created_at', datetime('now'));
"""


# ============================================================================
# PERSISTENCE MANAGER
# ============================================================================

class DriftPersistenceManager:
    """
    Manages persistence of confidence drift data.
    
    Features:
    - Store confidence measurements
    - Cache drift analysis results
    - Track drift alerts
    - Query historical data
    - Automatic cleanup
    """
    
    def __init__(self, db_path: str = "data/drift_tracking.db"):
        """
        Initialize persistence manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
        logger.info(f"Drift persistence initialized: {self.db_path}")
    
    def _initialize_database(self):
        """Create database schema if needed."""
        with self._get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ========================================================================
    # CONFIDENCE MEASUREMENTS
    # ========================================================================
    
    def store_measurement(self, record: ConfidenceRecord) -> int:
        """
        Store a confidence measurement.
        
        Args:
            record: ConfidenceRecord to store
            
        Returns:
            Record ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO confidence_measurements
                (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.test_name,
                    record.confidence,
                    record.category,
                    record.timestamp.isoformat(),
                    record.failure_id,
                    record.rule_score,
                    record.signal_score
                )
            )
            conn.commit()
            return cursor.lastrowid
    
    def store_measurements(self, records: List[ConfidenceRecord]) -> int:
        """
        Store multiple confidence measurements (bulk insert).
        
        Args:
            records: List of ConfidenceRecord objects
            
        Returns:
            Number of records inserted
        """
        with self._get_connection() as conn:
            data = [
                (
                    r.test_name,
                    r.confidence,
                    r.category,
                    r.timestamp.isoformat(),
                    r.failure_id,
                    r.rule_score,
                    r.signal_score
                )
                for r in records
            ]
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO confidence_measurements
                (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            conn.commit()
            return cursor.rowcount
    
    def get_measurements(
        self,
        test_name: Optional[str] = None,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[ConfidenceRecord]:
        """
        Query confidence measurements.
        
        Args:
            test_name: Filter by test name
            category: Filter by category
            since: Filter by start timestamp
            until: Filter by end timestamp
            limit: Maximum number of records
            
        Returns:
            List of ConfidenceRecord objects
        """
        query = "SELECT * FROM confidence_measurements WHERE 1=1"
        params = []
        
        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
        
        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        return [
            ConfidenceRecord(
                test_name=row['test_name'],
                confidence=row['confidence'],
                category=row['category'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                failure_id=row['failure_id'],
                rule_score=row['rule_score'],
                signal_score=row['signal_score']
            )
            for row in rows
        ]
    
    def get_test_history(
        self,
        test_name: str,
        window: Optional[timedelta] = None
    ) -> List[ConfidenceRecord]:
        """
        Get confidence history for a specific test.
        
        Args:
            test_name: Test name
            window: Time window (e.g., timedelta(days=30))
            
        Returns:
            List of ConfidenceRecord objects, ordered by timestamp
        """
        since = None
        if window:
            since = datetime.utcnow() - window
        
        return self.get_measurements(test_name=test_name, since=since)
    
    def get_category_tests(self, category: str) -> List[str]:
        """
        Get all test names in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of test names
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT test_name FROM confidence_measurements WHERE category = ?",
                (category,)
            )
            return [row['test_name'] for row in cursor.fetchall()]
    
    # ========================================================================
    # DRIFT ANALYSIS CACHE
    # ========================================================================
    
    def store_drift_analysis(self, analysis: DriftAnalysis) -> int:
        """
        Store drift analysis result (for caching).
        
        Args:
            analysis: DriftAnalysis object
            
        Returns:
            Record ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO drift_analysis
                (test_name, baseline_confidence, current_confidence, drift_percentage,
                 drift_absolute, severity, direction, trend, measurements_count,
                 time_span_seconds, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis.test_name,
                    analysis.baseline_confidence,
                    analysis.current_confidence,
                    analysis.drift_percentage,
                    analysis.drift_absolute,
                    analysis.severity.value,
                    analysis.direction.value,
                    analysis.trend,
                    analysis.measurements_count,
                    analysis.time_span.total_seconds(),
                    json.dumps(analysis.recommendations)
                )
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_latest_drift_analysis(
        self,
        test_name: str,
        max_age_hours: int = 24
    ) -> Optional[DriftAnalysis]:
        """
        Get most recent drift analysis for a test.
        
        Args:
            test_name: Test name
            max_age_hours: Maximum age of cached analysis
            
        Returns:
            DriftAnalysis if found and fresh, None otherwise
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM drift_analysis
                WHERE test_name = ? AND analyzed_at >= ?
                ORDER BY analyzed_at DESC
                LIMIT 1
                """,
                (test_name, cutoff.isoformat())
            )
            row = cursor.fetchone()
        
        if not row:
            return None
        
        return DriftAnalysis(
            test_name=row['test_name'],
            current_confidence=row['current_confidence'],
            baseline_confidence=row['baseline_confidence'],
            drift_percentage=row['drift_percentage'],
            drift_absolute=row['drift_absolute'],
            severity=DriftSeverity(row['severity']),
            direction=DriftDirection(row['direction']),
            is_drifting=row['drift_percentage'] >= 0.05,
            measurements_count=row['measurements_count'],
            time_span=timedelta(seconds=row['time_span_seconds']),
            trend=row['trend'],
            recommendations=json.loads(row['recommendations']),
            timestamp=datetime.fromisoformat(row['analyzed_at'])
        )
    
    # ========================================================================
    # DRIFT ALERTS
    # ========================================================================
    
    def store_alert(self, alert: DriftAlert) -> int:
        """
        Store a drift alert.
        
        Args:
            alert: DriftAlert object
            
        Returns:
            Alert ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO drift_alerts
                (test_name, severity, drift_percentage, message, recommendations, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.test_name,
                    alert.severity.value,
                    alert.drift_percentage,
                    alert.message,
                    json.dumps(alert.recommendations),
                    alert.timestamp.isoformat()
                )
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_alerts(
        self,
        test_name: Optional[str] = None,
        min_severity: Optional[DriftSeverity] = None,
        acknowledged: Optional[bool] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query drift alerts.
        
        Args:
            test_name: Filter by test name
            min_severity: Minimum severity level
            acknowledged: Filter by acknowledgment status
            since: Filter by creation time
            limit: Maximum number of alerts
            
        Returns:
            List of alert dictionaries with metadata
        """
        severity_order = {
            DriftSeverity.NONE: 0,
            DriftSeverity.LOW: 1,
            DriftSeverity.MODERATE: 2,
            DriftSeverity.HIGH: 3,
            DriftSeverity.CRITICAL: 4
        }
        
        query = "SELECT * FROM drift_alerts WHERE 1=1"
        params = []
        
        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)
        
        if acknowledged is not None:
            query += " AND acknowledged = ?"
            params.append(1 if acknowledged else 0)
        
        if since:
            query += " AND created_at >= ?"
            params.append(since.isoformat())
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        alerts = []
        for row in rows:
            severity = DriftSeverity(row['severity'])
            
            # Apply severity filter
            if min_severity and severity_order[severity] < severity_order[min_severity]:
                continue
            
            alerts.append({
                'id': row['id'],
                'test_name': row['test_name'],
                'severity': severity,
                'drift_percentage': row['drift_percentage'],
                'message': row['message'],
                'recommendations': json.loads(row['recommendations']),
                'created_at': datetime.fromisoformat(row['created_at']),
                'acknowledged': bool(row['acknowledged']),
                'acknowledged_at': datetime.fromisoformat(row['acknowledged_at']) if row['acknowledged_at'] else None,
                'acknowledged_by': row['acknowledged_by']
            })
        
        return alerts
    
    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: str = "system"
    ) -> bool:
        """
        Mark an alert as acknowledged.
        
        Args:
            alert_id: Alert ID
            acknowledged_by: User/system that acknowledged
            
        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE drift_alerts
                SET acknowledged = 1,
                    acknowledged_at = datetime('now'),
                    acknowledged_by = ?
                WHERE id = ?
                """,
                (acknowledged_by, alert_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # STATISTICS & REPORTING
    # ========================================================================
    
    def get_drift_statistics(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get drift statistics across all tests.
        
        Args:
            category: Filter by category
            since: Filter by time period
            
        Returns:
            Dictionary with statistics
        """
        query = """
        SELECT
            COUNT(DISTINCT test_name) as total_tests,
            COUNT(*) as total_measurements,
            AVG(confidence) as avg_confidence,
            MIN(confidence) as min_confidence,
            MAX(confidence) as max_confidence
        FROM confidence_measurements
        WHERE 1=1
        """
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
        
        return {
            'total_tests': row['total_tests'],
            'total_measurements': row['total_measurements'],
            'avg_confidence': row['avg_confidence'],
            'min_confidence': row['min_confidence'],
            'max_confidence': row['max_confidence']
        }
    
    def get_alert_summary(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Get alert count by severity.
        
        Args:
            since: Filter by time period
            
        Returns:
            Dictionary mapping severity to count
        """
        query = """
        SELECT severity, COUNT(*) as count
        FROM drift_alerts
        WHERE 1=1
        """
        params = []
        
        if since:
            query += " AND created_at >= ?"
            params.append(since.isoformat())
        
        query += " GROUP BY severity"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        return {row['severity']: row['count'] for row in rows}
    
    # ========================================================================
    # MAINTENANCE
    # ========================================================================
    
    def cleanup_old_data(
        self,
        measurements_days: int = 90,
        analysis_days: int = 30,
        alerts_days: int = 60
    ) -> Dict[str, int]:
        """
        Remove old data to save space.
        
        Args:
            measurements_days: Keep measurements newer than this
            analysis_days: Keep analysis newer than this
            alerts_days: Keep alerts newer than this (acknowledged ones only)
            
        Returns:
            Dictionary with counts of deleted records
        """
        cutoffs = {
            'measurements': datetime.utcnow() - timedelta(days=measurements_days),
            'analysis': datetime.utcnow() - timedelta(days=analysis_days),
            'alerts': datetime.utcnow() - timedelta(days=alerts_days)
        }
        
        deleted = {}
        
        with self._get_connection() as conn:
            # Delete old measurements
            cursor = conn.execute(
                "DELETE FROM confidence_measurements WHERE timestamp < ?",
                (cutoffs['measurements'].isoformat(),)
            )
            deleted['measurements'] = cursor.rowcount
            
            # Delete old analysis
            cursor = conn.execute(
                "DELETE FROM drift_analysis WHERE analyzed_at < ?",
                (cutoffs['analysis'].isoformat(),)
            )
            deleted['analysis'] = cursor.rowcount
            
            # Delete old acknowledged alerts
            cursor = conn.execute(
                "DELETE FROM drift_alerts WHERE acknowledged = 1 AND created_at < ?",
                (cutoffs['alerts'].isoformat(),)
            )
            deleted['alerts'] = cursor.rowcount
            
            conn.commit()
        
        logger.info(f"Cleanup complete: {deleted}")
        return deleted
    
    def vacuum(self):
        """Optimize database (reclaim space)."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
        logger.info("Database vacuumed")
    
    def get_database_size(self) -> int:
        """
        Get database file size in bytes.
        
        Returns:
            Size in bytes
        """
        return self.db_path.stat().st_size if self.db_path.exists() else 0
    
    def export_to_json(self, output_path: str, since: Optional[datetime] = None):
        """
        Export data to JSON file.
        
        Args:
            output_path: Output file path
            since: Export data since this time
        """
        measurements = self.get_measurements(since=since)
        
        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'measurements': [
                {
                    'test_name': m.test_name,
                    'confidence': m.confidence,
                    'category': m.category,
                    'timestamp': m.timestamp.isoformat(),
                    'failure_id': m.failure_id,
                    'rule_score': m.rule_score,
                    'signal_score': m.signal_score
                }
                for m in measurements
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(measurements)} measurements to {output_path}")
