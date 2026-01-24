"""
Unit tests for LLM Test Analyzer.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.intelligence.llm_analyzer import (
    LLMTestAnalyzer,
    LLMTestSummaryCache
)
from core.intelligence.models import (
    UnifiedTestMemory,
    TestMetadata,
    StructuralSignals,
    SemanticSignals,
    Priority,
    TestType,
    APICall,
    Assertion
)


@pytest.fixture
def sample_unified_test():
    """Create a sample UnifiedTestMemory for testing."""
    from datetime import timezone
    
    metadata = TestMetadata(
        test_type=TestType.POSITIVE,
        priority=Priority.P0,
        feature="user_api",
        tags=["smoke", "api"]
    )
    
    structural = StructuralSignals(
        api_calls=[
            APICall(method="POST", endpoint="/api/users"),
            APICall(method="GET", endpoint="/api/users/123")
        ],
        assertions=[
            Assertion(type="status_code", target="response", expected_value=201)
        ]
    )
    
    semantic = SemanticSignals(
        intent_text="Create a new user and verify it was created",
        keywords=["create", "user", "api"]
    )
    
    return UnifiedTestMemory(
        test_id="pytest::tests/test_api.py::test_create_user",
        framework="pytest",
        language="python",
        file_path="tests/test_api.py",
        test_name="test_create_user",
        semantic=semantic,
        structural=structural,
        metadata=metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


class TestLLMTestAnalyzer:
    """Test LLM Test Analyzer."""
    
    def test_initialization_without_api_key(self):
        """Test analyzer initialization without API key."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        assert analyzer.model == "gpt-4"
        assert analyzer.api_key is None
    
    def test_initialization_with_api_key(self):
        """Test analyzer initialization with API key."""
        analyzer = LLMTestAnalyzer(model="gpt-4", api_key="test-key")
        assert analyzer.api_key == "test-key"
    
    def test_fallback_summary_no_llm(self, sample_unified_test):
        """Test fallback summary when LLM is not available."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None  # Ensure no client
        
        summary = analyzer.summarize_test(sample_unified_test)
        
        assert summary["test_id"] == sample_unified_test.test_id
        assert summary["framework"] == "pytest"
        assert "summary" in summary
        assert summary["model"] == "fallback"
        assert summary["confidence"] == "low"
    
    def test_fallback_summary_content(self, sample_unified_test):
        """Test content of fallback summary."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        summary = analyzer.summarize_test(sample_unified_test)
        
        assert "API" in summary["summary"]
        assert "python" in summary["summary"]
        assert "pytest" in summary["summary"]
        assert "P0" in summary["summary"]
    
    @patch('openai.OpenAI')
    def test_summarize_with_openai(self, mock_openai, sample_unified_test):
        """Test summarization with OpenAI API."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test creates a new user via API"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        analyzer = LLMTestAnalyzer(model="gpt-4", api_key="test-key")
        analyzer._client = mock_client
        analyzer._provider = "openai"
        
        summary = analyzer.summarize_test(sample_unified_test)
        
        assert summary["model"] == "gpt-4"
        assert "Test creates a new user via API" in summary["summary"]
    
    def test_batch_summarize(self, sample_unified_test):
        """Test batch summarization of multiple tests."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        tests = [sample_unified_test, sample_unified_test, sample_unified_test]
        summaries = analyzer.batch_summarize(tests)
        
        assert len(summaries) == 3
        assert all("test_id" in s for s in summaries)
    
    def test_batch_summarize_max_tests(self, sample_unified_test):
        """Test batch summarization respects max_tests limit."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        tests = [sample_unified_test] * 100
        summaries = analyzer.batch_summarize(tests, max_tests=10)
        
        assert len(summaries) == 10
    
    def test_fallback_comparison(self, sample_unified_test):
        """Test test comparison without LLM."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        # Create second test with different framework
        test2 = UnifiedTestMemory(
            test_id="junit::tests/ApiTest.java::testCreateUser",
            framework="junit",
            language="java",
            file_path="tests/ApiTest.java",
            test_name="testCreateUser",
            semantic=sample_unified_test.semantic,
            structural=sample_unified_test.structural,
            metadata=sample_unified_test.metadata
        )
        
        comparison = analyzer.compare_tests(sample_unified_test, test2)
        
        assert comparison["test1_id"] == sample_unified_test.test_id
        assert comparison["test2_id"] == test2.test_id
        assert "similarities" in comparison
        assert "differences" in comparison
    
    def test_comparison_same_framework(self, sample_unified_test):
        """Test comparison of tests with same framework."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        test2 = sample_unified_test
        comparison = analyzer.compare_tests(sample_unified_test, test2)
        
        similarities = comparison["similarities"]
        assert any("pytest" in s for s in similarities)
        assert any("python" in s for s in similarities)
    
    def test_fallback_suggestions(self, sample_unified_test):
        """Test improvement suggestions without LLM."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        suggestions = analyzer.suggest_test_improvements(sample_unified_test)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
    
    def test_suggestions_for_test_without_tags(self, sample_unified_test):
        """Test suggestions for test without tags."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        # Remove tags
        sample_unified_test.metadata.tags = []
        
        suggestions = analyzer.suggest_test_improvements(sample_unified_test)
        
        assert any("tag" in s.lower() for s in suggestions)
    
    def test_suggestions_for_test_without_assertions(self, sample_unified_test):
        """Test suggestions for test without assertions."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        # Remove assertions
        sample_unified_test.structural.assertions = []
        
        suggestions = analyzer.suggest_test_improvements(sample_unified_test)
        
        assert any("assertion" in s.lower() for s in suggestions)
    
    def test_build_summary_prompt(self, sample_unified_test):
        """Test building of summary prompt."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        
        prompt = analyzer._build_test_summary_prompt(
            sample_unified_test,
            source_code=None,
            include_recommendations=True
        )
        
        assert "pytest" in prompt
        assert "test_create_user" in prompt
        assert "P0" in prompt
        assert "API" in prompt


class TestLLMTestSummaryCache:
    """Test LLM summary cache."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = LLMTestSummaryCache()
        assert cache.size() == 0
    
    def test_cache_set_and_get(self):
        """Test setting and getting from cache."""
        cache = LLMTestSummaryCache()
        
        summary = {
            "test_id": "test123",
            "summary": "Test summary",
            "model": "gpt-4"
        }
        
        cache.set("test123", summary)
        retrieved = cache.get("test123")
        
        assert retrieved == summary
        assert cache.size() == 1
    
    def test_cache_get_nonexistent(self):
        """Test getting non-existent item from cache."""
        cache = LLMTestSummaryCache()
        
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_clear(self):
        """Test clearing cache."""
        cache = LLMTestSummaryCache()
        
        cache.set("test1", {"summary": "1"})
        cache.set("test2", {"summary": "2"})
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
        assert cache.get("test1") is None
    
    def test_cache_overwrite(self):
        """Test overwriting cached item."""
        cache = LLMTestSummaryCache()
        
        cache.set("test1", {"version": 1})
        cache.set("test1", {"version": 2})
        
        assert cache.size() == 1
        assert cache.get("test1")["version"] == 2


class TestLLMAnalyzerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_analyze_test_with_no_structural_signals(self):
        """Test analyzing test with no structural signals."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        from datetime import timezone
        
        unified = UnifiedTestMemory(
            test_id="test::empty",
            framework="pytest",
            language="python",
            file_path="/test.py",
            test_name="test_empty",
            semantic=SemanticSignals(),
            structural=StructuralSignals(),
            metadata=TestMetadata(
                test_type=TestType.POSITIVE,
                priority=Priority.P2,
                tags=[]
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        summary = analyzer.summarize_test(unified)
        
        assert summary["test_id"] == "test::empty"
        assert "summary" in summary
    
    def test_compare_tests_with_no_structural_signals(self):
        """Test comparing tests with no structural signals."""
        analyzer = LLMTestAnalyzer(model="gpt-4")
        analyzer._client = None
        
        from datetime import timezone
        
        test1 = UnifiedTestMemory(
            test_id="test1",
            framework="pytest",
            language="python",
            file_path="/test1.py",
            test_name="test1",
            semantic=SemanticSignals(),
            structural=StructuralSignals(),
            metadata=TestMetadata(
                test_type=TestType.POSITIVE,
                priority=Priority.P1,
                tags=[]
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        test2 = UnifiedTestMemory(
            test_id="test2",
            framework="junit",
            language="java",
            file_path="/Test2.java",
            test_name="test2",
            semantic=SemanticSignals(),
            structural=StructuralSignals(),
            metadata=TestMetadata(
                test_type=TestType.POSITIVE,
                priority=Priority.P1,
                tags=[]
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        comparison = analyzer.compare_tests(test1, test2)
        
        assert "similarities" in comparison
        assert "differences" in comparison


class TestLLMAnalyzerWithMockAPI:
    """Test LLM analyzer with mocked API responses."""
    
    @patch('openai.OpenAI')
    def test_summarize_api_error_falls_back(self, mock_openai, sample_unified_test):
        """Test that API errors fall back to basic summary."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        analyzer = LLMTestAnalyzer(model="gpt-4", api_key="test-key")
        analyzer._client = mock_client
        analyzer._provider = "openai"
        
        summary = analyzer.summarize_test(sample_unified_test)
        
        # Should fall back to basic summary
        assert summary["model"] == "fallback"
        assert "summary" in summary
