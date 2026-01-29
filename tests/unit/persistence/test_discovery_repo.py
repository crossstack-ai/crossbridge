"""
Unit tests for discovery repository.

Tests cover:
- Creating discovery runs
- Retrieving discovery runs
- Listing discoveries
- Discovery statistics
"""

import pytest
import uuid
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
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="test-project"
        )
        
        assert isinstance(discovery_id, uuid.UUID)
        mock_session.execute.assert_called_once()
        
        # Check the SQL values
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["project"] == "test-project"
        assert values["triggered_by"] == "cli"
    
    def test_create_discovery_run_with_git_context(self, mock_session):
        """Test creating discovery run with git context."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="my-project",
            git_commit="abc123",
            git_branch="main"
        )
        
        assert isinstance(discovery_id, uuid.UUID)
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["commit"] == "abc123"
        assert values["branch"] == "main"
    
    def test_create_discovery_run_with_metadata(self, mock_session):
        """Test creating discovery run with metadata."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        metadata = {"scan_duration_ms": 1234, "total_files": 10}
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="my-project",
            metadata=metadata
        )
        
        assert isinstance(discovery_id, uuid.UUID)
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["metadata"] == metadata
    
    def test_create_discovery_run_with_triggered_by(self, mock_session):
        """Test creating discovery run with custom triggered_by."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="my-project",
            triggered_by="ci"
        )
        
        assert isinstance(discovery_id, uuid.UUID)
        
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
        test_uuid = uuid.uuid4()
        test_time = datetime.now(UTC)
        # Mock row as tuple matching SQL SELECT order: id, project_name, git_commit, git_branch, triggered_by, created_at, metadata
        mock_row = (test_uuid, "test-project", "abc123", "main", "cli", test_time, {"key": "value"})
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        discovery = get_discovery_run(mock_session, test_uuid)
        
        assert discovery is not None
        assert discovery.id == test_uuid
        assert discovery.project_name == "test-project"
        assert discovery.git_commit == "abc123"
    
    def test_get_discovery_run_not_found(self, mock_session):
        """Test retrieving non-existent discovery run."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        discovery = get_discovery_run(mock_session, uuid.uuid4())
        
        assert discovery is None


class TestGetLatestDiscoveryRun:
    """Test get_latest_discovery_run function."""
    
    def test_get_latest_discovery_run_found(self, mock_session):
        """Test retrieving latest discovery run."""
        test_uuid = uuid.uuid4()
        created_at = datetime.now(UTC)
        # Tuple: (id, project_name, git_commit, git_branch, triggered_by, created_at, metadata)
        mock_row = (test_uuid, "my-project", None, None, "ci", created_at, None)
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        discovery = get_latest_discovery_run(mock_session, "my-project")
        
        assert discovery is not None
        assert discovery.id == test_uuid
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
        test_uuid1 = uuid.uuid4()
        test_uuid2 = uuid.uuid4()
        created_at = datetime.now(UTC)
        # Tuple: (id, project_name, git_commit, git_branch, triggered_by, created_at, metadata)
        mock_rows = [
            (test_uuid1, "proj1", None, None, "cli", created_at, None),
            (test_uuid2, "proj2", "abc", "main", "ci", created_at, None)
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session)
        
        assert len(discoveries) == 2
        assert discoveries[0].id == test_uuid1
        assert discoveries[1].id == test_uuid2
    
    def test_list_discovery_runs_by_project(self, mock_session):
        """Test listing discovery runs for specific project."""
        test_uuid = uuid.uuid4()
        created_at = datetime.now(UTC)
        # Tuple: (id, project_name, git_commit, git_branch, triggered_by, created_at, metadata)
        mock_rows = [
            (test_uuid, "target-project", None, None, "cli", created_at, None)
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session, project_name="target-project")
        
        assert len(discoveries) == 1
        assert discoveries[0].project_name == "target-project"
    
    def test_list_discovery_runs_with_limit(self, mock_session):
        """Test listing discovery runs with limit."""
        created_at = datetime.now(UTC)
        # Tuple: (id, project_name, git_commit, git_branch, triggered_by, created_at, metadata)
        mock_rows = [
            (uuid.uuid4(), f"proj{i}", None, None, "cli", created_at, None)
            for i in range(3)
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
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
        # Returns single tuple: (test_count, page_object_count, mapping_count)
        mock_row = (15, 8, 42)
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        stats = get_discovery_stats(mock_session, uuid.uuid4())
        
        assert stats["test_count"] == 15
        assert stats["page_object_count"] == 8
        assert stats["mapping_count"] == 42
    
    def test_get_discovery_stats_zero_counts(self, mock_session):
        """Test statistics with zero counts."""
        # Returns single tuple: (test_count, page_object_count, mapping_count)
        mock_row = (0, 0, 0)
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        stats = get_discovery_stats(mock_session, uuid.uuid4())
        
        assert stats["test_count"] == 0
        assert stats["page_object_count"] == 0
        assert stats["mapping_count"] == 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_create_discovery_run_empty_project_name(self, mock_session):
        """Test creating discovery run with empty project name."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        # Should still work (database constraint may reject it)
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name=""
        )
        
        assert isinstance(discovery_id, uuid.UUID)
    
    def test_create_discovery_run_none_metadata(self, mock_session):
        """Test creating discovery run with None metadata."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="test",
            metadata=None
        )
        
        assert isinstance(discovery_id, uuid.UUID)
    
    def test_get_discovery_stats_none_results(self, mock_session):
        """Test stats when queries return None."""
        # Returns None when no discovery run found
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        stats = get_discovery_stats(mock_session, uuid.uuid4())
        
        # Should handle None gracefully (convert to 0)
        assert stats["test_count"] == 0
        assert stats["page_object_count"] == 0
        assert stats["mapping_count"] == 0


class TestContractStability:
    """Test that API contracts remain stable."""
    
    def test_create_discovery_run_returns_uuid(self, mock_session):
        """Test that create_discovery_run returns a UUID."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        discovery_id = create_discovery_run(
            session=mock_session,
            project_name="test"
        )
        
        assert isinstance(discovery_id, uuid.UUID)
    
    def test_get_discovery_run_returns_discovery_or_none(self, mock_session):
        """Test that get_discovery_run returns DiscoveryRun or None."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        test_uuid = uuid.uuid4()
        discovery = get_discovery_run(mock_session, test_uuid)
        
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
