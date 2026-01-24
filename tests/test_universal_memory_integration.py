"""
Tests for universal memory and embedding integration across all frameworks.

Verifies that all 13 framework adapters can normalize to UnifiedTestMemory
with structural and semantic signals.
"""

import pytest
from pathlib import Path

from adapters.common.models import TestMetadata
from adapters.common.normalizer import UniversalTestNormalizer
from adapters.common.memory_integration import (
    cypress_to_memory,
    playwright_to_memory,
    robot_to_memory,
    pytest_to_memory,
    junit_to_memory,
    testng_to_memory,
    restassured_to_memory,
    selenium_to_memory,
    cucumber_to_memory,
    behave_to_memory,
    specflow_to_memory,
    add_memory_support_to_adapter
)
from core.intelligence.models import UnifiedTestMemory, TestType, Priority


class TestUniversalNormalizer:
    """Test the universal test normalizer."""
    
    def test_normalize_cypress_test(self):
        """Test normalizing Cypress test."""
        metadata = TestMetadata(
            test_name="should login successfully",
            file_path="cypress/e2e/login.cy.js",
            framework="cypress",
            tags=["e2e", "smoke"],
            test_type="e2e",
            language="javascript"
        )
        
        source_code = """
        describe('Login', () => {
            it('should login successfully', () => {
                cy.visit('/login');
                cy.get('#username').type('user@example.com');
                cy.get('#password').type('password123');
                cy.get('button[type="submit"]').click();
                cy.url().should('include', '/dashboard');
            });
        });
        """
        
        normalizer = UniversalTestNormalizer()
        unified = normalizer.normalize(metadata, source_code, generate_embedding=False)
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "cypress"
        assert unified.language == "javascript"
        assert unified.test_name == "should login successfully"
        assert "cypress" in unified.test_id
        assert unified.metadata.test_type == TestType.E2E
        
        # Check semantic signals
        assert unified.semantic.intent_text
        assert "login" in unified.semantic.keywords
    
    def test_normalize_playwright_test(self):
        """Test normalizing Playwright test."""
        metadata = TestMetadata(
            test_name="test checkout flow",
            file_path="tests/checkout.spec.ts",
            framework="playwright",
            tags=["e2e"],
            test_type="e2e",
            language="typescript"
        )
        
        source_code = """
        test('test checkout flow', async ({ page }) => {
            await page.goto('https://example.com/shop');
            await page.click('[data-testid="add-to-cart"]');
            await page.fill('#email', 'user@test.com');
            expect(page.url()).toContain('/cart');
        });
        """
        
        unified = playwright_to_memory(metadata, source_code)
        
        assert unified.framework == "playwright"
        assert unified.language == "typescript"
        assert unified.metadata.test_type == TestType.E2E
    
    def test_normalize_robot_test(self):
        """Test normalizing Robot Framework test."""
        metadata = TestMetadata(
            test_name="Valid Login Test",
            file_path="tests/login.robot",
            framework="robot",
            tags=["smoke"],
            test_type="ui",
            language="robot"
        )
        
        unified = robot_to_memory(metadata)
        
        assert unified.framework == "robot"
        assert unified.test_name == "Valid Login Test"
        assert "smoke" in unified.metadata.tags
    
    def test_normalize_junit_test(self):
        """Test normalizing JUnit test."""
        metadata = TestMetadata(
            test_name="testCreateUser",
            file_path="src/test/java/UserTest.java",
            framework="junit",
            tags=["api", "critical"],
            test_type="integration",
            language="java"
        )
        
        source_code = """
        @Test
        public void testCreateUser() {
            User user = new User("john", "john@example.com");
            Response response = userService.create(user);
            assertEquals(201, response.getStatusCode());
            assertNotNull(response.getBody());
        }
        """
        
        unified = junit_to_memory(metadata, source_code)
        
        assert unified.framework == "junit"
        assert unified.language == "java"
        assert unified.metadata.priority == Priority.P0  # critical tag
        assert len(unified.structural.assertions) > 0
    
    def test_normalize_batch(self):
        """Test batch normalization."""
        tests = [
            TestMetadata(
                test_name="test1",
                file_path="test1.js",
                framework="cypress",
                tags=[],
                language="javascript"
            ),
            TestMetadata(
                test_name="test2",
                file_path="test2.ts",
                framework="playwright",
                tags=[],
                language="typescript"
            ),
            TestMetadata(
                test_name="test3",
                file_path="test3.java",
                framework="junit",
                tags=[],
                language="java"
            )
        ]
        
        normalizer = UniversalTestNormalizer()
        unified_tests = normalizer.normalize_batch(tests, generate_embeddings=False)
        
        assert len(unified_tests) == 3
        assert all(isinstance(t, UnifiedTestMemory) for t in unified_tests)
        assert unified_tests[0].framework == "cypress"
        assert unified_tests[1].framework == "playwright"
        assert unified_tests[2].framework == "junit"
    
    def test_all_framework_converters(self):
        """Test that all framework-specific converters work."""
        converters = [
            (cypress_to_memory, "cypress", "javascript"),
            (playwright_to_memory, "playwright", "javascript"),
            (robot_to_memory, "robot", "robot"),
            (pytest_to_memory, "pytest", "python"),
            (junit_to_memory, "junit", "java"),
            (testng_to_memory, "testng", "java"),
            (restassured_to_memory, "restassured", "java"),
            (selenium_to_memory, "selenium", "python"),
            (cucumber_to_memory, "cucumber", "java"),
            (behave_to_memory, "behave", "python"),
            (specflow_to_memory, "specflow", "csharp")
        ]
        
        for converter, framework, language in converters:
            metadata = TestMetadata(
                test_name="test",
                file_path=f"test.{language}",
                framework=framework,
                tags=[],
                language=language
            )
            
            unified = converter(metadata)
            assert isinstance(unified, UnifiedTestMemory)
            assert unified.framework == framework
            print(f"✓ {framework} converter works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
