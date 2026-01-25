"""
ScenarioContext handler for SpecFlow.

Extracts and analyzes ScenarioContext usage in step definitions.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class ScenarioContextHandler:
    """Handle SpecFlow ScenarioContext operations."""
    
    def __init__(self):
        """Initialize the context handler."""
        self.context_patterns = {
            'add': re.compile(r'ScenarioContext\.Add\(["\'](\w+)["\']\s*,\s*([^)]+)\)'),
            'get': re.compile(r'ScenarioContext\.Get<(\w+)>\(["\'](\w+)["\']\)'),
            'set': re.compile(r'ScenarioContext\[["\'](\ w+)["\']\]\s*=\s*([^;]+)'),
            'contains': re.compile(r'ScenarioContext\.ContainsKey\(["\'](\w+)["\']\)'),
            'try_get': re.compile(r'ScenarioContext\.TryGetValue\(["\'](\w+)["\']\s*,\s*out\s+(\w+)\s+(\w+)\)'),
        }
        
    def extract_context_operations(self, file_path: Path) -> List[Dict]:
        """
        Extract ScenarioContext operations from C# file.
        
        Args:
            file_path: Path to C# step definition file
            
        Returns:
            List of context operation dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        operations = []
        
        # Extract Add operations
        for match in self.context_patterns['add'].finditer(content):
            operations.append({
                'operation': 'add',
                'key': match.group(1),
                'value': match.group(2).strip(),
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        # Extract Get operations
        for match in self.context_patterns['get'].finditer(content):
            operations.append({
                'operation': 'get',
                'type': match.group(1),
                'key': match.group(2),
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        # Extract indexer set operations
        for match in self.context_patterns['set'].finditer(content):
            operations.append({
                'operation': 'set',
                'key': match.group(1),
                'value': match.group(2).strip(),
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        # Extract ContainsKey operations
        for match in self.context_patterns['contains'].finditer(content):
            operations.append({
                'operation': 'contains',
                'key': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        # Extract TryGetValue operations
        for match in self.context_patterns['try_get'].finditer(content):
            operations.append({
                'operation': 'try_get',
                'key': match.group(1),
                'out_type': match.group(2),
                'out_variable': match.group(3),
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        return operations
    
    def analyze_context_usage(self, project_path: Path) -> Dict:
        """
        Analyze ScenarioContext usage across project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        cs_files = list(project_path.rglob("*Steps.cs"))
        cs_files.extend(project_path.rglob("*StepDefinitions.cs"))
        
        all_operations = []
        context_keys = {}
        operation_counts = {
            'add': 0, 'get': 0, 'set': 0, 'contains': 0, 'try_get': 0
        }
        
        for cs_file in cs_files:
            operations = self.extract_context_operations(cs_file)
            all_operations.extend(operations)
            
            for op in operations:
                # Count operation types
                operation_counts[op['operation']] += 1
                
                # Track context keys
                key = op.get('key')
                if key:
                    if key not in context_keys:
                        context_keys[key] = {
                            'operations': [],
                            'types': set(),
                        }
                    context_keys[key]['operations'].append(op['operation'])
                    if op.get('type'):
                        context_keys[key]['types'].add(op['type'])
        
        # Convert sets to lists for JSON serialization
        for key in context_keys:
            context_keys[key]['types'] = list(context_keys[key]['types'])
        
        return {
            'operations': all_operations,
            'operation_counts': operation_counts,
            'context_keys': context_keys,
            'files_analyzed': len(cs_files),
            'total_operations': len(all_operations),
        }
    
    def convert_to_pytest_context(self, operations: List[Dict]) -> str:
        """
        Convert ScenarioContext operations to pytest context.
        
        Args:
            operations: List of context operations
            
        Returns:
            Python code string
        """
        lines = []
        lines.append("import pytest")
        lines.append("from dataclasses import dataclass, field")
        lines.append("from typing import Any, Dict, Optional")
        lines.append("")
        
        lines.append("@dataclass")
        lines.append("class ScenarioContext:")
        lines.append('    """SpecFlow-compatible scenario context for pytest."""')
        lines.append("    _storage: Dict[str, Any] = field(default_factory=dict)")
        lines.append("")
        lines.append("    def add(self, key: str, value: Any) -> None:")
        lines.append('        """Add value to context."""')
        lines.append("        self._storage[key] = value")
        lines.append("")
        lines.append("    def get(self, key: str, value_type: type = None) -> Any:")
        lines.append('        """Get value from context."""')
        lines.append("        return self._storage.get(key)")
        lines.append("")
        lines.append("    def __setitem__(self, key: str, value: Any) -> None:")
        lines.append('        """Set value using indexer."""')
        lines.append("        self._storage[key] = value")
        lines.append("")
        lines.append("    def __getitem__(self, key: str) -> Any:")
        lines.append('        """Get value using indexer."""')
        lines.append("        return self._storage[key]")
        lines.append("")
        lines.append("    def contains_key(self, key: str) -> bool:")
        lines.append('        """Check if key exists."""')
        lines.append("        return key in self._storage")
        lines.append("")
        lines.append("    def try_get_value(self, key: str) -> tuple[bool, Any]:")
        lines.append('        """Try to get value."""')
        lines.append("        if key in self._storage:")
        lines.append("            return True, self._storage[key]")
        lines.append("        return False, None")
        lines.append("")
        
        lines.append("@pytest.fixture")
        lines.append("def scenario_context():")
        lines.append('    """Provide ScenarioContext fixture."""')
        lines.append("    return ScenarioContext()")
        lines.append("")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for ScenarioContext usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# SpecFlow ScenarioContext Usage\n")
        
        lines.append("## Operation Summary\n")
        for op_type, count in analysis['operation_counts'].items():
            lines.append(f"- {op_type}: {count} occurrences")
        lines.append("")
        
        lines.append("## Context Keys\n")
        lines.append(f"Found {len(analysis['context_keys'])} unique context keys:\n")
        
        for key, info in sorted(analysis['context_keys'].items())[:10]:
            lines.append(f"### `{key}`")
            lines.append(f"- Operations: {', '.join(set(info['operations']))}")
            if info['types']:
                lines.append(f"- Types: {', '.join(info['types'])}")
            lines.append("")
        
        return '\n'.join(lines)
