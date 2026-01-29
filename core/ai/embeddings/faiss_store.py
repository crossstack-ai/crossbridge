"""
FAISS Vector Store Implementation

Fast similarity search using Facebook AI Similarity Search (FAISS).
Alternative to pgvector for local/high-performance deployments.

FAISS is used when:
- Embeddings > 50k
- Local deployment required
- Clustering/ANN search needed
"""

import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from core.ai.embeddings.vector_store import VectorStore, SimilarityResult
from core.logging import get_logger, LogCategory
from cli.errors import CrossBridgeError

logger = get_logger(__name__, category=LogCategory.AI)


class FAISSError(CrossBridgeError):
    """FAISS operation error"""
    pass


@dataclass
class FAISSConfig:
    """FAISS index configuration"""
    dimensions: int
    index_type: str = "flat"  # flat, ivf, hnsw
    metric: str = "cosine"  # cosine, l2, ip
    n_lists: int = 100  # For IVF index
    n_probe: int = 10  # For IVF search
    
    def __post_init__(self):
        if self.index_type not in ["flat", "ivf", "hnsw"]:
            raise ValueError(f"Invalid index type: {self.index_type}")
        if self.metric not in ["cosine", "l2", "ip"]:
            raise ValueError(f"Invalid metric: {self.metric}")


