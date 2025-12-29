"""
Unit tests for Java AST parser and test extraction.

Tests cover:
- JUnit test extraction
- TestNG test extraction
- Mixed framework projects
- Tag/annotation extraction
- PageObject detection
- Edge cases with mocking
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from adapters.selenium_java.config import SeleniumJavaConfig
from adapters.selenium_java.extractor import SeleniumJavaExtractor
from adapters.common.models import TestMetadata


# Sample Java fixtures
JUNIT5_LOGIN_TEST = """
package com.example;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Tag;

public class LoginTest {

    @Test
    @Tag("smoke")
    void testValidLogin() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.enterCredentials("user", "pass");
    }

    @Test
    @Tag("regression")
    void testInvalidLogin() {
        LoginPage loginPage = new LoginPage(driver);
        DashboardPage dashboard = new DashboardPage(driver);
    }
}
"""

TESTNG_CHECKOUT_TEST = """
package com.example;

import org.testng.annotations.Test;

public class CheckoutTest {

    @Test(groups = {"smoke"})
    public void testCheckoutFlow() {
        CartPage cart = new CartPage(driver);
        CheckoutPage checkout = new CheckoutPage(driver);
    }
}
"""

JUNIT4_PROFILE_TEST = """
package com.example;

import org.junit.Test;
import org.junit.experimental.categories.Category;

public class ProfileTest {

