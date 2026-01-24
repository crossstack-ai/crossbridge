"""
Test exactly what format Grafana panels need
"""
import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host="10.55.12.99",
    port=5432,
    database="udp-native-webservices-automation",
    user="postgres",
    password="admin"
)

cursor = conn.cursor()

print("=" * 70)
print("TESTING DIFFERENT QUERY FORMATS FOR GRAFANA")
print("=" * 70)

# Test 1: Simple count (what you tried)
print("\n1. Simple COUNT with time:")
query1 = """
SELECT 
    NOW() as time,
    COUNT(*) as value
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days'
"""
cursor.execute(query1)
result = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
print(f"   Columns: {columns}")
print(f"   Result: {result}")
print(f"   Row count: {len(result)}")

# Test 2: Without time (for Stat panel)
print("\n2. Simple COUNT without time:")
query2 = """
SELECT COUNT(*) as value
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days'
"""
cursor.execute(query2)
result = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
print(f"   Columns: {columns}")
print(f"   Result: {result}")

# Test 3: With explicit column name
print("\n3. COUNT with explicit name:")
query3 = """
SELECT COUNT(*) as "Total Tests"
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days'
"""
cursor.execute(query3)
result = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
print(f"   Columns: {columns}")
print(f"   Result: {result}")

# Test 4: Bar gauge format
print("\n4. Bar gauge format (metric + value):")
query4 = """
SELECT 
    application_version as metric,
    ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 1) as value
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days'
GROUP BY application_version 
ORDER BY application_version
"""
cursor.execute(query4)
result = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
print(f"   Columns: {columns}")
print(f"   Results:")
for row in result:
    print(f"     {row}")

# Test 5: Check actual data timestamps
print("\n5. Check data timestamps:")
query5 = """
SELECT 
    MIN(created_at) as oldest,
    MAX(created_at) as newest,
    NOW() as current_time,
    COUNT(*) as total
FROM test_execution_event 
WHERE application_version IS NOT NULL
"""
cursor.execute(query5)
result = cursor.fetchone()
print(f"   Oldest: {result[0]}")
print(f"   Newest: {result[1]}")
print(f"   Current: {result[2]}")
print(f"   Total: {result[3]}")
if result[0]:
    age = result[2] - result[1]
    print(f"   Data age: {age}")

cursor.close()
conn.close()

print("\n" + "=" * 70)
print("DIAGNOSIS:")
print("=" * 70)
print("""
If all queries above return data, the issue is in Grafana configuration.

Common problems:
1. Datasource not selected in panel
2. Format set to "Time series" instead of "Table"
3. Query mode in "Builder" instead of "Code"
4. Wrong visualization type selected

SOLUTION: I'll create a working panel configuration for you to test.
""")
