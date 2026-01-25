"""
Value Retriever handler for SpecFlow.

Handles [StepArgumentTransformation] and custom value retrievers.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class ValueRetrieverHandler:
    """Handle SpecFlow value retrievers and step argument transformations."""
    
    def __init__(self):
        """Initialize the handler."""
        self.transformation_pattern = re.compile(
            r'\[StepArgumentTransformation(?:\(["\']([^"\']+)["\']\))?\]',
            re.MULTILINE
        )
        
    def extract_transformations(self, file_path: Path) -> List[Dict]:
        """
        Extract StepArgumentTransformation methods.
        
        Args:
            file_path: Path to C# file
            
        Returns:
            List of transformation dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        transformations = []
        
        # Find all StepArgumentTransformation attributes
        for match in self.transformation_pattern.finditer(content):
            regex_pattern = match.group(1) if match.group(1) else None
            attr_start = match.start()
            
            # Find the method following this attribute
            remaining_content = content[attr_start:]
            method_match = re.search(
                r'public\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)',
                remaining_content
            )
            
            if method_match:
                return_type = method_match.group(1)
                method_name = method_match.group(2)
                parameters = method_match.group(3).strip()
                
                transformations.append({
                    'method_name': method_name,
                    'return_type': return_type,
                    'parameters': parameters,
                    'regex_pattern': regex_pattern,
                    'line': content[:attr_start].count('\n') + 1,
                    'file': str(file_path),
                })
        
        return transformations
    
    def detect_custom_value_retrievers(self, file_path: Path) -> List[Dict]:
        """
        Detect custom value retriever implementations.
        
        Args:
            file_path: Path to C# file
            
        Returns:
            List of value retriever dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        retrievers = []
        
        # Look for classes implementing IValueRetriever
        class_pattern = re.compile(
            r'public\s+class\s+(\w+)\s*:\s*IValueRetriever',
            re.MULTILINE
        )
        
        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            retrievers.append({
                'class_name': class_name,
                'type': 'IValueRetriever',
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        return retrievers
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze value retriever usage in project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        cs_files = list(project_path.rglob("*.cs"))
        
        all_transformations = []
        all_retrievers = []
        return_types = set()
        
        for cs_file in cs_files:
            transformations = self.extract_transformations(cs_file)
            all_transformations.extend(transformations)
            
            retrievers = self.detect_custom_value_retrievers(cs_file)
            all_retrievers.extend(retrievers)
            
            # Collect return types
            for trans in transformations:
                return_types.add(trans['return_type'])
        
        return {
            'transformations': all_transformations,
            'custom_retrievers': all_retrievers,
            'return_types': sorted(return_types),
            'total_transformations': len(all_transformations),
            'total_custom_retrievers': len(all_retrievers),
        }
    
    def convert_to_pytest_fixtures(self, transformations: List[Dict]) -> str:
        """
        Convert SpecFlow transformations to pytest fixtures.
        
        Args:
            transformations: List of transformation dictionaries
            
        Returns:
            Python fixture code
        """
        lines = []
        lines.append("import pytest")
        lines.append("from typing import Any")
        lines.append("")
        
        for trans in transformations[:5]:  # Show first 5 examples
            fixture_name = trans['method_name'].lower()
            lines.append(f"@pytest.fixture")
            lines.append(f"def {fixture_name}():")
            lines.append(f'    """')
            lines.append(f'    Transformation: {trans["method_name"]}')
            lines.append(f'    Return type: {trans["return_type"]}')
            if trans['regex_pattern']:
                lines.append(f'    Pattern: {trans["regex_pattern"]}')
            lines.append(f'    """')
            lines.append(f"    # Implement transformation logic")
            lines.append(f"    pass")
            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_transformation_helper(self) -> str:
        """
        Generate helper class for step argument transformations.
        
        Returns:
            Python helper code
        """
        lines = []
        lines.append("import re")
        lines.append("from typing import Any, Callable, Dict, Optional")
        lines.append("")
        
        lines.append("class StepArgumentTransformer:")
        lines.append('    """Helper for SpecFlow-style argument transformations."""')
        lines.append("")
        lines.append("    def __init__(self):")
        lines.append("        self.transformations: Dict[str, Callable] = {}")
        lines.append("")
        
        lines.append("    def register(self, pattern: Optional[str] = None):")
        lines.append('        """Register a transformation function."""')
        lines.append("        def decorator(func: Callable) -> Callable:")
        lines.append("            key = pattern if pattern else func.__name__")
        lines.append("            self.transformations[key] = func")
        lines.append("            return func")
        lines.append("        return decorator")
        lines.append("")
        
        lines.append("    def transform(self, value: str, target_type: type) -> Any:")
        lines.append('        """Transform string value to target type."""')
        lines.append("        # Try registered transformations")
        lines.append("        for pattern, transformer in self.transformations.items():")
        lines.append("            if re.match(pattern, value):")
        lines.append("                return transformer(value)")
        lines.append("")
        lines.append("        # Default type conversion")
        lines.append("        if target_type == int:")
        lines.append("            return int(value)")
        lines.append("        elif target_type == float:")
        lines.append("            return float(value)")
        lines.append("        elif target_type == bool:")
        lines.append("            return value.lower() in ('true', 'yes', '1')")
        lines.append("        else:")
        lines.append("            return value")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for value retriever usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# SpecFlow Value Retriever Usage\n")
        
        lines.append("## Summary\n")
        lines.append(f"- Step Argument Transformations: {analysis['total_transformations']}")
        lines.append(f"- Custom Value Retrievers: {analysis['total_custom_retrievers']}")
        lines.append(f"- Return Types: {', '.join(analysis['return_types'])}\n")
        
        if analysis['transformations']:
            lines.append("## Transformations\n")
            for trans in analysis['transformations'][:5]:
                lines.append(f"### {trans['method_name']}")
                lines.append(f"- Return Type: {trans['return_type']}")
                if trans['regex_pattern']:
                    lines.append(f"- Pattern: `{trans['regex_pattern']}`")
                lines.append("")
        
        return '\n'.join(lines)
