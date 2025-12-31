"""
Memory and Embeddings System for CrossBridge AI.

Provides vector embeddings, semantic search, and context retrieval.
"""

from core.ai.memory.embeddings import EmbeddingEngine, Embedding
from core.ai.memory.vector_store import VectorStore, SearchResult
from core.ai.memory.retrieval import ContextRetriever, RetrievalConfig

__all__ = [
    "EmbeddingEngine",
    "Embedding",
    "VectorStore",
    "SearchResult",
    "ContextRetriever",
    "RetrievalConfig",
]
