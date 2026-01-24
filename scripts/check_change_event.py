#!/usr/bin/env python3
"""Check change_event table schema."""

import psycopg2

conn = psycopg2.connect('postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation')
cur = conn.cursor()

# Check change_event columns
cur.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name='change_event' 
    ORDER BY ordinal_position
""")
columns = cur.fetchall()

print("change_event table columns:")
for col in columns:
    print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")

cur.close()
conn.close()
