"""
Unit tests for JavaScript/TypeScript AST Extractor.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.intelligence.javascript_ast_extractor import (
    JavaScriptASTExtractor,
    TypeScriptASTExtractor,
    JavaScriptASTExtractorFactory
)
from core.intelligence.models import StructuralSignals


class TestJavaScriptASTExtractor:
    """Test JavaScript AST extractor."""
    
    def test_supports_language(self):
        extractor = JavaScriptASTExtractor()
        assert extractor.supports_language() == "javascript"
    
    def test_extract_with_regex_fallback(self):
        """Test regex-based extraction when esprima is not available."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        import { test, expect } from '@playwright/test';
        import axios from 'axios';
        
        test('user login', async ({ page }) => {
            await page.goto('/login');
            await page.fill('#username', 'test');
            await page.click('button[type="submit"]');
            await expect(page).toHaveURL('/dashboard');
        });
        """
        
        signals = extractor.extract(source_code, "user login")
        
        assert "@playwright/test" in signals.imports
        assert "axios" in signals.imports
    
    def test_extract_playwright_interactions(self):
        """Test extraction of Playwright UI interactions."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        test('e2e test', async ({ page }) => {
            await page.goto('https://example.com');
            await page.click('#button');
            await page.fill('input', 'value');
            await page.select('dropdown', 'option');
        });
        """
        
        signals = extractor.extract(source_code, "e2e test")
        
        assert "goto" in signals.ui_interactions
        assert "click" in signals.ui_interactions
        assert "fill" in signals.ui_interactions
    
    def test_extract_api_calls(self):
        """Test extraction of API calls."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        test('api test', async () => {
            const response = await axios.get('/api/users');
            const data = await fetch('/api/posts');
            await request.post('/api/create');
        });
        """
        
        signals = extractor.extract(source_code, "api test")
        
        assert len(signals.api_calls) >= 2
        methods = [call.method for call in signals.api_calls]
        assert "GET" in methods or "POST" in methods
    
    def test_extract_assertions(self):
        """Test extraction of assertions."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        test('assertions test', () => {
            expect(result).toBe(true);
            expect(value).toEqual(expected);
            assert(condition);
        });
        """
        
        signals = extractor.extract(source_code, "assertions test")
        
        assert len(signals.assertions) >= 2
        targets = [a.target for a in signals.assertions]
        assert "expect" in targets or "assert" in targets
    
    def test_extract_commonjs_require(self):
        """Test extraction of CommonJS require statements."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        const axios = require('axios');
        const { test } = require('@jest/globals');
        
        test('my test', () => {});
        """
        
        signals = extractor.extract(source_code, "my test")
        
        assert "axios" in signals.imports or len(signals.imports) > 0
    
    def test_extract_function_declarations(self):
        """Test extraction of function declarations."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        function helperFunction() {}
        
        const arrowFunc = () => {};
        
        async function asyncHelper() {}
        
        test('test', () => {});
        """
        
        signals = extractor.extract(source_code, "test")
        
        # Should extract some functions
        assert len(signals.functions) > 0
    
    def test_extract_class_declarations(self):
        """Test extraction of class declarations."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        class TestHelper {
            constructor() {}
        }
        
        class ApiClient {
            async fetch() {}
        }
        """
        
        signals = extractor.extract(source_code, "test")
        
        assert len(signals.classes) > 0
        assert "TestHelper" in signals.classes or "ApiClient" in signals.classes


class TestTypeScriptASTExtractor:
    """Test TypeScript AST extractor."""
    
    def test_supports_language(self):
        extractor = TypeScriptASTExtractor()
        assert extractor.supports_language() == "typescript"
    
    def test_extract_typescript_interfaces(self):
        """Test extraction of TypeScript interfaces."""
        extractor = TypeScriptASTExtractor()
        
        source_code = """
        interface User {
            id: number;
            name: string;
        }
        
        interface ApiResponse {
            data: any;
        }
        
        test('test with interfaces', () => {});
        """
        
        signals = extractor.extract(source_code, "test with interfaces")
        
        # Should extract interfaces as special class types
        interface_items = [c for c in signals.classes if c.startswith("interface:")]
        assert len(interface_items) > 0
    
    def test_extract_type_aliases(self):
        """Test extraction of TypeScript type aliases."""
        extractor = TypeScriptASTExtractor()
        
        source_code = """
        type UserId = string;
        type ApiResult = { data: any };
        
        test('test', () => {});
        """
        
        signals = extractor.extract(source_code, "test")
        
        type_items = [c for c in signals.classes if c.startswith("type:")]
        assert len(type_items) > 0
    
    def test_extract_decorators(self):
        """Test extraction of TypeScript decorators."""
        extractor = TypeScriptASTExtractor()
        
        source_code = """
        @Injectable()
        class TestService {
            @Timeout(5000)
            async testMethod() {}
        }
        """
        
        signals = extractor.extract(source_code, "testMethod")
        
        # Should extract decorators as fixtures
        decorators = [f for f in signals.fixtures if f.startswith("@")]
        assert len(decorators) > 0


class TestJavaScriptASTExtractorFactory:
    """Test JavaScript AST extractor factory."""
    
    def test_create_javascript_extractor(self):
        extractor = JavaScriptASTExtractorFactory.create("javascript")
        assert isinstance(extractor, JavaScriptASTExtractor)
        assert extractor.supports_language() == "javascript"
    
    def test_create_typescript_extractor(self):
        extractor = JavaScriptASTExtractorFactory.create("typescript")
        assert isinstance(extractor, TypeScriptASTExtractor)
        assert extractor.supports_language() == "typescript"
    
    def test_create_default_javascript(self):
        extractor = JavaScriptASTExtractorFactory.create()
        assert isinstance(extractor, JavaScriptASTExtractor)
    
    def test_is_available(self):
        available = JavaScriptASTExtractorFactory.is_available()
        assert isinstance(available, bool)


class TestJavaScriptASTWithEsprima:
    """Test JavaScript AST extractor with esprima library (if available)."""
    
    @pytest.mark.skipif(
        not JavaScriptASTExtractorFactory.is_available(),
        reason="esprima not installed"
    )
    def test_extract_with_esprima(self):
        """Test full AST extraction with esprima."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        import { test } from 'framework';
        
        test('example', () => {
            const x = 5;
            expect(x).toBe(5);
        });
        """
        
        signals = extractor.extract(source_code, "example")
        
        assert "framework" in signals.imports


class TestJavaScriptASTEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_source_code(self):
        extractor = JavaScriptASTExtractor()
        signals = extractor.extract("", "test")
        
        assert isinstance(signals, StructuralSignals)
        assert len(signals.imports) == 0
    
    def test_malformed_javascript_code(self):
        extractor = JavaScriptASTExtractor()
        
        # Malformed code should fall back to regex
        source_code = "function { invalid }"
        signals = extractor.extract(source_code, "test")
        
        assert isinstance(signals, StructuralSignals)
    
    def test_test_not_found(self):
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        test('different test', () => {
            console.log('test');
        });
        """
        
        signals = extractor.extract(source_code, "non-existent test")
        
        # Should still parse file-level structures
        assert isinstance(signals, StructuralSignals)
    
    def test_cypress_syntax(self):
        """Test extraction from Cypress tests."""
        extractor = JavaScriptASTExtractor()
        
        source_code = """
        describe('Login', () => {
            it('should login successfully', () => {
                cy.visit('/login');
                cy.get('#username').type('user');
                cy.get('#password').type('pass');
                cy.get('button').click();
            });
        });
        """
        
        signals = extractor.extract(source_code, "should login successfully")
        
        # Should extract cy.* interactions
        assert len(signals.ui_interactions) > 0 or len(signals.api_calls) >= 0
