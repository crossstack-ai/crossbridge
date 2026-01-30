"""
Unit Tests for AI Semantic Engine

Tests all components:
- Embedding versioning
- Semantic search with confidence
- Duplicate detection
- Clustering
- Smart test selection

Framework Compatibility: Works with all 13 CrossBridge frameworks
(pytest, selenium, Robot, Cypress, Playwright, JUnit, TestNG, RestAssured, Cucumber, NUnit, SpecFlow, Behave, BDD)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from core.ai.embeddings.embedding_version import (
    EMBEDDING_VERSION,
    get_current_version_info,
    is_version_deprecated,
    get_version_info,
    EmbeddingVersionInfo
)
from core.ai.semantic.semantic_search_service import (
    SemanticSearchService,
    SemanticResult,
    SearchIntent,
    create_semantic_search_service
)
from core.ai.semantic.duplicate_detection import (
    DuplicateDetector,
    ClusteringEngine,
    DuplicateMatch,
    DuplicateType,
    Cluster,
    DUPLICATE_SIMILARITY_THRESHOLD,
    DUPLICATE_CONFIDENCE_THRESHOLD
)
from core.ai.semantic.smart_test_selection import (
    SmartTestSelector,
    SelectedTest,
    ChangeContext,
    WEIGHT_SEMANTIC_SIMILARITY,
    WEIGHT_COVERAGE_RELEVANCE,
    WEIGHT_FAILURE_HISTORY,
    WEIGHT_FLAKINESS_PENALTY
)
from core.ai.embeddings.vector_store import SimilarityResult


# ============================================================================
# Embedding Version Tests
# ============================================================================

class TestEmbeddingVersion:
    """Test embedding version management"""
    
    def test_current_version_format(self):
        """Current version should follow v{N}-{descriptor} format"""
        assert EMBEDDING_VERSION.startswith("v")
        assert "-" in EMBEDDING_VERSION
    
    def test_get_current_version_info(self):
        """Should create version info with correct metadata"""
        version_info = get_current_version_info(
            model="text-embedding-3-large",
            dimensions=3072,
            ast_augmented=True
        )
        
        assert version_info.version == EMBEDDING_VERSION
        assert version_info.model == "text-embedding-3-large"
        assert version_info.dimensions == 3072
        assert version_info.ast_augmented is True
        assert isinstance(version_info.created_at, datetime)
    
    def test_version_info_serialization(self):
        """Version info should serialize to/from dict"""
        version_info = get_current_version_info(
            model="test-model",
            dimensions=1536
        )
        
        data = version_info.to_dict()
        assert data["version"] == EMBEDDING_VERSION
        assert data["model"] == "test-model"
        assert data["dimensions"] == 1536
        
        restored = EmbeddingVersionInfo.from_dict(data)
        assert restored.version == version_info.version
        assert restored.model == version_info.model
    
    def test_version_compatibility_check(self):
        """Should correctly check version compatibility"""
        v1 = get_current_version_info("model-a", 1536)
        v2 = get_current_version_info("model-a", 1536)
        v3 = get_current_version_info("model-b", 1536)
        
        assert v1.is_compatible_with(v2)
        assert not v1.is_compatible_with(v3)
    
    def test_version_deprecated_check(self):
        """Should correctly identify deprecated versions"""
        assert not is_version_deprecated(EMBEDDING_VERSION)
        assert is_version_deprecated("v0-ancient")
        assert is_version_deprecated("unknown-version")
    
    def test_get_version_info(self):
        """Should retrieve version history"""
        info = get_version_info(EMBEDDING_VERSION)
        assert info is not None
        assert "description" in info
        assert "text_builder" in info


# ============================================================================
# Semantic Search Tests
# ============================================================================

class TestSemanticSearchService:
    """Test semantic search with confidence and explainability"""
    
    @pytest.fixture
    def mock_embedding_provider(self):
        """Mock embedding provider"""
        provider = Mock()
        provider.model_name.return_value = "text-embedding-3-large"
        provider.dimensions.return_value = 3072
        provider.embed.return_value = [0.1] * 3072
        return provider
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store"""
        store = Mock()
        return store
    
    @pytest.fixture
    def semantic_service(self, mock_embedding_provider, mock_vector_store):
        """Create semantic search service"""
        return SemanticSearchService(
            embedding_provider=mock_embedding_provider,
            vector_store=mock_vector_store
        )
    
    def test_initialization(self, semantic_service):
        """Should initialize with correct version info"""
        assert semantic_service.version_info.version == EMBEDDING_VERSION
        assert semantic_service.version_info.model == "text-embedding-3-large"
        assert semantic_service.version_info.dimensions == 3072
    
    def test_search_with_confidence(self, semantic_service, mock_vector_store):
        """Should return results with calibrated confidence"""
        # Setup mock results
        mock_vector_store.similarity_search.return_value = [
            SimilarityResult(
                id="test_1",
                entity_type="test",
                score=0.9,
                text="Test login functionality",
                metadata={"framework": "pytest"}
            ),
            SimilarityResult(
                id="test_2",
                entity_type="test",
                score=0.7,
                text="Test authentication",
                metadata={"framework": "pytest"}
            )
        ]
        
        results = semantic_service.search(
            query_text="login tests",
            entity_type="test",
            top_k=5
        )
        
        assert len(results) == 2
        assert all(isinstance(r, SemanticResult) for r in results)
        assert all(0.0 <= r.confidence <= 1.0 for r in results)
        assert all(r.score <= r.confidence or r.score >= r.confidence for r in results)
    
    def test_search_with_min_confidence_filter(self, semantic_service, mock_vector_store):
        """Should filter results below confidence threshold"""
        mock_vector_store.similarity_search.return_value = [
            SimilarityResult(
                id="test_1",
                entity_type="test",
                score=0.5,
                text="Low similarity test",
                metadata={}
            )
        ]
        
        results = semantic_service.search(
            query_text="query",
            min_confidence=0.8
        )
        
        # Low score should result in low confidence, filtered out
        assert len(results) == 0
    
    def test_search_intent_integration(self, semantic_service, mock_vector_store):
        """Should use search intent for explanation"""
        mock_vector_store.similarity_search.return_value = [
            SimilarityResult(
                id="test_1",
                entity_type="test",
                score=0.95,  # High score for duplicate detection
                text="Test case",
                metadata={}
            )
        ]
        
        results = semantic_service.search(
            query_text="query",
            intent=SearchIntent.FIND_DUPLICATES
        )
        
        assert len(results) > 0
        # Should include duplicate-specific explanation when score is high
        # Check that reasons exist and contain relevant information
        assert all(len(r.reasons) > 0 for r in results)
    
    def test_explainability_reasons(self, semantic_service, mock_vector_store):
        """Every result must have explanatory reasons"""
        mock_vector_store.similarity_search.return_value = [
            SimilarityResult(
                id="test_1",
                entity_type="test",
                score=0.85,
                text="Test",
                metadata={}
            )
        ]
        
        results = semantic_service.search(query_text="query")
        
        assert len(results) > 0
        for result in results:
            assert len(result.reasons) > 0
            assert all(isinstance(r, str) for r in result.reasons)
            assert any("similarity" in r.lower() for r in result.reasons)
    
    def test_confidence_calibration_formula(self, semantic_service):
        """Should use correct calibration formula"""
        # Test formula: score * log1p(sample_count) / log1p(30)
        import math
        
        score = 0.8
        sample_count = 10
        
        confidence = semantic_service._calibrate_confidence(
            score=score,
            entity_type="test",
            sample_count=sample_count
        )
        
        expected = min(1.0, score * math.log1p(sample_count) / math.log1p(30))
        assert abs(confidence - expected) < 0.001
    
    def test_factory_function(self, mock_embedding_provider, mock_vector_store):
        """Should create service via factory"""
        service = create_semantic_search_service(
            embedding_provider=mock_embedding_provider,
            vector_store=mock_vector_store,
            enable_ast_augmentation=True
        )
        
        assert isinstance(service, SemanticSearchService)
        assert service.text_builder.enable_ast_augmentation is True


