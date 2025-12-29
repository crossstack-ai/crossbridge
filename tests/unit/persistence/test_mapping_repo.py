"""
Unit tests for mapping repository.

Tests cover:
- Inserting mappings (append-only)
- Finding mappings by test
- Getting impacted tests by page object
- Latest mappings deduplication
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, UTC
from persistence.repositories.mapping_repo import (
    insert_mapping,
    get_mappings_for_test as get_mappings_by_test,
    get_impacted_tests,
    get_latest_mappings_for_test,
    get_mapping_sources as get_mapping_source_stats
)
from persistence.models import TestPageMapping


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=None)
    return session


class TestInsertMapping:
    """Test insert_mapping function."""
    
    def test_insert_mapping_minimal(self, mock_session):
        """Test inserting mapping with minimal parameters."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [123]
        mock_session.execute.return_value = mock_result
        
        mapping_id = insert_mapping(
            session=mock_session,
            test_case_id=10,
            page_object_id=20,
            discovery_run_id=30,
            source="static_ast"
        )
        
        assert mapping_id == 123
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_insert_mapping_with_confidence(self, mock_session):
        """Test inserting mapping with confidence score."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [456]
        mock_session.execute.return_value = mock_result
        
        mapping_id = insert_mapping(
            session=mock_session,
            test_case_id=10,
            page_object_id=20,
            discovery_run_id=30,
            source="coverage",
            confidence=0.95
        )
        
        assert mapping_id == 456
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["confidence"] == 0.95
    
    def test_insert_mapping_append_only(self, mock_session):
        """Test that mappings are append-only (no ON CONFLICT)."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [789]
        mock_session.execute.return_value = mock_result
        
        # Insert same mapping twice
        mapping_id_1 = insert_mapping(
            session=mock_session,
            test_case_id=10,
            page_object_id=20,
            discovery_run_id=30,
            source="static_ast"
        )
        
        mock_result.inserted_primary_key = [790]
        
        mapping_id_2 = insert_mapping(
            session=mock_session,
            test_case_id=10,
            page_object_id=20,
            discovery_run_id=30,
            source="static_ast"
        )
        
        # Both inserts should succeed (append-only)
        assert mapping_id_1 == 789
        assert mapping_id_2 == 790
        assert mock_session.execute.call_count == 2
    
    def test_insert_mapping_different_sources(self, mock_session):
        """Test inserting mappings from different sources."""
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result
        
        sources = ["static_ast", "coverage", "ai", "manual"]
        
        for i, source in enumerate(sources):
            mock_result.inserted_primary_key = [100 + i]
            
            mapping_id = insert_mapping(
                session=mock_session,
                test_case_id=10,
                page_object_id=20,
                discovery_run_id=30,
                source=source
            )
            
            assert mapping_id == 100 + i
    
    def test_insert_mapping_error_handling(self, mock_session):
        """Test error handling in insert."""
        mock_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            insert_mapping(
                session=mock_session,
                test_case_id=10,
                page_object_id=20,
                discovery_run_id=30,
                source="static_ast"
            )
        
        mock_session.rollback.assert_called_once()


