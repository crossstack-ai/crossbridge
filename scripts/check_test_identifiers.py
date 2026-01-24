import psycopg2
import json

conn = psycopg2.connect('postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db')
cur = conn.cursor()

print('\n=== CHECKING METADATA AND TEST CASE IDENTIFIERS ===\n')

print('1. Memory Embeddings Metadata Structure:')
cur.execute("""
    SELECT entity_id, entity_type, metadata 
    FROM memory_embeddings 
    ORDER BY created_at DESC 
    LIMIT 5
""")
for row in cur.fetchall():
    print(f'\n  Entity ID: {row[0]}')
    print(f'  Type: {row[1]}')
    print(f'  Metadata: {json.dumps(row[2], indent=4) if row[2] else "None"}')

print('\n\n2. Test Case Table (for linking):')
cur.execute("""
    SELECT id, test_name, framework, file_path 
    FROM test_case 
    LIMIT 5
""")
print('  ID | Test Name | Framework | File Path')
print('  ' + '-'*80)
for row in cur.fetchall():
    print(f'  {row[0]} | {row[1][:30]}... | {row[2]} | {row[3][:30]}...')

print('\n\n3. Test Query for Grafana Panel (with JOIN):')
cur.execute("""
    SELECT 
        tc.test_name as "Test Case",
        tc.framework as "Framework",
        me.entity_type as "Entity Type",
        tc.file_path as "File Path",
        me.metadata->>'model' as "Embedding Model",
        me.created_at as "Created At"
    FROM memory_embeddings me
    LEFT JOIN test_case tc ON me.entity_id = tc.id
    WHERE me.entity_type IN ('test', 'test_case')
    ORDER BY me.created_at DESC
    LIMIT 10
""")

print('\n  Results:')
for row in cur.fetchall():
    print(f'  {row[0][:40] if row[0] else "N/A":<40} | {row[1]:<10} | {row[2]:<12} | {row[5]}')

conn.close()
print('\n=== Analysis Complete ===')
