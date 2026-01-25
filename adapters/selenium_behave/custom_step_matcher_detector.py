"""
Custom step matcher detector for Behave.

Detects custom step matchers and parsers.
"""

from typing import List, Dict, Optional
from pathlib import Path
import ast
import re


class CustomStepMatcherDetector:
    """Detect custom step matchers in Behave."""
    
    BUILTIN_MATCHERS = ['re', 'parse', 'cfparse', 'string']
    
    def __init__(self):
        """Initialize the matcher detector."""
        self.custom_matchers = {}
        
    def is_matcher_registration(self, node: ast.Call) -> bool:
        """
        Check if a node is a matcher registration.
        
        Args:
            node: AST Call node
            
        Returns:
            True if matcher registration
        """
        # Check for use_step_matcher() or register_type()
        if isinstance(node.func, ast.Name):
            return node.func.id in ['use_step_matcher', 'register_type']
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr in ['use_step_matcher', 'register_type']
        return False
    
    def extract_matcher_name(self, node: ast.Call) -> Optional[str]:
        """
        Extract matcher name from registration call.
        
        Args:
            node: AST Call node
            
        Returns:
            Matcher name or None
        """
        if node.args and isinstance(node.args[0], ast.Constant):
            return node.args[0].value
        return None
    
    def extract_custom_matcher(self, node: ast.FunctionDef) -> Optional[Dict]:
        """
        Extract custom matcher class information.
        
        Args:
            node: AST ClassDef or FunctionDef node
            
        Returns:
            Matcher information dictionary or None
        """
        # Look for Matcher class
        if not isinstance(node, ast.ClassDef):
            return None
        
        if 'Matcher' in node.name or any(
            isinstance(base, ast.Name) and 'Matcher' in base.id
            for base in node.bases
        ):
            matcher_info = {
                'name': node.name,
                'methods': [],
                'line': node.lineno,
            }
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    matcher_info['methods'].append(item.name)
            
            return matcher_info
        
        return None
    
    def extract_parse_type_registration(self, file_path: Path) -> List[Dict]:
        """
        Extract parse type registrations.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            List of type registration dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []
        
        registrations = []
        
        # Look for register_type calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'register_type':
                    if len(node.args) >= 1:
                        # First argument is the type converter
                        type_info = {
                            'line': node.lineno,
                            'file': str(file_path),
                        }
                        
                        # Extract type name from keyword arguments
                        for keyword in node.keywords:
                            if keyword.arg in ['name', 'pattern']:
                                if isinstance(keyword.value, ast.Constant):
                                    type_info[keyword.arg] = keyword.value.value
                        
                        registrations.append(type_info)
        
        return registrations
    
    def extract_matcher_usage(self, file_path: Path) -> List[Dict]:
        """
        Extract matcher usage from step definitions.
        
        Args:
            file_path: Path to step definition file
            
        Returns:
            List of matcher usage dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []
        
        usages = []
        current_matcher = 're'  # Default matcher
        
        for node in ast.walk(tree):
            # Check for use_step_matcher calls
            if isinstance(node, ast.Call):
                if self.is_matcher_registration(node):
                    matcher_name = self.extract_matcher_name(node)
                    if matcher_name:
                        current_matcher = matcher_name
                        usages.append({
                            'type': 'matcher_change',
                            'matcher': matcher_name,
                            'line': node.lineno,
                        })
            
            # Check for step definitions
            elif isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in ['given', 'when', 'then', 'step']:
                                usages.append({
                                    'type': 'step_definition',
                                    'step_type': decorator.func.attr,
                                    'function': node.name,
                                    'matcher': current_matcher,
                                    'line': node.lineno,
                                })
        
        return usages
    
    def extract_all_matchers(self, project_path: Path) -> Dict:
        """
        Extract all custom matchers from a project.
        
        Args:
            project_path: Root path of project
            
        Returns:
            Dictionary with all matcher information
        """
        # Find step definition and support files
        python_files = []
        python_files.extend(project_path.rglob("steps/*.py"))
        python_files.extend(project_path.rglob("features/**/*.py"))
        python_files.extend(project_path.rglob("support/*.py"))
        
        all_registrations = []
        all_usages = []
        custom_matchers = []
        
        for py_file in python_files:
            registrations = self.extract_parse_type_registration(py_file)
            usages = self.extract_matcher_usage(py_file)
            
            all_registrations.extend(registrations)
            all_usages.extend(usages)
            
            # Check for custom matcher classes
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        matcher = self.extract_custom_matcher(node)
                        if matcher:
                            matcher['file'] = str(py_file)
                            custom_matchers.append(matcher)
            except (SyntaxError, UnicodeDecodeError):
                continue
        
        # Count matcher usage
        matcher_counts = {}
        for usage in all_usages:
            if usage['type'] == 'step_definition':
                matcher = usage['matcher']
                matcher_counts[matcher] = matcher_counts.get(matcher, 0) + 1
        
        return {
            'type_registrations': all_registrations,
            'matcher_usages': all_usages,
            'custom_matchers': custom_matchers,
            'matcher_counts': matcher_counts,
            'files_analyzed': len(python_files),
        }
    
    def generate_matcher_documentation(self, matchers_info: Dict) -> str:
        """
        Generate documentation for custom matchers.
        
        Args:
            matchers_info: Matchers information dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Behave Custom Step Matchers\n")
        
        # Matcher usage statistics
        lines.append("## Matcher Usage\n")
        for matcher, count in sorted(matchers_info['matcher_counts'].items()):
            lines.append(f"- `{matcher}`: {count} steps")
        lines.append("")
        
        # Custom type registrations
        if matchers_info['type_registrations']:
            lines.append("## Custom Parse Types\n")
            for reg in matchers_info['type_registrations']:
                name = reg.get('name', 'unknown')
                pattern = reg.get('pattern', 'N/A')
                lines.append(f"### {name}")
                lines.append(f"- Pattern: `{pattern}`")
                lines.append(f"- File: {reg['file']} (line {reg['line']})")
                lines.append("")
        
        # Custom matcher classes
        if matchers_info['custom_matchers']:
            lines.append("## Custom Matcher Classes\n")
            for matcher in matchers_info['custom_matchers']:
                lines.append(f"### {matcher['name']}")
                lines.append(f"- File: {matcher['file']} (line {matcher['line']})")
                if matcher['methods']:
                    lines.append("- Methods:")
                    for method in matcher['methods']:
                        lines.append(f"  - `{method}()`")
                lines.append("")
        
        return '\n'.join(lines)
    
    def convert_to_pytest_bdd_parsers(self, matchers_info: Dict) -> str:
        """
        Convert Behave matchers to pytest-bdd parsers.
        
        Args:
            matchers_info: Matchers information dictionary
            
        Returns:
            Python pytest-bdd parser code
        """
        lines = []
        lines.append("from pytest_bdd import parsers")
        lines.append("import re\n")
        
        # Convert custom parse types
        for reg in matchers_info['type_registrations']:
            name = reg.get('name', 'custom')
            pattern = reg.get('pattern', '.*')
            
            lines.append(f"""
