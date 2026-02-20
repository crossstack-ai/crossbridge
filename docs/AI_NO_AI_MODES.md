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
# For self-hosted/Ollama
crossbridge auth login --provider selfhosted \
    --url http://localhost:11434 \
    --model deepseek-coder:6.7b

# For OpenAI
crossbridge auth login --provider openai \
    --token YOUR_OPENAI_API_KEY

# For Anthropic
crossbridge auth login --provider anthropic \
    --token YOUR_ANTHROPIC_API_KEY
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
        model: your-model-name
        api_key: your-api-key  # optional, for OpenAI/Anthropic
      vector_store:
        type: faiss  # Default: FAISS (no database required)
        storage_path: ./faiss_index  # Optional: where to persist FAISS index
        # For PostgreSQL with pgvector extension:
        # type: pgvector
        # connection_string: postgresql://user:pass@localhost/dbname
    ollama:
      base_url: http://localhost:11434
      model: deepseek-coder:6.7b
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
