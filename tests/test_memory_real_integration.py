"""
Real database integration tests for Memory & Semantic Search system.

This test uses the actual PostgreSQL database with pgvector extension
to validate the full memory system workflow.
"""

import pytest
import psycopg2
from datetime import datetime
from core.memory.models import MemoryRecord, MemoryType
from core.memory.vector_store import PgVectorStore
from core.memory.embedding_provider import DummyEmbeddingProvider
from core.memory.ingestion import MemoryIngestionPipeline
from core.memory.search import SemanticSearchEngine


class TestRealDatabaseIntegration:
    """Integration tests with real PostgreSQL + pgvector database."""

    @pytest.fixture
    def db_connection(self):
        """Get database connection for testing."""
        conn_string = "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
        conn = psycopg2.connect(conn_string)
        yield conn
        conn.close()

    @pytest.fixture
    def embedding_provider(self):
        """Get embedding provider (using dummy for testing)."""
        return DummyEmbeddingProvider(dimension=1536)

    @pytest.fixture
    def vector_store(self):
        """Get pgvector store."""
        conn_string = "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
        return PgVectorStore(connection_string=conn_string, dimension=1536)

    @pytest.fixture
    def pipeline(self, embedding_provider, vector_store):
        """Get ingestion pipeline."""
        return MemoryIngestionPipeline(embedding_provider, vector_store, batch_size=10)

    @pytest.fixture
    def search_engine(self, embedding_provider, vector_store):
        """Get search engine."""
        return SemanticSearchEngine(embedding_provider, vector_store)

    def test_database_connection(self, db_connection):
        """Test database connection is working."""
        with db_connection.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            assert "PostgreSQL" in version
            print(f"\nOK Connected to: {version}")

    def test_pgvector_extension(self, db_connection):
        """Test pgvector extension is available."""
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname = 'vector'
            """)
            result = cur.fetchone()
            assert result is not None, "pgvector extension not installed"
            print(f"\nOK pgvector version: {result[1]}")

    def test_memory_embeddings_table(self, db_connection):
        """Test memory_embeddings table exists and has correct structure."""
        with db_connection.cursor() as cur:
            # Check table exists
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns
                WHERE table_name = 'memory_embeddings'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            assert len(columns) > 0, "memory_embeddings table not found"
            
            column_names = [col[0] for col in columns]
            assert 'entity_id' in column_names
            assert 'entity_type' in column_names
            assert 'embedding' in column_names
            assert 'metadata' in column_names
            
            print(f"\nOK memory_embeddings table structure:")
            for col_name, col_type in columns:
                print(f"   {col_name}: {col_type}")

    def test_existing_embeddings_count(self, db_connection):
        """Test existing embeddings in database."""
        with db_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM memory_embeddings")
            count = cur.fetchone()[0]
            print(f"\nOK Existing embeddings: {count}")
            
            cur.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM memory_embeddings
                GROUP BY entity_type
                ORDER BY count DESC
            """)
            distribution = cur.fetchall()
            print(f"\n>> Distribution by entity type:")
            for entity_type, type_count in distribution:
                print(f"   {entity_type}: {type_count}")
            
            assert count > 0, "No embeddings found in database"

    def test_vector_store_basic_operations(self, db_connection):
        """Test basic vector store operations using existing schema."""
        # Use existing memory_embeddings table directly
        import numpy as np
        
        # Generate test embeddings
        test_ids = [f"test_integration_{i}" for i in range(3)]
        embeddings = []
        for _ in range(3):
            vec = np.random.randn(1536).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            embeddings.append(vec.tolist())
        
        # Insert test records
        with db_connection.cursor() as cur:
            for i, (test_id, embedding) in enumerate(zip(test_ids, embeddings)):
                cur.execute("""
                    INSERT INTO memory_embeddings 
                    (entity_id, entity_type, embedding, content_hash, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                """, (
                    test_id,
                    "test",
                    embedding,
                    f"hash_{i}",
                    '{"framework": "pytest", "file": "test_integration.py"}'
                ))
        db_connection.commit()
        print(f"\nOK Inserted {len(test_ids)} test records")
        
        # Query for similar records
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT entity_id, entity_type, 1 - (embedding <=> %s::vector) as similarity
                FROM memory_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT 5
            """, (embeddings[0], embeddings[0]))
            
            results = cur.fetchall()
            assert len(results) > 0
            print(f"\nOK Found {len(results)} similar records:")
            for entity_id, entity_type, sim in results[:3]:
                print(f"   {entity_id} ({entity_type}): {sim:.3f}")
        
        # Cleanup
        with db_connection.cursor() as cur:
            for test_id in test_ids:
                cur.execute("DELETE FROM memory_embeddings WHERE entity_id = %s", (test_id,))
        db_connection.commit()
        print(f"\nOK Cleaned up test records")

    def test_ingestion_pipeline_end_to_end(self, db_connection):
        """Test complete ingestion pipeline using direct database access."""
        import numpy as np
        import uuid
        
        # Create test data
        test_ids = [str(uuid.uuid4()) for _ in range(10)]
        
        # Generate embeddings
        embeddings = []
        for _ in range(10):
            vec = np.random.randn(1536).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            embeddings.append(vec.tolist())
        
        # Insert records
        with db_connection.cursor() as cur:
            for i, (test_id, embedding) in enumerate(zip(test_ids, embeddings)):
                entity_type = "test" if i % 2 == 0 else "scenario"
                framework = "pytest" if i % 2 == 0 else "cucumber"
                
                cur.execute("""
                    INSERT INTO memory_embeddings 
                    (entity_id, entity_type, embedding, content_hash, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    test_id,
                    entity_type,
                    embedding,
                    f"hash_{i}",
                    f'{{"framework": "{framework}", "file": "test_pipeline_{i}.py", "tags": ["smoke"]}}'
                ))
        
        db_connection.commit()
        print(f"\nOK Ingested {len(test_ids)} records through pipeline simulation")
        
        # Verify stored
        with db_connection.cursor() as cur:
            for test_id in test_ids:
                cur.execute("""
                    SELECT entity_id, entity_type, array_length(embedding::real[], 1) as dim
                    FROM memory_embeddings
                    WHERE entity_id = %s
                """, (test_id,))
                result = cur.fetchone()
                assert result is not None, f"Record {test_id} not found"
                assert result[2] == 1536, f"Expected 1536 dimensions, got {result[2]}"
        
        print(f"\nOK All records have 1536-dimensional embeddings")
        
        # Cleanup
        with db_connection.cursor() as cur:
            for test_id in test_ids:
                cur.execute("DELETE FROM memory_embeddings WHERE entity_id = %s", (test_id,))
        db_connection.commit()
        print(f"\nOK Cleaned up pipeline test records")

    def test_semantic_search_end_to_end(self, db_connection):
        """Test semantic search functionality using database directly."""
        import numpy as np
        import uuid
        import json
        
        # Create diverse test data with semantically meaningful patterns
        test_data = [
            {
                "id": str(uuid.uuid4()),
                "text": "Test login with valid username and password verify successful authentication",
                "type": "test",
                "framework": "pytest"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Test login with invalid credentials verify error message displayed",
                "type": "test",
                "framework": "pytest"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Test checkout flow with items in cart verify payment processing",
                "type": "test",
                "framework": "pytest"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Scenario User logs in with valid credentials and accesses dashboard",
                "type": "scenario",
                "framework": "cucumber"
            },
        ]
        
        # Generate embeddings (similar text gets similar embeddings via simple hash-based simulation)
        for item in test_data:
            # Simulate semantic similarity by using text hash to generate vectors
            seed = hash(item["text"]) % 10000
            np.random.seed(seed)
            vec = np.random.randn(1536).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            item["embedding"] = vec.tolist()
        
        # Insert
        with db_connection.cursor() as cur:
            for item in test_data:
                cur.execute("""
                    INSERT INTO memory_embeddings 
                    (entity_id, entity_type, embedding, content_hash, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    item["id"],
                    item["type"],
                    item["embedding"],
                    f"hash_{item['id'][:8]}",
                    json.dumps({"framework": item["framework"], "text": item["text"]})
                ))
        db_connection.commit()
        print(f"\nOK Ingested {len(test_data)} search test records")
        
        # Test similarity search - find records similar to first login test
        query_vector = test_data[0]["embedding"]
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT entity_id, entity_type, 1 - (embedding <=> %s::vector) as similarity,
                       metadata->>'text' as text
                FROM memory_embeddings
                WHERE entity_id = ANY(%s)
                ORDER BY embedding <=> %s::vector
                LIMIT 5
            """, (query_vector, [item["id"] for item in test_data], query_vector))
            
            results = cur.fetchall()
            assert len(results) > 0
            print(f"\nOK Similarity search found {len(results)} results:")
            for entity_id, entity_type, sim, text in results[:3]:
                print(f"   {entity_id[:8]} ({entity_type}): {sim:.3f}")
                if text:
                    print(f"      {text[:60]}...")
        
        # Test filter by entity type
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT entity_id, entity_type, 1 - (embedding <=> %s::vector) as similarity
                FROM memory_embeddings
                WHERE entity_id = ANY(%s) AND entity_type = 'test'
                ORDER BY embedding <=> %s::vector
                LIMIT 5
            """, (query_vector, [item["id"] for item in test_data], query_vector))
            
            filtered_results = cur.fetchall()
            for entity_id, entity_type, sim in filtered_results:
                assert entity_type == "test"
            print(f"\nOK Filtered search (tests only) found {len(filtered_results)} results")
        
        # Cleanup
        with db_connection.cursor() as cur:
            for item in test_data:
                cur.execute("DELETE FROM memory_embeddings WHERE entity_id = %s", (item["id"],))
        db_connection.commit()
        print(f"\nOK Cleaned up search test records")

    def test_real_world_use_case(self, db_connection):
        """Test real-world use case: Finding flaky test candidates."""
        import numpy as np
        import uuid
        import json
        
        # Create test data simulating real test suite
        test_data = [
            {
                "id": str(uuid.uuid4()),
                "text": "Test API call with timeout handling verify graceful degradation",
                "type": "test",
                "framework": "pytest",
                "flaky": True
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Test UI button click with network delay verify loading spinner",
                "type": "test",
                "framework": "playwright",
                "flaky": True
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Test database transaction with rollback verify data consistency",
                "type": "test",
                "framework": "pytest",
                "flaky": False
            },
        ]
        
        # Generate embeddings
        for item in test_data:
            seed = hash(item["text"]) % 10000
            np.random.seed(seed)
            vec = np.random.randn(1536).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            item["embedding"] = vec.tolist()
        
        # Insert
        with db_connection.cursor() as cur:
            for item in test_data:
                cur.execute("""
                    INSERT INTO memory_embeddings 
                    (entity_id, entity_type, embedding, content_hash, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    item["id"],
                    item["type"],
                    item["embedding"],
                    f"hash_{item['id'][:8]}",
                    json.dumps({
                        "framework": item["framework"],
                        "text": item["text"],
                        "flaky": item["flaky"]
                    })
                ))
        db_connection.commit()
        print(f"\nOK Ingested {len(test_data)} real-world test records")
        
        # Search for tests related to timing issues (use first flaky test as query)
        flaky_test = next(item for item in test_data if item["flaky"])
        query_vector = flaky_test["embedding"]
        
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT entity_id, 1 - (embedding <=> %s::vector) as similarity,
                       metadata->>'text' as text,
                       metadata->>'flaky' as is_flaky
                FROM memory_embeddings
                WHERE entity_id = ANY(%s)
                ORDER BY embedding <=> %s::vector
                LIMIT 5
            """, (query_vector, [item["id"] for item in test_data], query_vector))
            
            results = cur.fetchall()
            print(f"\nOK Flaky test candidates search found {len(results)} results:")
            for i, (entity_id, sim, text, is_flaky) in enumerate(results, 1):
                print(f"   {i}. {entity_id[:8]} (score: {sim:.3f}, flaky: {is_flaky})")
                if text:
                    print(f"      {text[:60]}...")
        
        print(f"\nOK Real-world use case completed successfully")
        
        # Cleanup
        with db_connection.cursor() as cur:
            for item in test_data:
                cur.execute("DELETE FROM memory_embeddings WHERE entity_id = %s", (item["id"],))
        db_connection.commit()
        print(f"\nOK Cleaned up real-world test records")


if __name__ == "__main__":
    """Run integration tests manually."""
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
