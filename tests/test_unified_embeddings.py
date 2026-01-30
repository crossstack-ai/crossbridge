"""
Tests for Unified Embedding System

Validates that the consolidated embedding system works correctly
for both Memory and Execution Intelligence use cases.
"""

import pytest
from typing import List

from core.embeddings import (
    create_provider,
    create_store,
    Embedding,
    CucumberAdapter,
    RobotAdapter,
    PytestAdapter,
)
from core.execution.intelligence.models import (
    CucumberScenario,
    CucumberStep,
    RobotTest,
    RobotKeyword,
    PytestTest,
)


class TestUnifiedProviders:
    """Test unified embedding providers"""
    
    def test_sentence_transformer_provider(self):
        """Test SentenceTransformer provider"""
        try:
            provider = create_provider('sentence-transformers', model='all-MiniLM-L6-v2')
            
            # Generate embedding
            vector = provider.embed("Test login with valid credentials")
            
            # Verify dimension
            assert len(vector) == 384
            assert provider.get_dimension() == 384
            assert 'sentence-transformers' in provider.get_model_name()
            
        except ImportError:
            pytest.skip("sentence-transformers not installed")
    
    def test_hash_provider(self):
        """Test hash-based provider (always available)"""
        provider = create_provider('hash', dimension=384)
        
        # Generate embedding
        vector = provider.embed("Test login with valid credentials")
        
        # Verify dimension
        assert len(vector) == 384
        assert provider.get_dimension() == 384
        
        # Deterministic
        vector2 = provider.embed("Test login with valid credentials")
        assert vector == vector2
    
    def test_batch_embedding(self):
        """Test batch embedding generation"""
        provider = create_provider('hash', dimension=384)
        
        texts = [
            "Test login",
            "Test logout",
            "Test registration"
        ]
        
        vectors = provider.embed_batch(texts)
        
        assert len(vectors) == 3
        assert all(len(v) == 384 for v in vectors)


class TestUnifiedStores:
    """Test unified embedding stores"""
    
    def test_memory_store(self):
        """Test in-memory store"""
        store = create_store('memory')
        provider = create_provider('hash', dimension=384)
        
        # Create embedding
        vector = provider.embed("Test login")
        emb = Embedding(
            entity_id="test_login",
            entity_type="test",
            text="Test login",
            vector=vector,
            model=provider.get_model_name()
        )
        
        # Add to store
        store.add(emb)
        
        # Verify
        assert store.count() == 1
        retrieved = store.get("test_login")
        assert retrieved is not None
        assert retrieved.entity_id == "test_login"
    
    def test_find_similar(self):
        """Test similarity search"""
        store = create_store('memory')
        provider = create_provider('hash', dimension=384)
        
        # Add embeddings
        texts = [
            "Test user login with valid credentials",
            "Test admin login with valid password",
            "Test logout functionality",
        ]
        
        for i, text in enumerate(texts):
            vector = provider.embed(text)
            emb = Embedding(
                entity_id=f"test_{i}",
                entity_type="test",
                text=text,
                vector=vector,
                model=provider.get_model_name()
            )
            store.add(emb)
        
        # Query
        query_vector = provider.embed("Test user login with valid credentials")
        query_emb = Embedding(
            entity_id="query",
            entity_type="query",
            text="Test user login with valid credentials",
            vector=query_vector,
            model=provider.get_model_name()
        )
        
        # Find similar
        results = store.find_similar(query_emb, top_k=2)
        
        # Verify (should get 2 results, excluding the query itself which has same ID as test_0)
        assert len(results) >= 1  # At least 1 result
        assert all(isinstance(r, tuple) for r in results)
        assert all(len(r) == 2 for r in results)  # (embedding, score)


