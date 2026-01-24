"""
AST/ASM Extraction Layer for CrossBridge Intelligent Test Assistance.

Extracts structural signals from test code using AST analysis.
Framework-agnostic through adapter pattern.

Supported Languages:
- Python (via ast module)
- Java (via javalang)
- JavaScript (via esprima or tree-sitter)
"""

import ast
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.intelligence.models import (
    APICall,
    Assertion,
    StructuralSignals,
)

logger = logging.getLogger(__name__)


class ASTExtractor(ABC):
    """
    Abstract base class for language-specific AST extractors.
    
    Each language implementation must extract the same structural signals
    in a normalized format.
    """
    
    @abstractmethod
    def extract(self, source_code: str, test_name: str) -> StructuralSignals:
        """
        Extract structural signals from test source code.
        
        Args:
            source_code: Test source code as string
            test_name: Name of the test function/method
            
        Returns:
            StructuralSignals object with normalized data
        """
        pass
    
    @abstractmethod
    def supports_language(self) -> str:
        """Return the language this extractor supports."""
        pass


class PythonASTExtractor(ASTExtractor):
    """
    Python AST extractor using built-in ast module.
    
    Extracts structural signals from pytest, unittest, and other Python test frameworks.
    """
    
    def __init__(self):
        self.api_patterns = [
            "requests.get",
            "requests.post",
            "requests.put",
            "requests.delete",
            "requests.patch",
            "client.get",
            "client.post",
            "session.get",
            "httpx.get",
        ]
        
        self.assertion_patterns = [
            "assertEqual",
            "assertNotEqual",
            "assertTrue",
            "assertFalse",
            "assertRaises",
            "assertIn",
            "assert",
        ]
    
    def supports_language(self) -> str:
        return "python"
    
    def extract(self, source_code: str, test_name: str) -> StructuralSignals:
        """Extract signals from Python test code."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.error(f"Failed to parse Python code: {e}")
            return StructuralSignals()
        
        # Find the test function
        test_func = self._find_test_function(tree, test_name)
        if not test_func:
            logger.warning(f"Test function {test_name} not found in AST")
            return StructuralSignals()
        
        signals = StructuralSignals()
        
        # Extract API calls
        signals.api_calls = self._extract_api_calls(test_func)
        
        # Extract assertions
        signals.assertions = self._extract_assertions(test_func)
        
        # Extract status codes
        signals.expected_status_codes = self._extract_status_codes(test_func)
        
        # Extract exceptions
        signals.expected_exceptions = self._extract_exceptions(test_func)
        
        # Extract control flow patterns
        signals.has_retry_logic = self._detect_retry_logic(test_func)
        signals.has_timeout = self._detect_timeout(test_func)
        signals.has_async_await = self._detect_async(test_func)
        signals.has_loop = self._detect_loops(test_func)
        signals.has_conditional = self._detect_conditionals(test_func)
        
        # Extract dependencies
        signals.external_services = self._extract_external_services(test_func)
        signals.database_operations = self._extract_db_operations(test_func)
        signals.file_operations = self._extract_file_operations(test_func)
        
        # Extract fixtures (pytest specific)
        signals.fixtures = self._extract_fixtures(test_func)
        
        return signals
    
    def _find_test_function(self, tree: ast.AST, test_name: str) -> Optional[ast.FunctionDef]:
        """Find test function by name in AST."""
        for node in ast.walk(tree):
            # Check for both FunctionDef and AsyncFunctionDef
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_name:
                return node
        return None
    
    def _extract_api_calls(self, func: ast.FunctionDef) -> List[APICall]:
        """Extract API calls from function."""
        api_calls = []
        
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                
                # Match against known API patterns
                if any(pattern in call_name for pattern in self.api_patterns):
                    method, endpoint, status = self._parse_api_call(node, call_name)
                    if method and endpoint:
                        api_calls.append(
                            APICall(
                                method=method,
                                endpoint=endpoint,
                                expected_status=status,
                            )
                        )
        
        return api_calls
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Get the full name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""
    
    def _parse_api_call(self, node: ast.Call, call_name: str) -> tuple:
        """Parse API call details from AST node."""
        method = "GET"  # Default
        endpoint = None
        status = None
        
        # Extract method from call name
        if "get" in call_name.lower():
            method = "GET"
        elif "post" in call_name.lower():
            method = "POST"
        elif "put" in call_name.lower():
            method = "PUT"
        elif "delete" in call_name.lower():
            method = "DELETE"
        elif "patch" in call_name.lower():
            method = "PATCH"
        
        # Extract endpoint from first argument (usually a string)
        if node.args and isinstance(node.args[0], ast.Constant):
            endpoint = node.args[0].value
        elif node.args and hasattr(ast, 'Str') and isinstance(node.args[0], ast.Str):  # Python < 3.8
            endpoint = node.args[0].s
        
        return method, endpoint, status
    
    def _extract_assertions(self, func: ast.FunctionDef) -> List[Assertion]:
        """Extract assertion statements."""
        assertions = []
        
        for node in ast.walk(func):
            # Plain assert statements
            if isinstance(node, ast.Assert):
                assertion = self._parse_assert(node)
                if assertion:
                    assertions.append(assertion)
            
            # unittest assertions (assertEqual, etc.)
            elif isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if any(pattern in call_name for pattern in self.assertion_patterns):
                    assertion = self._parse_assertion_call(node, call_name)
                    if assertion:
                        assertions.append(assertion)
        
        return assertions
    
    def _parse_assert(self, node: ast.Assert) -> Optional[Assertion]:
        """Parse plain assert statement."""
        if isinstance(node.test, ast.Compare):
            target = ast.unparse(node.test.left) if hasattr(ast, 'unparse') else "unknown"
            comparator = self._get_comparator(node.test.ops[0])
            expected = ast.unparse(node.test.comparators[0]) if hasattr(ast, 'unparse') else None
            
            return Assertion(
                type="assert",
                target=target,
                expected_value=expected,
                comparator=comparator,
            )
        return None
    
    def _get_comparator(self, op: ast.cmpop) -> str:
        """Get string representation of comparison operator."""
        if isinstance(op, ast.Eq):
            return "=="
        elif isinstance(op, ast.NotEq):
            return "!="
        elif isinstance(op, ast.Lt):
            return "<"
        elif isinstance(op, ast.LtE):
            return "<="
        elif isinstance(op, ast.Gt):
            return ">"
        elif isinstance(op, ast.GtE):
            return ">="
        elif isinstance(op, ast.In):
            return "in"
        elif isinstance(op, ast.NotIn):
            return "not in"
        return "=="
    
    def _parse_assertion_call(self, node: ast.Call, call_name: str) -> Optional[Assertion]:
        """Parse unittest-style assertion method call."""
        if len(node.args) >= 1:
            target = ast.unparse(node.args[0]) if hasattr(ast, 'unparse') else "unknown"
            expected = ast.unparse(node.args[1]) if len(node.args) > 1 and hasattr(ast, 'unparse') else None
            
            return Assertion(
                type=call_name,
                target=target,
                expected_value=expected,
            )
        return None
    
    def _extract_status_codes(self, func: ast.FunctionDef) -> List[int]:
        """Extract expected HTTP status codes."""
        codes = []
        
        for node in ast.walk(func):
            # Look for comparisons with status codes (200, 404, etc.)
            if isinstance(node, ast.Compare):
                for comp in node.comparators:
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, int):
                        if 100 <= comp.value < 600:  # Valid HTTP status code range
                            codes.append(comp.value)
        
        return list(set(codes))  # Unique codes
    
    def _extract_exceptions(self, func: ast.FunctionDef) -> List[str]:
        """Extract expected exceptions."""
        exceptions = []
        
        for node in ast.walk(func):
            # pytest.raises(Exception)
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if "raises" in call_name and node.args:
                    if isinstance(node.args[0], ast.Name):
                        exceptions.append(node.args[0].id)
            
            # with pytest.raises(Exception):
            elif isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call):
                        call_name = self._get_call_name(item.context_expr)
                        if "raises" in call_name and item.context_expr.args:
                            if isinstance(item.context_expr.args[0], ast.Name):
                                exceptions.append(item.context_expr.args[0].id)
        
        return exceptions
    
    def _detect_retry_logic(self, func: ast.FunctionDef) -> bool:
        """Detect retry/repeat patterns."""
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if any(keyword in call_name.lower() for keyword in ["retry", "repeat", "attempt"]):
                    return True
            # Look for decorators with retry
            if hasattr(func, 'decorator_list'):
                for dec in func.decorator_list:
                    if isinstance(dec, ast.Name) and "retry" in dec.id.lower():
                        return True
        return False
    
    def _detect_timeout(self, func: ast.FunctionDef) -> bool:
        """Detect timeout patterns."""
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                # Check for timeout in kwargs
                for keyword in node.keywords:
                    if keyword.arg == "timeout":
                        return True
            # Check decorators
            if hasattr(func, 'decorator_list'):
                for dec in func.decorator_list:
                    if isinstance(dec, ast.Call):
                        call_name = self._get_call_name(dec)
                        if "timeout" in call_name.lower():
                            return True
        return False
    
    def _detect_async(self, func: ast.FunctionDef) -> bool:
        """Detect async/await patterns."""
        # Check if function itself is async
        if isinstance(func, ast.AsyncFunctionDef):
            return True
        
        # Check for await expressions in function body
        for node in ast.walk(func):
            if isinstance(node, ast.Await):
                return True
        
        return False
    
    def _detect_loops(self, func: ast.FunctionDef) -> bool:
        """Detect loop constructs."""
        for node in ast.walk(func):
            if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
                return True
        return False
    
    def _detect_conditionals(self, func: ast.FunctionDef) -> bool:
        """Detect conditional logic."""
        for node in ast.walk(func):
            if isinstance(node, ast.If):
                return True
        return False
    
    def _extract_external_services(self, func: ast.FunctionDef) -> List[str]:
        """Extract external service dependencies."""
        services = []
        
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                # Common service patterns
                if any(svc in call_name.lower() for svc in ["redis", "kafka", "rabbitmq", "mqtt", "grpc"]):
                    services.append(call_name.split(".")[0])
        
        return list(set(services))
    
    def _extract_db_operations(self, func: ast.FunctionDef) -> List[str]:
        """Extract database operations."""
        operations = []
        
        db_keywords = ["select", "insert", "update", "delete", "execute", "query", "commit", "rollback"]
        
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node).lower()
                for keyword in db_keywords:
                    if keyword in call_name:
                        operations.append(keyword.upper())
                        break
        
        return list(set(operations))
    
    def _extract_file_operations(self, func: ast.FunctionDef) -> List[str]:
        """Extract file operations."""
        operations = []
        
        file_keywords = ["open", "read", "write", "close", "remove", "exists"]
        
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node).lower()
                for keyword in file_keywords:
                    if keyword in call_name:
                        operations.append(keyword)
                        break
        
        return list(set(operations))
    
    def _extract_fixtures(self, func: ast.FunctionDef) -> List[str]:
        """Extract pytest fixtures from function parameters."""
        fixtures = []
        
        if hasattr(func, 'args') and func.args.args:
            for arg in func.args.args:
                if arg.arg != "self":  # Skip self parameter
                    fixtures.append(arg.arg)
        
        return fixtures


class ASTExtractorFactory:
    """Factory for creating language-specific AST extractors."""
    
    _extractors = {
        "python": PythonASTExtractor,
        # Future: JavaASTExtractor, JavaScriptASTExtractor, etc.
    }
    
    @classmethod
    def get_extractor(cls, language: str) -> Optional[ASTExtractor]:
        """Get AST extractor for language."""
        extractor_class = cls._extractors.get(language.lower())
        if extractor_class:
            return extractor_class()
        return None
    
    @classmethod
    def register_extractor(cls, language: str, extractor_class: type):
        """Register a new AST extractor."""
        cls._extractors[language.lower()] = extractor_class


def extract_from_file(file_path: str, test_name: str, language: str = "python") -> StructuralSignals:
    """
    Extract structural signals from a test file.
    
    Args:
        file_path: Path to test file
        test_name: Name of test function/method
        language: Programming language (python, java, javascript)
        
    Returns:
        StructuralSignals object
    """
    extractor = ASTExtractorFactory.get_extractor(language)
    if not extractor:
        logger.error(f"No AST extractor available for language: {language}")
        return StructuralSignals()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        return extractor.extract(source_code, test_name)
    
    except Exception as e:
        logger.error(f"Failed to extract from {file_path}: {e}")
        return StructuralSignals()
