"""
Unified Embedding Interface

Defines the common interface for all embedding providers and stores,
consolidating the separate Memory and Execution Intelligence systems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Protocol
from enum import Enum


class EmbeddingDimension(Enum):
    """Standard embedding dimensions"""
    SMALL = 384      # SentenceTransformers all-MiniLM-L6-v2
    MEDIUM = 768     # SentenceTransformers all-mpnet-base-v2
    LARGE = 1536     # OpenAI text-embedding-3-small
    XLARGE = 3072    # OpenAI text-embedding-3-large


@dataclass
class Embedding:
    """
    Universal embedding representation.
    
    Compatible with both Memory system and Execution Intelligence.
    """
    entity_id: str                           # Unique identifier
    entity_type: str                         # test, scenario, step, keyword, etc.
    text: str                                # Original text
    vector: List[float]                      # Embedding vector
    metadata: Dict[str, Any] = field(default_factory=dict)
    model: str = "unknown"                   # Model used for embedding
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        return len(self.vector)
    
    def cosine_similarity(self, other: 'Embedding') -> float:
        """Calculate cosine similarity with another embedding"""
        if self.dimension != other.dimension:
            raise ValueError(f"Dimension mismatch: {self.dimension} vs {other.dimension}")
        
        # Dot product
        dot_product = sum(a * b for a, b in zip(self.vector, other.vector))
        
        # Magnitudes
        mag_a = sum(a * a for a in self.vector) ** 0.5
        mag_b = sum(b * b for b in other.vector) ** 0.5
        
        if mag_a == 0 or mag_b == 0:
            return 0.0
        
        return dot_product / (mag_a * mag_b)


class IEmbeddingProvider(ABC):
    """
    Abstract interface for embedding providers.
    
    Implementations:
    - OpenAIProvider: Uses OpenAI API
    - SentenceTransformerProvider: Uses local models
    - HashBasedProvider: Deterministic fallback (no ML)
    """
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get model identifier"""
        pass


class IEmbeddingStore(ABC):
    """
    Abstract interface for embedding storage.
    
    Implementations:
    - PgVectorStore: PostgreSQL with pgvector (persistent)
    - InMemoryStore: Python dict (ephemeral)
    - ChromaDBStore: ChromaDB (hybrid)
    """
    
    @abstractmethod
    def add(self, embedding: Embedding) -> None:
        """Add embedding to store"""
        pass
    
    @abstractmethod
    def add_batch(self, embeddings: List[Embedding]) -> None:
        """Add multiple embeddings"""
        pass
    
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Embedding]:
        """Get embedding by ID"""
        pass
    
    @abstractmethod
    def find_similar(
        self,
        query: Embedding,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[tuple[Embedding, float]]:
        """
        Find similar embeddings.
        
        Args:
            query: Query embedding
            top_k: Number of results
            entity_type: Filter by type (optional)
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (embedding, similarity_score) tuples
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete embedding by ID"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all embeddings"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Get total number of embeddings"""
        pass
    
    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        pass


class IFrameworkAdapter(Protocol):
    """
    Protocol for framework-specific embedding adapters.
    
    Implementations:
    - CucumberAdapter: BDD scenarios/steps
    - RobotAdapter: Robot tests/keywords
    - PytestAdapter: Pytest tests/assertions
    """
    
    def generate_embeddings(
        self,
        entities: List[Any],
        provider: IEmbeddingProvider,
        include_granular: bool = False
    ) -> List[Embedding]:
        """
        Generate embeddings for framework entities.
        
        Args:
            entities: Framework-specific entities (scenarios, tests, etc.)
            provider: Embedding provider to use
            include_granular: Include step/keyword/assertion level
            
        Returns:
            List of embeddings
        """
        ...


@dataclass
class EmbeddingConfig:
    """
    Unified embedding configuration.
    
    Used by both Memory system and Execution Intelligence.
    """
    # Provider settings
    provider_type: str = "sentence-transformers"  # openai, sentence-transformers, hash
    model: str = "all-MiniLM-L6-v2"
    api_key: Optional[str] = None
    
    # Storage settings
    storage_type: str = "memory"  # memory, pgvector, chromadb
    connection_string: Optional[str] = None
    dimension: Optional[int] = None
    
    # Behavior settings
    enable_cache: bool = True
    batch_size: int = 32
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingConfig':
        """Create from dictionary (e.g., from crossbridge.yml)"""
        return cls(
            provider_type=data.get('provider_type', 'sentence-transformers'),
            model=data.get('model', 'all-MiniLM-L6-v2'),
            api_key=data.get('api_key'),
            storage_type=data.get('storage_type', 'memory'),
            connection_string=data.get('connection_string'),
            dimension=data.get('dimension'),
            enable_cache=data.get('enable_cache', True),
            batch_size=data.get('batch_size', 32),
        )
