"""
Pytest plugin support detector.

Detects and analyzes pytest plugins used in the project.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import ast
import re


class PluginSupportDetector:
    """Detect pytest plugins in the project."""
    
    KNOWN_PLUGINS = {
        'pytest-xdist': {
            'markers': ['run_xdist', 'xfail_on_xdist'],
            'options': ['--dist', '--numprocesses', '-n'],
            'imports': ['xdist'],
        },
        'pytest-cov': {
            'markers': [],
            'options': ['--cov', '--cov-report', '--cov-config'],
            'imports': ['pytest_cov'],
        },
        'pytest-asyncio': {
            'markers': ['asyncio'],
            'options': ['--asyncio-mode'],
            'imports': ['pytest_asyncio'],
        },
        'pytest-mock': {
            'markers': [],
            'options': [],
            'imports': ['pytest_mock'],
            'fixtures': ['mocker'],
        },
        'pytest-django': {
            'markers': ['django_db'],
            'options': ['--reuse-db', '--create-db'],
            'imports': ['pytest_django'],
        },
        'pytest-bdd': {
            'markers': [],
            'options': [],
            'imports': ['pytest_bdd'],
            'functions': ['given', 'when', 'then', 'scenario'],
        },
        'pytest-html': {
            'markers': [],
            'options': ['--html', '--self-contained-html'],
            'imports': ['pytest_html'],
        },
        'pytest-timeout': {
            'markers': ['timeout'],
            'options': ['--timeout', '--timeout-method'],
            'imports': ['pytest_timeout'],
        },
        'pytest-ordering': {
            'markers': ['run', 'order'],
            'options': [],
            'imports': ['pytest_ordering'],
        },
        'pytest-dependency': {
            'markers': ['dependency', 'depends'],
            'options': [],
            'imports': ['pytest_dependency'],
        },
    }
    
    def __init__(self):
        """Initialize the plugin detector."""
        self.detected_plugins = set()
        
    def detect_from_imports(self, file_path: Path) -> Set[str]:
        """
        Detect plugins from import statements.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Set of detected plugin names
        """
        if not file_path.exists():
            return set()
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return set()
        
        detected = set()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        # Check against known plugins
                        for plugin, info in self.KNOWN_PLUGINS.items():
                            for import_name in info.get('imports', []):
                                if import_name in module_name:
                                    detected.add(plugin)
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ''
                    for plugin, info in self.KNOWN_PLUGINS.items():
                        for import_name in info.get('imports', []):
                            if import_name in module_name:
                                detected.add(plugin)
        
        return detected
    
    def detect_from_markers(self, file_path: Path) -> Set[str]:
        """
        Detect plugins from pytest markers.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Set of detected plugin names
        """
        if not file_path.exists():
            return set()
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return set()
        
        detected = set()
        
        # Check for marker usage
        for plugin, info in self.KNOWN_PLUGINS.items():
            for marker in info.get('markers', []):
                pattern = rf'@pytest\.mark\.{marker}'
                if re.search(pattern, content):
                    detected.add(plugin)
        
        return detected
    
    def detect_from_fixtures(self, file_path: Path) -> Set[str]:
        """
        Detect plugins from fixture usage.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Set of detected plugin names
        """
        if not file_path.exists():
            return set()
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return set()
        
        detected = set()
        
        # Extract function parameters (potential fixtures)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    fixture_name = arg.arg
                    # Check against known plugin fixtures
                    for plugin, info in self.KNOWN_PLUGINS.items():
                        if fixture_name in info.get('fixtures', []):
                            detected.add(plugin)
        
        return detected
    
    def detect_from_conftest(self, file_path: Path) -> Set[str]:
        """
        Detect plugins from conftest.py configuration.
        
        Args:
            file_path: Path to conftest.py
            
        Returns:
            Set of detected plugin names
        """
        if not file_path.exists() or file_path.name != 'conftest.py':
            return set()
        
        detected = set()
        
        # Check imports
        detected.update(self.detect_from_imports(file_path))
        
        # Check for pytest_plugins variable
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'pytest_plugins':
                            # Extract plugin names
                            if isinstance(node.value, (ast.List, ast.Tuple)):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        plugin_name = elt.value
                                        # Match against known plugins
                                        for known_plugin in self.KNOWN_PLUGINS:
                                            if known_plugin.replace('pytest-', '') in plugin_name:
                                                detected.add(known_plugin)
        except (SyntaxError, UnicodeDecodeError):
            pass
        
        return detected
    
    def detect_from_setup_cfg(self, file_path: Path) -> Set[str]:
        """
        Detect plugins from setup.cfg.
        
        Args:
            file_path: Path to setup.cfg
            
        Returns:
            Set of detected plugin names
        """
        if not file_path.exists():
            return set()
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return set()
        
        detected = set()
        
        # Look in [options] or [tool:pytest] sections
        for plugin in self.KNOWN_PLUGINS:
            if plugin in content:
                detected.add(plugin)
        
        return detected
    
    def detect_from_pyproject_toml(self, file_path: Path) -> Set[str]:
        """
        Detect plugins from pyproject.toml.
        
        Args:
            file_path: Path to pyproject.toml
            
        Returns:
            Set of detected plugin names
        """
        if not file_path.exists():
            return set()
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return set()
        
        detected = set()
        
        # Check dependencies sections
        for plugin in self.KNOWN_PLUGINS:
            if plugin in content:
                detected.add(plugin)
        
        return detected
    
    def detect_all_plugins(self, project_path: Path) -> Dict:
        """
        Detect all pytest plugins used in a project.
        
        Args:
            project_path: Root path of project
            
        Returns:
            Dictionary with all plugin information
        """
        all_detected = set()
        plugin_locations = {}
        
        # Check conftest files
        conftest_files = list(project_path.rglob("conftest.py"))
        for conftest in conftest_files:
            detected = self.detect_from_conftest(conftest)
            all_detected.update(detected)
            for plugin in detected:
                if plugin not in plugin_locations:
                    plugin_locations[plugin] = []
                plugin_locations[plugin].append(str(conftest))
        
        # Check test files
        test_files = list(project_path.rglob("test_*.py"))
        for test_file in test_files:
            detected = self.detect_from_imports(test_file)
            detected.update(self.detect_from_markers(test_file))
            detected.update(self.detect_from_fixtures(test_file))
            all_detected.update(detected)
            
            for plugin in detected:
                if plugin not in plugin_locations:
                    plugin_locations[plugin] = []
                plugin_locations[plugin].append(str(test_file))
        
        # Check configuration files
        setup_cfg = project_path / "setup.cfg"
        if setup_cfg.exists():
            detected = self.detect_from_setup_cfg(setup_cfg)
            all_detected.update(detected)
        
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            detected = self.detect_from_pyproject_toml(pyproject)
            all_detected.update(detected)
        
        # Build detailed info
        plugins_info = []
        for plugin in sorted(all_detected):
            info = self.KNOWN_PLUGINS.get(plugin, {})
            plugins_info.append({
                'name': plugin,
                'markers': info.get('markers', []),
                'options': info.get('options', []),
                'locations': plugin_locations.get(plugin, []),
            })
        
        return {
            'plugins': plugins_info,
            'total_plugins': len(all_detected),
            'conftest_files_checked': len(conftest_files),
            'test_files_checked': len(test_files),
        }
    
    def generate_plugin_requirements(self, plugins_info: Dict) -> str:
        """
        Generate requirements.txt content for detected plugins.
        
        Args:
            plugins_info: Plugins information dictionary
            
        Returns:
            Requirements.txt content
        """
        lines = []
        lines.append("# Pytest plugins")
        lines.append("pytest>=7.0.0")
        
        for plugin in plugins_info['plugins']:
            lines.append(plugin['name'])
        
        return '\n'.join(lines)
    
    def generate_plugin_documentation(self, plugins_info: Dict) -> str:
        """
        Generate documentation for detected plugins.
        
        Args:
            plugins_info: Plugins information dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Pytest Plugins Used\n")
        
        for plugin_info in plugins_info['plugins']:
            lines.append(f"## {plugin_info['name']}\n")
            
            if plugin_info['markers']:
                lines.append("### Markers:")
                for marker in plugin_info['markers']:
                    lines.append(f"- `@pytest.mark.{marker}`")
                lines.append("")
            
            if plugin_info['options']:
                lines.append("### Command-line Options:")
                for option in plugin_info['options']:
                    lines.append(f"- `{option}`")
                lines.append("")
            
            if plugin_info['locations']:
                lines.append("### Used in:")
                for location in plugin_info['locations'][:5]:  # Show first 5
                    lines.append(f"- {location}")
                if len(plugin_info['locations']) > 5:
                    lines.append(f"- ... and {len(plugin_info['locations']) - 5} more files")
                lines.append("")
        
        return '\n'.join(lines)