def parse_{name}(text):
    \"\"\"Parse {name} from text.\"\"\"
    match = re.search(r'{pattern}', text)
    if match:
        return match.group(1)
    return None
""")
        
        return '\n'.join(lines)
    
    def detect_matcher_compatibility_issues(self, matchers_info: Dict) -> List[Dict]:
        """
        Detect potential matcher compatibility issues.
        
        Args:
            matchers_info: Matchers information dictionary
            
        Returns:
            List of issue dictionaries
        """
        issues = []
        
        # Check for mixed matcher usage
        matcher_changes = [
            usage for usage in matchers_info['matcher_usages']
            if usage['type'] == 'matcher_change'
        ]
        
        if len(matcher_changes) > 3:
            issues.append({
                'type': 'excessive_matcher_switching',
                'severity': 'warning',
                'message': f'Found {len(matcher_changes)} matcher switches, consider using a consistent matcher',
            })
        
        # Check for deprecated matchers
        for matcher, count in matchers_info['matcher_counts'].items():
            if matcher == 'cfparse':
                issues.append({
                    'type': 'deprecated_matcher',
                    'severity': 'warning',
                    'matcher': matcher,
                    'message': 'cfparse matcher is deprecated, consider using parse instead',
                })
        
        # Check for unused custom matchers
        custom_matcher_names = {m['name'] for m in matchers_info['custom_matchers']}
        used_matchers = set(matchers_info['matcher_counts'].keys())
        unused = custom_matcher_names - used_matchers
        
        if unused:
            issues.append({
                'type': 'unused_custom_matcher',
                'severity': 'info',
                'matchers': list(unused),
                'message': f'Custom matchers defined but not used: {", ".join(unused)}',
            })
        
        return issues
