from sqlalchemy import text, create_engine

engine = create_engine('postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation')
conn = engine.connect()

print('All flaky test records:')
print('=' * 80)
result = conn.execute(text('SELECT test_name, severity, failure_rate, is_flaky FROM flaky_test ORDER BY severity'))
rows = result.fetchall()
for r in rows:
    print(f'Test: {r[0][:40]:40} | Severity: {r[1]:10} | Failure Rate: {r[2]:.2%} | Is Flaky: {r[3]}')

print('\nSeverity distribution for is_flaky=true:')
result2 = conn.execute(text('SELECT severity, COUNT(*) FROM flaky_test WHERE is_flaky = true GROUP BY severity ORDER BY severity'))
rows2 = result2.fetchall()
for r in rows2:
    print(f'  {r[0]}: {r[1]} tests')

print('\nQuery used in Grafana:')
result3 = conn.execute(text("SELECT severity as metric, COUNT(*) as value FROM flaky_test WHERE is_flaky = true GROUP BY severity ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END"))
rows3 = result3.fetchall()
for r in rows3:
    print(f'  metric: {r[0]}, value: {r[1]}')
