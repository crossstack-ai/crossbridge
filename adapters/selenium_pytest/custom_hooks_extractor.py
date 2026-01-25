"""
Custom pytest hooks extractor.

Handles pytest_configure, pytest_collection_modifyitems, and other hooks.
"""

from typing import List, Dict, Optional
from pathlib import Path
import ast
import re


class CustomHooksExtractor:
    """Extract custom pytest hooks from conftest files."""
    
    PYTEST_HOOKS = [
        'pytest_configure', 'pytest_unconfigure',
        'pytest_sessionstart', 'pytest_sessionfinish',
        'pytest_collection', 'pytest_collection_modifyitems', 'pytest_collection_finish',
        'pytest_runtest_setup', 'pytest_runtest_call', 'pytest_runtest_teardown',
        'pytest_runtest_makereport', 'pytest_runtest_logreport',
        'pytest_fixture_setup', 'pytest_fixture_post_finalizer',
        'pytest_addoption', 'pytest_cmdline_main', 'pytest_cmdline_parse',
        'pytest_generate_tests', 'pytest_make_parametrize_id',
        'pytest_itemcollected', 'pytest_deselected',
        'pytest_report_header', 'pytest_report_collectionfinish',
        'pytest_assertrepr_compare',
    ]
    
    def __init__(self):
        """Initialize the hooks extractor."""
        self.hooks = {}
        
    def is_pytest_hook(self, func_name: str) -> bool:
        """
        Check if a function is a pytest hook.
        
        Args:
            func_name: Function name
            
        Returns:
            True if pytest hook
        """
        return func_name in self.PYTEST_HOOKS
    
    def extract_hook_info(self, node: ast.FunctionDef, file_path: Path) -> Dict:
        """
        Extract information about a pytest hook.
        
        Args:
            node: AST function node
            file_path: Source file path
            
        Returns:
            Hook information dictionary
        """
        hook_info = {
            'name': node.name,
            'file': str(file_path),
            'line': node.lineno,
            'parameters': [],
            'decorators': [],
            'docstring': ast.get_docstring(node),
        }
        
        # Extract parameters
        for arg in node.args.args:
            hook_info['parameters'].append(arg.arg)
        
        # Extract decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                hook_info['decorators'].append(decorator.id)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    hook_info['decorators'].append(decorator.func.id)
        
        # Detect hookimpl decorator
        hook_info['is_hookimpl'] = any('hookimpl' in str(d) for d in hook_info['decorators'])
        
        return hook_info
    
    def extract_hooks_from_file(self, file_path: Path) -> List[Dict]:
        """
        Extract all pytest hooks from a file.
        
        Args:
            file_path: Path to conftest.py or plugin file
            
        Returns:
            List of hook dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []
        
        hooks = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self.is_pytest_hook(node.name):
                    hook_info = self.extract_hook_info(node, file_path)
                    hooks.append(hook_info)
        
        return hooks
    
    def extract_pytest_addoption_options(self, file_path: Path) -> List[Dict]:
        """
        Extract custom command-line options from pytest_addoption.
        
        Args:
            file_path: Path to conftest.py
            
        Returns:
            List of option dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []
        
        options = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'pytest_addoption':
                # Look for parser.addoption() calls
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute):
                            if child.func.attr == 'addoption':
                                option_info = self._parse_addoption_call(child)
                                if option_info:
                                    options.append(option_info)
        
        return options
    
    def _parse_addoption_call(self, node: ast.Call) -> Optional[Dict]:
        """
        Parse an addoption() call to extract option details.
        
        Args:
            node: AST Call node
            
        Returns:
            Option dictionary or None
        """
        option_info = {
            'name': None,
            'action': None,
            'default': None,
            'help': None,
            'type': None,
        }
        
        # Get positional arguments (option names)
        if node.args:
            for arg in node.args:
                if isinstance(arg, ast.Constant):
                    if option_info['name'] is None:
                        option_info['name'] = arg.value
        
        # Get keyword arguments
        for keyword in node.keywords:
            if keyword.arg in option_info:
                if isinstance(keyword.value, ast.Constant):
                    option_info[keyword.arg] = keyword.value.value
                elif isinstance(keyword.value, ast.Name):
                    option_info[keyword.arg] = keyword.value.id
        
        return option_info if option_info['name'] else None
    
    def extract_collection_modifiers(self, file_path: Path) -> List[Dict]:
        """
        Extract test collection modification logic.
        
        Args:
            file_path: Path to conftest.py
            
        Returns:
            List of collection modifier dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []
        
        modifiers = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == 'pytest_collection_modifyitems':
                    modifier_info = {
                        'file': str(file_path),
                        'line': node.lineno,
                        'operations': [],
                    }
                    
                    # Analyze what the hook does
                    for child in ast.walk(node):
                        # Check for items.append/remove/insert
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Attribute):
                                if child.func.attr in ['append', 'remove', 'insert', 'sort']:
                                    modifier_info['operations'].append(child.func.attr)
                        
                        # Check for marker manipulation
                        if isinstance(child, ast.Attribute):
                            if child.attr == 'add_marker':
                                modifier_info['operations'].append('add_marker')
                    
                    modifiers.append(modifier_info)
        
        return modifiers
    
    def extract_all_hooks(self, project_path: Path) -> Dict:
        """
        Extract all pytest hooks from a project.
        
        Args:
            project_path: Root path of project
            
        Returns:
            Dictionary with all hook information
        """
        conftest_files = list(project_path.rglob("conftest.py"))
        
        all_hooks = []
        all_options = []
        all_modifiers = []
        
        for conftest in conftest_files:
            hooks = self.extract_hooks_from_file(conftest)
            options = self.extract_pytest_addoption_options(conftest)
            modifiers = self.extract_collection_modifiers(conftest)
            
            all_hooks.extend(hooks)
            all_options.extend(options)
            all_modifiers.extend(modifiers)
        
        # Group hooks by type
        hooks_by_type = {}
        for hook in all_hooks:
            hook_name = hook['name']
            if hook_name not in hooks_by_type:
                hooks_by_type[hook_name] = []
            hooks_by_type[hook_name].append(hook)
        
        return {
            'hooks': all_hooks,
            'options': all_options,
            'collection_modifiers': all_modifiers,
            'hooks_by_type': hooks_by_type,
            'total_conftest_files': len(conftest_files),
            'unique_hook_types': len(hooks_by_type),
        }
    
    def generate_hook_documentation(self, hooks_info: Dict) -> str:
        """
        Generate documentation for detected hooks.
        
        Args:
            hooks_info: Hooks information dictionary
            
        Returns:
            Markdown documentation string
        """
        lines = []
        lines.append("# Pytest Hooks Documentation\n")
        
        # Configuration hooks
        config_hooks = ['pytest_configure', 'pytest_unconfigure', 'pytest_addoption']
        lines.append("## Configuration Hooks\n")
        for hook_type in config_hooks:
            if hook_type in hooks_info['hooks_by_type']:
                lines.append(f"### {hook_type}\n")
                for hook in hooks_info['hooks_by_type'][hook_type]:
                    lines.append(f"- File: {hook['file']} (line {hook['line']})")
                    if hook['docstring']:
                        lines.append(f"  - {hook['docstring']}")
                lines.append("")
        
        # Collection hooks
        collection_hooks = ['pytest_collection_modifyitems', 'pytest_collection_finish']
        lines.append("## Collection Hooks\n")
        for hook_type in collection_hooks:
            if hook_type in hooks_info['hooks_by_type']:
                lines.append(f"### {hook_type}\n")
                for hook in hooks_info['hooks_by_type'][hook_type]:
                    lines.append(f"- File: {hook['file']} (line {hook['line']})")
                lines.append("")
        
        # Custom options
        if hooks_info['options']:
            lines.append("## Custom Command-Line Options\n")
            for option in hooks_info['options']:
                lines.append(f"### {option['name']}\n")
                if option['help']:
                    lines.append(f"- Help: {option['help']}")
                if option['default']:
                    lines.append(f"- Default: {option['default']}")
                if option['action']:
                    lines.append(f"- Action: {option['action']}")
                lines.append("")
        
        return '\n'.join(lines)
    
    def convert_to_unittest_hooks(self, hooks_info: Dict) -> str:
        """
        Convert pytest hooks to unittest equivalents.
        
        Args:
            hooks_info: Hooks information dictionary
            
        Returns:
            Python unittest code
        """
        lines = []
        lines.append("import unittest\n")
        
        # Convert pytest_configure to setUpModule
        if 'pytest_configure' in hooks_info['hooks_by_type']:
            lines.append("def setUpModule():")
            lines.append('    """Module setup from pytest_configure."""')
            lines.append("    pass\n")
        
        # Convert pytest_sessionstart to setUpClass
        if 'pytest_sessionstart' in hooks_info['hooks_by_type']:
            lines.append("class TestCase(unittest.TestCase):")
            lines.append("    @classmethod")
            lines.append("    def setUpClass(cls):")
            lines.append('        """Class setup from pytest_sessionstart."""')
            lines.append("        pass\n")
        
        return '\n'.join(lines)
    
    def get_hook_execution_order(self) -> List[str]:
        """
        Get the execution order of pytest hooks.
        
        Returns:
            Ordered list of hook names
        """
        return [
            'pytest_cmdline_parse',
            'pytest_cmdline_main',
            'pytest_configure',
            'pytest_sessionstart',
            'pytest_collection',
            'pytest_collection_modifyitems',
            'pytest_collection_finish',
            'pytest_runtest_setup',
            'pytest_runtest_call',
            'pytest_runtest_teardown',
            'pytest_runtest_makereport',
            'pytest_sessionfinish',
            'pytest_unconfigure',
        ]
