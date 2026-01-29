-- ============================================================================
-- CrossBridge Semantic Search Database Schema
-- ============================================================================
-- Purpose: Store vector embeddings for semantic similarity search
-- Features: 
--   - pgvector for cosine similarity search
--   - JSONB metadata for flexible filtering
--   - Versioned embeddings for reindexing support
--   - IVFFlat index for efficient similarity search
-- ============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Semantic Embeddings Table
-- ============================================================================
-- Stores vector embeddings for test artifacts (tests, scenarios, failures)
-- with metadata and versioning support.
-- ============================================================================
CREATE TABLE IF NOT EXISTS semantic_embeddings (
    -- Primary identification
    id TEXT PRIMARY KEY,                              -- Unique entity ID (e.g., "test_login_timeout")
    entity_type TEXT NOT NULL,                        -- Entity type: test, scenario, failure
    
    -- Embedding data
    embedding VECTOR(3072) NOT NULL,                  -- Vector embedding (default: OpenAI text-embedding-3-large)
    embedding_text TEXT NOT NULL,                     -- Original text used to generate embedding
    
    -- Model tracking
    model TEXT NOT NULL,                              -- Embedding model used (e.g., "text-embedding-3-large")
    version TEXT NOT NULL DEFAULT 'v1-text-only',    -- Embedding version for reindexing
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,               -- Flexible metadata (framework, file_path, tags, etc.)
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),               -- Creation timestamp
    updated_at TIMESTAMP DEFAULT now()                -- Last update timestamp
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Index on entity_type for filtered searches
CREATE INDEX IF NOT EXISTS idx_semantic_embeddings_entity_type 
    ON semantic_embeddings(entity_type);

-- Index on version for version-specific queries
CREATE INDEX IF NOT EXISTS idx_semantic_embeddings_version 
    ON semantic_embeddings(version);

-- Composite index on entity_type and version for common queries
CREATE INDEX IF NOT EXISTS idx_semantic_embeddings_type_version 
    ON semantic_embeddings(entity_type, version);

-- GIN index on metadata for JSONB queries
CREATE INDEX IF NOT EXISTS idx_semantic_embeddings_metadata 
    ON semantic_embeddings USING GIN(metadata);

-- IVFFlat index for fast vector similarity search
-- Note: This index is created separately after data is loaded
-- See: PgVectorStore.create_index() method
-- Command: CREATE INDEX idx_semantic_embeddings_vector 
--          ON semantic_embeddings USING ivfflat (embedding vector_cosine_ops)
--          WITH (lists = 100);

-- ============================================================================
-- Functions
-- ============================================================================

-- Update updated_at timestamp on row update
CREATE OR REPLACE FUNCTION update_semantic_embeddings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trg_update_semantic_embeddings_updated_at ON semantic_embeddings;
CREATE TRIGGER trg_update_semantic_embeddings_updated_at
    BEFORE UPDATE ON semantic_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_semantic_embeddings_updated_at();

-- ============================================================================
-- Example Queries
-- ============================================================================

-- Find top 10 most similar entities to a query embedding
-- SELECT id, entity_type, 1 - (embedding <-> '[0.1, 0.2, ...]'::vector) as similarity_score
-- FROM semantic_embeddings
-- WHERE entity_type = 'test' AND version = 'v1-text-only'
-- ORDER BY embedding <-> '[0.1, 0.2, ...]'::vector
-- LIMIT 10;

-- Count entities by type and version
-- SELECT entity_type, version, COUNT(*) as count
-- FROM semantic_embeddings
-- GROUP BY entity_type, version
-- ORDER BY entity_type, version;

-- Find tests with specific metadata
-- SELECT id, entity_type, metadata->>'framework' as framework
-- FROM semantic_embeddings
-- WHERE entity_type = 'test' 
--   AND metadata->>'framework' = 'pytest'
--   AND version = 'v1-text-only';

-- ============================================================================
-- Notes
-- ============================================================================
-- 1. The embedding VECTOR size should match your embedding model:
--    - OpenAI text-embedding-3-large: 3072 dimensions
--    - OpenAI text-embedding-3-small: 1536 dimensions
--    - Voyage AI voyage-large-2: 1536 dimensions
--    - sentence-transformers all-MiniLM-L6-v2: 384 dimensions
--
--    To change dimension size for different models:
--    ALTER TABLE semantic_embeddings ALTER COLUMN embedding TYPE VECTOR(1536);
--
-- 2. IVFFlat index should be created after loading data for better performance.
--    Recommended after loading 1000+ entities:
--    CREATE INDEX idx_semantic_embeddings_vector 
--        ON semantic_embeddings USING ivfflat (embedding vector_cosine_ops)
--        WITH (lists = 100);
--
--    Adjust 'lists' parameter based on data size:
--    - Small datasets (< 10k): lists = 10-50
--    - Medium datasets (10k-100k): lists = 100-500
--    - Large datasets (> 100k): lists = 1000+
--
-- 3. The <-> operator computes cosine distance (0 = identical, 2 = opposite).
--    Cosine similarity = 1 - cosine_distance
--
-- 4. For best query performance, always filter by entity_type and version
--    before doing similarity search to reduce the search space.
-- ============================================================================
