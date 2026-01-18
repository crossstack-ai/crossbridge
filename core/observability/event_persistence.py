"""
Event Persistence Layer

Stores execution events to PostgreSQL for continuous intelligence and analysis.
"""

import logging
import psycopg2
import psycopg2.extras
from typing import Optional
import os

from .events import CrossBridgeEvent

logger = logging.getLogger(__name__)

# Register UUID adapter
psycopg2.extras.register_uuid()


class EventPersistence:
    """
    Persists CrossBridge events to PostgreSQL.
    
    Events are stored in the test_execution_event table and used for:
    - History tracking
    - Trend analysis
    - Flakiness detection
    - AI context
    - Coverage intelligence
    """
    
    def __init__(self):
        """Initialize persistence layer"""
        self.db_url = self._get_db_url()
        self._ensure_table_exists()
    
    def _get_db_url(self) -> Optional[str]:
        """Get database connection URL from environment"""
        # Check for full connection string
        db_url = os.getenv('CROSSBRIDGE_DB_URL')
        if db_url:
            return db_url
        
        # Build from individual components
        host = os.getenv('CROSSBRIDGE_DB_HOST', '10.55.12.99')
        port = os.getenv('CROSSBRIDGE_DB_PORT', '5432')
        database = os.getenv('CROSSBRIDGE_DB_NAME', 'udp-native-webservices-automation')
        user = os.getenv('CROSSBRIDGE_DB_USER', 'postgres')
        password = os.getenv('CROSSBRIDGE_DB_PASSWORD', 'admin')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def _get_connection(self):
        """Get database connection"""
        if not self.db_url:
            raise ValueError("Database URL not configured")
        return psycopg2.connect(self.db_url)
    
    def _ensure_table_exists(self):
        """Create test_execution_event table if it doesn't exist"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_execution_event (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    event_type TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    test_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    status TEXT,
                    duration_ms INTEGER,
                    error_message TEXT,
                    stack_trace TEXT,
                    metadata JSONB,
                    schema_version TEXT DEFAULT '1.0',
                    application_version TEXT,
                    product_name TEXT,
                    environment TEXT,
                    created_at TIMESTAMP DEFAULT now()
                );
                
                CREATE INDEX IF NOT EXISTS idx_event_framework ON test_execution_event(framework);
                CREATE INDEX IF NOT EXISTS idx_event_test_id ON test_execution_event(test_id);
                CREATE INDEX IF NOT EXISTS idx_event_type ON test_execution_event(event_type);
                CREATE INDEX IF NOT EXISTS idx_event_timestamp ON test_execution_event(timestamp);
                CREATE INDEX IF NOT EXISTS idx_event_status ON test_execution_event(status);
                CREATE INDEX IF NOT EXISTS idx_app_version ON test_execution_event(application_version);
                CREATE INDEX IF NOT EXISTS idx_product_name ON test_execution_event(product_name);
                CREATE INDEX IF NOT EXISTS idx_environment ON test_execution_event(environment);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to ensure table exists: {e}")
    
    def store_event(self, event: CrossBridgeEvent) -> None:
        """
        Store event to database.
        
        Args:
            event: CrossBridgeEvent to persist
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO test_execution_event (
                    event_type, framework, test_id, timestamp,
                    status, duration_ms, error_message, stack_trace,
                    metadata, schema_version,
                    application_version, product_name, environment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event.event_type,
                event.framework,
                event.test_id,
                event.timestamp,
                event.status,
                event.duration_ms,
                event.error_message,
                event.stack_trace,
                psycopg2.extras.Json(event.metadata),
                event.schema_version,
                event.application_version,
                event.product_name,
                event.environment
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store event: {e}", exc_info=True)
            # Never fail test execution due to persistence errors
