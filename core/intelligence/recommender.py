"""
Test Recommendation Engine for CrossBridge Intelligent Test Assistance.

Recommends tests to run based on code changes, feature names, or failure patterns.
Uses hybrid intelligence: semantic similarity + structural overlap + priority.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from core.intelligence.models import UnifiedTestMemory, calculate_structural_overlap
from core.memory.search import SemanticSearchEngine

logger = logging.getLogger(__name__)


class RecommendationReason(Enum):
    """Reason for test recommendation."""
    
    SEMANTIC_SIMILARITY = "semantic_similarity"
    STRUCTURAL_OVERLAP = "structural_overlap"
    HIGH_PRIORITY = "high_priority"
    RECENT_FAILURE = "recent_failure"
    FLAKY_HISTORY = "flaky_history"
    FEATURE_MATCH = "feature_match"
    CODE_CHANGE_IMPACT = "code_change_impact"


@dataclass
class TestRecommendation:
    """A single test recommendation with reasoning."""
    
    test_id: str
    test_name: str
    framework: str
    confidence: float  # 0.0-1.0
    reasons: List[RecommendationReason]
    reasoning_text: str  # Human-readable explanation
    priority: str  # P0, P1, P2, P3
    estimated_runtime_seconds: Optional[int] = None


@dataclass
class RecommendationResult:
    """Result of test recommendation."""
    
    recommended_tests: List[TestRecommendation]
    total_candidates: int
    reasoning_summary: str
    estimated_total_runtime: int  # seconds


class TestRecommender:
    """
    Test recommendation engine using hybrid intelligence.
    
    Ranking Formula:
    score = (0.5 * semantic_similarity) + (0.3 * structural_overlap) + (0.2 * priority_weight)
    
    Use Cases:
    1. Code changes: "I modified checkout.py"
    2. Feature name: "I'm working on payment processing"
    3. Failure pattern: "Tests are failing with 500 errors"
    """
    
    def __init__(
        self,
        search_engine: SemanticSearchEngine,
    ):
        """
        Initialize recommender.
        
        Args:
            search_engine: Semantic search engine for retrieval
        """
        self.search_engine = search_engine
        
        # Weights for ranking
        self.semantic_weight = 0.5
        self.structural_weight = 0.3
        self.priority_weight = 0.2
    
    def recommend_for_code_changes(
        self,
        changed_files: List[str],
        max_recommendations: int = 20,
        min_confidence: float = 0.6,
    ) -> RecommendationResult:
        """
        Recommend tests for code changes.
        
        Args:
            changed_files: List of changed file paths
            max_recommendations: Maximum tests to recommend
            min_confidence: Minimum confidence threshold
            
        Returns:
            RecommendationResult with ranked tests
        """
        logger.info(f"Recommending tests for {len(changed_files)} changed files")
        
        # Build search query from file names
        query = self._build_query_from_files(changed_files)
        
        # Retrieve candidate tests
        candidates = self._retrieve_candidates(
            query=query,
            max_candidates=max_recommendations * 3,  # Over-retrieve for ranking
        )
        
        # Rank candidates
        recommendations = self._rank_candidates(
            candidates=candidates,
            query=query,
            reason=RecommendationReason.CODE_CHANGE_IMPACT,
        )
        
        # Filter by confidence
        recommendations = [r for r in recommendations if r.confidence >= min_confidence]
        
        # Limit to max
        recommendations = recommendations[:max_recommendations]
        
        # Calculate total runtime
        total_runtime = sum(
            r.estimated_runtime_seconds or 0 for r in recommendations
        )
        
        reasoning = (
            f"Recommended {len(recommendations)} tests based on code changes to "
            f"{len(changed_files)} files. Tests selected for semantic relevance "
            f"and structural overlap with modified code."
        )
        
        return RecommendationResult(
            recommended_tests=recommendations,
            total_candidates=len(candidates),
            reasoning_summary=reasoning,
            estimated_total_runtime=total_runtime,
        )
    
    def recommend_for_feature(
        self,
        feature_name: str,
        max_recommendations: int = 20,
        min_confidence: float = 0.6,
    ) -> RecommendationResult:
        """
        Recommend tests for a feature.
        
        Args:
            feature_name: Name or description of feature
            max_recommendations: Maximum tests to recommend
            min_confidence: Minimum confidence threshold
            
        Returns:
            RecommendationResult with ranked tests
        """
        logger.info(f"Recommending tests for feature: {feature_name}")
        
        # Retrieve candidate tests
        candidates = self._retrieve_candidates(
            query=feature_name,
            max_candidates=max_recommendations * 3,
        )
        
        # Rank candidates
        recommendations = self._rank_candidates(
            candidates=candidates,
            query=feature_name,
            reason=RecommendationReason.FEATURE_MATCH,
        )
        
        # Filter by confidence
        recommendations = [r for r in recommendations if r.confidence >= min_confidence]
        
        # Limit to max
        recommendations = recommendations[:max_recommendations]
        
        # Calculate total runtime
        total_runtime = sum(
            r.estimated_runtime_seconds or 0 for r in recommendations
        )
        
        reasoning = (
            f"Recommended {len(recommendations)} tests for feature '{feature_name}'. "
            f"Tests selected based on semantic similarity to feature description."
        )
        
        return RecommendationResult(
            recommended_tests=recommendations,
            total_candidates=len(candidates),
            reasoning_summary=reasoning,
            estimated_total_runtime=total_runtime,
        )
    
    def recommend_for_failure_pattern(
        self,
        failure_description: str,
        max_recommendations: int = 20,
        min_confidence: float = 0.6,
    ) -> RecommendationResult:
        """
        Recommend tests based on failure pattern.
        
        Args:
            failure_description: Description of failure (e.g., "500 errors in checkout")
            max_recommendations: Maximum tests to recommend
            min_confidence: Minimum confidence threshold
            
        Returns:
            RecommendationResult with ranked tests
        """
        logger.info(f"Recommending tests for failure: {failure_description}")
        
        # Retrieve candidate tests
        candidates = self._retrieve_candidates(
            query=failure_description,
            max_candidates=max_recommendations * 3,
        )
        
        # Rank candidates
        recommendations = self._rank_candidates(
            candidates=candidates,
            query=failure_description,
            reason=RecommendationReason.RECENT_FAILURE,
        )
        
        # Filter by confidence
        recommendations = [r for r in recommendations if r.confidence >= min_confidence]
        
        # Limit to max
        recommendations = recommendations[:max_recommendations]
        
        # Calculate total runtime
        total_runtime = sum(
            r.estimated_runtime_seconds or 0 for r in recommendations
        )
        
        reasoning = (
            f"Recommended {len(recommendations)} tests to diagnose failure pattern. "
            f"Tests selected for similarity to reported failure: '{failure_description}'"
        )
        
        return RecommendationResult(
            recommended_tests=recommendations,
            total_candidates=len(candidates),
            reasoning_summary=reasoning,
            estimated_total_runtime=total_runtime,
        )
    
    def _build_query_from_files(self, changed_files: List[str]) -> str:
        """Build search query from changed file paths."""
        # Extract meaningful parts from file paths
        parts = []
        for file_path in changed_files:
            # Get filename without extension
            filename = file_path.split("/")[-1].split("\\")[-1]
            name_without_ext = filename.rsplit(".", 1)[0]
            
            # Convert snake_case or camelCase to words
            words = name_without_ext.replace("_", " ").replace("-", " ")
            parts.append(words)
        
        return " ".join(parts)
    
    def _retrieve_candidates(
        self,
        query: str,
        max_candidates: int,
    ) -> List[UnifiedTestMemory]:
        """Retrieve candidate tests via semantic search."""
        # Search for relevant tests
        search_results = self.search_engine.search(
            query=query,
            entity_types=["test_case", "test"],
            top_k=max_candidates,
        )
        
        # TODO: Load UnifiedTestMemory objects from database
        # For now, return empty list
        return []
    
    def _rank_candidates(
        self,
        candidates: List[UnifiedTestMemory],
        query: str,
        reason: RecommendationReason,
    ) -> List[TestRecommendation]:
        """Rank candidates using hybrid scoring."""
        recommendations = []
        
        for candidate in candidates:
            # Calculate semantic similarity (from search result)
            semantic_score = 0.8  # Placeholder - should come from search result
            
            # Calculate structural overlap (if applicable)
            structural_score = self._calculate_structural_score(candidate)
            
            # Calculate priority weight
            priority_score = self._calculate_priority_score(candidate)
            
            # Combined score
            confidence = (
                self.semantic_weight * semantic_score +
                self.structural_weight * structural_score +
                self.priority_weight * priority_score
            )
            
            # Determine reasons
            reasons = [reason]
            if semantic_score > 0.8:
                reasons.append(RecommendationReason.SEMANTIC_SIMILARITY)
            if structural_score > 0.7:
                reasons.append(RecommendationReason.STRUCTURAL_OVERLAP)
            if candidate.metadata and candidate.metadata.priority in ["P0", "P1"]:
                reasons.append(RecommendationReason.HIGH_PRIORITY)
            if candidate.metadata and candidate.metadata.flakiness_score > 0.5:
                reasons.append(RecommendationReason.FLAKY_HISTORY)
            
            # Build reasoning text
            reasoning_text = self._build_reasoning_text(candidate, reasons, confidence)
            
            recommendations.append(
                TestRecommendation(
                    test_id=candidate.test_id,
                    test_name=candidate.semantic.intent_text if candidate.semantic else candidate.test_id,
                    framework=candidate.framework,
                    confidence=confidence,
                    reasons=reasons,
                    reasoning_text=reasoning_text,
                    priority=candidate.metadata.priority if candidate.metadata else "P2",
                    estimated_runtime_seconds=None,  # TODO: Get from test metadata
                )
            )
        
        # Sort by confidence descending
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        
        return recommendations
    
    def _calculate_structural_score(self, test: UnifiedTestMemory) -> float:
        """Calculate structural relevance score."""
        if not test.structural:
            return 0.0
        
        score = 0.0
        
        # Reward for API calls
        if test.structural.api_calls:
            score += min(0.3, len(test.structural.api_calls) * 0.1)
        
        # Reward for assertions
        if test.structural.assertions:
            score += min(0.3, len(test.structural.assertions) * 0.1)
        
        # Reward for complex logic
        if test.structural.has_conditional:
            score += 0.1
        if test.structural.has_loop:
            score += 0.1
        if test.structural.has_retry_logic:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_priority_score(self, test: UnifiedTestMemory) -> float:
        """Calculate priority-based score."""
        if not test.metadata or not test.metadata.priority:
            return 0.5  # Default
        
        priority_map = {
            "P0": 1.0,
            "P1": 0.8,
            "P2": 0.5,
            "P3": 0.3,
        }
        
        return priority_map.get(test.metadata.priority, 0.5)
    
    def _build_reasoning_text(
        self,
        test: UnifiedTestMemory,
        reasons: List[RecommendationReason],
        confidence: float,
    ) -> str:
        """Build human-readable reasoning text."""
        parts = []
        
        parts.append(f"Confidence: {confidence:.2f}")
        
        for reason in reasons:
            if reason == RecommendationReason.SEMANTIC_SIMILARITY:
                parts.append("High semantic similarity to query")
            elif reason == RecommendationReason.STRUCTURAL_OVERLAP:
                parts.append("Similar test structure")
            elif reason == RecommendationReason.HIGH_PRIORITY:
                parts.append("High priority test")
            elif reason == RecommendationReason.FLAKY_HISTORY:
                parts.append("Has flaky history")
            elif reason == RecommendationReason.CODE_CHANGE_IMPACT:
                parts.append("Likely impacted by code changes")
            elif reason == RecommendationReason.FEATURE_MATCH:
                parts.append("Matches feature description")
            elif reason == RecommendationReason.RECENT_FAILURE:
                parts.append("Similar to recent failure pattern")
        
        if test.structural:
            parts.append(
                f"Contains {len(test.structural.api_calls)} API calls, "
                f"{len(test.structural.assertions)} assertions"
            )
        
        return ". ".join(parts)


def recommend_tests_for_changes(
    changed_files: List[str],
    search_engine: SemanticSearchEngine,
    max_recommendations: int = 20,
) -> RecommendationResult:
    """
    Convenience function to recommend tests for code changes.
    
    Args:
        changed_files: List of changed file paths
        search_engine: Semantic search engine instance
        max_recommendations: Maximum tests to recommend
        
    Returns:
        RecommendationResult with ranked tests
    """
    recommender = TestRecommender(search_engine)
    return recommender.recommend_for_code_changes(changed_files, max_recommendations)
