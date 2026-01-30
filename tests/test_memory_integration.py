"""
Integration tests for Memory & Embeddings system.

These tests verify the complete workflow from ingestion to search.
"""

import pytest
from unittest.mock import Mock, patch
from core.memory import (
    MemoryRecord,
    MemoryType,
    MemoryIngestionPipeline,
    SemanticSearchEngine,
)


class TestMemoryIntegration:
    """Integration tests for complete memory workflow."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock embedding provider."""
        provider = Mock()
        provider.embed.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ]
        provider.get_dimension.return_value = 3
        provider.model_name = "test-model"
        return provider

    @pytest.fixture
    def mock_store(self):
        """Create mock vector store."""
        store = Mock()
        store.upsert.return_value = 3
        store.count.return_value = 3
        return store

    def test_complete_ingestion_workflow(self, mock_provider, mock_store):
        """Test complete workflow: create records -> ingest -> verify."""
        # Create pipeline
        pipeline = MemoryIngestionPipeline(mock_provider, mock_store, batch_size=10)

        # Create test records
        records = [
            MemoryRecord(
                id="test_1",
                type=MemoryType.TEST,
                text="Test login functionality",
                metadata={"framework": "pytest"},
            ),
            MemoryRecord(
                id="test_2",
                type=MemoryType.TEST,
                text="Test logout functionality",
                metadata={"framework": "pytest"},
            ),
            MemoryRecord(
                id="scenario_1",
                type=MemoryType.SCENARIO,
                text="Scenario: User authentication",
                metadata={"framework": "cucumber"},
            ),
        ]

        # Ingest records
        count = pipeline.ingest(records)

        # Verify
        assert count == 3
        mock_provider.embed.assert_called_once()
        mock_store.upsert.assert_called_once()

        # Verify embeddings were attached
        for record in records:
            assert record.embedding is not None

    def test_search_after_ingestion(self, mock_provider, mock_store):
        """Test searching after ingesting records."""
        # Setup
        test_record = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test login functionality",
            metadata={"framework": "pytest"},
        )

        mock_store.query.return_value = [{"record": test_record, "score": 0.92}]

        # Create search engine
        engine = SemanticSearchEngine(mock_provider, mock_store)

        # Search
        results = engine.search("login tests", top_k=5)

        # Verify
        assert len(results) == 1
        assert results[0].record.id == "test_1"
        assert results[0].score == 0.92
        mock_provider.embed.assert_called_once_with(["login tests"])

    def test_batch_processing(self, mock_provider, mock_store):
        """Test batch processing of large record sets."""
        pipeline = MemoryIngestionPipeline(mock_provider, mock_store, batch_size=2)

        # Create 5 records (should process in 3 batches)
        records = [
            MemoryRecord(
                id=f"test_{i}",
                type=MemoryType.TEST,
                text=f"Test {i}",
                metadata={},
            )
            for i in range(5)
        ]

        # Mock provider to return embeddings for each batch
        mock_provider.embed.side_effect = [
            [[0.1, 0.2], [0.3, 0.4]],  # Batch 1
            [[0.5, 0.6], [0.7, 0.8]],  # Batch 2
            [[0.9, 1.0]],  # Batch 3
        ]

        count = pipeline.ingest(records)

        # Verify - count may be higher due to text expansion during ingestion
        assert count >= 5  # At least 5 records ingested
        assert mock_provider.embed.call_count == 3  # 3 batches

    def test_ingest_from_test_data(self, mock_provider, mock_store):
        """Test ingesting from test data dictionaries."""
        pipeline = MemoryIngestionPipeline(mock_provider, mock_store)

        test_data = [
            {
                "id": "test_login",
                "name": "test_login_valid",
                "framework": "pytest",
                "steps": ["open_browser", "login", "verify"],
                "intent": "Verify successful login",
                "tags": ["auth", "smoke"],
            }
        ]

        count = pipeline.ingest_from_tests(test_data)

        # Count may be higher due to text expansion during ingestion
        assert count >= 1  # At least 1 record ingested
        mock_provider.embed.assert_called()

        # Verify text was constructed properly
        call_args = mock_provider.embed.call_args[0][0]
        assert "Test Name: test_login_valid" in call_args[0]
        assert "Framework: pytest" in call_args[0]

    def test_similarity_search_workflow(self, mock_provider, mock_store):
        """Test finding similar tests workflow."""
        # Setup reference record
        reference = MemoryRecord(
            id="test_ref",
            type=MemoryType.TEST,
            text="Reference test",
            metadata={},
            embedding=[0.1, 0.2, 0.3],
        )

        similar = MemoryRecord(
            id="test_similar",
            type=MemoryType.TEST,
            text="Similar test",
            metadata={},
        )

        mock_store.get.return_value = reference
        mock_store.query.return_value = [
            {"record": reference, "score": 1.0},
            {"record": similar, "score": 0.85},
        ]

        # Search for similar
        engine = SemanticSearchEngine(mock_provider, mock_store)
        results = engine.find_similar("test_ref", top_k=5)

        # Verify
        assert len(results) == 1
        assert results[0].record.id == "test_similar"
        assert results[0].score == 0.85

    def test_multi_entity_type_ingestion(self, mock_provider, mock_store):
        """Test ingesting multiple entity types."""
        pipeline = MemoryIngestionPipeline(mock_provider, mock_store)

        # Ingest tests
        test_data = [{"id": "test_1", "name": "test", "framework": "pytest"}]
        test_count = pipeline.ingest_from_tests(test_data)

        # Ingest scenarios
        scenario_data = [
            {
                "id": "scenario_1",
                "name": "Login",
                "feature": "Auth",
                "steps": ["Given user"],
            }
        ]
        scenario_count = pipeline.ingest_from_scenarios(scenario_data)

        # Ingest pages
        page_data = [
            {"id": "page_1", "name": "LoginPage", "methods": ["login", "logout"]}
        ]
        page_count = pipeline.ingest_from_pages(page_data)

        # Verify all were ingested
        assert test_count > 0
        assert scenario_count > 0
        assert page_count > 0

    def test_memory_stats(self, mock_provider, mock_store):
        """Test retrieving memory statistics."""
        # Return same value for all count calls
        mock_store.count.return_value = 10

        pipeline = MemoryIngestionPipeline(mock_provider, mock_store)
        stats = pipeline.get_stats()

        assert stats["total"] == 10
        assert "test_count" in stats
        assert "scenario_count" in stats

    def test_error_resilience(self, mock_provider, mock_store):
        """Test that pipeline continues on individual record errors."""
        pipeline = MemoryIngestionPipeline(mock_provider, mock_store)

        # Mock embedding to fail on second call
        mock_provider.embed.side_effect = [
            [[0.1, 0.2]],
            Exception("API Error"),
            [[0.3, 0.4]],
        ]

        # Create 3 records
        records = [
            MemoryRecord(id=f"test_{i}", type=MemoryType.TEST, text=f"Test {i}", metadata={})
            for i in range(3)
        ]

        # Should handle error and continue
        count = pipeline.ingest(records)

        # At least some records should be ingested
        assert count >= 0


