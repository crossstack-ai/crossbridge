"""
Setup script for CrossBridge comprehensive database schema.
Sets up PostgreSQL with TimescaleDB, pgvector, and all required tables.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
import psycopg2
from psycopg2 import sql

logger = logging.getLogger(__name__)


def read_schema_file(schema_path: Path) -> str:
    """Read SQL schema file."""
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r') as f:
        return f.read()


def check_extensions(conn):
    """Check if required extensions are available."""
    logger.info("Checking required PostgreSQL extensions...")
    
    required_extensions = {
        "uuid-ossp": "UUID generation",
        "vector": "pgvector for embeddings",
        "timescaledb": "TimescaleDB for time-series"
    }
    
    with conn.cursor() as cur:
        for ext_name, description in required_extensions.items():
            try:
                cur.execute(f"CREATE EXTENSION IF NOT EXISTS \"{ext_name}\" CASCADE")
                logger.info(f"✅ {description} ({ext_name})")
            except Exception as e:
                logger.error(f"❌ Failed to enable {ext_name}: {e}")
                if ext_name == "timescaledb":
                    logger.warning("TimescaleDB not available. Time-series features will be limited.")
                elif ext_name == "vector":
                    logger.error("pgvector is required for semantic search. Please install it.")
                    raise
                else:
                    logger.warning(f"Extension {ext_name} not available: {e}")
    
    conn.commit()


def setup_schema(conn, schema_sql: str, dry_run: bool = False):
    """Execute schema setup SQL."""
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("="*60)
        logger.info(schema_sql)
        logger.info("="*60)
        return
    
    logger.info("Executing schema setup...")
    
    try:
        with conn.cursor() as cur:
            # Execute the schema SQL
            cur.execute(schema_sql)
        
        conn.commit()
        logger.info("✅ Schema setup completed successfully")
    
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Schema setup failed: {e}", exc_info=True)
        raise


def verify_schema(conn):
    """Verify that all expected tables exist."""
    logger.info("\nVerifying schema...")
    
    expected_tables = [
        "discovery_run",
        "test_case",
        "page_object",
        "test_page_mapping",
        "test_execution",
        "flaky_test",
        "flaky_test_history",
        "feature",
        "code_unit",
        "test_feature_map",
        "test_code_coverage_map",
        "memory_embeddings",
        "git_change_event",
        "observability_event"
    ]
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        existing_tables = {row[0] for row in cur.fetchall()}
    
    missing_tables = set(expected_tables) - existing_tables
    extra_tables = existing_tables - set(expected_tables)
    
    if missing_tables:
        logger.warning(f"⚠️  Missing tables: {', '.join(missing_tables)}")
    
    logger.info(f"\n✅ Found {len(existing_tables)} tables:")
    for table in sorted(existing_tables):
        icon = "  ✓" if table in expected_tables else "  +"
        logger.info(f"{icon} {table}")
    
    # Check for hypertables (TimescaleDB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT hypertable_name 
                FROM timescaledb_information.hypertables
            """)
            hypertables = [row[0] for row in cur.fetchall()]
        
        if hypertables:
            logger.info(f"\n✅ TimescaleDB hypertables: {', '.join(hypertables)}")
        else:
            logger.warning("⚠️  No TimescaleDB hypertables found")
    except Exception:
        logger.warning("⚠️  Could not check TimescaleDB hypertables (extension may not be installed)")
    
    # Check for continuous aggregates
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT view_name 
                FROM timescaledb_information.continuous_aggregates
            """)
            caggs = [row[0] for row in cur.fetchall()]
        
        if caggs:
            logger.info(f"✅ Continuous aggregates: {', '.join(caggs)}")
    except Exception:
        pass
    
    # Check for pgvector indexes
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT indexname, tablename
                FROM pg_indexes
                WHERE indexname LIKE '%vector%' OR indexname LIKE '%embedding%'
            """)
            vector_indexes = cur.fetchall()
        
        if vector_indexes:
            logger.info(f"\n✅ Vector indexes:")
            for idx_name, tbl_name in vector_indexes:
                logger.info(f"  ✓ {idx_name} on {tbl_name}")
        else:
            logger.warning("⚠️  No vector indexes found")
    except Exception as e:
        logger.warning(f"⚠️  Could not check vector indexes: {e}")
    
    return len(missing_tables) == 0


def drop_all_tables(conn, confirm: bool = False):
    """Drop all CrossBridge tables (dangerous!)."""
    if not confirm:
        response = input("⚠️  This will DROP ALL TABLES! Type 'YES' to confirm: ")
        if response != "YES":
            logger.info("Operation cancelled")
            return
    
    logger.warning("Dropping all tables...")
    
    with conn.cursor() as cur:
        # Get all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        
        # Drop each table
        for table in tables:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"  Dropped {table}")
            except Exception as e:
                logger.warning(f"  Could not drop {table}: {e}")
    
    conn.commit()
    logger.info("✅ All tables dropped")


def get_connection_string(args) -> str:
    """Get database connection string from args or environment."""
    if args.connection:
        return args.connection
    
    # Try environment variable
    conn_string = os.getenv("CROSSBRIDGE_DB_URL")
    if conn_string:
        return conn_string
    
    # Build from components
    host = os.getenv("CROSSBRIDGE_DB_HOST", "localhost")
    port = os.getenv("CROSSBRIDGE_DB_PORT", "5432")
    dbname = os.getenv("CROSSBRIDGE_DB_NAME", "crossbridge")
    user = os.getenv("CROSSBRIDGE_DB_USER", "postgres")
    password = os.getenv("CROSSBRIDGE_DB_PASSWORD", "")
    
    if not password:
        logger.error("Database password not provided. Set CROSSBRIDGE_DB_PASSWORD or use --connection")
        sys.exit(1)
    
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup CrossBridge comprehensive database schema"
    )
    parser.add_argument(
        "--connection",
        help="PostgreSQL connection string (default: from CROSSBRIDGE_DB_URL env var)"
    )
    parser.add_argument(
        "--schema-file",
        default="scripts/comprehensive_schema.sql",
        help="Path to schema SQL file"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all existing tables before setup"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL without executing"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing schema"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Get connection string
    conn_string = get_connection_string(args)
    
    # Hide password in logs
    safe_conn = conn_string.split('@')[-1] if '@' in conn_string else conn_string
    logger.info(f"Connecting to database: {safe_conn}")
    
    # Connect to database
    try:
        conn = psycopg2.connect(conn_string)
        logger.info("✅ Connected to database")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        # Verify only mode
        if args.verify_only:
            verify_schema(conn)
            return
        
        # Drop tables if requested
        if args.drop:
            drop_all_tables(conn, confirm=args.dry_run)
        
        # Check extensions
        if not args.dry_run:
            check_extensions(conn)
        
        # Read schema file
        schema_path = Path(args.schema_file)
        logger.info(f"Reading schema from: {schema_path}")
        schema_sql = read_schema_file(schema_path)
        
        # Setup schema
        setup_schema(conn, schema_sql, dry_run=args.dry_run)
        
        # Verify schema
        if not args.dry_run:
            success = verify_schema(conn)
            
            if success:
                logger.info("\n" + "="*60)
                logger.info("✅ Database setup completed successfully!")
                logger.info("="*60)
                logger.info("\nNext steps:")
                logger.info("1. Run: python scripts/generate_test_data.py")
                logger.info("2. Import Grafana dashboard: grafana/dashboards/crossbridge_overview.json")
                logger.info("3. Configure Grafana datasource to connect to this database")
            else:
                logger.warning("\n⚠️  Some tables may be missing. Check the logs above.")
    
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
