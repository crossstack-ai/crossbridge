# CrossBridge Comprehensive Database Schema

## Overview

This document describes the comprehensive PostgreSQL database schema for CrossBridge, including TimescaleDB hypertables for time-series data, pgvector indexes for semantic search, and Grafana dashboards for visualization.

## Architecture

### Technology Stack

- **PostgreSQL 14+**: Core relational database
- **TimescaleDB**: Time-series data optimization and continuous aggregates
- **pgvector**: Vector similarity search for AI-powered features
- **Grafana**: Real-time dashboards and monitoring

### Key Features

1. **Time-Series Optimization**: Hypertables for test executions, flaky history, and git events
2. **Semantic Search**: Vector embeddings with HNSW indexing for fast similarity search
3. **Continuous Aggregates**: Pre-computed hourly/daily metrics for dashboard performance
4. **Retention Policies**: Automatic data lifecycle management
5. **Analytical Views**: Pre-built views optimized for Grafana queries

## Schema Components

### 1. Core Discovery Tables

#### `discovery_run`
Tracks test discovery operations with git context.

```sql
CREATE TABLE discovery_run (
    id UUID PRIMARY KEY,
    project_name TEXT NOT NULL,
    git_commit TEXT,
    git_branch TEXT,
    triggered_by TEXT,        -- cli | ci | jira | manual
    framework TEXT,
    test_count INTEGER,
    page_count INTEGER,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);
```

**Indexes**: `created_at`, `project_name`, `git_branch`, `framework`

#### `test_case`
Framework-agnostic test case storage.

```sql
CREATE TABLE test_case (
    id UUID PRIMARY KEY,
    framework TEXT NOT NULL,
    package TEXT,
    class_name TEXT,
    method_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    tags TEXT[],
    intent TEXT,              -- AI-extracted intent
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (framework, package, class_name, method_name)
);
```

**Indexes**: `framework`, `file_path`, `tags` (GIN), `created_at`

#### `page_object`
UI automation page objects.

```sql
CREATE TABLE page_object (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    framework TEXT,
    package TEXT,
    locator_count INTEGER,
    method_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (name, file_path)
);
```

### 2. Time-Series Tables (TimescaleDB Hypertables)

#### `test_execution` ⏱️
Test execution history with time-series optimization.

```sql
CREATE TABLE test_execution (
    id UUID,
    executed_at TIMESTAMPTZ NOT NULL,
    test_id TEXT NOT NULL,
    test_name TEXT,
    framework TEXT NOT NULL,
    status TEXT NOT NULL,     -- passed | failed | skipped | error
    duration_ms REAL NOT NULL,
    error_signature TEXT,
    error_type TEXT,
    environment TEXT,
    build_id TEXT,
    product_name TEXT,
    app_version TEXT,
    metadata JSONB,
    PRIMARY KEY (id, executed_at)
);

-- Convert to hypertable
SELECT create_hypertable('test_execution', 'executed_at', 
    chunk_time_interval => INTERVAL '1 day');

-- Retention: 90 days
SELECT add_retention_policy('test_execution', INTERVAL '90 days');
```

**Chunk Interval**: 1 day  
**Retention**: 90 days  
**Indexes**: `test_id`, `status`, `framework`, `environment`, `build_id`

#### `flaky_test_history` ⏱️
Historical flaky detection trends.

```sql
CREATE TABLE flaky_test_history (
    id UUID,
    detected_at TIMESTAMPTZ NOT NULL,
    test_id TEXT NOT NULL,
    flaky_score REAL NOT NULL,
    is_flaky BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    classification TEXT NOT NULL,
    failure_rate REAL,
    switch_rate REAL,
    model_version TEXT NOT NULL,
    PRIMARY KEY (id, detected_at)
);

SELECT create_hypertable('flaky_test_history', 'detected_at',
    chunk_time_interval => INTERVAL '7 days');

SELECT add_retention_policy('flaky_test_history', INTERVAL '180 days');
```

**Chunk Interval**: 7 days  
**Retention**: 180 days  
**Indexes**: `test_id`

#### `git_change_event` ⏱️
Git change tracking with impact analysis.