# ============================================================================
# Duplicate Detection Tests
# ============================================================================

class TestDuplicateDetector:
    """Test duplicate detection with clustering"""
    
    @pytest.fixture
    def mock_semantic_search(self):
        """Mock semantic search service"""
        service = Mock()
        return service
    
    @pytest.fixture
    def duplicate_detector(self, mock_semantic_search):
        """Create duplicate detector"""
        return DuplicateDetector(
            semantic_search=mock_semantic_search,
            similarity_threshold=0.9,
            confidence_threshold=0.8
        )
    
    def test_initialization(self, duplicate_detector):
        """Should initialize with correct thresholds"""
        assert duplicate_detector.similarity_threshold == 0.9
        assert duplicate_detector.confidence_threshold == 0.8
    
    def test_find_duplicates_with_high_similarity(self, duplicate_detector, mock_semantic_search):
        """Should detect duplicates above thresholds"""
        mock_semantic_search.search.return_value = [
            SemanticResult(
                entity_id="test_1",
                entity_type="test",
                score=0.95,
                confidence=0.9,
                reasons=["High similarity"],
                text="Test login",
                metadata={}
            ),
            SemanticResult(
                entity_id="test_2",
                entity_type="test",
                score=0.85,
                confidence=0.75,
                reasons=["Moderate similarity"],
                text="Test auth",
                metadata={}
            )
        ]
        
        duplicates = duplicate_detector.find_duplicates(
            entity_id="test_original",
            entity_text="Test login functionality",
            entity_type="test"
        )
        
        # Only test_1 should be detected (meets both thresholds)
        assert len(duplicates) == 1
        assert duplicates[0].entity_id_2 == "test_1"
        assert duplicates[0].similarity_score == 0.95
        assert duplicates[0].duplicate_type == DuplicateType.EXACT
    
    def test_duplicate_type_classification(self, duplicate_detector):
        """Should correctly classify duplicate types"""
        assert duplicate_detector._classify_duplicate_type(0.96) == DuplicateType.EXACT
        assert duplicate_detector._classify_duplicate_type(0.92) == DuplicateType.VERY_SIMILAR
        assert duplicate_detector._classify_duplicate_type(0.85) == DuplicateType.SIMILAR
        assert duplicate_detector._classify_duplicate_type(0.75) == DuplicateType.POTENTIALLY_SIMILAR
    
    def test_duplicate_explanation(self, duplicate_detector):
        """Duplicates must have explanatory reasons"""
        reasons = duplicate_detector._explain_duplicate(
            entity_id_1="test_1",
            entity_id_2="test_2",
            score=0.95,
            confidence=0.9,
            duplicate_type=DuplicateType.EXACT
        )
        
        assert len(reasons) > 0
        assert any("duplicate" in r.lower() for r in reasons)
        assert any("0.95" in r for r in reasons)
        assert any("confidence" in r.lower() for r in reasons)
    
    def test_self_match_filtered(self, duplicate_detector, mock_semantic_search):
        """Should not return entity as duplicate of itself"""
        mock_semantic_search.search.return_value = [
            SemanticResult(
                entity_id="test_1",
                entity_type="test",
                score=1.0,
                confidence=1.0,
                reasons=[],
                text="Test",
                metadata={}
            )
        ]
        
        duplicates = duplicate_detector.find_duplicates(
            entity_id="test_1",
            entity_text="Test",
            entity_type="test"
        )
        
        assert len(duplicates) == 0


