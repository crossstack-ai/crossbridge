"""
Indirect fixture support for pytest.

Handles fixtures with indirect=True parameterization.
"""

import ast
from typing import List, Dict, Optional, Set
from pathlib import Path
from dataclasses import dataclass


@dataclass
class IndirectFixture:
    """Represents an indirectly parametrized fixture."""
    fixture_name: str
    param_values: List[any]
    indirect_params: List[str]
    test_function: str


class PytestIndirectFixtureExtractor:
    """Extract and handle indirect fixtures from pytest tests."""
    
    def __init__(self):
        self.fixtures = {}
    
    def extract_indirect_parametrize(
        self,
        test_function: ast.FunctionDef
    ) -> Optional[IndirectFixture]:
        """
        Extract indirect parametrize decorator from a test function.
        
        Args:
            test_function: AST node for test function
            
        Returns:
            IndirectFixture object or None
        """
        for decorator in test_function.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            
            # Check if it's pytest.mark.parametrize
            if not self._is_parametrize_decorator(decorator):
                continue
            
            # Extract indirect parameter
            indirect = self._extract_indirect_param(decorator)
            if not indirect:
                continue
            
            # Extract fixture names and values
            fixture_names = self._extract_fixture_names(decorator)
            param_values = self._extract_param_values(decorator)
            
            # Determine which fixtures are indirect
            indirect_list = self._resolve_indirect(indirect, fixture_names)
            
            if indirect_list:
                return IndirectFixture(
                    fixture_name=fixture_names[0] if fixture_names else 'unknown',
                    param_values=param_values,
                    indirect_params=indirect_list,
                    test_function=test_function.name
                )
        
        return None
    
    def _is_parametrize_decorator(self, decorator: ast.Call) -> bool:
        """Check if decorator is pytest.mark.parametrize."""
        func = decorator.func
        
        # @pytest.mark.parametrize
        if isinstance(func, ast.Attribute):
            if (isinstance(func.value, ast.Attribute) and
                func.value.attr == 'mark' and
                func.attr == 'parametrize'):
                return True
        
        # @parametrize (imported directly)
        if isinstance(func, ast.Name) and func.id == 'parametrize':
            return True
        
        return False
    
    def _extract_indirect_param(self, decorator: ast.Call) -> Optional[any]:
        """Extract the indirect parameter value."""
        # Check keyword arguments
        for keyword in decorator.keywords:
            if keyword.arg == 'indirect':
                # Can be True, False, or a list of fixture names
                if isinstance(keyword.value, ast.Constant):
                    return keyword.value.value
                elif isinstance(keyword.value, ast.List):
                    return [
                        elt.value if isinstance(elt, ast.Constant) else str(elt.id)
                        for elt in keyword.value.elts
                    ]
        
        return None
    
    def _extract_fixture_names(self, decorator: ast.Call) -> List[str]:
        """Extract fixture names from parametrize decorator."""
        if not decorator.args:
            return []
        
        first_arg = decorator.args[0]
        
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            # Single string: "fixture1,fixture2" or "fixture1"
            return [name.strip() for name in first_arg.value.split(',')]
        elif isinstance(first_arg, ast.List):
            # List of strings: ["fixture1", "fixture2"]
            return [
                elt.value if isinstance(elt, ast.Constant) else str(elt.id)
                for elt in first_arg.elts
            ]
        
        return []
    
    def _extract_param_values(self, decorator: ast.Call) -> List[any]:
        """Extract parameter values from parametrize decorator."""
        if len(decorator.args) < 2:
            return []
        
        second_arg = decorator.args[1]
        
        if isinstance(second_arg, ast.List):
            # List of values
            values = []
            for elt in second_arg.elts:
                if isinstance(elt, ast.Constant):
                    values.append(elt.value)
                elif isinstance(elt, ast.Tuple):
                    # Tuple of values
                    tuple_values = [
                        e.value if isinstance(e, ast.Constant) else None
                        for e in elt.elts
                    ]
                    values.append(tuple(tuple_values))
                else:
                    values.append(None)
            return values
        
        return []
    
    def _resolve_indirect(
        self,
        indirect: any,
        fixture_names: List[str]
    ) -> List[str]:
        """Resolve which fixtures are indirect."""
        if indirect is True:
            # All fixtures are indirect
            return fixture_names
        elif indirect is False:
            return []
        elif isinstance(indirect, list):
            # Specific fixtures are indirect
            return [name for name in indirect if name in fixture_names]
        else:
            return []
    
    def extract_from_file(self, test_file: Path) -> List[IndirectFixture]:
        """
        Extract all indirect fixtures from a test file.
        
        Args:
            test_file: Path to Python test file
            
        Returns:
            List of IndirectFixture objects
        """
        if not test_file.exists():
            return []
        
        try:
            content = test_file.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(test_file))
        except SyntaxError:
            return []
        
        indirect_fixtures = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    indirect = self.extract_indirect_parametrize(node)
                    if indirect:
                        indirect_fixtures.append(indirect)
        
        return indirect_fixtures
    
    def requires_fixture_transformation(
        self,
        indirect_fixture: IndirectFixture
    ) -> bool:
        """
        Check if indirect fixture requires special transformation.
        
        Args:
            indirect_fixture: IndirectFixture object
            
        Returns:
            True if transformation needed
        """
        # Indirect fixtures need special handling in migration
        return len(indirect_fixture.indirect_params) > 0
