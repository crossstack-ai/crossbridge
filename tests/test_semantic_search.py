"""
Unit tests for semantic search engine.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.memory.search import SemanticSearchEngine
from core.memory.models import MemoryRecord, MemoryType, SearchResult


class TestSemanticSearchEngine:
    """Tests for SemanticSearchEngine."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock embedding provider."""
        provider = Mock()
        provider.embed.return_value = [[0.1, 0.2, 0.3]]
        return provider

    @pytest.fixture
    def mock_store(self):
        """Create mock vector store."""
        store = Mock()
        return store

    @pytest.fixture
    def engine(self, mock_provider, mock_store):
        """Create search engine with mocks."""
        return SemanticSearchEngine(mock_provider, mock_store)

    def test_initialization(self, mock_provider, mock_store):
        """Test search engine initialization."""
        engine = SemanticSearchEngine(mock_provider, mock_store)

        assert engine.embedding_provider == mock_provider
        assert engine.vector_store == mock_store

    def test_search_basic(self, engine, mock_provider, mock_store):
        """Test basic search functionality."""
        # Mock vector store response
        test_record = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test login functionality",
            metadata={"framework": "pytest"},
        )

        mock_store.query.return_value = [
            {"record": test_record, "score": 0.92},
        ]

        results = engine.search("login tests", top_k=10)

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].record.id == "test_1"
        assert results[0].score == 0.92
        assert results[0].rank == 1

        # Verify embedding was generated
        mock_provider.embed.assert_called_once_with(["login tests"])

        # Verify store was queried
        mock_store.query.assert_called_once()

    def test_search_with_filters(self, engine, mock_provider, mock_store):
        """Test search with entity type and framework filters."""
        mock_store.query.return_value = []

        engine.search(
            "login tests", entity_types=["test"], framework="pytest", top_k=5
        )

        # Verify filters were passed to vector store
        call_args = mock_store.query.call_args
        assert call_args[1]["filters"]["type"] == ["test"]
        assert call_args[1]["filters"]["framework"] == "pytest"
        assert call_args[1]["top_k"] == 5

    def test_search_empty_query(self, engine):
        """Test search with empty query returns empty list."""
        results = engine.search("")

        assert results == []

    def test_search_with_min_score(self, engine, mock_provider, mock_store):
        """Test filtering results by minimum score."""
        test_record1 = MemoryRecord(
            id="test_1", type=MemoryType.TEST, text="Test 1", metadata={}
        )
        test_record2 = MemoryRecord(
            id="test_2", type=MemoryType.TEST, text="Test 2", metadata={}
        )

        mock_store.query.return_value = [
            {"record": test_record1, "score": 0.9},
            {"record": test_record2, "score": 0.4},
        ]

        results = engine.search("test", min_score=0.5)

        # Only record with score >= 0.5 should be returned
        assert len(results) == 1
        assert results[0].record.id == "test_1"

    def test_find_similar(self, engine, mock_store):
        """Test finding similar records."""
        reference_record = MemoryRecord(
            id="test_ref",
            type=MemoryType.TEST,
            text="Reference test",
            metadata={},
            embedding=[0.1, 0.2, 0.3],
        )

        similar_record = MemoryRecord(
            id="test_similar",
            type=MemoryType.TEST,
            text="Similar test",
            metadata={},
        )

        mock_store.get.return_value = reference_record
        mock_store.query.return_value = [
            {"record": reference_record, "score": 1.0},  # Self (should be excluded)
            {"record": similar_record, "score": 0.85},
        ]

        results = engine.find_similar("test_ref", top_k=5)

        assert len(results) == 1
        assert results[0].record.id == "test_similar"
        assert results[0].score == 0.85

        # Verify store.get was called
        mock_store.get.assert_called_once_with("test_ref")

    def test_find_similar_no_embedding(self, engine, mock_store):
        """Test find_similar when record has no embedding."""
        record_no_embedding = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test",
            metadata={},
            embedding=None,
        )

        mock_store.get.return_value = record_no_embedding

        results = engine.find_similar("test_1")

        assert results == []

    def test_find_similar_not_found(self, engine, mock_store):
        """Test find_similar when record doesn't exist."""
        mock_store.get.return_value = None

        results = engine.find_similar("nonexistent")

        assert results == []

    def test_search_by_example(self, engine, mock_provider, mock_store):
        """Test search by example text."""
        mock_store.query.return_value = []

        engine.search_by_example(
            "TimeoutException: element not found",
            entity_types=["failure"],
            top_k=5,
        )

        # Should behave like regular search
        mock_provider.embed.assert_called_once()
        mock_store.query.assert_called_once()

    def test_multi_query_search(self, engine, mock_provider, mock_store):
        """Test multi-query search with score aggregation."""
        record1 = MemoryRecord(
            id="test_1", type=MemoryType.TEST, text="Test 1", metadata={}
        )
        record2 = MemoryRecord(
            id="test_2", type=MemoryType.TEST, text="Test 2", metadata={}
        )

        # Mock responses for each query
        def query_side_effect(vector, top_k, filters):
            if mock_provider.embed.call_count == 1:
                return [
                    {"record": record1, "score": 0.9},
                    {"record": record2, "score": 0.7},
                ]
            else:
                return [
                    {"record": record1, "score": 0.8},
                    {"record": record2, "score": 0.6},
                ]

        mock_store.query.side_effect = query_side_effect
        mock_store.get.side_effect = lambda id: record1 if id == "test_1" else record2

        results = engine.multi_query_search(
            ["login tests", "authentication"], top_k=2
        )

        # Should have aggregated scores
        assert len(results) <= 2
        # record1 should rank higher (avg 0.85 vs 0.65)
        if len(results) > 0:
            assert results[0].record.id == "test_1"

    def test_multi_query_search_empty(self, engine):
        """Test multi-query search with empty query list."""
        results = engine.multi_query_search([])

        assert results == []

    def test_search_with_context(self, engine, mock_provider, mock_store):
        """Test search with additional context."""
        mock_store.query.return_value = []

        context = {"file": "login_tests.py", "framework": "pytest"}

        engine.search_with_context("timeout tests", context=context, top_k=5)

        # Verify framework filter was applied
        call_args = mock_store.query.call_args
        assert call_args[1]["filters"]["framework"] == "pytest"

    def test_get_recommendations_duplicate(self, engine, mock_store):
        """Test get recommendations for duplicates."""
        reference = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test",
            metadata={},
            embedding=[0.1, 0.2, 0.3],
        )

        high_similar = MemoryRecord(
            id="test_2", type=MemoryType.TEST, text="Test", metadata={}
        )

        mock_store.get.return_value = reference
        mock_store.query.return_value = [
            {"record": reference, "score": 1.0},
            {"record": high_similar, "score": 0.95},  # > 0.9 threshold
        ]

        results = engine.get_recommendations(
            "test_1", recommendation_type="duplicate", top_k=5
        )

        assert len(results) == 1
        assert results[0].score > 0.9

    def test_get_recommendations_similar(self, engine, mock_store):
        """Test get recommendations for similar tests."""
        reference = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test",
            metadata={},
            embedding=[0.1, 0.2, 0.3],
        )

        similar = MemoryRecord(
            id="test_2", type=MemoryType.TEST, text="Test", metadata={}
        )

        mock_store.get.return_value = reference
        mock_store.query.return_value = [
            {"record": reference, "score": 1.0},
            {"record": similar, "score": 0.75},
        ]

        results = engine.get_recommendations(
            "test_1", recommendation_type="similar", top_k=5
        )

        assert len(results) >= 1

    def test_get_recommendations_complement(self, engine, mock_store):
        """Test get recommendations for complementary tests."""
        reference = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test",
            metadata={},
            embedding=[0.1, 0.2, 0.3],
        )

        complement = MemoryRecord(
            id="test_2", type=MemoryType.TEST, text="Test", metadata={}
        )

        mock_store.get.return_value = reference
        mock_store.query.return_value = [
            {"record": reference, "score": 1.0},
            {"record": complement, "score": 0.65},  # 0.5 < score < 0.8
        ]

        results = engine.get_recommendations(
            "test_1", recommendation_type="complement", top_k=5
        )

        assert len(results) >= 1
        # Should be in complement range
        for result in results:
            assert 0.5 < result.score < 0.8

    def test_explain_search(self, engine):
        """Test search explanation generation."""
        record = MemoryRecord(
            id="test_login",
            type=MemoryType.TEST,
            text="Test login functionality with timeout handling",
            metadata={"framework": "pytest", "tags": ["auth", "timeout"]},
        )

        result = SearchResult(record=record, score=0.85, rank=1)

        explanation = engine.explain_search("login timeout", result)

        assert "test" in explanation.lower()
        assert "85" in explanation  # Score percentage
        assert "pytest" in explanation.lower()

    def test_search_error_handling(self, engine, mock_provider):
        """Test error handling when search fails."""
        mock_provider.embed.side_effect = Exception("API Error")

        results = engine.search("test query")

        # Should return empty list instead of raising
        assert results == []
