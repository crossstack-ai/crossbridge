# AI Semantic Engine

## Overview

The AI Semantic Engine provides CrossBridge with advanced semantic intelligence capabilities:

**Framework Compatibility:** Works seamlessly with all 13 CrossBridge frameworks:
- **Python:** pytest, selenium_pytest, selenium_behave, behave
- **JavaScript/TypeScript:** Cypress, Playwright
- **Java:** JUnit, TestNG, selenium_java, restassured_java, selenium_bdd_java, Cucumber
- **.NET:** NUnit, SpecFlow
- **Multi-language:** Robot Framework

The semantic engine is framework-agnostic and operates on normalized test representations.

- **Semantic Search**: Natural language search across tests, scenarios, and failures
- **Duplicate Detection**: Automatic identification of duplicate test cases
- **Clustering**: Grouping similar entities for analysis
- **Smart Test Selection**: AI-powered test selection for code changes

## Architecture

```
Extractors (Test/Scenario/Failure)
        ↓
Text Builder (Deterministic, Labeled)
        ↓
Embedding Provider (OpenAI/Anthropic/Local)
        ↓
Vector Store (pgvector/FAISS)
        ↓
Semantic Engine
  ├─ Semantic Search (confidence calibrated)
  ├─ Duplicate Detection (clustering-based)
  └─ Smart Test Selection (multi-signal scoring)
```

## Key Principles

1. **No Raw Code Embeddings**: Always use deterministic, labeled text
2. **Versioned Embeddings**: Track versions for reindexing
3. **Confidence Calibration**: Never trust raw scores
4. **Explainability**: Every result must explain itself
5. **Multi-Signal Decisions**: Combine semantic + coverage + history
6. **Provider Agnostic**: Support multiple embedding providers

## Components

### 1. Embedding Pipeline

**Text Builder** (`core/ai/embeddings/text_builder.py`)
- Deterministic text construction for tests, scenarios, failures
- AST augmentation support
- Framework-agnostic normalization

**Embedding Providers** (`core/ai/embeddings/provider.py`)
- OpenAI (text-embedding-3-large, 3072 dimensions)
- Anthropic (future)
- HuggingFace (local)
- Mock (testing)

**Version Management** (`core/ai/embeddings/embedding_version.py`)
- Current version: `v2-text+ast`
- Automatic reindexing detection
- Version compatibility checks

### 2. Vector Store Abstraction

**Interface** (`core/ai/embeddings/vector_store.py`)
```python
class VectorStore(ABC):
    def upsert(entity, embedding, model, version): ...
    def similarity_search(query_embedding, top_k, filters): ...
    def get(entity_id): ...
    def delete(entity_id): ...
```

**Implementations**:
- **PgVector** (`core/ai/embeddings/pgvector_store.py`) - Production (PostgreSQL)
- **FAISS** (`core/ai/embeddings/faiss_store.py`) - Local/high-performance

### 3. Semantic Search Service

**API** (`core/ai/semantic/semantic_search_service.py`)
```python
service.search(
    query_text="user authentication tests",
    entity_type="test",
    top_k=10,
    min_confidence=0.5,
    intent=SearchIntent.FIND_SIMILAR_TESTS
)
```

**Features**:
- Intent-aware search (duplicates, failures, impacts)
- Confidence calibration: `score * log1p(samples) / log1p(30)`
- Explainable results (every result has reasons)
- Filter by entity type, metadata

### 4. Duplicate Detection

**API** (`core/ai/semantic/duplicate_detection.py`)
```python
detector.find_duplicates(
    entity_id="test_login",
    entity_text="Test user login functionality",
    entity_type="test"
)
```

**Duplicate Criteria** (from spec):
- Similarity >= 0.9
- Confidence >= 0.8

**Types**:
- EXACT: score >= 0.95
- VERY_SIMILAR: score >= 0.9
- SIMILAR: score >= 0.8
- POTENTIALLY_SIMILAR: score >= 0.7

### 5. Clustering Engine

**API** (`core/ai/semantic/duplicate_detection.py`)
```python
engine.cluster_entities(
    entity_ids=["test_1", "test_2", ...],
    entity_type="test",
    min_cluster_size=3,
    eps=0.3
)
```

**Algorithm**: DBSCAN (density-based, no labels required)

**Cluster Output**:
- cluster_id
- members (entity IDs)
- centroid (average embedding)
- confidence (cohesion score)

### 6. Smart Test Selection

**API** (`core/ai/semantic/smart_test_selection.py`)
```python
selector.select_tests(
    change_context=ChangeContext(
        change_id="commit_abc123",
        files_changed=["auth/login.py"],
        diff_summary="Added 2FA support"
    ),
    budget=20,
    min_score=0.5
)
```

**Scoring Formula** (from spec):
```
selection_score = 
  0.4 * semantic_similarity +
  0.3 * coverage_relevance +
  0.2 * failure_history -
  0.1 * flakiness_penalty
```

