import psycopg2

conn = psycopg2.connect('postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db')
cur = conn.cursor()

print('\n=== DATABASE SCHEMA ANALYSIS ===\n')

print('1. Test_case table columns:')
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'test_case'
    ORDER BY ordinal_position
""")
for col in cur.fetchall():
    print(f'  {col[0]}: {col[1]}')

print('\n2. Sample test_case data:')
cur.execute("SELECT * FROM test_case LIMIT 3")
cols = [desc[0] for desc in cur.description]
print(f'  Columns: {", ".join(cols)}')
for row in cur.fetchall():
    print(f'\n  Record:')
    for i, col in enumerate(cols):
        val = str(row[i])[:50] if row[i] else 'NULL'
        print(f'    {col}: {val}')

print('\n3. Improved query for Grafana (with test names):')
improved_query = """
    SELECT 
        CASE 
            WHEN tc.test_name IS NOT NULL THEN tc.test_name
            WHEN me.metadata->>'name' IS NOT NULL THEN me.metadata->>'name'
            WHEN me.metadata->>'text' IS NOT NULL THEN LEFT(me.metadata->>'text', 50)
            ELSE CAST(me.entity_id AS VARCHAR)
        END as "Test Case ID",
        me.entity_type as "Type",
        tc.framework as "Framework",
        tc.source_file as "File",
        me.metadata->>'model' as "Model",
        me.created_at as "Time"
    FROM memory_embeddings me
    LEFT JOIN test_case tc ON me.entity_id = tc.id
    ORDER BY me.created_at DESC
    LIMIT 20
"""

cur.execute(improved_query)
print('\n  Results (first 10):')
print('  Test Case ID | Type | Framework | File | Time')
print('  ' + '-'*100)
for i, row in enumerate(cur.fetchall()[:10]):
    test_id = row[0][:40] if row[0] else 'N/A'
    typ = row[1] or 'N/A'
    framework = row[2] or 'N/A'
    file = row[3][:20] if row[3] else 'N/A'
    time = row[5]
    print(f'  {test_id:<40} | {typ:<8} | {framework:<10} | {file:<20} | {time}')

conn.close()
print('\n=== Analysis Complete ===')
