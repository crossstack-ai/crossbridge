"""
Unit tests for test case repository.

Tests cover:
- Upserting test cases
- Finding test cases
- Linking tests to discoveries
- Retrieving tests in discoveries
"""

import pytest
import uuid
from unittest.mock import MagicMock
from datetime import datetime, UTC
from persistence.repositories.test_case_repo import (
    upsert_test_case,
    find_test_case,
    get_tests_in_discovery,
    link_test_to_discovery
)
from persistence.models import TestCase


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=None)
    return session


class TestUpsertTestCase:
    """Test upsert_test_case function."""
    
    def test_upsert_test_case_new(self, mock_session):
        """Test inserting a new test case."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        test_id = upsert_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="LoginTest",
            method_name="testValidLogin",
            file_path="src/test/java/com/example/LoginTest.java"
        )
        
        assert test_id == 123
        mock_session.execute.assert_called_once()
    
    def test_upsert_test_case_with_tags(self, mock_session):
        """Test upserting test case with tags."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        test_id = upsert_test_case(
            session=mock_session,
            framework="testng",
            package="com.example",
            class_name="CartTest",
            method_name="testAddToCart",
            file_path="src/test/java/com/example/CartTest.java",
            tags=["smoke", "critical"]
        )
        
        assert test_id == 456
        
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["tags"] == ["smoke", "critical"]
    
    def test_upsert_test_case_update_file_path(self, mock_session):
        """Test updating file path on conflict."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        test_id = upsert_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="LoginTest",
            method_name="testLogin",
            file_path="src/test/java/com/example/auth/LoginTest.java"
        )
        
        assert test_id == 789
        # ON CONFLICT clause should update file_path
    
    def test_upsert_test_case_empty_tags(self, mock_session):
        """Test upserting with empty tags list."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        test_id = upsert_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="Test",
            method_name="testMethod",
            file_path="Test.java",
            tags=[]
        )
        
        assert test_id == 999
    
    def test_upsert_test_case_error_handling(self, mock_session):
        """Test error handling in upsert."""
        mock_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            upsert_test_case(
                session=mock_session,
                framework="junit5",
                package="com.example",
                class_name="Test",
                method_name="testMethod",
                file_path="Test.java"
            )
        
        mock_session.rollback.assert_called_once()


