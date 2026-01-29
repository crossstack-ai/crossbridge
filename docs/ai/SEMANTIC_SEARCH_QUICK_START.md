# Semantic Search - Quick Start Guide

Get started with CrossBridge Semantic Search in 5 minutes.

## Prerequisites

- CrossBridge installed and configured
- PostgreSQL database with pgvector extension
- OpenAI API key (or Anthropic/local provider configured)

## Step 1: Configure (2 minutes)

### Set API Key

```bash
# Linux/Mac
export OPENAI_API_KEY=sk-your-key-here

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"

# Windows CMD
set OPENAI_API_KEY=sk-your-key-here
```

### Verify Configuration

Check your `crossbridge.yml`:

```yaml
runtime:
  semantic_search:
    enabled: auto  # Auto-enables in migration mode
    provider_type: openai
    openai:
      api_key: ${OPENAI_API_KEY}
      model: text-embedding-3-large
```

## Step 2: Setup Database (1 minute)

Create the semantic embeddings table:

```bash
# Run the migration SQL
psql -h your-host -U your-user -d your-database -f scripts/semantic_embeddings_schema.sql

# Or manually create the table (see scripts/semantic_embeddings_schema.sql)
```

## Step 3: Index Your Tests (1 minute)

### Index Pytest Tests

```bash
crossbridge semantic index -f pytest -p ./tests
```

### Index Robot Framework Tests

```bash
crossbridge semantic index -f robot -p ./tests --entity-type scenario
```

### Index Multiple Frameworks

```bash
# Let CrossBridge auto-detect frameworks
crossbridge semantic index -p ./tests
```

**Expected Output:**
```
📊 Indexing Configuration
Framework: pytest
Path: ./tests
Entity Type: test
Provider: openai (text-embedding-3-large)

Found 50 test files
[========================================] 50/50
✓ Successfully indexed 50 tests
Total entities in vector store: 50
```

## Step 4: Search (1 minute)

### Basic Search

```bash
crossbridge semantic search "login timeout error"
```

**Output:**
```
🔍 Search Results for: login timeout error

Score    Type     ID                        Preview
─────────────────────────────────────────────────────────────
0.891    test     test_login_timeout        Test: test_login_timeout, Framework: pytest...
0.867    test     test_auth_timeout         Test: test_auth_timeout, Framework: pytest...
0.843    failure  login_timeout_20240115    Error: TimeoutError waiting for element...

Found 3 similar entities
```

### Search with Filters

```bash
# Only tests, minimum score 0.8
crossbridge semantic search "API validation" --entity-type test --min-score 0.8

# Get more results
crossbridge semantic search "authentication" --top-k 20
```

### Find Similar Tests

```bash
crossbridge semantic similar test_user_login
```

**Output:**
```
🔗 Entities Similar to: test_user_login

Score    Type     ID                        Preview
─────────────────────────────────────────────────────────────
0.925    test     test_admin_login          Test: test_admin_login, Framework: pytest...
0.887    test     test_oauth_login          Test: test_oauth_login, Framework: pytest...
0.856    test     test_user_authentication  Test: test_user_authentication...
```

## Step 5: Check Statistics

```bash
crossbridge semantic stats
```

**Output:**
```
📊 Semantic Search Statistics

Total Entities: 150
Entity Types: test: 120, scenario: 20, failure: 10
Embedding Versions: v1-text-only
Provider: openai (text-embedding-3-large)
Dimensions: 3072
```

## Common Use Cases

### 1. Find Tests Affected by Bug

```bash
# Search for tests that might be affected
crossbridge semantic search "database connection timeout" --entity-type test
```

### 2. Discover Similar Failures

```bash
# Find similar historical failures
crossbridge semantic search "NullPointerException in user service" --entity-type failure
```

### 3. Test Migration Discovery

```bash
# Find equivalent tests in target framework
crossbridge semantic search "user login with OAuth" --entity-type test
```

### 4. Test Recommendation

```bash
# Find similar tests to understand test patterns
crossbridge semantic similar test_checkout_success
```

## Python API Quick Start

```python
from core.ai.embeddings.semantic_service import SemanticSearchService
from core.config.loader import ConfigLoader

# Initialize
config_loader = ConfigLoader()
service = SemanticSearchService(config_loader=config_loader)

# Index a test
service.index_entity(
    entity_id="test_user_login",
    entity_type="test",
    test_name="test_user_login",
    description="User login with valid credentials",
    framework="pytest"
)

# Search
results = service.search("login", top_k=5)
for result in results:
    print(f"{result.score:.3f} - {result.id}")

# Find similar
similar = service.find_similar("test_user_login", top_k=5)
for result in similar:
    print(f"{result.score:.3f} - {result.id}")
```

## Configuration Options

### Use Local Provider (No API Key)

```yaml
runtime:
  semantic_search:
    provider_type: local
    local:
      model: all-MiniLM-L6-v2
      device: cpu
```

### Tune Similarity Threshold

```yaml
runtime:
  semantic_search:
    search:
      min_similarity_score: 0.6  # Lower = more lenient (0-1)
```

### Adjust Batch Size

```yaml
runtime:
  semantic_search:
    search:
      batch_size: 50  # Smaller batches for rate limiting
```

## Troubleshooting

### Issue: "No results found"

**Solution**: Check if tests are indexed
```bash
crossbridge semantic stats
# If Total Entities: 0, run:
crossbridge semantic index -f pytest -p ./tests
```

### Issue: "API timeout"

**Solution**: Increase timeout or use smaller batches
```yaml
search:
  api_timeout: 60
  retry_attempts: 5
  batch_size: 50
```

### Issue: "Vector dimension mismatch"

**Solution**: Recreate table with correct dimensions
```sql
-- For text-embedding-3-large (3072)
ALTER TABLE semantic_embeddings ALTER COLUMN embedding TYPE VECTOR(3072);

-- For text-embedding-3-small (1536)
ALTER TABLE semantic_embeddings ALTER COLUMN embedding TYPE VECTOR(1536);
```

## Next Steps

1. **Read Full Documentation**: [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md)
2. **Explore Examples**: [examples/semantic_search_examples.py](../../examples/semantic_search_examples.py)
3. **Optimize Performance**: Create IVFFlat index for large datasets
4. **Integrate with CI/CD**: Add semantic indexing to your test pipeline

## Performance Tips

### For Large Datasets (> 1000 tests)

```python
# Create IVFFlat index for fast similarity search
from core.ai.embeddings.pgvector_store import PgVectorStore
store = PgVectorStore()
store.create_index(lists=100)
```

### Batch Indexing

```bash
# Use larger batch size for faster indexing
crossbridge semantic index -f pytest -p ./tests --batch-size 200
```

### Filter Searches

```bash
# Always filter by entity_type for better performance
crossbridge semantic search "query" --entity-type test
```

## Need Help?

- **Documentation**: [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md)
- **Examples**: [examples/semantic_search_examples.py](../../examples/semantic_search_examples.py)
- **Issues**: Check logs in `logs/crossbridge.log`

---

**You're all set!** Start exploring semantic search to discover hidden connections in your test suite.