**Every Test Explains**:
```json
{
  "test_id": "test_login_2fa",
  "score": 0.85,
  "confidence": 0.82,
  "reasons": [
    "High semantic similarity to changed code (0.87)",
    "Covers modified authentication flow",
    "Previously failed with similar changes",
    "High confidence based on robust evidence"
  ]
}
```

## Configuration

### Enable Semantic Engine

**crossbridge.yml**:
```yaml
ai:
  semantic_engine:
    enabled: true
    
    embedding:
      provider: openai
      model: text-embedding-3-large
      version: v2-text+ast
      ast_augmentation: true
    
    vector_store:
      type: pgvector  # or 'faiss'
      distance_metric: cosine
    
    search:
      default_top_k: 10
      min_confidence: 0.5
    
    duplicate_detection:
      similarity_threshold: 0.9
      confidence_threshold: 0.8
    
    test_selection:
      weights:
        semantic_similarity: 0.4
        coverage_relevance: 0.3
        failure_history: 0.2
        flakiness_penalty: 0.1
```

### Environment Variables

```bash
export OPENAI_API_KEY=sk-...
export CROSSBRIDGE_SEMANTIC_ENABLED=true
```

## Usage Examples

### 1. Semantic Search

```python
from core.ai.semantic import (
    create_semantic_search_service,
    SearchIntent
)
from core.ai.embeddings.provider import OpenAIEmbeddingProvider
from core.ai.embeddings.pgvector_store import PgVectorStore

# Create service
embedding_provider = OpenAIEmbeddingProvider(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="text-embedding-3-large"
)
vector_store = PgVectorStore(connection_string="postgresql://...")

service = create_semantic_search_service(
    embedding_provider=embedding_provider,
    vector_store=vector_store
)

# Search for similar tests
results = service.search(
    query_text="user authentication and login",
    entity_type="test",
    top_k=10,
    intent=SearchIntent.FIND_SIMILAR_TESTS
)

for result in results:
    print(f"Test: {result.entity_id}")
    print(f"Score: {result.score:.3f}, Confidence: {result.confidence:.3f}")
    print(f"Reasons: {', '.join(result.reasons)}")
```

### 2. Find Duplicates

```python
from core.ai.semantic import DuplicateDetector

detector = DuplicateDetector(
    semantic_search=service,
    similarity_threshold=0.9,
    confidence_threshold=0.8
)

duplicates = detector.find_duplicates(
    entity_id="test_login_user",
    entity_text="Test successful user login with valid credentials",
    entity_type="test"
)

for dup in duplicates:
    print(f"Duplicate: {dup.entity_id_1} <-> {dup.entity_id_2}")
    print(f"Type: {dup.duplicate_type.value}")
    print(f"Score: {dup.similarity_score:.3f}")
    print(f"Reasons: {', '.join(dup.reasons)}")
```

### 3. Smart Test Selection

```python
from core.ai.semantic import SmartTestSelector, ChangeContext

selector = SmartTestSelector(
    semantic_search=service,
    coverage_service=coverage_svc,  # Optional
    failure_history_service=history_svc,  # Optional
    flaky_detection_service=flaky_svc  # Optional
)

# Define code change
change = ChangeContext(
    change_id="commit_abc123",
    files_changed=["src/auth/login.py", "src/auth/session.py"],
    diff_summary="Added two-factor authentication to login flow",
    functions_changed=["login", "verify_2fa", "create_session"],
    modules_changed=["auth"]
)

# Select tests
selected_tests = selector.select_tests(
    change_context=change,
    budget=20,
    min_score=0.5,
    include_flaky=False
)

for test in selected_tests:
    print(f"\nTest: {test.test_name}")
    print(f"Score: {test.score:.3f} (confidence: {test.confidence:.3f})")
    print(f"Priority: {test.priority}")
    print(f"Signal Breakdown:")
    print(f"  - Semantic: {test.semantic_score:.3f}")
    print(f"  - Coverage: {test.coverage_score:.3f}")
    print(f"  - Failure History: {test.failure_score:.3f}")
    print(f"  - Flakiness: {test.flakiness_score:.3f}")
    print(f"Reasons:")
    for reason in test.reasons:
        print(f"  - {reason}")
```

### 4. Clustering

```python
from core.ai.semantic import ClusteringEngine

engine = ClusteringEngine(
    vector_store=vector_store,
    embedding_provider=embedding_provider,
    algorithm="dbscan"
)

clusters = engine.cluster_entities(
    entity_ids=["test_1", "test_2", "test_3", ...],
    entity_type="test",
    min_cluster_size=3,
    eps=0.3
)

for cluster in clusters:
    print(f"\nCluster: {cluster.cluster_id}")
    print(f"Size: {cluster.size}, Confidence: {cluster.confidence:.3f}")
    print(f"Members: {', '.join(cluster.members[:5])}...")
```

## CLI Commands

### Index Tests for Semantic Search

```bash
# Index all tests in workspace
crossbridge semantic index \
  --workspace ./tests \
  --framework pytest \
  --output ./data/vectors

# Index specific test files
crossbridge semantic index \
  --files tests/test_auth.py tests/test_api.py
```

### Search Tests

