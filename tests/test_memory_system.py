"""
Comprehensive unit tests for Memory & Embeddings system.

Tests cover:
- Memory models and data structures
- Embedding providers (OpenAI, local, HuggingFace)
- Vector stores (pgvector, FAISS)
- Memory ingestion pipeline
- Semantic search engine
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from typing import List

from core.memory.models import (
    MemoryRecord,
    MemoryType,
    SearchResult,
    convert_test_to_text,
    scenario_to_text,
    step_to_text,
    page_to_text,
    failure_to_text,
)
from core.memory.embedding_provider import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    HuggingFaceEmbeddingProvider,
    EmbeddingProviderError,
    create_embedding_provider,
)
from core.memory.vector_store import (
    VectorStore,
    PgVectorStore,
    FAISSVectorStore,
    create_vector_store,
)
from core.memory.ingestion import (
    MemoryIngestionPipeline,
    ingest_from_discovery,
)
from core.memory.search import SemanticSearchEngine


# ============================================================================
# Test Memory Models
# ============================================================================


class TestMemoryRecord:
    """Test MemoryRecord model."""

    def test_create_record(self):
        """Test creating a valid memory record."""
        record = MemoryRecord(
            id="test_login",
            type=MemoryType.TEST,
            text="Test Name: test_login",
            metadata={"framework": "pytest"},
        )

        assert record.id == "test_login"
        assert record.type == MemoryType.TEST
        assert record.text == "Test Name: test_login"
        assert record.metadata["framework"] == "pytest"
        assert record.embedding is None
        assert isinstance(record.created_at, datetime)

    def test_record_validation(self):
        """Test record validation."""
        # Empty ID should raise error
        with pytest.raises(ValueError):
            MemoryRecord(
                id="",
                type=MemoryType.TEST,
                text="Test",
                metadata={},
            )

        # Empty text should raise error
        with pytest.raises(ValueError):
            MemoryRecord(
                id="test",
                type=MemoryType.TEST,
                text="",
                metadata={},
            )

    def test_record_serialization(self):
        """Test record to_dict/from_dict."""
        original = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test text",
            metadata={"key": "value"},
            embedding=[0.1, 0.2, 0.3],
        )

        # Serialize
        data = original.to_dict()
        assert data["id"] == "test_1"
        assert data["type"] == "test"
        assert data["embedding"] == [0.1, 0.2, 0.3]

        # Deserialize
        restored = MemoryRecord.from_dict(data)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.text == original.text
        assert restored.embedding == original.embedding


class TestTextConstructors:
    """Test text construction helpers."""

    def test_test_to_text(self):
        """Test test_data_to_text converter."""
        test_data = {
            "name": "test_login",
            "framework": "pytest",
            "steps": ["open_browser", "login"],
            "intent": "Verify login works",
            "tags": ["smoke"],
        }

        text = convert_test_to_text(test_data)

        assert "test_login" in text
        assert "pytest" in text
        assert "open_browser" in text
        assert "Verify login works" in text

    def test_scenario_to_text(self):
        """Test scenario_to_text converter."""
        scenario_data = {
            "name": "User logs in",
            "feature": "Authentication",
            "steps": ["Given user on login page", "When enters credentials"],
            "tags": ["auth"],
        }

        text = scenario_to_text(scenario_data)

        assert "User logs in" in text
        assert "Authentication" in text
        assert "Given user on login page" in text

    def test_step_to_text(self):
        """Test step_to_text converter."""
        step_data = {
            "text": "user enters credentials",
            "keyword": "When",
            "action": "enter_text",
        }

        text = step_to_text(step_data)

        assert "user enters credentials" in text
        assert "When" in text

    def test_failure_to_text(self):
        """Test failure_to_text converter."""
        failure_data = {
            "test_name": "test_login",
            "error_type": "TimeoutException",
            "message": "element not found",
        }

        text = failure_to_text(failure_data)

        assert "test_login" in text
        assert "TimeoutException" in text
        assert "element not found" in text


# ============================================================================
# Test Embedding Providers
# ============================================================================


class TestEmbeddingProviders:
    """Test embedding provider implementations."""

    @pytest.mark.skip(reason="Use unified core.embeddings.OpenAIProvider instead")
    def test_openai_provider(self):
        """Test OpenAI embedding provider."""
        # This test is deprecated - use core.embeddings.OpenAIProvider
        # from core.embeddings import OpenAIProvider
        # provider = OpenAIProvider(model="text-embedding-3-small", api_key="test-key")
        pass

    def test_create_embedding_provider(self):
        """Test embedding provider factory."""
        # Invalid provider type
        with pytest.raises(ValueError):
            create_embedding_provider("invalid_type")

    @pytest.mark.skip(reason="Requires actual Ollama server")
    def test_local_provider(self):
        """Test local embedding provider (requires Ollama)."""
        provider = LocalEmbeddingProvider(model="nomic-embed-text")
        embeddings = provider.embed(["test text"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) > 0


# ============================================================================
# Test Vector Stores
# ============================================================================


class TestFAISSVectorStore:
    """Test FAISS vector store (no external dependencies)."""

    def test_faiss_basic_operations(self):
        """Test basic FAISS operations."""
        store = FAISSVectorStore(dimension=3)

        # Create test records
        records = [
            MemoryRecord(
                id="test_1",
                type=MemoryType.TEST,
                text="Test 1",
                metadata={"framework": "pytest"},
                embedding=[1.0, 0.0, 0.0],
            ),
            MemoryRecord(
                id="test_2",
                type=MemoryType.TEST,
                text="Test 2",
                metadata={"framework": "pytest"},
                embedding=[0.0, 1.0, 0.0],
            ),
            MemoryRecord(
                id="scenario_1",
                type=MemoryType.SCENARIO,
                text="Scenario 1",
                metadata={"framework": "cucumber"},
                embedding=[0.0, 0.0, 1.0],
            ),
        ]

        # Upsert records
        count = store.upsert(records)
        assert count == 3

        # Query similar records
        query_vector = [1.0, 0.0, 0.0]  # Should match test_1
        results = store.query(query_vector, top_k=2)

        assert len(results) == 2
        assert results[0]["record"].id == "test_1"
        assert results[0]["score"] > 0.9  # Very similar

        # Get specific record
        record = store.get("test_1")
        assert record is not None
        assert record.id == "test_1"

        # Count records
        assert store.count() == 3
        assert store.count(filters={"type": ["test"]}) == 2
        assert store.count(filters={"framework": "pytest"}) == 2

        # Delete record
        deleted = store.delete(["test_1"])
        assert deleted == 1
        assert store.count() == 2

    def test_faiss_filters(self):
        """Test FAISS filtering."""
        store = FAISSVectorStore(dimension=2)

        # Add records with different types and frameworks
        records = [
            MemoryRecord(
                id="pytest_test",
                type=MemoryType.TEST,
                text="Test",
                metadata={"framework": "pytest"},
                embedding=[1.0, 0.0],
            ),
            MemoryRecord(
                id="robot_test",
                type=MemoryType.TEST,
                text="Test",
                metadata={"framework": "robot"},
                embedding=[0.9, 0.1],
            ),
            MemoryRecord(
                id="pytest_scenario",
                type=MemoryType.SCENARIO,
                text="Scenario",
                metadata={"framework": "pytest"},
                embedding=[0.8, 0.2],
            ),
        ]

        store.upsert(records)

        # Filter by type
        results = store.query(
            [1.0, 0.0],
            top_k=10,
            filters={"type": ["test"]},
        )
        assert len(results) == 2

        # Filter by framework
        results = store.query(
            [1.0, 0.0],
            top_k=10,
            filters={"framework": "pytest"},
        )
        assert len(results) == 2

    def test_create_vector_store(self):
        """Test vector store factory."""
        # Invalid store type
        with pytest.raises(ValueError):
            create_vector_store("invalid_type")

        # Create FAISS store
        store = create_vector_store("faiss", dimension=128)
        assert isinstance(store, FAISSVectorStore)


# ============================================================================
# Test Memory Ingestion Pipeline
# ============================================================================


class TestMemoryIngestionPipeline:
    """Test memory ingestion pipeline."""

    def test_ingestion_basic(self):
        """Test basic ingestion flow."""
        # Mock providers
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        mock_store = Mock(spec=VectorStore)
        mock_store.upsert.return_value = 2

        # Create pipeline
        pipeline = MemoryIngestionPipeline(
            mock_provider,
            mock_store,
            batch_size=10,
        )

        # Create records without embeddings
        records = [
            MemoryRecord(
                id="test_1",
                type=MemoryType.TEST,
                text="Test 1",
                metadata={},
            ),
            MemoryRecord(
                id="test_2",
                type=MemoryType.TEST,
                text="Test 2",
                metadata={},
            ),
        ]

        # Ingest
        count = pipeline.ingest(records)

        assert count == 2
        mock_provider.embed.assert_called_once()
        mock_store.upsert.assert_called_once()

        # Verify embeddings were attached
        call_args = mock_store.upsert.call_args[0][0]
        assert call_args[0].embedding == [0.1, 0.2]
        assert call_args[1].embedding == [0.3, 0.4]

    def test_ingest_from_tests(self):
        """Test ingesting test data."""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.return_value = [[0.1, 0.2]]

        mock_store = Mock(spec=VectorStore)
        mock_store.upsert.return_value = 1

        pipeline = MemoryIngestionPipeline(mock_provider, mock_store)

        test_data = [
            {
                "id": "test_login",
                "name": "test_login",
                "framework": "pytest",
                "steps": ["open", "login"],
                "intent": "Verify login",
            }
        ]

        count = pipeline.ingest_from_tests(test_data)

        assert count == 1
        mock_provider.embed.assert_called_once()

    def test_batch_processing(self):
        """Test batch processing."""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.side_effect = [
            [[0.1, 0.2], [0.3, 0.4]],  # Batch 1
            [[0.5, 0.6]],  # Batch 2
        ]

        mock_store = Mock(spec=VectorStore)
        mock_store.upsert.return_value = 2

        # Small batch size to force multiple batches
        pipeline = MemoryIngestionPipeline(
            mock_provider,
            mock_store,
            batch_size=2,
        )

        records = [
            MemoryRecord(id=f"test_{i}", type=MemoryType.TEST, text=f"Test {i}", metadata={})
            for i in range(3)
        ]

        count = pipeline.ingest(records)

        assert count == 4  # 2 from first batch + 2 from second batch
        assert mock_provider.embed.call_count == 2  # Two batches

    def test_get_stats(self):
        """Test pipeline statistics."""
        mock_provider = Mock(spec=EmbeddingProvider)

        mock_store = Mock(spec=VectorStore)
        # Return values for each memory type call
        mock_store.count.return_value = 10  # Return same value for all calls

        pipeline = MemoryIngestionPipeline(mock_provider, mock_store)

        stats = pipeline.get_stats()

        assert stats["total"] == 10
        assert "test_count" in stats
        assert "scenario_count" in stats


# ============================================================================
# Test Semantic Search Engine
# ============================================================================


class TestSemanticSearchEngine:
    """Test semantic search engine."""

    def test_search_basic(self):
        """Test basic search."""
        # Mock provider
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.return_value = [[0.1, 0.2, 0.3]]

        # Mock store
        test_record = MemoryRecord(
            id="test_login",
            type=MemoryType.TEST,
            text="Test login",
            metadata={"framework": "pytest"},
        )

        mock_store = Mock(spec=VectorStore)
        mock_store.query.return_value = [
            {"record": test_record, "score": 0.95}
        ]

        # Create engine
        engine = SemanticSearchEngine(mock_provider, mock_store)

        # Search
        results = engine.search("login test", top_k=5)

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].record.id == "test_login"
        assert results[0].score == 0.95
        assert results[0].rank == 1

        mock_provider.embed.assert_called_once_with(["login test"])
        mock_store.query.assert_called_once()

    def test_search_with_filters(self):
        """Test search with entity type and framework filters."""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.return_value = [[0.1, 0.2]]

        mock_store = Mock(spec=VectorStore)
        mock_store.query.return_value = []

        engine = SemanticSearchEngine(mock_provider, mock_store)

        # Search with filters
        engine.search(
            "test query",
            entity_types=["test", "scenario"],
            framework="pytest",
            top_k=10,
        )

        # Verify filters were passed
        call_args = mock_store.query.call_args
        filters = call_args[1]["filters"]

        assert filters["type"] == ["test", "scenario"]
        assert filters["framework"] == "pytest"

    def test_find_similar(self):
        """Test finding similar records."""
        # Create test record with embedding
        reference_record = MemoryRecord(
            id="test_original",
            type=MemoryType.TEST,
            text="Original test",
            metadata={},
            embedding=[1.0, 0.0, 0.0],
        )

        similar_record = MemoryRecord(
            id="test_similar",
            type=MemoryType.TEST,
            text="Similar test",
            metadata={},
        )

        mock_provider = Mock(spec=EmbeddingProvider)

        mock_store = Mock(spec=VectorStore)
        mock_store.get.return_value = reference_record
        mock_store.query.return_value = [
            {"record": reference_record, "score": 1.0},  # Self (will be filtered)
            {"record": similar_record, "score": 0.92},
        ]

        engine = SemanticSearchEngine(mock_provider, mock_store)

        # Find similar
        results = engine.find_similar("test_original", top_k=5)

        assert len(results) == 1
        assert results[0].record.id == "test_similar"
        assert results[0].score == 0.92

    def test_multi_query_search(self):
        """Test multi-query search with aggregation."""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.side_effect = [
            [[0.1, 0.2]],  # Query 1
            [[0.3, 0.4]],  # Query 2
        ]

        record1 = MemoryRecord(id="test_1", type=MemoryType.TEST, text="Test 1", metadata={})
        record2 = MemoryRecord(id="test_2", type=MemoryType.TEST, text="Test 2", metadata={})

        mock_store = Mock(spec=VectorStore)
        mock_store.query.side_effect = [
            [{"record": record1, "score": 0.9}, {"record": record2, "score": 0.7}],  # Query 1
            [{"record": record1, "score": 0.8}, {"record": record2, "score": 0.9}],  # Query 2
        ]
        mock_store.get.side_effect = [record1, record2]

        engine = SemanticSearchEngine(mock_provider, mock_store)

        # Multi-query search
        results = engine.multi_query_search(
            queries=["query 1", "query 2"],
            top_k=10,
        )

        assert len(results) == 2
        # test_1: (0.9 + 0.8) / 2 = 0.85
        # test_2: (0.7 + 0.9) / 2 = 0.8
        assert results[0].record.id == "test_1"  # Higher average score

    def test_get_recommendations(self):
        """Test recommendation system."""
        reference_record = MemoryRecord(
            id="test_ref",
            type=MemoryType.TEST,
            text="Reference",
            metadata={},
            embedding=[1.0, 0.0],
        )

        similar_record = MemoryRecord(
            id="test_similar",
            type=MemoryType.TEST,
            text="Similar",
            metadata={},
        )

        duplicate_record = MemoryRecord(
            id="test_duplicate",
            type=MemoryType.TEST,
            text="Duplicate",
            metadata={},
        )

        mock_provider = Mock(spec=EmbeddingProvider)
        mock_store = Mock(spec=VectorStore)
        mock_store.get.return_value = reference_record
        mock_store.query.return_value = [
            {"record": reference_record, "score": 1.0},
            {"record": duplicate_record, "score": 0.95},  # Duplicate
            {"record": similar_record, "score": 0.75},  # Similar
        ]

        engine = SemanticSearchEngine(mock_provider, mock_store)

        # Get duplicates (>0.9)
        duplicates = engine.get_recommendations(
            "test_ref",
            recommendation_type="duplicate",
            top_k=5,
        )
        assert len(duplicates) == 1
        assert duplicates[0].record.id == "test_duplicate"

    def test_explain_search(self):
        """Test search explanation."""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_store = Mock(spec=VectorStore)

        engine = SemanticSearchEngine(mock_provider, mock_store)

        result = SearchResult(
            record=MemoryRecord(
                id="test_1",
                type=MemoryType.TEST,
                text="Test with login and timeout handling",
                metadata={"framework": "pytest", "tags": ["auth"]},
            ),
            score=0.87,
            rank=1,
        )

        explanation = engine.explain_search("login timeout", result)

        # Accept any percentage format: 0.87, 87%, or 87.00%
        assert "87" in explanation or "0.87" in explanation
        assert "pytest" in explanation


# ============================================================================
# Test Integration
# ============================================================================


class TestIntegration:
    """Integration tests for the complete system."""

    def test_end_to_end_flow(self):
        """Test complete ingestion and search flow."""
        # Use FAISS for in-memory testing
        store = FAISSVectorStore(dimension=3)

        # Mock embedding provider with fixed embeddings
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.side_effect = [
            # Ingestion embeddings
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.0]],
            # Search query embedding
            [[1.0, 0.1, 0.0]],  # Similar to first test
        ]

        # Create pipeline and ingest
        pipeline = MemoryIngestionPipeline(mock_provider, store)

        test_data = [
            {"id": "test_login", "name": "test_login", "framework": "pytest"},
            {"id": "test_logout", "name": "test_logout", "framework": "pytest"},
            {"id": "test_auth", "name": "test_auth", "framework": "robot"},
        ]

        count = pipeline.ingest_from_tests(test_data)
        assert count == 3

        # Search
        engine = SemanticSearchEngine(mock_provider, store)
        results = engine.search("login test", top_k=2)

        assert len(results) == 2
        assert results[0].record.id == "test_login"  # Most similar


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
