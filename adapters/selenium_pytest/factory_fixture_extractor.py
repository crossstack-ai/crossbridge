"""
Factory fixture extraction and handling for pytest.

Supports fixtures that return callable factories.
"""

import ast
from typing import List, Dict, Optional, Callable
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FactoryFixture:
    """Represents a factory fixture that returns a callable."""
    name: str
    return_type: Optional[str]
    factory_function: str
    parameters: List[str]
    file_path: Path


class PytestFactoryFixtureExtractor:
    """Extract factory fixtures from pytest test files."""
    
    def __init__(self):
        self.factory_patterns = ['make_', 'create_', 'build_', '_factory']
    
    def is_factory_fixture(self, fixture_func: ast.FunctionDef) -> bool:
        """
        Check if a fixture returns a callable (factory pattern).
        
        Args:
            fixture_func: AST node for fixture function
            
        Returns:
            True if fixture is a factory
        """
        # Check for factory naming patterns
        for pattern in self.factory_patterns:
            if pattern in fixture_func.name.lower():
                return True
        
        # Check if function returns another function
        for node in ast.walk(fixture_func):
            if isinstance(node, ast.Return):
                # Check if returning a function definition
                if isinstance(node.value, (ast.Lambda, ast.Name)):
                    return True
                # Check if returning a function call that returns a function
                if isinstance(node.value, ast.Call):
                    return True
        
        # Check for nested function definitions (inner functions)
        has_inner_function = False
        for node in fixture_func.body:
            if isinstance(node, ast.FunctionDef):
                has_inner_function = True
                break
        
        return has_inner_function
    
    def extract_factory_fixture(
        self,
        fixture_func: ast.FunctionDef,
        file_path: Path
    ) -> Optional[FactoryFixture]:
        """
        Extract factory fixture details.
        
        Args:
            fixture_func: AST node for fixture function
            file_path: Path to source file
            
        Returns:
            FactoryFixture object or None
        """
        if not self.is_factory_fixture(fixture_func):
            return None
        
        # Extract factory function name (inner function)
        factory_name = None
        for node in fixture_func.body:
            if isinstance(node, ast.FunctionDef):
                factory_name = node.name
                break
        
        # Extract parameters
        params = [arg.arg for arg in fixture_func.args.args]
        
        # Try to determine return type from type hints
        return_type = None
        if fixture_func.returns:
            if isinstance(fixture_func.returns, ast.Name):
                return_type = fixture_func.returns.id
            elif isinstance(fixture_func.returns, ast.Subscript):
                # Callable[[...], ReturnType]
                if isinstance(fixture_func.returns.value, ast.Name):
                    return_type = f"Callable[{fixture_func.returns.slice}]"
        
        return FactoryFixture(
            name=fixture_func.name,
            return_type=return_type,
            factory_function=factory_name or 'anonymous',
            parameters=params,
            file_path=file_path
        )
    
    def extract_from_file(self, test_file: Path) -> List[FactoryFixture]:
        """
        Extract all factory fixtures from a file.
        
        Args:
            test_file: Path to Python file
            
        Returns:
            List of FactoryFixture objects
        """
        if not test_file.exists():
            return []
        
        try:
            content = test_file.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(test_file))
        except SyntaxError:
            return []
        
        factory_fixtures = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if decorated with @pytest.fixture
                is_fixture = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, (ast.Name, ast.Attribute)):
                        dec_name = (decorator.id if isinstance(decorator, ast.Name) 
                                  else decorator.attr)
                        if dec_name == 'fixture':
                            is_fixture = True
                            break
                    elif isinstance(decorator, ast.Call):
                        func = decorator.func
                        func_name = (func.id if isinstance(func, ast.Name)
                                   else func.attr if isinstance(func, ast.Attribute)
                                   else None)
                        if func_name == 'fixture':
                            is_fixture = True
                            break
                
                if is_fixture:
                    factory = self.extract_factory_fixture(node, test_file)
                    if factory:
                        factory_fixtures.append(factory)
        
        return factory_fixtures
    
    def get_factory_usage_pattern(
        self,
        factory: FactoryFixture
    ) -> str:
        """
        Generate usage pattern for a factory fixture.
        
        Args:
            factory: FactoryFixture object
            
        Returns:
            Usage pattern string
        """
        return (
            f"# Factory fixture: {factory.name}\n"
            f"def test_example({factory.name}):\n"
            f"    # Call factory to create instance\n"
            f"    instance = {factory.name}()\n"
            f"    # Use instance...\n"
        )
    
    def convert_to_robot_keyword(
        self,
        factory: FactoryFixture
    ) -> List[str]:
        """
        Convert factory fixture to Robot Framework keyword.
        
        Args:
            factory: FactoryFixture object
            
        Returns:
            List of Robot keyword lines
        """
        keywords = [
            f"*** Keywords ***",
            f"{factory.name.replace('_', ' ').title()}",
            f"    [Arguments]    @{{args}}",
            f"    # Factory pattern - create and return instance",
            f"    ${{instance}}=    Create {factory.factory_function.title()}    @{{args}}",
            f"    [Return]    ${{instance}}",
            ""
        ]
        return keywords
