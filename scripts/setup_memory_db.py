"""
Database schema setup for CrossBridge Memory system.

This script creates the necessary tables and indexes for pgvector storage.
Run this before using the memory/semantic search features.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_memory_schema(connection_string: str, dimension: int = 1536):
    """
    Set up the memory schema in PostgreSQL.
    
    Args:
        connection_string: PostgreSQL connection string
        dimension: Vector dimension (must match embedding provider)
    """
    logger.info("Setting up memory schema...")

    engine = create_engine(connection_string)

    with engine.connect() as conn:
        # Enable pgvector extension
        logger.info("Enabling pgvector extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

        # Create memory_embeddings table
        logger.info(f"Creating memory_embeddings table (dimension={dimension})...")
        conn.execute(
            text(
                f"""
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                text TEXT NOT NULL,
                metadata JSONB DEFAULT '{{}}'::jsonb,
                embedding VECTOR({dimension}),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )
        conn.commit()

        # Create indexes for performance
        logger.info("Creating indexes...")

        # Type index
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memory_embeddings(type)
        """
            )
        )

        # Metadata index (GIN for JSON queries)
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_memory_metadata 
            ON memory_embeddings USING GIN(metadata jsonb_path_ops)
        """
            )
        )

        # Vector similarity index (HNSW for fast approximate search)
        # This is crucial for performance on large datasets
        logger.info("Creating HNSW vector index (this may take a moment)...")
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_memory_embedding_cosine 
            ON memory_embeddings USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """
            )
        )

        # Alternative: IVFFlat index (faster build, slower query)
        # Uncomment if HNSW is too slow to build
        # conn.execute(text("""
        #     CREATE INDEX IF NOT EXISTS idx_memory_embedding_ivfflat
        #     ON memory_embeddings USING ivfflat (embedding vector_cosine_ops)
        #     WITH (lists = 100)
        # """))

        # Timestamp index for filtering by date
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_memory_created_at 
            ON memory_embeddings(created_at)
        """
            )
        )

        conn.commit()

        # Verify setup
        result = conn.execute(
            text(
                """
            SELECT COUNT(*) as count FROM information_schema.tables 
            WHERE table_name = 'memory_embeddings'
        """
            )
        )
        count = result.scalar()

        if count > 0:
            logger.info("✅ Memory schema setup complete!")

            # Show table info
            result = conn.execute(
                text("SELECT COUNT(*) FROM memory_embeddings")
            )
            record_count = result.scalar()
            logger.info(f"📊 Current records: {record_count}")

        else:
            logger.error("❌ Failed to create memory_embeddings table")
            return False

    return True


def drop_memory_schema(connection_string: str):
    """
    Drop the memory schema (use with caution!).
    
    Args:
        connection_string: PostgreSQL connection string
    """
    logger.warning("Dropping memory schema...")

    engine = create_engine(connection_string)

    with engine.connect() as conn:
        # Drop indexes first
        conn.execute(text("DROP INDEX IF EXISTS idx_memory_type CASCADE"))
        conn.execute(text("DROP INDEX IF EXISTS idx_memory_metadata CASCADE"))
        conn.execute(
            text("DROP INDEX IF EXISTS idx_memory_embedding_cosine CASCADE")
        )
        conn.execute(text("DROP INDEX IF EXISTS idx_memory_created_at CASCADE"))

        # Drop table
        conn.execute(text("DROP TABLE IF EXISTS memory_embeddings CASCADE"))

        conn.commit()

    logger.info("✅ Memory schema dropped")


def upgrade_schema(connection_string: str):
    """
    Upgrade existing schema to latest version.
    
    Args:
        connection_string: PostgreSQL connection string
    """
    logger.info("Upgrading memory schema...")

    engine = create_engine(connection_string)

    with engine.connect() as conn:
        # Add any missing columns
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE memory_embeddings 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
                )
            )
            conn.commit()
            logger.info("✅ Schema upgrade complete")

        except Exception as e:
            logger.error(f"Schema upgrade failed: {e}")
            return False

    return True


if __name__ == "__main__":
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="Setup CrossBridge Memory database schema")
    parser.add_argument(
        "--connection",
        "-c",
        help="PostgreSQL connection string (overrides config file)",
    )
    parser.add_argument(
        "--dimension",
        "-d",
        type=int,
        default=1536,
        help="Vector dimension (default: 1536 for OpenAI text-embedding-3-small)",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing schema (WARNING: deletes all data)",
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Upgrade existing schema to latest version",
    )

    args = parser.parse_args()

    # Get connection string from args or config file
    if args.connection:
        connection_string = args.connection
    else:
        # Try to load from crossbridge.yml
        config_path = Path("crossbridge.yml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

            memory_config = config.get("memory", {})
            store_config = memory_config.get("vector_store", {})

            if "connection_string" in store_config:
                connection_string = store_config["connection_string"]
            else:
                logger.error("No connection string found in config or arguments")
                logger.info("Usage: python setup_memory_db.py --connection 'postgresql://user:pass@host:port/db'")
                sys.exit(1)
        else:
            logger.error("crossbridge.yml not found and no connection string provided")
            sys.exit(1)

    # Execute requested operation
    try:
        if args.drop:
            if input("⚠️  Are you sure you want to drop all memory data? (yes/no): ") == "yes":
                drop_memory_schema(connection_string)
            else:
                logger.info("Cancelled")
                sys.exit(0)

        elif args.upgrade:
            success = upgrade_schema(connection_string)
            sys.exit(0 if success else 1)

        else:
            success = setup_memory_schema(connection_string, args.dimension)
            sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)