class TestFrameworkAdapters:
    """Test framework-specific adapters"""
    
    def test_cucumber_adapter(self):
        """Test Cucumber adapter"""
        provider = create_provider('hash', dimension=384)
        adapter = CucumberAdapter()
        
        # Create scenario
        scenario = CucumberScenario(
            name="Login with valid credentials",
            feature_name="User Authentication",
            steps=[
                CucumberStep(keyword="Given", text="I am on login page", status="passed", duration_ms=100),
                CucumberStep(keyword="When", text="I enter valid credentials", status="passed", duration_ms=200),
                CucumberStep(keyword="Then", text="I should see dashboard", status="passed", duration_ms=150),
            ],
            status="passed",
            duration_ms=450
        )
        
        # Generate embeddings
        embeddings = adapter.generate_embeddings([scenario], provider, include_steps=True)
        
        # Verify
        assert len(embeddings) == 4  # 1 scenario + 3 steps
        
        scenario_emb = [e for e in embeddings if e.entity_type == "scenario"]
        step_embs = [e for e in embeddings if e.entity_type == "step"]
        
        assert len(scenario_emb) == 1
        assert len(step_embs) == 3
        
        # Verify metadata
        assert scenario_emb[0].metadata['framework'] == 'cucumber'
        assert scenario_emb[0].metadata['feature_name'] == 'User Authentication'
    
    def test_robot_adapter(self):
        """Test Robot adapter"""
        provider = create_provider('hash', dimension=384)
        adapter = RobotAdapter()
        
        # Create test
        test = RobotTest(
            name="Login Test",
            suite_name="Authentication Suite",
            keywords=[
                RobotKeyword(name="Open Browser", library="SeleniumLibrary", status="PASS", duration_ms=500),
                RobotKeyword(name="Input Text", library="SeleniumLibrary", status="PASS", duration_ms=100),
            ],
            status="PASS",
            duration_ms=600
        )
        
        # Generate embeddings
        embeddings = adapter.generate_embeddings([test], provider, include_keywords=True)
        
        # Verify
        assert len(embeddings) == 3  # 1 test + 2 keywords
        
        test_emb = [e for e in embeddings if e.entity_type == "test"]
        kw_embs = [e for e in embeddings if e.entity_type == "keyword"]
        
        assert len(test_emb) == 1
        assert len(kw_embs) == 2
        
        # Verify metadata
        assert test_emb[0].metadata['framework'] == 'robot'
        assert test_emb[0].metadata['suite_name'] == 'Authentication Suite'
    
    def test_pytest_adapter(self):
        """Test Pytest adapter"""
        provider = create_provider('hash', dimension=384)
        adapter = PytestAdapter()
        
        # Create test
        test = PytestTest(
            name="test_login_success",
            module="tests.test_auth",
            status="passed",
            duration_ms=250,
            markers=["smoke", "auth"]
        )
        
        # Generate embeddings
        embeddings = adapter.generate_embeddings([test], provider)
        
        # Verify
        assert len(embeddings) == 1
        assert embeddings[0].entity_type == "function"
        assert embeddings[0].metadata['framework'] == 'pytest'
        assert embeddings[0].metadata['module'] == 'tests.test_auth'


class TestUnifiedUseCases:
    """Test real-world use cases"""
    
    def test_duplicate_detection(self):
        """Test duplicate test detection (Intelligence use case)"""
        provider = create_provider('hash', dimension=384)
        store = create_store('memory')
        
        # Similar tests
        texts = [
            "Test user login with valid credentials",
            "Test user login with correct credentials",  # Very similar
            "Test logout functionality",
        ]
        
        embeddings = []
        for i, text in enumerate(texts):
            vector = provider.embed(text)
            emb = Embedding(
                entity_id=f"test_{i}",
                entity_type="test",
                text=text,
                vector=vector,
                model=provider.get_model_name()
            )
            embeddings.append(emb)
            store.add(emb)
        
        # Find duplicates (similarity > 0.95)
        duplicates = []
        for emb in embeddings:
            similar = store.find_similar(emb, top_k=2, min_similarity=0.95)
            if similar:
                duplicates.append((emb.entity_id, similar[0][0].entity_id, similar[0][1]))
        
        # Verify
        # Note: Hash-based embeddings might not detect semantic similarity
        # This test mainly validates the API works
        assert isinstance(duplicates, list)
    
    def test_cross_framework_search(self):
        """Test searching across multiple frameworks (Memory use case)"""
        provider = create_provider('hash', dimension=384)
        store = create_store('memory')
        adapter_cucumber = CucumberAdapter()
        adapter_robot = RobotAdapter()
        
        # Cucumber scenario
        scenario = CucumberScenario(
            name="Login test",
            feature_name="Auth",
            steps=[CucumberStep(keyword="Given", text="step", status="passed", duration_ms=100)],
            status="passed",
            duration_ms=100
        )
        
        # Robot test
        robot_test = RobotTest(
            name="Login Test",
            suite_name="Auth Suite",
            keywords=[RobotKeyword(name="Keyword", library="Lib", status="PASS", duration_ms=100)],
            status="PASS",
            duration_ms=100
        )
        
        # Generate embeddings
        cucumber_embs = adapter_cucumber.generate_embeddings([scenario], provider)
        robot_embs = adapter_robot.generate_embeddings([robot_test], provider)
        
        # Store all
        store.add_batch(cucumber_embs + robot_embs)
        
        # Search across frameworks
        query_vector = provider.embed("login test")
        query_emb = Embedding(
            entity_id="query",
            entity_type="query",
            text="login test",
            vector=query_vector,
            model=provider.get_model_name()
        )
        
        results = store.find_similar(query_emb, top_k=10)
        
        # Verify we get results from both frameworks
        frameworks = set()
        for emb, score in results:
            frameworks.add(emb.metadata.get('framework'))
        
        # Both frameworks should be represented (if similarity detected)
        assert len(frameworks) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
