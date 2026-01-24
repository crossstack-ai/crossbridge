# Memory & Embeddings System - Technical Documentation

## Overview

CrossBridge's Memory & Embeddings system provides **intelligent, semantic storage and retrieval** of test-related knowledge. Unlike traditional keyword search, this system understands the meaning and context of tests, enabling AI-powered discovery, similarity detection, and intelligent recommendations.

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    CrossBridge Core                         │
├─────────────────────────────────────────────────────────────┤
│  Test Discovery → Extractors → Memory Records              │
│                                    ↓                         │
│                         Embedding Provider                   │
│                         (OpenAI/Local/HF)                   │
│                                    ↓                         │
│                          Vector Store                        │
│                    (PostgreSQL + pgvector)                  │
│                                    ↓                         │
│                      Semantic Search Engine                  │
│                                    ↓                         │
│                    CLI / API / AI Features                   │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| **MemoryRecord** | Canonical data model for test entities | `core/memory/models.py` |
| **EmbeddingProvider** | Pluggable embedding generation | `core/memory/embedding_provider.py` |
| **VectorStore** | Pluggable vector database | `core/memory/vector_store.py` |
| **MemoryIngestionPipeline** | Entity extraction and storage | `core/memory/ingestion.py` |
| **SemanticSearchEngine** | Natural language search | `core/memory/search.py` |

---

## Memory Records

### What Gets Stored?

The system embeds **semantic units**, not raw files:

| Entity Type | Example | Use Case |
|-------------|---------|----------|
| `test` | `LoginTest.testValidLogin` | Find tests by behavior/intent |
| `scenario` | `Scenario: Valid Login` | Search BDD scenarios |
| `step` | `When user enters valid credentials` | Find step definitions |
| `page` | `LoginPage.login()` | Locate page objects |
| `code` | `LoginService.authenticate()` | Coverage analysis |
| `failure` | `TimeoutException during login` | Failure pattern matching |

### MemoryRecord Structure

```python
@dataclass
class MemoryRecord:
    id: str                      # Stable ID (test_id, step_id)
    type: MemoryType            # Entity type (test, scenario, etc.)
    text: str                   # Natural language representation
    metadata: Dict[str, Any]    # Framework, file, tags, intent
    embedding: List[float]      # Vector representation
    created_at: datetime
    updated_at: datetime
```

### Text Construction

Records are converted to natural language for embedding:

**Test Example:**
```
Test Name: test_login_valid
Framework: pytest
Steps: open_browser, navigate_to_login, enter_credentials, click_submit
Purpose: Verify successful login with valid credentials
Tags: auth, smoke
```

**Scenario Example:**
```
Scenario: User logs in with valid credentials
Feature: Authentication
Steps:
  - Given user is on login page
  - When user enters valid username
  - And user enters valid password
  - Then user should be redirected to dashboard
Tags: @smoke @auth
```

---

## Embedding Providers

### Supported Providers

#### 1. OpenAI (Recommended)

```yaml
memory:
  embedding_provider:
    type: openai
    model: text-embedding-3-large  # 3072 dimensions
    # model: text-embedding-3-small  # 1536 dimensions (faster, cheaper)
    # model: text-embedding-ada-002  # 1536 dimensions (legacy)
    api_key: ${OPENAI_API_KEY}
    batch_size: 100
```

**Features:**
- ✅ Highest quality embeddings
- ✅ Best for English test descriptions
- ✅ Production-ready
- ⚠️ Requires API key and credits

**Pricing** (as of 2024):
- `text-embedding-3-large`: $0.13 per 1M tokens (~500K test records)
- `text-embedding-3-small`: $0.02 per 1M tokens

#### 2. Local (Ollama)

```yaml
memory:
  embedding_provider:
    type: local
    model: nomic-embed-text  # 768 dimensions
    base_url: http://localhost:11434
```

**Features:**
- ✅ Completely private (no API calls)
- ✅ No cost
- ✅ Good for small-medium projects
- ⚠️ Requires Ollama installed locally

