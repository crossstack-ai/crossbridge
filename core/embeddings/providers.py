"""
Unified Embedding Providers

Consolidates OpenAI, SentenceTransformers, and hash-based providers
from Memory system and Execution Intelligence.
"""

import hashlib
import os
from typing import List, Optional

from core.embeddings.interface import IEmbeddingProvider, EmbeddingDimension
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


class OpenAIProvider(IEmbeddingProvider):
    """
    OpenAI embedding provider.
    
    Supports:
    - text-embedding-3-large (3072 dims)
    - text-embedding-3-small (1536 dims)
    - text-embedding-ada-002 (1536 dims)
    """
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        batch_size: int = 100
    ):
        self.model = model
        self.batch_size = batch_size
        
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required. Install: pip install openai"
            )
        
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self._dimension = self._detect_dimension()
        
        logger.info(f"Initialized OpenAI provider: {model} ({self._dimension} dims)")
    
    def _detect_dimension(self) -> int:
        """Detect dimension from model name"""
        dims = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
        }
        return dims.get(self.model, 1536)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        response = self.client.embeddings.create(
            model=self.model,
            input=[text]
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch
            )
            all_embeddings.extend([item.embedding for item in response.data])
        
        return all_embeddings
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_model_name(self) -> str:
        return f"openai:{self.model}"


class SentenceTransformerProvider(IEmbeddingProvider):
    """
    SentenceTransformers provider (local models).
    
    Popular models:
    - all-MiniLM-L6-v2 (384 dims, fast, good quality)
    - all-mpnet-base-v2 (768 dims, high quality)
    - paraphrase-multilingual (768 dims, multilingual)
    """
    
    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        self.model_name = model
        self.device = device
        
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers required. Install: pip install sentence-transformers"
            )
        
        self.model = SentenceTransformer(model, device=device)
        self._dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"Initialized SentenceTransformer: {model} ({self._dimension} dims)")
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embedding = self.model.encode([text], convert_to_numpy=True)[0]
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_model_name(self) -> str:
        return f"sentence-transformers:{self.model_name}"


class HashBasedProvider(IEmbeddingProvider):
    """
    Hash-based embedding provider (deterministic fallback).
    
    Features:
    - No external dependencies
    - Deterministic (same text = same embedding)
    - Fast
    - No ML quality, but useful for exact matching
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        logger.info(f"Initialized HashBased provider ({dimension} dims)")
    
    def embed(self, text: str) -> List[float]:
        """Generate hash-based embedding"""
        # Create multiple hashes for different dimensions
        num_hashes = (self.dimension + 7) // 8  # 8 floats per hash (SHA256 = 32 bytes = 8 floats)
        
        vector = []
        for i in range(num_hashes):
            # Hash with salt
            hash_input = f"{text}:{i}".encode()
            hash_bytes = hashlib.sha256(hash_input).digest()
            
            # Convert to floats in [-1, 1]
            for j in range(0, min(len(hash_bytes), (self.dimension - len(vector)) * 4), 4):
                if len(vector) >= self.dimension:
                    break
                chunk = hash_bytes[j:j+4]
                value = int.from_bytes(chunk, byteorder='big', signed=False)
                # Normalize to [-1, 1]
                normalized = (value / (2**32 - 1)) * 2 - 1
                vector.append(normalized)
        
        # Ensure exact dimension
        while len(vector) < self.dimension:
            vector.append(0.0)
        
        return vector[:self.dimension]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate hash-based embeddings for multiple texts"""
        return [self.embed(text) for text in texts]
    
    def get_dimension(self) -> int:
        return self.dimension
    
    def get_model_name(self) -> str:
        return f"hash-based:{self.dimension}"


def create_provider(
    provider_type: str = "sentence-transformers",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    dimension: int = 384,
    **kwargs
) -> IEmbeddingProvider:
    """
    Factory function to create embedding provider.
    
    Args:
        provider_type: Type of provider (openai, sentence-transformers, hash)
        model: Model name (provider-specific)
        api_key: API key (for OpenAI)
        dimension: Embedding dimension (for hash-based)
        **kwargs: Additional provider-specific arguments
        
    Returns:
        IEmbeddingProvider instance
    """
    provider_type = provider_type.lower()
    
    if provider_type == "openai":
        model = model or "text-embedding-3-small"
        return OpenAIProvider(model=model, api_key=api_key, **kwargs)
    
    elif provider_type == "sentence-transformers":
        model = model or "all-MiniLM-L6-v2"
        return SentenceTransformerProvider(model=model, **kwargs)
    
    elif provider_type == "hash":
        return HashBasedProvider(dimension=dimension)
    
    else:
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Supported: openai, sentence-transformers, hash"
        )