```sql
CREATE TABLE git_change_event (
    id UUID,
    event_time TIMESTAMPTZ NOT NULL,
    commit_sha TEXT NOT NULL,
    author TEXT NOT NULL,
    branch TEXT,
    files_changed TEXT[],
    code_units_changed UUID[],
    features_affected UUID[],
    tests_affected UUID[],
    risk_score FLOAT,
    metadata JSONB,
    PRIMARY KEY (id, event_time)
);

SELECT create_hypertable('git_change_event', 'event_time',
    chunk_time_interval => INTERVAL '7 days');

SELECT add_retention_policy('git_change_event', INTERVAL '365 days');
```

**Chunk Interval**: 7 days  
**Retention**: 365 days  
**Indexes**: `commit_sha`, `branch`

#### `observability_event` ⏱️
CrossBridge system monitoring events.

```sql
CREATE TABLE observability_event (
    id UUID,
    event_time TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,     -- discovery | transformation | execution
    event_name TEXT NOT NULL,
    status TEXT NOT NULL,         -- started | completed | failed
    duration_ms INTEGER,
    project_name TEXT,
    framework TEXT,
    environment TEXT,
    metrics JSONB,
    error_message TEXT,
    metadata JSONB,
    PRIMARY KEY (id, event_time)
);

SELECT create_hypertable('observability_event', 'event_time',
    chunk_time_interval => INTERVAL '1 day');

SELECT add_retention_policy('observability_event', INTERVAL '30 days');
```

**Chunk Interval**: 1 day  
**Retention**: 30 days  
**Indexes**: `event_type`, `status`

### 3. Flaky Test Detection

#### `flaky_test`
Current state of flaky test detection.

