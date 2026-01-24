#!/usr/bin/env python3
"""Check existing database schema."""

import psycopg2

conn = psycopg2.connect('postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation')
cur = conn.cursor()

# Check existing tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [t[0] for t in cur.fetchall()]

print("Existing tables in database:")
for t in tables:
    print(f"  - {t}")

print(f"\nTotal: {len(tables)} tables")

# Check if test_case table exists
if 'test_case' in tables:
    print("\n✅ test_case table exists")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='test_case' ORDER BY ordinal_position")
    columns = cur.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")
else:
    print("\n❌ test_case table does NOT exist - need to apply main schema first")

cur.close()
conn.close()
