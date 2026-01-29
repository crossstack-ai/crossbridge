"""
Vector Store Interface

Abstract interface for vector similarity search.
Implementations: pgvector (production), FAISS (optional phase 2)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from core.ai.embeddings.text_builder import EmbeddableEntity


@dataclass
class SimilarityResult:
    """
    Result from similarity search
    
    Contains entity info and similarity score.
    """
    id: str                           # Entity ID
    entity_type: str                  # Entity type
    score: float                      # Similarity score (0.0-1.0)
    text: str                         # Embedding text
    metadata: Dict[str, Any]          # Entity metadata
    embedding: Optional[List[float]] = None  # Optionally return embedding
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'score': self.score,
            'text': self.text,
            'metadata': self.metadata
        }


class VectorStore(ABC):
    """
    Abstract vector store interface
    
    All implementations must support:
    - upsert(): Insert or update embeddings
    - similarity_search(): Find similar entities
    - get(): Retrieve specific entity
    - delete(): Remove entity
    - count(): Get total entities
    """
    
    @abstractmethod
    def upsert(
        self,
        entity: EmbeddableEntity,
        embedding: List[float],
        model: str,
        version: str
    ) -> None:
        """
        Insert or update entity embedding
        
        Args:
            entity: Embeddable entity
            embedding: Embedding vector
            model: Model used to generate embedding
            version: Embedding version (for reindexing)
        
        Raises:
            VectorStoreError: If upsert fails
        """
        pass
    
    @abstractmethod
    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[SimilarityResult]:
        """
        Find similar entities by embedding
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            entity_type: Filter by entity type (test, scenario, failure)
            filters: Additional metadata filters
            min_score: Minimum similarity score
        
        Returns:
            List of similarity results, sorted by score (descending)
        
        Raises:
            VectorStoreError: If search fails
        """
        pass
    
    @abstractmethod
    def get(self, entity_id: str) -> Optional[SimilarityResult]:
        """
        Retrieve entity by ID
        
        Args:
            entity_id: Entity identifier
        
        Returns:
            SimilarityResult if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """
        Delete entity by ID
        
        Args:
            entity_id: Entity identifier
        
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def count(
        self,
        entity_type: Optional[str] = None,
        version: Optional[str] = None
    ) -> int:
        """
        Count entities in store
        
        Args:
            entity_type: Filter by entity type
            version: Filter by embedding version
        
        Returns:
            Count of matching entities
        """
        pass
    
    @abstractmethod
    def list_versions(self) -> List[str]:
        """
        List all embedding versions in store
        
        Returns:
            List of version strings
        """
        pass
    
    def upsert_batch(
        self,
        entities: List[EmbeddableEntity],
        embeddings: List[List[float]],
        model: str,
        version: str
    ) -> None:
        """
        Batch upsert (default: loop through one by one)
        
        Override for batch-optimized implementations.
        
        Args:
            entities: List of entities
            embeddings: List of embedding vectors
            model: Model used
            version: Embedding version
        """
        if len(entities) != len(embeddings):
            raise ValueError("entities and embeddings must have same length")
        
        for entity, embedding in zip(entities, embeddings):
            self.upsert(entity, embedding, model, version)