```sql
CREATE TABLE flaky_test (
    id UUID PRIMARY KEY,
    test_id TEXT NOT NULL UNIQUE,
    test_name TEXT,
    framework TEXT NOT NULL,
    flaky_score REAL NOT NULL,
    is_flaky BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    classification TEXT NOT NULL,  -- flaky | suspected_flaky | stable
    severity TEXT,                 -- critical | high | medium | low
    failure_rate REAL,
    switch_rate REAL,
    duration_variance REAL,
    unique_error_count INTEGER,
    total_executions INTEGER,
    primary_indicators TEXT[],
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    model_version TEXT NOT NULL,
    explanation JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes**: `is_flaky`, `classification`, `severity`, `detected_at`

### 4. Feature Coverage

#### `feature`
Product feature registry.

```sql
CREATE TABLE feature (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,           -- api | service | bdd | module | component
    source TEXT NOT NULL,         -- cucumber | jira | code | manual
    description TEXT,
    parent_feature_id UUID REFERENCES feature(id),
    status TEXT DEFAULT 'active', -- active | deprecated | planned
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (name, type, source)
);
```

#### `code_unit`
Individual code units for detailed coverage.

```sql
CREATE TABLE code_unit (
    id UUID PRIMARY KEY,
    file_path TEXT NOT NULL,
    class_name TEXT,
    method_name TEXT,
    package_name TEXT,
    line_start INTEGER,
    line_end INTEGER,
    complexity INTEGER,
    language TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (file_path, class_name, method_name)
);
```

#### `test_feature_map`
Maps tests to features for coverage analysis.

```sql
CREATE TABLE test_feature_map (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id),
    feature_id UUID REFERENCES feature(id),
    confidence FLOAT DEFAULT 1.0,
    source TEXT NOT NULL,         -- coverage | tag | annotation | ai
    discovery_run_id UUID REFERENCES discovery_run(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (test_case_id, feature_id, source)
);
```

### 5. Memory & Embeddings (pgvector)

#### `memory_embeddings` 🔍
Semantic embeddings for AI-powered search.

```sql
CREATE TABLE memory_embeddings (
    id UUID PRIMARY KEY,
    type TEXT NOT NULL,           -- test | scenario | step | page | failure
    text TEXT NOT NULL,
    embedding VECTOR(3072),       -- Adjust dimension based on model
    metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast vector similarity
CREATE INDEX idx_memory_embedding_cosine 
ON memory_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Index Type**: HNSW (Hierarchical Navigable Small World)  
**Similarity**: Cosine distance  
**Performance**: Sub-linear search time for millions of vectors

**Index Parameters**:
- `m = 16`: Number of connections per layer
- `ef_construction = 64`: Quality vs build time tradeoff

### 6. Continuous Aggregates

#### `test_execution_hourly`
Hourly test execution metrics.

```sql
CREATE MATERIALIZED VIEW test_execution_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', executed_at) AS bucket,
    framework,
    environment,
    status,
    COUNT(*) AS execution_count,
    AVG(duration_ms) AS avg_duration_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_duration_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99_duration_ms
FROM test_execution
GROUP BY bucket, framework, environment, status;
```

**Refresh Policy**: Every 1 hour  
**Retention**: Last 3 hours of data

#### `test_execution_daily`
Daily test execution summary.

```sql
CREATE MATERIALIZED VIEW test_execution_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', executed_at) AS bucket,
    framework,
    environment,
    status,
    COUNT(*) AS execution_count,
    AVG(duration_ms) AS avg_duration_ms,
    COUNT(DISTINCT test_id) AS unique_tests,
    COUNT(DISTINCT build_id) AS builds
FROM test_execution
GROUP BY bucket, framework, environment, status;
```

**Refresh Policy**: Every 1 day  
**Retention**: Last 7 days of data

#### `flaky_test_trend_daily`
Daily flaky test trends.

```sql
CREATE MATERIALIZED VIEW flaky_test_trend_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', detected_at) AS bucket,
    classification,
    COUNT(*) AS test_count,
    AVG(flaky_score) AS avg_flaky_score,
    AVG(confidence) AS avg_confidence
FROM flaky_test_history
GROUP BY bucket, classification;
```

**Refresh Policy**: Every 1 day  
**Retention**: Last 14 days of data

### 7. Analytical Views

#### `test_health_overview`
High-level test suite health metrics.

```sql
CREATE OR REPLACE VIEW test_health_overview AS
SELECT 
    COUNT(DISTINCT tc.id) AS total_tests,
    COUNT(DISTINCT CASE WHEN ft.is_flaky THEN tc.id END) AS flaky_tests,
    COUNT(DISTINCT po.id) AS total_pages,
    COUNT(DISTINCT f.id) AS total_features,
    COUNT(DISTINCT tfm.test_case_id) AS tests_with_feature_mapping,
    (COUNT(DISTINCT tfm.test_case_id)::FLOAT / 
     NULLIF(COUNT(DISTINCT tc.id), 0)) * 100 AS feature_coverage_percent
FROM test_case tc
LEFT JOIN flaky_test ft ON tc.method_name = ft.test_id
LEFT JOIN test_feature_map tfm ON tc.id = tfm.test_case_id
CROSS JOIN (SELECT COUNT(*) FROM page_object) po(id)
CROSS JOIN (SELECT COUNT(*) FROM feature) f(id);
```

#### `feature_coverage_gaps`
Features with inadequate test coverage.

```sql
CREATE OR REPLACE VIEW feature_coverage_gaps AS
SELECT 
    f.name,
    f.type,
    f.source,
    COUNT(tfm.test_case_id) AS test_count,
    CASE 
        WHEN COUNT(tfm.test_case_id) = 0 THEN 'no_coverage'
        WHEN COUNT(tfm.test_case_id) < 3 THEN 'low_coverage'
        ELSE 'adequate_coverage'
    END AS coverage_status
FROM feature f
LEFT JOIN test_feature_map tfm ON f.id = tfm.feature_id
GROUP BY f.id, f.name, f.type, f.source
ORDER BY COUNT(tfm.test_case_id) ASC;
```

## Setup Instructions

### Prerequisites

```bash
# Install PostgreSQL 14+
sudo apt-get install postgresql-14

# Install TimescaleDB
sudo add-apt-repository ppa:timescale/timescaledb-ppa
sudo apt-get update
sudo apt-get install timescaledb-2-postgresql-14

# Install pgvector
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### Database Setup

```bash
# 1. Create database
createdb crossbridge

# 2. Run comprehensive schema setup
python scripts/setup_comprehensive_schema.py \
    --connection "postgresql://user:pass@host:5432/crossbridge"

# 3. Verify schema
python scripts/setup_comprehensive_schema.py --verify-only

# 4. Generate test data
python scripts/generate_test_data.py

# 5. Import Grafana dashboard
# Import grafana/dashboards/crossbridge_overview.json
```

### Configuration

Update `crossbridge.yml`:

```yaml
crossbridge:
  database:
    enabled: true
    host: ${CROSSBRIDGE_DB_HOST:-localhost}
    port: ${CROSSBRIDGE_DB_PORT:-5432}
    name: ${CROSSBRIDGE_DB_NAME:-crossbridge}
    user: ${CROSSBRIDGE_DB_USER:-postgres}
    password: ${CROSSBRIDGE_DB_PASSWORD}
    
  memory:
    vector_store:
      type: pgvector
      connection_string: postgresql://${CROSSBRIDGE_DB_USER}:${CROSSBRIDGE_DB_PASSWORD}@${CROSSBRIDGE_DB_HOST}:${CROSSBRIDGE_DB_PORT}/${CROSSBRIDGE_DB_NAME}
      dimension: 3072
```

## Grafana Dashboard

### Overview

The CrossBridge Grafana dashboard provides real-time insights into test execution, flaky tests, feature coverage, and system health.

**Dashboard Location**: `grafana/dashboards/crossbridge_overview.json`

### Key Panels

1. **Test Execution Summary** (Stat): Total executions in last 24h
2. **Pass Rate** (Stat): Overall pass percentage
3. **Flaky Tests Detected** (Stat): Count of flaky tests
4. **Feature Coverage** (Stat): Percentage of features with test coverage
5. **Test Execution Trend** (Time Series): Executions over time by status
6. **Test Duration Distribution** (Time Series): P50, P95, P99 latencies
7. **Flaky Test Trend** (Time Series): Flaky tests over 30 days
8. **Test Execution by Framework** (Pie Chart): Distribution across frameworks
9. **Test Execution by Environment** (Pie Chart): Distribution across environments
10. **Top 10 Slowest Tests** (Table): Tests with highest average duration
11. **Top 10 Most Flaky Tests** (Table): Tests with highest flaky scores
12. **Features Without Coverage** (Table): Coverage gaps
13. **Recent Discovery Runs** (Table): Latest test discovery operations

### Grafana Setup

```bash
# 1. Install Grafana
sudo apt-get install -y grafana

# 2. Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# 3. Access Grafana
# http://localhost:3000 (admin/admin)

# 4. Add PostgreSQL datasource
# - Type: PostgreSQL
# - Host: localhost:5432
# - Database: crossbridge
# - User: postgres
# - SSL Mode: disable
# - TimescaleDB: Enabled
# - Version: 14+

# 5. Import dashboard
# - Dashboard > Import
# - Upload grafana/dashboards/crossbridge_overview.json
```

### Query Examples

**Total test executions (last 24h)**:
```sql
SELECT COUNT(*) 
FROM test_execution 
WHERE executed_at > NOW() - INTERVAL '24 hours'
```

**Pass rate**:
```sql
SELECT 
    (COUNT(*) FILTER (WHERE status = 'passed')::FLOAT / 
     NULLIF(COUNT(*), 0) * 100) as pass_rate
FROM test_execution 
WHERE executed_at > NOW() - INTERVAL '24 hours'
```

**Test execution trend** (uses continuous aggregate):
```sql
SELECT 
    bucket as time,
    status,
    execution_count as value
FROM test_execution_hourly 
WHERE bucket > NOW() - INTERVAL '7 days'
ORDER BY bucket
```

**Top flaky tests**:
```sql
SELECT 
    test_name,
    framework,
    (flaky_score * 100)::INT as flaky_score_pct,
    classification,
    severity
FROM flaky_test 
WHERE is_flaky = TRUE
ORDER BY flaky_score DESC 
LIMIT 10
```

## Performance Tuning

### TimescaleDB Optimization

```sql
-- Adjust chunk size based on data volume
SELECT set_chunk_time_interval('test_execution', INTERVAL '1 day');

-- Enable compression for older chunks
ALTER TABLE test_execution SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'framework,environment'
);

