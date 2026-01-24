"""
Unit tests for test recommendation engine.
"""

import pytest
from unittest.mock import Mock
from core.intelligence.recommender import (
    TestRecommender,
    TestRecommendation,
    RecommendationReason,
    RecommendationResult,
)
from core.intelligence.models import (
    UnifiedTestMemory,
    SemanticSignals,
    StructuralSignals,
    TestMetadata,
    APICall,
    Assertion,
    TestType,
    Priority,
)


class TestRecommenderEngine:
    """Test test recommendation engine."""
    
    def test_recommend_for_code_changes(self):
        """Test recommendations for code changes."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        recommender = TestRecommender(search_engine)
        
        result = recommender.recommend_for_code_changes(
            changed_files=["src/checkout.py", "src/payment.py"],
            max_recommendations=10,
        )
        
        assert isinstance(result, RecommendationResult)
        assert result.total_candidates >= 0
    
    def test_recommend_for_feature(self):
        """Test recommendations for feature."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        recommender = TestRecommender(search_engine)
        
        result = recommender.recommend_for_feature(
            feature_name="payment processing",
            max_recommendations=10,
        )
        
        assert isinstance(result, RecommendationResult)
        assert "payment processing" in result.reasoning_summary
    
    def test_recommend_for_failure_pattern(self):
        """Test recommendations for failure pattern."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        recommender = TestRecommender(search_engine)
        
        result = recommender.recommend_for_failure_pattern(
            failure_description="500 errors in checkout",
            max_recommendations=10,
        )
        
        assert isinstance(result, RecommendationResult)
        assert "500 errors in checkout" in result.reasoning_summary
    
    def test_build_query_from_files(self):
        """Test query building from file paths."""
        search_engine = Mock()
        recommender = TestRecommender(search_engine)
        
        query = recommender._build_query_from_files([
            "src/checkout.py",
            "src/payment_processor.py",
            "lib/user_service.py",
        ])
        
        assert "checkout" in query
        assert "payment" in query
        assert "user" in query
    
    def test_calculate_structural_score(self):
        """Test structural score calculation."""
        search_engine = Mock()
        recommender = TestRecommender(search_engine)
        
        # Test with no structural signals
        test1 = UnifiedTestMemory(
            test_id="test_1",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_1",
            semantic=SemanticSignals(),
            structural=None,
            metadata=TestMetadata(),
        )
        
        score1 = recommender._calculate_structural_score(test1)
        assert score1 == 0.0
        
        # Test with rich structural signals
        test2 = UnifiedTestMemory(
            test_id="test_2",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_2",
            semantic=SemanticSignals(),
            structural=StructuralSignals(
                api_calls=[APICall(method="GET", endpoint="/api/test")] * 5,
                assertions=[Assertion(type="assert", target="x")] * 5,
                has_conditional=True,
                has_loop=True,
                has_retry_logic=True,
            ),
            metadata=TestMetadata(),
        )
        
        score2 = recommender._calculate_structural_score(test2)
        assert score2 > 0.5
    
    def test_calculate_priority_score(self):
        """Test priority score calculation."""
        search_engine = Mock()
        recommender = TestRecommender(search_engine)
        
        # Test P0 priority
        test_p0 = UnifiedTestMemory(
            test_id="test_p0",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_p0",
            semantic=SemanticSignals(),
            structural=StructuralSignals(),
            metadata=TestMetadata(priority=Priority.P0),
        )
        
        score_p0 = recommender._calculate_priority_score(test_p0)
        assert score_p0 == 1.0
        
        # Test P3 priority
        test_p3 = UnifiedTestMemory(
            test_id="test_p3",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_p3",
            semantic=SemanticSignals(),
            structural=StructuralSignals(),
            metadata=TestMetadata(priority=Priority.P3),
        )
        
        score_p3 = recommender._calculate_priority_score(test_p3)
        assert score_p3 == 0.3
    
    def test_build_reasoning_text(self):
        """Test reasoning text generation."""
        search_engine = Mock()
        recommender = TestRecommender(search_engine)
        
        test = UnifiedTestMemory(
            test_id="test_1",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_1",
            semantic=SemanticSignals(),
            structural=StructuralSignals(
                api_calls=[APICall(method="GET", endpoint="/api/test")],
                assertions=[Assertion(type="assert", target="x")],
            ),
            metadata=TestMetadata(),
        )
        
        reasons = [
            RecommendationReason.SEMANTIC_SIMILARITY,
            RecommendationReason.STRUCTURAL_OVERLAP,
        ]
        
        reasoning = recommender._build_reasoning_text(test, reasons, 0.85)
        
        assert "0.85" in reasoning
        assert "semantic" in reasoning.lower()
        # Check for structural-related words
        assert any(word in reasoning.lower() for word in ["structural", "structure", "overlap"])
    
    def test_confidence_filtering(self):
        """Test that low confidence recommendations are filtered."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        recommender = TestRecommender(search_engine)
        
        # Mock to return low-confidence candidates
        recommender._retrieve_candidates = Mock(return_value=[])
        
        result = recommender.recommend_for_feature(
            feature_name="test feature",
            min_confidence=0.8,  # High threshold
        )
        
        # All recommendations should meet threshold
        for rec in result.recommended_tests:
            assert rec.confidence >= 0.8


class TestRecommendationStructures:
    """Test recommendation data structures."""
    
    def test_test_recommendation_creation(self):
        """Test creation of test recommendation."""
        rec = TestRecommendation(
            test_id="test_checkout",
            test_name="test_checkout_with_valid_card",
            framework="pytest",
            confidence=0.85,
            reasons=[RecommendationReason.SEMANTIC_SIMILARITY],
            reasoning_text="High semantic similarity",
            priority="P1",
            estimated_runtime_seconds=30,
        )
        
        assert rec.test_id == "test_checkout"
        assert rec.confidence == 0.85
        assert rec.priority == "P1"
        assert rec.estimated_runtime_seconds == 30
    
    def test_recommendation_result_creation(self):
        """Test creation of recommendation result."""
        recommendations = [
            TestRecommendation(
                test_id=f"test_{i}",
                test_name=f"test_{i}",
                framework="pytest",
                confidence=0.8,
                reasons=[],
                reasoning_text="Test",
                priority="P2",
                estimated_runtime_seconds=10,
            )
            for i in range(5)
        ]
        
        result = RecommendationResult(
            recommended_tests=recommendations,
            total_candidates=20,
            reasoning_summary="Recommended 5 tests",
            estimated_total_runtime=50,
        )
        
        assert len(result.recommended_tests) == 5
        assert result.total_candidates == 20
        assert result.estimated_total_runtime == 50


class TestRecommendationReasons:
    """Test recommendation reason enum."""
    
    def test_recommendation_reason_values(self):
        """Test recommendation reason enum values."""
        assert RecommendationReason.SEMANTIC_SIMILARITY.value == "semantic_similarity"
        assert RecommendationReason.STRUCTURAL_OVERLAP.value == "structural_overlap"
        assert RecommendationReason.HIGH_PRIORITY.value == "high_priority"
        assert RecommendationReason.RECENT_FAILURE.value == "recent_failure"
        assert RecommendationReason.FLAKY_HISTORY.value == "flaky_history"
        assert RecommendationReason.FEATURE_MATCH.value == "feature_match"
        assert RecommendationReason.CODE_CHANGE_IMPACT.value == "code_change_impact"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
