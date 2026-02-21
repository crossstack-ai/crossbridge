# AI and Semantic Search Modes in CrossBridge CLI

CrossBridge supports both AI-powered and deterministic (no-AI) operation modes for all supported frameworks and CLI commands.

## How It Works

- **AI/semantic features enabled:**
  - Set `ai.enabled: true` and `semantic_search.enabled: true` in your `crossbridge.yml`.
  - All semantic search, duplicate detection, and embedding features are available.
  - CLI commands like `search query`, `search duplicates`, and `search similar` will use the configured AI provider (OpenAI, local, etc.).

- **AI/semantic features disabled:**
  - Set `ai.enabled: false` or `semantic_search.enabled: false` in your `crossbridge.yml`.
  - CLI commands that require AI/semantic features will print a friendly message and exit gracefully.
  - All other CLI features (ingestion, stats, log parsing, etc.) continue to work as before.

## Authentication and Credential Priority

CrossBridge prioritizes AI credentials in the following order:

### Priority 1: Cached Credentials (Recommended)

Use the `crossbridge auth login` command to cache credentials securely:

```bash
# For self-hosted/Ollama (use embedding-specific models)
crossbridge auth login --provider selfhosted \
    --url http://localhost:11434 \
    --model nomic-embed-text

# Other supported Ollama embedding models:
# - nomic-embed-text (recommended, 768 dimensions)
# - mxbai-embed-large (1024 dimensions)
# - all-minilm (384 dimensions)
# Note: Text generation models like deepseek-coder or llama cannot be used for embeddings

# For OpenAI
crossbridge auth login --provider openai \
    --token YOUR_OPENAI_API_KEY

# For Anthropic
crossbridge auth login --provider anthropic \
    --token YOUR_ANTHROPIC_API_KEY
```

**Important:** Ollama's embedding endpoint requires embedding-specific models. Text generation models (e.g., `deepseek-coder`, `llama3`, `mistral`) cannot generate embeddings. Pull an embedding model first:

```bash
# Pull an embedding model
ollama pull nomic-embed-text
```

Cached credentials are stored securely and take priority over config file settings.

### Priority 2: Config File

If no cached credentials are found, CrossBridge falls back to the `crossbridge.yml` configuration:

```yaml
crossbridge:
  ai:
    enabled: true
    semantic_engine:
      embedding:
        provider: local  # or "openai", "anthropic"
        model: nomic-embed-text  # For Ollama: use embedding-specific models
        api_key: your-api-key  # optional, for OpenAI/Anthropic
      vector_store:
        type: faiss  # Default: FAISS (no database required)
        storage_path: ./faiss_index  # Optional: where to persist FAISS index
        # For PostgreSQL with pgvector extension:
        # type: pgvector
        # connection_string: postgresql://user:pass@localhost/dbname
    ollama:
      base_url: http://localhost:11434
      model: nomic-embed-text  # Must be an embedding model, not a text generation model
  semantic_search:
    enabled: true
```

### Vector Store Configuration

CrossBridge supports two vector store backends:

**FAISS (Default - Recommended)**
- No external database required
- Fast in-memory similarity search
- Optional persistence to disk
- Ideal for local development and testing

```yaml
crossbridge:
  ai:
    semantic_engine:
      vector_store:
        type: faiss
        storage_path: ./faiss_index  # Optional
```

**PostgreSQL with pgvector**
- Production-grade persistent storage
- Requires PostgreSQL 12+ with pgvector extension
- Supports distributed/shared vector storage

```yaml
crossbridge:
  ai:
    semantic_engine:
      vector_store:
        type: pgvector
        connection_string: postgresql://user:pass@localhost:5432/crossbridge
```

**Note:** If `pgvector` is specified but no `connection_string` is provided, CrossBridge automatically falls back to FAISS.

### Checking Cached Credentials

To view your cached credentials:

```bash
crossbridge auth list
```

This will show all configured AI providers, including self-hosted endpoints, models, and authentication status.

### Why Cached Credentials?

- **Security:** Credentials are not stored in plain text config files
- **Flexibility:** Switch between providers without editing config files
- **Portability:** Works across different environments and CI/CD systems
- **Priority:** Cached credentials always override config file settings

## Example Configuration

