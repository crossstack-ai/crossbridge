-- CrossBridge AI & Memory Extension Schema
-- Extends the base discovery schema with AI/ML capabilities
-- Design: Supports embeddings, semantic search, and AI confidence tracking

-- 1️⃣ Memory Records (for embeddings)
-- Stores vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS memory_record (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,                     -- Original text content
    embedding vector(1536),                    -- Vector embedding (dimension depends on model)
    memory_type TEXT NOT NULL,                 -- test_case | page_object | step_definition | locator
    entity_id UUID,                            -- Foreign key to related entity (test_case_id, page_object_id, etc.)
    framework TEXT,                            -- Source framework
    metadata JSONB DEFAULT '{}',               -- Extensible metadata
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_memory_record_type ON memory_record(memory_type);
CREATE INDEX idx_memory_record_entity ON memory_record(entity_id);
CREATE INDEX idx_memory_record_framework ON memory_record(framework);
-- Vector similarity index (requires pgvector extension)
CREATE INDEX idx_memory_record_embedding ON memory_record USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 2️⃣ AI Transformation History
-- Tracks AI-assisted transformations with confidence scores
CREATE TABLE IF NOT EXISTS ai_transformation (
    id UUID PRIMARY KEY,
    source_framework TEXT NOT NULL,            -- Original framework
    target_framework TEXT NOT NULL,            -- Target framework
    source_file TEXT NOT NULL,                 -- Original file path
    target_file TEXT,                          -- Generated file path
    transformation_type TEXT NOT NULL,         -- migration | enhancement | refactor
    ai_model TEXT,                             -- Model used (gpt-4, claude-3, etc.)
    confidence_score FLOAT,                    -- 0.0 to 1.0 confidence
    status TEXT DEFAULT 'pending',             -- pending | approved | rejected | manual_review
    reviewed_by TEXT,                          -- User who reviewed
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    metadata JSONB DEFAULT '{}'                -- AI reasoning, suggestions, etc.
);

CREATE INDEX idx_ai_transformation_source ON ai_transformation(source_framework);
CREATE INDEX idx_ai_transformation_target ON ai_transformation(target_framework);
CREATE INDEX idx_ai_transformation_status ON ai_transformation(status);
CREATE INDEX idx_ai_transformation_created ON ai_transformation(created_at);

-- 3️⃣ Flaky Test Detection
-- Stores flaky test patterns and execution history
CREATE TABLE IF NOT EXISTS flaky_test_history (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    execution_time TIMESTAMP NOT NULL,
    status TEXT NOT NULL,                      -- passed | failed | skipped | flaky
    failure_reason TEXT,
    execution_duration_ms INTEGER,
    environment JSONB DEFAULT '{}',            -- Browser, OS, CI details
    git_commit TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_flaky_test_history_test ON flaky_test_history(test_case_id);
CREATE INDEX idx_flaky_test_history_execution ON flaky_test_history(execution_time);
CREATE INDEX idx_flaky_test_history_status ON flaky_test_history(status);

-- 4️⃣ Duplicate Test Detection
-- Stores semantic similarity scores between tests
CREATE TABLE IF NOT EXISTS test_similarity (
    id UUID PRIMARY KEY,
    test_case_1_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    test_case_2_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    similarity_score FLOAT NOT NULL,           -- 0.0 to 1.0 cosine similarity
    detection_method TEXT NOT NULL,            -- embedding | ast | name_pattern
    suggested_action TEXT,                     -- merge | keep_both | review
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now(),
    CHECK (test_case_1_id < test_case_2_id)    -- Prevent duplicates
);

CREATE INDEX idx_test_similarity_test1 ON test_similarity(test_case_1_id);
CREATE INDEX idx_test_similarity_test2 ON test_similarity(test_case_2_id);
CREATE INDEX idx_test_similarity_score ON test_similarity(similarity_score);
CREATE INDEX idx_test_similarity_reviewed ON test_similarity(reviewed);

-- 5️⃣ AI Confidence Feedback
-- Tracks human feedback on AI suggestions for continuous learning
CREATE TABLE IF NOT EXISTS ai_confidence_feedback (
    id UUID PRIMARY KEY,
    transformation_id UUID REFERENCES ai_transformation(id) ON DELETE CASCADE,
    feedback_type TEXT NOT NULL,               -- accept | reject | modify
    original_confidence FLOAT,
    actual_quality FLOAT,                      -- 0.0 to 1.0 assessed quality
    reviewer_notes TEXT,
    reviewed_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_ai_confidence_feedback_transformation ON ai_confidence_feedback(transformation_id);
CREATE INDEX idx_ai_confidence_feedback_type ON ai_confidence_feedback(feedback_type);

-- 6️⃣ Test Execution Patterns
-- Stores execution patterns for smart test selection
CREATE TABLE IF NOT EXISTS test_execution_pattern (
    id UUID PRIMARY KEY,
    test_case_id UUID REFERENCES test_case(id) ON DELETE CASCADE,
    file_dependencies TEXT[],                  -- Files this test depends on
    avg_execution_time_ms INTEGER,
    failure_rate FLOAT,                        -- 0.0 to 1.0
    last_modified TIMESTAMP,
    execution_count INTEGER DEFAULT 0,
    last_executed TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_test_execution_pattern_test ON test_execution_pattern(test_case_id);
CREATE INDEX idx_test_execution_pattern_failure_rate ON test_execution_pattern(failure_rate);
CREATE INDEX idx_test_execution_pattern_execution_time ON test_execution_pattern(avg_execution_time_ms);

-- Views for AI/ML queries

-- View: Tests with high confidence transformations
CREATE OR REPLACE VIEW high_confidence_transformations AS
SELECT 
    ait.id,
    ait.source_framework,
    ait.target_framework,
    ait.source_file,
    ait.confidence_score,
    ait.status,
    ait.created_at
FROM ai_transformation ait
WHERE ait.confidence_score >= 0.8
ORDER BY ait.confidence_score DESC, ait.created_at DESC;

-- View: Flaky tests with failure rates
CREATE OR REPLACE VIEW flaky_test_summary AS
SELECT 
    tc.id,
    tc.framework,
    tc.class_name,
    tc.method_name,
    COUNT(*) as total_executions,
    SUM(CASE WHEN fth.status = 'failed' THEN 1 ELSE 0 END) as failure_count,
    CAST(SUM(CASE WHEN fth.status = 'failed' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as failure_rate,
    AVG(fth.execution_duration_ms) as avg_duration_ms
FROM test_case tc
JOIN flaky_test_history fth ON tc.id = fth.test_case_id
GROUP BY tc.id, tc.framework, tc.class_name, tc.method_name
HAVING CAST(SUM(CASE WHEN fth.status = 'failed' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) > 0.1
ORDER BY failure_rate DESC;

-- View: Potential duplicate tests
CREATE OR REPLACE VIEW potential_duplicate_tests AS
SELECT 
    ts.id,
    tc1.framework as framework_1,
    tc1.method_name as test_1,
    tc2.framework as framework_2,
    tc2.method_name as test_2,
    ts.similarity_score,
    ts.detection_method,
    ts.suggested_action,
    ts.reviewed
FROM test_similarity ts
JOIN test_case tc1 ON ts.test_case_1_id = tc1.id
JOIN test_case tc2 ON ts.test_case_2_id = tc2.id
WHERE ts.similarity_score >= 0.85 AND ts.reviewed = FALSE
ORDER BY ts.similarity_score DESC;

-- View: AI model performance tracking
CREATE OR REPLACE VIEW ai_model_performance AS
SELECT 
    ait.ai_model,
    COUNT(*) as total_transformations,
    AVG(ait.confidence_score) as avg_confidence,
    SUM(CASE WHEN ait.status = 'approved' THEN 1 ELSE 0 END) as approved_count,
    SUM(CASE WHEN ait.status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
    CAST(SUM(CASE WHEN ait.status = 'approved' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as approval_rate,
    AVG(acf.actual_quality) as avg_actual_quality
FROM ai_transformation ait
LEFT JOIN ai_confidence_feedback acf ON ait.id = acf.transformation_id
WHERE ait.ai_model IS NOT NULL
GROUP BY ait.ai_model
ORDER BY approval_rate DESC, avg_actual_quality DESC;

-- View: Smart test selection candidates
CREATE OR REPLACE VIEW smart_test_selection AS
SELECT 
    tc.id,
    tc.framework,
    tc.method_name,
    tc.file_path,
    tep.avg_execution_time_ms,
    tep.failure_rate,
    tep.execution_count,
    tep.last_executed,
    CASE 
        WHEN tep.failure_rate > 0.5 THEN 'high_priority'
        WHEN tep.failure_rate > 0.2 THEN 'medium_priority'
        ELSE 'low_priority'
    END as priority
FROM test_case tc
JOIN test_execution_pattern tep ON tc.id = tep.test_case_id
WHERE tep.execution_count > 5
ORDER BY tep.failure_rate DESC, tep.avg_execution_time_ms ASC;

-- Comments for documentation
COMMENT ON TABLE memory_record IS 'Vector embeddings for semantic search across test artifacts';
COMMENT ON TABLE ai_transformation IS 'AI-assisted transformation history with confidence tracking';
COMMENT ON TABLE flaky_test_history IS 'Execution history for flaky test detection';
COMMENT ON TABLE test_similarity IS 'Semantic similarity scores for duplicate detection';
COMMENT ON TABLE ai_confidence_feedback IS 'Human feedback loop for AI quality improvement';
COMMENT ON TABLE test_execution_pattern IS 'Execution patterns for smart test selection';

-- Enable pgvector extension if not already enabled
-- Requires PostgreSQL with pgvector extension installed
-- CREATE EXTENSION IF NOT EXISTS vector;
