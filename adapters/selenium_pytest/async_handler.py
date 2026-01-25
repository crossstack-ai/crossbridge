"""
Async test support for pytest-asyncio.

Handles discovery and execution of async test functions.
"""

import ast
from typing import List, Dict, Optional, Set
from pathlib import Path


class PytestAsyncTestHandler:
    """Handle pytest-asyncio test detection and transformation."""
    
    def __init__(self):
        self.async_markers = {'asyncio', 'trio', 'anyio'}
        self.async_fixtures = set()
    
    def is_async_test(self, test_function: ast.FunctionDef) -> bool:
        """
        Check if a test function is async.
        
        Args:
            test_function: AST node for test function
            
        Returns:
            True if function is async def
        """
        return isinstance(test_function, ast.AsyncFunctionDef)
    
    def has_async_marker(self, test_function: ast.FunctionDef) -> bool:
        """
        Check if function has async-related pytest markers.
        
        Args:
            test_function: AST node for test function
            
        Returns:
            True if has @pytest.mark.asyncio or similar
        """
        for decorator in test_function.decorator_list:
            if isinstance(decorator, ast.Attribute):
                # @pytest.mark.asyncio
                if isinstance(decorator.value, ast.Attribute):
                    if (decorator.value.attr == 'mark' and 
                        decorator.attr in self.async_markers):
                        return True
            elif isinstance(decorator, ast.Call):
                # @pytest.mark.asyncio(...)
                if isinstance(decorator.func, ast.Attribute):
                    if (decorator.func.attr in self.async_markers or
                        (isinstance(decorator.func.value, ast.Attribute) and
                         decorator.func.value.attr == 'mark')):
                        return True
        
        return False
    
    def extract_async_tests(self, file_path: Path) -> List[Dict]:
        """
        Extract all async tests from a Python file.
        
        Args:
            file_path: Path to Python test file
            
        Returns:
            List of async test metadata
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return []
        
        async_tests = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if it's a test function
                if not node.name.startswith('test_'):
                    continue
                
                is_async = self.is_async_test(node)
                has_marker = self.has_async_marker(node)
                
                if is_async or has_marker:
                    async_tests.append({
                        'name': node.name,
                        'line': node.lineno,
                        'is_async_def': is_async,
                        'has_async_marker': has_marker,
                        'file': str(file_path)
                    })
        
        return async_tests
    
    def detect_async_fixtures(self, file_path: Path) -> Set[str]:
        """
        Detect async fixtures in a conftest.py or test file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Set of async fixture names
        """
        if not file_path.exists():
            return set()
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return set()
        
        async_fixtures = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                # Check for @pytest.fixture decorator
                for decorator in node.decorator_list:
                    if isinstance(decorator, (ast.Name, ast.Attribute)):
                        dec_name = decorator.id if isinstance(decorator, ast.Name) else decorator.attr
                        if dec_name == 'fixture':
                            async_fixtures.add(node.name)
                            break
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, (ast.Name, ast.Attribute)):
                            func_name = (decorator.func.id if isinstance(decorator.func, ast.Name) 
                                       else decorator.func.attr)
                            if func_name == 'fixture':
                                async_fixtures.add(node.name)
                                break
        
        return async_fixtures
    
    def requires_pytest_asyncio(self, project_root: Path) -> bool:
        """
        Check if project requires pytest-asyncio plugin.
        
        Args:
            project_root: Root directory of project
            
        Returns:
            True if any async tests are found
        """
        for test_file in project_root.rglob("test_*.py"):
            async_tests = self.extract_async_tests(test_file)
            if async_tests:
                return True
        
        for test_file in project_root.rglob("*_test.py"):
            async_tests = self.extract_async_tests(test_file)
            if async_tests:
                return True
        
        return False
    
    def get_async_config(self) -> Dict[str, str]:
        """
        Get pytest configuration for async tests.
        
        Returns:
            Dictionary with pytest.ini settings
        """
        return {
            'asyncio_mode': 'auto',
            'asyncio_default_fixture_loop_scope': 'function'
        }
