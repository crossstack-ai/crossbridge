-- Coverage Mapping Database Schema
-- Stores test-to-code coverage mappings for precise impact analysis

-- Test coverage mapping (append-only, never UPDATE)
CREATE TABLE IF NOT EXISTS test_code_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id TEXT NOT NULL,
    test_name TEXT,
    test_framework TEXT,  -- 'cucumber', 'junit', 'pytest', 'robot'
    
    -- Covered code
    class_name TEXT NOT NULL,
    method_name TEXT,  -- NULL for class-level coverage
    package_name TEXT,
    
    -- Coverage metrics
    coverage_type TEXT NOT NULL,  -- 'instruction', 'line', 'branch', 'method'
    covered_count INTEGER DEFAULT 0,
    missed_count INTEGER DEFAULT 0,
    coverage_percentage REAL DEFAULT 0.0,
    
    -- Line numbers (JSON array)
    line_numbers TEXT,  -- JSON: [10, 11, 12, 15, 16]
    
    -- Confidence and metadata
    confidence REAL DEFAULT 0.5,
    execution_mode TEXT,  -- 'isolated', 'small_batch', 'full_suite'
    coverage_source TEXT,  -- 'jacoco', 'coverage.py', 'istanbul'
    
    -- Discovery metadata
    discovery_run_id TEXT,
    discovery_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jacoco_report_path TEXT,
    
    -- Source file info
    source_file_path TEXT,
    repository_url TEXT,
    commit_hash TEXT,
    
    -- Indexes for fast impact queries
    CONSTRAINT unique_test_coverage UNIQUE (
        test_id, 
        class_name, 
        method_name, 
        coverage_type, 
        discovery_run_id
    )
);

-- Index for impact queries: "What tests cover this class?"
CREATE INDEX IF NOT EXISTS idx_coverage_class 
ON test_code_coverage(class_name, confidence DESC);

-- Index for impact queries: "What tests cover this method?"
CREATE INDEX IF NOT EXISTS idx_coverage_method 
ON test_code_coverage(class_name, method_name, confidence DESC);

-- Index for test queries: "What code does this test cover?"
CREATE INDEX IF NOT EXISTS idx_coverage_test 
ON test_code_coverage(test_id, confidence DESC);

-- Index for discovery queries: "What coverage was collected in run X?"
CREATE INDEX IF NOT EXISTS idx_coverage_discovery 
ON test_code_coverage(discovery_run_id, discovery_timestamp DESC);

-- Scenario coverage mapping (BDD-specific)
CREATE TABLE IF NOT EXISTS scenario_code_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    feature_name TEXT,
    feature_file TEXT,
    
    -- Aggregated coverage
    class_name TEXT NOT NULL,
    method_name TEXT,
    
    -- Coverage metrics (aggregated from steps)
    coverage_type TEXT NOT NULL,
    covered_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    coverage_percentage REAL DEFAULT 0.0,
    
    -- Confidence (min of step confidences)
    confidence REAL DEFAULT 0.5,
    execution_mode TEXT,
    coverage_source TEXT,
    
    -- Step count
    step_count INTEGER DEFAULT 0,
    
    -- Discovery metadata
    discovery_run_id TEXT,
    discovery_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_scenario_coverage UNIQUE (
        scenario_id,
        class_name,
        method_name,
        coverage_type,
        discovery_run_id
    )
);

-- Index for impact queries: "What scenarios cover this class?"
CREATE INDEX IF NOT EXISTS idx_scenario_coverage_class 
ON scenario_code_coverage(class_name, confidence DESC);

-- Index for scenario queries: "What code does this scenario cover?"
CREATE INDEX IF NOT EXISTS idx_scenario_coverage_scenario 
ON scenario_code_coverage(scenario_id);

-- Step coverage mapping (for step-level granularity)
CREATE TABLE IF NOT EXISTS step_code_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id TEXT NOT NULL,
    step_keyword TEXT,  -- 'Given', 'When', 'Then', 'And', 'But'
    step_name TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    
    -- Covered code
    class_name TEXT NOT NULL,
    method_name TEXT NOT NULL,  -- Steps always map to methods
    
    -- Coverage metrics
    coverage_type TEXT NOT NULL,
    covered_count INTEGER DEFAULT 0,
    
    -- Confidence
    confidence REAL DEFAULT 0.5,
    execution_mode TEXT,
    
    -- Discovery metadata
    discovery_run_id TEXT,
    discovery_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_step_coverage UNIQUE (
        step_id,
        class_name,
        method_name,
        coverage_type,
        discovery_run_id
    )
);

