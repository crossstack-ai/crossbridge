# Drift Detection with PostgreSQL

## Overview

The drift detection system supports both **SQLite** (development/testing) and **PostgreSQL** (production) as persistence backends.

**Default**: SQLite (file-based, no setup required)  
**Production**: PostgreSQL (recommended for scale, Grafana integration)

---

## Quick Start

### SQLite (Default)

```python
from core.intelligence.drift_persistence import DriftPersistenceManager

# SQLite - no setup required
manager = DriftPersistenceManager(
    backend="sqlite",
    db_path="data/drift_tracking.db"
)
```

### PostgreSQL

```python
from core.intelligence.drift_persistence import DriftPersistenceManager

# PostgreSQL - production recommended
manager = DriftPersistenceManager(
    backend="postgres",
    host="localhost",
    port=5432,
    database="crossbridge",
    user="crossbridge",
    password="your_password",
    schema="drift"  # PostgreSQL schema to use
)
```

---

## PostgreSQL Setup

### 1. Install PostgreSQL

```bash
# Option 1: Docker (recommended)
docker run -d \
  --name crossbridge-postgres \
  -e POSTGRES_DB=crossbridge \
  -e POSTGRES_USER=crossbridge \
  -e POSTGRES_PASSWORD=secret \
  -p 5432:5432 \
  postgres:15

# Option 2: System installation
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql@15

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### 2. Create Database

```sql
CREATE DATABASE crossbridge;
CREATE USER crossbridge WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE crossbridge TO crossbridge;
```

### 3. Install Python Dependencies

```bash
pip install psycopg2-binary
```

### 4. Configure Application

```python
# Option A: Direct instantiation
from core.intelligence.drift_persistence import DriftPersistenceManager

manager = DriftPersistenceManager(
    backend="postgres",
    host="localhost",
    port=5432,
    database="crossbridge",
    user="crossbridge",
    password="secret",
    schema="drift"
)

# Option B: From environment variables
import os

manager = DriftPersistenceManager(
    backend="postgres",
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", 5432)),
    database=os.getenv("POSTGRES_DB", "crossbridge"),
    user=os.getenv("POSTGRES_USER", "crossbridge"),
    password=os.getenv("POSTGRES_PASSWORD"),
    schema=os.getenv("POSTGRES_SCHEMA", "drift")
)
```

---

## Schema Structure

The system automatically creates these tables:

### `drift.confidence_measurements`
Stores historical confidence scores for tests.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| test_name | TEXT | Test identifier |
| confidence | REAL | Confidence score (0.0-1.0) |
| category | TEXT | Test category |
| timestamp | TIMESTAMP | Measurement time |
| failure_id | TEXT | Optional failure ID |
| rule_score | REAL | Rule-based confidence |
| signal_score | REAL | Signal-based confidence |
| created_at | TIMESTAMP | Record creation time |

**Indexes**: test_name, category, timestamp

### `drift.drift_analysis`
Caches drift analysis results for performance.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| test_name | TEXT | Test identifier |
| baseline_confidence | REAL | Baseline confidence |
| current_confidence | REAL | Current confidence |
| drift_percentage | REAL | Drift as percentage |
| drift_absolute | REAL | Absolute drift value |
| severity | TEXT | Severity level |
| direction | TEXT | Drift direction |
| trend | TEXT | Trend description |
| measurements_count | INTEGER | Number of measurements |
| time_span_seconds | REAL | Time span analyzed |
| recommendations | TEXT | JSON array of recommendations |
| analyzed_at | TIMESTAMP | Analysis timestamp |

**Indexes**: test_name, severity, analyzed_at

### `drift.drift_alerts`
Tracks drift alerts and acknowledgments.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| test_name | TEXT | Test identifier |
| severity | TEXT | Alert severity |
| drift_percentage | REAL | Drift percentage |
| message | TEXT | Alert message |
| recommendations | TEXT | JSON array |
| created_at | TIMESTAMP | Alert creation time |
| acknowledged | BOOLEAN | Acknowledged flag |
| acknowledged_at | TIMESTAMP | Acknowledgment time |
| acknowledged_by | TEXT | Who acknowledged |

**Indexes**: test_name, severity, created_at, acknowledged

---

## CLI Usage with PostgreSQL

### Environment Variables

```bash
export DRIFT_BACKEND=postgres
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=crossbridge
export POSTGRES_USER=crossbridge
export POSTGRES_PASSWORD=secret
export POSTGRES_SCHEMA=drift
```

### CLI Commands (with PostgreSQL)

```bash
# Status command with PostgreSQL
python -m cli.main drift status \
  --db-backend postgres \
  --db-host localhost \
  --db-name crossbridge \
  --db-user crossbridge \
  --db-password secret

# Or use connection string
python -m cli.main drift status \
  --db-url postgresql://crossbridge:secret@localhost:5432/crossbridge
```

**Note**: CLI integration for PostgreSQL configuration is coming in the next update. Currently, use Python API directly for PostgreSQL.

---

## Migration from SQLite to PostgreSQL

### Export from SQLite

```python
from core.intelligence.drift_persistence import DriftPersistenceManager

# Export from SQLite
sqlite_manager = DriftPersistenceManager(
    backend="sqlite",
    db_path="data/drift_tracking.db"
)

