"""
Database connection and session management for CrossBridge persistence.

Optional PostgreSQL persistence for discovery metadata.
Works gracefully when DB is not configured.
"""

import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration from environment."""
    
    @staticmethod
    def get_db_url() -> Optional[str]:
        """
        Get database URL from environment.
        
        Returns:
            Database URL or None if not configured.
            
        Environment variables (in priority order):
            1. CROSSBRIDGE_DB_URL - Full connection string
            2. Individual components: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        # Try full URL first
        db_url = os.environ.get("CROSSBRIDGE_DB_URL")
        if db_url:
            return db_url
        
        # Try individual components
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        name = os.environ.get("DB_NAME", "crossbridge")
        user = os.environ.get("DB_USER", "crossbridge")
        password = os.environ.get("DB_PASSWORD")
        
        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        
        return None
    
    @staticmethod
    def is_configured() -> bool:
        """Check if database is configured."""
        return DatabaseConfig.get_db_url() is not None


def create_session(db_url: Optional[str] = None) -> Optional[Session]:
    """
    Create a database session.
    
    Args:
        db_url: Database URL. If None, reads from environment.
        
    Returns:
        SQLAlchemy session or None if DB not configured.
        
    Example:
        >>> session = create_session()
        >>> if session:
        ...     # Use session
        ...     session.commit()
        ...     session.close()
    """
    if db_url is None:
        db_url = DatabaseConfig.get_db_url()
    
    if db_url is None:
        logger.debug("Database not configured. Persistence disabled.")
        return None
    
    try:
        # Create engine with connection pooling
        engine = create_engine(
            db_url,
            future=True,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,          # Set to True for SQL debugging
            poolclass=NullPool if "sqlite" in db_url else None  # No pooling for SQLite
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        logger.info(f"Database connection established: {db_url.split('@')[-1] if '@' in db_url else 'local'}")
        return Session()
    
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.debug("Continuing without persistence...")
        return None


def init_database(db_url: Optional[str] = None) -> bool:
    """
    Initialize database schema.
    
    Args:
        db_url: Database URL. If None, reads from environment.
        
    Returns:
        True if schema created/verified, False otherwise.
        
    Example:
        >>> if init_database():
        ...     print("Database ready")
    """
    session = create_session(db_url)
    if session is None:
        return False
    
    try:
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        
        if not os.path.exists(schema_path):
            logger.warning(f"Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema in a transaction
        session.execute(text(schema_sql))
        session.commit()
        
        logger.info("Database schema initialized successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        session.rollback()
        return False
    
    finally:
        session.close()


def check_database_health() -> dict:
    """
    Check database connection and health.
    
    Returns:
        Dictionary with health status.
        
    Example:
        >>> health = check_database_health()
        >>> if health['connected']:
        ...     print(f"Tables: {health['table_count']}")
    """
    session = create_session()
    
    if session is None:
        return {
            "configured": False,
            "connected": False,
            "message": "Database not configured"
        }
    
    try:
        # Check connection
        session.execute(text("SELECT 1"))
        
        # Count tables
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        table_count = result.scalar()
        
        # Check key tables exist
        key_tables = ['discovery_run', 'test_case', 'page_object', 'test_page_mapping', 'discovery_test_case']
        existing_tables = []
        
        for table in key_tables:
            result = session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                )
            """))
            if result.scalar():
                existing_tables.append(table)
        
        return {
            "configured": True,
            "connected": True,
            "table_count": table_count,
            "key_tables": existing_tables,
            "schema_complete": len(existing_tables) == len(key_tables),
            "message": "Database healthy" if len(existing_tables) == len(key_tables) else "Schema incomplete"
        }
    
    except Exception as e:
        return {
            "configured": True,
            "connected": False,
            "error": str(e),
            "message": f"Connection failed: {e}"
        }
    
    finally:
        session.close()
