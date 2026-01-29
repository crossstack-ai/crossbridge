"""Test if Grafana queries can access the data"""
import psycopg2
from datetime import datetime, timedelta

# Database connection
conn = psycopg2.connect(
    host="10.55.12.99",
    port=5432,
    database="udp-native-webservices-automation",
    user="postgres",
    password="admin"
)

print("=" * 70)
print("Testing Grafana-style Queries")
print("=" * 70)

cursor = conn.cursor()

# Test 1: Simple count
print("\n1. Total Events:")
cursor.execute("SELECT COUNT(*) FROM test_execution_event WHERE application_version IS NOT NULL")
count = cursor.fetchone()[0]
print(f"   Found {count} events with version data")

# Test 2: Recent events (last 10 days - matching user's time range)
print("\n2. Events in Last 10 Days:")
ten_days_ago = datetime.now() - timedelta(days=10)
cursor.execute("""
    SELECT COUNT(*) 
    FROM test_execution_event 
    WHERE application_version IS NOT NULL 
    AND created_at >= %s
""", (ten_days_ago,))
recent_count = cursor.fetchone()[0]
print(f"   Found {recent_count} events in last 10 days")

# Test 3: Time range of data
print("\n3. Data Time Range:")
cursor.execute("""
    SELECT 
        MIN(created_at) as oldest,
        MAX(created_at) as newest,
        NOW() as current_time
    FROM test_execution_event 
    WHERE application_version IS NOT NULL
""")
row = cursor.fetchone()
print(f"   Oldest: {row[0]}")
print(f"   Newest: {row[1]}")
print(f"   Current: {row[2]}")
if row[1] and row[2]:
    try:
        print(f"   Data age: {row[2] - row[1]}")
    except TypeError:
        # Handle timezone mismatch
        print(f"   Data age: (timezone mismatch)")


# Test 4: Version breakdown (exact query from dashboard)
print("\n4. Version Breakdown (Dashboard Query):")
cursor.execute("""
    SELECT 
        application_version,
        product_name,
        environment,
        COUNT(*) as total_tests,
        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
        ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 2) as pass_rate
    FROM test_execution_event
    WHERE application_version IS NOT NULL
    AND created_at >= NOW() - INTERVAL '10 days'
    GROUP BY application_version, product_name, environment
    ORDER BY product_name, application_version
""")
print(f"   {'Version':<12} {'Product':<15} {'Environment':<12} {'Tests':<8} {'Pass Rate'}")
print("   " + "-" * 65)
for row in cursor.fetchall():
    print(f"   {row[0]:<12} {row[1]:<15} {row[2]:<12} {row[3]:<8} {row[5]:.1f}%")

# Test 5: Check if data has proper timestamps
print("\n5. Sample Event Timestamps:")
cursor.execute("""
    SELECT created_at, application_version, product_name, status
    FROM test_execution_event 
    WHERE application_version IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"   {row[0]} - {row[1]} ({row[2]}) - {row[3]}")

cursor.close()
conn.close()

print("\n" + "=" * 70)
print("If queries above show data, the issue is in Grafana configuration")
print("=" * 70)
