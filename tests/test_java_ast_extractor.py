"""
Unit tests for Java AST Extractor.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.intelligence.java_ast_extractor import (
    JavaASTExtractor,
    JavaASTExtractorFactory
)
from core.intelligence.models import StructuralSignals


class TestJavaASTExtractor:
    """Test Java AST extractor."""
    
    def test_supports_language(self):
        extractor = JavaASTExtractor()
        assert extractor.supports_language() == "java"
    
    def test_extract_with_regex_fallback(self):
        """Test regex-based extraction when javalang is not available."""
        extractor = JavaASTExtractor()
        
        source_code = """
        package com.example.test;
        
        import org.junit.Test;
        import static org.junit.Assert.*;
        
        public class UserTest {
            
            @Test
            public void testGetUser() {
                String result = api.get("/api/users/123");
                assertEquals(200, response.statusCode);
                assertTrue(result.contains("name"));
            }
        }
        """
        
        signals = extractor.extract(source_code, "testGetUser")
        
        assert "org.junit.Test" in signals.imports
        assert "UserTest" in signals.classes
        assert "testGetUser" in signals.functions
        assert len(signals.api_calls) > 0
        assert len(signals.assertions) > 0
    
    def test_extract_restassured_api_calls(self):
        """Test extraction of RestAssured API calls."""
        extractor = JavaASTExtractor()
        
        source_code = """
        @Test
        public void testApiCall() {
            given()
                .pathParam("id", 123)
            .when()
                .get("/api/users/{id}")
            .then()
                .statusCode(200);
        }
        """
        
        signals = extractor.extract(source_code, "testApiCall")
        
        assert len(signals.api_calls) >= 1
        assert any(call.method == "GET" for call in signals.api_calls)
    
    def test_extract_selenium_interactions(self):
        """Test extraction of Selenium WebDriver calls."""
        extractor = JavaASTExtractor()
        
        source_code = """
        @Test
        public void testUIInteraction() {
            driver.findElement(By.id("username")).sendKeys("test");
            driver.findElement(By.id("login")).click();
            String text = driver.findElement(By.className("welcome")).getText();
        }
        """
        
        signals = extractor.extract(source_code, "testUIInteraction")
        
        assert "findElement" in signals.ui_interactions
        assert "sendKeys" in signals.ui_interactions
        assert "click" in signals.ui_interactions
    
    def test_extract_testng_annotations(self):
        """Test extraction of TestNG annotations."""
        extractor = JavaASTExtractor()
        
        source_code = """
        @Test(priority = 0, groups = {"smoke", "api"})
        @BeforeClass
        public void setup() {}
        
        @Test
        public void testExample() {}
        """
        
        signals = extractor.extract(source_code, "testExample")
        
        # Should extract @Test and @BeforeClass
        test_annotations = [f for f in signals.fixtures if f.startswith("@")]
        assert len(test_annotations) > 0
    
    def test_extract_multiple_assertions(self):
        """Test extraction of multiple assertion types."""
        extractor = JavaASTExtractor()
        
        source_code = """
        @Test
        public void testAssertions() {
            assertEquals(expected, actual);
            assertTrue(condition);
            assertFalse(flag);
            assertNotNull(object);
        }
        """
        
        signals = extractor.extract(source_code, "testAssertions")
        
        assert len(signals.assertions) >= 4
        assertion_types = [a.target for a in signals.assertions]
        assert "assertEquals" in assertion_types
        assert "assertTrue" in assertion_types


class TestJavaASTExtractorFactory:
    """Test Java AST extractor factory."""
    
    def test_create_extractor(self):
        extractor = JavaASTExtractorFactory.create()
        assert isinstance(extractor, JavaASTExtractor)
        assert extractor.supports_language() == "java"
    
    def test_is_available(self):
        # Should return True or False, not raise exception
        available = JavaASTExtractorFactory.is_available()
        assert isinstance(available, bool)


class TestJavaASTWithJavalang:
    """Test Java AST extractor with javalang library (if available)."""
    
    @pytest.mark.skipif(
        not JavaASTExtractorFactory.is_available(),
        reason="javalang not installed"
    )
    def test_extract_with_javalang(self):
        """Test full AST extraction with javalang."""
        extractor = JavaASTExtractor()
        
        source_code = """
        package com.example;
        
        import org.junit.Test;
        
        public class SimpleTest {
            @Test
            public void testMethod() {
                int x = 5;
                assertEquals(5, x);
            }
        }
        """
        
        signals = extractor.extract(source_code, "testMethod")
        
        assert "org.junit.Test" in signals.imports
        assert "SimpleTest" in signals.classes
        assert "testMethod" in signals.functions


class TestJavaASTEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_source_code(self):
        extractor = JavaASTExtractor()
        signals = extractor.extract("", "testEmpty")
        
        assert isinstance(signals, StructuralSignals)
        assert len(signals.imports) == 0
    
    def test_malformed_java_code(self):
        extractor = JavaASTExtractor()
        
        # Malformed code should fall back to regex
        source_code = "public class { invalid syntax }"
        signals = extractor.extract(source_code, "test")
        
        assert isinstance(signals, StructuralSignals)
    
    def test_test_method_not_found(self):
        extractor = JavaASTExtractor()
        
        source_code = """
        public class Test {
            public void someOtherMethod() {}
        }
        """
        
        signals = extractor.extract(source_code, "nonExistentTest")
        
        # Should still extract class-level info
        assert "Test" in signals.classes
        assert len(signals.assertions) == 0
