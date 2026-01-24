-- CrossBridge Comprehensive Database Schema (PostgreSQL + pgvector)
-- Version: 1.0 (pgvector-only, without TimescaleDB)
-- Description: Complete schema for test intelligence with semantic search capabilities
-- Dependencies: PostgreSQL 14+, pgvector 0.5+

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for semantic embeddings
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Discovery Runs: Track test discovery operations
CREATE TABLE IF NOT EXISTS discovery_run (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    total_tests_discovered INTEGER DEFAULT 0,
    new_tests_count INTEGER DEFAULT 0,
    modified_tests_count INTEGER DEFAULT 0,
    framework VARCHAR(100),
    git_branch VARCHAR(255),
    git_commit VARCHAR(40),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_discovery_run_status ON discovery_run(status);
CREATE INDEX idx_discovery_run_started_at ON discovery_run(started_at DESC);
CREATE INDEX idx_discovery_run_framework ON discovery_run(framework);

-- Test Cases: Core test metadata
CREATE TABLE IF NOT EXISTS test_case (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE SET NULL,
    test_name VARCHAR(500) NOT NULL,
    test_file_path TEXT NOT NULL,
    framework VARCHAR(100) NOT NULL,
    suite_name VARCHAR(255),
    description TEXT,
    tags TEXT[],
    priority VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active',
    first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(test_name, framework)
);

CREATE INDEX idx_test_case_framework ON test_case(framework);
CREATE INDEX idx_test_case_status ON test_case(status);
CREATE INDEX idx_test_case_discovery_run ON test_case(discovery_run_id);
CREATE INDEX idx_test_case_tags ON test_case USING GIN(tags);
CREATE INDEX idx_test_case_last_seen ON test_case(last_seen_at DESC);

-- Page Objects: UI component tracking
CREATE TABLE IF NOT EXISTS page_object (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    framework VARCHAR(100) NOT NULL,
    locators JSONB DEFAULT '[]',
    actions TEXT[],
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(page_name, framework)
);

CREATE INDEX idx_page_object_framework ON page_object(framework);
CREATE INDEX idx_page_object_locators ON page_object USING GIN(locators);

-- Test-Page Mapping: Link tests to page objects
CREATE TABLE IF NOT EXISTS test_page_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    page_id UUID NOT NULL REFERENCES page_object(id) ON DELETE CASCADE,
    interaction_count INTEGER DEFAULT 0,
    last_interaction_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(test_id, page_id)
);

CREATE INDEX idx_test_page_test_id ON test_page_mapping(test_id);
CREATE INDEX idx_test_page_page_id ON test_page_mapping(page_id);

-- ============================================================================
-- TIME-SERIES TABLES (Regular tables with time-based indexing)
-- ============================================================================

-- Test Executions: Execution history
CREATE TABLE IF NOT EXISTS test_execution (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL,
    duration_ms INTEGER,
    error_message TEXT,
    stack_trace TEXT,
    build_id VARCHAR(255),
    environment VARCHAR(100),
    browser VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Optimized indexes for time-series queries
CREATE INDEX idx_test_execution_executed_at ON test_execution(executed_at DESC);
CREATE INDEX idx_test_execution_test_id ON test_execution(test_id, executed_at DESC);
CREATE INDEX idx_test_execution_status ON test_execution(status);
CREATE INDEX idx_test_execution_build ON test_execution(build_id);
CREATE INDEX idx_test_execution_environment ON test_execution(environment);
CREATE INDEX idx_test_execution_composite ON test_execution(test_id, status, executed_at DESC);

-- Flaky Test History: Historical flaky trends
CREATE TABLE IF NOT EXISTS flaky_test_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    flaky_score DECIMAL(5,4),
    pass_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    skip_count INTEGER DEFAULT 0,
    classification VARCHAR(50),
    confidence_level DECIMAL(5,4),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_flaky_history_recorded_at ON flaky_test_history(recorded_at DESC);
CREATE INDEX idx_flaky_history_test_id ON flaky_test_history(test_id, recorded_at DESC);
CREATE INDEX idx_flaky_history_classification ON flaky_test_history(classification);

-- Git Change Events: Version control tracking
CREATE TABLE IF NOT EXISTS git_change_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    commit_sha VARCHAR(40) NOT NULL,
    author VARCHAR(255),
    commit_message TEXT,
    branch VARCHAR(255),
    changed_files TEXT[],
    test_files_changed TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_git_event_time ON git_change_event(event_time DESC);
CREATE INDEX idx_git_event_commit ON git_change_event(commit_sha);
CREATE INDEX idx_git_event_branch ON git_change_event(branch);

-- Observability Events: System monitoring
CREATE TABLE IF NOT EXISTS observability_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50),
    source VARCHAR(255),
    message TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_observability_event_time ON observability_event(event_time DESC);
