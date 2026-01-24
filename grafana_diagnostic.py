#!/usr/bin/env python3
"""
Quick fix for Grafana dashboard - Test and diagnose issues
"""

import psycopg2
import json

DB_CONFIG = {
    'host': '10.60.67.247',
    'port': 5432,
    'database': 'cbridge-unit-test-db',
    'user': 'postgres',
    'password': 'admin'
}

print("🔍 Grafana Dashboard Diagnostic Tool")
print("="*60)

# Test 1: Database Connection
print("\n1️⃣  Testing database connection...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("   ✅ Database connection successful")
    conn.close()
except Exception as e:
    print(f"   ❌ Database connection failed: {e}")
    exit(1)

# Test 2: Check data exists
print("\n2️⃣  Checking if data exists...")
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM crossbridge.tests")
total_tests = cursor.fetchone()[0]
print(f"   ✅ Total tests in database: {total_tests}")

if total_tests == 0:
    print("   ❌ No data found! Run: python populate_profiling_sample_data.py")
    exit(1)

# Test 3: Check recent data
cursor.execute("SELECT COUNT(*) FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours'")
recent_tests = cursor.fetchone()[0]
print(f"   ✅ Tests in last 24 hours: {recent_tests}")

# Test 4: Check time range
cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM crossbridge.tests")
min_date, max_date = cursor.fetchone()
print(f"   ✅ Data time range: {min_date.date()} to {max_date.date()}")

# Test 5: Test all dashboard queries
print("\n3️⃣  Testing dashboard queries...")

queries = [
    ("Total Tests", "SELECT COUNT(DISTINCT test_id) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours'"),
    ("Avg Duration", "SELECT ROUND(AVG(duration_ms)::numeric, 2) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours'"),
    ("Framework Breakdown", "SELECT framework as metric, COUNT(*) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours' GROUP BY framework"),
    ("Time Series", "SELECT DATE_TRUNC('hour', created_at) as time, framework, ROUND(AVG(duration_ms)::numeric, 2) as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY time, framework ORDER BY time LIMIT 5"),
]

all_passed = True
for name, query in queries:
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        if results:
            print(f"   ✅ {name}: {len(results)} rows")
        else:
            print(f"   ⚠️  {name}: No results")
            all_passed = False
    except Exception as e:
        print(f"   ❌ {name}: {e}")
        all_passed = False

cursor.close()
conn.close()

if not all_passed:
    print("\n❌ Some queries failed. Check database schema.")
    exit(1)

# Print Grafana setup instructions
print("\n" + "="*60)
print("📋 Grafana Setup Instructions")
print("="*60)

print("""
STEP 1: Configure PostgreSQL Datasource in Grafana
---------------------------------------------------
1. Open Grafana: http://10.55.12.99:3000
2. Go to Configuration (⚙️) → Data sources
3. Click "Add data source"
4. Select "PostgreSQL"
5. Enter these settings:

   Name:     CrossBridge PostgreSQL
   Host:     10.60.67.247:5432
   Database: cbridge-unit-test-db
   User:     postgres
   Password: admin
   SSL Mode: disable
   Version:  12+

6. Click "Save & Test" - should show green checkmark

STEP 2: Import Dashboard
-------------------------
1. Go to Dashboards (☰) → Import
2. Click "Upload JSON file"
3. Select: grafana/performance_profiling_dashboard_simple.json
4. In "Select a PostgreSQL data source" dropdown:
   → Select "CrossBridge PostgreSQL"
5. Click "Import"

STEP 3: View Dashboard
-----------------------
1. Dashboard should load automatically
2. Set time range to "Last 24 hours"
3. Wait a few seconds for data to load
4. You should see:
   ✅ Total Tests: """ + str(recent_tests) + """
   ✅ Multiple frameworks in pie chart
   ✅ Time series graph with trends
   ✅ Table of recent test executions

TROUBLESHOOTING:
----------------
If panels show "No data":
1. Check datasource is selected (panel edit → Query tab)
2. Use Query Inspector (panel menu → Inspect → Query)
3. Verify actual SQL matches expected query
4. Check time range includes data (""" + str(min_date.date()) + """ to """ + str(max_date.date()) + """)

If getting "Permission denied":
   Run in PostgreSQL:
   GRANT USAGE ON SCHEMA crossbridge TO postgres;
   GRANT SELECT ON ALL TABLES IN SCHEMA crossbridge TO postgres;

If timezone issues:
   Database timezone: Asia/Calcutta (IST)
   Grafana timezone: Set to "Browser" or "Asia/Calcutta"

ALTERNATIVE: Use datasource UID
--------------------------------
If the simple dashboard doesn't work, you may need to get the datasource UID:
1. Go to Data sources in Grafana
2. Click on your PostgreSQL datasource
3. Look at the URL: /datasources/edit/<UID>
4. Edit the JSON file and replace "datasource": null with:
   "datasource": {"type": "postgres", "uid": "<UID>"}
""")

print("\n✅ Diagnostic complete! Follow the steps above to set up Grafana.")
