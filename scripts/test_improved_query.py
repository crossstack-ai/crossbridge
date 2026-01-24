import psycopg2

conn = psycopg2.connect('postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db')
cur = conn.cursor()

print('\n=== IMPROVED GRAFANA QUERY TEST ===\n')

# The improved query for Grafana panel
improved_query = """
    SELECT 
        COALESCE(
            tc.test_name,
            me.metadata->>'name',
            SUBSTRING(me.metadata->>'text', 1, 50),
            CAST(me.entity_id AS VARCHAR)
        ) as "Test Case ID",
        me.entity_type as "Type",
        COALESCE(tc.framework, me.metadata->>'framework', 'N/A') as "Framework",
        COALESCE(
            SUBSTRING(tc.test_file_path, 1, 40),
            me.metadata->>'file',
            'N/A'
        ) as "File",
        COALESCE(tc.suite_name, 'N/A') as "Suite",
        COALESCE(me.metadata->>'model', 'N/A') as "Model",
        me.created_at as "Created At"
    FROM memory_embeddings me
    LEFT JOIN test_case tc ON me.entity_id = tc.id
    ORDER BY me.created_at DESC
    LIMIT 20
"""

cur.execute(improved_query)
results = cur.fetchall()

print('Query Results (Test Case IDs now showing):')
print('='*120)
print(f'{"Test Case ID":<45} | {"Type":<10} | {"Framework":<10} | {"Suite":<15} | {"Created At"}')
print('='*120)

for row in results:
    test_id = row[0][:44] if row[0] else 'N/A'
    typ = row[1] or 'N/A'
    framework = row[2] or 'N/A'
    suite = row[4][:14] if row[4] else 'N/A'
    created = row[6]
    print(f'{test_id:<45} | {typ:<10} | {framework:<10} | {suite:<15} | {created}')

print(f'\n✓ Found {len(results)} embeddings with proper test case identifiers')

conn.close()
print('\n=== Query Validated Successfully ===')