```bash
# Search for similar tests
crossbridge semantic search \
  --query "user authentication and login" \
  --top-k 10 \
  --type test

# Search with intent
crossbridge semantic search \
  --query "timeout failures" \
  --type failure \
  --intent find_duplicates
```

### Find Duplicates

```bash
# Find all duplicates
crossbridge semantic duplicates \
  --workspace ./tests \
  --threshold 0.9

# Find duplicates for specific test
crossbridge semantic duplicates \
  --test-id test_login_user \
  --threshold 0.9
```

### Smart Test Selection

```bash
# Select tests for code change
crossbridge semantic select \
  --change-id commit_abc123 \
  --files "src/auth/*.py" \
  --diff-summary "Added 2FA support" \
  --budget 20

# With filters
crossbridge semantic select \
  --change-id commit_abc123 \
  --min-score 0.5 \
  --exclude-flaky \
  --priority high
```

## Performance

### Embedding Generation
- **OpenAI text-embedding-3-large**: ~100ms per request, ~8000 tokens/request
- **Batch**: 100 texts in ~5 seconds
- **Cost**: $0.00013 per 1K tokens (~$0.01 per 100 tests)

### Vector Search
- **PgVector**: <10ms for 10K vectors, <50ms for 1M vectors
- **FAISS**: <1ms for 10K vectors, <10ms for 1M vectors
- **Memory**: ~12KB per vector (3072 dimensions * 4 bytes)

### Smart Test Selection
- **Typical**: 200ms for 10K tests (includes semantic + scoring)
- **With Coverage**: +50ms (coverage mapping lookup)
- **With History**: +30ms (historical failure queries)

## Testing

Run Phase-2 tests:
```bash
# All semantic engine tests
pytest tests/unit/ai/test_phase2_semantic_engine.py -v

# Specific test categories
pytest tests/unit/ai/test_phase2_semantic_engine.py::TestSemanticSearchService -v
pytest tests/unit/ai/test_phase2_semantic_engine.py::TestDuplicateDetector -v
pytest tests/unit/ai/test_phase2_semantic_engine.py::TestSmartTestSelector -v
```

## Migration Guide

### From Existing Semantic Search

If you have existing semantic search:

1. **Update Text Builders**: Add AST augmentation
2. **Reindex Embeddings**: Use new v2-text+ast version
3. **Update Queries**: Use new SemanticSearchService API
4. **Enable Confidence**: Add min_confidence filters

### Reindexing

```python
from core.ai.embeddings.embedding_version import is_version_deprecated

# Check if reindexing needed
for entity in entities:
    if is_version_deprecated(entity.embedding_version):
        # Reindex this entity
        new_embedding = provider.embed(text_builder.build_text(entity))
        vector_store.upsert(entity, new_embedding, model, EMBEDDING_VERSION)
```

## Troubleshooting

### Low Confidence Scores

**Symptom**: All results have confidence < 0.3

**Cause**: Not enough sample data for calibration

**Solution**: 
- Lower min_confidence threshold
- Add more entities to vector store
- Check if embeddings are indexed correctly

### Duplicate Detection Missing Duplicates

**Symptom**: Known duplicates not detected

**Cause**: Thresholds too strict or text differences

**Solution**:
- Lower similarity_threshold to 0.85
- Check text builder output for consistency
- Verify entities are using same embedding version

### Smart Test Selection Poor Results

**Symptom**: Selected tests not relevant to changes

**Cause**: Missing signals (coverage, history)

**Solution**:
- Enable coverage_service for better results
- Add failure_history_service for pattern matching
- Check ChangeContext has detailed information
- Verify semantic_similarity weight is appropriate

## Best Practices

1. **Version All Embeddings**: Always store version with vectors
2. **Calibrate Confidence**: Never use raw similarity scores
3. **Explain Results**: Include reasons in all outputs
4. **Multi-Signal Scoring**: Don't rely on semantic similarity alone
5. **Monitor Performance**: Track embedding costs and latency
6. **Cache Aggressively**: Cache search results for repeated queries
7. **Batch Operations**: Batch embed when indexing large datasets
8. **Test Reindexing**: Have reindexing strategy before production

## Roadmap

### Phase-2.1 (Current)
- ✅ Embedding pipeline with versioning
- ✅ Semantic search with confidence
- ✅ Duplicate detection
- ✅ Smart test selection

### Phase-2.2 (Next)
- [ ] Advanced clustering (HDBSCAN)
- [ ] Multi-modal embeddings (code + text)
- [ ] Fine-tuned embedding models
- [ ] Real-time indexing

### Phase-2.3 (Future)
- [ ] Graph-based relationships
- [ ] Temporal evolution tracking
- [ ] Cross-repository search
- [ ] Federation across teams

## References

- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [PgVector](https://github.com/pgvector/pgvector)
- [FAISS](https://github.com/facebookresearch/faiss)
- [DBSCAN Clustering](https://scikit-learn.org/stable/modules/clustering.html#dbscan)

## Support

For issues or questions:
- GitHub Issues: https://github.com/crossstack/crossbridge/issues
- Documentation: https://docs.crossbridge.ai/semantic-engine
- Email: support@crossstack.ai
