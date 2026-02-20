# Unit/Integration Test Coverage for Memory, Embeddings, and Duplicate Detection

The following test modules provide comprehensive coverage for the memory, embeddings, semantic search, and duplicate detection features in CrossBridge. These tests ensure robust support for all frameworks and custom test directory/project root logic:

- `tests/test_memory_system.py`: Unit tests for memory models, embedding providers (OpenAI, local, HuggingFace), vector stores (pgvector, FAISS), ingestion pipeline, and semantic search engine.
- `tests/test_memory_real_integration.py`: Real database integration tests for the memory and semantic search system using PostgreSQL + pgvector.
- `tests/test_memory_models.py`: Unit tests for memory record models and validation logic.
- `tests/test_memory_integration.py`: Integration tests for the complete memory workflow (ingestion to search).
- `tests/test_universal_memory_integration.py`: Tests for universal memory and embedding integration across all 13+ supported frameworks, verifying normalization and duplicate detection.
- `tests/unit/core/ai/test_mcp_and_memory.py`: Comprehensive unit tests for MCP client/server, embeddings, vector store, and context retrieval.

**How to Run All Tests:**

```bash
pytest tests/
```

All tests are designed to work with the latest CLI and adapter logic, including the `--test-dir` option and framework auto-detection. For more details, see the main README and the docstrings in each test file.
