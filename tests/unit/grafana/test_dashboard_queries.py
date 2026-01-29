"""
Test simple queries to ensure dashboard will work
"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation')
cursor = conn.cursor()

print("\n" + "="*70)
print("Testing Dashboard Queries")
print("="*70 + "\n")

# Test 1: Simple count by version
print("Test 1: Count by version")
cursor.execute("""
    SELECT 
        application_version,
        COUNT(*) as count
    FROM test_execution_event
    WHERE event_type = 'test_end'
    GROUP BY application_version
    ORDER BY application_version
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} events")

# Test 2: Check timestamp range
print("\nTest 2: Timestamp range")
cursor.execute("""
    SELECT 
        MIN(timestamp) as oldest,
        MAX(timestamp) as newest
    FROM test_execution_event
""")
row = cursor.fetchone()
print(f"  Oldest: {row[0]}")
print(f"  Newest: {row[1]}")

# Test 3: Pass rate by version
print("\nTest 3: Pass rate by version")
cursor.execute("""
    SELECT 
        application_version,
        COUNT(*) as total,
        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
        ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 1) as pass_rate
    FROM test_execution_event
    WHERE event_type = 'test_end'
    GROUP BY application_version
    ORDER BY application_version
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[2]}/{row[1]} passed ({row[3]}%)")

conn.close()

print("\n" + "="*70)
print("All queries work! Dashboard should display data.")
print("="*70)
print("\nIf dashboard is still blank:")
print("1. Check datasource name in Grafana matches 'postgres-crossbridge'")
print("2. Set time range to 'Last 30 days' or 'Last 7 days'")
print("3. Try the simple dashboard instead: dashboard_working.json")
print("="*70)
