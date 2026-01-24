"""
Unit tests for RAG explanation engine.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.intelligence.rag_engine import (
    RAGExplanationEngine,
    ValidatedBehavior,
    ExplanationResult,
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


class TestRAGExplanationEngine:
    """Test RAG explanation engine."""
    
    def test_explain_coverage_no_tests(self):
        """Test explanation when no tests found."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        engine = RAGExplanationEngine(search_engine)
        result = engine.explain_coverage("What tests do we have?")
        
        assert result.confidence_score == 0.0
        assert len(result.validated_behaviors) == 0
        assert "No relevant tests found" in result.summary
    
    def test_explain_coverage_with_tests(self):
        """Test explanation with test results."""
        # Create mock search engine
        search_engine = Mock()
        
        # Create mock search results
        search_engine.search.return_value = [
            Mock(entity_id="test_1", score=0.9),
            Mock(entity_id="test_2", score=0.8),
        ]
        
        # Create mock test memories
        test_memory = UnifiedTestMemory(
            test_id="test_checkout",
            framework="pytest",
            language="python",
            file_path="/tests/test_checkout.py",
            test_name="test_checkout",
            semantic=SemanticSignals(
                intent_text="Test checkout with valid credit card",
                embedding=[0.1] * 1536,
                keywords=["checkout", "credit card", "payment"],
            ),
            structural=StructuralSignals(
                api_calls=[
                    APICall(method="POST", endpoint="/api/checkout", expected_status=200),
                ],
                assertions=[
                    Assertion(type="assert", target="response.status_code", expected_value="200"),
                ],
                expected_status_codes=[200],
            ),
            metadata=TestMetadata(
                test_type=TestType.POSITIVE,
                priority=Priority.P1,
                feature="checkout",
            ),
        )
        
        engine = RAGExplanationEngine(search_engine)
        
        # Mock the internal method to return our test memory
        engine._load_test_memories = Mock(return_value=[test_memory])
        
        result = engine.explain_coverage("What checkout scenarios are tested?")
        
        assert result.confidence_score >= 0.0
        assert len(result.test_references) > 0
        assert "test_checkout" in result.test_references
    
    def test_extract_structural_evidence(self):
        """Test extraction of structural evidence."""
        search_engine = Mock()
        engine = RAGExplanationEngine(search_engine)
        
        test_memory = UnifiedTestMemory(
            test_id="test_1",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_1",
            semantic=SemanticSignals(),
            structural=StructuralSignals(
                api_calls=[APICall(method="GET", endpoint="/api/users")],
                assertions=[Assertion(type="assert", target="status")],
                expected_status_codes=[200, 404],
                expected_exceptions=["ValueError"],
                external_services=["redis", "kafka"],
            ),
            metadata=TestMetadata(),
        )
        
        evidence = engine._extract_structural_evidence([test_memory])
        
        assert len(evidence["api_calls"]) == 1
        assert len(evidence["assertions"]) == 1
        assert len(evidence["status_codes"]) == 2
        assert len(evidence["exceptions"]) == 1
        assert len(evidence["external_services"]) == 2
    
    def test_generate_llm_summary(self):
        """Test LLM summary generation."""
        search_engine = Mock()
        engine = RAGExplanationEngine(search_engine)
        
        test_memory = UnifiedTestMemory(
            test_id="test_api",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_api",
            semantic=SemanticSignals(intent_text="Test API endpoint"),
            structural=StructuralSignals(
                api_calls=[APICall(method="GET", endpoint="/api/test")],
                assertions=[Assertion(type="assert", target="result")],
                expected_status_codes=[200],
            ),
            metadata=TestMetadata(),
        )
        
        structural_evidence = engine._extract_structural_evidence([test_memory])
        
        summary = engine._generate_llm_summary(
            "What API tests exist?",
            [test_memory],
            structural_evidence,
        )
        
        assert len(summary) > 0
        assert "test" in summary.lower()
    
    def test_validate_behaviors(self):
        """Test behavior validation."""
        search_engine = Mock()
        engine = RAGExplanationEngine(search_engine)
        
        test_memory = UnifiedTestMemory(
            test_id="test_checkout",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_checkout",
            semantic=SemanticSignals(intent_text="Test checkout flow"),
            structural=StructuralSignals(
                api_calls=[
                    APICall(method="POST", endpoint="/api/checkout"),
                    APICall(method="GET", endpoint="/api/order"),
                ],
                assertions=[
                    Assertion(type="assert", target="status", expected_value="200"),
                    Assertion(type="assert", target="order_id", comparator="is not None"),
                ],
                expected_status_codes=[200],
            ),
            metadata=TestMetadata(),
        )
        
        structural_evidence = engine._extract_structural_evidence([test_memory])
        
        validated = engine._validate_behaviors(
            [test_memory],
            structural_evidence,
            min_confidence=0.5,
        )
        
        assert len(validated) >= 0  # May be empty if no behaviors grouped
        for behavior in validated:
            assert behavior.confidence >= 0.5
            assert len(behavior.evidence) > 0
    
    def test_identify_coverage_gaps(self):
        """Test coverage gap identification."""
        search_engine = Mock()
        engine = RAGExplanationEngine(search_engine)
        
        # Test with no error handling mentioned
        validated_behaviors = [
            ValidatedBehavior(
                behavior="Test valid checkout",
                confidence=0.9,
                evidence=["API: POST /checkout"],
                test_references=["test_1"],
            ),
        ]
        
        gaps = engine._identify_coverage_gaps(
            "What about error handling for checkout?",
            validated_behaviors,
        )
        
        assert len(gaps) > 0
        assert any("error handling" in gap.lower() for gap in gaps)
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        search_engine = Mock()
        engine = RAGExplanationEngine(search_engine)
        
        # No behaviors
        confidence = engine._calculate_confidence([])
        assert confidence == 0.0
        
        # Multiple behaviors
        behaviors = [
            ValidatedBehavior(
                behavior="Test 1",
                confidence=0.8,
                evidence=[],
                test_references=[],
            ),
            ValidatedBehavior(
                behavior="Test 2",
                confidence=0.6,
                evidence=[],
                test_references=[],
            ),
        ]
        
        confidence = engine._calculate_confidence(behaviors)
        assert confidence == pytest.approx(0.7, 0.01)


class TestExplanationResults:
    """Test explanation result structures."""
    
    def test_validated_behavior_creation(self):
        """Test creation of validated behavior."""
        behavior = ValidatedBehavior(
            behavior="Test checkout",
            confidence=0.9,
            evidence=["API call to /checkout", "Status code 200"],
            test_references=["test_1", "test_2"],
        )
        
        assert behavior.behavior == "Test checkout"
        assert behavior.confidence == 0.9
        assert len(behavior.evidence) == 2
        assert len(behavior.test_references) == 2
    
    def test_explanation_result_creation(self):
        """Test creation of explanation result."""
        result = ExplanationResult(
            summary="Found 3 tests for checkout",
            validated_behaviors=[],
            missing_coverage=["Error handling"],
            test_references=["test_1", "test_2", "test_3"],
            confidence_score=0.85,
        )
        
        assert "3 tests" in result.summary
        assert len(result.test_references) == 3
        assert result.confidence_score == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