class TestFindTestCase:
    """Test find_test_case function."""
    
    def test_find_test_case_found(self, mock_session):
        """Test finding an existing test case."""
        mock_row = MagicMock()
        mock_row.id = 123
        mock_row.framework = "junit5"
        mock_row.package = "com.example"
        mock_row.class_name = "LoginTest"
        mock_row.method_name = "testLogin"
        mock_row.file_path = "src/test/LoginTest.java"
        mock_row.tags = ["smoke"]
        mock_row.created_at = datetime.now(UTC)
        mock_row.updated_at = datetime.now(UTC)
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        test_case = find_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="LoginTest",
            method_name="testLogin"
        )
        
        assert test_case is not None
        assert test_case.id == 123
        assert test_case.full_name == "LoginTest.testLogin"
    
    def test_find_test_case_not_found(self, mock_session):
        """Test finding non-existent test case."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        test_case = find_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="Unknown",
            method_name="testUnknown"
        )
        
        assert test_case is None


class TestLinkTestToDiscovery:
    """Test link_test_to_discovery function."""
    
    def test_link_test_to_discovery_success(self, mock_session):
        """Test linking test to discovery."""
        link_test_to_discovery(
            session=mock_session,
            test_id=123,
            discovery_run_id=456
        )
        
        mock_session.execute.assert_called_once()
        
        # Verify the INSERT statement
        call_args = mock_session.execute.call_args
        values = call_args[0][0].compile().params
        assert values["test_case_id"] == 123
        assert values["discovery_run_id"] == 456
    
    def test_link_test_to_discovery_duplicate(self, mock_session):
        """Test linking same test twice (should be idempotent)."""
        # First link
        link_test_to_discovery(
            session=mock_session,
            test_id=123,
            discovery_run_id=456
        )
        
        # Second link (ON CONFLICT DO NOTHING)
        link_test_to_discovery(
            session=mock_session,
            test_id=123,
            discovery_run_id=456
        )
        
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 2
    
    def test_link_test_to_discovery_error_handling(self, mock_session):
        """Test error handling in link."""
        mock_session.execute.side_effect = Exception("Link failed")
        
        with pytest.raises(Exception, match="Link failed"):
            link_test_to_discovery(
                session=mock_session,
                test_id=123,
                discovery_run_id=456
            )
        
        mock_session.rollback.assert_called_once()


class TestGetTestsInDiscovery:
    """Test get_tests_in_discovery function."""
    
    def test_get_tests_in_discovery_multiple(self, mock_session):
        """Test retrieving multiple tests in a discovery."""
        mock_rows = [
            MagicMock(
                id=1, framework="junit5", package="com.example",
                class_name="Test1", method_name="test1",
                file_path="Test1.java", tags=["smoke"],
                created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
            ),
            MagicMock(
                id=2, framework="testng", package="com.example",
                class_name="Test2", method_name="test2",
                file_path="Test2.java", tags=[],
                created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        tests = get_tests_in_discovery(mock_session, 456)
        
        assert len(tests) == 2
        assert tests[0].id == 1
        assert tests[1].id == 2
        assert tests[0].framework == "junit5"
        assert tests[1].framework == "testng"
    
    def test_get_tests_in_discovery_empty(self, mock_session):
        """Test retrieving tests when discovery has none."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        tests = get_tests_in_discovery(mock_session, 999)
        
        assert len(tests) == 0
    
    def test_get_tests_in_discovery_with_tags(self, mock_session):
        """Test that tags are properly retrieved."""
        mock_rows = [
            MagicMock(
                id=1, framework="junit5", package="com.example",
                class_name="Test", method_name="test",
                file_path="Test.java", tags=["smoke", "critical", "regression"],
                created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        tests = get_tests_in_discovery(mock_session, 123)
        
        assert len(tests) == 1
        assert len(tests[0].tags) == 3
        assert "smoke" in tests[0].tags


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_upsert_test_case_none_tags(self, mock_session):
        """Test upserting with None tags."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        test_id = upsert_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="Test",
            method_name="test",
            file_path="Test.java",
            tags=None
        )
        
        assert test_id == 111
    
    def test_upsert_test_case_empty_package(self, mock_session):
        """Test upserting with empty package."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        test_id = upsert_test_case(
            session=mock_session,
            framework="junit5",
            package="",
            class_name="Test",
            method_name="test",
            file_path="Test.java"
        )
        
        assert test_id == 222
    
    def test_find_test_case_special_characters(self, mock_session):
        """Test finding test with special characters."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        test_case = find_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="Test$Inner",
            method_name="test_with_underscores"
        )
        
        # Should handle gracefully
        assert test_case is None
    
    def test_get_tests_in_discovery_none_tags(self, mock_session):
        """Test retrieving tests with None tags."""
        mock_rows = [
            MagicMock(
                id=1, framework="junit5", package="com.example",
                class_name="Test", method_name="test",
                file_path="Test.java", tags=None,
                created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
            )
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        tests = get_tests_in_discovery(mock_session, 123)
        
        assert len(tests) == 1
        # Should handle None tags gracefully
        assert tests[0].tags is None or tests[0].tags == []


class TestContractStability:
    """Test that API contracts remain stable."""
    
    def test_upsert_returns_uuid(self, mock_session):
        """Test that upsert_test_case returns UUID type."""
        """Test that upsert returns a UUID."""
        test_uuid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.inserted_primary_key = [test_uuid]
        mock_session.execute.return_value = mock_result
        
        test_id = upsert_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="Test",
            method_name="test",
            file_path="Test.java"
        )
        
        assert isinstance(test_id, uuid.UUID)
    
    def test_find_returns_test_or_none(self, mock_session):
        """Test that find returns TestCase or None."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        test_case = find_test_case(
            session=mock_session,
            framework="junit5",
            package="com.example",
            class_name="Test",
            method_name="test"
        )
        
        assert test_case is None or isinstance(test_case, TestCase)
    
    def test_get_tests_returns_list(self, mock_session):
        """Test that get_tests_in_discovery returns list."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        tests = get_tests_in_discovery(mock_session, 123)
        
        assert isinstance(tests, list)
    
    def test_link_returns_none(self, mock_session):
        """Test that link_test_to_discovery returns None."""
        result = link_test_to_discovery(
            session=mock_session,
            test_id=123,
            discovery_run_id=456
        )
        
        assert result is None
