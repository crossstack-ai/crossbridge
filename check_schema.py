import psycopg2

conn = psycopg2.connect(
    host='10.60.67.247',
    port=5432,
    database='cbridge-unit-test-db',
    user='postgres',
    password='admin'
)

cursor = conn.cursor()

for table in ['runs', 'tests', 'steps', 'http_calls']:
    cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'crossbridge' 
        AND table_name = '{table}' 
        ORDER BY ordinal_position
    """)
    print(f'\n{table} table:')
    for row in cursor.fetchall():
        print(f'  - {row[0]} ({row[1]})')

cursor.close()
conn.close()
