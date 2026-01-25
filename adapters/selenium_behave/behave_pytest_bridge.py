"""
Behave-pytest fixture bridge.

Bridges Behave context to pytest fixtures for hybrid testing.
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
import ast


class BehavePytestBridge:
    """Bridge Behave context to pytest fixtures."""
    
    def __init__(self):
        """Initialize the bridge."""
        self.context_vars = set()
        self.fixtures_generated = []
        
    def extract_context_usage(self, step_file: Path) -> List[Dict]:
        """
        Extract context variable usage from step definitions.
        
        Args:
            step_file: Path to steps file
            
        Returns:
            List of context usage dictionaries
        """
        if not step_file.exists():
            return []
        
        try:
            content = step_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception:
            return []
        
        usages = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id == 'context':
                    var_name = node.attr
                    usages.append({
                        'variable': var_name,
                        'line': node.lineno,
                    })
                    self.context_vars.add(var_name)
        
        return usages
    
    def generate_pytest_fixtures(self, context_vars: List[str]) -> str:
        """
        Generate pytest fixtures from context variables.
        
        Args:
            context_vars: List of context variable names
            
        Returns:
            Python fixture code
        """
        lines = []
        lines.append("import pytest")
        lines.append("from dataclasses import dataclass\n")
        
        # Create a context class
        lines.append("@dataclass")
        lines.append("class TestContext:")
        lines.append('    """Context object for Behave-style testing."""')
        for var in sorted(context_vars):
            lines.append(f"    {var}: Any = None")
        lines.append("")
        
        # Create fixture
        lines.append("@pytest.fixture")
        lines.append("def context():")
        lines.append('    """Behave-style context fixture."""')
        lines.append("    return TestContext()")
        lines.append("")
        
        return '\n'.join(lines)
    
    def convert_step_to_fixture(self, step_func: Dict) -> str:
        """
        Convert Behave step to pytest fixture-based test.
        
        Args:
            step_func: Step function information
            
        Returns:
            Pytest fixture code
        """
        func_name = step_func.get('name', 'test_step')
        
        code = f'''
import pytest

@pytest.fixture
def {func_name}_fixture(context):
    """Fixture for {func_name}."""
    # Original Behave step implementation
    yield context
    # Cleanup if needed
'''
        return code
    
    def create_hybrid_conftest(self, context_vars: List[str]) -> str:
        """
        Create conftest.py for hybrid Behave-pytest setup.
        
        Args:
            context_vars: List of context variables
            
        Returns:
            conftest.py content
        """
        lines = []
        lines.append('"""')
        lines.append("Hybrid Behave-pytest configuration.")
        lines.append("Bridges Behave context to pytest fixtures.")
        lines.append('"""')
        lines.append("")
        lines.append("import pytest")
        lines.append("from typing import Any")
        lines.append("from dataclasses import dataclass, field")
        lines.append("")
        
        # Context class
        lines.append("@dataclass")
        lines.append("class BehaveContext:")
        lines.append('    """Behave-compatible context for pytest."""')
        for var in sorted(context_vars):
            lines.append(f"    {var}: Any = None")
        lines.append("    _cleanup_funcs: list = field(default_factory=list)")
        lines.append("")
        lines.append("    def add_cleanup(self, func):")
        lines.append('        """Add cleanup function."""')
        lines.append("        self._cleanup_funcs.append(func)")
        lines.append("")
        
        # Context fixture
        lines.append("@pytest.fixture(scope='function')")
        lines.append("def context():")
        lines.append('    """Provide Behave-style context."""')
        lines.append("    ctx = BehaveContext()")
        lines.append("    yield ctx")
        lines.append("    # Run cleanup functions")
        lines.append("    for cleanup in ctx._cleanup_funcs:")
        lines.append("        cleanup()")
        lines.append("")
        
        # Behave hooks as fixtures
        lines.append("@pytest.fixture(scope='function', autouse=True)")
        lines.append("def before_scenario(context):")
        lines.append('    """Behave before_scenario hook."""')
        lines.append("    # Initialize scenario context")
        lines.append("    pass")
        lines.append("")
        
        lines.append("@pytest.fixture(scope='session', autouse=True)")
        lines.append("def before_all():")
        lines.append('    """Behave before_all hook."""')
        lines.append("    # Session setup")
        lines.append("    pass")
        lines.append("")
        
        return '\n'.join(lines)
    
    def analyze_behave_project(self, project_path: Path) -> Dict:
        """
        Analyze Behave project for pytest migration.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        step_files = list(project_path.rglob("steps/*.py"))
        step_files.extend(project_path.rglob("*_steps.py"))
        
        all_context_vars = set()
        context_usage_by_file = {}
        
        for step_file in step_files:
            usages = self.extract_context_usage(step_file)
            if usages:
                context_usage_by_file[str(step_file)] = usages
                all_context_vars.update(u['variable'] for u in usages)
        
        return {
            'step_files': len(step_files),
            'context_variables': sorted(all_context_vars),
            'context_usage_by_file': context_usage_by_file,
            'total_context_accesses': sum(len(v) for v in context_usage_by_file.values()),
        }
    
    def generate_migration_guide(self, analysis: Dict) -> str:
        """
        Generate migration guide from Behave to pytest.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown guide
        """
        lines = []
        lines.append("# Behave to Pytest Migration Guide\n")
        
        lines.append("## Context Variables\n")
        lines.append("The following context variables were detected:\n")
        for var in analysis['context_variables']:
            lines.append(f"- `context.{var}`")
        lines.append("")
        
        lines.append("## Migration Steps\n")
        lines.append("1. Create conftest.py with context fixture")
        lines.append("2. Convert step definitions to pytest functions")
        lines.append("3. Replace @given/@when/@then with pytest-bdd decorators")
        lines.append("4. Update context access to use fixture")
        lines.append("5. Convert hooks to pytest fixtures\n")
        
        lines.append("## Example Conversion\n")
        lines.append("**Before (Behave):**")
        lines.append("```python")
        lines.append("@given('I have a user')")
        lines.append("def step_impl(context):")
        lines.append("    context.user = User()")
        lines.append("```\n")
        
        lines.append("**After (pytest-bdd):**")
        lines.append("```python")
        lines.append("from pytest_bdd import given")
        lines.append("")
        lines.append("@given('I have a user')")
        lines.append("def step_impl(context):")
        lines.append("    context.user = User()")
        lines.append("```\n")
        
        return '\n'.join(lines)
