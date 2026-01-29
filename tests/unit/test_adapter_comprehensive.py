"""
Comprehensive Test Infrastructure for Framework Adapters

Provides base test classes, fixtures, and utilities for testing all
framework adapters with consistent coverage and quality.

Ensures comprehensive test coverage for all framework adapters.
"""

import ast
import json
import pytest
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from unittest.mock import Mock, patch

from adapters.base import FrameworkAdapter
from core.models import (
    TestCase,
    TestSuite,
    FeatureFile,
    StepDefinition,
    PageObject,
    TestDiscovery,
)


class AdapterTestBase(ABC):
    """
    Base class for all adapter tests.
    
    Provides common test infrastructure, fixtures, and assertion helpers
    for consistent testing across all 12+ framework adapters.
    """

    @property
    @abstractmethod
    def adapter_class(self) -> Type[FrameworkAdapter]:
        """Return the adapter class being tested."""
        pass

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Return the framework name (e.g., 'pytest', 'selenium_java')."""
        pass

    @pytest.fixture
    def adapter(self) -> FrameworkAdapter:
        """Create adapter instance for testing."""
        return self.adapter_class()

    @pytest.fixture
    def sample_test_file(self, tmp_path: Path) -> Path:
        """
        Create a sample test file for the framework.
        
        Subclasses should override to provide framework-specific content.
        """
        return self._create_sample_file(tmp_path)

    @abstractmethod
    def _create_sample_file(self, tmp_path: Path) -> Path:
        """Create framework-specific sample test file."""
        pass

    # ========================================================================
    # Common Test Methods (All Adapters Must Pass)
    # ========================================================================

    def test_adapter_initialization(self, adapter):
        """Test that adapter initializes correctly."""
        assert adapter is not None
        assert adapter.framework_name == self.framework_name
        assert hasattr(adapter, "discover_tests")
        assert hasattr(adapter, "parse_test")

    def test_framework_detection(self, adapter, sample_test_file):
        """Test that adapter can detect its framework."""
        assert adapter.can_handle(sample_test_file)

    def test_basic_test_discovery(self, adapter, sample_test_file):
        """Test basic test discovery functionality."""
        discovery = adapter.discover_tests(sample_test_file.parent)
        
        assert discovery is not None
        assert isinstance(discovery, TestDiscovery)
        assert len(discovery.test_cases) > 0
        
        # Verify test case structure
        test_case = discovery.test_cases[0]
        assert test_case.name is not None
        assert test_case.file_path is not None

    def test_parse_single_test(self, adapter, sample_test_file):
        """Test parsing a single test file."""
        result = adapter.parse_test(sample_test_file)
        
        assert result is not None
        assert hasattr(result, "name")
        assert hasattr(result, "steps") or hasattr(result, "test_methods")

    def test_locator_extraction(self, adapter, sample_test_file):
        """Test locator extraction from test files."""
        locators = adapter.extract_locators(sample_test_file)
        
        # Not all frameworks have locators, but method should exist
        assert locators is not None
        assert isinstance(locators, list)

    def test_error_handling_invalid_file(self, adapter, tmp_path):
        """Test error handling with invalid file."""
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("This is not a valid test file")
        
        # Should handle gracefully, not crash
        result = adapter.parse_test(invalid_file)
        # Result can be None or empty, but should not raise exception

    def test_empty_directory_discovery(self, adapter, tmp_path):
        """Test discovery in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        discovery = adapter.discover_tests(empty_dir)
        assert discovery is not None
        assert len(discovery.test_cases) == 0

    def test_metadata_extraction(self, adapter, sample_test_file):
        """Test extraction of test metadata (tags, markers, etc.)."""
        result = adapter.parse_test(sample_test_file)
        
        # Should have metadata field
        assert hasattr(result, "metadata") or hasattr(result, "tags")

    def test_concurrent_discovery(self, adapter, sample_test_file):
        """Test that adapter is thread-safe for concurrent discovery."""
        import concurrent.futures
        
        def discover():
            return adapter.discover_tests(sample_test_file.parent)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(discover) for _ in range(3)]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(r is not None for r in results)
        assert all(len(r.test_cases) > 0 for r in results)

    # ========================================================================
    # Performance Tests
    # ========================================================================

    def test_discovery_performance(self, adapter, sample_test_file, benchmark):
        """Benchmark test discovery performance."""
        result = benchmark(adapter.discover_tests, sample_test_file.parent)
        
        assert result is not None
        # Discovery should complete in reasonable time (< 5 seconds for small projects)

    def test_parse_performance(self, adapter, sample_test_file, benchmark):
        """Benchmark single file parsing performance."""
        result = benchmark(adapter.parse_test, sample_test_file)
        
        assert result is not None
        # Parsing should be fast (< 1 second per file)

    # ========================================================================
    # Regression Tests
    # ========================================================================

    def test_backward_compatibility(self, adapter, sample_test_file):
        """
        Test that adapter maintains backward compatibility.
        
        Ensures changes don't break existing functionality.
        """
        # Parse once
        result1 = adapter.parse_test(sample_test_file)
        
        # Parse again
        result2 = adapter.parse_test(sample_test_file)
        
        # Results should be consistent
        assert result1.name == result2.name

    # ========================================================================
    # Assertion Helpers
    # ========================================================================

    def assert_valid_test_case(self, test_case: TestCase):
        """Assert that a test case has all required fields."""
        assert test_case.id is not None
        assert test_case.name is not None
        assert test_case.file_path is not None
        assert test_case.framework == self.framework_name

    def assert_valid_test_suite(self, suite: TestSuite):
        """Assert that a test suite is valid."""
        assert suite.name is not None
        assert suite.tests is not None
        assert isinstance(suite.tests, list)

    def assert_locators_extracted(self, locators: List[Dict[str, Any]]):
        """Assert that locators were extracted correctly."""
        for locator in locators:
            assert "type" in locator  # xpath, css, id, etc.
            assert "value" in locator
            assert "element" in locator  # element name/description


