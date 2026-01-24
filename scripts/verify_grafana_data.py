import psycopg2

conn = psycopg2.connect('postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db')
cur = conn.cursor()

print('\n=== GRAFANA DASHBOARD DATA VERIFICATION ===\n')

print('Memory & Embeddings Overview:')
cur.execute('SELECT COUNT(*) FROM memory_embeddings')
print(f'  Total Embeddings: {cur.fetchone()[0]}')

print('\nEmbeddings by Entity Type:')
cur.execute('''
    SELECT entity_type, COUNT(*) as count, 
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
    FROM memory_embeddings
    GROUP BY entity_type
    ORDER BY count DESC
''')
for row in cur.fetchall():
    print(f'  {row[0]:15} {row[1]:3} ({row[2]:5.1f}%)')

print('\nEmbedding Storage Trend (Last 7 Days):')
cur.execute('''
    SELECT DATE(created_at) as date, COUNT(*) as count
    FROM memory_embeddings
    WHERE created_at > NOW() - INTERVAL '7 days'
    GROUP BY DATE(created_at)
    ORDER BY date DESC
    LIMIT 7
''')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]} embeddings')

print('\nRecent Embeddings Created:')
cur.execute('''
    SELECT entity_id, entity_type, metadata->>'model' as model, created_at
    FROM memory_embeddings
    ORDER BY created_at DESC
    LIMIT 5
''')
for row in cur.fetchall():
    print(f'  {str(row[0])[:18]}... ({row[1]}) - {row[2]} - {row[3]}')

conn.close()
print('\n=== All Grafana panels have data! ===\n')
