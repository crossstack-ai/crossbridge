"""
Database Migration: Add Version Tracking Columns

This script adds application_version, product_name, and environment columns
to the test_execution_event table for coverage-by-version analysis.

Run this script if you have an existing CrossBridge database that needs
to be updated with version tracking support.

Usage:
    python scripts/migrate_add_version_tracking.py
"""

import psycopg2
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection from environment variables"""
    host = os.getenv('CROSSBRIDGE_DB_HOST', '10.55.12.99')
    port = os.getenv('CROSSBRIDGE_DB_PORT', '5432')
    database = os.getenv('CROSSBRIDGE_DB_NAME', 'udp-native-webservices-automation')
    user = os.getenv('CROSSBRIDGE_DB_USER', 'postgres')
    password = os.getenv('CROSSBRIDGE_DB_PASSWORD', 'admin')
    
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    logger.info(f"Connecting to database: {host}:{port}/{database}")
    
    return psycopg2.connect(connection_string)


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in the table"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    """, (table_name, column_name))
    
    return cursor.fetchone() is not None


def migrate():
    """Apply migration to add version tracking columns"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Starting migration: Add version tracking columns")
        
        # Check if columns already exist
        columns_to_add = [
            ('application_version', 'TEXT'),
            ('product_name', 'TEXT'),
            ('environment', 'TEXT')
        ]
        
        columns_added = []
        columns_skipped = []
        
        for column_name, column_type in columns_to_add:
            if check_column_exists(cursor, 'test_execution_event', column_name):
                logger.info(f"  ⏭  Column '{column_name}' already exists, skipping")
                columns_skipped.append(column_name)
            else:
                logger.info(f"  ➕ Adding column '{column_name}' ({column_type})")
                cursor.execute(f"""
                    ALTER TABLE test_execution_event 
                    ADD COLUMN {column_name} {column_type}
                """)
                columns_added.append(column_name)
        
        # Create indexes for new columns
        indexes_to_create = [
            ('idx_app_version', 'application_version'),
            ('idx_product_name', 'product_name'),
            ('idx_environment', 'environment')
        ]
        
        indexes_created = []
        
        for index_name, column_name in indexes_to_create:
            logger.info(f"  🔍 Creating index '{index_name}' on '{column_name}'")
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name} 
                ON test_execution_event({column_name})
            """)
            indexes_created.append(index_name)
        
        # Commit changes
        conn.commit()
        
        logger.info("\n✅ Migration completed successfully!")
        logger.info(f"  • Columns added: {len(columns_added)}")
        logger.info(f"  • Columns skipped: {len(columns_skipped)}")
        logger.info(f"  • Indexes created: {len(indexes_created)}")
        
        if columns_added:
            logger.info(f"\n📝 New columns:")
            for col in columns_added:
                logger.info(f"  - {col}")
        
        logger.info("\n🎯 Next Steps:")
        logger.info("  1. Update crossbridge.yaml with version tracking config")
        logger.info("  2. Set environment variables:")
        logger.info("     export APP_VERSION=$(git describe --tags)")
        logger.info("     export PRODUCT_NAME='MyApp'")
        logger.info("     export ENVIRONMENT='staging'")
        logger.info("  3. Run tests to start collecting version-specific data")
        logger.info("  4. View coverage by version in Grafana dashboards")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False


def rollback():
    """Rollback migration by removing version tracking columns"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Starting rollback: Remove version tracking columns")
        
        # Drop indexes
        indexes_to_drop = ['idx_app_version', 'idx_product_name', 'idx_environment']
        
        for index_name in indexes_to_drop:
            logger.info(f"  🗑️  Dropping index '{index_name}'")
            cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
        
        # Drop columns
        columns_to_drop = ['application_version', 'product_name', 'environment']
        
        for column_name in columns_to_drop:
            if check_column_exists(cursor, 'test_execution_event', column_name):
                logger.info(f"  🗑️  Dropping column '{column_name}'")
                cursor.execute(f"""
                    ALTER TABLE test_execution_event 
                    DROP COLUMN {column_name}
                """)
            else:
                logger.info(f"  ⏭  Column '{column_name}' doesn't exist, skipping")
        
        conn.commit()
        
        logger.info("\n✅ Rollback completed successfully!")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CrossBridge Version Tracking Migration")
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback migration (remove version tracking columns)'
    )
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback()
    else:
        success = migrate()
    
    sys.exit(0 if success else 1)