CREATE INDEX idx_observability_event_type ON observability_event(event_type);
CREATE INDEX idx_observability_event_severity ON observability_event(severity);

-- ============================================================================
-- FLAKY TEST DETECTION
-- ============================================================================

-- Flaky Test Detection: Current state
CREATE TABLE IF NOT EXISTS flaky_test (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    is_flaky BOOLEAN NOT NULL DEFAULT FALSE,
    flaky_score DECIMAL(5,4) NOT NULL DEFAULT 0,
    confidence_level DECIMAL(5,4) NOT NULL DEFAULT 0,
    classification VARCHAR(50),
    severity VARCHAR(50),
    total_runs INTEGER DEFAULT 0,
    pass_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    skip_count INTEGER DEFAULT 0,
    first_detected_at TIMESTAMP WITH TIME ZONE,
    last_updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(test_id)
);

CREATE INDEX idx_flaky_test_is_flaky ON flaky_test(is_flaky);
CREATE INDEX idx_flaky_test_score ON flaky_test(flaky_score DESC);
CREATE INDEX idx_flaky_test_classification ON flaky_test(classification);
CREATE INDEX idx_flaky_test_severity ON flaky_test(severity);

-- ============================================================================
-- FEATURE COVERAGE TRACKING
-- ============================================================================

-- Features: Business features/requirements
CREATE TABLE IF NOT EXISTS feature (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name VARCHAR(500) NOT NULL,
    feature_type VARCHAR(100),
    description TEXT,
    priority VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active',
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(feature_name)
);

CREATE INDEX idx_feature_type ON feature(feature_type);
CREATE INDEX idx_feature_status ON feature(status);
CREATE INDEX idx_feature_priority ON feature(priority);
CREATE INDEX idx_feature_tags ON feature USING GIN(tags);

-- Code Units: Source code components
CREATE TABLE IF NOT EXISTS code_unit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT NOT NULL,
    unit_type VARCHAR(100) NOT NULL,
    unit_name VARCHAR(500) NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    complexity_score INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(file_path, unit_name)
);

CREATE INDEX idx_code_unit_type ON code_unit(unit_type);
CREATE INDEX idx_code_unit_file ON code_unit(file_path);
CREATE INDEX idx_code_unit_complexity ON code_unit(complexity_score DESC);

-- Test-Feature Mapping: Link tests to features
CREATE TABLE IF NOT EXISTS test_feature_map (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    feature_id UUID NOT NULL REFERENCES feature(id) ON DELETE CASCADE,
    coverage_type VARCHAR(100),
    confidence DECIMAL(5,4) DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(test_id, feature_id)
);

CREATE INDEX idx_test_feature_test_id ON test_feature_map(test_id);
CREATE INDEX idx_test_feature_feature_id ON test_feature_map(feature_id);
CREATE INDEX idx_test_feature_coverage_type ON test_feature_map(coverage_type);