**Setup:**
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull embedding model
ollama pull nomic-embed-text
```

#### 3. HuggingFace

```yaml
memory:
  embedding_provider:
    type: huggingface
    model: sentence-transformers/all-MiniLM-L6-v2  # 384 dimensions
    device: cpu  # or 'cuda' for GPU
```

**Features:**
- ✅ Completely offline
- ✅ No external dependencies
- ✅ Good for air-gapped environments
- ⚠️ Slower than API-based solutions

---

## Vector Stores

### PostgreSQL + pgvector (Recommended)

```yaml
memory:
  vector_store:
    type: pgvector
    connection_string: postgresql://user:pass@host:port/db
    dimension: 3072  # Must match embedding model
```

**Why pgvector?**
- ✅ Production-ready (used by Supabase, Timescale)
- ✅ ACID transactions
- ✅ Powerful filtering with JSONB
- ✅ HNSW index for fast similarity search
- ✅ Scales to millions of vectors

**Setup:**

1. **Install pgvector extension:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **Run setup script:**
   ```bash
   python scripts/setup_memory_db.py --dimension 3072
   ```

3. **Verify:**
   ```bash
   crossbridge memory stats
   ```

### FAISS (Local, Development)

```yaml
memory:
  vector_store:
    type: faiss
    index_path: ./data/memory/faiss_index
    dimension: 1536
```

**Why FAISS?**
- ✅ Fast for local development
- ✅ No database required
- ✅ Good for < 100K vectors
- ⚠️ No ACID transactions
- ⚠️ Limited filtering capabilities

---

## Memory Ingestion

### Manual Ingestion

```bash
# Ingest from discovery results
crossbridge discover --framework pytest --output discovery.json
crossbridge memory ingest --source discovery.json

# Check stats
crossbridge memory stats
```

### Automatic Ingestion

```yaml
memory:
  auto_ingest_on_discovery: true  # Ingest after every discovery
  update_on_change: true          # Re-embed when test code changes
```

### Programmatic Ingestion

```python
from core.memory import (
    MemoryIngestionPipeline,
    create_embedding_provider,
    create_vector_store,
)

# Setup
provider = create_embedding_provider('openai', model='text-embedding-3-large')
store = create_vector_store('pgvector', connection_string='postgresql://...', dimension=3072)
pipeline = MemoryIngestionPipeline(provider, store)

# Ingest tests
test_data = [
    {
        'id': 'test_login_valid',
        'name': 'test_login_valid',
        'framework': 'pytest',
        'steps': ['open_browser', 'navigate_to_login', 'enter_credentials'],
        'intent': 'Verify successful login with valid credentials',
        'tags': ['auth', 'smoke']
    }
]

count = pipeline.ingest_from_tests(test_data)
print(f"Ingested {count} tests")
```

---

## Semantic Search

### CLI Commands

#### 1. Natural Language Search

```bash
# Find tests covering login timeout
crossbridge search query "tests covering login timeout"

# Filter by type
crossbridge search query "payment edge cases" --type scenario

# Filter by framework
crossbridge search query "flaky auth tests" --framework pytest --top 5

# Show explanation
crossbridge search query "timeout tests" --explain
```

**Output:**
```
🔍 Searching for: "tests covering login timeout"

┌──────────────────────────────────────────────────────────┐
│              Search Results (3 found)                     │
├────┬────────┬─────────────────────┬───────┬──────────────┤
│ #  │ Type   │ ID                  │ Score │ Preview      │
├────┼────────┼─────────────────────┼───────┼──────────────┤
│ 1  │ test   │ test_login_timeout  │ 0.923 │ Test Name... │
│ 2  │ scen.  │ login_timeout_scen  │ 0.876 │ Scenario:... │
│ 3  │ test   │ test_auth_timeout   │ 0.845 │ Test Name... │
└────┴────────┴─────────────────────┴───────┴──────────────┘