class FaissVectorStore(VectorStore):
    """
    FAISS-based vector store.
    
    Features:
    - Fast cosine similarity search
    - Persistence to disk
    - Metadata storage (separate from vectors)
    - Scalable to millions of vectors
    
    Storage strategy:
    - Vectors → FAISS index (binary)
    - Metadata → Pickle file (JSON in future)
    - IDs → Bidirectional mapping
    
    Phase-1: IndexFlatIP (cosine similarity, exact search)
    Phase-2: IVF/HNSW (approximate search for scale)
    """
    
    def __init__(
        self,
        dimensions: int,
        config: Optional[FAISSConfig] = None,
        index_path: Optional[str] = None
    ):
        """
        Initialize FAISS vector store
        
        Args:
            dimensions: Vector dimensionality
            config: FAISS configuration
            index_path: Path to persist index (optional)
        """
        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            raise FAISSError(
                "FAISS not installed",
                error_code="FAISS_NOT_INSTALLED",
                suggestion="Install with: pip install faiss-cpu (or faiss-gpu)"
            )
        
        self.dimensions = dimensions
        self.config = config or FAISSConfig(dimensions=dimensions)
        self.index_path = Path(index_path) if index_path else None
        
        # Initialize index
        self.index = self._create_index()
        
        # ID mapping (FAISS uses integer IDs, we need string IDs)
        self.id_to_idx: Dict[str, int] = {}  # entity_id -> FAISS idx
        self.idx_to_id: Dict[int, str] = {}  # FAISS idx -> entity_id
        
        # Metadata storage (separate from vectors)
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        # Load existing index if path provided
        if self.index_path and self.index_path.exists():
            self.load(str(self.index_path))
        
        logger.info(
            f"FAISS vector store initialized",
            dimensions=dimensions,
            index_type=self.config.index_type,
            metric=self.config.metric
        )
    
    def _create_index(self):
        """Create FAISS index based on configuration"""
        if self.config.metric == "cosine":
            # For cosine similarity: normalize vectors + Inner Product
            if self.config.index_type == "flat":
                return self.faiss.IndexFlatIP(self.dimensions)
            elif self.config.index_type == "ivf":
                quantizer = self.faiss.IndexFlatIP(self.dimensions)
                return self.faiss.IndexIVFFlat(
                    quantizer,
                    self.dimensions,
                    self.config.n_lists,
                    self.faiss.METRIC_INNER_PRODUCT
                )
        elif self.config.metric == "l2":
            if self.config.index_type == "flat":
                return self.faiss.IndexFlatL2(self.dimensions)
            elif self.config.index_type == "ivf":
                quantizer = self.faiss.IndexFlatL2(self.dimensions)
                return self.faiss.IndexIVFFlat(
                    quantizer,
                    self.dimensions,
                    self.config.n_lists,
                    self.faiss.METRIC_L2
                )
        
        # Default: Flat IP (exact cosine)
        return self.faiss.IndexFlatIP(self.dimensions)
    
    def _normalize_vector(self, vector: List[float]) -> np.ndarray:
        """Normalize vector for cosine similarity"""
        vec = np.array([vector], dtype=np.float32)
        if self.config.metric == "cosine":
            # Normalize to unit length for cosine similarity
            norm = np.linalg.norm(vec, axis=1, keepdims=True)
            if norm > 0:
                vec = vec / norm
        return vec
    
    def upsert(
        self,
        entity_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Insert or update vector
        
        Args:
            entity_id: Unique entity identifier
            vector: Embedding vector
            metadata: Optional metadata
        """
        if len(vector) != self.dimensions:
            raise FAISSError(
                f"Vector dimension mismatch: expected {self.dimensions}, got {len(vector)}",
                error_code="DIMENSION_MISMATCH"
            )
        
        # Check if entity already exists
        if entity_id in self.id_to_idx:
            # Remove old vector (FAISS doesn't support update)
            old_idx = self.id_to_idx[entity_id]
            # Note: FAISS doesn't support deletion efficiently
            # For now, we'll just update the mapping
            logger.warning(f"Entity {entity_id} already exists, adding new version")
        
        # Normalize vector
        vec = self._normalize_vector(vector)
        
        # Add to FAISS
        self.index.add(vec)
        
        # Get the index of the newly added vector
        new_idx = self.index.ntotal - 1
        
        # Update mappings
        self.id_to_idx[entity_id] = new_idx
        self.idx_to_id[new_idx] = entity_id
        
        # Store metadata
        if metadata:
            self.metadata[entity_id] = metadata
        
        logger.debug(f"Upserted entity {entity_id} at index {new_idx}")
    
    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SimilarityResult]:
        """
        Search for similar vectors
        
        Args:
            query_vector: Query embedding
            top_k: Number of results
            min_score: Minimum similarity score (0-1 for cosine)
            filters: Metadata filters (applied post-search)
        
        Returns:
            List of similarity results
        """
        if self.index.ntotal == 0:
            return []
        
        if len(query_vector) != self.dimensions:
            raise FAISSError(
                f"Query vector dimension mismatch: expected {self.dimensions}, got {len(query_vector)}",
                error_code="DIMENSION_MISMATCH"
            )
        
        # Normalize query vector
        query_vec = self._normalize_vector(query_vector)
        
        # Search (get more results if filtering)
        search_k = top_k * 3 if filters else top_k
        scores, indices = self.index.search(query_vec, search_k)
        
        # Convert to results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            # Check if valid index
            if idx == -1 or idx not in self.idx_to_id:
                continue
            
            # Convert score (FAISS inner product → cosine similarity for normalized vectors)
            # Inner product of normalized vectors = cosine similarity
            similarity = float(score)
            
            # Filter by min score
            if similarity < min_score:
                continue
            
            entity_id = self.idx_to_id[idx]
            metadata = self.metadata.get(entity_id, {})
            
            # Apply metadata filters
            if filters and not self._matches_filters(metadata, filters):
                continue
            
            results.append(SimilarityResult(
                entity_id=entity_id,
                score=similarity,
                metadata=metadata
            ))
            
            # Stop if we have enough results
            if len(results) >= top_k:
                break
        
        return results
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches filters"""
        for key, expected_value in filters.items():
            actual_value = metadata.get(key)
            
            # List filter (check if any value matches)
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            # Exact match
            elif actual_value != expected_value:
                return False
        
        return True
    
    def get(self, entity_id: str) -> Optional[Tuple[List[float], Dict[str, Any]]]:
        """
        Get vector and metadata for entity
        
        Returns:
            (vector, metadata) or None if not found
        """
        if entity_id not in self.id_to_idx:
            return None
        
        idx = self.id_to_idx[entity_id]
        
        # FAISS doesn't support direct vector retrieval efficiently
        # This is a limitation of FAISS - it's optimized for search, not retrieval
        logger.warning("FAISS get() is inefficient - consider using pgvector for retrieval")
        
        metadata = self.metadata.get(entity_id, {})
        return ([], metadata)  # Vector retrieval not supported efficiently
    
    def delete(self, entity_id: str) -> bool:
        """
        Delete entity (note: FAISS doesn't support efficient deletion)
        
        Returns:
            True if deleted
        """
        if entity_id not in self.id_to_idx:
            return False
        
        # Remove from mappings
        idx = self.id_to_idx.pop(entity_id)
        del self.idx_to_id[idx]
        
        # Remove metadata
        if entity_id in self.metadata:
            del self.metadata[entity_id]
        
        # Note: Vector remains in FAISS index (no efficient deletion)
        logger.warning(f"Deleted mapping for {entity_id}, but vector remains in index")
        
        return True
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities
        
        Args:
            filters: Metadata filters (optional)
        
        Returns:
            Number of entities
        """
        if not filters:
            return len(self.id_to_idx)
        
        # Count with filters
        count = 0
        for entity_id in self.id_to_idx.keys():
            metadata = self.metadata.get(entity_id, {})
            if self._matches_filters(metadata, filters):
                count += 1
        
        return count
    
    def clear(self) -> None:
        """Clear all vectors and metadata"""
        self.index.reset()
        self.id_to_idx.clear()
        self.idx_to_id.clear()
        self.metadata.clear()
        
        logger.info("FAISS index cleared")
    
    def persist(self, path: str) -> None:
        """
        Persist index to disk
        
        Saves:
        - FAISS index (binary)
        - ID mappings (pickle)
        - Metadata (pickle)
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_file = str(path.with_suffix('.faiss'))
        self.faiss.write_index(self.index, index_file)
        
        # Save mappings and metadata
        mappings_file = str(path.with_suffix('.pkl'))
        with open(mappings_file, 'wb') as f:
            pickle.dump({
                'id_to_idx': self.id_to_idx,
                'idx_to_id': self.idx_to_id,
                'metadata': self.metadata,
                'config': self.config
            }, f)
        
        logger.info(f"FAISS index persisted to {path}")
    
    def load(self, path: str) -> None:
        """Load index from disk"""
        path = Path(path)
        
        # Load FAISS index
        index_file = str(path.with_suffix('.faiss'))
        if not Path(index_file).exists():
            raise FAISSError(
                f"FAISS index file not found: {index_file}",
                error_code="INDEX_NOT_FOUND"
            )
        
        self.index = self.faiss.read_index(index_file)
        
        # Load mappings and metadata
        mappings_file = str(path.with_suffix('.pkl'))
        if Path(mappings_file).exists():
            with open(mappings_file, 'rb') as f:
                data = pickle.load(f)
                self.id_to_idx = data['id_to_idx']
                self.idx_to_id = data['idx_to_id']
                self.metadata = data['metadata']
                # Update config if available
                if 'config' in data:
                    self.config = data['config']
        
        logger.info(f"FAISS index loaded from {path}, {self.index.ntotal} vectors")


def create_faiss_store(
    dimensions: int,
    index_type: str = "flat",
    metric: str = "cosine",
    index_path: Optional[str] = None
) -> FaissVectorStore:
    """
    Factory function to create FAISS vector store
    
    Args:
        dimensions: Vector dimensionality
        index_type: Index type (flat, ivf, hnsw)
        metric: Distance metric (cosine, l2, ip)
        index_path: Path to persist/load index
    
    Returns:
        Configured FAISS vector store
    """
    config = FAISSConfig(
        dimensions=dimensions,
        index_type=index_type,
        metric=metric
    )
    
    return FaissVectorStore(
        dimensions=dimensions,
        config=config,
        index_path=index_path
    )
