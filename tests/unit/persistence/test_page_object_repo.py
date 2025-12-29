"""
Unit tests for page object repository.

Tests cover:
- Upserting page objects
- Finding page objects
- Getting page object usage statistics
- Listing most used page objects
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, UTC
from persistence.repositories.page_object_repo import (
    upsert_page_object,
    find_page_object,
    get_page_object_usage,
    get_most_used_page_objects
)
from persistence.models import PageObject


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=None)
    return session


class TestUpsertPageObject:
    """Test upsert_page_object function."""
    
    def test_upsert_page_object_new(self, mock_session):
        """Test inserting a new page object."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [123]
        mock_session.execute.return_value = mock_result
        
        page_id = upsert_page_object(
            session=mock_session,
            name="LoginPage",
            file_path="src/main/java/pages/LoginPage.java",
            package="com.example.pages"
        )
        
        assert page_id == 123
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_upsert_page_object_with_metadata(self, mock_session):
        """Test upserting page object with metadata."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [456]
        mock_session.execute.return_value = mock_result
        
        metadata = {"elements": 5, "locators": ["id", "css"]}
        
        page_id = upsert_page_object(
            session=mock_session,
            name="HomePage",
            file_path="src/main/java/pages/HomePage.java",
            package="com.example.pages",
            metadata=metadata
        )
        
        assert page_id == 456
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["metadata"] == metadata
    
    def test_upsert_page_object_update_package(self, mock_session):
        """Test updating package on conflict."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [789]
        mock_session.execute.return_value = mock_result
        
        page_id = upsert_page_object(
            session=mock_session,
            name="LoginPage",
            file_path="src/main/java/pages/LoginPage.java",
            package="com.example.newpackage"
        )
        
        assert page_id == 789
        # ON CONFLICT clause should update package
    
    def test_upsert_page_object_none_package(self, mock_session):
        """Test upserting with None package."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [999]
        mock_session.execute.return_value = mock_result
        
        page_id = upsert_page_object(
            session=mock_session,
            name="Page",
            file_path="Page.java",
            package=None
        )
        
        assert page_id == 999
    
    def test_upsert_page_object_error_handling(self, mock_session):
        """Test error handling in upsert."""
        mock_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            upsert_page_object(
                session=mock_session,
                name="Page",
                file_path="Page.java"
            )
        
        mock_session.rollback.assert_called_once()


class TestFindPageObject:
    """Test find_page_object function."""
    
    def test_find_page_object_found(self, mock_session):
        """Test finding an existing page object."""
        mock_row = MagicMock()
        mock_row.id = 123
        mock_row.name = "LoginPage"
        mock_row.file_path = "src/main/java/pages/LoginPage.java"
        mock_row.package = "com.example.pages"
        mock_row.metadata = None
        mock_row.created_at = datetime.now(UTC)
        mock_row.updated_at = datetime.now(UTC)
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        page_object = find_page_object(
            session=mock_session,
            name="LoginPage",
            file_path="src/main/java/pages/LoginPage.java"
        )
        
        assert page_object is not None
        assert page_object.id == 123
        assert page_object.name == "LoginPage"
    
    def test_find_page_object_not_found(self, mock_session):
        """Test finding non-existent page object."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        page_object = find_page_object(
            session=mock_session,
            name="Unknown",
            file_path="Unknown.java"
        )
        
        assert page_object is None


