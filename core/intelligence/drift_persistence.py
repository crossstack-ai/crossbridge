"""
Persistence Layer for Confidence Drift Detection

This module provides database persistence for drift tracking:
- Store confidence measurements (SQLite or PostgreSQL)
- Query historical drift data
- Support for trend analysis over extended periods
- Efficient storage with automatic cleanup

Design Principles:
- Database abstraction (supports SQLite and PostgreSQL)
- Automatic schema creation
- Thread-safe operations
- Configurable retention policies

Backend Selection:
- SQLite: Development, testing, small deployments
- PostgreSQL: Production, large scale, Grafana integration
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from core.intelligence.confidence_drift import (
    ConfidenceRecord,
    DriftAnalysis,
    DriftAlert,
    DriftSeverity
)
from core.intelligence.drift_storage import (
    DriftStorageBackend,
    create_drift_storage
)

logger = logging.getLogger(__name__)


# ============================================================================
# PERSISTENCE MANAGER
# ============================================================================

class DriftPersistenceManager:
    """
    Manages persistence of confidence drift data.
    
    Supports both SQLite and PostgreSQL backends through abstraction layer.
    
    Features:
    - Store confidence measurements
    - Cache drift analysis results
    - Track drift alerts
    - Query historical data
    - Automatic cleanup
    
    Examples:
        # SQLite (development/testing)
        manager = DriftPersistenceManager(backend="sqlite", db_path="data/drift.db")
        
        # PostgreSQL (production)
        manager = DriftPersistenceManager(
            backend="postgres",
            host="localhost",
            database="crossbridge",
            user="crossbridge",
            password="secret",
            schema="drift"
        )
    """
    
    def __init__(
        self,
        backend: str = "sqlite",
        db_path: str = "data/drift_tracking.db",
        **kwargs
    ):
        """
        Initialize persistence manager.
        
        Args:
            backend: "sqlite" or "postgres"
            db_path: Path to SQLite database (if backend="sqlite")
            **kwargs: Backend-specific configuration (host, port, etc.)
        """
        # Create storage backend
        if backend == "sqlite":
            self.storage: DriftStorageBackend = create_drift_storage("sqlite", db_path=db_path)
        elif backend == "postgres":
            self.storage: DriftStorageBackend = create_drift_storage("postgres", **kwargs)
        else:
            raise ValueError(f"Unknown backend: {backend}")
        
        # Initialize database
        if not self.storage.initialize():
            raise RuntimeError(f"Failed to initialize {backend} drift storage")
        
        logger.info(f"Drift persistence initialized with {backend} backend")
    
    # ========================================================================
    # CONFIDENCE MEASUREMENTS
    # ========================================================================
    
    def store_measurement(
        self,
        test_name: str,
        confidence: float,
        category: str,
        timestamp: Optional[datetime] = None,
        failure_id: Optional[str] = None,
        rule_score: Optional[float] = None,
        signal_score: Optional[float] = None
    ) -> int:
        """
        Store a confidence measurement.
        
        Args:
            test_name: Name of the test
            confidence: Confidence score (0.0-1.0)
            category: Test category
            timestamp: Measurement timestamp (default: now)
            failure_id: Optional failure ID
            rule_score: Optional rule-based score
            signal_score: Optional signal-based score
            
        Returns:
            Record ID
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        return self.storage.store_measurement(
            test_name=test_name,
            confidence=confidence,
            category=category,
            timestamp=timestamp,
            failure_id=failure_id,
            rule_score=rule_score,
            signal_score=signal_score
        )
    
    def store_measurements(self, records: List[ConfidenceRecord]) -> int:
        """
        Store multiple confidence measurements (bulk insert).
        
        Args:
            records: List of ConfidenceRecord objects
            
        Returns:
            Number of records inserted
        """
        return self.storage.store_measurements_bulk(records)
    
    def get_measurements(
        self,
        test_name: Optional[str] = None,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ConfidenceRecord]:
        """Query confidence measurements with filters."""
        return self.storage.get_measurements(
            test_name=test_name,
            category=category,
            since=since,
            until=until,
            limit=limit
        )
    
    def get_test_history(
        self,
        test_name: str,
        window: timedelta = timedelta(days=30)
    ) -> List[ConfidenceRecord]:
        """Get historical measurements for a specific test."""
        return self.storage.get_test_history(test_name=test_name, window=window)
    
    def get_category_tests(self, category: str) -> List[str]:
        """Get all test names in a category."""
        measurements = self.get_measurements(category=category, limit=10000)
        return list(set(m.test_name for m in measurements))
    
    # ========================================================================
    # DRIFT ANALYSIS CACHE
    # ========================================================================
    
    def store_drift_analysis(self, test_name: str, analysis: DriftAnalysis) -> int:
        """Store drift analysis result (for caching)."""
        return self.storage.store_drift_analysis(test_name, analysis)
    
    def get_latest_drift_analysis(self, test_name: str) -> Optional[DriftAnalysis]:
        """Get most recent drift analysis for a test."""
        return self.storage.get_latest_analysis(test_name)
    
    # ========================================================================
    # DRIFT ALERTS
    # ========================================================================
    
    def store_alert(self, alert: DriftAlert) -> int:
        """Store a drift alert."""
        return self.storage.store_alert(alert)
    
    def get_alerts(
        self,
        test_name: Optional[str] = None,
        min_severity: Optional[DriftSeverity] = None,
        acknowledged: Optional[bool] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Query drift alerts."""
        return self.storage.get_alerts(
            test_name=test_name,
            min_severity=min_severity,
            acknowledged=acknowledged,
            since=since
        )
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "system") -> bool:
        """Mark an alert as acknowledged."""
        return self.storage.acknowledge_alert(alert_id, acknowledged_by)
    
    # ========================================================================
    # STATISTICS & REPORTING
    # ========================================================================
    
    def get_drift_statistics(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get drift statistics across all tests."""
        return self.storage.get_drift_statistics(category=category, since=since)
    
    def get_alert_summary(self, since: Optional[datetime] = None) -> Dict[str, int]:
        """Get alert count by severity."""
        stats = self.storage.get_drift_statistics(since=since)
        # Return empty dict for now - can be enhanced later
        return {}
    
    # ========================================================================
    # MAINTENANCE
    # ========================================================================
    
    def cleanup_old_data(
        self,
        measurements_days: int = 90,
        analysis_days: int = 30,
        alerts_days: int = 60
    ) -> Dict[str, int]:
        """Remove old data to save space."""
        return self.storage.cleanup_old_data(
            measurements_days=measurements_days,
            analysis_days=analysis_days,
            alerts_days=alerts_days
        )
    
    def vacuum(self):
        """Optimize database (reclaim space)."""
        self.storage.vacuum()
        logger.info("Database optimized")
    
    def get_database_size(self) -> int:
        """Get database size in bytes."""
        return self.storage.get_database_size()
    
    def export_to_json(self, output_path: str, since: Optional[datetime] = None):
        """Export data to JSON file."""
        self.storage.export_to_json(output_path, since=since)
        logger.info(f"Exported data to {output_path}")