📋 Top Result Details:
┌─────────────────────────────────────────────────────────┐
│ ID: test_login_timeout                                  │
│ Type: test                                              │
│ Score: 0.923                                            │
│ Metadata:                                               │
│   • framework: pytest                                   │
│   • tags: auth, timeout                                 │
│                                                         │
│ Text:                                                   │
│ Test Name: test_login_timeout                          │
│ Framework: pytest                                       │
│ Steps: open_browser, wait_for_login_form, submit      │
│ Purpose: Verify timeout handling during login         │
└─────────────────────────────────────────────────────────┘
```

#### 2. Similarity Search

```bash
# Find tests similar to a given test
crossbridge search similar test_login_valid

# Filter results
crossbridge search similar test_checkout --type test --top 10
```

**Use Cases:**
- 🔍 **Duplicate Detection**: Find tests with >0.9 similarity
- 🔗 **Related Tests**: Find complementary tests (0.5-0.8 similarity)
- 📊 **Redundant Coverage**: Identify overlapping test coverage

#### 3. Find Duplicates

```bash
crossbridge search duplicates --framework pytest --threshold 0.95
```

### Programmatic Search

```python
from core.memory import SemanticSearchEngine

engine = SemanticSearchEngine(embedding_provider, vector_store)

# Natural language search
results = engine.search(
    query="tests covering login timeout",
    entity_types=["test"],
    framework="pytest",
    top_k=10
)

for result in results:
    print(f"{result.rank}. {result.record.id} (score: {result.score:.3f})")

# Find similar tests
similar = engine.find_similar("test_login_valid", top_k=5)

# Multi-query search (combines multiple queries)
results = engine.multi_query_search(
    queries=["login tests", "authentication scenarios"],
    entity_types=["test", "scenario"]
)

# Search with context
results = engine.search_with_context(
    query="timeout tests",
    context={"file": "login_tests.py", "framework": "pytest"}
)
```

---

## Advanced Features

### 1. Duplicate Detection

Automatically find potential duplicate tests:

```python
results = engine.find_similar("test_login_valid", top_k=10)
duplicates = [r for r in results if r.score > 0.9]

if duplicates:
    print(f"⚠️  Found {len(duplicates)} potential duplicates:")
    for dup in duplicates:
        print(f"  - {dup.record.id} (similarity: {dup.score:.3f})")
```

### 2. Recommendation System

```python
# Get recommendations for a test
recommendations = engine.get_recommendations(
    record_id="test_login_valid",
    recommendation_type="similar",  # or "duplicate", "complement"
    top_k=5
)
```

**Recommendation Types:**
- `similar`: Find similar tests (general)
- `duplicate`: Very high similarity (>0.9) - potential duplicates
- `complement`: Related but different (0.5-0.8) - complementary tests

### 3. Failure Pattern Matching

Ingest failures and search for similar ones:

```python
failure_data = [{
    'id': 'failure_123',
    'test_name': 'test_login',
    'error_type': 'TimeoutException',
    'message': 'element not found within timeout',
    'stack_trace': '...'
}]

pipeline.ingest_from_failures(failure_data)

# Later, search for similar failures
results = engine.search(
    "TimeoutException element not found",
    entity_types=["failure"]
)
```

### 4. AI Integration

Use memory for contextual AI prompts:

```python
# Find related tests for AI context
context_tests = engine.search(
    query="authentication timeout handling",
    top_k=3
)

# Build AI prompt with context
prompt = f"""
Generate missing tests for authentication timeout handling.

Related existing tests:
{'\n'.join([f"- {r.record.text}" for r in context_tests])}

Generate tests that complement these existing tests.
"""

