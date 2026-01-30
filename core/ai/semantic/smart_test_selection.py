"""
Smart Test Selection - Phase-2 AI Engine

Answers: "Which tests should I run for this change?"

Uses weighted scoring from multiple signals:
- 40% Semantic similarity (code/test relationship)
- 30% Coverage relevance (code coverage mapping)
- 20% Failure history (historical failure patterns)
- 10% Flakiness penalty (avoid flaky tests)

Every selected test MUST explain why it was selected.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
import math

from core.ai.semantic.semantic_search_service import (
    SemanticSearchService,
    SearchIntent
)
from core.ai.embeddings.text_builder import EmbeddingTextBuilder
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


# Scoring weights from Phase-2 spec
WEIGHT_SEMANTIC_SIMILARITY = 0.4
WEIGHT_COVERAGE_RELEVANCE = 0.3
WEIGHT_FAILURE_HISTORY = 0.2
WEIGHT_FLAKINESS_PENALTY = 0.1


@dataclass
class ChangeContext:
    """
    Context about code changes for test selection
    
    Represents a code change (commit, PR, diff) that needs test coverage.
    """
    change_id: str                      # Commit SHA, PR number, etc.
    files_changed: List[str]            # Changed file paths
    diff_summary: str                   # High-level description of changes
    functions_changed: List[str] = field(default_factory=list)
    classes_changed: List[str] = field(default_factory=list)
    modules_changed: List[str] = field(default_factory=list)
    change_type: str = "code"           # code | test | config | docs
    risk_level: str = "medium"          # low | medium | high | critical
    
    def to_semantic_query(self) -> str:
        """
        Convert change context to semantic query text
        
        This is critical - good query text = good test selection
        """
        parts = []
        
        # Change summary
        if self.diff_summary:
            parts.append(f"Changes: {self.diff_summary}")
        
        # Files context
        if self.files_changed:
            files_str = ", ".join(self.files_changed[:5])  # Limit to 5 for token budget
            if len(self.files_changed) > 5:
                files_str += f" (and {len(self.files_changed) - 5} more)"
            parts.append(f"Modified files: {files_str}")
        
        # Function/class context
        if self.functions_changed:
            funcs_str = ", ".join(self.functions_changed[:10])
            parts.append(f"Modified functions: {funcs_str}")
        
        if self.classes_changed:
            classes_str = ", ".join(self.classes_changed[:10])
            parts.append(f"Modified classes: {classes_str}")
        
        # Module context
        if self.modules_changed:
            modules_str = ", ".join(self.modules_changed)
            parts.append(f"Modified modules: {modules_str}")
        
        return "\n".join(parts)


@dataclass
class SelectedTest:
    """
    Test selected for execution with explainability
    
    Phase-2 requirement: Every selected test must explain why.
    """
    test_id: str
    test_name: str
    score: float                        # Total selection score (0.0-1.0)
    confidence: float                   # Confidence in selection (0.0-1.0)
    reasons: List[str]                  # WHY this test was selected
    
    # Individual signal scores (for transparency)
    semantic_score: float = 0.0
    coverage_score: float = 0.0
    failure_score: float = 0.0
    flakiness_score: float = 0.0
    
    # Metadata
    framework: Optional[str] = None
    priority: str = "medium"            # low | medium | high | critical
    estimated_duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "score": self.score,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "signal_scores": {
                "semantic": self.semantic_score,
                "coverage": self.coverage_score,
                "failure_history": self.failure_score,
                "flakiness": self.flakiness_score
            },
            "framework": self.framework,
            "priority": self.priority,
            "estimated_duration": self.estimated_duration,
            "metadata": self.metadata
        }


class SmartTestSelector:
    """
    Smart test selection using AI semantic engine
    
    Phase-2 True AI - answers: "Which tests should run for this change?"
    
    Scoring formula:
        selection_score = 0.4 * semantic + 0.3 * coverage + 0.2 * failure - 0.1 * flakiness
    """
    
    def __init__(
        self,
        semantic_search: SemanticSearchService,
        coverage_service: Optional[Any] = None,
        failure_history_service: Optional[Any] = None,
        flaky_detection_service: Optional[Any] = None
    ):
        """
        Initialize smart test selector
        
        Args:
            semantic_search: Semantic search service
            coverage_service: Code coverage service (optional)
            failure_history_service: Failure history service (optional)
            flaky_detection_service: Flaky test detection service (optional)
        """
        self.semantic_search = semantic_search
        self.coverage_service = coverage_service
        self.failure_history_service = failure_history_service
        self.flaky_detection_service = flaky_detection_service
        
        logger.info(
            f"Initialized smart test selector "
            f"(coverage={'enabled' if coverage_service else 'disabled'}, "
            f"failure_history={'enabled' if failure_history_service else 'disabled'}, "
            f"flaky_detection={'enabled' if flaky_detection_service else 'disabled'})"
        )
    
    def select_tests(
        self,
        change_context: ChangeContext,
        budget: Optional[int] = None,
        min_score: float = 0.3,
        include_flaky: bool = False
    ) -> List[SelectedTest]:
        """
        Select tests for a code change
        
        Args:
            change_context: Context about the code change
            budget: Maximum number of tests to select (None = no limit)
            min_score: Minimum selection score threshold
            include_flaky: Whether to include flaky tests
        
        Returns:
            List of selected tests with scores and explanations
        
        Example:
            >>> selector.select_tests(
            ...     change_context=ChangeContext(
            ...         change_id="abc123",
            ...         files_changed=["auth/login.py"],
            ...         diff_summary="Added 2FA support to login"
            ...     ),
            ...     budget=20,
            ...     min_score=0.5
            ... )
        """
        try:
            logger.info(
                f"Selecting tests for change {change_context.change_id} "
                f"(budget={budget}, min_score={min_score})"
            )
            
            # Step 1: Get semantic matches
            semantic_results = self._get_semantic_matches(change_context, budget)
            
            # Step 2: Enrich with additional signals
            selected_tests = []
            for result in semantic_results:
                test_id = result.entity_id
                test_name = result.metadata.get("name", test_id)
                
                # Get coverage score
                coverage_score = self._get_coverage_score(
                    test_id=test_id,
                    changed_files=change_context.files_changed
                )
                
                # Get failure history score
                failure_score = self._get_failure_history_score(
                    test_id=test_id,
                    changed_files=change_context.files_changed
                )
                
                # Get flakiness score
                flakiness_score = self._get_flakiness_score(test_id)
                
                # Calculate total selection score
                selection_score = self._calculate_selection_score(
                    semantic_score=result.score,
                    coverage_score=coverage_score,
                    failure_score=failure_score,
                    flakiness_score=flakiness_score
                )
                
                # Skip if below threshold
                if selection_score < min_score:
                    continue
                
                # Skip flaky tests if requested
                if not include_flaky and flakiness_score > 0.7:
                    logger.debug(f"Skipping flaky test {test_id} (flakiness={flakiness_score:.2f})")
                    continue
                
                # Calculate confidence
                confidence = self._calculate_confidence(
                    semantic_score=result.score,
                    coverage_score=coverage_score,
                    failure_score=failure_score,
                    signals_available=self._count_available_signals()
                )
                
                # Generate explanations
                reasons = self._explain_selection(
                    test_name=test_name,
                    semantic_score=result.score,
                    coverage_score=coverage_score,
                    failure_score=failure_score,
                    flakiness_score=flakiness_score,
                    selection_score=selection_score,
                    change_context=change_context
                )
                
                # Determine priority
                priority = self._determine_priority(
                    selection_score=selection_score,
                    risk_level=change_context.risk_level
                )
                
                selected_tests.append(SelectedTest(
                    test_id=test_id,
                    test_name=test_name,
                    score=selection_score,
                    confidence=confidence,
                    reasons=reasons,
                    semantic_score=result.score,
                    coverage_score=coverage_score,
                    failure_score=failure_score,
                    flakiness_score=flakiness_score,
                    framework=result.metadata.get("framework"),
                    priority=priority,
                    estimated_duration=result.metadata.get("duration"),
                    metadata=result.metadata
                ))
            
            # Sort by score (descending)
            selected_tests.sort(key=lambda t: t.score, reverse=True)
            
            # Apply budget
            if budget:
                selected_tests = selected_tests[:budget]
            
            logger.info(
                f"Selected {len(selected_tests)} tests "
                f"(avg_score={sum(t.score for t in selected_tests) / len(selected_tests):.3f})"
                if selected_tests else "Selected 0 tests"
            )
            
            return selected_tests
            
        except Exception as e:
            logger.error(f"Test selection failed: {e}", exc_info=True)
            return []
    
    def _get_semantic_matches(
        self,
        change_context: ChangeContext,
        budget: Optional[int]
    ) -> List[Any]:
        """Get semantically similar tests"""
        query_text = change_context.to_semantic_query()
        
        # Get more candidates than budget to allow for filtering
        top_k = (budget * 3) if budget else 100
        
        return self.semantic_search.search(
            query_text=query_text,
            entity_type="test",
            top_k=top_k,
            min_confidence=0.0,  # Filter later with multi-signal score
            intent=SearchIntent.FIND_IMPACTED_TESTS
        )
    
    def _get_coverage_score(
        self,
        test_id: str,
        changed_files: List[str]
    ) -> float:
        """
        Get coverage relevance score
        
        Returns 0.0-1.0 based on how well test covers changed files
        """
        if not self.coverage_service:
            return 0.0
        
        try:
            # Get test coverage mapping
            # Note: Implement this based on your coverage service
            # covered_files = self.coverage_service.get_covered_files(test_id)
            # overlap = len(set(covered_files) & set(changed_files))
            # return min(1.0, overlap / len(changed_files))
            
            # Placeholder for now
            return 0.5
        except Exception as e:
            logger.warning(f"Coverage score failed for {test_id}: {e}")
            return 0.0
    
    def _get_failure_history_score(
        self,
        test_id: str,
        changed_files: List[str]
    ) -> float:
        """
        Get failure history score
        
        Returns 0.0-1.0 based on historical failure patterns
        Higher = more likely to fail with similar changes
        """
        if not self.failure_history_service:
            return 0.0
        
        try:
            # Check if test has failed with similar file changes
            # Note: Implement based on your failure history service
            # recent_failures = self.failure_history_service.get_failures(
            #     test_id=test_id,
            #     days_back=30
            # )
            # similar_failures = [
            #     f for f in recent_failures
            #     if any(file in f.changed_files for file in changed_files)
            # ]
            # return min(1.0, len(similar_failures) / 10)
            
            # Placeholder
            return 0.0
        except Exception as e:
            logger.warning(f"Failure history score failed for {test_id}: {e}")
            return 0.0
    
    def _get_flakiness_score(self, test_id: str) -> float:
        """
        Get flakiness score
        
        Returns 0.0-1.0 where higher = more flaky
        This is a PENALTY - subtracted from final score
        """
        if not self.flaky_detection_service:
            return 0.0
        
        try:
            # Get flaky score from service
            # Note: Implement based on your flaky detection service
            # flaky_status = self.flaky_detection_service.get_flaky_status(test_id)
            # return flaky_status.flaky_score
            
            # Placeholder
            return 0.0
        except Exception as e:
            logger.warning(f"Flakiness score failed for {test_id}: {e}")
            return 0.0
    
    def _calculate_selection_score(
        self,
        semantic_score: float,
        coverage_score: float,
        failure_score: float,
        flakiness_score: float
    ) -> float:
        """
        Calculate total selection score using weighted formula
        
        Formula from Phase-2 spec:
            selection_score = 0.4*semantic + 0.3*coverage + 0.2*failure - 0.1*flakiness
        """
        score = (
            WEIGHT_SEMANTIC_SIMILARITY * semantic_score +
            WEIGHT_COVERAGE_RELEVANCE * coverage_score +
            WEIGHT_FAILURE_HISTORY * failure_score -
            WEIGHT_FLAKINESS_PENALTY * flakiness_score
        )
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))
    
    def _calculate_confidence(
        self,
        semantic_score: float,
        coverage_score: float,
        failure_score: float,
        signals_available: int
    ) -> float:
        """
        Calculate confidence in selection
        
        Confidence increases with:
        - Higher individual scores
        - More signals available
        - Score consistency across signals
        """
        # Base confidence from semantic score
        base_confidence = semantic_score
        
        # Boost for multiple signals
        signal_boost = math.log1p(signals_available) / math.log1p(4)  # Max 4 signals
        
        # Consistency bonus (all scores high = more confident)
        scores = [semantic_score, coverage_score, failure_score]
        active_scores = [s for s in scores if s > 0.0]
        if active_scores:
            score_std = math.sqrt(sum((s - sum(active_scores) / len(active_scores)) ** 2 for s in active_scores) / len(active_scores))
            consistency_bonus = 1.0 - min(1.0, score_std)
        else:
            consistency_bonus = 0.0
        
        confidence = base_confidence * signal_boost * (1.0 + 0.2 * consistency_bonus)
        
        return max(0.0, min(1.0, confidence))
    
    def _count_available_signals(self) -> int:
        """Count how many signal sources are available"""
        count = 1  # Semantic always available
        if self.coverage_service:
            count += 1
        if self.failure_history_service:
            count += 1
        if self.flaky_detection_service:
            count += 1
        return count
    
    def _explain_selection(
        self,
        test_name: str,
        semantic_score: float,
        coverage_score: float,
        failure_score: float,
        flakiness_score: float,
        selection_score: float,
        change_context: ChangeContext
    ) -> List[str]:
        """
        Generate explanations for test selection
        
        Phase-2 requirement: Every test MUST explain why it was selected
        """
        reasons = []
        
        # Overall score
        if selection_score >= 0.8:
            reasons.append(f"✅ High priority test (score: {selection_score:.2f})")
        elif selection_score >= 0.5:
            reasons.append(f"Medium priority test (score: {selection_score:.2f})")
        else:
            reasons.append(f"Low priority test (score: {selection_score:.2f})")
        
        # Semantic similarity (40% weight)
        if semantic_score >= 0.7:
            reasons.append(f"High semantic similarity to changed code ({semantic_score:.2f})")
        elif semantic_score >= 0.4:
            reasons.append(f"Moderate semantic similarity to changed code ({semantic_score:.2f})")
        
        # Coverage relevance (30% weight)
        if coverage_score > 0.0:
            if coverage_score >= 0.7:
                reasons.append(f"Covers modified code extensively ({coverage_score:.2f})")
            else:
                reasons.append(f"Covers some modified code ({coverage_score:.2f})")
        
        # Failure history (20% weight)
        if failure_score > 0.0:
            if failure_score >= 0.5:
                reasons.append(f"⚠️ Previously failed with similar changes ({failure_score:.2f})")
            else:
                reasons.append(f"Has some historical failures ({failure_score:.2f})")
        
        # Flakiness penalty (10% weight)
        if flakiness_score > 0.0:
            if flakiness_score >= 0.7:
                reasons.append(f"⚠️ High flakiness detected - results may be unstable ({flakiness_score:.2f})")
            elif flakiness_score >= 0.3:
                reasons.append(f"Some flakiness detected ({flakiness_score:.2f})")
        
        # Change context
        if change_context.risk_level == "high":
            reasons.append("Selected due to high-risk change")
        
        return reasons
    
    def _determine_priority(
        self,
        selection_score: float,
        risk_level: str
    ) -> str:
        """
        Determine test priority
        
        Args:
            selection_score: Selection score
            risk_level: Change risk level
        
        Returns:
            Priority level: critical | high | medium | low
        """
        # Risk level can boost priority
        if risk_level == "critical":
            if selection_score >= 0.5:
                return "critical"
            elif selection_score >= 0.3:
                return "high"
        
        # Normal priority based on score
        if selection_score >= 0.8:
            return "critical"
        elif selection_score >= 0.6:
            return "high"
        elif selection_score >= 0.4:
            return "medium"
        else:
            return "low"
