"""
Autouse fixture chain handler for pytest.

Handles complex autouse=True fixture chains and dependencies.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import ast
import re


class AutouseFixtureChainHandler:
    """Handle autouse fixture chains in pytest."""
    
    def __init__(self):
        """Initialize the autouse chain handler."""
        self.fixture_graph = {}
        self.autouse_fixtures = set()
        
    def is_autouse_fixture(self, node: ast.FunctionDef) -> bool:
        """
        Check if a function is an autouse fixture.
        
        Args:
            node: AST function node
            
        Returns:
            True if autouse fixture
        """
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == 'fixture':
                        # Check for autouse=True
                        for keyword in decorator.keywords:
                            if keyword.arg == 'autouse' and isinstance(keyword.value, ast.Constant):
                                if keyword.value.value is True:
                                    return True
        return False
    
    def get_fixture_scope(self, node: ast.FunctionDef) -> str:
        """
        Get the scope of a fixture.
        
        Args:
            node: AST function node
            
        Returns:
            Scope string ('function', 'class', 'module', 'session')
        """
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                for keyword in decorator.keywords:
                    if keyword.arg == 'scope':
                        if isinstance(keyword.value, ast.Constant):
                            return keyword.value.value
        return 'function'
    
    def get_fixture_dependencies(self, node: ast.FunctionDef) -> List[str]:
        """
        Get fixture dependencies from function parameters.
        
        Args:
            node: AST function node
            
        Returns:
            List of fixture names
        """
        dependencies = []
        for arg in node.args.args:
            if arg.arg != 'request':  # Skip pytest request
                dependencies.append(arg.arg)
        return dependencies
    
    def extract_autouse_fixtures(self, file_path: Path) -> List[Dict]:
        """
        Extract all autouse fixtures from a file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            List of autouse fixture dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []
        
        autouse_fixtures = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self.is_autouse_fixture(node):
                    fixture_info = {
                        'name': node.name,
                        'scope': self.get_fixture_scope(node),
                        'dependencies': self.get_fixture_dependencies(node),
                        'line': node.lineno,
                        'file': str(file_path),
                    }
                    
                    # Check for yield vs return
                    has_yield = any(isinstance(n, ast.Yield) or isinstance(n, ast.YieldFrom) 
                                   for n in ast.walk(node))
                    fixture_info['is_generator'] = has_yield
                    
                    autouse_fixtures.append(fixture_info)
                    self.autouse_fixtures.add(node.name)
        
        return autouse_fixtures
    
    def build_dependency_graph(self, fixtures: List[Dict]) -> Dict[str, Set[str]]:
        """
        Build dependency graph from fixtures.
        
        Args:
            fixtures: List of fixture dictionaries
            
        Returns:
            Dictionary mapping fixture names to their dependencies
        """
        graph = {}
        
        for fixture in fixtures:
            name = fixture['name']
            dependencies = set(fixture['dependencies'])
            graph[name] = dependencies
        
        self.fixture_graph = graph
        return graph
    
    def get_execution_order(self, fixtures: List[Dict]) -> List[str]:
        """
        Get execution order of autouse fixtures based on scope and dependencies.
        
        Args:
            fixtures: List of fixture dictionaries
            
        Returns:
            Ordered list of fixture names
        """
        # Build dependency graph
        graph = self.build_dependency_graph(fixtures)
        
        # Sort by scope hierarchy
        scope_order = {'session': 0, 'package': 1, 'module': 2, 'class': 3, 'function': 4}
        
        # Group by scope
        scope_groups = {}
        for fixture in fixtures:
            scope = fixture['scope']
            if scope not in scope_groups:
                scope_groups[scope] = []
            scope_groups[scope].append(fixture)
        
        # Topological sort within each scope
        ordered = []
        for scope in ['session', 'package', 'module', 'class', 'function']:
            if scope in scope_groups:
                scope_fixtures = scope_groups[scope]
                sorted_fixtures = self._topological_sort([f['name'] for f in scope_fixtures], graph)
                ordered.extend(sorted_fixtures)
        
        return ordered
    
    def _topological_sort(self, fixtures: List[str], graph: Dict[str, Set[str]]) -> List[str]:
        """
        Perform topological sort on fixtures.
        
        Args:
            fixtures: List of fixture names
            graph: Dependency graph
            
        Returns:
            Sorted list of fixture names
        """
        visited = set()
        stack = []
        
        def visit(name):
            if name in visited:
                return
            visited.add(name)
            
            if name in graph:
                for dep in graph[name]:
                    if dep in fixtures:
                        visit(dep)
            
            stack.append(name)
        
        for fixture in fixtures:
            visit(fixture)
        
        return stack
    
    def detect_circular_dependencies(self, fixtures: List[Dict]) -> List[List[str]]:
        """
        Detect circular dependencies in fixture chains.
        
        Args:
            fixtures: List of fixture dictionaries
            
        Returns:
            List of circular dependency chains
        """
        graph = self.build_dependency_graph(fixtures)
        cycles = []
        
        def dfs(node, path, visited):
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            if node in graph:
                for neighbor in graph[node]:
                    dfs(neighbor, path[:], visited)
        
        for fixture in fixtures:
            dfs(fixture['name'], [], set())
        
        return cycles
    
    def extract_all_autouse_fixtures(self, project_path: Path) -> Dict:
        """
        Extract all autouse fixtures from a project.
        
        Args:
            project_path: Root path of project
            
        Returns:
            Dictionary with all autouse fixture information
        """
        # Find conftest.py files and test files
        conftest_files = list(project_path.rglob("conftest.py"))
        test_files = list(project_path.rglob("test_*.py"))
        all_files = conftest_files + test_files
        
        all_fixtures = []
        for file_path in all_files:
            fixtures = self.extract_autouse_fixtures(file_path)
            all_fixtures.extend(fixtures)
        
        # Build execution order
        execution_order = self.get_execution_order(all_fixtures)
        
        # Detect circular dependencies
        circular_deps = self.detect_circular_dependencies(all_fixtures)
        
        # Group by scope
        by_scope = {}
        for fixture in all_fixtures:
            scope = fixture['scope']
            if scope not in by_scope:
                by_scope[scope] = []
            by_scope[scope].append(fixture)
        
        return {
            'fixtures': all_fixtures,
            'execution_order': execution_order,
            'circular_dependencies': circular_deps,
            'by_scope': by_scope,
            'total_autouse_fixtures': len(all_fixtures),
        }
    
    def generate_fixture_diagram(self, fixtures: List[Dict]) -> str:
        """
        Generate a text diagram of fixture dependencies.
        
        Args:
            fixtures: List of fixture dictionaries
            
        Returns:
            Text diagram string
        """
        lines = []
        lines.append("Autouse Fixture Dependency Chain:")
        lines.append("=" * 50)
        
        graph = self.build_dependency_graph(fixtures)
        order = self.get_execution_order(fixtures)
        
        for i, fixture_name in enumerate(order, 1):
            fixture = next((f for f in fixtures if f['name'] == fixture_name), None)
            if not fixture:
                continue
            
            scope = fixture['scope']
            deps = graph.get(fixture_name, set())
            
            lines.append(f"\n{i}. {fixture_name} (scope: {scope})")
            if deps:
                lines.append(f"   Dependencies: {', '.join(deps)}")
            else:
                lines.append("   No dependencies")
        
        return '\n'.join(lines)
    
    def convert_to_setup_teardown(self, fixture: Dict) -> str:
        """
        Convert an autouse fixture to setup/teardown methods.
        
        Args:
            fixture: Fixture dictionary
            
        Returns:
            Python code string
        """
        name = fixture['name']
        scope = fixture['scope']
        is_generator = fixture.get('is_generator', False)
        
        if scope == 'function':
            if is_generator:
                return f"""
def setup_method(self):
    \"\"\"Setup from {name} fixture.\"\"\"
    # Setup code from {name}
    pass

def teardown_method(self):
    \"\"\"Teardown from {name} fixture.\"\"\"
    # Teardown code from {name}
    pass
"""
            else:
                return f"""
def setup_method(self):
    \"\"\"Setup from {name} fixture.\"\"\"
    # Code from {name}
    pass
"""
        
        elif scope == 'class':
            if is_generator:
                return f"""
@classmethod
def setup_class(cls):
    \"\"\"Setup from {name} fixture.\"\"\"
    # Setup code from {name}
    pass

@classmethod
def teardown_class(cls):
    \"\"\"Teardown from {name} fixture.\"\"\"
    # Teardown code from {name}
    pass
"""
            else:
                return f"""
@classmethod
def setup_class(cls):
    \"\"\"Setup from {name} fixture.\"\"\"
    # Code from {name}
    pass
"""
        
        elif scope == 'module':
            if is_generator:
                return f"""
def setup_module():
    \"\"\"Setup from {name} fixture.\"\"\"
    # Setup code from {name}
    pass

def teardown_module():
    \"\"\"Teardown from {name} fixture.\"\"\"
    # Teardown code from {name}
    pass
"""
            else:
                return f"""
def setup_module():
    \"\"\"Setup from {name} fixture.\"\"\"
    # Code from {name}
    pass
"""
        
        return ""
