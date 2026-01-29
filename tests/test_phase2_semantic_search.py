"""
Unit tests for Phase-2 Semantic Search modules.

Tests AST extraction, FAISS backend, Graph similarity, and Confidence calibration.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import numpy as np

# AST Extraction Tests
from core.ai.embeddings.ast_extractor import (
    ASTSummary,
    ASTExtractor,
    PythonASTExtractor,
    JavaASTExtractor,
    JavaScriptASTExtractor,
    ASTExtractorFactory,
    augment_text_with_ast,
)

# FAISS Backend Tests
from core.ai.embeddings.faiss_store import (
    FAISSConfig,
    FaissVectorStore,
    create_faiss_store,
)
from core.ai.embeddings.vector_store import SimilarityResult

# Graph Similarity Tests
from core.ai.embeddings.graph_similarity import (
    GraphNode,
    GraphEdge,
    SimilarityGraph,
    GraphSimilarityScorer,
    GraphBuilder,
)

# Confidence Calibration Tests
from core.ai.embeddings.confidence import (
    ConfidenceLevel,
    SignalAgreement,
    ConfidenceFactors,
    CalibratedResult,
    ConfidenceCalibrator,
)


class TestASTExtractor:
    """Test AST extraction functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)
    
    def test_python_ast_extractor_basic(self, temp_dir):
        """Test basic Python AST extraction."""
        test_file = temp_dir / "test_login.py"
        test_file.write_text("""
import pytest
from selenium import webdriver

class TestLogin:
    def test_valid_login(self):
        driver = webdriver.Chrome()
        driver.get("http://example.com")
        assert driver.title == "Login"
        
    def test_invalid_login(self):
        assert False
""")
        
        extractor = PythonASTExtractor()
        summary = extractor.extract(test_file)
        
        assert summary.language == "python"
        assert "TestLogin" in summary.classes
        assert len(summary.methods) >= 2
        assert "pytest" in summary.imports or "selenium" in summary.imports
        assert summary.assertions >= 2
        
    def test_python_ast_control_flow(self, temp_dir):
        """Test control flow extraction."""
        test_file = temp_dir / "test_complex.py"
        test_file.write_text("""
def test_complex():
    if condition:
        for item in items:
            try:
                process(item)
            except Exception:
                pass
""")
        
        extractor = PythonASTExtractor()
        summary = extractor.extract(test_file)
        
        assert summary.control_flow["if"] >= 1
        assert summary.control_flow["loop"] >= 1
        assert summary.control_flow["try"] >= 1
        
    def test_java_ast_extractor_basic(self, temp_dir):
        """Test basic Java AST extraction (pattern matching)."""
        test_file = temp_dir / "LoginTest.java"
        test_file.write_text("""
import org.junit.Test;
import static org.junit.Assert.*;

public class LoginTest {
    @Test
    public void testValidLogin() {
        String result = loginService.login("user", "pass");
        assertEquals("success", result);
    }
    
    @Test
    public void testInvalidLogin() {
        assertTrue(loginService.isLocked());
    }
}
""")
        
        extractor = JavaASTExtractor()
        summary = extractor.extract(test_file)
        
        assert summary.language == "java"
        assert "LoginTest" in summary.classes
        assert len(summary.methods) >= 2
        assert "org.junit" in " ".join(summary.imports)
        assert summary.assertions >= 2
        
    def test_javascript_ast_extractor_basic(self, temp_dir):
        """Test basic JavaScript AST extraction."""
        test_file = temp_dir / "login.spec.js"
        test_file.write_text("""
describe('Login Tests', () => {
    it('should login successfully', () => {
        cy.visit('/login');
        cy.get('#username').type('user');
        cy.get('#password').type('pass');
        cy.get('#submit').click();
        cy.url().should('include', '/dashboard');
    });
    
    it('should show error for invalid credentials', () => {
        expect(loginPage.errorMessage).toBeVisible();
    });
});
""")
        
        extractor = JavaScriptASTExtractor()
        summary = extractor.extract(test_file)
        
        assert summary.language == "javascript"
        assert len(summary.methods) >= 2
        assert summary.assertions >= 1
        
    def test_ast_extractor_factory(self, temp_dir):
        """Test AST extractor factory for language detection."""
        python_file = temp_dir / "test.py"
        python_file.write_text("def test(): pass")
        
        java_file = temp_dir / "Test.java"
        java_file.write_text("public class Test {}")
        
        js_file = temp_dir / "test.spec.js"
        js_file.write_text("describe('test', () => {})")
        
        factory = ASTExtractorFactory()
        
        assert isinstance(factory.create_extractor(python_file), PythonASTExtractor)
        assert isinstance(factory.create_extractor(java_file), JavaASTExtractor)
        assert isinstance(factory.create_extractor(js_file), JavaScriptASTExtractor)
        
    def test_augment_text_with_ast(self, temp_dir):
        """Test AST augmentation appends to base text."""
        test_file = temp_dir / "test.py"
        test_file.write_text("""
import pytest

class TestLogin:
    def test_login(self):
        assert True
""")
        
        base_text = "Test login functionality"
        augmented = augment_text_with_ast(base_text, test_file)
        
        # Verify base text is preserved
        assert augmented.startswith(base_text)
        assert "\n\n---\n\nCode Structure" in augmented
        assert "python" in augmented.lower()
        assert "TestLogin" in augmented or "test_login" in augmented
        
    def test_ast_summary_to_text(self):
        """Test AST summary text generation."""
        summary = ASTSummary(
            language="python",
            classes=["TestLogin", "TestLogout"],
            methods=["test_valid_login", "test_invalid_login"],
            imports=["pytest", "selenium"],
            assertions=3,
            control_flow={"if": 2, "loop": 1, "try": 1},
        )
        
        text = summary.to_text()
        
        assert "python" in text.lower()
        assert "TestLogin" in text
        assert "test_valid_login" in text
        assert "pytest" in text
        assert "3" in text  # assertions count


