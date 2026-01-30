-- ============================================================================
-- Embedding Reliability Schema Extensions
-- 
-- Extends existing memory/embedding tables with reliability tracking:
-- - Embedding versions
-- - Content fingerprints
-- - Staleness detection
-- - Drift monitoring
-- ============================================================================

-- Add reliability columns to existing test_embedding table (if using PostgreSQL)
-- Note: Adjust table name based on actual schema (test_memory, memory_records, etc.)

-- Version tracking
ALTER TABLE test_embedding 
ADD COLUMN IF NOT EXISTS embedding_version TEXT,
ADD COLUMN IF NOT EXISTS embedding_created_at TIMESTAMP DEFAULT NOW();

-- Fingerprint for change detection
ALTER TABLE test_embedding
ADD COLUMN IF NOT EXISTS entity_fingerprint TEXT;

-- Staleness flags
ALTER TABLE test_embedding
ADD COLUMN IF NOT EXISTS manually_stale BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS stale_marked_at TIMESTAMP;

-- Drift detection
ALTER TABLE test_embedding
ADD COLUMN IF NOT EXISTS drift_score FLOAT,
ADD COLUMN IF NOT EXISTS drift_detected BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS last_drift_check TIMESTAMP;

-- Lifecycle state
CREATE TYPE embedding_state AS ENUM ('ACTIVE', 'STALE', 'REINDEXING', 'DEPRECATED');

ALTER TABLE test_embedding
ADD COLUMN IF NOT EXISTS index_state embedding_state DEFAULT 'ACTIVE';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_embedding_version 
ON test_embedding(embedding_version);

CREATE INDEX IF NOT EXISTS idx_embedding_state 
ON test_embedding(index_state) 
WHERE index_state != 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_drift_detected 
ON test_embedding(drift_detected) 
WHERE drift_detected = TRUE;

CREATE INDEX IF NOT EXISTS idx_stale_embeddings
ON test_embedding(manually_stale, embedding_created_at)
WHERE manually_stale = TRUE OR embedding_created_at < NOW() - INTERVAL '90 days';

-- Reindex queue table (optional - can use in-memory queue instead)
CREATE TABLE IF NOT EXISTS embedding_reindex_queue (
    id SERIAL PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    priority INTEGER DEFAULT 50,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB,
    UNIQUE(entity_id, status)
);

CREATE INDEX IF NOT EXISTS idx_reindex_queue_status 
ON embedding_reindex_queue(status, priority DESC)
WHERE status = 'pending';

-- View for stale embeddings
CREATE OR REPLACE VIEW stale_embeddings AS
SELECT 
    id,
    entity_id,
    entity_type,
    embedding_version,
    embedding_created_at,
    EXTRACT(DAY FROM NOW() - embedding_created_at) as age_days,
    drift_score,
    drift_detected,
    manually_stale,
    index_state,
    CASE
        WHEN embedding_version != 'v1::text-only::openai' THEN 'VERSION_MISMATCH'
        WHEN manually_stale THEN 'MANUAL_STALE'
        WHEN drift_detected THEN 'DRIFT_DETECTED'
        WHEN EXTRACT(DAY FROM NOW() - embedding_created_at) > 90 THEN 'AGE_THRESHOLD'
        ELSE 'UNKNOWN'
    END as staleness_reason
FROM test_embedding
WHERE 
    index_state != 'ACTIVE'
    OR embedding_version IS NULL
    OR embedding_version != 'v1::text-only::openai'
    OR manually_stale = TRUE
    OR drift_detected = TRUE
    OR EXTRACT(DAY FROM NOW() - embedding_created_at) > 90;

-- Function to mark embedding as stale
CREATE OR REPLACE FUNCTION mark_embedding_stale(p_entity_id TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE test_embedding
    SET 
        manually_stale = TRUE,
        stale_marked_at = NOW(),
        index_state = 'STALE'
    WHERE entity_id = p_entity_id;
END;
$$ LANGUAGE plpgsql;

-- Function to queue reindex job
CREATE OR REPLACE FUNCTION queue_reindex(
    p_entity_id TEXT,
    p_entity_type TEXT,
    p_reason TEXT,
    p_priority INTEGER DEFAULT 50
)
RETURNS INTEGER AS $$
DECLARE
    v_job_id INTEGER;
BEGIN
    INSERT INTO embedding_reindex_queue (
        entity_id,
        entity_type,
        reason,
        priority
    )
    VALUES (
        p_entity_id,
        p_entity_type,
        p_reason,
        p_priority
    )
    ON CONFLICT (entity_id, status) DO UPDATE
    SET priority = GREATEST(embedding_reindex_queue.priority, p_priority)
    RETURNING id INTO v_job_id;
    
    RETURN v_job_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-queue stale embeddings for reindex
CREATE OR REPLACE FUNCTION auto_queue_stale_embeddings()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.index_state = 'STALE' OR NEW.manually_stale = TRUE THEN
        PERFORM queue_reindex(
            NEW.entity_id,
            NEW.entity_type,
            'AUTO_DETECTED',
            60
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_queue_stale
AFTER UPDATE ON test_embedding
FOR EACH ROW
WHEN (OLD.index_state != NEW.index_state OR OLD.manually_stale != NEW.manually_stale)
EXECUTE FUNCTION auto_queue_stale_embeddings();

COMMENT ON TABLE embedding_reindex_queue IS 
'Queue for embedding reindexing jobs triggered by staleness detection';

COMMENT ON COLUMN test_embedding.embedding_version IS 
'Semantic version: <schema>::<content>::<model> (e.g., v1::text-only::openai)';

COMMENT ON COLUMN test_embedding.entity_fingerprint IS 
'SHA-256 fingerprint of entity text for change detection';

COMMENT ON COLUMN test_embedding.drift_score IS 
'Cosine similarity between old and new embeddings (0-1)';
