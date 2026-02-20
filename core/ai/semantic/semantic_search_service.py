"""
Semantic Search Service - Phase-2 True AI Engine

Provides high-level semantic search API with:
- Confidence calibration
- Query intent understanding
- Result ranking and filtering
- Explainable results

This is the main entry point for semantic operations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import math

from core.ai.embeddings.provider import EmbeddingProvider
from core.ai.embeddings.vector_store import VectorStore, SimilarityResult
from core.ai.embeddings.text_builder import EmbeddingTextBuilder
from core.ai.embeddings.embedding_version import (
    EMBEDDING_VERSION,
    get_current_version_info
)
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


class SearchIntent(Enum):
    """
    Query intent classification
    
    Helps optimize search and explain results.
    """
    FIND_SIMILAR_TESTS = "find_similar_tests"
    FIND_RELATED_FAILURES = "find_related_failures"
    FIND_IMPACTED_TESTS = "find_impacted_tests"
    FIND_DUPLICATES = "find_duplicates"
    GENERAL_SEARCH = "general_search"


@dataclass
class SemanticResult:
    """
    Semantic search result with confidence and explainability
    
    Phase-2 enhancement: Every result must explain itself.
    """
    entity_id: str
    entity_type: str
    score: float                    # Raw similarity score (0.0-1.0)
    confidence: float               # Calibrated confidence (0.0-1.0)
    reasons: List[str]              # Explainability: why this result?
    text: str                       # Original text
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "score": self.score,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "text": self.text,
            "metadata": self.metadata
        }


class SemanticSearchService:
    """
    High-level semantic search service
    
    Phase-2 True AI Engine - provides:
    - Intent-aware search
    - Confidence calibration
    - Result ranking
    - Explainability
    """
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        text_builder: Optional[EmbeddingTextBuilder] = None
    ):
        """
        Initialize semantic search service
        
        Args:
            embedding_provider: Provider for generating embeddings
            vector_store: Vector store for similarity search
            text_builder: Text builder for creating embeddings (optional)
        """
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.text_builder = text_builder or EmbeddingTextBuilder()
        
        # Get current version info
        self.version_info = get_current_version_info(
            model=embedding_provider.model_name,
            dimensions=embedding_provider.get_dimension(),
            ast_augmented=text_builder.enable_ast_augmentation if text_builder else True
        )
        
        logger.info(
            f"Initialized semantic search with {embedding_provider.model_name} "
            f"(version: {EMBEDDING_VERSION})"
        )
    
    def search(
        self,
        query_text: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
        min_confidence: float = 0.0,
        intent: SearchIntent = SearchIntent.GENERAL_SEARCH,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SemanticResult]:
        """
        Semantic search with confidence and explainability
        
        Args:
            query_text: Natural language query
            entity_type: Filter by entity type (test, scenario, failure)
            top_k: Number of results to return
            min_confidence: Minimum confidence threshold
            intent: Search intent for optimization
            filters: Additional metadata filters
        
        Returns:
            List of semantic results with confidence and reasons
        
        Example:
            >>> service.search(
            ...     "tests for user authentication",
            ...     entity_type="test",
            ...     top_k=5,
            ...     intent=SearchIntent.FIND_SIMILAR_TESTS
            ... )
        """
        try:
            # Generate query embedding
            logger.debug(f"Generating embedding for query: {query_text[:100]}...")
            query_embeddings = self.embedding_provider.embed([query_text])
            query_embedding = query_embeddings[0]  # Extract single embedding from list
            
            # Prepare filters for vector store
            search_filters = filters or {}
            if entity_type:
                search_filters["type"] = entity_type
            
            # Perform vector search using the standard query() method
            logger.debug(f"Searching vector store (top_k={top_k}, type={entity_type})...")
            raw_results = self.vector_store.query(
                vector=query_embedding,
                top_k=top_k * 2,  # Get more results for filtering
                filters=search_filters
            )
            
            # Convert MemoryRecord results to SimilarityResult format
            similarity_results = []
            for r in raw_results:
                record = r["record"]
                similarity_results.append(SimilarityResult(
                    id=record.id,
                    entity_type=record.type.value,
                    score=r["score"],
                    text=record.text,
                    metadata=record.metadata,
                    embedding=record.embedding
                ))
            
            # Convert to semantic results with confidence and explanations
            semantic_results = []
            for sim_result in similarity_results:
                # Calibrate confidence based on score and sample count
                confidence = self._calibrate_confidence(
                    score=sim_result.score,
                    entity_type=entity_type or "all",
                    sample_count=len(similarity_results)
                )
                
                # Skip if below confidence threshold
                if confidence < min_confidence:
                    continue
                
                # Generate explanations
                reasons = self._explain_result(
                    query_text=query_text,
                    result=sim_result,
                    score=sim_result.score,
                    confidence=confidence,
                    intent=intent
                )
                
                semantic_results.append(SemanticResult(
                    entity_id=sim_result.id,
                    entity_type=sim_result.entity_type,
                    score=sim_result.score,
                    confidence=confidence,
                    reasons=reasons,
                    text=sim_result.text,
                    metadata=sim_result.metadata
                ))
                
                # Stop if we have enough results
                if len(semantic_results) >= top_k:
                    break
            
            logger.info(
                f"Found {len(semantic_results)} results for query "
                f"(filtered from {len(similarity_results)} candidates)"
            )
            
            return semantic_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            raise
    
    def _calibrate_confidence(
        self,
        score: float,
        entity_type: str,
        sample_count: int
    ) -> float:
        """
        Calibrate confidence based on similarity score and context
        
        Uses logarithmic calibration:
        - Higher scores get boosted more
        - More samples increase confidence
        - Plateaus at ~30 samples
        
        Args:
            score: Raw similarity score (0.0-1.0)
            entity_type: Entity type for type-specific calibration
            sample_count: Number of samples in result set
        
        Returns:
            Calibrated confidence (0.0-1.0)
        """
        # Base calibration using logarithmic scaling
        # This is the standard formula from the spec
        base_confidence = score * math.log1p(sample_count) / math.log1p(30)
        
        # Clamp to [0.0, 1.0]
        calibrated = max(0.0, min(1.0, base_confidence))
        
        logger.debug(
            f"Calibrated confidence: {score:.3f} -> {calibrated:.3f} "
            f"(samples={sample_count}, type={entity_type})"
        )
        
        return calibrated
    
    def _explain_result(
        self,
        query_text: str,
        result: SimilarityResult,
        score: float,
        confidence: float,
        intent: SearchIntent
    ) -> List[str]:
        """
        Generate explanations for why this result was returned
        
        Phase-2 requirement: Every result must explain itself.
        
        Args:
            query_text: Original query
            result: Similarity result
            score: Similarity score
            confidence: Calibrated confidence
            intent: Search intent
        
        Returns:
            List of explanation strings
        """
        reasons = []
        
        # High similarity explanation
        if score >= 0.9:
            reasons.append(f"Very high semantic similarity ({score:.2f})")
        elif score >= 0.7:
            reasons.append(f"High semantic similarity ({score:.2f})")
        elif score >= 0.5:
            reasons.append(f"Moderate semantic similarity ({score:.2f})")
        else:
            reasons.append(f"Low semantic similarity ({score:.2f})")
        
        # Confidence explanation
        if confidence >= 0.8:
            reasons.append("High confidence based on robust evidence")
        elif confidence >= 0.5:
            reasons.append("Moderate confidence")
        else:
            reasons.append("Low confidence - verify relevance")
        
        # Intent-specific explanations
        if intent == SearchIntent.FIND_SIMILAR_TESTS:
            reasons.append("Test selected based on semantic similarity to query")
        elif intent == SearchIntent.FIND_RELATED_FAILURES:
            reasons.append("Failure pattern matches query characteristics")
        elif intent == SearchIntent.FIND_IMPACTED_TESTS:
            reasons.append("Test may be impacted based on semantic overlap")
        elif intent == SearchIntent.FIND_DUPLICATES:
            if score >= 0.9 and confidence >= 0.8:
                reasons.append("⚠️ Potential duplicate detected")
        
        # Entity type context
        entity_desc = {
            "test": "test case",
            "scenario": "test scenario",
            "failure": "failure pattern"
        }.get(result.entity_type, "entity")
        
        reasons.append(f"Matched {entity_desc}: {result.id}")
        
        return reasons


def create_semantic_search_service(
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    enable_ast_augmentation: bool = True
) -> SemanticSearchService:
    """
    Factory function to create semantic search service
    
    Args:
        embedding_provider: Embedding provider
        vector_store: Vector store
        enable_ast_augmentation: Enable AST text augmentation
    
    Returns:
        Configured semantic search service
    """
    text_builder = EmbeddingTextBuilder(
        enable_ast_augmentation=enable_ast_augmentation
    )
    
    return SemanticSearchService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        text_builder=text_builder
    )