class TestFAISSBackend:
    """Test FAISS vector store functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for FAISS index."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)
    
    def test_faiss_store_initialization(self, temp_dir):
        """Test FAISS store initialization."""
        config = FAISSConfig(
            dimensions=128,
            index_type="flat",
            metric="cosine",
            persist_path=str(temp_dir / "index"),
        )
        
        store = FaissVectorStore(config)
        
        assert store.config == config
        assert store.dimensions == 128
        assert store.index is not None
        
    def test_faiss_store_add_entity(self, temp_dir):
        """Test adding entity to FAISS store."""
        config = FAISSConfig(dimensions=128, persist_path=str(temp_dir / "index"))
        store = FaissVectorStore(config)
        
        entity_id = "test_1"
        embedding = np.random.rand(128).tolist()
        metadata = {"type": "test", "framework": "pytest"}
        
        store.add(entity_id, embedding, metadata)
        
        # Verify entity was added
        assert entity_id in store._id_to_internal
        assert len(store._metadata) == 1
        assert store._metadata[0]["entity_id"] == entity_id
        
    def test_faiss_store_search(self, temp_dir):
        """Test searching in FAISS store."""
        config = FAISSConfig(dimensions=128, persist_path=str(temp_dir / "index"))
        store = FaissVectorStore(config)
        
        # Add some entities
        for i in range(10):
            embedding = np.random.rand(128).tolist()
            store.add(f"test_{i}", embedding, {"type": "test", "id": i})
        
        # Search
        query_embedding = np.random.rand(128).tolist()
        results = store.search(query_embedding, top_k=5)
        
        assert len(results) <= 5
        for result in results:
            assert isinstance(result, SimilarityResult)
            assert result.entity_id.startswith("test_")
            assert 0.0 <= result.similarity_score <= 1.0
            
    def test_faiss_store_persistence(self, temp_dir):
        """Test saving and loading FAISS index."""
        config = FAISSConfig(
            dimensions=128,
            persist_path=str(temp_dir / "index"),
            auto_persist=True,
        )
        store = FaissVectorStore(config)
        
        # Add entities
        for i in range(5):
            embedding = np.random.rand(128).tolist()
            store.add(f"test_{i}", embedding, {"type": "test"})
        
        # Save
        store.save()
        
        # Load in new store
        new_store = FaissVectorStore(config)
        new_store.load()
        
        # Verify entities are present
        assert len(new_store._metadata) == 5
        assert "test_0" in new_store._id_to_internal
        
    def test_faiss_store_metadata_filtering(self, temp_dir):
        """Test metadata filtering after search."""
        config = FAISSConfig(dimensions=128, persist_path=str(temp_dir / "index"))
        store = FaissVectorStore(config)
        
        # Add entities with different frameworks
        for i in range(5):
            embedding = np.random.rand(128).tolist()
            store.add(f"pytest_{i}", embedding, {"type": "test", "framework": "pytest"})
        
        for i in range(5):
            embedding = np.random.rand(128).tolist()
            store.add(f"junit_{i}", embedding, {"type": "test", "framework": "junit"})
        
        # Search with filter
        query_embedding = np.random.rand(128).tolist()
        results = store.search(
            query_embedding,
            top_k=10,
            filters={"framework": "pytest"},
        )
        
        # All results should be pytest
        for result in results:
            assert result.entity_id.startswith("pytest_")
            
    def test_create_faiss_store_factory(self, temp_dir):
        """Test FAISS store factory function."""
        store = create_faiss_store(
            dimensions=128,
            index_type="flat",
            metric="cosine",
            persist_path=str(temp_dir / "index"),
        )
        
        assert isinstance(store, FaissVectorStore)
        assert store.dimensions == 128


class TestGraphSimilarity:
    """Test graph-based similarity scoring."""
    
    def test_similarity_graph_initialization(self):
        """Test graph initialization."""
        graph = SimilarityGraph()
        
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        
    def test_add_nodes_and_edges(self):
        """Test adding nodes and edges to graph."""
        graph = SimilarityGraph()
        
        # Add nodes
        test_node = GraphNode(id="test_1", node_type="test", properties={"name": "test_login"})
        file_node = GraphNode(id="file_1", node_type="file", properties={"path": "login.py"})
        
        graph.add_node(test_node)
        graph.add_node(file_node)
        
        # Add edge
        edge = GraphEdge(source="test_1", target="file_1", edge_type="uses_file", weight=1.0)
        graph.add_edge(edge)
        
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert "test_1" in graph.adjacency
        assert "file_1" in graph.adjacency["test_1"]
        
    def test_get_neighbors(self):
        """Test getting node neighbors."""
        graph = SimilarityGraph()
        
        graph.add_node(GraphNode(id="test_1", node_type="test", properties={}))
        graph.add_node(GraphNode(id="file_1", node_type="file", properties={}))
        graph.add_node(GraphNode(id="file_2", node_type="file", properties={}))
        
        graph.add_edge(GraphEdge(source="test_1", target="file_1", edge_type="uses_file"))
        graph.add_edge(GraphEdge(source="test_1", target="file_2", edge_type="uses_file"))
        
        neighbors = graph.get_neighbors("test_1")
        
        assert len(neighbors) == 2
        assert "file_1" in neighbors
        assert "file_2" in neighbors
        
    def test_graph_similarity_scorer(self):
        """Test graph similarity scoring."""
        graph = SimilarityGraph()
        
        # Create test graph
        graph.add_node(GraphNode(id="test_1", node_type="test", properties={}))
        graph.add_node(GraphNode(id="test_2", node_type="test", properties={}))
        graph.add_node(GraphNode(id="file_1", node_type="file", properties={}))
        graph.add_node(GraphNode(id="file_2", node_type="file", properties={}))
        
        # test_1 uses file_1, file_2
        graph.add_edge(GraphEdge(source="test_1", target="file_1", edge_type="uses_file"))
        graph.add_edge(GraphEdge(source="test_1", target="file_2", edge_type="uses_file"))
        
        # test_2 uses file_1 (partial overlap)
        graph.add_edge(GraphEdge(source="test_2", target="file_1", edge_type="uses_file"))
        
        scorer = GraphSimilarityScorer(graph, semantic_weight=0.7, graph_weight=0.3)
        
        # Calculate similarity with semantic score
        semantic_score = 0.8
        combined_score = scorer.calculate_similarity("test_1", "test_2", semantic_score)
        
        # Combined score should be between semantic score and 1.0
        assert 0.0 <= combined_score <= 1.0
        # Graph overlap should boost the score slightly
        assert combined_score >= semantic_score * 0.7
        
    def test_jaccard_overlap(self):
        """Test Jaccard overlap calculation."""
        graph = SimilarityGraph()
        
        graph.add_node(GraphNode(id="test_1", node_type="test", properties={}))
        graph.add_node(GraphNode(id="test_2", node_type="test", properties={}))
        graph.add_node(GraphNode(id="file_1", node_type="file", properties={}))
        graph.add_node(GraphNode(id="file_2", node_type="file", properties={}))
        graph.add_node(GraphNode(id="file_3", node_type="file", properties={}))
        
        # test_1: file_1, file_2
        graph.add_edge(GraphEdge(source="test_1", target="file_1", edge_type="uses_file"))
        graph.add_edge(GraphEdge(source="test_1", target="file_2", edge_type="uses_file"))
        
        # test_2: file_2, file_3
        graph.add_edge(GraphEdge(source="test_2", target="file_2", edge_type="uses_file"))
        graph.add_edge(GraphEdge(source="test_2", target="file_3", edge_type="uses_file"))
        
        scorer = GraphSimilarityScorer(graph)
        overlap = scorer._jaccard_overlap("test_1", "test_2")
        
        # Intersection: {file_2}, Union: {file_1, file_2, file_3}
        # Jaccard = 1/3 = 0.333
        assert abs(overlap - 0.333) < 0.01
        
    def test_graph_builder(self):
        """Test graph builder from test data."""
        builder = GraphBuilder()
        
        # Build graph from test records
        test_data = [
            {
                "test_id": "test_1",
                "file_path": "tests/test_login.py",
                "methods": ["test_valid_login", "test_invalid_login"],
                "imports": ["pytest", "selenium"],
            },
            {
                "test_id": "test_2",
                "file_path": "tests/test_logout.py",
                "methods": ["test_logout"],
                "imports": ["pytest"],
            },
        ]
        
        graph = builder.build_from_tests(test_data)
        
        # Verify nodes were created
        assert len(graph.nodes) > 0
        # Verify edges were created
        assert len(graph.edges) > 0


class TestConfidenceCalibration:
    """Test confidence calibration functionality."""
    
    def test_confidence_level_classification(self):
        """Test confidence level enum."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"
        
    def test_signal_agreement_single_signal(self):
        """Test signal agreement with single signal."""
        agreement = SignalAgreement(text_score=0.9)
        
        score = agreement.agreement_score()
        
        # Single signal should return 1.0 (perfect agreement with itself)
        assert score == 1.0
        
    def test_signal_agreement_multiple_signals(self):
        """Test signal agreement with multiple signals."""
        # High agreement - all scores close
        agreement_high = SignalAgreement(
            text_score=0.9,
            ast_score=0.88,
            graph_score=0.92,
        )
        
        # Low agreement - scores diverge
        agreement_low = SignalAgreement(
            text_score=0.9,
            ast_score=0.3,
            graph_score=0.5,
        )
        
        high_score = agreement_high.agreement_score()
        low_score = agreement_low.agreement_score()
        
        # High agreement should score higher
        assert high_score > low_score
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= low_score <= 1.0
        
    def test_confidence_calibrator_basic(self):
        """Test basic confidence calibration."""
        calibrator = ConfidenceCalibrator(
            sample_threshold=30,
            min_confidence=0.1,
        )
        
        result = calibrator.calibrate(
            similarity_score=0.85,
            sample_count=50,
            agreement=SignalAgreement(text_score=0.85),
        )
        
        assert isinstance(result, CalibratedResult)
        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
        assert len(result.reasons) > 0
        
    def test_confidence_increases_with_samples(self):
        """Test confidence increases with more samples."""
        calibrator = ConfidenceCalibrator(sample_threshold=30)
        
        result_few = calibrator.calibrate(
            similarity_score=0.8,
            sample_count=5,
            agreement=SignalAgreement(text_score=0.8),
        )
        
        result_many = calibrator.calibrate(
            similarity_score=0.8,
            sample_count=100,
            agreement=SignalAgreement(text_score=0.8),
        )
        
        # More samples should yield higher confidence
        assert result_many.confidence >= result_few.confidence
        
    def test_confidence_with_consistency(self):
        """Test confidence with temporal consistency."""
        calibrator = ConfidenceCalibrator()
        
        # High consistency
        result_high = calibrator.calibrate(
            similarity_score=0.8,
            sample_count=30,
            agreement=SignalAgreement(text_score=0.8),
            consistency=0.95,
        )
        
        # Low consistency
        result_low = calibrator.calibrate(
            similarity_score=0.8,
            sample_count=30,
            agreement=SignalAgreement(text_score=0.8),
            consistency=0.5,
        )
        
        # High consistency should yield higher confidence
        assert result_high.confidence > result_low.confidence
        
    def test_confidence_level_thresholds(self):
        """Test confidence level classification."""
        calibrator = ConfidenceCalibrator()
        
        # High confidence
        result_high = calibrator.calibrate(
            similarity_score=0.95,
            sample_count=100,
            agreement=SignalAgreement(text_score=0.95, ast_score=0.93, graph_score=0.94),
            consistency=0.98,
        )
        
        # Low confidence
        result_low = calibrator.calibrate(
            similarity_score=0.4,
            sample_count=5,
            agreement=SignalAgreement(text_score=0.4),
            consistency=0.5,
        )
        
        assert result_high.confidence_level == ConfidenceLevel.HIGH
        assert result_low.confidence_level == ConfidenceLevel.LOW
        
    def test_confidence_reasons(self):
        """Test confidence reasons are provided."""
        calibrator = ConfidenceCalibrator()
        
        result = calibrator.calibrate(
            similarity_score=0.8,
            sample_count=30,
            agreement=SignalAgreement(text_score=0.8, ast_score=0.78, graph_score=0.82),
        )
        
        # Verify reasons are provided
        assert len(result.reasons) > 0
        # Should mention similarity, samples, and agreement
        reasons_text = " ".join(result.reasons)
        assert any(word in reasons_text.lower() for word in ["similarity", "score", "high", "samples", "agreement"])
        
    def test_batch_calibration(self):
        """Test batch confidence calibration."""
        calibrator = ConfidenceCalibrator()
        
        results = [
            {"similarity_score": 0.9, "sample_count": 50},
            {"similarity_score": 0.7, "sample_count": 20},
            {"similarity_score": 0.5, "sample_count": 10},
        ]
        
        calibrated = calibrator.calibrate_batch(results)
        
        assert len(calibrated) == 3
        for result in calibrated:
            assert isinstance(result, CalibratedResult)
            assert 0.0 <= result.confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