# Export to JSON
sqlite_manager.export_to_json("drift_export.json")
```

### Import to PostgreSQL

```python
import json
from datetime import datetime

# Connect to PostgreSQL
pg_manager = DriftPersistenceManager(
    backend="postgres",
    host="localhost",
    database="crossbridge",
    user="crossbridge",
    password="secret",
    schema="drift"
)

# Load and import data
with open("drift_export.json") as f:
    data = json.load(f)

# Import measurements
for m in data['measurements']:
    pg_manager.store_measurement(
        test_name=m['test_name'],
        confidence=m['confidence'],
        category=m['category'],
        timestamp=datetime.fromisoformat(m['timestamp']),
        failure_id=m.get('failure_id'),
        rule_score=m.get('rule_score'),
        signal_score=m.get('signal_score')
    )

print(f"Migrated {len(data['measurements'])} measurements to PostgreSQL")
```

---

## Performance Considerations

### SQLite
- **Best for**: Development, testing, CI/CD, small deployments
- **Pros**: Zero setup, file-based, portable
- **Cons**: Single-threaded writes, limited concurrency
- **Scale**: < 1000 measurements/day

### PostgreSQL
- **Best for**: Production, large scale, multi-tenant
- **Pros**: High concurrency, ACID compliance, replication
- **Cons**: Requires server setup and maintenance
- **Scale**: 100K+ measurements/day

### Indexing Strategy

Both backends use identical indexing for optimal query performance:
- **test_name**: Fast lookups by test
- **category**: Category-level aggregation
- **timestamp**: Time-based queries and filtering
- **severity**: Alert filtering
- **acknowledged**: Unacknowledged alert queries

---

## Monitoring & Observability

### Database Size

```python
size_bytes = manager.get_database_size()
print(f"Database size: {size_bytes / 1024 / 1024:.2f} MB")
```

### Statistics

```python
stats = manager.get_drift_statistics(
    category="authentication",
    since=datetime.utcnow() - timedelta(days=7)
)

print(f"Tests tracked: {stats['total_tests']}")
print(f"Measurements: {stats['total_measurements']}")
print(f"Avg confidence: {stats['avg_confidence']:.2%}")
```

### Cleanup

```python
# Remove old data
deleted = manager.cleanup_old_data(
    measurements_days=90,  # Keep 90 days of measurements
    analysis_days=30,      # Keep 30 days of analysis
    alerts_days=60         # Keep 60 days of alerts
)

print(f"Cleaned up {deleted['measurements']} old measurements")

# Optimize database
manager.vacuum()
```

---

## Grafana Integration

PostgreSQL enables powerful drift visualization with Grafana:

### 1. Add PostgreSQL Data Source

```
Host: localhost:5432
Database: crossbridge
User: crossbridge
SSL Mode: disable
```

### 2. Example Queries

**Drift Over Time**:
```sql
SELECT
  timestamp,
  test_name,
  confidence
FROM drift.confidence_measurements
WHERE $__timeFilter(timestamp)
ORDER BY timestamp
```

**Alert Count by Severity**:
```sql
SELECT
  severity,
  COUNT(*) as count
FROM drift.drift_alerts
WHERE $__timeFilter(created_at)
GROUP BY severity
```

**Tests with Recent Drift**:
```sql
SELECT DISTINCT
  test_name,
  drift_percentage,
  severity
FROM drift.drift_analysis
WHERE analyzed_at >= NOW() - INTERVAL '24 hours'
  AND drift_percentage > 0.05
ORDER BY drift_percentage DESC
```

---

## Troubleshooting

### Connection Failed

```python
# Test connection
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="crossbridge",
        user="crossbridge",
        password="secret"
    )
    print("✓ Connection successful")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Schema Not Found

```python
# Verify schema exists
import psycopg2

conn = psycopg2.connect(...)
cursor = conn.cursor()

cursor.execute("SELECT schema_name FROM information_schema.schemata")
schemas = [row[0] for row in cursor.fetchall()]
print(f"Available schemas: {schemas}")

# Create schema if missing
cursor.execute("CREATE SCHEMA IF NOT EXISTS drift")
conn.commit()
```

### Performance Issues

```python
# Check indexes
cursor.execute("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'drift'
""")
for idx_name, idx_def in cursor.fetchall():
    print(f"{idx_name}: {idx_def}")

# Analyze tables for query planning
cursor.execute("ANALYZE drift.confidence_measurements")
cursor.execute("ANALYZE drift.drift_analysis")
cursor.execute("ANALYZE drift.drift_alerts")
```

---

## Best Practices

1. **Use Connection Pooling**: The PostgreSQL backend uses psycopg2's connection pool (1-10 connections)
2. **Regular Cleanup**: Schedule cleanup jobs to remove old data
3. **Monitor Database Size**: Set up alerts for database growth
4. **Backup Strategy**: Regular backups of drift data
5. **Index Maintenance**: Run VACUUM ANALYZE periodically
6. **Security**: Use strong passwords, restrict network access
7. **Environment Variables**: Never hardcode credentials

---

## Next Steps

- [ ] Add CLI support for PostgreSQL configuration
- [ ] Create migration script (SQLite → PostgreSQL)
- [ ] Add connection pooling configuration options
- [ ] Create Grafana dashboard templates
- [ ] Add TimescaleDB support for time-series optimization
- [ ] Implement database replication support