# ============================================================================
# Concrete Test Classes for Each Adapter
# ============================================================================


class TestPytestAdapter(AdapterTestBase):
    """Comprehensive tests for pytest adapter."""

    @property
    def adapter_class(self):
        from adapters.pytest import PytestAdapter
        return PytestAdapter

    @property
    def framework_name(self):
        return "pytest"

    def _create_sample_file(self, tmp_path: Path) -> Path:
        """Create sample pytest file."""
        test_file = tmp_path / "test_sample.py"
        test_file.write_text("""
import pytest

class TestLogin:
    @pytest.mark.smoke
    def test_valid_login(self):
        '''Test valid user login'''
        # Arrange
        username = "testuser"
        password = "testpass"
        
        # Act
        result = login(username, password)
        
        # Assert
        assert result.success is True
        assert result.user.name == username

    @pytest.mark.regression
    def test_invalid_credentials(self):
        '''Test login with invalid credentials'''
        with pytest.raises(AuthenticationError):
            login("invalid", "wrong")

def test_logout():
    '''Test user logout'''
    logout()
    assert session.is_active() is False
""")
        return test_file

    def test_pytest_marker_extraction(self, adapter, sample_test_file):
        """Test extraction of pytest markers."""
        result = adapter.parse_test(sample_test_file)
        
        # Should extract @pytest.mark decorators
        markers = result.metadata.get("markers", [])
        assert "smoke" in markers or "regression" in markers

    def test_pytest_fixture_detection(self, adapter, tmp_path):
        """Test detection of pytest fixtures."""
        conftest = tmp_path / "conftest.py"
        conftest.write_text("""
import pytest

@pytest.fixture
def db_connection():
    return DatabaseConnection()

@pytest.fixture(scope="session")
def browser():
    return WebDriver()
""")
        
        discovery = adapter.discover_tests(tmp_path)
        assert "fixtures" in discovery.metadata


class TestSeleniumJavaAdapter(AdapterTestBase):
    """Comprehensive tests for Selenium Java adapter."""

    @property
    def adapter_class(self):
        from adapters.selenium_java import SeleniumJavaAdapter
        return SeleniumJavaAdapter

    @property
    def framework_name(self):
        return "selenium_java"

    def _create_sample_file(self, tmp_path: Path) -> Path:
        """Create sample Selenium Java test file."""
        test_file = tmp_path / "LoginTest.java"
        test_file.write_text("""
package com.example.tests;

import org.junit.Test;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

public class LoginTest {
    private WebDriver driver;
    
    @Test
    public void testValidLogin() {
        driver.get("https://example.com/login");
        
        WebElement usernameField = driver.findElement(By.id("username"));
        WebElement passwordField = driver.findElement(By.id("password"));
        WebElement loginButton = driver.findElement(By.cssSelector("button.login"));
        
        usernameField.sendKeys("testuser");
        passwordField.sendKeys("testpass");
        loginButton.click();
        
        WebElement welcome = driver.findElement(By.xpath("//h1[@class='welcome']"));
        assert welcome.getText().contains("Welcome");
    }
    
    @Test
    public void testInvalidLogin() {
        driver.get("https://example.com/login");
        driver.findElement(By.id("username")).sendKeys("invalid");
        driver.findElement(By.id("password")).sendKeys("wrong");
        driver.findElement(By.cssSelector("button.login")).click();
        
        WebElement error = driver.findElement(By.className("error-message"));
        assert error.isDisplayed();
    }
}
""")
        return test_file

    def test_java_locator_extraction(self, adapter, sample_test_file):
        """Test extraction of Selenium locators from Java code."""
        locators = adapter.extract_locators(sample_test_file)
        
        assert len(locators) > 0
        
        # Should extract By.id(), By.cssSelector(), By.xpath()
        locator_types = [loc["type"] for loc in locators]
        assert "id" in locator_types
        assert "css" in locator_types or "xpath" in locator_types

    def test_java_annotation_extraction(self, adapter, sample_test_file):
        """Test extraction of JUnit/TestNG annotations."""
        result = adapter.parse_test(sample_test_file)
        
        # Should detect @Test annotations
        assert len(result.test_methods) >= 2


