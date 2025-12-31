"""
Vector Store for Semantic Search.

Stores and retrieves embeddings using similarity search.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from core.ai.memory.embeddings import Embedding, EmbeddingEngine


@dataclass
class SearchResult:
    """Represents a search result."""
    
    embedding: Embedding
    score: float
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.embedding.content,
            "score": self.score,
            "rank": self.rank,
            "metadata": self.embedding.metadata,
        }


class VectorStore:
    """
    In-memory vector store with similarity search.
    
    Stores embeddings and provides fast nearest-neighbor search.
    In production, use specialized vector databases (Pinecone, Weaviate, Qdrant).
    """
    
    def __init__(
        self,
        embedding_engine: Optional[EmbeddingEngine] = None,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize vector store.
        
        Args:
            embedding_engine: Engine for generating embeddings
            storage_path: Optional path to persist embeddings
        """
        self.engine = embedding_engine or EmbeddingEngine()
        self.storage_path = storage_path
        self._embeddings: Dict[str, Embedding] = {}
        
        if storage_path and storage_path.exists():
            self._load_embeddings()
    
    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_id: Optional[str] = None,
    ) -> Embedding:
        """
        Add content to vector store.
        
        Args:
            content: Text/code content
            metadata: Optional metadata
            embedding_id: Optional custom ID
        
        Returns:
            Generated embedding
        """
        embedding = self.engine.embed(content, metadata)
        
        if embedding_id:
            embedding.embedding_id = embedding_id
        
        self._embeddings[embedding.embedding_id] = embedding
        
        return embedding
    
    def add_batch(
        self,
        contents: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Embedding]:
        """
        Add multiple contents to vector store.
        
        Args:
            contents: List of text/code contents
            metadata: Optional list of metadata dicts
        
        Returns:
            List of generated embeddings
        """
        embeddings = self.engine.embed_batch(contents, metadata)
        
        for emb in embeddings:
            self._embeddings[emb.embedding_id] = emb
        
        return embeddings
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for similar embeddings.
        
        Args:
            query: Query text
            top_k: Number of results to return
            threshold: Minimum similarity score
            filter_metadata: Optional metadata filters
        
        Returns:
            List of search results sorted by similarity
        """
        # Generate query embedding
        query_embedding = self.engine.embed(query)
        
        # Compute similarities
        results = []
        
        for emb in self._embeddings.values():
            # Apply metadata filters
            if filter_metadata:
                if not self._matches_filter(emb.metadata, filter_metadata):
                    continue
            
            score = self.engine.similarity(query_embedding, emb)
            
            if score >= threshold:
                results.append((emb, score))
        
        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Take top-k
        results = results[:top_k]
        
        # Convert to SearchResult objects
        return [
            SearchResult(embedding=emb, score=score, rank=i+1)
            for i, (emb, score) in enumerate(results)
        ]
    
    def search_by_embedding(
        self,
        query_embedding: Embedding,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search using an existing embedding.
        
        Args:
            query_embedding: Query embedding
            top_k: Number of results to return
            threshold: Minimum similarity score
        
        Returns:
            List of search results
        """
        results = []
        
        for emb in self._embeddings.values():
            if emb.embedding_id == query_embedding.embedding_id:
                continue  # Skip self
            
            score = self.engine.similarity(query_embedding, emb)
            
            if score >= threshold:
                results.append((emb, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:top_k]
        
        return [
            SearchResult(embedding=emb, score=score, rank=i+1)
            for i, (emb, score) in enumerate(results)
        ]
    
    def get(self, embedding_id: str) -> Optional[Embedding]:
        """Get embedding by ID."""
        return self._embeddings.get(embedding_id)
    
    def delete(self, embedding_id: str) -> bool:
        """
        Delete embedding by ID.
        
        Args:
            embedding_id: ID of embedding to delete
        
        Returns:
            True if deleted
        """
        if embedding_id in self._embeddings:
            del self._embeddings[embedding_id]
            return True
        return False
    
    def count(self) -> int:
        """Get number of embeddings in store."""
        return len(self._embeddings)
    
    def clear(self):
        """Clear all embeddings."""
        self._embeddings.clear()
    
    def _matches_filter(
        self,
        metadata: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> bool:
        """Check if metadata matches filters."""
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def _load_embeddings(self):
        """Load embeddings from disk."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path) as f:
                data = json.load(f)
            
            for item in data:
                emb = Embedding(
                    content=item["content"],
                    vector=item["vector"],
                    metadata=item.get("metadata", {}),
                    embedding_id=item.get("embedding_id"),
                    model=item.get("model", "default"),
                )
                self._embeddings[emb.embedding_id] = emb
        
        except Exception as e:
            print(f"Failed to load embeddings: {e}")
    
    def save_embeddings(self):
        """Save embeddings to disk."""
        if not self.storage_path:
            return
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = []
        for emb in self._embeddings.values():
            data.append({
                "content": emb.content,
                "vector": emb.vector,
                "metadata": emb.metadata,
                "embedding_id": emb.embedding_id,
                "model": emb.model,
            })
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics."""
        if not self._embeddings:
            return {
                "total_embeddings": 0,
                "avg_content_length": 0,
                "embedding_dimensions": 0,
            }
        
        total = len(self._embeddings)
        avg_length = sum(len(e.content) for e in self._embeddings.values()) / total
        dimensions = len(next(iter(self._embeddings.values())).vector)
        
        return {
            "total_embeddings": total,
            "avg_content_length": avg_length,
            "embedding_dimensions": dimensions,
            "models": list(set(e.model for e in self._embeddings.values())),
        }
