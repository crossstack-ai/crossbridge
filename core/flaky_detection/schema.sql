-- Flaky Test Detection Database Schema
-- For storing test execution history and flaky detection results

-- Table: test_execution
-- Stores normalized execution records from all frameworks
CREATE TABLE IF NOT EXISTS test_execution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Test identification
    test_id TEXT NOT NULL,
    test_name TEXT,
    test_file TEXT,
    test_line INTEGER,
    framework TEXT NOT NULL,
    
    -- Execution outcome
    status TEXT NOT NULL,  -- passed | failed | skipped | aborted | error
    duration_ms REAL NOT NULL,
    executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Error details
    error_signature TEXT,
    error_full TEXT,
    error_type TEXT,
    
    -- Context
    retry_count INTEGER DEFAULT 0,
    git_commit TEXT,
    environment TEXT DEFAULT 'unknown',
    build_id TEXT,
    
    -- Test metadata (JSON)
    tags TEXT[],
    metadata JSONB,
    
    -- Indexing
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_test_execution_test_id ON test_execution(test_id);
CREATE INDEX IF NOT EXISTS idx_test_execution_executed_at ON test_execution(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_test_execution_status ON test_execution(status);
CREATE INDEX IF NOT EXISTS idx_test_execution_framework ON test_execution(framework);
CREATE INDEX IF NOT EXISTS idx_test_execution_git_commit ON test_execution(git_commit);
CREATE INDEX IF NOT EXISTS idx_test_execution_composite ON test_execution(test_id, executed_at DESC);

-- Table: flaky_test
-- Stores flaky test detection results
CREATE TABLE IF NOT EXISTS flaky_test (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Test identification
    test_id TEXT NOT NULL UNIQUE,
    test_name TEXT,
    framework TEXT NOT NULL,
    
    -- Flakiness scores
    flaky_score REAL NOT NULL,
    is_flaky BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    classification TEXT NOT NULL,  -- flaky | suspected_flaky | stable | insufficient_data
    severity TEXT,  -- critical | high | medium | low | none
    
    -- Features used
    failure_rate REAL,
    switch_rate REAL,
    duration_variance REAL,
    unique_error_count INTEGER,
    total_executions INTEGER,
    
    -- Detection metadata
    primary_indicators TEXT[],
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    model_version TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW(),
    
    -- Phase-2: Explanation (JSONB for detailed analysis)
    explanation JSONB,
    
    -- Indexing
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for flaky_test
CREATE INDEX IF NOT EXISTS idx_flaky_test_is_flaky ON flaky_test(is_flaky);
CREATE INDEX IF NOT EXISTS idx_flaky_test_classification ON flaky_test(classification);
CREATE INDEX IF NOT EXISTS idx_flaky_test_severity ON flaky_test(severity);
CREATE INDEX IF NOT EXISTS idx_flaky_test_confidence ON flaky_test(confidence);
CREATE INDEX IF NOT EXISTS idx_flaky_test_detected_at ON flaky_test(detected_at DESC);

-- Table: flaky_test_history
-- Stores historical flaky detection results for trend analysis
CREATE TABLE IF NOT EXISTS flaky_test_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    test_id TEXT NOT NULL,
    flaky_score REAL NOT NULL,
    is_flaky BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    classification TEXT NOT NULL,
    failure_rate REAL,
    total_executions INTEGER,
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    model_version TEXT NOT NULL,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for history queries
CREATE INDEX IF NOT EXISTS idx_flaky_history_test_id ON flaky_test_history(test_id, detected_at DESC);

-- View: flaky_test_summary
-- Aggregated view of flaky tests with latest execution info
CREATE OR REPLACE VIEW flaky_test_summary AS
SELECT 
    f.test_id,
    f.test_name,
    f.framework,
    f.is_flaky,
    f.confidence,
    f.classification,
    f.severity,
    f.failure_rate,
    f.switch_rate,
    f.total_executions,
    f.primary_indicators,
    f.detected_at,
    e.last_execution,
    e.last_status
FROM flaky_test f
LEFT JOIN LATERAL (
    SELECT 
        executed_at as last_execution,
        status as last_status
    FROM test_execution
    WHERE test_id = f.test_id
    ORDER BY executed_at DESC
    LIMIT 1
) e ON true
WHERE f.is_flaky = true
ORDER BY 
    CASE f.severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END,
    f.failure_rate DESC;

-- View: test_execution_stats
-- Aggregated execution statistics per test
CREATE OR REPLACE VIEW test_execution_stats AS
SELECT
    test_id,
    test_name,
    framework,
    COUNT(*) as total_executions,
    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_count,
    SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_count,
    ROUND(
        SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END)::numeric / 
        COUNT(*)::numeric * 100,
        2
    ) as failure_rate_pct,
    ROUND(AVG(duration_ms), 2) as avg_duration_ms,
    ROUND(STDDEV(duration_ms), 2) as stddev_duration_ms,
    MAX(executed_at) as last_executed,
    MIN(executed_at) as first_executed
FROM test_execution
GROUP BY test_id, test_name, framework;

-- Function: cleanup_old_executions
-- Remove old execution records to manage database size
CREATE OR REPLACE FUNCTION cleanup_old_executions(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM test_execution
    WHERE executed_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function: update_flaky_test_timestamp
-- Automatically update last_updated timestamp
CREATE OR REPLACE FUNCTION update_flaky_test_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Update timestamp on flaky_test changes
CREATE TRIGGER trigger_update_flaky_test_timestamp
    BEFORE UPDATE ON flaky_test
    FOR EACH ROW
    EXECUTE FUNCTION update_flaky_test_timestamp();

-- Comments for documentation
COMMENT ON TABLE test_execution IS 'Normalized test execution records from all frameworks';
COMMENT ON TABLE flaky_test IS 'Current flaky test detection results';
COMMENT ON TABLE flaky_test_history IS 'Historical flaky detection results for trend analysis';

-- ============================================================================
-- Phase-2: Step-Level Detection Tables
-- ============================================================================

-- Table: step_execution
-- Stores step/keyword execution records for BDD and keyword-based frameworks
CREATE TABLE IF NOT EXISTS step_execution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Step identification
    step_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    step_text TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    
    -- Execution outcome
    status TEXT NOT NULL,  -- passed | failed | skipped | aborted
    duration_ms REAL NOT NULL,
    executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Error details
    error_signature TEXT,
    error_message TEXT,
    stack_trace TEXT,
    
    -- Context
    framework TEXT NOT NULL,
    environment TEXT DEFAULT 'unknown',
    git_commit TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Step metadata
    is_background BOOLEAN DEFAULT FALSE,
    is_hook BOOLEAN DEFAULT FALSE,
    keyword_type TEXT,  -- Robot: setup, teardown, test, etc.
    
    -- Indexing
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for step execution
CREATE INDEX IF NOT EXISTS idx_step_execution_step_id ON step_execution(step_id);
CREATE INDEX IF NOT EXISTS idx_step_execution_scenario_id ON step_execution(scenario_id);
CREATE INDEX IF NOT EXISTS idx_step_execution_test_id ON step_execution(test_id);
CREATE INDEX IF NOT EXISTS idx_step_execution_executed_at ON step_execution(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_step_execution_composite ON step_execution(step_id, executed_at DESC);

-- Table: flaky_step
-- Stores step-level flaky detection results
CREATE TABLE IF NOT EXISTS flaky_step (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Step identification
    step_id TEXT NOT NULL UNIQUE,
    step_text TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    framework TEXT NOT NULL,
    
    -- Flakiness scores
    flaky_score REAL NOT NULL,
    is_flaky BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    classification TEXT NOT NULL,
    severity TEXT,
    
    -- Features
    step_failure_rate REAL,
    step_switch_rate REAL,
    step_duration_variance REAL,
    unique_error_count INTEGER,
    total_executions INTEGER,
    
    -- Detection metadata
    primary_indicators TEXT[],
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    model_version TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW(),
    
    -- Indexing
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for flaky steps
CREATE INDEX IF NOT EXISTS idx_flaky_step_scenario_id ON flaky_step(scenario_id);
CREATE INDEX IF NOT EXISTS idx_flaky_step_is_flaky ON flaky_step(is_flaky);
CREATE INDEX IF NOT EXISTS idx_flaky_step_severity ON flaky_step(severity);
CREATE INDEX IF NOT EXISTS idx_flaky_step_confidence ON flaky_step(confidence DESC);

-- Table: scenario_analysis
-- Stores aggregated scenario-level flakiness analysis
CREATE TABLE IF NOT EXISTS scenario_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Scenario identification
    scenario_id TEXT NOT NULL UNIQUE,
    scenario_name TEXT NOT NULL,
    framework TEXT NOT NULL,
    
    -- Scenario-level scores
    scenario_flaky_score REAL NOT NULL,
    is_scenario_flaky BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    severity TEXT,
    
    -- Step-level summary
    total_steps INTEGER NOT NULL,
    flaky_steps_count INTEGER NOT NULL,
    suspected_steps_count INTEGER NOT NULL,
    stable_steps_count INTEGER NOT NULL,
    
    -- Root cause
    root_cause_step_id TEXT,
    root_cause_explanation TEXT,
    
    -- Metadata
    analyzed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW(),
    
    -- Indexing
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for scenario analysis
CREATE INDEX IF NOT EXISTS idx_scenario_analysis_is_flaky ON scenario_analysis(is_scenario_flaky);
CREATE INDEX IF NOT EXISTS idx_scenario_analysis_severity ON scenario_analysis(severity);

-- View: flaky_scenarios_with_steps
-- Join scenarios with their flaky steps
CREATE OR REPLACE VIEW flaky_scenarios_with_steps AS
SELECT
    sa.scenario_id,
    sa.scenario_name,
    sa.framework,
    sa.scenario_flaky_score,
    sa.severity,
    sa.confidence,
    sa.total_steps,
    sa.flaky_steps_count,
    sa.root_cause_explanation,
    array_agg(fs.step_text ORDER BY fs.step_failure_rate DESC) FILTER (WHERE fs.is_flaky) as flaky_step_texts,
    array_agg(fs.severity ORDER BY fs.step_failure_rate DESC) FILTER (WHERE fs.is_flaky) as step_severities
FROM scenario_analysis sa
LEFT JOIN flaky_step fs ON fs.scenario_id = sa.scenario_id AND fs.is_flaky = true
WHERE sa.is_scenario_flaky = true
GROUP BY sa.scenario_id, sa.scenario_name, sa.framework, sa.scenario_flaky_score, 
         sa.severity, sa.confidence, sa.total_steps, sa.flaky_steps_count, sa.root_cause_explanation
ORDER BY 
    CASE sa.severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END,
    sa.scenario_flaky_score DESC;

-- Trigger: Update timestamp on flaky_step changes
CREATE TRIGGER trigger_update_flaky_step_timestamp
    BEFORE UPDATE ON flaky_step
    FOR EACH ROW
    EXECUTE FUNCTION update_flaky_test_timestamp();

-- Trigger: Update timestamp on scenario_analysis changes
CREATE TRIGGER trigger_update_scenario_analysis_timestamp
    BEFORE UPDATE ON scenario_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_flaky_test_timestamp();

-- Comments for Phase-2 tables
COMMENT ON TABLE step_execution IS 'Step/keyword execution records for BDD frameworks';
COMMENT ON TABLE flaky_step IS 'Step-level flaky detection results';
COMMENT ON TABLE scenario_analysis IS 'Aggregated scenario-level flakiness analysis';

COMMENT ON VIEW flaky_test_summary IS 'Summary of flaky tests with latest execution info';
COMMENT ON VIEW test_execution_stats IS 'Aggregated execution statistics per test';
