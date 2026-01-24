-- =====================================================
-- CrossBridge Comprehensive Database Schema (Basic Version)
-- PostgreSQL 14+ without TimescaleDB/pgvector
-- =====================================================
-- This version provides the same functionality without requiring TimescaleDB or pgvector extensions
-- Time-series features are implemented using native PostgreSQL partitioning
-- Vector search can be added later when pgvector is available

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- CORE TABLES
-- =====================================================

-- Discovery Run: Tracks each discovery operation
CREATE TABLE IF NOT EXISTS discovery_run (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_url TEXT NOT NULL,
    branch_name TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT CHECK (status IN ('running', 'completed', 'failed')),
    frameworks_detected TEXT[],
    total_tests_found INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_discovery_run_commit ON discovery_run(commit_hash);
CREATE INDEX idx_discovery_run_started ON discovery_run(started_at DESC);
CREATE INDEX idx_discovery_run_status ON discovery_run(status);

-- Test Case: Stores individual test information
CREATE TABLE IF NOT EXISTS test_case (
    test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discovery_run_id UUID REFERENCES discovery_run(run_id) ON DELETE CASCADE,
    test_name TEXT NOT NULL,
    test_suite TEXT,
    framework TEXT NOT NULL,
    file_path TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    tags TEXT[],
    dependencies TEXT[],
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_case_discovery ON test_case(discovery_run_id);
CREATE INDEX idx_test_case_name ON test_case(test_name);
CREATE INDEX idx_test_case_framework ON test_case(framework);
CREATE INDEX idx_test_case_file ON test_case(file_path);
CREATE INDEX idx_test_case_tags ON test_case USING GIN(tags);

-- Page Object: Tracks page objects and UI components
CREATE TABLE IF NOT EXISTS page_object (
    page_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    class_name TEXT,
    locators JSONB DEFAULT '[]'::JSONB,
    actions TEXT[],
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_page_object_name ON page_object(page_name);
CREATE INDEX idx_page_object_file ON page_object(file_path);
CREATE INDEX idx_page_object_locators ON page_object USING GIN(locators);

-- Test to Page Mapping: Links tests to page objects
CREATE TABLE IF NOT EXISTS test_page_mapping (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID REFERENCES test_case(test_id) ON DELETE CASCADE,
    page_id UUID REFERENCES page_object(page_id) ON DELETE CASCADE,
    interaction_type TEXT,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_id, page_id)
);

CREATE INDEX idx_test_page_mapping_test ON test_page_mapping(test_id);
CREATE INDEX idx_test_page_mapping_page ON test_page_mapping(page_id);

-- =====================================================
-- TIME-SERIES TABLES (Using Native Partitioning)
-- =====================================================

-- Test Execution: Stores test run results (partitioned by month)
CREATE TABLE IF NOT EXISTS test_execution (
    execution_id UUID DEFAULT uuid_generate_v4(),
    test_id UUID REFERENCES test_case(test_id) ON DELETE CASCADE,
    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'skipped', 'error')),
    build_id TEXT,
    environment TEXT,
    error_message TEXT,
    stack_trace TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    PRIMARY KEY (execution_id, executed_at)
) PARTITION BY RANGE (executed_at);

