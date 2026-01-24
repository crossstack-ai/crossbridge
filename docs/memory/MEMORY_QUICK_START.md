# Memory & Embeddings System - Quick Start Guide

Get started with CrossBridge's semantic search in **5 minutes**.

---

## Prerequisites

- ✅ PostgreSQL with pgvector extension
- ✅ OpenAI API key (or local Ollama setup)
- ✅ CrossBridge installed

---

## Step 1: Configure `crossbridge.yml`

Add memory configuration:

```yaml
memory:
  enabled: true
  
  embedding_provider:
    type: openai
    model: text-embedding-3-small  # Faster, cheaper option
    api_key: ${OPENAI_API_KEY}
  
  vector_store:
    type: pgvector
    connection_string: postgresql://postgres:password@localhost:5432/crossbridge
    dimension: 1536  # For text-embedding-3-small
```

---

## Step 2: Set Environment Variables

```bash
# OpenAI API Key
export OPENAI_API_KEY=sk-your-key-here

# Or use local Ollama (no API key needed)
# brew install ollama
# ollama pull nomic-embed-text
```

---

## Step 3: Setup Database

```bash
# Run setup script
python scripts/setup_memory_db.py

# Or manually:
python scripts/setup_memory_db.py --connection "postgresql://postgres:password@localhost:5432/crossbridge" --dimension 1536
```

**Expected Output:**
```
INFO:root:Setting up memory schema...
INFO:root:Enabling pgvector extension...
INFO:root:Creating memory_embeddings table (dimension=1536)...
INFO:root:Creating indexes...
INFO:root:Creating HNSW vector index...
INFO:root:✅ Memory schema setup complete!
INFO:root:📊 Current records: 0
```

---

## Step 4: Discover and Ingest Tests

```bash
# Discover tests and save to JSON
crossbridge discover --framework pytest --output discovery.json

# Ingest into memory system
crossbridge memory ingest --source discovery.json
```

**Expected Output:**
```
🔄 Starting memory ingestion...

Ingestion Results
┌─────────────┬────────┐
│ Entity Type │ Count  │
├─────────────┼────────┤
│ tests       │ 150    │
│ scenarios   │ 45     │
│ steps       │ 380    │
└─────────────┴────────┘

✅ Successfully ingested 575 records
```

---

## Step 5: Try Semantic Search

```bash
# Search for tests
crossbridge search query "tests covering login timeout"

# Find similar tests
crossbridge search similar test_login_valid

# Check stats
crossbridge memory stats
```

**Example Output:**
```
🔍 Searching for: "tests covering login timeout"

┌────────────────────────────────────────────────────────────┐
│              Search Results (3 found)                       │
├────┬────────┬─────────────────────┬───────┬───────────────┤
│ #  │ Type   │ ID                  │ Score │ Preview       │
├────┼────────┼─────────────────────┼───────┼───────────────┤
│ 1  │ test   │ test_login_timeout  │ 0.923 │ Test verifies │
│ 2  │ scen.  │ login_timeout_scen  │ 0.876 │ Scenario: Log │
│ 3  │ test   │ test_auth_timeout   │ 0.845 │ Test handles  │
└────┴────────┴─────────────────────┴───────┴───────────────┘
```

---

## Common Use Cases

### 1. Find Tests by Intent

```bash
crossbridge search query "tests that verify error handling"
```

### 2. Detect Duplicates

```bash
crossbridge search similar test_login_valid --top 10

# High similarity (>0.9) = potential duplicate
```

### 3. Find Related Tests

```bash
crossbridge search query "authentication tests" --framework pytest
```

### 4. Filter by Entity Type

```bash
# Only search scenarios
crossbridge search query "checkout flow" --type scenario

# Only search page objects
crossbridge search query "login form" --type page
```

---

## Programmatic Usage

```python
from core.memory import (
    MemoryIngestionPipeline,
    SemanticSearchEngine,
    create_embedding_provider,
    create_vector_store,
)

# Setup
provider = create_embedding_provider('openai', model='text-embedding-3-small')
store = create_vector_store('pgvector', 
    connection_string='postgresql://...',
    dimension=1536
)

# Search
engine = SemanticSearchEngine(provider, store)
results = engine.search("login timeout tests", top_k=5)

for result in results:
    print(f"{result.rank}. {result.record.id} - {result.score:.3f}")
```

---

## Troubleshooting

### "pgvector extension not found"

```bash
# Install pgvector (Ubuntu/Debian)
sudo apt install postgresql-15-pgvector

# Or use Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password ankane/pgvector
```

### "No OpenAI API key found"

```bash
export OPENAI_API_KEY=sk-your-key-here

# Or switch to local embeddings (Ollama)
# Edit crossbridge.yml:
# embedding_provider:
#   type: local
#   model: nomic-embed-text
```

### "Dimension mismatch"

Ensure embedding model dimension matches vector store:

| Model | Dimension |
|-------|-----------|
| text-embedding-3-large | 3072 |
| text-embedding-3-small | 1536 |
| text-embedding-ada-002 | 1536 |
| nomic-embed-text | 768 |

---

## Next Steps

- 📖 Read [Complete Documentation](./MEMORY_EMBEDDINGS_SYSTEM.md)
- 🔍 See [Search Examples](./SEMANTIC_SEARCH_EXAMPLES.md)
- 🤖 Learn [AI Integration](./AI_INTEGRATION.md)
- 🛠️ Check [API Reference](./MEMORY_API.md)

---

## Cost Estimation

**OpenAI Pricing (as of 2024):**

- `text-embedding-3-small`: **$0.02 per 1M tokens**
- `text-embedding-3-large`: **$0.13 per 1M tokens**

**Example:**
- 1,000 tests @ ~100 tokens each = 100K tokens
- Cost: **$0.002 - $0.013** (less than a penny!)

**Local Options (Free):**
- Ollama + nomic-embed-text
- HuggingFace sentence-transformers
- No API costs, fully private

---

## Support

- 💬 GitHub Discussions: [github.com/crossbridge/discussions](https://github.com/crossbridge/discussions)
- 🐛 Issues: [github.com/crossbridge/issues](https://github.com/crossbridge/issues)
- 📧 Email: support@crossbridge.dev