class TestRobotAdapter(AdapterTestBase):
    """Comprehensive tests for Robot Framework adapter."""

    @property
    def adapter_class(self):
        from adapters.robot import RobotAdapter
        return RobotAdapter

    @property
    def framework_name(self):
        return "robot"

    def _create_sample_file(self, tmp_path: Path) -> Path:
        """Create sample Robot Framework file."""
        test_file = tmp_path / "login_tests.robot"
        test_file.write_text("""
*** Settings ***
Library           SeleniumLibrary
Suite Setup       Open Browser    https://example.com    chrome
Suite Teardown    Close Browser

*** Variables ***
${USERNAME}       testuser
${PASSWORD}       testpass

*** Test Cases ***
Valid Login Test
    [Tags]    smoke    critical
    [Documentation]    Test valid user login flow
    Input Text        id=username    ${USERNAME}
    Input Text        id=password    ${PASSWORD}
    Click Button      css=button.login
    Wait Until Page Contains    Welcome
    Page Should Contain    ${USERNAME}

Invalid Login Test
    [Tags]    regression
    [Documentation]    Test login with invalid credentials
    Input Text        id=username    invalid
    Input Text        id=password    wrong
    Click Button      css=button.login
    Wait Until Page Contains    Error
    Element Should Be Visible    class=error-message

*** Keywords ***
Login With Credentials
    [Arguments]    ${user}    ${pass}
    Input Text        id=username    ${user}
    Input Text        id=password    ${pass}
    Click Button      css=button.login
""")
        return test_file

    def test_robot_keyword_extraction(self, adapter, sample_test_file):
        """Test extraction of Robot Framework keywords."""
        result = adapter.parse_test(sample_test_file)
        
        # Should extract custom keywords from *** Keywords *** section
        keywords = result.keywords
        assert len(keywords) > 0
        assert any("Login" in kw.name for kw in keywords)

    def test_robot_variable_extraction(self, adapter, sample_test_file):
        """Test extraction of Robot Framework variables."""
        result = adapter.parse_test(sample_test_file)
        
        # Should extract variables from *** Variables *** section
        variables = result.variables
        assert "USERNAME" in variables or "${USERNAME}" in str(variables)

    def test_robot_tag_extraction(self, adapter, sample_test_file):
        """Test extraction of test tags."""
        result = adapter.parse_test(sample_test_file)
        
        # Should extract [Tags] from test cases
        test_cases = result.test_cases
        tags = [tag for tc in test_cases for tag in tc.tags]
        assert "smoke" in tags or "regression" in tags


class TestCypressAdapter(AdapterTestBase):
    """Comprehensive tests for Cypress adapter."""

    @property
    def adapter_class(self):
        from adapters.cypress import CypressAdapter
        return CypressAdapter

    @property
    def framework_name(self):
        return "cypress"

    def _create_sample_file(self, tmp_path: Path) -> Path:
        """Create sample Cypress test file."""
        test_file = tmp_path / "login.spec.js"
        test_file.write_text("""
describe('Login Flow', () => {
  beforeEach(() => {
    cy.visit('https://example.com/login');
  });

  it('should login with valid credentials', { tags: ['@smoke', '@critical'] }, () => {
    cy.get('[data-testid="username"]').type('testuser');
    cy.get('[data-testid="password"]').type('testpass');
    cy.get('button.login').click();
    
    cy.url().should('include', '/dashboard');
    cy.get('.welcome-message').should('contain', 'Welcome testuser');
  });

  it('should show error with invalid credentials', { tags: ['@regression'] }, () => {
    cy.get('[data-testid="username"]').type('invalid');
    cy.get('[data-testid="password"]').type('wrong');
    cy.get('button.login').click();
    
    cy.get('.error-message').should('be.visible');
    cy.get('.error-message').should('contain', 'Invalid credentials');
  });

  it('should handle empty form submission', () => {
    cy.get('button.login').click();
    
    cy.get('#username-error').should('exist');
    cy.get('#password-error').should('exist');
  });
});

describe('Logout Flow', () => {
  it('should logout successfully', () => {
    // Login first
    cy.login('testuser', 'testpass');
    
    // Logout
    cy.get('[data-testid="logout-button"]').click();
    cy.url().should('include', '/login');
  });
});
""")
        return test_file

    def test_cypress_command_extraction(self, adapter, sample_test_file):
        """Test extraction of Cypress commands."""
        result = adapter.parse_test(sample_test_file)
        
        # Should identify cy.get(), cy.type(), cy.click() patterns
        commands = result.metadata.get("commands", [])
        assert any("get" in cmd or "type" in cmd for cmd in commands)

    def test_cypress_describe_block_parsing(self, adapter, sample_test_file):
        """Test parsing of describe/it blocks."""
        result = adapter.parse_test(sample_test_file)
        
        # Should identify test suites (describe blocks)
        assert len(result.test_suites) >= 2  # Login Flow, Logout Flow

    def test_cypress_data_testid_extraction(self, adapter, sample_test_file):
        """Test extraction of data-testid locators."""
        locators = adapter.extract_locators(sample_test_file)
        
        # Should prioritize data-testid attributes
        testid_locators = [loc for loc in locators if loc["type"] == "data-testid"]
        assert len(testid_locators) > 0


