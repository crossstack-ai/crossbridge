# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Memory and Embeddings System for CrossBridge.

This module provides intelligent memory management for test-related entities,
enabling semantic search, similarity detection, and AI-powered insights.
"""

from core.memory.models import MemoryRecord, MemoryType, SearchResult
from core.memory.embedding_provider import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    HuggingFaceEmbeddingProvider,
    create_embedding_provider,
)
from core.memory.vector_store import (
    VectorStore,
    PgVectorStore,
    FAISSVectorStore,
    create_vector_store,
)
from core.memory.ingestion import MemoryIngestionPipeline
from core.memory.search import SemanticSearchEngine

__all__ = [
    "MemoryRecord",
    "MemoryType",
    "SearchResult",
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "LocalEmbeddingProvider",
    "HuggingFaceEmbeddingProvider",
    "create_embedding_provider",
    "VectorStore",
    "PgVectorStore",
    "FAISSVectorStore",
    "create_vector_store",
    "MemoryIngestionPipeline",
    "SemanticSearchEngine",
]