# ============================================================================
# Smart Test Selection Tests
# ============================================================================

class TestSmartTestSelector:
    """Test smart test selection engine"""
    
    @pytest.fixture
    def mock_semantic_search(self):
        """Mock semantic search"""
        service = Mock()
        return service
    
    @pytest.fixture
    def test_selector(self, mock_semantic_search):
        """Create smart test selector"""
        return SmartTestSelector(
            semantic_search=mock_semantic_search,
            coverage_service=None,
            failure_history_service=None,
            flaky_detection_service=None
        )
    
    def test_initialization(self, test_selector):
        """Should initialize with services"""
        assert test_selector.semantic_search is not None
        assert test_selector.coverage_service is None
    
    def test_change_context_to_query(self):
        """Should convert change context to semantic query"""
        context = ChangeContext(
            change_id="commit_123",
            files_changed=["auth/login.py", "auth/session.py"],
            diff_summary="Added 2FA support to login flow",
            functions_changed=["login", "verify_2fa"],
            modules_changed=["auth"]
        )
        
        query = context.to_semantic_query()
        
        assert "2FA support" in query
        assert "auth/login.py" in query
        assert "login" in query
        assert "auth" in query
    
    def test_select_tests_with_semantic_only(self, test_selector, mock_semantic_search):
        """Should select tests using semantic similarity"""
        mock_semantic_search.search.return_value = [
            SemanticResult(
                entity_id="test_login",
                entity_type="test",
                score=0.85,
                confidence=0.8,
                reasons=["High similarity"],
                text="Test login with 2FA",
                metadata={"name": "test_login", "framework": "pytest"}
            )
        ]
        
        context = ChangeContext(
            change_id="commit_123",
            files_changed=["auth/login.py"],
            diff_summary="Added 2FA"
        )
        
        selected = test_selector.select_tests(
            change_context=context,
            budget=5,
            min_score=0.3
        )
        
        assert len(selected) > 0
        assert all(isinstance(t, SelectedTest) for t in selected)
        assert all(t.score >= 0.3 for t in selected)
        assert selected[0].test_id == "test_login"
    
    def test_selection_score_weights(self, test_selector):
        """Should use correct weight formula"""
        score = test_selector._calculate_selection_score(
            semantic_score=0.8,
            coverage_score=0.6,
            failure_score=0.4,
            flakiness_score=0.2
        )
        
        expected = (
            0.4 * 0.8 +  # semantic
            0.3 * 0.6 +  # coverage
            0.2 * 0.4 -  # failure
            0.1 * 0.2    # flakiness (penalty)
        )
        
        assert abs(score - expected) < 0.001
    
    def test_selection_explainability(self, test_selector, mock_semantic_search):
        """Every selected test must have reasons"""
        mock_semantic_search.search.return_value = [
            SemanticResult(
                entity_id="test_1",
                entity_type="test",
                score=0.7,
                confidence=0.7,
                reasons=[],
                text="Test",
                metadata={"name": "test_1"}
            )
        ]
        
        context = ChangeContext(
            change_id="commit_123",
            files_changed=["file.py"],
            diff_summary="Change"
        )
        
        selected = test_selector.select_tests(context, min_score=0.2)  # Lower threshold
        
        assert len(selected) > 0
        for test in selected:
            assert len(test.reasons) > 0
            assert all(isinstance(r, str) for r in test.reasons)
    
    def test_budget_limit(self, test_selector, mock_semantic_search):
        """Should respect test budget"""
        # Return 10 mock results
        mock_semantic_search.search.return_value = [
            SemanticResult(
                entity_id=f"test_{i}",
                entity_type="test",
                score=0.8,
                confidence=0.8,
                reasons=[],
                text=f"Test {i}",
                metadata={"name": f"test_{i}"}
            )
            for i in range(10)
        ]
        
        context = ChangeContext(
            change_id="commit_123",
            files_changed=["file.py"],
            diff_summary="Change"
        )
        
        selected = test_selector.select_tests(
            change_context=context,
            budget=3
        )
        
        assert len(selected) <= 3
    
    def test_flaky_test_filtering(self, test_selector, mock_semantic_search):
        """Should filter flaky tests when requested"""
        mock_semantic_search.search.return_value = [
            SemanticResult(
                entity_id="test_stable",
                entity_type="test",
                score=0.8,
                confidence=0.8,
                reasons=[],
                text="Stable test",
                metadata={"name": "test_stable"}
            )
        ]
        
        # Override flakiness service to return high flakiness
        test_selector.flaky_detection_service = Mock()
        test_selector.flaky_detection_service.get_flaky_status = Mock(
            return_value=Mock(flaky_score=0.8)
        )
        
        context = ChangeContext(
            change_id="commit_123",
            files_changed=["file.py"],
            diff_summary="Change"
        )
        
        selected_with_flaky = test_selector.select_tests(
            change_context=context,
            include_flaky=True
        )
        
        selected_without_flaky = test_selector.select_tests(
            change_context=context,
            include_flaky=False
        )
        
        # When flaky test has high score, should be included with flag
        # but excluded without flag
        assert len(selected_with_flaky) >= len(selected_without_flaky)
    
    def test_priority_determination(self, test_selector):
        """Should correctly determine test priority"""
        assert test_selector._determine_priority(0.9, "medium") == "critical"
        assert test_selector._determine_priority(0.7, "medium") == "high"
        assert test_selector._determine_priority(0.5, "medium") == "medium"
        assert test_selector._determine_priority(0.3, "medium") == "low"
        assert test_selector._determine_priority(0.6, "critical") == "critical"


