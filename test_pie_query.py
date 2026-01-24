from sqlalchemy import text, create_engine
import json

engine = create_engine('postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation')
conn = engine.connect()

print('Testing the exact Grafana query:')
print('=' * 80)

query = """
SELECT severity as metric, COUNT(*) as value 
FROM flaky_test 
WHERE is_flaky = true 
GROUP BY severity 
ORDER BY CASE severity 
    WHEN 'critical' THEN 1 
    WHEN 'high' THEN 2 
    WHEN 'medium' THEN 3 
    WHEN 'low' THEN 4 
END
"""

result = conn.execute(text(query))
rows = result.fetchall()

print(f'\nQuery returned {len(rows)} rows:')
for i, r in enumerate(rows, 1):
    print(f'  Row {i}: metric="{r[0]}", value={r[1]}')

# Check for any issues
print('\n' + '=' * 80)
if len(rows) == 0:
    print('❌ NO DATA RETURNED')
elif len(rows) == 1:
    print('⚠️  ONLY 1 ROW RETURNED - This might explain the issue!')
    print(f'   The single row is: {rows[0]}')
else:
    print(f'✅ {len(rows)} rows returned - Chart should show {len(rows)} slices')

# Also test without the ORDER BY
print('\n' + '=' * 80)
print('Testing without ORDER BY:')
query2 = "SELECT severity as metric, COUNT(*) as value FROM flaky_test WHERE is_flaky = true GROUP BY severity"
result2 = conn.execute(text(query2))
rows2 = result2.fetchall()
print(f'Rows: {len(rows2)}')
for r in rows2:
    print(f'  {r[0]}: {r[1]}')