# Send to AI...
```

---

## Configuration Reference

### Complete Configuration

```yaml
memory:
  enabled: true
  
  embedding_provider:
    type: openai
    model: text-embedding-3-large
    api_key: ${OPENAI_API_KEY}
    batch_size: 100
  
  vector_store:
    type: pgvector
    connection_string: postgresql://user:pass@host:port/db
    dimension: 3072
  
  batch_size: 100
  auto_ingest_on_discovery: true
  update_on_change: true
  
  default_top_k: 10
  min_similarity_score: 0.5
  
  ttl_days: 90
  cleanup_on_startup: false
```

### Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# Database
export CROSSBRIDGE_DB_HOST=localhost
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=password
export CROSSBRIDGE_DB_NAME=crossbridge
```

---

## Performance Tuning

### Batch Size

```yaml
memory:
  batch_size: 100  # Process 100 records per batch
```

- **Small batches (10-50)**: Lower memory usage, slower
- **Medium batches (50-200)**: Balanced (recommended)
- **Large batches (200-1000)**: Faster, higher memory usage

### Vector Store Optimization

**PostgreSQL + pgvector:**

```sql
-- HNSW index parameters
CREATE INDEX ON memory_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Higher values = better recall, slower build
-- m: number of connections per layer (8-64)
-- ef_construction: size of dynamic candidate list (10-200)

-- Query-time parameter
SET hnsw.ef_search = 100;  -- Higher = better recall, slower queries
```

**FAISS:**

```python
# Use IVFFlat for large datasets
store = FAISSVectorStore(dimension=1536)
# FAISS automatically manages indexes
```

---

## Troubleshooting

### Common Issues

#### 1. "No embeddings found"

**Cause:** Records not ingested or embedding provider not configured

**Fix:**
```bash
# Check stats
crossbridge memory stats

# If 0 records, run ingestion
crossbridge memory ingest --source discovery.json
```

#### 2. "Dimension mismatch"

**Cause:** Embedding model dimension doesn't match vector store

**Fix:**
```yaml
# Ensure these match:
embedding_provider:
  model: text-embedding-3-large  # 3072 dimensions

vector_store:
  dimension: 3072  # Must match!
```

#### 3. "pgvector extension not found"

**Cause:** pgvector not installed in PostgreSQL

**Fix:**
```bash
# Install pgvector (Ubuntu)
sudo apt install postgresql-15-pgvector

# Or using Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password ankane/pgvector
```

#### 4. "Search returns no results"

**Cause:** Query embedding doesn't match any records

**Fix:**
```bash
# Lower similarity threshold
crossbridge search query "your query" --min-score 0.3

# Check if records exist
crossbridge memory stats
```

---

## Best Practices

### 1. Entity Granularity

✅ **Do:**
- Embed individual tests, scenarios, steps
- Include rich metadata (framework, tags, intent)
- Use descriptive test names

❌ **Don't:**
- Embed entire test files
- Store raw code without context
- Skip metadata

### 2. Memory Lifecycle

✅ **Do:**
- Set appropriate TTL (30-90 days)
- Clean up old records regularly
- Re-embed when tests change

❌ **Don't:**
- Store embeddings forever
- Forget to update on code changes
- Keep failed/deleted tests

### 3. Search Strategies

✅ **Do:**
- Use natural language queries
- Leverage metadata filters
- Start with high similarity thresholds (0.7+)

❌ **Don't:**
- Use keyword-only queries
- Ignore low scores (< 0.5)
- Over-rely on exact matches

---

## API Reference

See [Memory API Documentation](./MEMORY_API.md) for complete API reference.

---

## Next Steps

1. ✅ **Setup**: Configure `crossbridge.yml` and run `setup_memory_db.py`
2. ✅ **Ingest**: Run `crossbridge memory ingest`
3. ✅ **Search**: Try `crossbridge search query "your query"`
4. ✅ **Integrate**: Use memory in AI features

For more examples, see:
- [Memory Quick Start Guide](./MEMORY_QUICK_START.md)
- [Semantic Search Examples](./SEMANTIC_SEARCH_EXAMPLES.md)
- [AI Integration Guide](./AI_INTEGRATION.md)
