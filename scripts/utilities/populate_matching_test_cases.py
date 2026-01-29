"""
Populate test_case table with records matching tests in profiling data.
This creates test_case entries for all unique test_id/framework combinations
in the crossbridge.tests table.
"""
import psycopg2
import uuid
import json
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    host='10.60.67.247',
    port=5432,
    database='cbridge-unit-test-db',
    user='postgres',
    password='admin'
)

cursor = conn.cursor()

# First, get all unique test_id/framework combinations from tests table
print("Fetching unique test IDs from profiling data...")
cursor.execute("""
    SELECT DISTINCT test_id, framework
    FROM crossbridge.tests
    ORDER BY framework, test_id;
""")
test_combinations = cursor.fetchall()
print(f"Found {len(test_combinations)} unique test/framework combinations")

# Check which ones already exist in test_case
cursor.execute("""
    SELECT test_name, framework
    FROM public.test_case;
""")
existing_test_cases = set(cursor.fetchall())
print(f"Found {len(existing_test_cases)} existing test case records")

# Insert new test_case records for tests that don't have them
inserted = 0
skipped = 0

for test_id, framework in test_combinations:
    if (test_id, framework) in existing_test_cases:
        skipped += 1
        continue
    
    # Generate a UUID for the test case
    test_case_id = str(uuid.uuid4())
    
    # Extract a reasonable description from the test name
    # Remove framework prefix and timestamp suffix if present
    test_name_clean = test_id
    if test_id.startswith(f"{framework}_"):
        test_name_clean = test_id[len(framework)+1:]
    
    # Generate metadata
    now = datetime.now()
    
    cursor.execute("""
        INSERT INTO public.test_case (
            id, test_name, framework, test_file_path, 
            description, tags, priority, status,
            first_seen_at, last_seen_at, metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
        );
    """, (
        test_case_id,
        test_id,  # Use the exact test_id from tests table
        framework,
        f"tests/{framework}/{test_name_clean}.py",
        f"Test case for {test_name_clean}",
        ["automated", framework, "profiling"],
        "medium",
        "active",
        now,
        now,
        json.dumps({"source": "profiling_data", "auto_generated": True})
    ))
    
    inserted += 1
    
    if inserted % 100 == 0:
        print(f"  Inserted {inserted} test cases...")

conn.commit()

print(f"\n✅ Complete!")
print(f"  - Inserted: {inserted} new test case records")
print(f"  - Skipped: {skipped} existing records")
print(f"  - Total in test_case table: {len(existing_test_cases) + inserted}")

# Verify the join now works
cursor.execute("""
    SELECT 
        COUNT(*) as total_tests,
        COUNT(tc.id) as tests_with_tc_id
    FROM crossbridge.tests t
    LEFT JOIN public.test_case tc ON t.test_id = tc.test_name AND t.framework = tc.framework;
""")
row = cursor.fetchone()
match_rate = (row[1] / row[0] * 100) if row[0] > 0 else 0
print(f"\n📊 Join Validation:")
print(f"  - Total tests: {row[0]}")
print(f"  - Tests with test_case ID: {row[1]}")
print(f"  - Match rate: {match_rate:.1f}%")

# Show sample results
cursor.execute("""
    SELECT 
        SUBSTRING(tc.id::text, 1, 8) as tc_id,
        t.test_id,
        t.framework
    FROM crossbridge.tests t
    LEFT JOIN public.test_case tc ON t.test_id = tc.test_name AND t.framework = tc.framework
    LIMIT 5;
""")
print(f"\n📋 Sample Join Results:")
for row in cursor.fetchall():
    tc_id = row[0] if row[0] else "(no match)"
    print(f"  TC ID: {tc_id:12s} | Test: {row[1][:50]:<50s} | Framework: {row[2]}")

cursor.close()
conn.close()

print("\n✨ Test case population complete! The dashboards should now show test case IDs.")
