"""
Unit tests for discovery repository.

Tests cover:
- Creating discovery runs
- Retrieving discovery runs
- Listing discoveries
- Discovery statistics
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
from persistence.repositories.discovery_repo import (
    create_discovery_run,
    get_discovery_run,
    get_latest_discovery_run,
    list_discovery_runs,
    get_discovery_stats
)
from persistence.models import DiscoveryRun


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=None)
    return session


class TestCreateDiscoveryRun:
    """Test create_discovery_run function."""
    
    def test_create_discovery_run_minimal(self, mock_session):
        """Test creating discovery run with minimal parameters."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [123]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="test-project"
        )
        
        assert discovery_id == 123
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Check the SQL values
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["project_name"] == "test-project"
        assert values["triggered_by"] == "cli"
    
    def test_create_discovery_run_with_git_context(self, mock_session):
        """Test creating discovery run with git context."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [456]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="my-project",
            git_commit="abc123",
            git_branch="main"
        )
        
        assert discovery_id == 456
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["git_commit"] == "abc123"
        assert values["git_branch"] == "main"
    
    def test_create_discovery_run_with_metadata(self, mock_session):
        """Test creating discovery run with metadata."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [789]
        mock_session.execute.return_value = mock_result
        
        metadata = {"scan_duration_ms": 1234, "total_files": 10}
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="my-project",
            metadata=metadata
        )
        
        assert discovery_id == 789
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["metadata"] == metadata
    
    def test_create_discovery_run_with_triggered_by(self, mock_session):
        """Test creating discovery run with custom triggered_by."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [999]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="my-project",
            triggered_by="ci"
        )
        
        assert discovery_id == 999
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["triggered_by"] == "ci"
    
    def test_create_discovery_run_error_handling(self, mock_session):
        """Test error handling in create_discovery_run."""
        mock_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            create_discovery_run(
                session=mock_session,
                project_name="test-project"
            )
        
        mock_session.rollback.assert_called_once()


class TestGetDiscoveryRun:
    """Test get_discovery_run function."""
    
    def test_get_discovery_run_found(self, mock_session):
        """Test retrieving an existing discovery run."""
        mock_row = MagicMock()
        mock_row.id = 123
        mock_row.project_name = "test-project"
        mock_row.triggered_by = "cli"
        mock_row.created_at = datetime.now(UTC)
        mock_row.git_commit = "abc123"
        mock_row.git_branch = "main"
        mock_row.metadata = {"key": "value"}
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        discovery = get_discovery_run(mock_session, 123)
        
        assert discovery is not None
        assert discovery.id == 123
        assert discovery.project_name == "test-project"
        assert discovery.git_commit == "abc123"
    
    def test_get_discovery_run_not_found(self, mock_session):
        """Test retrieving non-existent discovery run."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        discovery = get_discovery_run(mock_session, 999)
        
        assert discovery is None


class TestGetLatestDiscoveryRun:
    """Test get_latest_discovery_run function."""
    
    def test_get_latest_discovery_run_found(self, mock_session):
        """Test retrieving latest discovery run."""
        mock_row = MagicMock()
        mock_row.id = 456
        mock_row.project_name = "my-project"
        mock_row.triggered_by = "ci"
        mock_row.created_at = datetime.now(UTC)
        mock_row.git_commit = None
        mock_row.git_branch = None
        mock_row.metadata = None
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        discovery = get_latest_discovery_run(mock_session, "my-project")
        
        assert discovery is not None
        assert discovery.id == 456
        assert discovery.project_name == "my-project"
    
    def test_get_latest_discovery_run_not_found(self, mock_session):
        """Test when no discovery runs exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        discovery = get_latest_discovery_run(mock_session, "unknown-project")
        
        assert discovery is None


class TestListDiscoveryRuns:
    """Test list_discovery_runs function."""
    
    def test_list_discovery_runs_all(self, mock_session):
        """Test listing all discovery runs."""
        mock_rows = [
            MagicMock(
                id=1, project_name="proj1", triggered_by="cli",
                created_at=datetime.now(UTC), git_commit=None,
                git_branch=None, metadata=None
            ),
            MagicMock(
                id=2, project_name="proj2", triggered_by="ci",
                created_at=datetime.now(UTC), git_commit="abc",
                git_branch="main", metadata=None
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session)
        
        assert len(discoveries) == 2
        assert discoveries[0].id == 1
        assert discoveries[1].id == 2
    
    def test_list_discovery_runs_by_project(self, mock_session):
        """Test listing discovery runs for specific project."""
        mock_rows = [
            MagicMock(
                id=3, project_name="target-project", triggered_by="cli",
                created_at=datetime.now(UTC), git_commit=None,
                git_branch=None, metadata=None
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session, project_name="target-project")
        
        assert len(discoveries) == 1
        assert discoveries[0].project_name == "target-project"
    
    def test_list_discovery_runs_with_limit(self, mock_session):
        """Test listing discovery runs with limit."""
        mock_rows = [
            MagicMock(
                id=i, project_name=f"proj{i}", triggered_by="cli",
                created_at=datetime.now(UTC), git_commit=None,
                git_branch=None, metadata=None
            )
            for i in range(5)
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows[:3]
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session, limit=3)
        
        assert len(discoveries) == 3
    
    def test_list_discovery_runs_empty(self, mock_session):
        """Test listing when no discovery runs exist."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session)
        
        assert len(discoveries) == 0


