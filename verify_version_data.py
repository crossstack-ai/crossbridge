import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'admin')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'crossbridge_db')}"
)
cursor = conn.cursor()

print("\n" + "="*70)
print("Version-Aware Data Verification")
print("="*70 + "\n")

cursor.execute("""
    SELECT application_version, product_name, environment, COUNT(*) 
    FROM test_execution_event 
    GROUP BY application_version, product_name, environment 
    ORDER BY application_version, product_name
""")
rows = cursor.fetchall()

print("Version      | Product      | Environment  | Events")
print("-"*60)
for row in rows:
    print(f"{row[0]:<12} | {row[1]:<12} | {row[2]:<12} | {row[3]}")

cursor.execute('SELECT COUNT(*) FROM test_execution_event')
total = cursor.fetchone()[0]
print("-"*60)
print(f"Total events: {total}\n")

conn.close()

print("="*70)
print("Next Step: Import Grafana Dashboard")
print("="*70)
grafana_host = os.getenv('GRAFANA_HOST', 'localhost')
grafana_port = os.getenv('GRAFANA_PORT', '3000')
print(f"\n1. Open Grafana: http://{grafana_host}:{grafana_port}/")
print("2. Login (admin/admin)")
print("3. Click '+' > Import Dashboard")
print("4. Upload: grafana/dashboard_version_aware.json")
print("5. Select datasource: PostgreSQL")
print("6. Click Import")
print("\nYou'll see:")
print("  - Test execution trends by version")
print("  - Coverage comparison across versions")
print("  - Pass rate analysis")
print("  - Version-to-version delta tracking")
print("="*70)
