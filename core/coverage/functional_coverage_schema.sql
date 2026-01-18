-- Functional Coverage & Impact Analysis Schema
-- Extends CrossBridge with Test-to-Feature Coverage, Change Impact Surface, and External TC Integration
-- Design principles: Append-only, BI-ready, Grafana-ready, AI-friendly

-- ========================================
-- 1️⃣ FEATURE REGISTRY
-- ========================================

-- Features represent functional units of the product
CREATE TABLE IF NOT EXISTS feature (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,              -- api | service | bdd | module | component
    source TEXT NOT NULL,            -- cucumber | jira | code | manual | api_spec
    description TEXT,
    parent_feature_id UUID REFERENCES feature(id) ON DELETE CASCADE,  -- Hierarchical features
    metadata JSONB,                  -- Extensible for custom fields
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE (name, type, source)
);

CREATE INDEX idx_feature_name ON feature(name);
CREATE INDEX idx_feature_type ON feature(type);
CREATE INDEX idx_feature_source ON feature(source);
CREATE INDEX idx_feature_parent ON feature(parent_feature_id);

COMMENT ON TABLE feature IS 'Product features - functional units of the system';
COMMENT ON COLUMN feature.type IS 'Feature type: api, service, bdd, module, component';
COMMENT ON COLUMN feature.source IS 'Where feature was discovered: cucumber, jira, code, manual';

-- ========================================
-- 2️⃣ CODE UNITS (for detailed coverage)
-- ========================================

-- Code units represent individual code elements that can be covered
CREATE TABLE IF NOT EXISTS code_unit (
    id UUID PRIMARY KEY,
    file_path TEXT NOT NULL,
    class_name TEXT,
    method_name TEXT,
    package_name TEXT,
    module_name TEXT,               -- For Python/Robot
    line_start INTEGER,
    line_end INTEGER,
    complexity INTEGER,             -- Cyclomatic complexity if available
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE (file_path, class_name, method_name)
);

CREATE INDEX idx_code_unit_file_path ON code_unit(file_path);
CREATE INDEX idx_code_unit_class ON code_unit(class_name);
CREATE INDEX idx_code_unit_package ON code_unit(package_name);

COMMENT ON TABLE code_unit IS 'Individual code units (classes, methods, functions) that can be covered by tests';

-- ========================================
-- 3️⃣ EXTERNAL TEST CASE REFERENCES
-- ========================================

-- External test case systems (TestRail, Zephyr, qTest, etc.)
CREATE TABLE IF NOT EXISTS external_test_case (
    id UUID PRIMARY KEY,
    system TEXT NOT NULL,            -- testrail | zephyr | qtest | jira
    external_id TEXT NOT NULL,       -- e.g. C12345, T-1234
    title TEXT,
    description TEXT,
    priority TEXT,                   -- high | medium | low
    status TEXT,                     -- active | inactive | deprecated
    metadata JSONB,                  -- Extensible for system-specific fields
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE (system, external_id)
);

CREATE INDEX idx_external_tc_system ON external_test_case(system);
CREATE INDEX idx_external_tc_external_id ON external_test_case(external_id);
CREATE INDEX idx_external_tc_system_id ON external_test_case(system, external_id);

COMMENT ON TABLE external_test_case IS 'External test case references (TestRail, Zephyr, etc.)';
COMMENT ON COLUMN external_test_case.system IS 'Test management system: testrail, zephyr, qtest, jira';

-- ========================================
-- 4️⃣ TEST-TO-EXTERNAL MAPPING
-- ========================================

