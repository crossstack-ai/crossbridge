-- ============================================================================
-- CrossBridge Comprehensive Database Schema
-- ============================================================================
-- Complete PostgreSQL schema with TimescaleDB hypertables and pgvector
-- Designed for: Time-series analysis, Semantic search, Grafana dashboards
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;

-- ============================================================================
-- 1. DISCOVERY & TEST METADATA (Core Tables)
-- ============================================================================

-- Discovery Run (anchor table for all discovery operations)
CREATE TABLE IF NOT EXISTS discovery_run (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_name TEXT NOT NULL,
    git_commit TEXT,
    git_branch TEXT,
    triggered_by TEXT,           -- cli | ci | jira | manual
    framework TEXT,              -- junit | pytest | robot | cypress
    test_count INTEGER DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_discovery_run_created_at ON discovery_run(created_at DESC);
CREATE INDEX idx_discovery_run_project ON discovery_run(project_name);
CREATE INDEX idx_discovery_run_branch ON discovery_run(git_branch);
CREATE INDEX idx_discovery_run_framework ON discovery_run(framework);

-- Test Case (framework-agnostic test storage)
CREATE TABLE IF NOT EXISTS test_case (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework TEXT NOT NULL,
    package TEXT,
    class_name TEXT,
    method_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    tags TEXT[],
    intent TEXT,                 -- AI-extracted intent
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (framework, package, class_name, method_name)
);

CREATE INDEX idx_test_case_framework ON test_case(framework);
CREATE INDEX idx_test_case_file_path ON test_case(file_path);
CREATE INDEX idx_test_case_tags ON test_case USING GIN(tags);
CREATE INDEX idx_test_case_created_at ON test_case(created_at DESC);

-- Page Object (UI automation page objects)
CREATE TABLE IF NOT EXISTS page_object (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    framework TEXT,
    package TEXT,
    locator_count INTEGER DEFAULT 0,
    method_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (name, file_path)
);

CREATE INDEX idx_page_object_name ON page_object(name);
CREATE INDEX idx_page_object_file_path ON page_object(file_path);
CREATE INDEX idx_page_object_created_at ON page_object(created_at DESC);

-- Test to Page Mapping
CREATE TABLE IF NOT EXISTS test_page_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_case_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    page_object_id UUID NOT NULL REFERENCES page_object(id) ON DELETE CASCADE,
    source TEXT NOT NULL,        -- static_ast | coverage | ai | manual
    confidence FLOAT DEFAULT 1.0,
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_test_page_mapping_test ON test_page_mapping(test_case_id);
CREATE INDEX idx_test_page_mapping_page ON test_page_mapping(page_object_id);
CREATE INDEX idx_test_page_mapping_run ON test_page_mapping(discovery_run_id);


-- ============================================================================
-- 2. TEST EXECUTION HISTORY (TimescaleDB Hypertable)
-- ============================================================================

-- Test Execution Events (time-series data)
CREATE TABLE IF NOT EXISTS test_execution (
    id UUID DEFAULT uuid_generate_v4(),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Test identification
    test_id TEXT NOT NULL,
    test_name TEXT,
    test_file TEXT,
    test_line INTEGER,
    framework TEXT NOT NULL,
    
    -- Execution outcome
    status TEXT NOT NULL,        -- passed | failed | skipped | aborted | error
    duration_ms REAL NOT NULL,
    
    -- Error details
    error_signature TEXT,
    error_full TEXT,
    error_type TEXT,
    
    -- Context
    retry_count INTEGER DEFAULT 0,
    git_commit TEXT,
    environment TEXT DEFAULT 'unknown',
    build_id TEXT,
    ci_job_id TEXT,
    
    -- Product version tracking
    product_name TEXT,
    app_version TEXT,
    
    -- Test metadata
    tags TEXT[],
    metadata JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, executed_at)
);

