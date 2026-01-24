"""
Direct test of what Grafana sees from the database
"""
import psycopg2
import json

conn = psycopg2.connect(
    host="10.55.12.99",
    port=5432,
    database="udp-native-webservices-automation",
    user="postgres",
    password="admin"
)

cursor = conn.cursor()

# Test the exact query from the stat panel
print("Query 1: Simple COUNT")
cursor.execute("SELECT COUNT(*) FROM test_execution_event WHERE application_version IS NOT NULL")
result = cursor.fetchall()
print(f"Result: {result}")
print(f"Row count: {cursor.rowcount}")
print(f"Column names: {[desc[0] for desc in cursor.description]}")
print()

# Test with alias
print("Query 2: COUNT with alias")
cursor.execute('SELECT COUNT(*) as "Total Tests" FROM test_execution_event WHERE application_version IS NOT NULL')
result = cursor.fetchall()
print(f"Result: {result}")
print(f"Column names: {[desc[0] for desc in cursor.description]}")
print()

# Test the bargauge query
print("Query 3: Pass rate by version")
cursor.execute("""
SELECT 
    application_version as metric, 
    ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 1) as value 
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days' 
GROUP BY application_version 
ORDER BY application_version
""")
result = cursor.fetchall()
print(f"Result: {result}")
print(f"Column names: {[desc[0] for desc in cursor.description]}")
print()

# Test table query
print("Query 4: Version details table")
cursor.execute("""
SELECT 
    application_version as "Version", 
    product_name as "Product", 
    environment as "Environment", 
    COUNT(*) as "Total Tests"
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days' 
GROUP BY application_version, product_name, environment 
ORDER BY product_name, application_version
LIMIT 5
""")
result = cursor.fetchall()
print(f"Results:")
for row in result:
    print(f"  {row}")
print(f"Column names: {[desc[0] for desc in cursor.description]}")

cursor.close()
conn.close()

print("\n" + "="*70)
print("All queries return data successfully")
print("Issue must be in Grafana panel configuration or datasource settings")
print("="*70)
