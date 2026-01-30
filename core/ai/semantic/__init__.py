"""
Semantic AI Module - Phase-2 True AI Engine

Complete semantic intelligence layer for CrossBridge:
- Semantic search with confidence calibration
- Duplicate detection and clustering  
- Smart test selection
- Explainable AI results

All features are versioned and production-ready.
"""

from core.ai.semantic.semantic_search_service import (
    SemanticSearchService,
    SemanticResult,
    SearchIntent,
    create_semantic_search_service
)
from core.ai.semantic.duplicate_detection import (
    DuplicateDetector,
    ClusteringEngine,
    DuplicateMatch,
    DuplicateType,
    Cluster,
    DUPLICATE_SIMILARITY_THRESHOLD,
    DUPLICATE_CONFIDENCE_THRESHOLD
)
from core.ai.semantic.smart_test_selection import (
    SmartTestSelector,
    SelectedTest,
    ChangeContext,
    WEIGHT_SEMANTIC_SIMILARITY,
    WEIGHT_COVERAGE_RELEVANCE,
    WEIGHT_FAILURE_HISTORY,
    WEIGHT_FLAKINESS_PENALTY
)

__all__ = [
    # Semantic Search
    "SemanticSearchService",
    "SemanticResult",
    "SearchIntent",
    "create_semantic_search_service",
    
    # Duplicate Detection & Clustering
    "DuplicateDetector",
    "ClusteringEngine",
    "DuplicateMatch",
    "DuplicateType",
    "Cluster",
    "DUPLICATE_SIMILARITY_THRESHOLD",
    "DUPLICATE_CONFIDENCE_THRESHOLD",
    
    # Smart Test Selection
    "SmartTestSelector",
    "SelectedTest",
    "ChangeContext",
    "WEIGHT_SEMANTIC_SIMILARITY",
    "WEIGHT_COVERAGE_RELEVANCE",
    "WEIGHT_FAILURE_HISTORY",
    "WEIGHT_FLAKINESS_PENALTY",
]