SELECT add_compression_policy('test_execution', INTERVAL '7 days');

-- Adjust continuous aggregate refresh
SELECT alter_continuous_aggregate_refresh_interval('test_execution_hourly', 
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour'
);
```

### pgvector Optimization

```sql
-- Adjust HNSW parameters for better performance
CREATE INDEX idx_memory_embedding_fast 
ON memory_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 8, ef_construction = 32);  -- Faster build, slightly lower accuracy

-- Or for higher accuracy
CREATE INDEX idx_memory_embedding_accurate 
ON memory_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);  -- Slower build, higher accuracy

-- Query-time tuning
SET hnsw.ef_search = 100;  -- Default is 40, higher = more accurate but slower
```

### PostgreSQL Tuning

```sql
-- Increase shared buffers
ALTER SYSTEM SET shared_buffers = '4GB';

-- Increase work memory for complex queries
ALTER SYSTEM SET work_mem = '256MB';

-- Increase effective cache size
ALTER SYSTEM SET effective_cache_size = '8GB';

-- Reload configuration
SELECT pg_reload_conf();
```

## Monitoring

### Key Metrics

1. **Data Volume**: `SELECT pg_size_pretty(pg_database_size('crossbridge'));`
2. **Chunk Count**: `SELECT count(*) FROM timescaledb_information.chunks;`
3. **Compression Ratio**: Check `timescaledb_information.compression_settings`
4. **Query Performance**: Use `EXPLAIN ANALYZE` on dashboard queries

### Health Checks

```sql
-- Check hypertables
SELECT * FROM timescaledb_information.hypertables;