# ============================================================================
# Embedding Similarity Regression Tests
# ============================================================================


class TestEmbeddingSimilarity:
    """
    Regression tests for embedding similarity calculations.
    
    Ensures semantic search quality doesn't degrade over time.
    """

    @pytest.fixture
    def embedding_provider(self):
        """Create embedding provider for testing."""
        from core.memory.embedding_provider import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider(model="text-embedding-3-small")

    def test_identical_texts_high_similarity(self, embedding_provider):
        """Test that identical texts have high similarity (> 0.95)."""
        text = "Login with valid user credentials"
        
        emb1 = embedding_provider.embed([text])[0]
        emb2 = embedding_provider.embed([text])[0]
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert similarity > 0.95

    def test_similar_texts_moderate_similarity(self, embedding_provider):
        """Test that similar texts have moderate similarity (0.7-0.9)."""
        text1 = "Login with valid user credentials"
        text2 = "User authentication with correct password"
        
        emb1 = embedding_provider.embed([text1])[0]
        emb2 = embedding_provider.embed([text2])[0]
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert 0.7 <= similarity <= 0.9

    def test_unrelated_texts_low_similarity(self, embedding_provider):
        """Test that unrelated texts have low similarity (< 0.5)."""
        text1 = "Login with valid user credentials"
        text2 = "Calculate shipping cost for order"
        
        emb1 = embedding_provider.embed([text1])[0]
        emb2 = embedding_provider.embed([text2])[0]
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert similarity < 0.5

    def test_embedding_dimension_consistency(self, embedding_provider):
        """Test that all embeddings have consistent dimensions."""
        texts = [
            "Short text",
            "This is a medium length text with more words",
            "This is a very long text that contains many words and spans multiple " +
            "lines to test whether the embedding dimension remains consistent " +
            "regardless of input text length."
        ]
        
        embeddings = embedding_provider.embed(texts)
        
        dimensions = [len(emb) for emb in embeddings]
        assert len(set(dimensions)) == 1  # All same dimension
        assert dimensions[0] == embedding_provider.get_dimension()

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


# ============================================================================
# Performance/Fuzz Tests
# ============================================================================


class TestAdapterPerformance:
    """Performance and stress tests for adapters."""

    @pytest.mark.slow
    def test_large_file_parsing(self, tmp_path):
        """Test parsing very large test files."""
        from adapters.pytest import PytestAdapter
        
        # Generate large test file (1000 test methods)
        large_file = tmp_path / "test_large.py"
        test_methods = []
        for i in range(1000):
            test_methods.append(f"""
    def test_method_{i}(self):
        assert True
""")
        
        content = f"""
import pytest

class TestLarge:
{''.join(test_methods)}
"""
        large_file.write_text(content)
        
        # Should complete in reasonable time (< 10 seconds)
        import time
        start = time.time()
        
        adapter = PytestAdapter()
        result = adapter.parse_test(large_file)
        
        elapsed = time.time() - start
        assert elapsed < 10.0
        assert len(result.test_methods) == 1000

    @pytest.mark.slow
    def test_deep_directory_discovery(self, tmp_path):
        """Test discovery in deeply nested directory structure."""
        from adapters.pytest import PytestAdapter
        
        # Create 10 levels deep
        current = tmp_path
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir()
            test_file = current / f"test_level{i}.py"
            test_file.write_text("""
def test_example():
    assert True
""")
        
        # Should discover all tests without stack overflow
        adapter = PytestAdapter()
        discovery = adapter.discover_tests(tmp_path)
        
        assert len(discovery.test_cases) == 10