-- Test-Code Coverage Mapping
CREATE TABLE IF NOT EXISTS test_code_coverage_map (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    code_unit_id UUID NOT NULL REFERENCES code_unit(id) ON DELETE CASCADE,
    lines_covered INTEGER[],
    coverage_percentage DECIMAL(5,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(test_id, code_unit_id)
);

CREATE INDEX idx_test_code_test_id ON test_code_coverage_map(test_id);
CREATE INDEX idx_test_code_unit_id ON test_code_coverage_map(code_unit_id);

-- ============================================================================
-- SEMANTIC SEARCH & EMBEDDINGS (pgvector)
-- ============================================================================

-- Memory Embeddings: Vector embeddings for semantic search
-- Using 1536 dimensions (OpenAI text-embedding-3-small or ada-002 compatible)
CREATE TABLE IF NOT EXISTS memory_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    embedding vector(1536),
    content_hash VARCHAR(64),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(entity_type, entity_id)
);

CREATE INDEX idx_memory_entity_type ON memory_embeddings(entity_type);
CREATE INDEX idx_memory_entity_id ON memory_embeddings(entity_id);

-- Create HNSW index for fast vector similarity search
-- m: number of connections per layer (16 is optimal for most cases)
-- ef_construction: size of dynamic candidate list (64 provides good recall)
CREATE INDEX idx_memory_embedding_cosine ON memory_embeddings 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- AGGREGATED VIEWS FOR GRAFANA (Without TimescaleDB continuous aggregates)
-- ============================================================================

-- Materialized view for hourly test execution metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS test_execution_hourly AS
SELECT 
    date_trunc('hour', executed_at) as bucket,
    test_id,
    status,
    COUNT(*) as execution_count,
    AVG(duration_ms) as avg_duration_ms,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) as p50_duration_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_duration_ms
FROM test_execution
WHERE executed_at > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('hour', executed_at), test_id, status;

CREATE INDEX idx_test_execution_hourly_bucket ON test_execution_hourly(bucket DESC);
CREATE INDEX idx_test_execution_hourly_test ON test_execution_hourly(test_id);

-- Materialized view for daily test execution summary
CREATE MATERIALIZED VIEW IF NOT EXISTS test_execution_daily AS
SELECT 
    date_trunc('day', executed_at) as bucket,
    COUNT(DISTINCT test_id) as unique_tests,
    COUNT(DISTINCT build_id) as unique_builds,
    COUNT(*) as total_executions,
    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_count,
    AVG(duration_ms) as avg_duration_ms
FROM test_execution
WHERE executed_at > NOW() - INTERVAL '90 days'
GROUP BY date_trunc('day', executed_at);

CREATE INDEX idx_test_execution_daily_bucket ON test_execution_daily(bucket DESC);

-- Materialized view for daily flaky test trends
CREATE MATERIALIZED VIEW IF NOT EXISTS flaky_test_trend_daily AS
SELECT 
    date_trunc('day', recorded_at) as bucket,
    classification,
    COUNT(*) as count,
    AVG(flaky_score) as avg_flaky_score,
    AVG(confidence_level) as avg_confidence
FROM flaky_test_history
WHERE recorded_at > NOW() - INTERVAL '90 days'
GROUP BY date_trunc('day', recorded_at), classification;

CREATE INDEX idx_flaky_test_trend_daily_bucket ON flaky_test_trend_daily(bucket DESC);

-- ============================================================================
-- ANALYTICAL VIEWS
-- ============================================================================

-- Test Health Overview
CREATE OR REPLACE VIEW test_health_overview AS
SELECT 
    tc.id,
    tc.test_name,
    tc.framework,
    tc.suite_name,
    COUNT(te.id) as total_executions,
    SUM(CASE WHEN te.status = 'passed' THEN 1 ELSE 0 END) as passed_count,
    SUM(CASE WHEN te.status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN te.status = 'skipped' THEN 1 ELSE 0 END) as skipped_count,
    AVG(te.duration_ms) as avg_duration_ms,
    MAX(te.executed_at) as last_execution,
    ft.is_flaky,
    ft.flaky_score,
    ft.classification as flaky_classification