-- Check continuous aggregates
SELECT * FROM timescaledb_information.continuous_aggregates;

-- Check retention policies
SELECT * FROM timescaledb_information.jobs WHERE proc_name LIKE '%retention%';

-- Check vector indexes
SELECT 
    schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE indexdef LIKE '%hnsw%';
```

## Troubleshooting

### TimescaleDB Issues

**Problem**: Hypertables not created  
**Solution**: Ensure TimescaleDB extension is installed and enabled

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
SELECT * FROM timescaledb_information.hypertables;
```

**Problem**: Continuous aggregates not refreshing  
**Solution**: Check refresh policies

```sql
SELECT * FROM timescaledb_information.job_stats 
WHERE job_type = 'refresh_continuous_aggregate';

-- Manually refresh
CALL refresh_continuous_aggregate('test_execution_hourly', NULL, NULL);
```

### pgvector Issues

**Problem**: Vector index not being used  
**Solution**: Check query plan and statistics

```sql
EXPLAIN ANALYZE 
SELECT * FROM memory_embeddings 
ORDER BY embedding <=> '[...]' 
LIMIT 10;

-- Update statistics
ANALYZE memory_embeddings;
```

**Problem**: Slow vector queries  
**Solution**: Adjust HNSW parameters or use IVFFlat

```sql
-- Try IVFFlat for faster build
CREATE INDEX idx_memory_embedding_ivfflat 
ON memory_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Migration Guide

### From Basic Schema to Comprehensive Schema

```bash
# 1. Backup existing data
pg_dump crossbridge > backup.sql

# 2. Run migration script
python scripts/migrate_to_comprehensive_schema.py

# 3. Verify data integrity
python scripts/verify_migration.py
```

### Upgrading TimescaleDB

```bash
# 1. Backup database
pg_dump crossbridge > backup_before_upgrade.sql

# 2. Upgrade extension
ALTER EXTENSION timescaledb UPDATE;

# 3. Run post-upgrade script
SELECT timescaledb_post_restore();
```

## Best Practices

1. **Retention Policies**: Set appropriate retention based on data volume and compliance
2. **Continuous Aggregates**: Use for frequently queried time ranges
3. **Compression**: Enable for older data to save storage
4. **Indexes**: Create indexes on frequently filtered columns
5. **Vector Embeddings**: Update embeddings when test code changes
6. **Grafana Queries**: Use continuous aggregates for dashboard performance
7. **Monitoring**: Set up alerts for data volume, query performance, and system health

## Support

- Documentation: `docs/`
- Issues: GitHub Issues
- Community: CrossBridge Slack/Discord
