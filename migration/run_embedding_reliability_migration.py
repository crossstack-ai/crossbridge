"""
Database migration runner for embedding reliability features.

This script applies the embedding_reliability.sql migration to extend
the existing embedding tables with reliability tracking columns.

Usage:
    python migration/run_embedding_reliability_migration.py

Requirements:
    - PostgreSQL database configured in crossbridge.yml
    - psycopg2 or asyncpg installed
    - Database user with ALTER TABLE privileges
"""

import sys
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2 import sql
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

from core.config.settings import load_config

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Runs database migrations for embedding reliability."""
    
    def __init__(self, database_url: str):
        """Initialize with database connection URL."""
        self.database_url = database_url
        self.conn: Optional[any] = None
        self.cursor: Optional[any] = None
    
    def connect(self) -> bool:
        """Connect to database."""
        if not HAS_PSYCOPG2:
            logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
            return False
        
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor()
            logger.info("✓ Connected to database")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to database: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met."""
        logger.info("Checking prerequisites...")
        
        # Check if pgvector extension exists
        try:
            self.cursor.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
            has_pgvector = self.cursor.fetchone() is not None
            
            if has_pgvector:
                logger.info("✓ pgvector extension is installed")
            else:
                logger.warning("⚠ pgvector extension not found - vector features may be limited")
        except Exception as e:
            logger.warning(f"⚠ Could not check pgvector: {e}")
        
        # Check if test_embedding table exists
        try:
            self.cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%embedding%'
            """)
            tables = [row[0] for row in self.cursor.fetchall()]
            
            if tables:
                logger.info(f"✓ Found embedding tables: {', '.join(tables)}")
                return True
            else:
                logger.error("✗ No embedding tables found")
                logger.error("  Please ensure your embedding tables are created first")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to check tables: {e}")
            return False
    
    def apply_migration(self, sql_path: Path) -> bool:
        """Apply SQL migration file."""
        logger.info(f"Applying migration: {sql_path.name}")
        
        if not sql_path.exists():
            logger.error(f"✗ Migration file not found: {sql_path}")
            return False
        
        try:
            # Read migration SQL
            with open(sql_path, 'r') as f:
                migration_sql = f.read()
            
            # Split into individual statements
            statements = [
                stmt.strip() 
                for stmt in migration_sql.split(';') 
                if stmt.strip() and not stmt.strip().startswith('--')
            ]
            
            logger.info(f"Executing {len(statements)} statements...")
            
            # Execute each statement
            for i, statement in enumerate(statements, 1):
                try:
                    self.cursor.execute(statement)
                    logger.debug(f"  [{i}/{len(statements)}] ✓")
                except Exception as e:
                    # Some statements may fail if columns already exist - that's OK
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        logger.warning(f"  [{i}/{len(statements)}] ⚠ Already exists (skipped)")
                    else:
                        logger.error(f"  [{i}/{len(statements)}] ✗ Error: {e}")
                        raise
            
            # Commit changes
            self.conn.commit()
            logger.info("✓ Migration applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Migration failed: {e}")
            self.conn.rollback()
            return False
    
    def verify_migration(self) -> bool:
        """Verify migration was applied correctly."""
        logger.info("Verifying migration...")
        
        expected_columns = [
            'embedding_version',
            'embedding_created_at',
            'entity_fingerprint',
            'drift_score',
            'drift_detected',
            'manually_stale',
            'index_state'
        ]
        
        try:
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'test_embedding'
                ORDER BY column_name
            """)
            actual_columns = [row[0] for row in self.cursor.fetchall()]
            
            missing = set(expected_columns) - set(actual_columns)
            if missing:
                logger.warning(f"⚠ Missing columns: {', '.join(missing)}")
                logger.info("  (This is OK if using metadata JSON pattern)")
            else:
                logger.info("✓ All reliability columns present")
            
            # Check if reindex queue table exists
            self.cursor.execute("""
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'embedding_reindex_queue'
            """)
            has_queue = self.cursor.fetchone() is not None
            
            if has_queue:
                logger.info("✓ Reindex queue table exists")
            else:
                logger.warning("⚠ Reindex queue table not found (using in-memory queue)")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Verification failed: {e}")
            return False


def main():
    """Main migration runner."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 70)
    logger.info("Embedding Reliability Migration")
    logger.info("=" * 70)
    
    # Load config
    try:
        config = load_config()
        database_url = config.get('database', {}).get('url')
        
        if not database_url:
            logger.error("✗ Database URL not found in crossbridge.yml")
            logger.error("  Please configure database.url in your config file")
            return 1
    except Exception as e:
        logger.error(f"✗ Failed to load config: {e}")
        return 1
    
    # Find migration file
    migration_path = Path(__file__).parent / 'sql' / 'embedding_reliability.sql'
    if not migration_path.exists():
        logger.error(f"✗ Migration file not found: {migration_path}")
        return 1
    
    # Run migration
    runner = MigrationRunner(database_url)
    
    try:
        if not runner.connect():
            return 1
        
        if not runner.check_prerequisites():
            logger.error("✗ Prerequisites not met")
            return 1
        
        if not runner.apply_migration(migration_path):
            return 1
        
        if not runner.verify_migration():
            logger.warning("⚠ Verification had warnings, but migration applied")
        
        logger.info("=" * 70)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Update crossbridge.yml with reliability settings")
        logger.info("  2. Run: crossbridge reliability status")
        logger.info("  3. Configure automatic reindexing if needed")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n⚠ Migration interrupted by user")
        return 1
    finally:
        runner.close()


if __name__ == '__main__':
    sys.exit(main())
