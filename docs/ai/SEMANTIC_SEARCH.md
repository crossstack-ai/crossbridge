# Semantic Search & Test Intelligence

## Overview

CrossBridge's Semantic Search system provides a **unified platform** for test normalization, structural analysis, and intelligent similarity search. It combines:

1. **Universal Test Normalization** - Converts tests from any framework to `UnifiedTestMemory` format
2. **AST Extraction** - Extracts structural signals (imports, functions, assertions, API calls, UI interactions)
3. **Vector Embeddings** - Generates semantic embeddings for intelligent search
4. **Similarity Search** - Finds related tests using natural language queries

Instead of exact keyword matching, semantic search understands the *meaning* of tests, scenarios, and failures to find relevant matches even when they use different terminology.

## Key Features

- **Framework-Agnostic Normalization**: Works with pytest, Robot Framework, Cypress, Playwright, Java, and 12+ frameworks
- **Natural Language Queries**: Search using plain English descriptions
- **Multi-Provider Support**: OpenAI, Anthropic (Voyage AI), or local sentence-transformers
- **Structural Intelligence**: Combines semantic similarity with AST-based structural signals
- **Versioned Embeddings**: Reindex with new models without losing old data
- **Production Ready**: PostgreSQL + pgvector for scalable, reliable vector storage
- **Migration Mode Auto-Enable**: Automatically enabled during migration for test discovery

## Configuration

All settings are unified under `runtime.semantic_search` in [crossbridge.yml](../../crossbridge.yml):

```yaml
runtime:
  semantic_search:
    enabled: auto  # Auto-enable in migration mode
    
    # Test normalization & AST extraction
    normalization:
      auto_normalize: true
      extract_structural_signals: true
      extract_ui_interactions: true
      extract_api_calls: true
    
    # Embedding provider
    provider_type: openai
    openai:
      api_key: ${OPENAI_API_KEY}
      model: text-embedding-3-large
    
    # Search settings
    search:
      max_tokens: 8000
      min_similarity_score: 0.7
      default_top_k: 10
```

**Note**: There is only ONE configuration section - `runtime.semantic_search`. This replaces any older `memory` or `embeddings` sections you may see in older documentation.

## Use Cases

### 1. **Find Similar Test Failures**
Quickly identify similar historical failures to understand patterns:
```bash
crossbridge semantic search "timeout waiting for element to load"
```

### 2. **Discover Related Tests**
Find tests that might be affected by a code change:
```bash
crossbridge semantic similar test_user_login
```

### 3. **Test Migration Assistance**
During framework migration, find equivalent tests in the target framework:
```bash
crossbridge semantic search "user authentication with OAuth flow" --entity-type test
```

### 4. **Flaky Test Analysis**
Find tests with similar failure patterns:
```bash
crossbridge semantic search "intermittent connection error" --entity-type failure
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                             │
│              "login timeout error"                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              EmbeddingTextBuilder                           │
│  Normalize & enhance text with domain context              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              EmbeddingProvider                              │
│  Generate vector embedding (OpenAI/Anthropic/Local)        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              PgVectorStore                                   │
│  Cosine similarity search in PostgreSQL                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              SimilarityResults                              │
│  Ranked list of similar entities with scores               │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### YAML Configuration (crossbridge.yml)

```yaml
runtime:
  semantic_search:
    # Enable/disable semantic search (auto = enable in migration mode)
    enabled: auto
    
    # Embedding provider: openai, anthropic, local
    provider_type: openai
    
    # OpenAI configuration (text-embedding-3-large/small)
    openai:
      api_key: ${OPENAI_API_KEY}
      model: text-embedding-3-large  # 3072 dimensions, highest quality
      dimensions: 3072
    
    # Search configuration
    search:
      max_tokens: 8000
      min_similarity_score: 0.7  # 0-1 range, higher = more strict
      default_top_k: 10
      api_timeout: 30
      retry_attempts: 3
      batch_size: 100
    
    # Migration mode overrides
    migration_overrides:
      enabled: true
      provider_type: openai
      model: text-embedding-3-large
      min_similarity_score: 0.6  # Lower threshold for discovery
```

### Environment Variables

```bash
# OpenAI API Key (required for OpenAI provider)
export OPENAI_API_KEY=sk-...

# Anthropic API Key (required for Anthropic provider)
export ANTHROPIC_API_KEY=sk-ant-...

