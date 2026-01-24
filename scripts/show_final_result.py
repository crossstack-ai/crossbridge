import psycopg2

conn = psycopg2.connect('postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db')
cur = conn.cursor()

print('\n' + '='*120)
print('GRAFANA PANEL: "Recent Embeddings Created" - NOW SHOWING TEST CASE IDs!')
print('='*120)

# Execute the new query
cur.execute("""
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
""")

results = cur.fetchall()

# Display header
print(f'\n{"Test Case ID":<50} | {"Type":<10} | {"Framework":<12} | {"Suite":<20}')
print('-'*120)

# Display results
for i, row in enumerate(results, 1):
    test_id = row[0][:49] if row[0] else 'N/A'
    typ = row[1][:9] if row[1] else 'N/A'
    framework = row[2][:11] if row[2] else 'N/A'
    suite = row[4][:19] if row[4] else 'N/A'
    
    print(f'{test_id:<50} | {typ:<10} | {framework:<12} | {suite:<20}')

print('-'*120)
print(f'\nShowing {len(results)} most recent embeddings')

conn.close()

print('\n' + '='*120)
print('BENEFITS:')
print('  - Test names like "test_playwright_checkout_1" instead of UUIDs')
print('  - Framework information (pytest, playwright, cucumber, testng, junit)')
print('  - Suite names for better organization')
print('  - File paths showing test location')
print('  - Similar to TestRail/Zephyr test management experience')
print('='*120 + '\n')
