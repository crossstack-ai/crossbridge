"""
Execution Intelligence Database Schema

Comprehensive schema for storing execution events, signals, classifications,
and historical analysis data. Supports:
- Event tracking
- Signal extraction history
- Classification results
- Historical frequency analysis
- Performance metrics
- Infrastructure health signals

Compatible with PostgreSQL 12+ (primary) and SQLite (development).
"""

# ============================================================================
# CORE TABLES
# ============================================================================

CREATE_EXECUTION_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.execution_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- Core identification
    run_id VARCHAR(100),
    event_id VARCHAR(100) UNIQUE NOT NULL,
    framework VARCHAR(50) NOT NULL,
    test_name VARCHAR(500),
    test_file VARCHAR(1000),
    
    -- Event classification
    event_type VARCHAR(50),  -- TEST_START, TEST_END, STEP, ASSERTION, etc.
    log_level VARCHAR(20) NOT NULL,  -- DEBUG, INFO, WARN, ERROR, FATAL
    log_source_type VARCHAR(50),  -- AUTOMATION, APPLICATION
    
    -- Timing
    timestamp TIMESTAMP NOT NULL,
    duration_ms INTEGER,
    
    -- Content
    source VARCHAR(200) NOT NULL,  -- pytest, selenium, robot, etc.
    message TEXT NOT NULL,
    exception_type VARCHAR(200),
    stacktrace TEXT,
    service_name VARCHAR(200),  -- For application logs
    
    -- Metadata
    metadata JSONB,
    
    -- Context
    environment VARCHAR(100),
    application_version VARCHAR(100),
    branch VARCHAR(200),
    commit_sha VARCHAR(100),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for fast queries
    CONSTRAINT execution_events_run_id_idx CHECK (run_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_events_run_id ON execution_intelligence.execution_events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_framework ON execution_intelligence.execution_events(framework);
CREATE INDEX IF NOT EXISTS idx_events_test_name ON execution_intelligence.execution_events(test_name);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON execution_intelligence.execution_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON execution_intelligence.execution_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_log_level ON execution_intelligence.execution_events(log_level);
CREATE INDEX IF NOT EXISTS idx_events_log_source ON execution_intelligence.execution_events(log_source_type);
"""

CREATE_FAILURE_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.failure_signals (
    id BIGSERIAL PRIMARY KEY,
    
    -- Core identification
    signal_id VARCHAR(100) UNIQUE NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    test_name VARCHAR(500) NOT NULL,
    framework VARCHAR(50) NOT NULL,
    
    -- Signal details
    signal_type VARCHAR(50) NOT NULL,  -- TIMEOUT, ASSERTION, LOCATOR, etc.
    message TEXT NOT NULL,
    confidence NUMERIC(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    
    -- Semantic flags
    is_retryable BOOLEAN DEFAULT FALSE,
    is_infra_related BOOLEAN DEFAULT FALSE,
    
    -- Code context
    stacktrace TEXT,
    file_path VARCHAR(1000),
    line_number INTEGER,
    
    -- Evidence
    keywords TEXT[],  -- Array of matched keywords
    patterns_matched TEXT[],  -- Array of matched patterns
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    CONSTRAINT fk_run_id FOREIGN KEY (run_id) 
        REFERENCES execution_intelligence.execution_events(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_signals_run_id ON execution_intelligence.failure_signals(run_id);
CREATE INDEX IF NOT EXISTS idx_signals_test_name ON execution_intelligence.failure_signals(test_name);
CREATE INDEX IF NOT EXISTS idx_signals_signal_type ON execution_intelligence.failure_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_signals_confidence ON execution_intelligence.failure_signals(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_signals_retryable ON execution_intelligence.failure_signals(is_retryable);
CREATE INDEX IF NOT EXISTS idx_signals_infra ON execution_intelligence.failure_signals(is_infra_related);
"""

CREATE_CLASSIFICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.classifications (
    id BIGSERIAL PRIMARY KEY,
    
    -- Core identification
    classification_id VARCHAR(100) UNIQUE NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    test_name VARCHAR(500) NOT NULL,
    framework VARCHAR(50) NOT NULL,
    
    -- Classification result
    failure_type VARCHAR(50) NOT NULL,  -- PRODUCT_DEFECT, AUTOMATION_DEFECT, etc.
    confidence NUMERIC(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    reason TEXT NOT NULL,
    
    -- Evidence and rules
    evidence TEXT[],  -- Array of evidence strings
    rules_applied TEXT[],  -- Array of rule IDs
    signals_used INTEGER[],  -- Array of signal IDs
    
    -- Code reference
    code_file VARCHAR(1000),
    code_line INTEGER,
    code_snippet TEXT,
    code_function VARCHAR(200),
    code_class VARCHAR(200),
    
    -- AI enhancement (optional)
    ai_enhanced BOOLEAN DEFAULT FALSE,
    ai_confidence_adjustment NUMERIC(3,2),
    ai_insights TEXT,
    ai_model VARCHAR(100),
    
    -- Decision support
    should_fail_ci BOOLEAN,
    recommended_action VARCHAR(50),  -- RETRY, INVESTIGATE, FIX_TEST, FIX_APP
    
    -- Timestamps
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_classifications_run_id ON execution_intelligence.classifications(run_id);
CREATE INDEX IF NOT EXISTS idx_classifications_test_name ON execution_intelligence.classifications(test_name);
CREATE INDEX IF NOT EXISTS idx_classifications_failure_type ON execution_intelligence.classifications(failure_type);
CREATE INDEX IF NOT EXISTS idx_classifications_confidence ON execution_intelligence.classifications(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_classifications_should_fail_ci ON execution_intelligence.classifications(should_fail_ci);
CREATE INDEX IF NOT EXISTS idx_classifications_timestamp ON execution_intelligence.classifications(classified_at DESC);
"""

# ============================================================================
# HISTORICAL ANALYSIS TABLES
# ============================================================================

CREATE_HISTORICAL_PATTERNS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.historical_patterns (
    id BIGSERIAL PRIMARY KEY,
    
    -- Pattern identification
    pattern_hash VARCHAR(64) UNIQUE NOT NULL,  -- Hash of normalized error message
    pattern_signature VARCHAR(500) NOT NULL,   -- Human-readable signature
    
    -- Classification
    failure_type VARCHAR(50) NOT NULL,
    signal_type VARCHAR(50) NOT NULL,
    framework VARCHAR(50) NOT NULL,
    
    -- Statistics
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    
    -- Affected tests
    test_names TEXT[],  -- Array of test names with this pattern
    avg_confidence NUMERIC(3,2),
    
    -- Resolution tracking
    resolved BOOLEAN DEFAULT FALSE,
    resolution_type VARCHAR(50),  -- FIXED, IGNORED, FLAKY
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patterns_hash ON execution_intelligence.historical_patterns(pattern_hash);
CREATE INDEX IF NOT EXISTS idx_patterns_failure_type ON execution_intelligence.historical_patterns(failure_type);
CREATE INDEX IF NOT EXISTS idx_patterns_occurrence ON execution_intelligence.historical_patterns(occurrence_count DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_last_seen ON execution_intelligence.historical_patterns(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_resolved ON execution_intelligence.historical_patterns(resolved);
"""

CREATE_PATTERN_OCCURRENCES_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.pattern_occurrences (
    id BIGSERIAL PRIMARY KEY,
    
    -- Pattern reference
    pattern_id INTEGER NOT NULL REFERENCES execution_intelligence.historical_patterns(id) ON DELETE CASCADE,
    
    -- Occurrence details
    run_id VARCHAR(100) NOT NULL,
    test_name VARCHAR(500) NOT NULL,
    classification_id VARCHAR(100),
    
    -- Timing
    occurred_at TIMESTAMP NOT NULL,
    
    -- Environment
    environment VARCHAR(100),
    application_version VARCHAR(100),
    branch VARCHAR(200),
    
    -- Result
    confidence NUMERIC(3,2),
    was_retried BOOLEAN DEFAULT FALSE,
    retry_succeeded BOOLEAN,
    
    -- Metadata
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_occurrences_pattern_id ON execution_intelligence.pattern_occurrences(pattern_id);
CREATE INDEX IF NOT EXISTS idx_occurrences_run_id ON execution_intelligence.pattern_occurrences(run_id);
CREATE INDEX IF NOT EXISTS idx_occurrences_test_name ON execution_intelligence.pattern_occurrences(test_name);
CREATE INDEX IF NOT EXISTS idx_occurrences_timestamp ON execution_intelligence.pattern_occurrences(occurred_at DESC);
"""

# ============================================================================
# PERFORMANCE & INFRASTRUCTURE TABLES
# ============================================================================

CREATE_PERFORMANCE_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.performance_signals (
    id BIGSERIAL PRIMARY KEY,
    
    -- Core identification
    signal_id VARCHAR(100) UNIQUE NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    test_name VARCHAR(500) NOT NULL,
    framework VARCHAR(50) NOT NULL,
    
    -- Performance metrics
    signal_type VARCHAR(50) NOT NULL,  -- SLOW_TEST, MEMORY_LEAK, HIGH_CPU, etc.
    severity VARCHAR(20) NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    
    -- Measurements
    duration_ms INTEGER,
    memory_mb NUMERIC(10,2),
    cpu_percent NUMERIC(5,2),
    
    -- Thresholds
    threshold_exceeded VARCHAR(100),
    threshold_value NUMERIC(10,2),
    actual_value NUMERIC(10,2),
    
    -- Context
    baseline_value NUMERIC(10,2),  -- Historical baseline
    deviation_percent NUMERIC(5,2),  -- % deviation from baseline
    
    -- Timestamps
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_perf_signals_run_id ON execution_intelligence.performance_signals(run_id);
CREATE INDEX IF NOT EXISTS idx_perf_signals_test_name ON execution_intelligence.performance_signals(test_name);
CREATE INDEX IF NOT EXISTS idx_perf_signals_type ON execution_intelligence.performance_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_perf_signals_severity ON execution_intelligence.performance_signals(severity);
"""

CREATE_INFRASTRUCTURE_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.infrastructure_signals (
    id BIGSERIAL PRIMARY KEY,
    
    -- Core identification
    signal_id VARCHAR(100) UNIQUE NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    
    -- Infrastructure component
    component_type VARCHAR(50) NOT NULL,  -- DATABASE, NETWORK, SERVICE, etc.
    component_name VARCHAR(200),
    
    -- Signal details
    signal_type VARCHAR(50) NOT NULL,  -- CONNECTION_ERROR, TIMEOUT, SERVICE_DOWN, etc.
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    
    -- Metrics
    response_time_ms INTEGER,
    error_rate NUMERIC(5,2),
    availability NUMERIC(5,2),
    
    -- Impact
    tests_affected INTEGER,
    test_names TEXT[],
    
    -- Detection
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    duration_minutes INTEGER,
    
    -- Environment
    environment VARCHAR(100),
    region VARCHAR(100),
    
    -- Metadata
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_infra_signals_run_id ON execution_intelligence.infrastructure_signals(run_id);
CREATE INDEX IF NOT EXISTS idx_infra_signals_component ON execution_intelligence.infrastructure_signals(component_type);
CREATE INDEX IF NOT EXISTS idx_infra_signals_severity ON execution_intelligence.infrastructure_signals(severity);
CREATE INDEX IF NOT EXISTS idx_infra_signals_timestamp ON execution_intelligence.infrastructure_signals(detected_at DESC);
"""

# ============================================================================
# ANALYTICS & REPORTING TABLES
# ============================================================================

CREATE_ANALYSIS_SUMMARY_TABLE = """
CREATE TABLE IF NOT EXISTS execution_intelligence.analysis_summary (
    id BIGSERIAL PRIMARY KEY,
    
    -- Run identification
    run_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- Run context
    framework VARCHAR(50) NOT NULL,
    environment VARCHAR(100),
    application_version VARCHAR(100),
    branch VARCHAR(200),
    commit_sha VARCHAR(100),
    
    -- Counts
    total_tests INTEGER NOT NULL,
    tests_passed INTEGER NOT NULL,
    tests_failed INTEGER NOT NULL,
    tests_skipped INTEGER NOT NULL,
    
    -- Failure breakdown
    product_defects INTEGER DEFAULT 0,
    automation_defects INTEGER DEFAULT 0,
    locator_issues INTEGER DEFAULT 0,
    environment_issues INTEGER DEFAULT 0,
    flaky_tests INTEGER DEFAULT 0,
    unknown_failures INTEGER DEFAULT 0,
    
    -- Signals
    total_signals INTEGER DEFAULT 0,
    total_classifications INTEGER DEFAULT 0,
    
    -- Confidence stats
    avg_confidence NUMERIC(3,2),
    high_confidence_count INTEGER DEFAULT 0,
    medium_confidence_count INTEGER DEFAULT 0,
    low_confidence_count INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- CI/CD decision
    should_fail_ci BOOLEAN,
    ci_decision_reason TEXT,
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_summary_run_id ON execution_intelligence.analysis_summary(run_id);
CREATE INDEX IF NOT EXISTS idx_summary_framework ON execution_intelligence.analysis_summary(framework);
CREATE INDEX IF NOT EXISTS idx_summary_timestamp ON execution_intelligence.analysis_summary(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_summary_should_fail_ci ON execution_intelligence.analysis_summary(should_fail_ci);
"""

# ============================================================================
# VIEWS FOR ANALYTICS
# ============================================================================

CREATE_FAILURE_TRENDS_VIEW = """
CREATE OR REPLACE VIEW execution_intelligence.failure_trends AS
SELECT 
    DATE_TRUNC('day', classified_at) as date,
    failure_type,
    framework,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    COUNT(CASE WHEN should_fail_ci THEN 1 END) as ci_failures
FROM execution_intelligence.classifications
WHERE classified_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', classified_at), failure_type, framework
ORDER BY date DESC, count DESC;
"""

CREATE_TOP_FAILING_TESTS_VIEW = """
CREATE OR REPLACE VIEW execution_intelligence.top_failing_tests AS
SELECT 
    test_name,
    framework,
    failure_type,
    COUNT(*) as failure_count,
    AVG(confidence) as avg_confidence,
    MAX(classified_at) as last_failure,
    ARRAY_AGG(DISTINCT reason) as failure_reasons
FROM execution_intelligence.classifications
WHERE classified_at >= NOW() - INTERVAL '7 days'
GROUP BY test_name, framework, failure_type
HAVING COUNT(*) >= 2
ORDER BY failure_count DESC
LIMIT 100;
"""

CREATE_PATTERN_FREQUENCY_VIEW = """
CREATE OR REPLACE VIEW execution_intelligence.pattern_frequency AS
SELECT 
    p.pattern_signature,
    p.failure_type,
    p.framework,
    p.occurrence_count,
    p.last_seen,
    COUNT(DISTINCT po.test_name) as affected_tests,
    p.resolved,
    p.resolution_type
FROM execution_intelligence.historical_patterns p
LEFT JOIN execution_intelligence.pattern_occurrences po ON p.id = po.pattern_id
WHERE p.last_seen >= NOW() - INTERVAL '30 days'
GROUP BY p.id, p.pattern_signature, p.failure_type, p.framework, 
         p.occurrence_count, p.last_seen, p.resolved, p.resolution_type
ORDER BY p.occurrence_count DESC;
"""

# ============================================================================
# MATERIALIZED VIEWS FOR PERFORMANCE
# ============================================================================

CREATE_DAILY_METRICS_MATERIALIZED_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS execution_intelligence.daily_metrics AS
SELECT 
    DATE_TRUNC('day', started_at) as date,
    framework,
    environment,
    SUM(total_tests) as total_tests,
    SUM(tests_failed) as total_failures,
    SUM(product_defects) as product_defects,
    SUM(automation_defects) as automation_defects,
    SUM(environment_issues) as environment_issues,
    SUM(flaky_tests) as flaky_tests,
    AVG(avg_confidence) as avg_confidence,
    COUNT(CASE WHEN should_fail_ci THEN 1 END) as ci_failures
FROM execution_intelligence.analysis_summary
WHERE started_at >= NOW() - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', started_at), framework, environment
ORDER BY date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_metrics_unique 
ON execution_intelligence.daily_metrics(date, framework, COALESCE(environment, 'unknown'));
"""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

CREATE_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS execution_intelligence;
"""

def get_all_ddl_statements():
    """Get all DDL statements in execution order"""
    return [
        CREATE_SCHEMA_SQL,
        CREATE_EXECUTION_EVENTS_TABLE,
        CREATE_FAILURE_SIGNALS_TABLE,
        CREATE_CLASSIFICATIONS_TABLE,
        CREATE_HISTORICAL_PATTERNS_TABLE,
        CREATE_PATTERN_OCCURRENCES_TABLE,
        CREATE_PERFORMANCE_SIGNALS_TABLE,
        CREATE_INFRASTRUCTURE_SIGNALS_TABLE,
        CREATE_ANALYSIS_SUMMARY_TABLE,
        CREATE_FAILURE_TRENDS_VIEW,
        CREATE_TOP_FAILING_TESTS_VIEW,
        CREATE_PATTERN_FREQUENCY_VIEW,
        CREATE_DAILY_METRICS_MATERIALIZED_VIEW,
    ]

def create_all_tables(connection):
    """
    Create all tables, indexes, and views.
    
    Args:
        connection: Database connection object (psycopg2 or sqlite3)
    """
    cursor = connection.cursor()
    
    for ddl in get_all_ddl_statements():
        cursor.execute(ddl)
    
    connection.commit()
    cursor.close()

def drop_all_tables(connection, cascade=True):
    """
    Drop all execution intelligence tables (DANGEROUS).
    
    Args:
        connection: Database connection object
        cascade: Drop with CASCADE option
    """
    cursor = connection.cursor()
    
    cascade_clause = " CASCADE" if cascade else ""
    
    cursor.execute(f"DROP SCHEMA IF EXISTS execution_intelligence{cascade_clause};")
    
    connection.commit()
    cursor.close()
