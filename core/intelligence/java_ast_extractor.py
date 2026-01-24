"""
Java AST Extractor for CrossBridge Intelligent Test Assistance.

Extracts structural signals from Java test code using javalang library.
Supports JUnit, TestNG, RestAssured, and Selenium Java tests.
"""

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


class JavaASTExtractor(ASTExtractor):
    """
    Java AST extractor using javalang library.
    
    Extracts structural signals from Java test code including:
    - Imports
    - Classes and methods
    - Annotations (@Test, @Before, @After)
    - API calls (RestAssured, HTTP clients)
    - Assertions (JUnit, TestNG, AssertJ)
    - UI interactions (Selenium WebDriver)
    """
    
    def supports_language(self) -> str:
        """Return the language this extractor supports."""
        return "java"
    
    def extract(self, source_code: str, test_name: str) -> StructuralSignals:
        """
        Extract structural signals from Java test source code.
        
        Args:
            source_code: Java test source code as string
            test_name: Name of the test method
            
        Returns:
            StructuralSignals object with normalized data
        """
        try:
            # Try to use javalang for proper AST parsing
            import javalang
            return self._extract_with_javalang(source_code, test_name)
        except ImportError:
            logger.warning("javalang not installed, falling back to regex extraction")
            return self._extract_with_regex(source_code, test_name)
        except Exception as e:
            logger.error(f"Java AST extraction failed: {e}")
            return self._extract_with_regex(source_code, test_name)
    
    def _extract_with_javalang(self, source_code: str, test_name: str) -> StructuralSignals:
        """Extract using javalang library for proper AST parsing."""
        import javalang
        
        try:
            tree = javalang.parse.parse(source_code)
        except Exception as e:
            logger.error(f"Failed to parse Java code: {e}")
            return self._extract_with_regex(source_code, test_name)
        
        signals = StructuralSignals()
        
        # Extract imports
        for imp in tree.imports:
            if imp.path:
                signals.imports.append(imp.path)
        
        # Extract classes and methods
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            signals.classes.append(node.name)
            
            # Extract methods
            for method in node.methods:
                signals.functions.append(method.name)
                
                # Check if this is our test method
                if method.name == test_name:
                    # Extract annotations
                    if method.annotations:
                        for annotation in method.annotations:
                            if annotation.name in ['Test', 'Before', 'After', 'BeforeClass', 'AfterClass']:
                                signals.fixtures.append(f"@{annotation.name}")
                    
                    # Extract method body for API calls and assertions
                    if method.body:
                        self._extract_method_body(method.body, signals)
        
        return signals
    
    def _extract_method_body(self, statements, signals: StructuralSignals):
        """Extract API calls and assertions from method body."""
        import javalang
        
        for statement in statements:
            # Look for method invocations
            for path, node in javalang.tree.filter(javalang.tree.MethodInvocation):
                method_name = node.member if hasattr(node, 'member') else None
                
                if method_name:
                    # Check for assertions
                    if method_name.startswith('assert') or method_name in ['assertEquals', 'assertTrue', 'assertFalse', 'assertNotNull']:
                        signals.assertions.append(
                            Assertion(
                                type="java_assertion",
                                target=method_name,
                                expected_value=None
                            )
                        )
                    
                    # Check for HTTP/API calls
                    if method_name in ['get', 'post', 'put', 'delete', 'patch']:
                        signals.api_calls.append(
                            APICall(
                                method=method_name.upper(),
                                endpoint=""
                            )
                        )
    
    def _extract_with_regex(self, source_code: str, test_name: str) -> StructuralSignals:
        """Fallback regex-based extraction when javalang is not available."""
        signals = StructuralSignals()
        
        # Extract imports
        import_pattern = r'import\s+(static\s+)?([a-zA-Z0-9_.]+);'
        for match in re.finditer(import_pattern, source_code):
            signals.imports.append(match.group(2))
        
        # Extract class names
        class_pattern = r'(?:public\s+)?class\s+([A-Z][a-zA-Z0-9]*)'
        for match in re.finditer(class_pattern, source_code):
            signals.classes.append(match.group(1))
        
        # Extract method names
        method_pattern = r'(?:public|private|protected)\s+(?:static\s+)?(?:void|[A-Z][a-zA-Z0-9<>]*)\s+([a-z][a-zA-Z0-9]*)\s*\('
        for match in re.finditer(method_pattern, source_code):
            signals.functions.append(match.group(1))
        
        # Extract test method body
        test_method_pattern = rf'@Test.*?(?:public|private)\s+(?:void|[A-Z][a-zA-Z0-9<>]*)\s+{test_name}\s*\([^)]*\)\s*\{{(.*?)\}}'
        test_match = re.search(test_method_pattern, source_code, re.DOTALL)
        
        if test_match:
            method_body = test_match.group(1)
            
            # Extract annotations
            annotation_pattern = r'@(Test|Before|After|BeforeClass|AfterClass)'
            for match in re.finditer(annotation_pattern, source_code):
                signals.fixtures.append(f"@{match.group(1)}")
            
            # Extract assertions
            assertion_pattern = r'assert(Equals|True|False|NotNull|Null|That|Same)\s*\('
            for match in re.finditer(assertion_pattern, method_body):
                signals.assertions.append(
                    Assertion(
                        type="java_assertion",
                        target=f"assert{match.group(1)}",
                        expected_value=None
                    )
                )
            
            # Extract RestAssured API calls
            rest_pattern = r'\.(get|post|put|delete|patch)\s*\('
            for match in re.finditer(rest_pattern, method_body):
                signals.api_calls.append(
                    APICall(
                        method=match.group(1).upper(),
                        endpoint=""
                    )
                )
            
            # Extract HTTP client calls
            http_pattern = r'\.execute\(new\s+(Get|Post|Put|Delete|Patch)'
            for match in re.finditer(http_pattern, method_body):
                signals.api_calls.append(
                    APICall(
                        method=match.group(1).upper(),
                        endpoint=""
                    )
                )
            
            # Extract Selenium WebDriver calls
            selenium_pattern = r'\.(findElement|click|sendKeys|getText|getAttribute)\s*\('
            for match in re.finditer(selenium_pattern, method_body):
                signals.ui_interactions.append(match.group(1))
        
        return signals


class JavaASTExtractorFactory:
    """Factory for creating Java AST extractors."""
    
    @staticmethod
    def create() -> JavaASTExtractor:
        """Create a new Java AST extractor instance."""
        return JavaASTExtractor()
    
    @staticmethod
    def is_available() -> bool:
        """Check if Java AST extraction is available."""
        try:
            import javalang
            return True
        except ImportError:
            logger.warning("javalang library not installed. Install with: pip install javalang")
            return False