# Database connection (uses main CrossBridge database)
# No additional configuration needed
```

## Embedding Providers

### OpenAI (Recommended)
- **Model**: `text-embedding-3-large` (3072 dimensions)
- **Quality**: Highest accuracy and semantic understanding
- **Cost**: ~$0.13 per 1M tokens
- **Use When**: Best quality needed, budget available

```yaml
provider_type: openai
openai:
  api_key: ${OPENAI_API_KEY}
  model: text-embedding-3-large
  dimensions: 3072
```

### Anthropic (Voyage AI)
- **Model**: `voyage-large-2` (1536 dimensions)
- **Quality**: High accuracy, competitive with OpenAI
- **Cost**: Similar to OpenAI
- **Use When**: Alternative to OpenAI, good quality/cost balance

```yaml
provider_type: anthropic
anthropic:
  api_key: ${ANTHROPIC_API_KEY}
  model: voyage-large-2
```

### Local (sentence-transformers)
- **Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Quality**: Good for basic similarity
- **Cost**: Free, runs on CPU/GPU
- **Use When**: Air-gapped environments, no API costs, lower quality acceptable

```yaml
provider_type: local
local:
  model: all-MiniLM-L6-v2
  device: cpu  # or cuda for GPU acceleration
```

## CLI Commands

### Index Tests
```bash
# Index all pytest tests
crossbridge semantic index -f pytest -p ./tests

# Index Robot Framework scenarios
crossbridge semantic index -f robot -p ./tests --entity-type scenario

# Index Cypress tests with reindexing
crossbridge semantic index -f cypress -p ./cypress/e2e --reindex

# Index with custom batch size
crossbridge semantic index -f playwright -p ./tests --batch-size 50
```

### Search
```bash
# Basic search
crossbridge semantic search "login timeout error"

# Search with filters
crossbridge semantic search "API validation" \
  --entity-type test \
  --min-score 0.8 \
  --top-k 5

# JSON output for scripting
crossbridge semantic search "authentication" --json
```

### Find Similar Entities
```bash
# Find tests similar to specific test
crossbridge semantic similar test_login_timeout

# Find with more results
crossbridge semantic similar scenario_user_authentication --top-k 20

# JSON output
crossbridge semantic similar test_api_validation --json
```

### Statistics
```bash
# Display system statistics
crossbridge semantic stats

# JSON output
crossbridge semantic stats --json
```

## Python API

### Basic Usage

```python
from core.ai.embeddings.semantic_service import SemanticSearchService
from core.config.loader import ConfigLoader

# Initialize service
config_loader = ConfigLoader()
service = SemanticSearchService(config_loader=config_loader)

# Index a test
service.index_entity(
    entity_id="test_user_login",
    entity_type="test",
    test_name="test_user_login",
    description="User login with valid credentials",
    framework="pytest",
    tags=["authentication", "smoke"]
)

# Search
results = service.search("login timeout", top_k=5)
for result in results:
    print(f"{result.score:.3f} - {result.id}: {result.text[:100]}...")

# Find similar
similar = service.find_similar("test_user_login", top_k=5)
```

### Advanced Usage

```python
# Batch indexing
entities = [
    {
        "entity_id": "test_1",
        "entity_type": "test",
        "test_name": "test_login",
        "framework": "pytest"
    },
    # ... more entities
]
service.index_batch(entities)

# Search with filters
results = service.search(
    query="authentication tests",
    top_k=10,
    entity_type="test",
    filters={"framework": "pytest"},
    min_score=0.75
)

