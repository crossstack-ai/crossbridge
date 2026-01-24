"""
Unit tests for Memory models.
"""

import pytest
from datetime import datetime
from core.memory.models import (
    MemoryRecord,
    MemoryType,
    SearchResult,
    test_to_text,
    scenario_to_text,
    step_to_text,
    page_to_text,
    failure_to_text,
)


class TestMemoryRecord:
    """Tests for MemoryRecord model."""

    def test_create_valid_record(self):
        """Test creating a valid memory record."""
        record = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test for login functionality",
            metadata={"framework": "pytest"},
        )

        assert record.id == "test_1"
        assert record.type == MemoryType.TEST
        assert record.text == "Test for login functionality"
        assert record.metadata["framework"] == "pytest"
        assert record.embedding is None

    def test_create_record_with_string_type(self):
        """Test creating record with string type (auto-converted)."""
        record = MemoryRecord(
            id="test_1",
            type="test",
            text="Test content",
            metadata={},
        )

        assert record.type == MemoryType.TEST

    def test_create_record_empty_id_fails(self):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            MemoryRecord(
                id="",
                type=MemoryType.TEST,
                text="Test content",
                metadata={},
            )

    def test_create_record_empty_text_fails(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            MemoryRecord(
                id="test_1",
                type=MemoryType.TEST,
                text="",
                metadata={},
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        record = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test content",
            metadata={"framework": "pytest"},
            embedding=[0.1, 0.2, 0.3],
        )

        data = record.to_dict()

        assert data["id"] == "test_1"
        assert data["type"] == "test"
        assert data["text"] == "Test content"
        assert data["metadata"]["framework"] == "pytest"
        assert data["embedding"] == [0.1, 0.2, 0.3]
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "id": "test_1",
            "type": "test",
            "text": "Test content",
            "metadata": {"framework": "pytest"},
            "embedding": [0.1, 0.2, 0.3],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        record = MemoryRecord.from_dict(data)

        assert record.id == "test_1"
        assert record.type == MemoryType.TEST
        assert record.text == "Test content"
        assert record.embedding == [0.1, 0.2, 0.3]


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self):
        """Test creating a search result."""
        record = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test content",
            metadata={},
        )

        result = SearchResult(record=record, score=0.85, rank=1)

        assert result.record == record
        assert result.score == 0.85
        assert result.rank == 1

    def test_search_result_to_dict(self):
        """Test search result conversion to dictionary."""
        record = MemoryRecord(
            id="test_1",
            type=MemoryType.TEST,
            text="Test content",
            metadata={"framework": "pytest"},
        )

        result = SearchResult(record=record, score=0.85, rank=1)
        data = result.to_dict()

        assert data["id"] == "test_1"
        assert data["type"] == "test"
        assert data["text"] == "Test content"
        assert data["score"] == 0.85
        assert data["rank"] == 1
        assert data["metadata"]["framework"] == "pytest"


class TestTextConstruction:
    """Tests for text construction helpers."""

    def test_test_to_text(self):
        """Test converting test data to text."""
        test_data = {
            "name": "test_login_valid",
            "framework": "pytest",
            "steps": ["open_browser", "navigate", "login"],
            "intent": "Verify successful login",
            "description": "Test valid login flow",
            "tags": ["auth", "smoke"],
        }

        text = test_to_text(test_data)

        assert "Test Name: test_login_valid" in text
        assert "Framework: pytest" in text
        assert "open_browser, navigate, login" in text
        assert "Purpose: Verify successful login" in text
        assert "Description: Test valid login flow" in text
        assert "Tags: auth, smoke" in text

    def test_scenario_to_text(self):
        """Test converting scenario data to text."""
        scenario_data = {
            "name": "User logs in successfully",
            "feature": "Authentication",
            "steps": [
                "Given user is on login page",
                "When user enters valid credentials",
                "Then user is redirected to dashboard",
            ],
            "tags": ["smoke", "auth"],
        }

        text = scenario_to_text(scenario_data)

        assert "Scenario: User logs in successfully" in text
        assert "Feature: Authentication" in text
        assert "Given user is on login page" in text
        assert "Tags: smoke, auth" in text

    def test_step_to_text(self):
        """Test converting step data to text."""
        step_data = {
            "text": "user enters valid credentials",
            "keyword": "When",
            "context": "login page",
            "action": "enter credentials",
        }

        text = step_to_text(step_data)

        assert "Type: When" in text
        assert "Step: user enters valid credentials" in text
        assert "Context: login page" in text
        assert "Action: enter credentials" in text

    def test_page_to_text(self):
        """Test converting page object data to text."""
        page_data = {
            "name": "LoginPage",
            "methods": ["login", "enterUsername", "enterPassword"],
            "locators": {"username": "#username", "password": "#password"},
            "purpose": "Handle login page interactions",
        }

        text = page_to_text(page_data)

        assert "Page: LoginPage" in text
        assert "Methods: login, enterUsername, enterPassword" in text
        assert "Elements: username, password" in text
        assert "Purpose: Handle login page interactions" in text

    def test_failure_to_text(self):
        """Test converting failure data to text."""
        failure_data = {
            "test_name": "test_login_timeout",
            "error_type": "TimeoutException",
            "message": "Element not found within timeout",
            "context": "Login page",
            "stack_trace": "line1\nline2\nline3\nline4",
        }

        text = failure_to_text(failure_data)

        assert "Test Failure: test_login_timeout" in text
        assert "Error: TimeoutException" in text
        assert "Message: Element not found within timeout" in text
        assert "Context: Login page" in text
        assert "Stack:" in text
        # Should only include first 3 lines of stack trace
        assert "line1" in text
        assert "line2" in text


class TestMemoryType:
    """Tests for MemoryType enum."""

    def test_all_memory_types(self):
        """Test that all expected memory types exist."""
        expected_types = [
            "test",
            "scenario",
            "step",
            "page",
            "code",
            "failure",
            "assertion",
            "locator",
        ]

        for type_name in expected_types:
            assert hasattr(MemoryType, type_name.upper())
            assert MemoryType[type_name.upper()].value == type_name

    def test_memory_type_string_conversion(self):
        """Test converting string to MemoryType."""
        assert MemoryType("test") == MemoryType.TEST
        assert MemoryType("scenario") == MemoryType.SCENARIO
        assert MemoryType("step") == MemoryType.STEP