```yaml
crossbridge:
  ai:
    enabled: false  # disables all AI features
  semantic_engine:
    enabled: false  # disables semantic search/embedding
```

## CLI Behavior

- If you run a semantic command (e.g., `crossbridge search duplicates`) with AI/semantic disabled, you will see:

```
AI and/or semantic search features are disabled in your configuration. To enable semantic search, set ai.enabled: true and semantic_search.enabled: true in crossbridge.yml.
```

- All output and warnings are logged using the CrossBridge logger for traceability.

## Sidecar Log Forwarding 🆕

When running CLI commands with a sidecar configured, AI operation logs are automatically forwarded to the sidecar for centralized visibility.

### Configuration

Set environment variables to enable sidecar log forwarding:

```bash
export CROSSBRIDGE_API_HOST=localhost  # Your sidecar hostname
export CROSSBRIDGE_API_PORT=8765        # Sidecar API port (default: 8765)
```

### How It Works

1. **Auto-Detection**: CrossBridge CLI automatically detects if a sidecar is available by checking `CROSSBRIDGE_API_HOST`
2. **Health Check**: Validates sidecar is reachable via `/health` endpoint
3. **Non-Blocking**: Log forwarding happens in background threads, never blocks CLI operations
4. **Selective:** Only forwards INFO+ level logs from AI and CLI categories
5. **Fail-Safe**: If sidecar becomes unavailable, forwarding automatically disables after 3 failures

### What Gets Forwarded

✅ **AI Operations:**
```
INFO | [CLI:ai] HTTP Request: POST http://10.60.75.145:11434/api/embeddings (model='nomic-embed-text', text_length=150)
INFO | [CLI:ai] Generated 45 embeddings using local model 'nomic-embed-text'
```

✅ **CLI Commands:**
```
INFO | [CLI:cli] Found 8 potential duplicates (threshold=0.95)
INFO | [CLI:cli] Search completed in 2.3s
```

❌ **Not Forwarded:**
- DEBUG level logs (too verbose)
- Adapter/framework execution logs (test-specific)
- General application logs

### Example: Viewing Sidecar Logs

```bash
# Start sidecar
docker-compose -f docker-compose-remote-sidecar.yml up -d

# Run CLI command
crossbridge search duplicates --framework robot --threshold 0.95 \
    --test-dir ./tests --output-file output.xml

# View forwarded logs in sidecar
docker logs crossbridge-sidecar --tail 50 | grep -E "\[CLI:(ai|cli)\]"
```

**Sample Output:**
```
INFO:     127.0.0.1:52130 - "GET /health HTTP/1.1" 200 OK
INFO | [CLI:ai] HTTP Request: POST http://10.60.75.145:11434/api/embeddings (model='nomic-embed-text', text_length=150)
INFO | [CLI:ai] HTTP Request: POST http://10.60.75.145:11434/api/embeddings (model='nomic-embed-text', text_length=142)
INFO | [CLI:ai] Generated 45 embeddings using local model 'nomic-embed-text'
INFO | [CLI:cli] Found 8 potential duplicates (threshold=0.95)
```

### Benefits

- 🔄 **Centralized Logging**: All CLI operations visible in sidecar logs
- 🤖 **AI Transparency**: See exactly what requests are sent to AI services (Ollama, OpenAI, etc.)
- 🏗️ **Distributed Architecture**: CLI can run on different machines, logs centralized in sidecar
- 🐳 **Docker-Friendly**: Perfect for containerized CI/CD pipelines
- 📊 **Non-Blocking**: Log forwarding never blocks CLI operations (fail-safe design)

### Framework Support

Sidecar log forwarding works for all supported frameworks:
- Robot Framework
- Pytest
- JUnit/Maven
- Cypress
- Playwright
- Jest
- Mocha
- All other CrossBridge-supported frameworks

The feature is **framework-agnostic** and operates at the core logging layer.

## Supported Frameworks

- Robot Framework
- Pytest
- JUnit/Maven
- Cypress
- Playwright
- Mocha
- Jest
- ...and more

## See Also
- [README.md](../README.md)
- [docs/UNIFIED_CLI.md](../docs/UNIFIED_CLI.md)
- [docs/frameworks/README.md](../docs/frameworks/README.md)

---

For more details, see the main README and CLI documentation.