# Get statistics
stats = service.get_statistics()
print(f"Total entities: {stats['total_entities']}")
print(f"Provider: {stats['provider_type']}")
```

## Database Schema

### semantic_embeddings Table

```sql
CREATE TABLE semantic_embeddings (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    embedding VECTOR(3072) NOT NULL,
    embedding_text TEXT NOT NULL,
    model TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1-text-only',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

### Key Fields

- **id**: Unique entity identifier (e.g., `test_login_timeout`)
- **entity_type**: Type of entity (`test`, `scenario`, `failure`)
- **embedding**: Vector embedding (dimensions match provider)
- **embedding_text**: Original text used to generate embedding
- **model**: Embedding model name
- **version**: Embedding version for reindexing
- **metadata**: Flexible JSONB for framework, tags, file paths, etc.

## Performance Tuning

### IVFFlat Index

For datasets > 1000 entities, create an IVFFlat index:

```python
from core.ai.embeddings.pgvector_store import PgVectorStore

store = PgVectorStore()
store.create_index(lists=100)  # Adjust based on data size
```

**Index Size Guidelines:**
- Small (< 10k entities): `lists = 10-50`
- Medium (10k-100k): `lists = 100-500`
- Large (> 100k): `lists = 1000+`

### Batch Indexing

Use batch operations for bulk indexing:

```python
# More efficient than individual index_entity calls
service.index_batch(entities)  # Default batch_size=100
```

### API Rate Limiting

Configure retry and timeout:

```yaml
search:
  api_timeout: 30  # Seconds
  retry_attempts: 3  # Retry failed API calls
  batch_size: 100  # Entities per batch
```

## Migration Mode Integration

Semantic search automatically enables during migration mode to assist with test discovery and mapping.

### Auto-Enable Configuration

```yaml
semantic_search:
  enabled: auto  # Enables in migration mode
  migration_overrides:
    enabled: true
    provider_type: openai
    model: text-embedding-3-large
    min_similarity_score: 0.6  # Lower threshold for discovery
```

### Migration Use Cases

1. **Find Equivalent Tests**: Discover tests in target framework similar to source tests
2. **Coverage Mapping**: Map source test coverage to target framework
3. **Duplicate Detection**: Identify redundant or duplicate tests
4. **Test Recommendations**: Suggest new tests based on existing patterns

## Text Building Strategy

### Deterministic Text Construction

The `EmbeddingTextBuilder` creates deterministic, domain-specific text representations:

```python
# Test entity
text = """
Test: test_user_login
Framework: pytest
Description: User login with valid credentials
Steps:
  - Navigate to login page
  - Enter username and password
  - Click login button
  - Verify dashboard loads
Tags: authentication, smoke
"""

# Scenario entity (BDD)
text = """
Scenario: User logs in successfully
Feature: User Authentication
Given user is on login page
When user enters valid credentials
And user clicks login button
Then user should see dashboard
Tags: authentication
"""
```

### Token Limits

Automatic token truncation ensures embeddings stay within model limits:

```python
# Estimated: 1 token ≈ 4 characters
service.index_entity(..., max_tokens=8000)  # Auto-truncates if needed
```

## Troubleshooting

### Issue: No results found

**Cause**: Similarity threshold too high or no indexed entities

**Solution**:
```bash
# Check indexed entities
crossbridge semantic stats

# Lower similarity threshold
crossbridge semantic search "query" --min-score 0.5

# Index entities if needed
crossbridge semantic index -f pytest -p ./tests
```

### Issue: API timeout errors

**Cause**: Network issues or API rate limits

**Solution**:
```yaml
search:
  api_timeout: 60  # Increase timeout
  retry_attempts: 5  # More retries
```

### Issue: Out of memory (local provider)

**Cause**: Large model on insufficient hardware

**Solution**:
```yaml
local:
  model: all-MiniLM-L6-v2  # Use smaller model
  device: cpu  # Use CPU if GPU memory insufficient
```

### Issue: Slow similarity search

**Cause**: Missing IVFFlat index or large dataset

**Solution**:
```python
# Create IVFFlat index
from core.ai.embeddings.pgvector_store import PgVectorStore
store = PgVectorStore()
store.create_index(lists=100)
```

## Best Practices

1. **Choose Right Provider**
   - Production: OpenAI text-embedding-3-large
   - Cost-sensitive: Anthropic Voyage AI
   - Air-gapped: Local sentence-transformers

2. **Index Incrementally**
   - Index new tests as they're created
   - Use batch operations for bulk indexing
   - Reindex when changing embedding models

3. **Tune Similarity Thresholds**
   - Start with 0.7 for strict matching
   - Lower to 0.5-0.6 for discovery
   - Adjust based on result quality

4. **Use Entity Type Filters**
   - Filter by entity_type for focused searches
   - Reduces search space and improves performance

5. **Monitor Statistics**
   - Track entity counts by type
   - Monitor embedding versions
   - Check provider usage

## Examples

See [examples/semantic_search_examples.py](../../examples/semantic_search_examples.py) for complete working examples.

## See Also

- [Quick Start Guide](SEMANTIC_SEARCH_QUICK_START.md)
- [API Reference](API_REFERENCE.md)
- [Configuration Reference](../CONFIGURATION.md)