FROM test_case tc
LEFT JOIN test_execution te ON tc.id = te.test_id
    AND te.executed_at > NOW() - INTERVAL '30 days'
LEFT JOIN flaky_test ft ON tc.id = ft.test_id
GROUP BY tc.id, tc.test_name, tc.framework, tc.suite_name, 
         ft.is_flaky, ft.flaky_score, ft.classification;

-- Recent Test Executions
CREATE OR REPLACE VIEW recent_test_executions AS
SELECT 
    te.id,
    tc.test_name,
    tc.framework,
    te.status,
    te.duration_ms,
    te.executed_at,
    te.build_id,
    te.environment,
    te.error_message
FROM test_execution te
JOIN test_case tc ON te.test_id = tc.id
WHERE te.executed_at > NOW() - INTERVAL '24 hours'
ORDER BY te.executed_at DESC;

-- Flaky Test Summary
CREATE OR REPLACE VIEW flaky_test_summary AS
SELECT 
    tc.test_name,
    tc.framework,
    ft.flaky_score,
    ft.classification,
    ft.severity,
    ft.total_runs,
    ft.pass_count,
    ft.fail_count,
    ft.first_detected_at,
    ft.last_updated_at
FROM flaky_test ft
JOIN test_case tc ON ft.test_id = tc.id
WHERE ft.is_flaky = TRUE
ORDER BY ft.flaky_score DESC;

-- Feature Coverage Gaps
CREATE OR REPLACE VIEW feature_coverage_gaps AS
SELECT 
    f.feature_name,
    f.feature_type,
    f.priority,
    COUNT(tfm.test_id) as test_count,
    CASE 
        WHEN COUNT(tfm.test_id) = 0 THEN 'No Coverage'
        WHEN COUNT(tfm.test_id) < 3 THEN 'Low Coverage'
        ELSE 'Adequate Coverage'
    END as coverage_status
FROM feature f
LEFT JOIN test_feature_map tfm ON f.id = tfm.feature_id
WHERE f.status = 'active'
GROUP BY f.id, f.feature_name, f.feature_type, f.priority
HAVING COUNT(tfm.test_id) < 3
ORDER BY f.priority DESC, COUNT(tfm.test_id) ASC;

-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATE TIMESTAMPS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update trigger to relevant tables
CREATE TRIGGER update_test_case_updated_at
    BEFORE UPDATE ON test_case
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_page_object_updated_at
    BEFORE UPDATE ON page_object
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feature_updated_at
    BEFORE UPDATE ON feature
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_code_unit_updated_at
    BEFORE UPDATE ON code_unit
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- MATERIALIZED VIEW REFRESH FUNCTION
-- ============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY test_execution_hourly;
    REFRESH MATERIALIZED VIEW CONCURRENTLY test_execution_daily;
    REFRESH MATERIALIZED VIEW CONCURRENTLY flaky_test_trend_daily;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE discovery_run IS 'Tracks test discovery operations and git context';
COMMENT ON TABLE test_case IS 'Core test metadata including framework, tags, and status';
COMMENT ON TABLE page_object IS 'UI page objects with locators and actions';
COMMENT ON TABLE test_execution IS 'Time-series test execution history';
COMMENT ON TABLE flaky_test IS 'Current flaky test detection state';
COMMENT ON TABLE flaky_test_history IS 'Historical flaky test trends';
COMMENT ON TABLE feature IS 'Business features and requirements';
COMMENT ON TABLE memory_embeddings IS 'Vector embeddings for semantic search using pgvector';
COMMENT ON MATERIALIZED VIEW test_execution_hourly IS 'Hourly aggregated test execution metrics';
COMMENT ON MATERIALIZED VIEW test_execution_daily IS 'Daily aggregated test execution summary';
COMMENT ON MATERIALIZED VIEW flaky_test_trend_daily IS 'Daily flaky test classification trends';

-- Schema setup complete
SELECT 'CrossBridge schema setup complete (pgvector-only version)' as status;
