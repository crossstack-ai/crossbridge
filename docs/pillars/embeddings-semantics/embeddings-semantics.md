# Embeddings & Semantics

> **Semantic understanding of test intent, behavior, and relationships**

CrossBridge AI uses embeddings and semantic analysis to understand what tests actually do, not just their structure.

---

## 🎯 What Are Embeddings?

**Embeddings** are vector representations of text that capture semantic meaning:

```
"test_login_timeout" → [0.23, -0.45, 0.67, ...] (768-3072 dimensions)
"test_authentication_timeout" → [0.25, -0.43, 0.69, ...] (similar vector!)
```

**Why it matters**:
- Find tests by **intent**, not keywords
- Detect **duplicate** tests with different names
- Understand **functional relationships** between tests
- Enable **natural language** search

---

## 🔍 Semantic Search

Search tests using natural language queries:

```bash
# Traditional keyword search (limited)
grep "timeout" tests/*.py

# Semantic search (intelligent)
crossbridge semantic search "tests covering login timeout handling"
```

**Results**:
```
1. test_login_timeout (similarity: 0.92)
2. test_auth_timeout_handling (similarity: 0.87)
3. test_session_timeout_recovery (similarity: 0.79)
4. test_connection_timeout (similarity: 0.65)
```

**Use cases**:
- "Find all payment-related tests"
- "Show tests that validate error messages"
- "Which tests cover database connections?"
- "Tests handling race conditions"

---

## 🔄 Duplicate Test Detection

Automatically identify redundant test coverage:

**Similarity Thresholds**:
- **>0.9**: Likely duplicates (same functionality, different names)
- **0.7-0.9**: Related tests (overlapping coverage)
- **0.5-0.7**: Complementary tests (same area, different aspects)
- **<0.5**: Unrelated tests

**Usage**:
```bash
# Find similar tests
crossbridge semantic similar test_user_login

# Results:
# test_login_valid (0.95) - DUPLICATE
# test_successful_authentication (0.92) - DUPLICATE
# test_login_with_valid_credentials (0.88) - RELATED
```

**Benefits**:
- Reduce test maintenance burden
- Identify consolidation opportunities
- Understand test coverage overlaps
- Optimize test suites

---

## 📊 Clustering & Grouping

Automatically group related tests by functional area:

**DBSCAN Clustering**:
- Minimum cluster size: 3 tests
- Distance metric: Cosine similarity
- Automatic outlier detection

**Example clusters**:
```
Cluster 1: Authentication (15 tests)
  - test_login_valid
  - test_login_invalid
  - test_password_reset
  - ...

Cluster 2: Payment Processing (23 tests)
  - test_checkout_flow
  - test_payment_validation
  - test_refund_processing
  - ...

Cluster 3: Search Functionality (8 tests)
  - test_basic_search
  - test_advanced_filters
  - ...
```

**Use cases**:
- Organize unstructured test suites
- Understand test coverage by feature
- Identify under-tested areas
- Plan test maintenance work

---

## 🧠 Unified Test Memory

CrossBridge maintains a semantic memory of all tests:

### Architecture

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Test Files        │         │  Normalization   │         │  UnifiedTestMemory  │
│  (All Frameworks)   │────────▶│  + AST Extract   │────────▶│  + Structural Sigs  │
└─────────────────────┘         └──────────────────┘         └──────────┬──────────┘
                                                                          │
                                                                          ▼
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Similar Tests     │         │   Embedding API  │         │   Text Builder      │
│  + Recommendations  │◀────────│  Vector Search   │◀────────│  (Domain Context)   │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

### Entity Types

| Type | Example | Use Case |
|------|---------|----------|
| `test` | `LoginTest.testValidLogin` | Find tests by behavior |
| `scenario` | `Scenario: Valid Login` | BDD scenario search |
| `step` | `When user enters credentials` | Step definition lookup |
| `page` | `LoginPage.login()` | Page object discovery |
| `failure` | `TimeoutException during login` | Failure pattern matching |

---

## 🔌 Embedding Providers

CrossBridge supports multiple embedding providers:

### OpenAI (Recommended for Production)

**text-embedding-3-large**:
- Dimensions: 3072
- Cost: $0.13 per 1M tokens
- Quality: Highest accuracy
- Use case: Production deployments

**text-embedding-3-small**:
- Dimensions: 1536
- Cost: $0.02 per 1M tokens
- Quality: Good balance
- Use case: Cost-sensitive workloads

### Anthropic (Voyage AI)

**voyage-large-2**:
- Dimensions: 1536
- Cost: $0.12 per 1M tokens
- Quality: High accuracy
- Use case: Alternative to OpenAI

### Ollama (Local, Free)

**nomic-embed-text**:
- Dimensions: 768
- Cost: Free
- Quality: Good for local use
- Use case: Offline, privacy-sensitive

### HuggingFace (Local, Free)

**all-MiniLM-L6-v2**:
- Dimensions: 384
- Cost: Free
- Quality: Adequate
- Use case: Air-gapped environments

---

## 💾 Vector Storage

### PostgreSQL + pgvector (Production)

**Setup**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE test_embeddings (
    id SERIAL PRIMARY KEY,
    test_name TEXT,
    embedding vector(3072),
    metadata JSONB
);

CREATE INDEX ON test_embeddings 
USING ivfflat (embedding vector_cosine_ops);
```

**Benefits**:
- Production-grade reliability
- ACID transactions
- Integrated with existing DB
- Scalable to millions of tests

### FAISS (Local Development)

**Setup**:
```python
import faiss