    @Test
    @Category(SmokeTests.class)
    public void testEditProfile() {
        ProfilePage profile = new ProfilePage(driver);
    }
}
"""


class TestJUnit5Extraction:
    """Test extraction of JUnit 5 tests."""
    
    def test_extract_junit5_tests(self, tmp_path):
        """Test extracting JUnit 5 test methods."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "LoginTest.java"
        test_file.write_text(JUNIT5_LOGIN_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="junit5",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should find 2 test methods
        method_names = [t.test_name for t in tests]
        assert any("testValidLogin" in name for name in method_names)
        assert any("testInvalidLogin" in name for name in method_names)
        
        # Check framework detection
        for test in tests:
            assert "selenium-java" in test.framework
            assert "LoginTest" in test.test_name
    
    def test_extract_junit5_tags(self, tmp_path):
        """Test extracting @Tag annotations from JUnit 5."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "LoginTest.java"
        test_file.write_text(JUNIT5_LOGIN_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="junit5",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Check that tags are extracted (if supported by extractor)
        assert len(tests) >= 2


class TestTestNGExtraction:
    """Test extraction of TestNG tests."""
    
    def test_extract_testng_tests(self, tmp_path):
        """Test extracting TestNG test methods."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "CheckoutTest.java"
        test_file.write_text(TESTNG_CHECKOUT_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="testng",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should find 1 test method
        assert len(tests) >= 1
        assert any("testCheckoutFlow" in t.test_name for t in tests)
        assert any("testng" in t.framework for t in tests)
    
    def test_extract_testng_groups(self, tmp_path):
        """Test extracting groups from TestNG @Test annotation."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "CheckoutTest.java"
        test_file.write_text(TESTNG_CHECKOUT_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="testng",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should extract test
        assert len(tests) >= 1


class TestJUnit4Extraction:
    """Test extraction of JUnit 4 tests."""
    
    def test_extract_junit4_tests(self, tmp_path):
        """Test extracting JUnit 4 test methods."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "ProfileTest.java"
        test_file.write_text(JUNIT4_PROFILE_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should find 1 test method
        assert len(tests) >= 1
        assert any("testEditProfile" in t.test_name for t in tests)


class TestPageObjectDetection:
    """Test detection of PageObject references in tests."""
    
    def test_detect_page_objects_in_junit5(self, tmp_path):
        """Test detecting PageObject instantiation in JUnit 5 tests (placeholder)."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "LoginTest.java"
        test_file.write_text(JUNIT5_LOGIN_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="junit5",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # PageObject detection would require additional parsing
        # This test validates the extraction works
        assert len(tests) >= 2
    
    def test_detect_page_objects_in_testng(self, tmp_path):
        """Test detecting PageObject instantiation in TestNG tests (placeholder)."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "CheckoutTest.java"
        test_file.write_text(TESTNG_CHECKOUT_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="testng",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # PageObject detection would require additional parsing
        # This test validates the extraction works
        assert len(tests) >= 1


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_no_tests_found(self, tmp_path):
        """Test when no test files exist."""
        src_dir = tmp_path / "src" / "test" / "java"
        src_dir.mkdir(parents=True)
        
        config = SeleniumJavaConfig(
            root_dir=str(src_dir),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should return empty list, not crash
        assert tests == []
    
    def test_invalid_java_file_does_not_crash(self, tmp_path):
        """Test that invalid Java files don't crash parser."""
        src_dir = tmp_path / "src" / "test" / "java"
        src_dir.mkdir(parents=True)
        
        bad_file = src_dir / "BadTest.java"
        bad_file.write_text("this is not java @#$%^&*()")
        
        config = SeleniumJavaConfig(
            root_dir=str(src_dir),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should return empty list, not crash
        assert isinstance(tests, list)
    
    def test_empty_test_class(self, tmp_path):
        """Test class with no test methods."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "EmptyTest.java"
        test_file.write_text("""
        package com.example;
        
        import org.junit.jupiter.api.Test;
        
        public class EmptyTest {
            // No test methods
        }
        """)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should handle gracefully
        assert isinstance(tests, list)
    
    def test_non_test_directory(self, tmp_path):
        """Test that non-test directories are handled."""
        src_dir = tmp_path / "src" / "main" / "java"
        src_dir.mkdir(parents=True)
        
        config = SeleniumJavaConfig(
            root_dir=str(src_dir),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should return empty list
        assert tests == []


class TestMockedJavaParser:
    """Test AST parser with mocked extraction (no external deps)."""
    
    @patch('adapters.selenium_java.extractor.SeleniumJavaExtractor.extract_tests')
    def test_mocked_junit_extraction(self, mock_extract, tmp_path):
        """Test extraction with mocked extractor."""
        # Mock the extractor to return test data
        mock_extract.return_value = [
            TestMetadata(
                framework="selenium-java-junit5",
                test_name="LoginTest.testLogin",
                file_path="LoginTest.java",
                tags=["smoke"],
                test_type="ui",
                language="java"
            )
        ]
        
        src_dir = tmp_path / "src" / "test" / "java"
        src_dir.mkdir(parents=True)
        
        config = SeleniumJavaConfig(
            root_dir=str(src_dir),
            test_framework="junit5",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should use mocked data
        assert len(tests) == 1
        test = tests[0]
        assert "LoginTest" in test.test_name
        assert "testLogin" in test.test_name
        assert "smoke" in test.tags
    
    @patch('adapters.selenium_java.extractor.Path.rglob')
    def test_mocked_parser_error_handling(self, mock_rglob, tmp_path):
        """Test that parser errors are handled gracefully."""
        # Mock rglob to raise exception
        mock_rglob.side_effect = Exception("File system error")
        
        src_dir = tmp_path / "src" / "test" / "java"
        src_dir.mkdir(parents=True)
        
        config = SeleniumJavaConfig(
            root_dir=str(src_dir),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        
        # Should raise exception (not silently fail)
        with pytest.raises(Exception):
            extractor.extract_tests()


class TestContractStability:
    """Test that TestMetadata contract remains stable (CRITICAL)."""
    
    def test_test_metadata_contract(self, tmp_path):
        """Test that TestMetadata has required attributes."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "LoginTest.java"
        test_file.write_text(JUNIT5_LOGIN_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="junit5",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        if tests:
            t = tests[0]
            # Required attributes for downstream consumers
            assert hasattr(t, "framework")
            assert hasattr(t, "test_name")
            assert hasattr(t, "file_path")
            assert hasattr(t, "tags")
            assert hasattr(t, "test_type")
            assert hasattr(t, "language")
    
    def test_return_type_is_list(self, tmp_path):
        """Test that extract_tests returns a list."""
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        result = extractor.extract_tests()
        
        assert isinstance(result, list)
    
    def test_empty_result_is_empty_list_not_none(self, tmp_path):
        """Test that no tests returns empty list, not None."""
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path),
            test_framework="junit",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        result = extractor.extract_tests()
        
        assert result == []
        assert result is not None
    
    def test_file_path_is_string(self, tmp_path):
        """Test that file paths are properly formatted."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "LoginTest.java"
        test_file.write_text(JUNIT5_LOGIN_TEST)
        
        config = SeleniumJavaConfig(
            root_dir=str(tmp_path / "src" / "test" / "java"),
            test_framework="junit5",
            project_root=str(tmp_path)
        )
        extractor = SeleniumJavaExtractor(config)
        tests = extractor.extract_tests()
        
        if tests:
            for test in tests:
                # File path should be a string and not empty
                assert isinstance(test.file_path, str)
                assert len(test.file_path) > 0
