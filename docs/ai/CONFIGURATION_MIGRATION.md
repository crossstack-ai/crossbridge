# Configuration Migration Notice

## Important: Unified Configuration

As of January 30, 2026, CrossBridge has **consolidated all memory, embedding, and semantic search configuration** into a single unified section: `runtime.semantic_search`.

### Old Configuration (DEPRECATED)

❌ **Do NOT use these sections anymore:**

```yaml
# OLD - NO LONGER USED
crossbridge:
  memory:
    enabled: true
    auto_normalize: true
    generate_embeddings: true
    embedding_provider: openai
    # ...

# OLD - NO LONGER USED  
crossbridge:
  memory:
    embedding_provider:
      type: openai
      model: text-embedding-3-large
    vector_store:
      type: pgvector
    # ...
```

### New Configuration (CURRENT)

✅ **Use this unified section:**

```yaml
runtime:
  semantic_search:
    enabled: auto
    
    # Test normalization & AST extraction
    normalization:
      auto_normalize: true
      extract_structural_signals: true
      extract_ui_interactions: true
      extract_api_calls: true
      frameworks:
        cypress: true
        playwright: true
        pytest: true
        # ... all frameworks
    
    # Embedding provider
    provider_type: openai
    openai:
      api_key: ${OPENAI_API_KEY}
      model: text-embedding-3-large
      dimensions: 3072
    
    # Search configuration
    search:
      max_tokens: 8000
      min_similarity_score: 0.7
      default_top_k: 10
      api_timeout: 30
      batch_size: 100
    
    # Vector store
    vector_store:
      type: pgvector
      index_type: ivfflat
      index_lists: 100
    
    # Ingestion & lifecycle
    ingestion:
      auto_ingest_on_discovery: true
      update_on_change: true
      ttl_days: 90
    
    # Migration overrides
    migration_overrides:
      enabled: true
      provider_type: openai
      min_similarity_score: 0.6
```

## Why the Change?

**Problem**: Users were confused by duplicate configuration in multiple places:
- `crossbridge.memory` (lines 62-102)
- `crossbridge.memory` again (lines 230-280)  
- `runtime.semantic_search` (lines 1208-1260)

All three sections configured the same features (embeddings, vector store, search), leading to:
- ❌ Confusion about which section to use
- ❌ Duplicate API key configuration
- ❌ Inconsistent settings across sections

**Solution**: Single unified section under `runtime.semantic_search` that combines:
- ✅ Test normalization (UnifiedTestMemory)
- ✅ AST extraction (structural signals)
- ✅ Embedding generation (OpenAI/Anthropic/Local)
- ✅ Vector storage (pgvector)
- ✅ Semantic search (similarity queries)

## Migration Steps

If you have an existing `crossbridge.yml` with old `memory` sections:

1. **Remove** old `memory` sections from `crossbridge:` block
2. **Add** new `semantic_search` section under `runtime:` block
3. **Transfer** your settings to the new structure
4. **Test** with: `crossbridge semantic stats`

## Code Changes

**No code changes required!** The `UnifiedTestMemory` implementation in `core/intelligence/models.py` remains unchanged. Only the YAML configuration structure has changed.

## Documentation Updates

All documentation now references only `runtime.semantic_search`:
- ✅ [README.md](../../README.md) - Updated feature section
- ✅ [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md) - Updated configuration guide
- ✅ [SEMANTIC_SEARCH_QUICK_START.md](SEMANTIC_SEARCH_QUICK_START.md) - Updated examples
- ✅ [crossbridge.yml](../../crossbridge.yml) - Single unified section

## Need Help?

If you're migrating from old configuration:
1. Check the [Quick Start Guide](SEMANTIC_SEARCH_QUICK_START.md)
2. Review the [complete documentation](SEMANTIC_SEARCH.md)
3. See example configuration in [crossbridge.yml](../../crossbridge.yml)

---

**Note**: This consolidation was implemented to reduce user confusion and provide a single source of truth for all semantic search and test intelligence features.