class TestGetMappingsByTest:
    """Test get_mappings_by_test function."""
    
    def test_get_mappings_by_test_multiple(self, mock_session):
        """Test retrieving multiple mappings for a test."""
        mock_rows = [
            MagicMock(
                id=1, test_case_id=10, page_object_id=20,
                discovery_run_id=30, source="static_ast",
                confidence=1.0, created_at=datetime.now(UTC)
            ),
            MagicMock(
                id=2, test_case_id=10, page_object_id=21,
                discovery_run_id=30, source="coverage",
                confidence=0.85, created_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        mappings = get_mappings_by_test(mock_session, 10)
        
        assert len(mappings) == 2
        assert mappings[0].test_case_id == 10
        assert mappings[0].source == "static_ast"
        assert mappings[1].source == "coverage"
    
    def test_get_mappings_by_test_filter_by_discovery(self, mock_session):
        """Test filtering mappings by discovery run."""
        mock_rows = [
            MagicMock(
                id=1, test_case_id=10, page_object_id=20,
                discovery_run_id=30, source="static_ast",
                confidence=1.0, created_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        mappings = get_mappings_by_test(mock_session, 10, discovery_run_id=30)
        
        assert len(mappings) == 1
        assert mappings[0].discovery_run_id == 30
    
    def test_get_mappings_by_test_empty(self, mock_session):
        """Test when test has no mappings."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        mappings = get_mappings_by_test(mock_session, 999)
        
        assert len(mappings) == 0


class TestGetImpactedTests:
    """Test get_impacted_tests function."""
    
    def test_get_impacted_tests_multiple(self, mock_session):
        """Test retrieving multiple impacted tests."""
        mock_rows = [
            MagicMock(
                id=1, test_case_id=10, page_object_id=20,
                discovery_run_id=30, source="static_ast",
                confidence=1.0, created_at=datetime.now(UTC)
            ),
            MagicMock(
                id=2, test_case_id=11, page_object_id=20,
                discovery_run_id=30, source="coverage",
                confidence=0.80, created_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        tests = get_impacted_tests(mock_session, 20)
        
        assert len(tests) == 2
        assert tests[0].page_object_id == 20
        assert tests[1].page_object_id == 20
    
    def test_get_impacted_tests_with_confidence_threshold(self, mock_session):
        """Test filtering by confidence threshold."""
        mock_rows = [
            MagicMock(
                id=1, test_case_id=10, page_object_id=20,
                discovery_run_id=30, source="static_ast",
                confidence=1.0, created_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        # Query with high confidence threshold
        tests = get_impacted_tests(mock_session, 20, min_confidence=0.9)
        
        assert len(tests) == 1
        assert tests[0].confidence >= 0.9
    
    def test_get_impacted_tests_empty(self, mock_session):
        """Test when page object has no mappings."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        tests = get_impacted_tests(mock_session, 999)
        
        assert len(tests) == 0


class TestGetLatestMappingsForTest:
    """Test get_latest_mappings_for_test function."""
    
    def test_get_latest_mappings_deduplication(self, mock_session):
        """Test that latest mappings are deduplicated by page_object_id."""
        mock_rows = [
            MagicMock(
                id=3, test_case_id=10, page_object_id=20,
                discovery_run_id=32, source="coverage",
                confidence=0.95, created_at=datetime.now(UTC)
            ),
            MagicMock(
                id=4, test_case_id=10, page_object_id=21,
                discovery_run_id=32, source="static_ast",
                confidence=1.0, created_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        mappings = get_latest_mappings_for_test(mock_session, 10)
        
        # Should return latest mapping for each page_object_id
        assert len(mappings) == 2
        assert mappings[0].page_object_id == 20
        assert mappings[1].page_object_id == 21
    
    def test_get_latest_mappings_empty(self, mock_session):
        """Test when test has no mappings."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        mappings = get_latest_mappings_for_test(mock_session, 999)
        
        assert len(mappings) == 0


class TestGetMappingSourceStats:
    """Test get_mapping_source_stats function."""
    
    def test_get_mapping_source_stats_multiple_sources(self, mock_session):
        """Test getting statistics for multiple sources."""
        mock_rows = [
            MagicMock(source="static_ast", count=100),
            MagicMock(source="coverage", count=50),
            MagicMock(source="ai", count=10)
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        stats = get_mapping_source_stats(mock_session)
        
        assert len(stats) == 3
        assert stats[0]["source"] == "static_ast"
        assert stats[0]["count"] == 100
        assert stats[1]["source"] == "coverage"
        assert stats[1]["count"] == 50
    
    def test_get_mapping_source_stats_filter_by_discovery(self, mock_session):
        """Test filtering stats by discovery run."""
        mock_rows = [
            MagicMock(source="static_ast", count=25)
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        stats = get_mapping_source_stats(mock_session, discovery_run_id=30)
        
        assert len(stats) == 1
        assert stats[0]["count"] == 25
    
    def test_get_mapping_source_stats_empty(self, mock_session):
        """Test when no mappings exist."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        stats = get_mapping_source_stats(mock_session)
        
        assert len(stats) == 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_insert_mapping_zero_confidence(self, mock_session):
        """Test inserting mapping with zero confidence."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [111]
        mock_session.execute.return_value = mock_result
        
        mapping_id = insert_mapping(
            session=mock_session,
            test_case_id=10,
            page_object_id=20,
            discovery_run_id=30,
            source="ai",
            confidence=0.0
        )
        
        assert mapping_id == 111
    
    def test_insert_mapping_max_confidence(self, mock_session):
        """Test inserting mapping with max confidence."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [222]
        mock_session.execute.return_value = mock_result
        
        mapping_id = insert_mapping(
            session=mock_session,
            test_case_id=10,
            page_object_id=20,
            discovery_run_id=30,
            source="static_ast",
            confidence=1.0
        )
        
        assert mapping_id == 222
    
    def test_get_impacted_tests_zero_confidence_threshold(self, mock_session):
        """Test impact analysis with zero confidence threshold."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        tests = get_impacted_tests(mock_session, 20, min_confidence=0.0)
        
        # Should include all tests
        assert isinstance(tests, list)
    
    def test_get_impacted_tests_high_confidence_threshold(self, mock_session):
        """Test impact analysis with very high confidence threshold."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        tests = get_impacted_tests(mock_session, 20, min_confidence=0.99)
        
        # Should filter to only high-confidence mappings
        assert isinstance(tests, list)


class TestContractStability:
    """Test that API contracts remain stable."""
    
    def test_insert_returns_int(self, mock_session):
        """Test that insert returns an integer."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [123]
        mock_session.execute.return_value = mock_result
        
        mapping_id = insert_mapping(
            session=mock_session,
            test_case_id=10,
            page_object_id=20,
            discovery_run_id=30,
            source="static_ast"
        )
        
        assert isinstance(mapping_id, int)
    
    def test_get_mappings_returns_list(self, mock_session):
        """Test that get_mappings_by_test returns list."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        mappings = get_mappings_by_test(mock_session, 10)
        
        assert isinstance(mappings, list)
    
    def test_get_impacted_tests_returns_list(self, mock_session):
        """Test that get_impacted_tests returns list."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        tests = get_impacted_tests(mock_session, 20)
        
        assert isinstance(tests, list)
    
    def test_get_source_stats_returns_list_of_dicts(self, mock_session):
        """Test that get_mapping_source_stats returns list of dicts."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        stats = get_mapping_source_stats(mock_session)
        
        assert isinstance(stats, list)
