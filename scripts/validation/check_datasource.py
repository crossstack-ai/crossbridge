"""
Check what datasource UID your Grafana is using
"""
import psycopg2

# Get a sample of the data to understand format
conn = psycopg2.connect(
    host="10.55.12.99",
    port=5432,
    database="udp-native-webservices-automation",
    user="postgres",
    password="admin"
)

print("=" * 70)
print("DATASOURCE INVESTIGATION")
print("=" * 70)

cursor = conn.cursor()

# Check data format
print("\n1. Sample data (first 3 rows):")
cursor.execute("""
    SELECT 
        id,
        created_at,
        application_version,
        product_name,
        environment,
        status,
        test_name
    FROM test_execution_event 
    WHERE application_version IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 3
""")

for row in cursor.fetchall():
    print(f"   ID: {row[0]}")
    print(f"   Time: {row[1]}")
    print(f"   Version: {row[2]}, Product: {row[3]}, Env: {row[4]}")
    print(f"   Status: {row[5]}, Test: {row[6]}")
    print()

# Check if there are any NULL values
print("2. Data quality check:")
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(application_version) as has_version,
        COUNT(product_name) as has_product,
        COUNT(environment) as has_env,
        COUNT(status) as has_status
    FROM test_execution_event 
    WHERE application_version IS NOT NULL
""")
row = cursor.fetchone()
print(f"   Total rows: {row[0]}")
print(f"   With version: {row[1]}")
print(f"   With product: {row[2]}")
print(f"   With environment: {row[3]}")
print(f"   With status: {row[4]}")

cursor.close()
conn.close()

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print()
print("1. In Grafana, go to: http://10.55.12.99:3000/connections/datasources")
print("2. Click on your PostgreSQL datasource")
print("3. Look at the URL - it will be like:")
print("   http://10.55.12.99:3000/connections/datasources/edit/XXXXXXXXX")
print("4. The XXXXXXXXX part is your datasource UID")
print()
print("5. Then manually create ONE panel:")
print("   - Create new dashboard")
print("   - Add visualization")
print("   - Select PostgreSQL datasource")
print("   - Switch to Code mode")
print("   - Paste: SELECT COUNT(*) FROM test_execution_event WHERE application_version IS NOT NULL")
print("   - If this shows 110, panels work!")
print()
print("6. If manual panel works, export that dashboard JSON")
print("   and send it to me so I can see the correct format")
print("=" * 70)
