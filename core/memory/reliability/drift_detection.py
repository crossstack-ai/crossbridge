"""
Semantic Drift Detection.

Detects when embeddings have semantically drifted from their original meaning,
even if text hasn't changed significantly. Uses cosine similarity to compare
old vs new embeddings.
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Drift threshold - embeddings with similarity below this are considered drifted
DRIFT_THRESHOLD = 0.85


@dataclass
class DriftResult:
    """Result from drift detection."""
    record_id: str
    has_drifted: bool
    similarity_score: float
    threshold: float
    old_vector: Optional[List[float]] = None
    new_vector: Optional[List[float]] = None


class DriftDetector:
    """
    Detects semantic drift in embeddings.
    
    Compares new embeddings against stored embeddings to detect
    significant semantic changes.
    """
    
    def __init__(
        self,
        vector_store,
        drift_threshold: float = DRIFT_THRESHOLD
    ):
        """
        Initialize drift detector.
        
        Args:
            vector_store: Existing VectorStore from core.memory
            drift_threshold: Similarity threshold (below = drifted)
        """
        self.vector_store = vector_store
        self.drift_threshold = drift_threshold
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Similarity score (0-1, higher = more similar)
        """
        if not vec1 or not vec2:
            return 0.0
        
        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)
        
        # Handle zero vectors
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(v1, v2) / (norm1 * norm2))
    
    def check_drift(
        self,
        record_id: str,
        new_embedding: List[float]
    ) -> DriftResult:
        """
        Check if new embedding has drifted from stored embedding.
        
        Args:
            record_id: Memory record ID
            new_embedding: Newly generated embedding
            
        Returns:
            DriftResult with drift information
        """
        # Get stored embedding
        record = self.vector_store.get(record_id)
        
        if not record or not record.embedding:
            # No stored embedding to compare against
            return DriftResult(
                record_id=record_id,
                has_drifted=False,
                similarity_score=1.0,
                threshold=self.drift_threshold,
                new_vector=new_embedding
            )
        
        # Compute similarity
        similarity = self.cosine_similarity(record.embedding, new_embedding)
        has_drifted = similarity < self.drift_threshold
        
        if has_drifted:
            logger.warning(
                f"Semantic drift detected for {record_id}: "
                f"similarity={similarity:.3f} < threshold={self.drift_threshold}"
            )
        
        result = DriftResult(
            record_id=record_id,
            has_drifted=has_drifted,
            similarity_score=similarity,
            threshold=self.drift_threshold,
            old_vector=record.embedding,
            new_vector=new_embedding
        )
        
        # Store drift score in metadata
        if record.metadata is None:
            record.metadata = {}
        record.metadata['drift_score'] = similarity
        record.metadata['drift_detected'] = has_drifted
        
        return result
    
    def bulk_check_drift(
        self,
        embeddings: List[tuple[str, List[float]]]
    ) -> List[DriftResult]:
        """
        Check drift for multiple embeddings in batch.
        
        Args:
            embeddings: List of (record_id, new_embedding) tuples
            
        Returns:
            List of DriftResult objects
        """
        results = []
        for record_id, new_embedding in embeddings:
            result = self.check_drift(record_id, new_embedding)
            results.append(result)
        return results