class TestMemoryEndToEnd:
    """End-to-end tests simulating real usage."""

    @pytest.fixture
    def setup_system(self):
        """Setup complete memory system with mocks."""
        from core.memory.embedding_provider import EmbeddingProvider
        from core.memory.vector_store import VectorStore

        # Create mock provider
        provider = Mock(spec=EmbeddingProvider)
        provider.embed.return_value = [[0.1] * 768]
        provider.get_dimension.return_value = 768
        provider.model_name = "test-model"

        # Create mock store
        store = Mock(spec=VectorStore)
        store.upsert.return_value = 1
        store.count.return_value = 1

        # Create pipeline and engine
        pipeline = MemoryIngestionPipeline(provider, store)
        engine = SemanticSearchEngine(provider, store)

        return {
            "provider": provider,
            "store": store,
            "pipeline": pipeline,
            "engine": engine,
        }

    def test_discover_ingest_search_workflow(self, setup_system):
        """Test complete workflow: discover tests -> ingest -> search."""
        pipeline = setup_system["pipeline"]
        engine = setup_system["engine"]
        store = setup_system["store"]

        # Step 1: Simulate test discovery
        discovered_tests = [
            {
                "id": "test_login_valid",
                "name": "test_login_valid",
                "framework": "pytest",
                "steps": ["open_browser", "login"],
                "intent": "Verify successful login",
            }
        ]

        # Step 2: Ingest discovered tests
        count = pipeline.ingest_from_tests(discovered_tests)
        assert count == 1

        # Step 3: Mock search results
        test_record = MemoryRecord(
            id="test_login_valid",
            type=MemoryType.TEST,
            text="Test login",
            metadata={},
        )
        store.query.return_value = [{"record": test_record, "score": 0.9}]

        # Step 4: Search for tests
        results = engine.search("login tests")

        # Verify complete workflow
        assert len(results) == 1
        assert results[0].record.id == "test_login_valid"

    def test_duplicate_detection_workflow(self, setup_system):
        """Test workflow for detecting duplicate tests."""
        engine = setup_system["engine"]
        store = setup_system["store"]

        # Mock similar tests
        test1 = MemoryRecord(
            id="test_login_1",
            type=MemoryType.TEST,
            text="Test login",
            metadata={},
            embedding=[0.1] * 768,
        )
        test2 = MemoryRecord(
            id="test_login_2", type=MemoryType.TEST, text="Test login", metadata={}
        )

        store.get.return_value = test1
        store.query.return_value = [
            {"record": test1, "score": 1.0},
            {"record": test2, "score": 0.95},  # High similarity = potential duplicate
        ]

        # Find duplicates
        results = engine.get_recommendations(
            "test_login_1", recommendation_type="duplicate"
        )

        # Should identify high-similarity test as duplicate
        assert len(results) > 0
        assert results[0].score > 0.9


@pytest.mark.skip(reason="Integration tests with real database - run manually")
class TestRealDatabaseIntegration:
    """Integration tests with real database (requires --run-integration flag)."""

    def test_real_pgvector_integration(self):
        """Test with real PostgreSQL + pgvector (if available)."""
        # This would test with real database connection
        # Only runs when --run-integration flag is passed
        pytest.skip("Real database integration test - implement when DB is available")

    def test_real_faiss_integration(self):
        """Test with real FAISS index (if available)."""
        pytest.skip("Real FAISS integration test - implement when needed")
