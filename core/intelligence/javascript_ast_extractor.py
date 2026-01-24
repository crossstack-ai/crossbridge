"""
JavaScript/TypeScript AST Extractor for CrossBridge Intelligent Test Assistance.

Extracts structural signals from JavaScript/TypeScript test code.
Supports Playwright, Jest, Mocha, Cypress, and other JS/TS test frameworks.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from core.intelligence.ast_extractor import ASTExtractor
from core.intelligence.models import (
    APICall,
    Assertion,
    StructuralSignals,
    TestType,
    Priority,
)

logger = logging.getLogger(__name__)


class JavaScriptASTExtractor(ASTExtractor):
    """
    JavaScript/TypeScript AST extractor.
    
    Extracts structural signals from JS/TS test code including:
    - Imports (ES6, CommonJS)
    - Functions and classes
    - Test blocks (describe, it, test)
    - API calls (fetch, axios, request)
    - Assertions (expect, assert, should)
    - UI interactions (Playwright, Cypress)
    """
    
    def supports_language(self) -> str:
        """Return the language this extractor supports."""
        return "javascript"
    
    def extract(self, source_code: str, test_name: str) -> StructuralSignals:
        """
        Extract structural signals from JavaScript/TypeScript test source code.
        
        Args:
            source_code: JS/TS test source code as string
            test_name: Name of the test function
            
        Returns:
            StructuralSignals object with normalized data
        """
        try:
            # Try to use esprima for proper AST parsing
            import esprima
            return self._extract_with_esprima(source_code, test_name)
        except ImportError:
            logger.warning("esprima not installed, falling back to regex extraction")
            return self._extract_with_regex(source_code, test_name)
        except Exception as e:
            logger.error(f"JavaScript AST extraction failed: {e}")
            return self._extract_with_regex(source_code, test_name)
    
    def _extract_with_esprima(self, source_code: str, test_name: str) -> StructuralSignals:
        """Extract using esprima library for proper AST parsing."""
        import esprima
        
        try:
            tree = esprima.parseScript(source_code, {'jsx': True, 'tolerant': True})
        except Exception as e:
            logger.error(f"Failed to parse JavaScript code: {e}")
            return self._extract_with_regex(source_code, test_name)
        
        signals = StructuralSignals()
        
        # Walk the AST
        self._walk_ast(tree, signals, test_name)
        
        return signals
    
    def _walk_ast(self, node, signals: StructuralSignals, test_name: str, in_test_block: bool = False):
        """Recursively walk the AST and extract signals."""
        if not hasattr(node, 'type'):
            return
        
        node_type = node.type
        
        # Extract imports
        if node_type == 'ImportDeclaration':
            if hasattr(node, 'source') and hasattr(node.source, 'value'):
                signals.imports.append(node.source.value)
        
        # Extract require statements (CommonJS)
        elif node_type == 'CallExpression':
            if (hasattr(node, 'callee') and 
                hasattr(node.callee, 'name') and 
                node.callee.name == 'require'):
                if hasattr(node, 'arguments') and len(node.arguments) > 0:
                    arg = node.arguments[0]
                    if hasattr(arg, 'value'):
                        signals.imports.append(arg.value)
            
            # Check for test blocks
            if hasattr(node, 'callee') and hasattr(node.callee, 'name'):
                callee_name = node.callee.name
                
                # Test definition blocks
                if callee_name in ['test', 'it', 'describe']:
                    if hasattr(node, 'arguments') and len(node.arguments) > 0:
                        test_arg = node.arguments[0]
                        if hasattr(test_arg, 'value'):
                            test_title = test_arg.value
                            if test_title == test_name:
                                in_test_block = True
                
                # In test block - extract API calls and assertions
                if in_test_block:
                    # API calls
                    if callee_name in ['fetch', 'axios', 'request', 'get', 'post', 'put', 'delete', 'patch']:
                        method = callee_name.upper() if callee_name in ['get', 'post', 'put', 'delete', 'patch'] else 'GET'
                        signals.api_calls.append(
                            APICall(
                                method=method,
                                endpoint=""
                            )
                        )
                    
                    # Playwright/Cypress UI interactions
                    if callee_name in ['goto', 'click', 'fill', 'type', 'select', 'check', 'visit']:
                        signals.ui_interactions.append(callee_name)
                    
                    # Assertions
                    if callee_name in ['expect', 'assert', 'should']:
                        signals.assertions.append(
                            Assertion(
                                type="js_assertion",
                                target=callee_name,
                                expected_value=None
                            )
                        )
        
        # Extract function declarations
        elif node_type in ['FunctionDeclaration', 'FunctionExpression', 'ArrowFunctionExpression']:
            if hasattr(node, 'id') and hasattr(node.id, 'name'):
                signals.functions.append(node.id.name)
        
        # Extract class declarations
        elif node_type == 'ClassDeclaration':
            if hasattr(node, 'id') and hasattr(node.id, 'name'):
                signals.classes.append(node.id.name)
        
        # Recursively process child nodes
        for key, value in node.__dict__.items():
            if isinstance(value, list):
                for item in value:
                    self._walk_ast(item, signals, test_name, in_test_block)
            elif hasattr(value, 'type'):
                self._walk_ast(value, signals, test_name, in_test_block)
    
    def _extract_with_regex(self, source_code: str, test_name: str) -> StructuralSignals:
        """Fallback regex-based extraction when esprima is not available."""
        signals = StructuralSignals()
        
        # Extract ES6 imports
        import_pattern = r'import\s+(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, source_code):
            signals.imports.append(match.group(1))
        
        # Extract CommonJS requires
        require_pattern = r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        for match in re.finditer(require_pattern, source_code):
            signals.imports.append(match.group(1))
        
        # Extract function declarations
        func_pattern = r'(?:function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)|const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>)'
        for match in re.finditer(func_pattern, source_code):
            func_name = match.group(1) or match.group(2)
            if func_name:
                signals.functions.append(func_name)
        
        # Extract class declarations
        class_pattern = r'class\s+([A-Z][a-zA-Z0-9]*)'
        for match in re.finditer(class_pattern, source_code):
            signals.classes.append(match.group(1))
        
        # Find test block
        # Match test/it blocks with either the test name or any string
        test_block_pattern = r'(?:test|it|describe)\s*\(\s*[\'"]([^\'"]*)[\'"]'
        test_matches = list(re.finditer(test_block_pattern, source_code))
        
        test_match = None
        for match in test_matches:
            if match.group(1) == test_name or test_name in match.group(1):
                test_match = match
                break
        
        if not test_match and test_matches:
            # If no exact match, use the first test block
            test_match = test_matches[0]
        
        if test_match:
            # Find the test function body
            # Look for => arrow function or function keyword
            start_pos = test_match.end()
            arrow_match = re.search(r'=>\s*\{', source_code[start_pos:])
            function_match = re.search(r'function\s*\([^)]*\)\s*\{', source_code[start_pos:])
            
            test_body = ""
            
            if arrow_match:
                # Arrow function - find the opening brace after =>
                body_start = start_pos + arrow_match.end() - 1  # -1 to include the {
                brace_count = 1
                i = body_start + 1
                
                while i < len(source_code) and brace_count > 0:
                    if source_code[i] == '{':
                        brace_count += 1
                    elif source_code[i] == '}':
                        brace_count -= 1
                    i += 1
                
                test_body = source_code[body_start:i]
                
            elif function_match:
                # Regular function - find matching closing brace
                body_start = start_pos + function_match.end() - 1
                brace_count = 1
                i = body_start + 1
                
                while i < len(source_code) and brace_count > 0:
                    if source_code[i] == '{':
                        brace_count += 1
                    elif source_code[i] == '}':
                        brace_count -= 1
                    i += 1
                
                test_body = source_code[body_start:i]
            else:
                # Fallback - use rest of code
                test_body = source_code[start_pos:]
            
            # Extract from test body
            
            # API calls
            api_pattern = r'\.(get|post|put|delete|patch)\s*\('
            for match in re.finditer(api_pattern, test_body):
                signals.api_calls.append(
                    APICall(
                        method=match.group(1).upper(),
                        endpoint=""
                    )
                )
            
            # fetch calls
            fetch_pattern = r'fetch\s*\('
            for match in re.finditer(fetch_pattern, test_body):
                signals.api_calls.append(
                    APICall(
                        method="GET",
                        endpoint=""
                    )
                )
            
            # Playwright/Cypress interactions
            interaction_pattern = r'(?:page|cy)\.(goto|click|fill|type|select|check|visit)\s*\('
            for match in re.finditer(interaction_pattern, test_body):
                signals.ui_interactions.append(match.group(1))
            
            # Assertions
            assertion_pattern = r'(expect|assert|should)\s*\('
            for match in re.finditer(assertion_pattern, test_body):
                signals.assertions.append(
                    Assertion(
                        type="js_assertion",
                        target=match.group(1),
                        expected_value=None
                    )
                )
        
        return signals


class TypeScriptASTExtractor(JavaScriptASTExtractor):
    """
    TypeScript AST extractor (extends JavaScript extractor).
    
    Adds TypeScript-specific features like interfaces, types, decorators.
    """
    
    def supports_language(self) -> str:
        """Return the language this extractor supports."""
        return "typescript"
    
    def extract(self, source_code: str, test_name: str) -> StructuralSignals:
        """
        Extract structural signals from TypeScript test source code.
        
        First attempts TypeScript-aware parsing, then falls back to JavaScript parsing.
        """
        # For now, use JavaScript extraction as base
        # TODO: Add TypeScript-specific parsing with @typescript-eslint/parser
        signals = super().extract(source_code, test_name)
        
        # Extract TypeScript-specific features
        self._extract_typescript_features(source_code, signals)
        
        return signals
    
    def _extract_typescript_features(self, source_code: str, signals: StructuralSignals):
        """Extract TypeScript-specific features like interfaces and types."""
        # Extract interfaces
        interface_pattern = r'interface\s+([A-Z][a-zA-Z0-9]*)'
        for match in re.finditer(interface_pattern, source_code):
            signals.classes.append(f"interface:{match.group(1)}")
        
        # Extract type aliases
        type_pattern = r'type\s+([A-Z][a-zA-Z0-9]*)'
        for match in re.finditer(type_pattern, source_code):
            signals.classes.append(f"type:{match.group(1)}")
        
        # Extract decorators
        decorator_pattern = r'@([a-zA-Z_$][a-zA-Z0-9_$]*)'
        for match in re.finditer(decorator_pattern, source_code):
            signals.fixtures.append(f"@{match.group(1)}")


class JavaScriptASTExtractorFactory:
    """Factory for creating JavaScript/TypeScript AST extractors."""
    
    @staticmethod
    def create(language: str = "javascript") -> ASTExtractor:
        """
        Create a new JavaScript/TypeScript AST extractor instance.
        
        Args:
            language: "javascript" or "typescript"
        """
        if language.lower() in ["typescript", "ts"]:
            return TypeScriptASTExtractor()
        return JavaScriptASTExtractor()
    
    @staticmethod
    def is_available() -> bool:
        """Check if JavaScript AST extraction is available."""
        try:
            import esprima
            return True
        except ImportError:
            logger.warning("esprima library not installed. Install with: pip install esprima")
            return False
