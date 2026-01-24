"""
Database Migration: Add Lifecycle and Coverage Graph Tables

This migration adds:
1. migration_state table - tracks project lifecycle (migration → observer)
2. coverage_graph_nodes table - coverage intelligence nodes
3. coverage_graph_edges table - relationships between nodes

Run with:
    python scripts/migrate_continuous_intelligence.py
"""

import psycopg2
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration(db_config):
    """Run the continuous intelligence migration"""
    
    logger.info("Connecting to database...")
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # 1. Create migration_state table
        logger.info("Creating migration_state table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_state (
                project_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL DEFAULT 'migration',
                migration_completed_at TIMESTAMP,
                observer_enabled BOOLEAN DEFAULT false,
                hooks_registered BOOLEAN DEFAULT false,
                last_event_at TIMESTAMP,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Add indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_migration_state_mode 
            ON migration_state(mode)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_migration_state_last_event 
            ON migration_state(last_event_at)
        """)
        
        # 2. Create coverage_graph_nodes table
        logger.info("Creating coverage_graph_nodes table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coverage_graph_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,  -- test | api | page | ui_component | feature
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Add indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_nodes_type 
            ON coverage_graph_nodes(node_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_nodes_metadata 
            ON coverage_graph_nodes USING GIN(metadata)
        """)
        
        # 3. Create coverage_graph_edges table
        logger.info("Creating coverage_graph_edges table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coverage_graph_edges (
                id SERIAL PRIMARY KEY,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                edge_type TEXT NOT NULL,  -- tests | calls_api | visits_page | interacts_with
                weight INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT NOW(),
                last_seen TIMESTAMP DEFAULT NOW(),
                metadata JSONB,
                UNIQUE(from_node, to_node, edge_type)
            )
        """)
        
        # Add indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_edges_from 
            ON coverage_graph_edges(from_node)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_edges_to 
            ON coverage_graph_edges(to_node)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_edges_type 
            ON coverage_graph_edges(edge_type)
        """)
        
        # 4. Create drift_signals table
        logger.info("Creating drift_signals table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_signals (
                id SERIAL PRIMARY KEY,
                signal_type TEXT NOT NULL,  -- new_test | removed_test | behavior_change | flaky
                test_id TEXT NOT NULL,
                severity TEXT NOT NULL,  -- low | medium | high
                description TEXT,
                metadata JSONB,
                detected_at TIMESTAMP DEFAULT NOW(),
                acknowledged BOOLEAN DEFAULT false,
                acknowledged_at TIMESTAMP,
                acknowledged_by TEXT
            )
        """)
        
        # Add indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_drift_signals_test 
            ON drift_signals(test_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_drift_signals_type 
            ON drift_signals(signal_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_drift_signals_severity 
            ON drift_signals(severity)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_drift_signals_detected 
            ON drift_signals(detected_at)
        """)
        
        # 5. Add new columns to test_execution_event (if they don't exist)
        logger.info("Checking test_execution_event table...")
        
        # Check if columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'test_execution_event'
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        # Add missing columns
        if 'error_message' not in existing_columns:
            logger.info("Adding error_message column...")
            cursor.execute("""
                ALTER TABLE test_execution_event 
                ADD COLUMN error_message TEXT
            """)
        
        if 'stack_trace' not in existing_columns:
            logger.info("Adding stack_trace column...")
            cursor.execute("""
                ALTER TABLE test_execution_event 
                ADD COLUMN stack_trace TEXT
            """)
        
        # Commit all changes
        conn.commit()
        logger.info("✅ Migration completed successfully!")
        
        # Print summary
        cursor.execute("SELECT COUNT(*) FROM migration_state")
        projects_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM coverage_graph_nodes")
        nodes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM coverage_graph_edges")
        edges_count = cursor.fetchone()[0]
        
        logger.info(f"""
Migration Summary:
- Projects tracked: {projects_count}
- Coverage nodes: {nodes_count}
- Coverage edges: {edges_count}

Next steps:
1. Run tests to emit events: pytest --crossbridge
2. Check observer service: python -m core.observability.observer_service
3. View drift signals: SELECT * FROM drift_signals
""")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': '10.55.12.99',
        'port': 5432,
        'database': 'udp-native-webservices-automation',
        'user': 'postgres',
        'password': 'admin'
    }
    
    logger.info("=" * 70)
    logger.info("CrossBridge Continuous Intelligence Migration")
    logger.info("=" * 70)
    
    run_migration(db_config)
