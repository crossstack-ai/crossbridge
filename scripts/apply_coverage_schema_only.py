#!/usr/bin/env python3
"""
Apply only the behavioral coverage schema to PostgreSQL database.

Usage:
    python scripts/apply_coverage_schema_only.py
"""

import psycopg2
from pathlib import Path
import sys


def apply_schema(connection_string: str, schema_file: Path) -> None:
    """Apply SQL schema to database, handling existing objects gracefully."""
    
    # Read schema file
    print(f"Reading schema from: {schema_file}")
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Connect to database
    print(f"Connecting to database...")
    conn = psycopg2.connect(connection_string)
    conn.autocommit = False
    
    try:
        cursor = conn.cursor()
        
        # Execute schema as a whole with proper error handling
        print(f"Applying schema...")
        try:
            cursor.execute(schema_sql)
            conn.commit()
            print(f"✅ Schema applied successfully!")
        except psycopg2.errors.DuplicateTable as e:
            conn.rollback()
            print(f"⚠️  Some tables already exist: {e}")
        except psycopg2.errors.DuplicateObject as e:
            conn.rollback()
            print(f"⚠️  Some objects already exist: {e}")
        except psycopg2.Error as e:
            conn.rollback()
            print(f"❌ Database error: {e}")
            raise
        
        # Verify tables created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%coverage%' OR table_name LIKE 'feature%' OR table_name LIKE 'git_change%')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\nCoverage-related tables ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Verify views created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%coverage%' OR table_name LIKE '%feature%' OR table_name LIKE '%impact%')
            ORDER BY table_name;
        """)
        
        views = cursor.fetchall()
        if views:
            print(f"\nCoverage-related views ({len(views)}):")
            for view in views:
                print(f"  - {view[0]}")
        
        cursor.close()
        
    finally:
        conn.close()
        print("\nDatabase connection closed.")


def main():
    """Main entry point."""
    
    # Connection details
    connection_string = "postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation"
    
    # Coverage schema file
    coverage_schema = Path(__file__).parent.parent / "core" / "coverage" / "functional_coverage_schema.sql"
    
    if not coverage_schema.exists():
        print(f"❌ Error: Coverage schema file not found: {coverage_schema}")
        sys.exit(1)
    
    try:
        print("=" * 70)
        print("Applying Behavioral Coverage Schema to PostgreSQL")
        print("=" * 70)
        apply_schema(connection_string, coverage_schema)
        
        print("\n" + "=" * 70)
        print("✅ Schema deployment completed successfully!")
        print("=" * 70)
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database connection error: {e}")
        print("\nPlease verify:")
        print("  - Database server is running")
        print("  - Connection details are correct")
        print("  - Network access to database server")
        sys.exit(1)
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
