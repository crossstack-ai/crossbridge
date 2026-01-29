"""
AI Embeddings Module

Provides semantic layer for CrossBridge:
- Text builders for tests/scenarios/failures
- Embedding provider abstraction
- Vector store integration (pgvector)
- Semantic similarity queries
"""

from core.ai.embeddings.text_builder import (
    EmbeddingTextBuilder,
    EmbeddableEntity
)
from core.ai.embeddings.provider import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    AnthropicEmbeddingProvider
)
from core.ai.embeddings.vector_store import (
    VectorStore,
    SimilarityResult
)
from core.ai.embeddings.pgvector_store import PgVectorStore

__all__ = [
    'EmbeddingTextBuilder',
    'EmbeddableEntity',
    'EmbeddingProvider',
    'OpenAIEmbeddingProvider',
    'AnthropicEmbeddingProvider',
    'VectorStore',
    'SimilarityResult',
    'PgVectorStore',
]