index = faiss.IndexFlatL2(3072)
index.add(embeddings)
```

**Benefits**:
- Fast local development
- No database required
- In-memory performance
- Easy experimentation

---

## 📈 Performance & Costs

### Embedding Generation

**Cost Example** (OpenAI text-embedding-3-large):
```
1,000 tests @ ~100 tokens each = 100K tokens
Cost: $0.013 (less than 2 cents!)

10,000 tests = 1M tokens
Cost: $0.13 (13 cents)
```

**Performance**:
- Embedding latency: 50-200ms per batch
- Batch size: 50-100 tests
- Throughput: ~500 tests/second

### Search Performance

**Vector similarity search**:
- Latency: <100ms for 100K tests
- Accuracy: 95%+ for top-10 results
- Memory: ~12MB per 1000 tests (3072 dim)

---

## 🛠️ Configuration

### Basic Setup

```yaml
# crossbridge.yml
memory:
  enabled: true
  embedding:
    provider: openai  # or anthropic, ollama, huggingface
    model: text-embedding-3-large
    dimensions: 3072
  
  vector_store:
    type: postgres  # or faiss
    postgres:
      host: localhost
      database: crossbridge
      table: test_embeddings
```

### Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic (Voyage AI)
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama (local server)
export OLLAMA_HOST="http://localhost:11434"
```

---

## 🚀 Usage Examples

### Index Tests

```bash
# Discover and index tests
crossbridge discover --framework pytest --output discovery.json
crossbridge memory ingest --source discovery.json

# Verify indexing
crossbridge memory stats
# Output: 1,245 tests indexed, 3,735 entities total
```

### Semantic Search

```bash
# Natural language query
crossbridge search query "authentication timeout tests"

# Filter by framework
crossbridge search query "database connection tests" --framework pytest

# Get explanations
crossbridge search query "flaky tests" --explain
```

### Duplicate Detection

```bash
# Find duplicates (>0.9 similarity)
crossbridge search duplicates --threshold 0.9

# Output:
# Found 12 duplicate pairs:
# 1. test_login_valid ↔ test_successful_login (0.95)
# 2. test_checkout_flow ↔ test_complete_purchase (0.92)
```

### Clustering

```bash
# Auto-cluster tests by functional area
crossbridge search cluster --min-cluster-size 5

# Output:
# Found 8 clusters:
# - Authentication (15 tests)
# - Payment (23 tests)
# - Search (8 tests)
```

---

## 🎯 Best Practices

### When to Use Embeddings

✅ **Good use cases**:
- Finding tests by intent/behavior
- Detecting duplicate coverage
- Understanding test relationships
- Natural language search
- Coverage gap analysis

❌ **Not ideal for**:
- Exact string matching (use grep)
- File path searches (use find)
- Simple keyword lookups
- Real-time search (<10ms latency required)

### Cost Optimization

**Strategies**:
1. Use text-embedding-3-small for development
2. Batch embedding generation
3. Cache embeddings with versioning
4. Use local providers (Ollama) for CI/CD
5. Incremental updates (don't re-embed unchanged tests)

### Quality Tips

**Improve embedding quality**:
- Include test names, docstrings, and comments
- Add structural signals (API calls, assertions)
- Use domain-specific context
- Regular re-indexing (weekly/monthly)

---

## 📚 Technical Details

### AST Extraction

CrossBridge extracts structural signals from test code:

**Python (pytest)**:
```python
def test_login_timeout():
    """Test login with timeout handling"""
    response = requests.post("/api/login", timeout=5)  # API call detected
    assert response.status_code == 200  # Assertion detected
```

**Extracted signals**:
- API call: `POST /api/login`
- Assertion: `status_code == 200`
- Intent: "login with timeout handling"

**Java (JUnit)**:
```java
@Test
public void testCheckoutFlow() {
    driver.findElement(By.id("checkout-btn")).click();  // UI interaction
    assertEquals(200, response.getStatus());  // Assertion
}
```

**Extracted signals**:
- UI interaction: `click checkout-btn`
- Assertion: `status == 200`
- Intent: "checkout flow validation"

### Text Building for Embeddings

CrossBridge builds rich text representations:

```
Test Name: test_login_timeout
Type: unit_test
Framework: pytest
Description: Test login with timeout handling
Interactions: API POST /api/login
Assertions: status_code equals 200
Tags: smoke, authentication
File: tests/test_auth.py
```

This rich context improves semantic understanding.

---

## 🔬 Advanced Features

### Version Tracking

Embeddings are versioned to support model changes:

```sql
SELECT test_name, embedding_version, created_at
FROM test_embeddings
WHERE embedding_version = 'text-embedding-3-large';
```

### Multi-Language Support

Embeddings work across programming languages:
- Python ↔ Java similarity detection
- BDD scenarios ↔ API tests correlation
- Legacy ↔ Modern framework mapping

### Hybrid Search

Combine semantic and keyword search:

```python
# Semantic search
semantic_results = search.semantic("authentication tests")

# Keyword filter
filtered = [r for r in semantic_results if "timeout" in r.name]
```

---

## 📖 Learn More

- [Semantic Engine Guide](../../SEMANTIC_ENGINE.md) - Full architecture
- [Quick Start](../../ai/SEMANTIC_SEARCH_QUICK_START.md) - Setup guide
- [Memory System](memory/) - Implementation details
- [Configuration](../../configuration/UNIFIED_CONFIGURATION_GUIDE.md) - Settings

---

**Ready to enable semantic search?** Follow the [quick start guide](../../ai/SEMANTIC_SEARCH_QUICK_START.md).