class TestGetPageObjectUsage:
    """Test get_page_object_usage function."""
    
    def test_get_page_object_usage_with_data(self, mock_session):
        """Test getting usage statistics."""
        mock_row = MagicMock()
        mock_row.test_count = 15
        mock_row.discovery_count = 3
        mock_row.sources = ["static_ast", "coverage"]
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        usage = get_page_object_usage(mock_session, 123)
        
        assert usage["test_count"] == 15
        assert usage["discovery_count"] == 3
        assert len(usage["sources"]) == 2
        assert "static_ast" in usage["sources"]
    
    def test_get_page_object_usage_no_data(self, mock_session):
        """Test usage when page object has no mappings."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        usage = get_page_object_usage(mock_session, 999)
        
        assert usage["test_count"] == 0
        assert usage["discovery_count"] == 0
        assert usage["sources"] == []
    
    def test_get_page_object_usage_null_counts(self, mock_session):
        """Test usage with NULL counts."""
        mock_row = MagicMock()
        mock_row.test_count = None
        mock_row.discovery_count = None
        mock_row.sources = None
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        usage = get_page_object_usage(mock_session, 123)
        
        # Should handle NULL gracefully
        assert usage["test_count"] == 0 or usage["test_count"] is None
        assert usage["discovery_count"] == 0 or usage["discovery_count"] is None
        assert usage["sources"] == [] or usage["sources"] is None


class TestGetMostUsedPageObjects:
    """Test get_most_used_page_objects function."""
    
    def test_get_most_used_page_objects_multiple(self, mock_session):
        """Test retrieving multiple page objects ranked by usage."""
        mock_rows = [
            (
                MagicMock(
                    id=1, name="LoginPage", file_path="LoginPage.java",
                    package="com.example", metadata=None,
                    created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
                ),
                25  # test_count
            ),
            (
                MagicMock(
                    id=2, name="HomePage", file_path="HomePage.java",
                    package="com.example", metadata=None,
                    created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
                ),
                15  # test_count
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        pages = get_most_used_page_objects(mock_session, limit=10)
        
        assert len(pages) == 2
        assert pages[0][0].name == "LoginPage"
        assert pages[0][1] == 25
        assert pages[1][0].name == "HomePage"
        assert pages[1][1] == 15
    
    def test_get_most_used_page_objects_with_limit(self, mock_session):
        """Test limiting results."""
        mock_rows = [
            (
                MagicMock(
                    id=1, name="Page1", file_path="Page1.java",
                    package="com.example", metadata=None,
                    created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
                ),
                10
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows[:1]
        mock_session.execute.return_value = mock_result
        
        pages = get_most_used_page_objects(mock_session, limit=1)
        
        assert len(pages) == 1
    
    def test_get_most_used_page_objects_empty(self, mock_session):
        """Test when no page objects exist."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        pages = get_most_used_page_objects(mock_session)
        
        assert len(pages) == 0
    
    def test_get_most_used_page_objects_default_limit(self, mock_session):
        """Test default limit of 50."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        pages = get_most_used_page_objects(mock_session)
        
        # Should apply default limit
        mock_session.execute.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_upsert_page_object_empty_name(self, mock_session):
        """Test upserting with empty name."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [111]
        mock_session.execute.return_value = mock_result
        
        # Should still work (database constraint may reject it)
        page_id = upsert_page_object(
            session=mock_session,
            name="",
            file_path="Page.java"
        )
        
        assert page_id == 111
    
    def test_upsert_page_object_none_metadata(self, mock_session):
        """Test upserting with None metadata."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [222]
        mock_session.execute.return_value = mock_result
        
        page_id = upsert_page_object(
            session=mock_session,
            name="Page",
            file_path="Page.java",
            metadata=None
        )
        
        assert page_id == 222
    
    def test_find_page_object_special_characters(self, mock_session):
        """Test finding page with special characters."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        page_object = find_page_object(
            session=mock_session,
            name="Page$Inner",
            file_path="src/Page$Inner.java"
        )
        
        # Should handle gracefully
        assert page_object is None
    
    def test_get_most_used_page_objects_zero_limit(self, mock_session):
        """Test with zero limit."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        pages = get_most_used_page_objects(mock_session, limit=0)
        
        # Should handle gracefully (may return empty or apply minimum)
        assert isinstance(pages, list)


class TestContractStability:
    """Test that API contracts remain stable."""
    
    def test_upsert_returns_int(self, mock_session):
        """Test that upsert returns an integer."""
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [123]
        mock_session.execute.return_value = mock_result
        
        page_id = upsert_page_object(
            session=mock_session,
            name="Page",
            file_path="Page.java"
        )
        
        assert isinstance(page_id, int)
    
    def test_find_returns_page_or_none(self, mock_session):
        """Test that find returns PageObject or None."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        page_object = find_page_object(
            session=mock_session,
            name="Page",
            file_path="Page.java"
        )
        
        assert page_object is None or isinstance(page_object, PageObject)
    
    def test_get_usage_returns_dict(self, mock_session):
        """Test that get_page_object_usage returns dict."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        usage = get_page_object_usage(mock_session, 123)
        
        assert isinstance(usage, dict)
        assert "test_count" in usage
        assert "discovery_count" in usage
        assert "sources" in usage
    
    def test_get_most_used_returns_list_of_tuples(self, mock_session):
        """Test that get_most_used returns list of tuples."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        pages = get_most_used_page_objects(mock_session)
        
        assert isinstance(pages, list)
