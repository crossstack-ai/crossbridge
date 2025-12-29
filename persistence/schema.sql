-- CrossBridge Discovery Metadata Schema
-- PostgreSQL database schema for test discovery persistence
-- Design principles: Append-only, BI-ready, AI-learning friendly

-- 1️⃣ Discovery Run (anchor table)
-- Tracks when and how discovery happened
CREATE TABLE IF NOT EXISTS discovery_run (
    id UUID PRIMARY KEY,
    project_name TEXT NOT NULL,
    git_commit TEXT,
    git_branch TEXT,
    triggered_by TEXT,           -- cli | ci | jira | manual
    created_at TIMESTAMP DEFAULT now(),
    metadata JSONB               -- Extensible for future fields
);

CREATE INDEX idx_discovery_run_created_at ON discovery_run(created_at);
CREATE INDEX idx_discovery_run_project ON discovery_run(project_name);
CREATE INDEX idx_discovery_run_branch ON discovery_run(git_branch);

-- 2️⃣ Test Case
-- Stores discovered test cases (framework-agnostic)
CREATE TABLE IF NOT EXISTS test_case (
    id UUID PRIMARY KEY,
    framework TEXT NOT NULL,              -- junit | testng | pytest | robot
    package TEXT,
    class_name TEXT,
    method_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    tags TEXT[],                          -- Array of tags/groups/categories
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE (framework, package, class_name, method_name)
);

CREATE INDEX idx_test_case_framework ON test_case(framework);
CREATE INDEX idx_test_case_file_path ON test_case(file_path);
CREATE INDEX idx_test_case_tags ON test_case USING GIN(tags);

-- 3️⃣ Page Object
-- Stores discovered page objects
CREATE TABLE IF NOT EXISTS page_object (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    framework TEXT,
    package TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE (name, file_path)
);

CREATE INDEX idx_page_object_name ON page_object(name);
CREATE INDEX idx_page_object_file_path ON page_object(file_path);

-- 4️⃣ Test ↔ Page Mapping (append-only, observational)
-- Records test-to-page relationships with provenance
CREATE TABLE IF NOT EXISTS test_page_mapping (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    page_object_id UUID REFERENCES page_object(id) ON DELETE CASCADE,
    source TEXT NOT NULL,                 -- static_ast | coverage | ai | manual
    confidence FLOAT DEFAULT 1.0,         -- 0.0 to 1.0
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT now(),
    metadata JSONB                        -- Extensible for AI reasoning, etc.
);

CREATE INDEX idx_test_page_mapping_test ON test_page_mapping(test_case_id);
CREATE INDEX idx_test_page_mapping_page ON test_page_mapping(page_object_id);
CREATE INDEX idx_test_page_mapping_run ON test_page_mapping(discovery_run_id);
CREATE INDEX idx_test_page_mapping_source ON test_page_mapping(source);

-- 5️⃣ Discovery ↔ Test Case (join table)
-- Tracks which tests were seen in which discovery run
CREATE TABLE IF NOT EXISTS discovery_test_case (
    discovery_run_id UUID REFERENCES discovery_run(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (discovery_run_id, test_case_id)
);

CREATE INDEX idx_discovery_test_case_run ON discovery_test_case(discovery_run_id);
CREATE INDEX idx_discovery_test_case_test ON discovery_test_case(test_case_id);

-- Views for common queries

-- View: Latest discovery per project
CREATE OR REPLACE VIEW latest_discovery_per_project AS
SELECT DISTINCT ON (project_name)
    id, project_name, git_commit, git_branch, triggered_by, created_at
FROM discovery_run
ORDER BY project_name, created_at DESC;

-- View: Test with page object count
CREATE OR REPLACE VIEW test_with_page_count AS
SELECT 
    tc.id,
    tc.framework,
    tc.class_name,
    tc.method_name,
    tc.file_path,
    COUNT(DISTINCT tpm.page_object_id) as page_object_count
FROM test_case tc
LEFT JOIN test_page_mapping tpm ON tc.id = tpm.test_case_id
GROUP BY tc.id, tc.framework, tc.class_name, tc.method_name, tc.file_path;

-- View: Page objects with usage count
CREATE OR REPLACE VIEW page_object_usage AS
SELECT 
    po.id,
    po.name,
    po.file_path,
    po.framework,
    COUNT(DISTINCT tpm.test_case_id) as test_count
FROM page_object po
LEFT JOIN test_page_mapping tpm ON po.id = tpm.page_object_id
GROUP BY po.id, po.name, po.file_path, po.framework;

-- View: Discovery history
CREATE OR REPLACE VIEW discovery_history AS
SELECT 
    dr.id as run_id,
    dr.project_name,
    dr.git_commit,
    dr.git_branch,
    dr.triggered_by,
    dr.created_at,
    COUNT(DISTINCT dtc.test_case_id) as test_count
FROM discovery_run dr
LEFT JOIN discovery_test_case dtc ON dr.id = dtc.discovery_run_id
GROUP BY dr.id, dr.project_name, dr.git_commit, dr.git_branch, dr.triggered_by, dr.created_at
ORDER BY dr.created_at DESC;

-- Comments for documentation
COMMENT ON TABLE discovery_run IS 'Tracks test discovery runs with git context';
COMMENT ON TABLE test_case IS 'Framework-agnostic test case storage';
COMMENT ON TABLE page_object IS 'Page Object pattern implementation storage';
COMMENT ON TABLE test_page_mapping IS 'Append-only test-to-page relationships with provenance';
COMMENT ON TABLE discovery_test_case IS 'Links tests to discovery runs for history tracking';