-- Maps discovered tests to external test case IDs
CREATE TABLE IF NOT EXISTS test_case_external_map (
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    external_test_case_id UUID REFERENCES external_test_case(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,    -- 0.0 to 1.0
    source TEXT NOT NULL,            -- annotation | tag | file | api | manual
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (test_case_id, external_test_case_id)
);

CREATE INDEX idx_tc_external_test ON test_case_external_map(test_case_id);
CREATE INDEX idx_tc_external_external ON test_case_external_map(external_test_case_id);
CREATE INDEX idx_tc_external_source ON test_case_external_map(source);

COMMENT ON TABLE test_case_external_map IS 'Maps CrossBridge tests to external test case IDs';
COMMENT ON COLUMN test_case_external_map.source IS 'How mapping was discovered: annotation, tag, file, api, manual';

-- ========================================
-- 5️⃣ TEST-TO-FEATURE MAPPING
-- ========================================

-- Maps tests to features (Test-to-Feature Coverage)
CREATE TABLE IF NOT EXISTS test_feature_map (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    feature_id UUID REFERENCES feature(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,    -- 0.0 to 1.0
    source TEXT NOT NULL,            -- coverage | tag | annotation | ai | manual
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (test_case_id, feature_id, source)
);

CREATE INDEX idx_test_feature_test ON test_feature_map(test_case_id);
CREATE INDEX idx_test_feature_feature ON test_feature_map(feature_id);
CREATE INDEX idx_test_feature_source ON test_feature_map(source);

COMMENT ON TABLE test_feature_map IS 'Maps tests to features - Test-to-Feature Coverage';

-- ========================================
-- 6️⃣ TEST-TO-CODE COVERAGE (enhanced)
-- ========================================

-- Enhanced test-to-code coverage mapping
CREATE TABLE IF NOT EXISTS test_code_coverage_map (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    code_unit_id UUID REFERENCES code_unit(id) ON DELETE CASCADE,
    coverage_type TEXT NOT NULL,     -- instruction | line | branch | method
    covered_count INTEGER DEFAULT 0,
    missed_count INTEGER DEFAULT 0,
    coverage_percentage FLOAT DEFAULT 0.0,
    confidence FLOAT DEFAULT 1.0,    -- 0.0 to 1.0
    execution_mode TEXT,             -- isolated | small_batch | full_suite
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (test_case_id, code_unit_id, coverage_type)
);

CREATE INDEX idx_test_code_test ON test_code_coverage_map(test_case_id);
CREATE INDEX idx_test_code_code_unit ON test_code_coverage_map(code_unit_id);
CREATE INDEX idx_test_code_type ON test_code_coverage_map(coverage_type);

COMMENT ON TABLE test_code_coverage_map IS 'Maps tests to code units via coverage - enables Change Impact Surface';

-- ========================================
-- 7️⃣ GIT CHANGE EVENTS (Code changes for impact analysis)
-- ========================================

-- Tracks code changes for impact analysis  
-- Note: Renamed from change_event to avoid conflict with existing table
CREATE TABLE IF NOT EXISTS git_change_event (
    id UUID PRIMARY KEY,
    commit_sha TEXT NOT NULL,
    commit_message TEXT,
    author TEXT,
    file_path TEXT NOT NULL,
    change_type TEXT,                -- added | modified | deleted | renamed
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    branch TEXT,
    timestamp TIMESTAMP NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_git_change_event_commit ON git_change_event(commit_sha);
CREATE INDEX idx_git_change_event_file ON git_change_event(file_path);
CREATE INDEX idx_git_change_event_timestamp ON git_change_event(timestamp);
CREATE INDEX idx_git_change_event_branch ON git_change_event(branch);

COMMENT ON TABLE git_change_event IS 'Git code change events for impact analysis';

-- ========================================
-- 8️⃣ CHANGE IMPACT (cached analysis)
-- ========================================

-- Pre-computed change impact for performance
CREATE TABLE IF NOT EXISTS git_change_impact (
    id UUID PRIMARY KEY,
    git_change_event_id UUID REFERENCES git_change_event(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    feature_id UUID REFERENCES feature(id) ON DELETE SET NULL,
    impact_score FLOAT DEFAULT 1.0,  -- 0.0 to 1.0
    impact_reason TEXT,              -- direct_coverage | feature_link | transitive
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (git_change_event_id, test_case_id)
);

CREATE INDEX idx_git_change_impact_event ON git_change_impact(git_change_event_id);
CREATE INDEX idx_git_change_impact_test ON git_change_impact(test_case_id);
CREATE INDEX idx_git_change_impact_feature ON git_change_impact(feature_id);

COMMENT ON TABLE git_change_impact IS 'Pre-computed git change impact for fast lookups';

-- ========================================
-- 9️⃣ VIEWS FOR CONSOLE OUTPUT & GRAFANA
-- ========================================

-- View: Functional Coverage Map
-- Shows which code units are covered by how many tests
CREATE OR REPLACE VIEW functional_coverage_map AS
SELECT 
    cu.file_path,
    cu.class_name,
    cu.method_name,
    COUNT(DISTINCT tccm.test_case_id) AS test_count,
    STRING_AGG(DISTINCT etc.external_id, ', ' ORDER BY etc.external_id) AS testrail_tcs,
    COUNT(DISTINCT etc.id) AS external_tc_count,
    AVG(tccm.coverage_percentage) AS avg_coverage_percentage,
    MAX(tccm.created_at) AS last_coverage_update
FROM code_unit cu
LEFT JOIN test_code_coverage_map tccm ON cu.id = tccm.code_unit_id
LEFT JOIN test_case_external_map tcem ON tccm.test_case_id = tcem.test_case_id
LEFT JOIN external_test_case etc ON tcem.external_test_case_id = etc.id AND etc.system = 'testrail'
GROUP BY cu.file_path, cu.class_name, cu.method_name
ORDER BY test_count DESC;

COMMENT ON VIEW functional_coverage_map IS 'Functional Coverage Map - shows code units with test coverage and TestRail TCs';

-- View: Test-to-Feature Coverage
-- Shows which tests validate which features
CREATE OR REPLACE VIEW test_to_feature_coverage AS
SELECT 
    f.name AS feature,
    f.type AS feature_type,
    tc.framework,
    tc.class_name || '.' || tc.method_name AS test_name,
    tc.id AS test_case_id,
    etc.external_id AS testrail_tc,
    tfm.confidence,
    tfm.source AS mapping_source
FROM test_feature_map tfm
JOIN feature f ON tfm.feature_id = f.id
JOIN test_case tc ON tfm.test_case_id = tc.id
LEFT JOIN test_case_external_map tcem ON tc.id = tcem.test_case_id
LEFT JOIN external_test_case etc ON tcem.external_test_case_id = etc.id AND etc.system = 'testrail'
ORDER BY f.name, tc.class_name, tc.method_name;

COMMENT ON VIEW test_to_feature_coverage IS 'Test-to-Feature Coverage - shows which tests validate which features';

-- View: Change Impact Surface (for specific file)
-- This is parameterized - use WHERE clause in queries
CREATE OR REPLACE VIEW change_impact_surface AS
SELECT 
    cu.file_path AS changed_file,
    tc.class_name || '.' || tc.method_name AS impacted_test,
    f.name AS feature,
    etc.external_id AS testrail_tc,
    tccm.coverage_percentage,
    tccm.coverage_type
FROM test_code_coverage_map tccm
JOIN test_case tc ON tccm.test_case_id = tc.id
JOIN code_unit cu ON tccm.code_unit_id = cu.id
LEFT JOIN test_feature_map tfm ON tc.id = tfm.test_case_id
LEFT JOIN feature f ON tfm.feature_id = f.id
LEFT JOIN test_case_external_map tcem ON tc.id = tcem.test_case_id
LEFT JOIN external_test_case etc ON tcem.external_test_case_id = etc.id AND etc.system = 'testrail'
ORDER BY cu.file_path, tccm.coverage_percentage DESC;

COMMENT ON VIEW change_impact_surface IS 'Change Impact Surface - shows tests/features impacted by code changes';

-- View: Coverage Gaps (features without tests)
CREATE OR REPLACE VIEW coverage_gaps AS
SELECT 
    f.name AS feature,
    f.type AS feature_type,
    f.source AS feature_source,
    COUNT(tfm.id) AS test_count
FROM feature f
LEFT JOIN test_feature_map tfm ON f.id = tfm.feature_id
GROUP BY f.id, f.name, f.type, f.source
HAVING COUNT(tfm.id) = 0
ORDER BY f.type, f.name;

COMMENT ON VIEW coverage_gaps IS 'Features with no test coverage';

-- View: Test Case Summary with External References
CREATE OR REPLACE VIEW test_case_summary AS
SELECT 
    tc.id,
    tc.framework,
    tc.class_name,
    tc.method_name,
    tc.file_path,
    tc.tags,
    STRING_AGG(DISTINCT etc.system || ':' || etc.external_id, ', ') AS external_ids,
    COUNT(DISTINCT tccm.code_unit_id) AS code_units_covered,
    COUNT(DISTINCT tfm.feature_id) AS features_covered
FROM test_case tc
LEFT JOIN test_case_external_map tcem ON tc.id = tcem.test_case_id
LEFT JOIN external_test_case etc ON tcem.external_test_case_id = etc.id
LEFT JOIN test_code_coverage_map tccm ON tc.id = tccm.test_case_id
LEFT JOIN test_feature_map tfm ON tc.id = tfm.test_case_id
GROUP BY tc.id, tc.framework, tc.class_name, tc.method_name, tc.file_path, tc.tags;

COMMENT ON VIEW test_case_summary IS 'Comprehensive test case summary with external references and coverage stats';

-- ========================================
-- 🔟 HELPER FUNCTIONS
-- ========================================

-- Function: Get impacted tests for a file
CREATE OR REPLACE FUNCTION get_impacted_tests(file_path_param TEXT)
RETURNS TABLE (
    test_name TEXT,
    feature_name TEXT,
    testrail_tc TEXT,
    coverage_percentage FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tc.class_name || '.' || tc.method_name AS test_name,
        f.name AS feature_name,
        etc.external_id AS testrail_tc,
        tccm.coverage_percentage
    FROM test_code_coverage_map tccm
    JOIN test_case tc ON tccm.test_case_id = tc.id
    JOIN code_unit cu ON tccm.code_unit_id = cu.id
    LEFT JOIN test_feature_map tfm ON tc.id = tfm.test_case_id
    LEFT JOIN feature f ON tfm.feature_id = f.id
    LEFT JOIN test_case_external_map tcem ON tc.id = tcem.test_case_id
    LEFT JOIN external_test_case etc ON tcem.external_test_case_id = etc.id AND etc.system = 'testrail'
    WHERE cu.file_path = file_path_param
    ORDER BY tccm.coverage_percentage DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_impacted_tests IS 'Get tests impacted by changes to a specific file';

-- ========================================
-- 🔟 BEHAVIORAL COVERAGE TABLES (SaaS-Friendly)
-- ========================================

-- API Endpoint Coverage (behavioral, not instrumented)
CREATE TABLE IF NOT EXISTS api_endpoint_coverage (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    endpoint_path TEXT NOT NULL,            -- e.g., /api/v1/users/{id}
    http_method TEXT NOT NULL,              -- GET, POST, PUT, DELETE, etc.
    status_code INTEGER,                    -- HTTP response code
    request_schema JSONB,                   -- Request payload schema
    response_schema JSONB,                  -- Response payload schema
    feature_flags TEXT[],                   -- Feature flags active during call
    execution_time_ms FLOAT,                -- Request duration
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_api_endpoint_test ON api_endpoint_coverage(test_case_id);
CREATE INDEX idx_api_endpoint_path ON api_endpoint_coverage(endpoint_path);
CREATE INDEX idx_api_endpoint_method ON api_endpoint_coverage(http_method);
CREATE INDEX idx_api_endpoint_method_path ON api_endpoint_coverage(http_method, endpoint_path);

COMMENT ON TABLE api_endpoint_coverage IS 'API endpoint coverage from network traffic - for SaaS/black-box testing';
COMMENT ON COLUMN api_endpoint_coverage.endpoint_path IS 'Normalized API path with {id} placeholders';

-- UI Component Coverage (behavioral)
CREATE TABLE IF NOT EXISTS ui_component_coverage (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    component_name TEXT NOT NULL,           -- Component/element name
    component_type TEXT NOT NULL,           -- button, input, dropdown, etc.
    selector TEXT,                          -- CSS selector or XPath
    page_url TEXT,                          -- Page where component appears
    interaction_type TEXT DEFAULT 'click',  -- click, type, hover, etc.
    interaction_count INTEGER DEFAULT 1,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_ui_component_test ON ui_component_coverage(test_case_id);
CREATE INDEX idx_ui_component_name ON ui_component_coverage(component_name);
CREATE INDEX idx_ui_component_page ON ui_component_coverage(page_url);

COMMENT ON TABLE ui_component_coverage IS 'UI component interaction coverage - tracks which UI elements are exercised';

-- Network Capture (raw network traffic)
CREATE TABLE IF NOT EXISTS network_capture (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    request_url TEXT NOT NULL,
    request_method TEXT NOT NULL,
    request_headers JSONB,
    request_body TEXT,
    response_status INTEGER,
    response_headers JSONB,
    response_body TEXT,
    duration_ms FLOAT,
    timestamp TIMESTAMP DEFAULT now(),
    metadata JSONB
);

CREATE INDEX idx_network_capture_test ON network_capture(test_case_id);
CREATE INDEX idx_network_capture_url ON network_capture(request_url);
CREATE INDEX idx_network_capture_timestamp ON network_capture(timestamp);

COMMENT ON TABLE network_capture IS 'Raw network traffic capture during test execution';

-- Contract/Schema Coverage
CREATE TABLE IF NOT EXISTS contract_coverage (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    contract_name TEXT NOT NULL,            -- e.g., UserAPI.getUser
    contract_version TEXT NOT NULL,         -- API version
    request_fields_covered TEXT[],          -- Request fields used
    response_fields_covered TEXT[],         -- Response fields received
    validation_passed BOOLEAN DEFAULT true,
    validation_errors TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_contract_coverage_test ON contract_coverage(test_case_id);
CREATE INDEX idx_contract_coverage_name ON contract_coverage(contract_name);

COMMENT ON TABLE contract_coverage IS 'API contract/schema coverage - tracks which request/response fields are exercised';

-- ========================================
-- 🔟 BEHAVIORAL COVERAGE VIEWS
-- ========================================

-- API Endpoint Coverage Summary
CREATE OR REPLACE VIEW api_endpoint_summary AS
SELECT 
    aec.endpoint_path,
    aec.http_method,
    COUNT(DISTINCT aec.test_case_id) AS test_count,
    ARRAY_AGG(DISTINCT aec.status_code ORDER BY aec.status_code) AS status_codes,
    AVG(aec.execution_time_ms) AS avg_execution_time_ms,
    COUNT(*) AS total_calls
FROM api_endpoint_coverage aec
GROUP BY aec.endpoint_path, aec.http_method
ORDER BY test_count DESC;

COMMENT ON VIEW api_endpoint_summary IS 'Summary of API endpoint coverage - which endpoints are tested';

-- UI Component Coverage Summary
CREATE OR REPLACE VIEW ui_component_summary AS
SELECT 
    ucc.component_name,
    ucc.component_type,
    ucc.page_url,
    COUNT(DISTINCT ucc.test_case_id) AS test_count,
    SUM(ucc.interaction_count) AS total_interactions,
    ARRAY_AGG(DISTINCT ucc.interaction_type) AS interaction_types
FROM ui_component_coverage ucc
GROUP BY ucc.component_name, ucc.component_type, ucc.page_url
ORDER BY test_count DESC;

COMMENT ON VIEW ui_component_summary IS 'Summary of UI component coverage - which UI elements are tested';

-- Functional Surface Coverage (Behavioral + Instrumented)
CREATE OR REPLACE VIEW functional_surface_coverage AS
SELECT 
    'API Endpoint' AS coverage_type,
    aec.endpoint_path AS surface_element,
    aec.http_method AS detail,
    COUNT(DISTINCT aec.test_case_id) AS test_count,
    'network' AS source
FROM api_endpoint_coverage aec
GROUP BY aec.endpoint_path, aec.http_method

UNION ALL

SELECT 
    'UI Component' AS coverage_type,
    ucc.component_name AS surface_element,
    ucc.component_type AS detail,
    COUNT(DISTINCT ucc.test_case_id) AS test_count,
    'ui_interaction' AS source
FROM ui_component_coverage ucc
GROUP BY ucc.component_name, ucc.component_type

UNION ALL

SELECT 
    'Code Unit' AS coverage_type,
    cu.file_path AS surface_element,
    cu.class_name || '.' || cu.method_name AS detail,
    COUNT(DISTINCT tccm.test_case_id) AS test_count,
    'coverage' AS source
FROM test_code_coverage_map tccm
JOIN code_unit cu ON tccm.code_unit_id = cu.id
GROUP BY cu.file_path, cu.class_name, cu.method_name

ORDER BY test_count DESC;

COMMENT ON VIEW functional_surface_coverage IS 'Unified view of all coverage types - behavioral + instrumented';