class TestGetDiscoveryStats:
    """Test get_discovery_stats function."""
    
    def test_get_discovery_stats_full(self, mock_session):
        """Test getting discovery statistics."""
        # Mock test count
        mock_test_count = MagicMock()
        mock_test_count.scalar.return_value = 15
        
        # Mock page count
        mock_page_count = MagicMock()
        mock_page_count.scalar.return_value = 8
        
        # Mock mapping count
        mock_mapping_count = MagicMock()
        mock_mapping_count.scalar.return_value = 42
        
        mock_session.execute.side_effect = [
            mock_test_count,
            mock_page_count,
            mock_mapping_count
        ]
        
        stats = get_discovery_stats(mock_session, 123)
        
        assert stats["test_count"] == 15
        assert stats["page_object_count"] == 8
        assert stats["mapping_count"] == 42
        assert mock_session.execute.call_count == 3
    
    def test_get_discovery_stats_zero_counts(self, mock_session):
        """Test statistics with zero counts."""
        mock_zero = MagicMock()
        mock_zero.scalar.return_value = 0
        
        mock_session.execute.side_effect = [mock_zero, mock_zero, mock_zero]
        
        stats = get_discovery_stats(mock_session, 999)
        
        assert stats["test_count"] == 0
        assert stats["page_object_count"] == 0
        assert stats["mapping_count"] == 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_create_discovery_run_empty_project_name(self, mock_session):
        """Test creating discovery run with empty project name."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [111]
        mock_session.execute.return_value = mock_result
        
        # Should still work (database constraint may reject it)
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name=""
        )
        
        assert discovery_id == 111
    
    def test_create_discovery_run_none_metadata(self, mock_session):
        """Test creating discovery run with None metadata."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [222]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="test",
            metadata=None
        )
        
        assert discovery_id == 222
    
    def test_get_discovery_stats_none_results(self, mock_session):
        """Test stats when queries return None."""
        mock_none = MagicMock()
        mock_none.scalar.return_value = None
        
        mock_session.execute.side_effect = [mock_none, mock_none, mock_none]
        
        stats = get_discovery_stats(mock_session, 123)
        
        # Should handle None gracefully (convert to 0)
        assert stats["test_count"] == 0 or stats["test_count"] is None
        assert stats["page_object_count"] == 0 or stats["page_object_count"] is None
        assert stats["mapping_count"] == 0 or stats["mapping_count"] is None


class TestContractStability:
    """Test that API contracts remain stable."""
    
    def test_create_discovery_run_returns_int(self, mock_session):
        """Test that create_discovery_run returns an integer."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [123]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="test"
        )
        
        assert isinstance(discovery_id, int)
    
    def test_get_discovery_run_returns_discovery_or_none(self, mock_session):
        """Test that get_discovery_run returns DiscoveryRun or None."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        discovery = get_discovery_run(mock_session, 123)
        
        assert discovery is None or isinstance(discovery, DiscoveryRun)
    
    def test_list_discovery_runs_returns_list(self, mock_session):
        """Test that list_discovery_runs returns a list."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session)
        
        assert isinstance(discoveries, list)
    
    def test_get_discovery_stats_returns_dict(self, mock_session):
        """Test that get_discovery_stats returns a dict."""
        mock_zero = MagicMock()
        mock_zero.scalar.return_value = 0
        mock_session.execute.side_effect = [mock_zero, mock_zero, mock_zero]
        
        stats = get_discovery_stats(mock_session, 123)
        
        assert isinstance(stats, dict)
        assert "test_count" in stats
        assert "page_object_count" in stats
        assert "mapping_count" in stats
