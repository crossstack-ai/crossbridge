"""
Embedding Generation Engine.

Converts text/code into vector embeddings for semantic search.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class Embedding:
    """Represents a text/code embedding."""
    
    content: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding_id: Optional[str] = None
    model: str = "default"
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.embedding_id:
            self.embedding_id = hashlib.md5(
                self.content.encode()
            ).hexdigest()[:16]


class EmbeddingEngine:
    """
    Generate embeddings for text and code.
    
    Supports multiple embedding backends:
    - OpenAI embeddings (text-embedding-ada-002)
    - Local sentence-transformers
    - Custom embedding models
    """
    
    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_path: Optional[Path] = None,
    ):
        """
        Initialize embedding engine.
        
        Args:
            model: Embedding model identifier
            cache_path: Optional path to cache embeddings
        """
        self.model = model
        self.cache_path = cache_path
        self._cache: Dict[str, List[float]] = {}
        
        if cache_path and cache_path.exists():
            self._load_cache()
    
    def embed(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Embedding:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            metadata: Optional metadata
        
        Returns:
            Embedding object
        """
        # Check cache
        cache_key = hashlib.md5(f"{self.model}:{text}".encode()).hexdigest()
        
        if cache_key in self._cache:
            vector = self._cache[cache_key]
        else:
            vector = self._generate_embedding(text)
            self._cache[cache_key] = vector
        
        return Embedding(
            content=text,
            vector=vector,
            metadata=metadata or {},
            model=self.model,
        )
    
    def embed_batch(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Embedding]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            metadata: Optional list of metadata dicts
        
        Returns:
            List of embedding objects
        """
        embeddings = []
        
        for i, text in enumerate(texts):
            meta = metadata[i] if metadata and i < len(metadata) else None
            embeddings.append(self.embed(text, meta))
        
        return embeddings
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector.
        
        In production, this would:
        1. Load embedding model (sentence-transformers, OpenAI, etc.)
        2. Tokenize and encode text
        3. Return normalized vector
        
        For now, returns mock embedding (384 dimensions for MiniLM).
        """
        # Mock embedding generation
        # In production, use sentence-transformers or OpenAI
        import random
        random.seed(hash(text) % (2**32))
        
        # Generate 384-dim vector (MiniLM default)
        vector = [random.random() for _ in range(384)]
        
        # Normalize
        magnitude = sum(x ** 2 for x in vector) ** 0.5
        vector = [x / magnitude for x in vector]
        
        return vector
    
    def similarity(self, embedding1: Embedding, embedding2: Embedding) -> float:
        """
        Compute cosine similarity between embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            Similarity score (0-1)
        """
        v1 = embedding1.vector
        v2 = embedding2.vector
        
        if len(v1) != len(v2):
            raise ValueError("Embedding dimensions don't match")
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        return max(0.0, min(1.0, dot_product))
    
    def _load_cache(self):
        """Load embedding cache from disk."""
        if not self.cache_path or not self.cache_path.exists():
            return
        
        try:
            with open(self.cache_path) as f:
                self._cache = json.load(f)
        except Exception as e:
            print(f"Failed to load embedding cache: {e}")
    
    def save_cache(self):
        """Save embedding cache to disk."""
        if not self.cache_path:
            return
        
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.cache_path, 'w') as f:
            json.dump(self._cache, f)
    
    def get_cache_size(self) -> int:
        """Get number of cached embeddings."""
        return len(self._cache)