-- Create partitions for current and next 3 months
CREATE TABLE IF NOT EXISTS test_execution_2026_01 PARTITION OF test_execution
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE IF NOT EXISTS test_execution_2026_02 PARTITION OF test_execution
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE IF NOT EXISTS test_execution_2026_03 PARTITION OF test_execution
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS test_execution_2026_04 PARTITION OF test_execution
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Indexes on partitioned table
CREATE INDEX IF NOT EXISTS idx_test_execution_test ON test_execution(test_id);
CREATE INDEX IF NOT EXISTS idx_test_execution_executed ON test_execution(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_test_execution_status ON test_execution(status);
CREATE INDEX IF NOT EXISTS idx_test_execution_build ON test_execution(build_id);
CREATE INDEX IF NOT EXISTS idx_test_execution_env ON test_execution(environment);

-- Flaky Test History: Tracks flaky test patterns (partitioned by month)
CREATE TABLE IF NOT EXISTS flaky_test_history (
    history_id UUID DEFAULT uuid_generate_v4(),
    test_id UUID REFERENCES test_case(test_id) ON DELETE CASCADE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    flaky_score FLOAT NOT NULL,
    pass_rate FLOAT,
    fail_rate FLOAT,
    total_runs INTEGER,
    classification TEXT CHECK (classification IN ('improving', 'degrading', 'stable', 'new')),
    metadata JSONB DEFAULT '{}'::JSONB,
    PRIMARY KEY (history_id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Create partitions for current and next 3 months
CREATE TABLE IF NOT EXISTS flaky_test_history_2026_01 PARTITION OF flaky_test_history
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE IF NOT EXISTS flaky_test_history_2026_02 PARTITION OF flaky_test_history
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE IF NOT EXISTS flaky_test_history_2026_03 PARTITION OF flaky_test_history
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS flaky_test_history_2026_04 PARTITION OF flaky_test_history
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Indexes on partitioned table
CREATE INDEX IF NOT EXISTS idx_flaky_history_test ON flaky_test_history(test_id);
CREATE INDEX IF NOT EXISTS idx_flaky_history_recorded ON flaky_test_history(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_flaky_history_score ON flaky_test_history(flaky_score DESC);

-- Git Change Event: Tracks code changes (partitioned by month)
CREATE TABLE IF NOT EXISTS git_change_event (
    event_id UUID DEFAULT uuid_generate_v4(),
    commit_hash TEXT NOT NULL,
    event_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author TEXT,
    message TEXT,
    files_changed TEXT[],
    insertions INTEGER,
    deletions INTEGER,
    metadata JSONB DEFAULT '{}'::JSONB,
    PRIMARY KEY (event_id, event_time)
) PARTITION BY RANGE (event_time);

-- Create partitions for current and next 3 months
CREATE TABLE IF NOT EXISTS git_change_event_2026_01 PARTITION OF git_change_event
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE IF NOT EXISTS git_change_event_2026_02 PARTITION OF git_change_event
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE IF NOT EXISTS git_change_event_2026_03 PARTITION OF git_change_event
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS git_change_event_2026_04 PARTITION OF git_change_event
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Indexes on partitioned table
CREATE INDEX IF NOT EXISTS idx_git_event_commit ON git_change_event(commit_hash);
CREATE INDEX IF NOT EXISTS idx_git_event_time ON git_change_event(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_git_event_author ON git_change_event(author);

-- Observability Event: System monitoring events (partitioned by month)
CREATE TABLE IF NOT EXISTS observability_event (
    event_id UUID DEFAULT uuid_generate_v4(),
    event_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    source TEXT,
    message TEXT,
    details JSONB DEFAULT '{}'::JSONB,
    PRIMARY KEY (event_id, event_time)
) PARTITION BY RANGE (event_time);

-- Create partitions for current and next 3 months
CREATE TABLE IF NOT EXISTS observability_event_2026_01 PARTITION OF observability_event
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE IF NOT EXISTS observability_event_2026_02 PARTITION OF observability_event
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE IF NOT EXISTS observability_event_2026_03 PARTITION OF observability_event
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS observability_event_2026_04 PARTITION OF observability_event
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Indexes on partitioned table
CREATE INDEX IF NOT EXISTS idx_observability_type ON observability_event(event_type);
CREATE INDEX IF NOT EXISTS idx_observability_time ON observability_event(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_observability_severity ON observability_event(severity);

-- =====================================================
-- FLAKY TEST DETECTION
-- =====================================================

-- Flaky Test: Current state of potentially flaky tests
CREATE TABLE IF NOT EXISTS flaky_test (
    flaky_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID REFERENCES test_case(test_id) ON DELETE CASCADE,
    first_detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_occurrence_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    flaky_score FLOAT NOT NULL CHECK (flaky_score >= 0 AND flaky_score <= 1),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    classification TEXT NOT NULL CHECK (classification IN ('improving', 'degrading', 'stable', 'new')),
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    is_flaky BOOLEAN DEFAULT TRUE,
    total_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_id)
);

CREATE INDEX idx_flaky_test_test ON flaky_test(test_id);
CREATE INDEX idx_flaky_test_score ON flaky_test(flaky_score DESC);
CREATE INDEX idx_flaky_test_severity ON flaky_test(severity);
CREATE INDEX idx_flaky_test_is_flaky ON flaky_test(is_flaky);

-- =====================================================
-- FEATURE COVERAGE TRACKING
-- =====================================================

-- Feature: Product features being tested
CREATE TABLE IF NOT EXISTS feature (
    feature_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name TEXT NOT NULL,
    feature_type TEXT CHECK (feature_type IN ('api', 'service', 'bdd', 'module', 'component')),
    description TEXT,
    priority TEXT CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    owner TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feature_name ON feature(feature_name);
CREATE INDEX idx_feature_type ON feature(feature_type);
CREATE INDEX idx_feature_priority ON feature(priority);

-- Code Unit: Code modules, classes, functions
CREATE TABLE IF NOT EXISTS code_unit (
    unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_name TEXT NOT NULL,
    unit_type TEXT CHECK (unit_type IN ('module', 'class', 'function', 'method')),
    file_path TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    complexity INTEGER,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_code_unit_name ON code_unit(unit_name);
CREATE INDEX idx_code_unit_file ON code_unit(file_path);
CREATE INDEX idx_code_unit_type ON code_unit(unit_type);

-- Test to Feature Mapping: Links tests to features
CREATE TABLE IF NOT EXISTS test_feature_map (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID REFERENCES test_case(test_id) ON DELETE CASCADE,
    feature_id UUID REFERENCES feature(feature_id) ON DELETE CASCADE,
    coverage_type TEXT CHECK (coverage_type IN ('direct', 'indirect', 'integration')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_id, feature_id)
);

CREATE INDEX idx_test_feature_map_test ON test_feature_map(test_id);
CREATE INDEX idx_test_feature_map_feature ON test_feature_map(feature_id);

-- Test to Code Coverage Mapping: Links tests to code units
CREATE TABLE IF NOT EXISTS test_code_coverage_map (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID REFERENCES test_case(test_id) ON DELETE CASCADE,
    unit_id UUID REFERENCES code_unit(unit_id) ON DELETE CASCADE,
    line_coverage FLOAT,
    branch_coverage FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_id, unit_id)
);

CREATE INDEX idx_test_code_coverage_map_test ON test_code_coverage_map(test_id);
CREATE INDEX idx_test_code_coverage_map_unit ON test_code_coverage_map(unit_id);

-- =====================================================
-- MEMORY EMBEDDINGS (Without pgvector)
-- =====================================================
-- Note: Vector similarity search will require pgvector extension
-- This table stores embeddings but cosine similarity must be computed in application

CREATE TABLE IF NOT EXISTS memory_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type TEXT NOT NULL CHECK (content_type IN ('test', 'step_definition', 'page_object', 'feature')),
    content_id UUID NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_text TEXT NOT NULL,
    embedding FLOAT[] NOT NULL, -- Store as array for now, can migrate to vector type later
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_memory_embeddings_content ON memory_embeddings(content_type, content_id);
CREATE INDEX idx_memory_embeddings_model ON memory_embeddings(embedding_model);

-- =====================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE (Instead of Continuous Aggregates)
-- =====================================================

-- Test Execution Hourly Summary
CREATE MATERIALIZED VIEW IF NOT EXISTS test_execution_hourly AS
SELECT 
    DATE_TRUNC('hour', executed_at) AS bucket,
    test_id,
    status,
    COUNT(*) AS execution_count,
    AVG(duration_ms) AS avg_duration_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_duration_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99_duration_ms,
    MIN(duration_ms) AS min_duration_ms,
    MAX(duration_ms) AS max_duration_ms
FROM test_execution
WHERE executed_at >= NOW() - INTERVAL '7 days'
GROUP BY bucket, test_id, status;

CREATE INDEX idx_test_execution_hourly_bucket ON test_execution_hourly(bucket DESC);
CREATE INDEX idx_test_execution_hourly_test ON test_execution_hourly(test_id);

-- Test Execution Daily Summary
CREATE MATERIALIZED VIEW IF NOT EXISTS test_execution_daily AS
SELECT 
    DATE_TRUNC('day', executed_at) AS bucket,
    status,
    COUNT(*) AS execution_count,
    COUNT(DISTINCT test_id) AS unique_tests,
    COUNT(DISTINCT build_id) AS unique_builds,
    AVG(duration_ms) AS avg_duration_ms
FROM test_execution
WHERE executed_at >= NOW() - INTERVAL '30 days'
GROUP BY bucket, status;

CREATE INDEX idx_test_execution_daily_bucket ON test_execution_daily(bucket DESC);

-- Flaky Test Trend Daily
CREATE MATERIALIZED VIEW IF NOT EXISTS flaky_test_trend_daily AS
SELECT 
    DATE_TRUNC('day', recorded_at) AS bucket,
    classification,
    COUNT(*) AS test_count,
    AVG(flaky_score) AS avg_flaky_score,
    AVG(pass_rate) AS avg_pass_rate
FROM flaky_test_history
WHERE recorded_at >= NOW() - INTERVAL '30 days'
GROUP BY bucket, classification;

CREATE INDEX idx_flaky_test_trend_daily_bucket ON flaky_test_trend_daily(bucket DESC);

-- =====================================================
-- ANALYTICAL VIEWS
-- =====================================================

-- Test Health Overview: Overall test suite health metrics
CREATE OR REPLACE VIEW test_health_overview AS
SELECT 
    COUNT(DISTINCT tc.test_id) AS total_tests,
    COUNT(DISTINCT te.test_id) AS active_tests,
    COUNT(DISTINCT CASE WHEN ft.is_flaky THEN tc.test_id END) AS flaky_tests,
    ROUND(AVG(CASE WHEN te.status = 'passed' THEN 1.0 ELSE 0.0 END) * 100, 2) AS pass_rate,
    ROUND(AVG(te.duration_ms), 0) AS avg_duration_ms,
    COUNT(DISTINCT f.feature_id) AS total_features,
    COUNT(DISTINCT tfm.feature_id) AS covered_features
FROM test_case tc
LEFT JOIN test_execution te ON tc.test_id = te.test_id 
    AND te.executed_at >= NOW() - INTERVAL '24 hours'
LEFT JOIN flaky_test ft ON tc.test_id = ft.test_id
LEFT JOIN test_feature_map tfm ON tc.test_id = tfm.test_id
LEFT JOIN feature f ON tfm.feature_id = f.feature_id;

-- Recent Test Executions: Last 24 hours of test runs
CREATE OR REPLACE VIEW recent_test_executions AS
SELECT 
    te.execution_id,
    tc.test_name,
    tc.framework,
    te.executed_at,
    te.duration_ms,
    te.status,
    te.build_id,
    te.environment,
    CASE WHEN ft.is_flaky THEN 'Yes' ELSE 'No' END AS is_flaky
FROM test_execution te
JOIN test_case tc ON te.test_id = tc.test_id
LEFT JOIN flaky_test ft ON tc.test_id = ft.test_id
WHERE te.executed_at >= NOW() - INTERVAL '24 hours'
ORDER BY te.executed_at DESC;

-- Flaky Test Summary: Current flaky test status
CREATE OR REPLACE VIEW flaky_test_summary AS
SELECT 
    ft.flaky_id,
    tc.test_name,
    tc.framework,
    ft.flaky_score,
    ft.confidence,
    ft.classification,
    ft.severity,
    ft.total_runs,
    ft.failed_runs,
    ROUND((ft.failed_runs::FLOAT / NULLIF(ft.total_runs, 0)) * 100, 2) AS fail_rate,
    ft.first_detected_at,
    ft.last_occurrence_at
FROM flaky_test ft
JOIN test_case tc ON ft.test_id = tc.test_id
WHERE ft.is_flaky = TRUE
ORDER BY ft.severity DESC, ft.flaky_score DESC;

-- Feature Coverage Gaps: Features with no or low test coverage
CREATE OR REPLACE VIEW feature_coverage_gaps AS
SELECT 
    f.feature_id,
    f.feature_name,
    f.feature_type,
    f.priority,
    f.owner,
    COUNT(DISTINCT tfm.test_id) AS test_count,
    CASE 
        WHEN COUNT(DISTINCT tfm.test_id) = 0 THEN 'No Coverage'
        WHEN COUNT(DISTINCT tfm.test_id) < 3 THEN 'Low Coverage'
        ELSE 'Adequate Coverage'
    END AS coverage_status
FROM feature f
LEFT JOIN test_feature_map tfm ON f.feature_id = tfm.feature_id
GROUP BY f.feature_id, f.feature_name, f.feature_type, f.priority, f.owner
HAVING COUNT(DISTINCT tfm.test_id) < 3
ORDER BY f.priority DESC, COUNT(DISTINCT tfm.test_id) ASC;

-- =====================================================
-- AUTOMATIC UPDATE TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to relevant tables
DROP TRIGGER IF EXISTS update_test_case_updated_at ON test_case;
CREATE TRIGGER update_test_case_updated_at
    BEFORE UPDATE ON test_case
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_page_object_updated_at ON page_object;
CREATE TRIGGER update_page_object_updated_at
    BEFORE UPDATE ON page_object
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_feature_updated_at ON feature;
CREATE TRIGGER update_feature_updated_at
    BEFORE UPDATE ON feature
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_code_unit_updated_at ON code_unit;
CREATE TRIGGER update_code_unit_updated_at
    BEFORE UPDATE ON code_unit
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_flaky_test_updated_at ON flaky_test;
CREATE TRIGGER update_flaky_test_updated_at
    BEFORE UPDATE ON flaky_test
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- MAINTENANCE FUNCTIONS
-- =====================================================

-- Function to create new partitions for time-series tables
CREATE OR REPLACE FUNCTION create_monthly_partitions(
    start_date DATE,
    months_ahead INTEGER
)
RETURNS VOID AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    next_date DATE;
BEGIN
    FOR i IN 0..months_ahead LOOP
        partition_date := start_date + (i || ' months')::INTERVAL;
        next_date := partition_date + INTERVAL '1 month';
        
        -- Test Execution partitions
        partition_name := 'test_execution_' || TO_CHAR(partition_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF test_execution FOR VALUES FROM (%L) TO (%L)',
                      partition_name, partition_date, next_date);
        
        -- Flaky Test History partitions
        partition_name := 'flaky_test_history_' || TO_CHAR(partition_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF flaky_test_history FOR VALUES FROM (%L) TO (%L)',
                      partition_name, partition_date, next_date);
        
        -- Git Change Event partitions
        partition_name := 'git_change_event_' || TO_CHAR(partition_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF git_change_event FOR VALUES FROM (%L) TO (%L)',
                      partition_name, partition_date, next_date);
        
        -- Observability Event partitions
        partition_name := 'observability_event_' || TO_CHAR(partition_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF observability_event FOR VALUES FROM (%L) TO (%L)',
                      partition_name, partition_date, next_date);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY test_execution_hourly;
    REFRESH MATERIALIZED VIEW CONCURRENTLY test_execution_daily;
    REFRESH MATERIALIZED VIEW CONCURRENTLY flaky_test_trend_daily;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- INITIAL SETUP COMPLETE
-- =====================================================

-- Create initial partitions (3 months ahead)
SELECT create_monthly_partitions(DATE_TRUNC('month', CURRENT_DATE), 3);

COMMENT ON DATABASE CURRENT_DATABASE() IS 'CrossBridge Test Intelligence Database (Basic Version without TimescaleDB/pgvector)';
