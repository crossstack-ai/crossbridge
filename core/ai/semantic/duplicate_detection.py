"""
Duplicate Detection & Clustering

Phase-2 AI Engine component for:
- Finding duplicate tests/scenarios/failures
- Clustering similar entities
- Deduplication recommendations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import numpy as np

from core.ai.embeddings.provider import EmbeddingProvider
from core.ai.embeddings.vector_store import VectorStore, SimilarityResult
from core.ai.semantic.semantic_search_service import (
    SemanticResult,
    SemanticSearchService
)
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


# Thresholds for duplicate detection (from spec)
DUPLICATE_SIMILARITY_THRESHOLD = 0.9
DUPLICATE_CONFIDENCE_THRESHOLD = 0.8


class DuplicateType(Enum):
    """Type of duplicate relationship"""
    EXACT = "exact"                   # score >= 0.95
    VERY_SIMILAR = "very_similar"     # score >= 0.9
    SIMILAR = "similar"               # score >= 0.8
    POTENTIALLY_SIMILAR = "potentially_similar"  # score >= 0.7


@dataclass
class DuplicateMatch:
    """
    Represents a duplicate match between two entities
    """
    entity_id_1: str
    entity_id_2: str
    entity_type: str
    similarity_score: float
    confidence: float
    duplicate_type: DuplicateType
    reasons: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entity_id_1": self.entity_id_1,
            "entity_id_2": self.entity_id_2,
            "entity_type": self.entity_type,
            "similarity_score": self.similarity_score,
            "confidence": self.confidence,
            "duplicate_type": self.duplicate_type.value,
            "reasons": self.reasons,
            "metadata": self.metadata
        }


@dataclass
class Cluster:
    """
    Cluster of similar entities
    
    Phase-2 spec requirement: Store cluster_id, members, centroid, confidence
    """
    cluster_id: str
    members: List[str]              # Entity IDs in cluster
    centroid: List[float]           # Average embedding
    confidence: float               # Cluster quality score
    entity_type: str
    label: Optional[str] = None     # Human-readable label
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "cluster_id": self.cluster_id,
            "members": self.members,
            "centroid": self.centroid,
            "confidence": self.confidence,
            "entity_type": self.entity_type,
            "label": self.label,
            "created_at": self.created_at
        }
    
    @property
    def size(self) -> int:
        """Number of members in cluster"""
        return len(self.members)


class DuplicateDetector:
    """
    Detects duplicate entities using semantic similarity
    
    Phase-2 spec:
    - Two entities are duplicates if similarity >= 0.9 AND confidence >= 0.8
    - Must explain why duplicates were detected
    """
    
    def __init__(
        self,
        semantic_search: SemanticSearchService,
        similarity_threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
        confidence_threshold: float = DUPLICATE_CONFIDENCE_THRESHOLD
    ):
        """
        Initialize duplicate detector
        
        Args:
            semantic_search: Semantic search service
            similarity_threshold: Minimum similarity for duplicates (default: 0.9)
            confidence_threshold: Minimum confidence for duplicates (default: 0.8)
        """
        self.semantic_search = semantic_search
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        
        logger.info(
            f"Initialized duplicate detector "
            f"(similarity>={similarity_threshold}, confidence>={confidence_threshold})"
        )
    
    def find_duplicates(
        self,
        entity_id: str,
        entity_text: str,
        entity_type: str,
        top_k: int = 10
    ) -> List[DuplicateMatch]:
        """
        Find duplicate entities for a given entity
        
        Args:
            entity_id: Entity ID to find duplicates for
            entity_text: Entity text for embedding
            entity_type: Entity type (test, scenario, failure)
            top_k: Maximum duplicates to return
        
        Returns:
            List of duplicate matches
        """
        try:
            # Search for similar entities
            results = self.semantic_search.search(
                query_text=entity_text,
                entity_type=entity_type,
                top_k=top_k + 1,  # +1 to account for self-match
                min_confidence=0.0  # We'll filter ourselves
            )
            
            # Convert to duplicate matches
            duplicates = []
            for result in results:
                # Skip self-match
                if result.entity_id == entity_id:
                    continue
                
                # Check duplicate criteria
                is_duplicate = (
                    result.score >= self.similarity_threshold and
                    result.confidence >= self.confidence_threshold
                )
                
                if is_duplicate:
                    # Determine duplicate type
                    dup_type = self._classify_duplicate_type(result.score)
                    
                    # Generate explanation
                    reasons = self._explain_duplicate(
                        entity_id_1=entity_id,
                        entity_id_2=result.entity_id,
                        score=result.score,
                        confidence=result.confidence,
                        duplicate_type=dup_type
                    )
                    
                    duplicates.append(DuplicateMatch(
                        entity_id_1=entity_id,
                        entity_id_2=result.entity_id,
                        entity_type=entity_type,
                        similarity_score=result.score,
                        confidence=result.confidence,
                        duplicate_type=dup_type,
                        reasons=reasons,
                        metadata=result.metadata
                    ))
            
            logger.info(f"Found {len(duplicates)} duplicates for {entity_id}")
            return duplicates
            
        except Exception as e:
            logger.error(f"Duplicate detection failed for {entity_id}: {e}", exc_info=True)
            return []
    
    def find_all_duplicates(
        self,
        entities: List[Dict[str, Any]],
        entity_type: str
    ) -> List[DuplicateMatch]:
        """
        Find all duplicates in a set of entities
        
        Args:
            entities: List of entities (must have 'id' and 'text' fields)
            entity_type: Entity type
        
        Returns:
            List of all duplicate matches
        """
        all_duplicates = []
        seen_pairs: Set[tuple] = set()
        
        for entity in entities:
            entity_id = entity["id"]
            entity_text = entity["text"]
            
            # Find duplicates for this entity
            duplicates = self.find_duplicates(
                entity_id=entity_id,
                entity_text=entity_text,
                entity_type=entity_type,
                top_k=20
            )
            
            # Add to results, avoiding duplicates
            for dup in duplicates:
                # Create ordered pair to avoid duplicates
                pair = tuple(sorted([dup.entity_id_1, dup.entity_id_2]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    all_duplicates.append(dup)
        
        logger.info(
            f"Found {len(all_duplicates)} total duplicate pairs "
            f"across {len(entities)} entities"
        )
        
        return all_duplicates
    
    def _classify_duplicate_type(self, score: float) -> DuplicateType:
        """
        Classify duplicate type based on similarity score
        
        Args:
            score: Similarity score
        
        Returns:
            Duplicate type
        """
        if score >= 0.95:
            return DuplicateType.EXACT
        elif score >= 0.9:
            return DuplicateType.VERY_SIMILAR
        elif score >= 0.8:
            return DuplicateType.SIMILAR
        else:
            return DuplicateType.POTENTIALLY_SIMILAR
    
    def _explain_duplicate(
        self,
        entity_id_1: str,
        entity_id_2: str,
        score: float,
        confidence: float,
        duplicate_type: DuplicateType
    ) -> List[str]:
        """
        Generate explanation for duplicate detection
        
        Phase-2 requirement: Explain why entities are duplicates
        """
        reasons = []
        
        # Duplicate type explanation
        if duplicate_type == DuplicateType.EXACT:
            reasons.append(f"⚠️ Exact duplicate detected (similarity: {score:.3f})")
        elif duplicate_type == DuplicateType.VERY_SIMILAR:
            reasons.append(f"⚠️ Very similar entities (similarity: {score:.3f})")
        elif duplicate_type == DuplicateType.SIMILAR:
            reasons.append(f"Similar entities (similarity: {score:.3f})")
        else:
            reasons.append(f"Potentially similar (similarity: {score:.3f})")
        
        # Confidence explanation
        if confidence >= 0.9:
            reasons.append("Very high confidence - strong duplicate signal")
        elif confidence >= 0.8:
            reasons.append("High confidence duplicate")
        else:
            reasons.append("Moderate confidence - review recommended")
        
        # Actionable recommendation
        if duplicate_type in [DuplicateType.EXACT, DuplicateType.VERY_SIMILAR]:
            reasons.append(
                f"💡 Recommendation: Review {entity_id_1} and {entity_id_2} "
                "for consolidation"
            )
        
        return reasons


class ClusteringEngine:
    """
    Clusters entities using embedding-based clustering
    
    Phase-2 spec: Use DBSCAN or HDBSCAN on embeddings, no labels required
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        algorithm: str = "dbscan"
    ):
        """
        Initialize clustering engine
        
        Args:
            vector_store: Vector store for retrieving embeddings
            embedding_provider: Embedding provider
            algorithm: Clustering algorithm (dbscan or hdbscan)
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.algorithm = algorithm
        
        logger.info(f"Initialized clustering engine (algorithm: {algorithm})")
    
    def cluster_entities(
        self,
        entity_ids: List[str],
        entity_type: str,
        min_cluster_size: int = 3,
        eps: float = 0.3  # Distance threshold for DBSCAN
    ) -> List[Cluster]:
        """
        Cluster entities using their embeddings
        
        Args:
            entity_ids: List of entity IDs to cluster
            entity_type: Entity type
            min_cluster_size: Minimum cluster size
            eps: Distance threshold for DBSCAN
        
        Returns:
            List of clusters
        """
        try:
            from sklearn.cluster import DBSCAN
            from datetime import datetime
            
            # Retrieve embeddings for all entities
            logger.info(f"Retrieving embeddings for {len(entity_ids)} entities...")
            # Note: In production, implement batch retrieval in vector_store
            embeddings = []
            valid_ids = []
            
            for entity_id in entity_ids:
                # This is a simplified version - implement proper batch retrieval
                # For now, we'll document this limitation
                logger.warning(
                    "Batch embedding retrieval not yet implemented. "
                    "Use vector_store.get_embeddings_batch() when available."
                )
                # Placeholder: would retrieve from vector store
                # embedding = self.vector_store.get(entity_id)
                # if embedding:
                #     embeddings.append(embedding)
                #     valid_ids.append(entity_id)
            
            if len(embeddings) < min_cluster_size:
                logger.warning(
                    f"Not enough embeddings for clustering "
                    f"(got {len(embeddings)}, need {min_cluster_size})"
                )
                return []
            
            # Convert to numpy array
            X = np.array(embeddings)
            
            # Perform DBSCAN clustering
            logger.info(f"Running DBSCAN clustering (eps={eps}, min_samples={min_cluster_size})...")
            clustering = DBSCAN(
                eps=eps,
                min_samples=min_cluster_size,
                metric='cosine'
            ).fit(X)
            
            labels = clustering.labels_
            
            # Build clusters
            clusters = []
            unique_labels = set(labels)
            
            for label in unique_labels:
                if label == -1:
                    # Skip noise points
                    continue
                
                # Get members of this cluster
                mask = labels == label
                member_ids = [valid_ids[i] for i in range(len(valid_ids)) if mask[i]]
                member_embeddings = X[mask]
                
                # Calculate centroid
                centroid = member_embeddings.mean(axis=0).tolist()
                
                # Calculate cluster confidence (cohesion)
                confidence = self._calculate_cluster_confidence(member_embeddings)
                
                cluster = Cluster(
                    cluster_id=f"{entity_type}_cluster_{label}",
                    members=member_ids,
                    centroid=centroid,
                    confidence=confidence,
                    entity_type=entity_type,
                    created_at=datetime.utcnow().isoformat()
                )
                
                clusters.append(cluster)
            
            logger.info(
                f"Created {len(clusters)} clusters from {len(entity_ids)} entities "
                f"({sum(c.size for c in clusters)} entities clustered)"
            )
            
            return clusters
            
        except ImportError:
            logger.error(
                "scikit-learn not available. Install with: pip install scikit-learn"
            )
            return []
        except Exception as e:
            logger.error(f"Clustering failed: {e}", exc_info=True)
            return []
    
    def _calculate_cluster_confidence(self, embeddings: np.ndarray) -> float:
        """
        Calculate cluster confidence based on cohesion
        
        Higher cohesion (lower variance) = higher confidence
        
        Args:
            embeddings: Cluster member embeddings
        
        Returns:
            Confidence score (0.0-1.0)
        """
        if len(embeddings) < 2:
            return 0.5  # Low confidence for singleton clusters
        
        # Calculate centroid
        centroid = embeddings.mean(axis=0)
        
        # Calculate average distance from centroid
        distances = np.linalg.norm(embeddings - centroid, axis=1)
        avg_distance = distances.mean()
        
        # Convert to confidence (lower distance = higher confidence)
        # Assume max meaningful distance is 1.0 (for normalized embeddings)
        confidence = max(0.0, 1.0 - avg_distance)
        
        return float(confidence)
