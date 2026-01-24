#!/usr/bin/env python3
"""
Apply behavioral coverage schema to PostgreSQL database.

Usage:
    python scripts/apply_coverage_schema.py
"""

import psycopg2
from pathlib import Path
import sys


def apply_schema(connection_string: str, schema_file: Path) -> None:
    """Apply SQL schema to database."""
    
    # Read schema file
    print(f"Reading schema from: {schema_file}")
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Connect to database
    print(f"Connecting to database...")
    conn = psycopg2.connect(connection_string)
    conn.autocommit = True
    
    try:
        cursor = conn.cursor()
        
        # Execute schema (errors will be caught)
        print("Applying schema...")
        try:
            cursor.execute(schema_sql)
        except psycopg2.errors.DuplicateTable as e:
            print(f"⚠️  Some tables already exist (this is OK): {e}")
        except psycopg2.errors.DuplicateObject as e:
            print(f"⚠️  Some objects already exist (this is OK): {e}")
        
        # Verify tables created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%coverage%'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n✅ Schema applied successfully!")
        print(f"\nCreated/Updated tables ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Verify views created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%coverage%'
            ORDER BY table_name;
        """)
        
        views = cursor.fetchall()
        if views:
            print(f"\nCreated/Updated views ({len(views)}):")
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
    
    # Apply main schema first (has test_case table)
    main_schema = Path(__file__).parent.parent / "persistence" / "schema.sql"
    coverage_schema = Path(__file__).parent.parent / "core" / "coverage" / "functional_coverage_schema.sql"
    
    if not main_schema.exists():
        print(f"❌ Error: Main schema file not found: {main_schema}")
        sys.exit(1)
    
    if not coverage_schema.exists():
        print(f"❌ Error: Coverage schema file not found: {coverage_schema}")
        sys.exit(1)
    
    try:
        # Apply main schema first
        print("=" * 60)
        print("Step 1: Applying main CrossBridge schema...")
        print("=" * 60)
        apply_schema(connection_string, main_schema)
        
        # Then apply coverage schema
        print("\n" + "=" * 60)
        print("Step 2: Applying behavioral coverage schema...")
        print("=" * 60)
        apply_schema(connection_string, coverage_schema)
        
        print("\n" + "=" * 60)
        print("✅ All schemas deployed successfully!")
        print("=" * 60)
        
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
        sys.exit(1)


if __name__ == "__main__":
    main()
