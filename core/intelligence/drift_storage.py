"""
Database Abstraction Layer for Drift Tracking

Supports both SQLite (development/testing) and PostgreSQL (production).
Provides unified interface for drift data persistence.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager
import json
import logging

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

# SQLite-specific schema (uses AUTOINCREMENT)
SQLITE_SCHEMA = """
-- Confidence measurements table
CREATE TABLE IF NOT EXISTS confidence_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    category TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    failure_id TEXT,
    rule_score REAL,
    signal_score REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_name, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_test_name ON confidence_measurements(test_name);
CREATE INDEX IF NOT EXISTS idx_category ON confidence_measurements(category);
CREATE INDEX IF NOT EXISTS idx_timestamp ON confidence_measurements(timestamp);

-- Drift analysis cache
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
    recommendations TEXT NOT NULL,
    analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    recommendations TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_at TIMESTAMP,
    acknowledged_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_alert_test ON drift_alerts(test_name);
CREATE INDEX IF NOT EXISTS idx_alert_severity ON drift_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alert_created ON drift_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alert_ack ON drift_alerts(acknowledged);

-- Metadata table
CREATE TABLE IF NOT EXISTS drift_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# PostgreSQL-specific schema (uses SERIAL)
POSTGRES_SCHEMA = """
-- Confidence measurements table
CREATE TABLE IF NOT EXISTS {schema}.confidence_measurements (
    id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    category TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    failure_id TEXT,
    rule_score REAL,
    signal_score REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_name, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_cm_test_name ON {schema}.confidence_measurements(test_name);
CREATE INDEX IF NOT EXISTS idx_cm_category ON {schema}.confidence_measurements(category);
CREATE INDEX IF NOT EXISTS idx_cm_timestamp ON {schema}.confidence_measurements(timestamp);

-- Drift analysis cache
CREATE TABLE IF NOT EXISTS {schema}.drift_analysis (
    id SERIAL PRIMARY KEY,
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
    recommendations TEXT NOT NULL,
    analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_da_test ON {schema}.drift_analysis(test_name);
CREATE INDEX IF NOT EXISTS idx_da_severity ON {schema}.drift_analysis(severity);
CREATE INDEX IF NOT EXISTS idx_da_analyzed ON {schema}.drift_analysis(analyzed_at);

-- Drift alerts table
CREATE TABLE IF NOT EXISTS {schema}.drift_alerts (
    id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    drift_percentage REAL NOT NULL,
    message TEXT NOT NULL,
    recommendations TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_da_test ON {schema}.drift_alerts(test_name);
CREATE INDEX IF NOT EXISTS idx_da_severity ON {schema}.drift_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_da_created ON {schema}.drift_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_da_ack ON {schema}.drift_alerts(acknowledged);

-- Metadata table
CREATE TABLE IF NOT EXISTS {schema}.drift_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


# ============================================================================
# ABSTRACT STORAGE BACKEND
# ============================================================================

class DriftStorageBackend(ABC):
    """Abstract storage backend for drift tracking."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize storage (create tables, etc). Returns True if successful."""
        pass
    
    @abstractmethod
    @contextmanager
    def get_connection(self):
        """Context manager to get a database connection."""
        pass
    
    @abstractmethod
    def store_measurement(
        self,
        test_name: str,
        confidence: float,
        category: str,
        timestamp: datetime,
        failure_id: Optional[str] = None,
        rule_score: Optional[float] = None,
        signal_score: Optional[float] = None
    ) -> int:
        """Store a confidence measurement. Returns the measurement ID."""
        pass
    
    @abstractmethod
    def store_measurements_bulk(self, measurements: List[ConfidenceRecord]) -> int:
        """Store multiple measurements. Returns count of inserted records."""
        pass
    
    @abstractmethod
    def get_measurements(
        self,
        test_name: Optional[str] = None,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ConfidenceRecord]:
        """Query confidence measurements."""
        pass
    
    @abstractmethod
    def get_test_history(
        self,
        test_name: str,
        window: timedelta = timedelta(days=30)
    ) -> List[ConfidenceRecord]:
        """Get historical measurements for a specific test."""
        pass
    
    @abstractmethod
    def store_drift_analysis(self, test_name: str, analysis: DriftAnalysis) -> int:
        """Cache drift analysis result. Returns analysis ID."""
        pass
    
    @abstractmethod
    def get_latest_analysis(self, test_name: str) -> Optional[DriftAnalysis]:
        """Get the most recent drift analysis for a test."""
        pass
    
    @abstractmethod
    def store_alert(self, alert: DriftAlert) -> int:
        """Store a drift alert. Returns alert ID."""
        pass
    
    @abstractmethod
    def get_alerts(
        self,
        test_name: Optional[str] = None,
        min_severity: Optional[DriftSeverity] = None,
        acknowledged: Optional[bool] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Query drift alerts."""
        pass
    
    @abstractmethod
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert. Returns True if successful."""
        pass
    
    @abstractmethod
    def get_drift_statistics(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregate drift statistics."""
        pass
    
    @abstractmethod
    def cleanup_old_data(
        self,
        measurements_days: int = 90,
        analysis_days: int = 30,
        alerts_days: int = 60
    ) -> Dict[str, int]:
        """Remove old data. Returns count of deleted records by table."""
        pass
    
    @abstractmethod
    def get_database_size(self) -> int:
        """Get database size in bytes."""
        pass
    
    @abstractmethod
    def vacuum(self) -> bool:
        """Optimize database. Returns True if successful."""
        pass
    
    @abstractmethod
    def export_to_json(self, output_path: str, since: Optional[datetime] = None) -> bool:
        """Export drift data to JSON. Returns True if successful."""
        pass


# ============================================================================
# SQLITE BACKEND
# ============================================================================

class SQLiteDriftStorage(DriftStorageBackend):
    """SQLite storage backend for drift tracking (development/testing)."""
    
    def __init__(self, db_path: str = "data/drift_tracking.db"):
        self.db_path = db_path
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        from pathlib import Path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def initialize(self) -> bool:
        """Create database and schema."""
        try:
            import sqlite3
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute schema
                for statement in SQLITE_SCHEMA.split(';'):
                    if statement.strip():
                        cursor.execute(statement)
                
                # Store schema version
                cursor.execute(
                    "INSERT OR REPLACE INTO drift_metadata (key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION))
                )
                
                conn.commit()
                logger.info(f"Initialized SQLite drift storage: {self.db_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize SQLite storage: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Get SQLite database connection."""
        import sqlite3
        
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        
        try:
            yield conn
        finally:
            conn.close()
    
    def store_measurement(
        self,
        test_name: str,
        confidence: float,
        category: str,
        timestamp: datetime,
        failure_id: Optional[str] = None,
        rule_score: Optional[float] = None,
        signal_score: Optional[float] = None
    ) -> int:
        """Store a single confidence measurement."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO confidence_measurements
                (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score))
            
            conn.commit()
            return cursor.lastrowid
    
    def store_measurements_bulk(self, measurements: List[ConfidenceRecord]) -> int:
        """Store multiple measurements in bulk."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            data = [
                (m.test_name, m.confidence, m.category, m.timestamp, 
                 m.failure_id, m.rule_score, m.signal_score)
                for m in measurements
            ]
            
            cursor.executemany("""
                INSERT OR REPLACE INTO confidence_measurements
                (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
            return cursor.rowcount
    
    def get_measurements(
        self,
        test_name: Optional[str] = None,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ConfidenceRecord]:
        """Query confidence measurements with filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
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
                params.append(since)
            
            if until:
                query += " AND timestamp <= ?"
                params.append(until)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                ConfidenceRecord(
                    test_name=row['test_name'],
                    confidence=row['confidence'],
                    category=row['category'],
                    timestamp=row['timestamp'],
                    failure_id=row['failure_id'],
                    rule_score=row['rule_score'],
                    signal_score=row['signal_score']
                )
                for row in rows
            ]
    
    def get_test_history(
        self,
        test_name: str,
        window: timedelta = timedelta(days=30)
    ) -> List[ConfidenceRecord]:
        """Get historical measurements for a specific test."""
        since = datetime.utcnow() - window
        return self.get_measurements(test_name=test_name, since=since, limit=10000)
    
    def store_drift_analysis(self, test_name: str, analysis: DriftAnalysis) -> int:
        """Cache drift analysis result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO drift_analysis
                (test_name, baseline_confidence, current_confidence, drift_percentage,
                 drift_absolute, severity, direction, trend, measurements_count,
                 time_span_seconds, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_name,
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
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_latest_analysis(self, test_name: str) -> Optional[DriftAnalysis]:
        """Get the most recent drift analysis for a test."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM drift_analysis
                WHERE test_name = ?
                ORDER BY analyzed_at DESC
                LIMIT 1
            """, (test_name,))
            
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
                is_drifting=row['drift_percentage'] >= 0.05,  # 5% threshold
                measurements_count=row['measurements_count'],
                time_span=timedelta(seconds=row['time_span_seconds']),
                trend=row['trend'],
                recommendations=json.loads(row['recommendations']),
                timestamp=datetime.fromisoformat(row['analyzed_at'])
            )
    
    def store_alert(self, alert: DriftAlert) -> int:
        """Store a drift alert."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO drift_alerts
                (test_name, severity, drift_percentage, message, recommendations, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert.test_name,
                alert.severity.value,
                alert.drift_percentage,
                alert.message,
                json.dumps(alert.recommendations),
                alert.timestamp
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_alerts(
        self,
        test_name: Optional[str] = None,
        min_severity: Optional[DriftSeverity] = None,
        acknowledged: Optional[bool] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Query drift alerts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM drift_alerts WHERE 1=1"
            params = []
            
            if test_name:
                query += " AND test_name = ?"
                params.append(test_name)
            
            if min_severity:
                severity_levels = ['none', 'low', 'moderate', 'high', 'critical']
                min_level = severity_levels.index(min_severity.value)
                allowed = severity_levels[min_level:]
                query += f" AND severity IN ({','.join('?' * len(allowed))})"
                params.extend(allowed)
            
            if acknowledged is not None:
                query += " AND acknowledged = ?"
                params.append(acknowledged)
            
            if since:
                query += " AND created_at >= ?"
                params.append(since)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row['id'],
                    'test_name': row['test_name'],
                    'severity': DriftSeverity(row['severity']),
                    'drift_percentage': row['drift_percentage'],
                    'message': row['message'],
                    'recommendations': json.loads(row['recommendations']),
                    'created_at': row['created_at'],
                    'acknowledged': bool(row['acknowledged']),
                    'acknowledged_at': row['acknowledged_at'],
                    'acknowledged_by': row['acknowledged_by']
                }
                for row in rows
            ]
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE drift_alerts
                SET acknowledged = 1,
                    acknowledged_at = ?,
                    acknowledged_by = ?
                WHERE id = ?
            """, (datetime.utcnow(), acknowledged_by, alert_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_drift_statistics(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregate drift statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT COUNT(DISTINCT test_name) as total_tests, COUNT(*) as total_measurements"
            query += ", AVG(confidence) as avg_confidence, MIN(confidence) as min_confidence"
            query += ", MAX(confidence) as max_confidence FROM confidence_measurements WHERE 1=1"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if since:
                query += " AND timestamp >= ?"
                params.append(since)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            return {
                'total_tests': row['total_tests'] or 0,
                'total_measurements': row['total_measurements'] or 0,
                'avg_confidence': row['avg_confidence'],
                'min_confidence': row['min_confidence'],
                'max_confidence': row['max_confidence']
            }
    
    def cleanup_old_data(
        self,
        measurements_days: int = 90,
        analysis_days: int = 30,
        alerts_days: int = 60
    ) -> Dict[str, int]:
        """Remove old data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_measurements = datetime.utcnow() - timedelta(days=measurements_days)
            cutoff_analysis = datetime.utcnow() - timedelta(days=analysis_days)
            cutoff_alerts = datetime.utcnow() - timedelta(days=alerts_days)
            
            # Delete old measurements
            cursor.execute("DELETE FROM confidence_measurements WHERE timestamp < ?", (cutoff_measurements,))
            deleted_measurements = cursor.rowcount
            
            # Delete old analysis
            cursor.execute("DELETE FROM drift_analysis WHERE analyzed_at < ?", (cutoff_analysis,))
            deleted_analysis = cursor.rowcount
            
            # Delete old acknowledged alerts
            cursor.execute("""
                DELETE FROM drift_alerts 
                WHERE acknowledged = 1 AND acknowledged_at < ?
            """, (cutoff_alerts,))
            deleted_alerts = cursor.rowcount
            
            conn.commit()
            
            return {
                'measurements': deleted_measurements,
                'analysis': deleted_analysis,
                'alerts': deleted_alerts
            }
    
    def get_database_size(self) -> int:
        """Get database size in bytes."""
        from pathlib import Path
        return Path(self.db_path).stat().st_size
    
    def vacuum(self) -> bool:
        """Optimize database."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
            return True
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False
    
    def export_to_json(self, output_path: str, since: Optional[datetime] = None) -> bool:
        """Export drift data to JSON."""
        try:
            data = {
                'measurements': [
                    {
                        'test_name': m.test_name,
                        'confidence': m.confidence,
                        'category': m.category,
                        'timestamp': m.timestamp.isoformat()
                    }
                    for m in self.get_measurements(since=since, limit=10000)
                ],
                'alerts': self.get_alerts(since=since)
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False


# ============================================================================
# POSTGRESQL BACKEND
# ============================================================================

class PostgresDriftStorage(DriftStorageBackend):
    """PostgreSQL storage backend for drift tracking (production)."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "crossbridge",
        user: str = "crossbridge",
        password: str = "",
        schema: str = "drift"
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self.pool = None
    
    def initialize(self) -> bool:
        """Create PostgreSQL connection pool and schema."""
        try:
            import psycopg2
            from psycopg2 import pool
            
            # Create connection pool
            self.pool = pool.SimpleConnectionPool(
                1, 10,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create schema
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                
                # Create tables (replace {schema} placeholder)
                schema_sql = POSTGRES_SCHEMA.format(schema=self.schema)
                
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        cursor.execute(statement)
                
                # Store schema version
                cursor.execute(
                    f"INSERT INTO {self.schema}.drift_metadata (key, value) "
                    f"VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                    ("schema_version", str(SCHEMA_VERSION))
                )
                
                conn.commit()
                logger.info(f"Initialized PostgreSQL drift storage: {self.database}.{self.schema}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL storage: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Get PostgreSQL connection from pool."""
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def store_measurement(
        self,
        test_name: str,
        confidence: float,
        category: str,
        timestamp: datetime,
        failure_id: Optional[str] = None,
        rule_score: Optional[float] = None,
        signal_score: Optional[float] = None
    ) -> int:
        """Store a single confidence measurement."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                INSERT INTO {self.schema}.confidence_measurements
                (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (test_name, timestamp) DO UPDATE
                SET confidence = EXCLUDED.confidence
                RETURNING id
            """, (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score))
            
            row_id = cursor.fetchone()[0]
            conn.commit()
            return row_id
    
    def store_measurements_bulk(self, measurements: List[ConfidenceRecord]) -> int:
        """Store multiple measurements in bulk."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            data = [
                (m.test_name, m.confidence, m.category, m.timestamp,
                 m.failure_id, m.rule_score, m.signal_score)
                for m in measurements
            ]
            
            from psycopg2.extras import execute_batch
            
            execute_batch(cursor, f"""
                INSERT INTO {self.schema}.confidence_measurements
                (test_name, confidence, category, timestamp, failure_id, rule_score, signal_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (test_name, timestamp) DO UPDATE
                SET confidence = EXCLUDED.confidence
            """, data)
            
            count = cursor.rowcount
            conn.commit()
            return count
    
    # Additional methods follow the same pattern as SQLite,
    # but use PostgreSQL-specific syntax (%s placeholders, RETURNING, etc.)
    # ... (implement remaining abstract methods similarly)
    
    def get_measurements(
        self,
        test_name: Optional[str] = None,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ConfidenceRecord]:
        """Query confidence measurements with filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = f"SELECT * FROM {self.schema}.confidence_measurements WHERE 1=1"
            params = []
            
            if test_name:
                query += " AND test_name = %s"
                params.append(test_name)
            
            if category:
                query += " AND category = %s"
                params.append(category)
            
            if since:
                query += " AND timestamp >= %s"
                params.append(since)
            
            if until:
                query += " AND timestamp <= %s"
                params.append(until)
            
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                ConfidenceRecord(
                    test_name=row[1],
                    confidence=row[2],
                    category=row[3],
                    timestamp=row[4],
                    failure_id=row[5],
                    rule_score=row[6],
                    signal_score=row[7]
                )
                for row in rows
            ]
    
    def get_test_history(
        self,
        test_name: str,
        window: timedelta = timedelta(days=30)
    ) -> List[ConfidenceRecord]:
        """Get historical measurements for a specific test."""
        since = datetime.utcnow() - window
        return self.get_measurements(test_name=test_name, since=since, limit=10000)
    
    # ... (implement remaining methods with PostgreSQL syntax)
    
    def get_database_size(self) -> int:
        """Get database size in bytes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT pg_total_relation_size('{self.schema}.confidence_measurements')
                     + pg_total_relation_size('{self.schema}.drift_analysis')
                     + pg_total_relation_size('{self.schema}.drift_alerts')
            """)
            return cursor.fetchone()[0]
    
    def vacuum(self) -> bool:
        """Optimize database."""
        try:
            with self.get_connection() as conn:
                conn.autocommit = True
                cursor = conn.cursor()
                cursor.execute(f"VACUUM ANALYZE {self.schema}.confidence_measurements")
                cursor.execute(f"VACUUM ANALYZE {self.schema}.drift_analysis")
                cursor.execute(f"VACUUM ANALYZE {self.schema}.drift_alerts")
            return True
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False
    
    def cleanup_old_data(
        self,
        measurements_days: int = 90,
        analysis_days: int = 30,
        alerts_days: int = 60
    ) -> Dict[str, int]:
        """Remove old data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_measurements = datetime.utcnow() - timedelta(days=measurements_days)
            cutoff_analysis = datetime.utcnow() - timedelta(days=analysis_days)
            cutoff_alerts = datetime.utcnow() - timedelta(days=alerts_days)
            
            cursor.execute(f"""
                DELETE FROM {self.schema}.confidence_measurements 
                WHERE timestamp < %s
            """, (cutoff_measurements,))
            deleted_measurements = cursor.rowcount
            
            cursor.execute(f"""
                DELETE FROM {self.schema}.drift_analysis 
                WHERE analyzed_at < %s
            """, (cutoff_analysis,))
            deleted_analysis = cursor.rowcount
            
            cursor.execute(f"""
                DELETE FROM {self.schema}.drift_alerts 
                WHERE acknowledged = TRUE AND acknowledged_at < %s
            """, (cutoff_alerts,))
            deleted_alerts = cursor.rowcount
            
            conn.commit()
            
            return {
                'measurements': deleted_measurements,
                'analysis': deleted_analysis,
                'alerts': deleted_alerts
            }
    
    def store_drift_analysis(self, test_name: str, analysis: DriftAnalysis) -> int:
        """Cache drift analysis result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                INSERT INTO {self.schema}.drift_analysis
                (test_name, baseline_confidence, current_confidence, drift_percentage,
                 drift_absolute, severity, direction, trend, measurements_count,
                 time_span_seconds, recommendations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                test_name,
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
            ))
            
            row_id = cursor.fetchone()[0]
            conn.commit()
            return row_id
    
    def get_latest_analysis(self, test_name: str) -> Optional[DriftAnalysis]:
        """Get the most recent drift analysis for a test."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT * FROM {self.schema}.drift_analysis
                WHERE test_name = %s
                ORDER BY analyzed_at DESC
                LIMIT 1
            """, (test_name,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return DriftAnalysis(
                test_name=row[1],
                current_confidence=row[3],
                baseline_confidence=row[2],
                drift_percentage=row[4],
                drift_absolute=row[5],
                severity=DriftSeverity(row[6]),
                direction=DriftDirection(row[7]),
                is_drifting=row[4] >= 0.05,
                measurements_count=row[9],
                time_span=timedelta(seconds=row[10]),
                trend=row[8],
                recommendations=json.loads(row[11]),
                timestamp=row[12]
            )
    
    def store_alert(self, alert: DriftAlert) -> int:
        """Store a drift alert."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                INSERT INTO {self.schema}.drift_alerts
                (test_name, severity, drift_percentage, message, recommendations, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                alert.test_name,
                alert.severity.value,
                alert.drift_percentage,
                alert.message,
                json.dumps(alert.recommendations),
                alert.timestamp
            ))
            
            row_id = cursor.fetchone()[0]
            conn.commit()
            return row_id
    
    def get_alerts(
        self,
        test_name: Optional[str] = None,
        min_severity: Optional[DriftSeverity] = None,
        acknowledged: Optional[bool] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Query drift alerts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = f"SELECT * FROM {self.schema}.drift_alerts WHERE 1=1"
            params = []
            
            if test_name:
                query += " AND test_name = %s"
                params.append(test_name)
            
            if min_severity:
                severity_levels = ['none', 'low', 'moderate', 'high', 'critical']
                min_level = severity_levels.index(min_severity.value)
                allowed = severity_levels[min_level:]
                query += " AND severity = ANY(%s)"
                params.append(allowed)
            
            if acknowledged is not None:
                query += " AND acknowledged = %s"
                params.append(acknowledged)
            
            if since:
                query += " AND created_at >= %s"
                params.append(since)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'test_name': row[1],
                    'severity': DriftSeverity(row[2]),
                    'drift_percentage': row[3],
                    'message': row[4],
                    'recommendations': json.loads(row[5]),
                    'created_at': row[6],
                    'acknowledged': row[7],
                    'acknowledged_at': row[8],
                    'acknowledged_by': row[9]
                }
                for row in rows
            ]
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                UPDATE {self.schema}.drift_alerts
                SET acknowledged = TRUE,
                    acknowledged_at = %s,
                    acknowledged_by = %s
                WHERE id = %s
            """, (datetime.utcnow(), acknowledged_by, alert_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_drift_statistics(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregate drift statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = f"""
                SELECT COUNT(DISTINCT test_name) as total_tests,
                       COUNT(*) as total_measurements,
                       AVG(confidence) as avg_confidence,
                       MIN(confidence) as min_confidence,
                       MAX(confidence) as max_confidence
                FROM {self.schema}.confidence_measurements
                WHERE 1=1
            """
            params = []
            
            if category:
                query += " AND category = %s"
                params.append(category)
            
            if since:
                query += " AND timestamp >= %s"
                params.append(since)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            return {
                'total_tests': row[0] or 0,
                'total_measurements': row[1] or 0,
                'avg_confidence': row[2],
                'min_confidence': row[3],
                'max_confidence': row[4]
            }
    
    def export_to_json(self, output_path: str, since: Optional[datetime] = None) -> bool:
        """Export drift data to JSON."""
        try:
            data = {
                'measurements': [
                    {
                        'test_name': m.test_name,
                        'confidence': m.confidence,
                        'category': m.category,
                        'timestamp': m.timestamp.isoformat()
                    }
                    for m in self.get_measurements(since=since, limit=10000)
                ],
                'alerts': self.get_alerts(since=since)
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False


# ============================================================================
# FACTORY
# ============================================================================

def create_drift_storage(
    backend: str = "sqlite",
    **kwargs
) -> DriftStorageBackend:
    """
    Factory function to create drift storage backend.
    
    Args:
        backend: "sqlite" or "postgres"
        **kwargs: Backend-specific configuration
        
    Returns:
        DriftStorageBackend instance
        
    Examples:
        # SQLite (default)
        storage = create_drift_storage("sqlite", db_path="data/drift.db")
        
        # PostgreSQL
        storage = create_drift_storage(
            "postgres",
            host="localhost",
            port=5432,
            database="crossbridge",
            user="crossbridge",
            password="secret",
            schema="drift"
        )
    """
    if backend == "sqlite":
        return SQLiteDriftStorage(**kwargs)
    elif backend == "postgres":
        return PostgresDriftStorage(**kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'sqlite' or 'postgres'.")