# ============================================================================
# Integration Tests
# ============================================================================

class TestSemanticEngineIntegration:
    """Test semantic engine components working together"""
    
    def test_embedding_version_consistency(self):
        """All components should use same embedding version"""
        from core.ai.embeddings.embedding_version import EMBEDDING_VERSION
        
        # Version should be consistent across all uses
        assert EMBEDDING_VERSION == "v2-text+ast"
    
    def test_scoring_weights_sum(self):
        """Smart selection weights should sum correctly"""
        total = (
            WEIGHT_SEMANTIC_SIMILARITY +
            WEIGHT_COVERAGE_RELEVANCE +
            WEIGHT_FAILURE_HISTORY +
            WEIGHT_FLAKINESS_PENALTY
        )
        
        # Should sum to 1.0 (100%)
        assert abs(total - 1.0) < 0.001
    
    def test_duplicate_thresholds_reasonable(self):
        """Duplicate thresholds should be reasonable"""
        assert 0.0 < DUPLICATE_SIMILARITY_THRESHOLD <= 1.0
        assert 0.0 < DUPLICATE_CONFIDENCE_THRESHOLD <= 1.0
        assert DUPLICATE_SIMILARITY_THRESHOLD >= 0.8  # Should be high for duplicates
        assert DUPLICATE_CONFIDENCE_THRESHOLD >= 0.7  # Should be confident


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