-- Index for step queries: "What code does this step cover?"
CREATE INDEX IF NOT EXISTS idx_step_coverage_step 
ON step_code_coverage(step_id);

-- Index for method queries: "What steps call this method?"
CREATE INDEX IF NOT EXISTS idx_step_coverage_method 
ON step_code_coverage(class_name, method_name);

-- Coverage discovery runs (metadata about coverage collection)
CREATE TABLE IF NOT EXISTS coverage_discovery_run (
    id TEXT PRIMARY KEY,  -- UUID
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_type TEXT NOT NULL,  -- 'isolated', 'batch', 'full_suite'
    
    -- Test execution info
    test_framework TEXT,
    test_count INTEGER DEFAULT 0,
    scenario_count INTEGER DEFAULT 0,
    
    -- Coverage tool info
    coverage_source TEXT,
    coverage_report_path TEXT,
    
    -- Build info
    build_id TEXT,
    repository_url TEXT,
    commit_hash TEXT,
    branch_name TEXT,
    
    -- Statistics
    classes_covered INTEGER DEFAULT 0,
    methods_covered INTEGER DEFAULT 0,
    average_confidence REAL DEFAULT 0.0,
    
    -- Duration
    duration_seconds REAL,
    
    -- Status
    status TEXT DEFAULT 'completed',  -- 'running', 'completed', 'failed'
    error_message TEXT
);

-- Impact analysis queries (views for common queries)

-- View: Test-to-class coverage (highest confidence first)
CREATE VIEW IF NOT EXISTS v_test_class_coverage AS
SELECT 
    test_id,
    test_name,
    test_framework,
    class_name,
    MAX(confidence) as max_confidence,
    MAX(discovery_timestamp) as latest_discovery,
    COUNT(DISTINCT coverage_type) as coverage_types_count
FROM test_code_coverage
GROUP BY test_id, class_name;

-- View: Class-to-test impact (for change impact analysis)
CREATE VIEW IF NOT EXISTS v_class_impact AS
SELECT 
    class_name,
    test_id,
    test_name,
    test_framework,
    MAX(confidence) as confidence,
    COUNT(DISTINCT method_name) as methods_covered,
    MAX(discovery_timestamp) as latest_discovery
FROM test_code_coverage
GROUP BY class_name, test_id
ORDER BY class_name, confidence DESC;

-- View: Scenario-to-class coverage
CREATE VIEW IF NOT EXISTS v_scenario_class_coverage AS
SELECT 
    scenario_id,
    scenario_name,
    feature_name,
    class_name,
    MAX(confidence) as max_confidence,
    SUM(step_count) as total_steps,
    MAX(discovery_timestamp) as latest_discovery
FROM scenario_code_coverage
GROUP BY scenario_id, class_name;

-- View: Coverage statistics by test framework
CREATE VIEW IF NOT EXISTS v_coverage_stats_by_framework AS
SELECT 
    test_framework,
    COUNT(DISTINCT test_id) as test_count,
    COUNT(DISTINCT class_name) as classes_covered,
    COUNT(DISTINCT class_name || '.' || method_name) as methods_covered,
    AVG(confidence) as avg_confidence,
    MAX(discovery_timestamp) as latest_discovery
FROM test_code_coverage
WHERE method_name IS NOT NULL
GROUP BY test_framework;

-- Stored queries for common impact analysis patterns

-- Example query: Find all tests that cover a changed class
-- SELECT DISTINCT test_id, test_name, confidence
-- FROM test_code_coverage
-- WHERE class_name IN ('com.example.LoginService', 'com.example.UserService')
-- ORDER BY confidence DESC, test_name;

-- Example query: Find what code a test covers
-- SELECT class_name, method_name, coverage_type, confidence
-- FROM test_code_coverage
-- WHERE test_id = 'LoginTest.testSuccessfulLogin'
-- ORDER BY class_name, method_name;

-- Example query: Find tests with highest coverage of a class
-- SELECT test_id, COUNT(DISTINCT method_name) as methods_covered, AVG(confidence) as avg_confidence
-- FROM test_code_coverage
-- WHERE class_name = 'com.example.LoginService'
-- GROUP BY test_id
-- ORDER BY methods_covered DESC, avg_confidence DESC
-- LIMIT 10;
