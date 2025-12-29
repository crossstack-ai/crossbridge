"""
Unit tests for persistence orchestrator.

Tests cover:
- persist_discovery workflow
- Git context capture
- Discovery statistics
- Discovery comparison
- Error handling
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
from persistence.orchestrator import (
    persist_discovery,
    get_latest_discovery_stats,
    compare_discoveries,
    get_git_commit,
    get_git_branch
)
from adapters.common.models import TestMetadata, PageObjectReference


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=None)
    return session


@pytest.fixture
def sample_tests():
    """Create sample test metadata."""
    return [
        TestMetadata(
            test_name="com.example.LoginTest.testValidLogin",
            file_path="src/test/java/com/example/LoginTest.java",
            tags=["smoke", "critical"],
            page_objects=[
                PageObjectReference(name="LoginPage", package="com.example.pages")
            ]
        ),
        TestMetadata(
            test_name="com.example.CartTest.testAddToCart",
            file_path="src/test/java/com/example/CartTest.java",
            tags=["regression"],
            page_objects=[
                PageObjectReference(name="CartPage", package="com.example.pages"),
                PageObjectReference(name="ProductPage", package="com.example.pages")
            ]
        )
    ]


class TestPersistDiscovery:
    """Test persist_discovery function."""
    
    @patch('persistence.orchestrator.create_discovery_run')
    @patch('persistence.orchestrator.upsert_test_case')
    @patch('persistence.orchestrator.link_test_to_discovery')
    @patch('persistence.orchestrator.upsert_page_object')
    @patch('persistence.orchestrator.insert_mapping')
    @patch('persistence.orchestrator.get_git_commit')
    @patch('persistence.orchestrator.get_git_branch')
    def test_persist_discovery_full_workflow(
        self, mock_git_branch, mock_git_commit, mock_insert_mapping,
        mock_upsert_page, mock_link_test, mock_upsert_test,
        mock_create_discovery, mock_session, sample_tests
    ):
        """Test complete persist_discovery workflow."""
        # Setup mocks
        mock_git_commit.return_value = "abc123"
        mock_git_branch.return_value = "main"
        mock_create_discovery.return_value = 100
        mock_upsert_test.side_effect = [1, 2]  # Test IDs
        mock_upsert_page.side_effect = [10, 20, 30]  # Page IDs
        mock_insert_mapping.side_effect = [101, 102, 103]  # Mapping IDs
        
        discovery_id = persist_discovery(
            session=mock_session,
            project_name="test-project",
            tests=sample_tests,
            framework_hint="junit5"
        )
        
        # Verify discovery run created
        assert discovery_id == 100
        mock_create_discovery.assert_called_once_with(
            session=mock_session,
            project_name="test-project",
            git_commit="abc123",
            git_branch="main",
            triggered_by="cli",
            metadata={"framework_hint": "junit5"}
        )
        
        # Verify tests upserted (2 tests)
        assert mock_upsert_test.call_count == 2
        
        # Verify tests linked to discovery (2 links)
        assert mock_link_test.call_count == 2
        
        # Verify page objects upserted (3 unique pages)
        assert mock_upsert_page.call_count == 3
        
        # Verify mappings inserted (1 + 2 = 3 mappings)
        assert mock_insert_mapping.call_count == 3
    
    @patch('persistence.orchestrator.create_discovery_run')
    @patch('persistence.orchestrator.get_git_commit')
    @patch('persistence.orchestrator.get_git_branch')
    def test_persist_discovery_empty_tests(
        self, mock_git_branch, mock_git_commit, mock_create_discovery,
        mock_session
    ):
        """Test persisting with empty test list."""
        mock_git_commit.return_value = None
        mock_git_branch.return_value = None
        mock_create_discovery.return_value = 200
        
        discovery_id = persist_discovery(
            session=mock_session,
            project_name="empty-project",
            tests=[]
        )
        
        # Should still create discovery run
        assert discovery_id == 200
        mock_create_discovery.assert_called_once()
    
    @patch('persistence.orchestrator.create_discovery_run')
    @patch('persistence.orchestrator.upsert_test_case')
    @patch('persistence.orchestrator.link_test_to_discovery')
    @patch('persistence.orchestrator.get_git_commit')
    @patch('persistence.orchestrator.get_git_branch')
    def test_persist_discovery_tests_without_pages(
        self, mock_git_branch, mock_git_commit, mock_link_test,
        mock_upsert_test, mock_create_discovery, mock_session
    ):
        """Test persisting tests without page objects."""
        mock_git_commit.return_value = None
        mock_git_branch.return_value = None
        mock_create_discovery.return_value = 300
        mock_upsert_test.return_value = 5
        
        tests = [
            TestMetadata(
                test_name="com.example.Test.testMethod",
                file_path="Test.java",
                tags=[],
                page_objects=[]
            )
        ]
        
        discovery_id = persist_discovery(
            session=mock_session,
            project_name="no-pages",
            tests=tests
        )
        
        assert discovery_id == 300
        mock_upsert_test.assert_called_once()
        mock_link_test.assert_called_once()
    
    @patch('persistence.orchestrator.create_discovery_run')
    @patch('persistence.orchestrator.get_git_commit')
    @patch('persistence.orchestrator.get_git_branch')
    def test_persist_discovery_error_handling(
        self, mock_git_branch, mock_git_commit, mock_create_discovery,
        mock_session, sample_tests
    ):
        """Test error handling in persist_discovery."""
        mock_git_commit.return_value = None
        mock_git_branch.return_value = None
        mock_create_discovery.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            persist_discovery(
                session=mock_session,
                project_name="error-project",
                tests=sample_tests
            )
        
        # Should rollback on error
        mock_session.rollback.assert_called()


class TestGetLatestDiscoveryStats:
    """Test get_latest_discovery_stats function."""
    
    @patch('persistence.orchestrator.get_latest_discovery_run')
    @patch('persistence.orchestrator.get_discovery_stats')
    def test_get_latest_discovery_stats_found(
        self, mock_get_stats, mock_get_latest, mock_session
    ):
        """Test getting stats for existing discovery."""
        mock_discovery = MagicMock()
        mock_discovery.id = 100
        mock_get_latest.return_value = mock_discovery
        
        mock_get_stats.return_value = {
            "test_count": 50,
            "page_object_count": 15,
            "mapping_count": 120
        }
        
        stats = get_latest_discovery_stats(mock_session, "test-project")
        
        assert stats is not None
        assert stats["discovery_id"] == 100
        assert stats["test_count"] == 50
        assert stats["page_object_count"] == 15
        mock_get_latest.assert_called_once_with(mock_session, "test-project")
        mock_get_stats.assert_called_once_with(mock_session, 100)
    
    @patch('persistence.orchestrator.get_latest_discovery_run')
    def test_get_latest_discovery_stats_not_found(
        self, mock_get_latest, mock_session
    ):
        """Test when no discovery exists."""
        mock_get_latest.return_value = None
        
        stats = get_latest_discovery_stats(mock_session, "unknown-project")
        
        assert stats is None


class TestCompareDiscoveries:
    """Test compare_discoveries function."""
    
    @patch('persistence.orchestrator.get_discovery_stats')
    def test_compare_discoveries_full(self, mock_get_stats, mock_session):
        """Test comparing two discoveries."""
        # Mock stats for old and new discoveries
        mock_get_stats.side_effect = [
            {
                "test_count": 40,
                "page_object_count": 10,
                "mapping_count": 80
            },
            {
                "test_count": 50,
                "page_object_count": 15,
                "mapping_count": 120
            }
        ]
        
        comparison = compare_discoveries(mock_session, 100, 200)
        
        assert comparison["old_discovery_id"] == 100
        assert comparison["new_discovery_id"] == 200
        assert comparison["test_count_diff"] == 10
        assert comparison["page_object_count_diff"] == 5
        assert comparison["mapping_count_diff"] == 40
        assert mock_get_stats.call_count == 2
    
    @patch('persistence.orchestrator.get_discovery_stats')
    def test_compare_discoveries_negative_diff(self, mock_get_stats, mock_session):
        """Test comparison with decreased counts."""
        mock_get_stats.side_effect = [
            {
                "test_count": 50,
                "page_object_count": 15,
                "mapping_count": 120
            },
            {
                "test_count": 40,
                "page_object_count": 10,
                "mapping_count": 80
            }
        ]
        
        comparison = compare_discoveries(mock_session, 200, 100)
        
        assert comparison["test_count_diff"] == -10
        assert comparison["page_object_count_diff"] == -5
        assert comparison["mapping_count_diff"] == -40


class TestGetGitCommit:
    """Test get_git_commit function."""
    
    @patch('subprocess.run')
    def test_get_git_commit_success(self, mock_run):
        """Test getting git commit successfully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123def456\n"
        )
        
        commit = get_git_commit()
        
        assert commit == "abc123def456"
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_git_commit_not_a_repo(self, mock_run):
        """Test when not in a git repository."""
        mock_run.side_effect = Exception("not a git repository")
        
        commit = get_git_commit()
        
        assert commit is None
    
    @patch('subprocess.run')
    def test_get_git_commit_no_commits(self, mock_run):
        """Test when repository has no commits."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout=""
        )
        
        commit = get_git_commit()
        
        assert commit is None


class TestGetGitBranch:
    """Test get_git_branch function."""
    
    @patch('subprocess.run')
    def test_get_git_branch_success(self, mock_run):
        """Test getting git branch successfully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="main\n"
        )
        
        branch = get_git_branch()
        
        assert branch == "main"
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_git_branch_detached_head(self, mock_run):
        """Test when in detached HEAD state."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="HEAD detached at abc123\n"
        )
        
        branch = get_git_branch()
        
        # Should still return the output
        assert "HEAD" in branch or branch is None
    
    @patch('subprocess.run')
    def test_get_git_branch_not_a_repo(self, mock_run):
        """Test when not in a git repository."""
        mock_run.side_effect = Exception("not a git repository")
        
        branch = get_git_branch()
        
        assert branch is None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('persistence.orchestrator.create_discovery_run')
    @patch('persistence.orchestrator.upsert_test_case')
    @patch('persistence.orchestrator.link_test_to_discovery')
    @patch('persistence.orchestrator.get_git_commit')
    @patch('persistence.orchestrator.get_git_branch')
    def test_persist_discovery_with_duplicate_page_objects(
        self, mock_git_branch, mock_git_commit, mock_link_test,
        mock_upsert_test, mock_create_discovery, mock_session
    ):
        """Test persisting tests with duplicate page objects."""
        mock_git_commit.return_value = None
        mock_git_branch.return_value = None
        mock_create_discovery.return_value = 400
        mock_upsert_test.return_value = 6
        
        tests = [
            TestMetadata(
                test_name="com.example.Test.test1",
                file_path="Test.java",
                tags=[],
                page_objects=[
                    PageObjectReference(name="Page1", package="com.example"),
                    PageObjectReference(name="Page1", package="com.example")  # Duplicate
                ]
            )
        ]
        
        # Should handle duplicates gracefully
        discovery_id = persist_discovery(
            session=mock_session,
            project_name="dup-pages",
            tests=tests
        )
        
        assert discovery_id == 400
    
    @patch('persistence.orchestrator.create_discovery_run')
    @patch('persistence.orchestrator.get_git_commit')
    @patch('persistence.orchestrator.get_git_branch')
    def test_persist_discovery_none_framework_hint(
        self, mock_git_branch, mock_git_commit, mock_create_discovery,
        mock_session
    ):
        """Test persisting without framework hint."""
        mock_git_commit.return_value = None
        mock_git_branch.return_value = None
        mock_create_discovery.return_value = 500
        
        discovery_id = persist_discovery(
            session=mock_session,
            project_name="no-hint",
            tests=[],
            framework_hint=None
        )
        
        assert discovery_id == 500
        
        # Should not include framework_hint in metadata
        call_args = mock_create_discovery.call_args
        metadata = call_args[1].get("metadata")
        assert metadata is None or "framework_hint" not in metadata


class TestContractStability:
    """Test that API contracts remain stable."""
    
    @patch('persistence.orchestrator.create_discovery_run')
    @patch('persistence.orchestrator.get_git_commit')
    @patch('persistence.orchestrator.get_git_branch')
    def test_persist_discovery_returns_int(
        self, mock_git_branch, mock_git_commit, mock_create_discovery,
        mock_session
    ):
        """Test that persist_discovery returns an integer."""
        mock_git_commit.return_value = None
        mock_git_branch.return_value = None
        mock_create_discovery.return_value = 123
        
        discovery_id = persist_discovery(
            session=mock_session,
            project_name="test",
            tests=[]
        )
        
        assert isinstance(discovery_id, int)
    
    @patch('persistence.orchestrator.get_latest_discovery_run')
    def test_get_latest_stats_returns_dict_or_none(
        self, mock_get_latest, mock_session
    ):
        """Test that get_latest_discovery_stats returns dict or None."""
        mock_get_latest.return_value = None
        
        stats = get_latest_discovery_stats(mock_session, "test")
        
        assert stats is None or isinstance(stats, dict)
    
    @patch('persistence.orchestrator.get_discovery_stats')
    def test_compare_returns_dict(self, mock_get_stats, mock_session):
        """Test that compare_discoveries returns dict."""
        mock_get_stats.side_effect = [
            {"test_count": 10, "page_object_count": 5, "mapping_count": 20},
            {"test_count": 15, "page_object_count": 8, "mapping_count": 30}
        ]
        
        comparison = compare_discoveries(mock_session, 1, 2)
        
        assert isinstance(comparison, dict)
        assert "old_discovery_id" in comparison
        assert "new_discovery_id" in comparison
        assert "test_count_diff" in comparison
    
    def test_get_git_commit_returns_string_or_none(self):
        """Test that get_git_commit returns string or None."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="abc\n")
            commit = get_git_commit()
            
            assert commit is None or isinstance(commit, str)
    
    def test_get_git_branch_returns_string_or_none(self):
        """Test that get_git_branch returns string or None."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
            branch = get_git_branch()
            
            assert branch is None or isinstance(branch, str)