-- Convert to hypertable (must be done after table creation)
SELECT create_hypertable('test_execution', 'executed_at', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for hypertable queries
CREATE INDEX IF NOT EXISTS idx_test_execution_test_id ON test_execution(test_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_test_execution_status ON test_execution(status, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_test_execution_framework ON test_execution(framework, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_test_execution_environment ON test_execution(environment, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_test_execution_build ON test_execution(build_id, executed_at DESC);

-- Retention policy: Keep detailed data for 90 days
SELECT add_retention_policy('test_execution', INTERVAL '90 days', if_not_exists => TRUE);


-- ============================================================================
-- 3. FLAKY TEST DETECTION
-- ============================================================================

-- Flaky Test Results (current state)
CREATE TABLE IF NOT EXISTS flaky_test (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Test identification
    test_id TEXT NOT NULL UNIQUE,
    test_name TEXT,
    framework TEXT NOT NULL,
    
    -- Flakiness scores
    flaky_score REAL NOT NULL,
    is_flaky BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    classification TEXT NOT NULL,  -- flaky | suspected_flaky | stable | insufficient_data
    severity TEXT,                 -- critical | high | medium | low | none
    
    -- Statistical features
    failure_rate REAL,
    switch_rate REAL,
    duration_variance REAL,
    unique_error_count INTEGER,
    total_executions INTEGER,
    
    -- Detection metadata
    primary_indicators TEXT[],
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version TEXT NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    -- Detailed analysis
    explanation JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_flaky_test_is_flaky ON flaky_test(is_flaky);
CREATE INDEX idx_flaky_test_classification ON flaky_test(classification);
CREATE INDEX idx_flaky_test_severity ON flaky_test(severity);
CREATE INDEX idx_flaky_test_detected_at ON flaky_test(detected_at DESC);

-- Flaky Test History (TimescaleDB Hypertable for trend analysis)
CREATE TABLE IF NOT EXISTS flaky_test_history (
    id UUID DEFAULT uuid_generate_v4(),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
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
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_flaky_history_test_id ON flaky_test_history(test_id, detected_at DESC);

-- Retention: Keep flaky history for 180 days
SELECT add_retention_policy('flaky_test_history', INTERVAL '180 days', if_not_exists => TRUE);


-- ============================================================================
-- 4. FUNCTIONAL COVERAGE & FEATURES
-- ============================================================================

-- Feature Registry
CREATE TABLE IF NOT EXISTS feature (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type TEXT NOT NULL,           -- api | service | bdd | module | component
    source TEXT NOT NULL,         -- cucumber | jira | code | manual | api_spec
    description TEXT,
    parent_feature_id UUID REFERENCES feature(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'active', -- active | deprecated | planned
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (name, type, source)
);

CREATE INDEX idx_feature_name ON feature(name);
CREATE INDEX idx_feature_type ON feature(type);
CREATE INDEX idx_feature_source ON feature(source);
CREATE INDEX idx_feature_status ON feature(status);

-- Code Units (for detailed coverage tracking)
CREATE TABLE IF NOT EXISTS code_unit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT NOT NULL,
    class_name TEXT,
    method_name TEXT,
    package_name TEXT,
    line_start INTEGER,
    line_end INTEGER,
    complexity INTEGER,
    language TEXT,                -- java | python | javascript | csharp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (file_path, class_name, method_name)
);

CREATE INDEX idx_code_unit_file_path ON code_unit(file_path);
CREATE INDEX idx_code_unit_class ON code_unit(class_name);

-- Test to Feature Mapping
CREATE TABLE IF NOT EXISTS test_feature_map (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_case_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    feature_id UUID NOT NULL REFERENCES feature(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,
    source TEXT NOT NULL,         -- coverage | tag | annotation | ai | manual
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (test_case_id, feature_id, source)
);

CREATE INDEX idx_test_feature_test ON test_feature_map(test_case_id);
CREATE INDEX idx_test_feature_feature ON test_feature_map(feature_id);

-- Test to Code Coverage Mapping
CREATE TABLE IF NOT EXISTS test_code_coverage_map (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_case_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    code_unit_id UUID NOT NULL REFERENCES code_unit(id) ON DELETE CASCADE,
    coverage_type TEXT NOT NULL,  -- instruction | line | branch | method
    covered_count INTEGER DEFAULT 0,
    missed_count INTEGER DEFAULT 0,
    coverage_percentage FLOAT DEFAULT 0.0,
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    UNIQUE (test_case_id, code_unit_id, coverage_type)
);

CREATE INDEX idx_test_code_test ON test_code_coverage_map(test_case_id);
CREATE INDEX idx_test_code_code ON test_code_coverage_map(code_unit_id);


-- ============================================================================
-- 5. MEMORY & EMBEDDINGS (pgvector for semantic search)
-- ============================================================================

-- Memory Embeddings (semantic search for tests, pages, failures)
CREATE TABLE IF NOT EXISTS memory_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL,           -- test | scenario | step | page | failure | code | assertion | locator
    text TEXT NOT NULL,
    embedding VECTOR(3072),       -- Adjust dimension based on model (3072 for text-embedding-3-large)
    metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_type ON memory_embeddings(type);
CREATE INDEX idx_memory_metadata ON memory_embeddings USING GIN(metadata jsonb_path_ops);

-- HNSW index for fast vector similarity search (crucial for performance)
CREATE INDEX IF NOT EXISTS idx_memory_embedding_cosine 
ON memory_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);


-- ============================================================================
-- 6. CHANGE IMPACT & GIT EVENTS (TimescaleDB Hypertable)
-- ============================================================================

-- Git Change Events (time-series for change tracking)
CREATE TABLE IF NOT EXISTS git_change_event (
    id UUID DEFAULT uuid_generate_v4(),
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    commit_sha TEXT NOT NULL,
    author TEXT NOT NULL,
    branch TEXT,
    message TEXT,
    
    -- Change details
    files_changed TEXT[],
    code_units_changed UUID[],    -- References to code_unit.id
    features_affected UUID[],     -- References to feature.id
    
    -- Impact surface
    tests_affected UUID[],        -- References to test_case.id
    risk_score FLOAT,             -- 0.0 to 1.0
    
    metadata JSONB,
    
    PRIMARY KEY (id, event_time)
);

SELECT create_hypertable('git_change_event', 'event_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_git_change_commit ON git_change_event(commit_sha, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_git_change_branch ON git_change_event(branch, event_time DESC);

-- Retention: Keep change events for 365 days
SELECT add_retention_policy('git_change_event', INTERVAL '365 days', if_not_exists => TRUE);


-- ============================================================================
-- 7. OBSERVABILITY EVENTS (TimescaleDB Hypertable)
-- ============================================================================

-- General observability events for monitoring CrossBridge itself
CREATE TABLE IF NOT EXISTS observability_event (
    id UUID DEFAULT uuid_generate_v4(),
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    event_type TEXT NOT NULL,     -- discovery | transformation | execution | analysis
    event_name TEXT NOT NULL,
    status TEXT NOT NULL,         -- started | completed | failed
    duration_ms INTEGER,
    
    -- Context
    project_name TEXT,
    framework TEXT,
    environment TEXT,
    
    -- Metrics
    metrics JSONB,                -- Flexible metrics storage
    error_message TEXT,
    
    metadata JSONB,
    
    PRIMARY KEY (id, event_time)
);

SELECT create_hypertable('observability_event', 'event_time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_obs_event_type ON observability_event(event_type, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_obs_event_status ON observability_event(status, event_time DESC);

-- Retention: Keep observability events for 30 days
SELECT add_retention_policy('observability_event', INTERVAL '30 days', if_not_exists => TRUE);


-- ============================================================================
-- 8. CONTINUOUS AGGREGATES (TimescaleDB for pre-computed metrics)
-- ============================================================================

-- Test execution summary (hourly aggregates for Grafana)
CREATE MATERIALIZED VIEW IF NOT EXISTS test_execution_hourly
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
GROUP BY bucket, framework, environment, status
WITH NO DATA;

-- Refresh policy: Update every hour
SELECT add_continuous_aggregate_policy('test_execution_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Test execution summary (daily aggregates)
CREATE MATERIALIZED VIEW IF NOT EXISTS test_execution_daily
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
GROUP BY bucket, framework, environment, status
WITH NO DATA;

SELECT add_continuous_aggregate_policy('test_execution_daily',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Flaky test trend (daily aggregates)
CREATE MATERIALIZED VIEW IF NOT EXISTS flaky_test_trend_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', detected_at) AS bucket,
    classification,
    COUNT(*) AS test_count,
    AVG(flaky_score) AS avg_flaky_score,
    AVG(confidence) AS avg_confidence
FROM flaky_test_history
GROUP BY bucket, classification
WITH NO DATA;

SELECT add_continuous_aggregate_policy('flaky_test_trend_daily',
    start_offset => INTERVAL '14 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);


-- ============================================================================
-- 9. ANALYTICAL VIEWS (For Grafana Dashboards)
-- ============================================================================

-- Test health overview
CREATE OR REPLACE VIEW test_health_overview AS
SELECT 
    COUNT(DISTINCT tc.id) AS total_tests,
    COUNT(DISTINCT CASE WHEN ft.is_flaky THEN tc.id END) AS flaky_tests,
    COUNT(DISTINCT po.id) AS total_pages,
    COUNT(DISTINCT f.id) AS total_features,
    COUNT(DISTINCT tfm.test_case_id) AS tests_with_feature_mapping,
    (COUNT(DISTINCT tfm.test_case_id)::FLOAT / NULLIF(COUNT(DISTINCT tc.id), 0)) * 100 AS feature_coverage_percent
FROM test_case tc
LEFT JOIN flaky_test ft ON tc.method_name = ft.test_id AND tc.framework = ft.framework
LEFT JOIN test_feature_map tfm ON tc.id = tfm.test_case_id
CROSS JOIN (SELECT COUNT(*) FROM page_object) po(id)
CROSS JOIN (SELECT COUNT(*) FROM feature) f(id);

-- Recent test execution summary (last 24 hours)
CREATE OR REPLACE VIEW recent_test_executions AS
SELECT 
    framework,
    status,
    COUNT(*) AS count,
    AVG(duration_ms) AS avg_duration,
    MIN(executed_at) AS first_execution,
    MAX(executed_at) AS last_execution
FROM test_execution
WHERE executed_at > NOW() - INTERVAL '24 hours'
GROUP BY framework, status
ORDER BY framework, status;

-- Flaky test summary
CREATE OR REPLACE VIEW flaky_test_summary AS
SELECT 
    ft.classification,
    ft.severity,
    COUNT(*) AS count,
    AVG(ft.flaky_score) AS avg_score,
    AVG(ft.confidence) AS avg_confidence,
    AVG(ft.failure_rate) AS avg_failure_rate
FROM flaky_test ft
WHERE ft.is_flaky = TRUE
GROUP BY ft.classification, ft.severity
ORDER BY ft.severity, ft.classification;

-- Feature coverage gaps
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
ORDER BY COUNT(tfm.test_case_id) ASC, f.name;


-- ============================================================================
-- 10. FUNCTIONS & TRIGGERS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update triggers
CREATE TRIGGER update_test_case_timestamp 
    BEFORE UPDATE ON test_case 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_page_object_timestamp 
    BEFORE UPDATE ON page_object 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feature_timestamp 
    BEFORE UPDATE ON feature 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_code_unit_timestamp 
    BEFORE UPDATE ON code_unit 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE discovery_run IS 'Test discovery runs with git context and metrics';
COMMENT ON TABLE test_case IS 'Framework-agnostic test case storage';
COMMENT ON TABLE page_object IS 'UI Page Object pattern implementations';
COMMENT ON TABLE test_execution IS 'Time-series test execution history (TimescaleDB hypertable)';
COMMENT ON TABLE flaky_test IS 'Current state of flaky test detection';
COMMENT ON TABLE flaky_test_history IS 'Historical flaky test detection trends (TimescaleDB hypertable)';
COMMENT ON TABLE feature IS 'Product feature registry for coverage mapping';
COMMENT ON TABLE code_unit IS 'Individual code units for detailed coverage tracking';
COMMENT ON TABLE memory_embeddings IS 'Semantic embeddings for AI-powered search (pgvector)';
COMMENT ON TABLE git_change_event IS 'Git change events with impact analysis (TimescaleDB hypertable)';
COMMENT ON TABLE observability_event IS 'CrossBridge observability and monitoring events (TimescaleDB hypertable)';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
