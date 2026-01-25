"""
Table conversion handler for SpecFlow.

Handles table transformations and TableConverter implementations.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class TableConversionHandler:
    """Handle SpecFlow table conversions."""
    
    def __init__(self):
        """Initialize the table conversion handler."""
        self.table_patterns = {
            'create_instance': re.compile(r'\.CreateInstance<(\w+)>\(\)'),
            'create_set': re.compile(r'\.CreateSet<(\w+)>\(\)'),
            'compare_to_instance': re.compile(r'\.CompareToInstance<(\w+)>\(([^)]+)\)'),
            'compare_to_set': re.compile(r'\.CompareToSet<(\w+)>\(([^)]+)\)'),
            'table_converter': re.compile(r'\[TableConverter\]'),
            'step_argument': re.compile(r'Table\s+(\w+)'),
        }
        
    def extract_table_operations(self, file_path: Path) -> List[Dict]:
        """
        Extract table operations from C# step definitions.
        
        Args:
            file_path: Path to C# file
            
        Returns:
            List of table operation dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        operations = []
        
        # Extract CreateInstance operations
        for match in self.table_patterns['create_instance'].finditer(content):
            operations.append({
                'type': 'create_instance',
                'target_type': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract CreateSet operations
        for match in self.table_patterns['create_set'].finditer(content):
            operations.append({
                'type': 'create_set',
                'target_type': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract CompareToInstance operations
        for match in self.table_patterns['compare_to_instance'].finditer(content):
            operations.append({
                'type': 'compare_to_instance',
                'target_type': match.group(1),
                'comparison_target': match.group(2).strip(),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract CompareToSet operations
        for match in self.table_patterns['compare_to_set'].finditer(content):
            operations.append({
                'type': 'compare_to_set',
                'target_type': match.group(1),
                'comparison_target': match.group(2).strip(),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        return operations
    
    def detect_table_converters(self, file_path: Path) -> List[Dict]:
        """
        Detect custom TableConverter implementations.
        
        Args:
            file_path: Path to C# file
            
        Returns:
            List of converter dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        converters = []
        
        # Find classes with TableConverter attribute
        class_pattern = re.compile(
            r'\[TableConverter\].*?public\s+class\s+(\w+)',
            re.DOTALL
        )
        
        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            converters.append({
                'class_name': class_name,
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        return converters
    
    def extract_step_table_parameters(self, file_path: Path) -> List[Dict]:
        """
        Extract Table parameters from step definitions.
        
        Args:
            file_path: Path to C# file
            
        Returns:
            List of table parameter dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        params = []
        
        # Find step methods with Table parameters
        step_pattern = re.compile(
            r'\[(Given|When|Then)\(["\']([^"\']+)["\']\)\].*?public\s+void\s+(\w+)\([^)]*Table\s+(\w+)[^)]*\)',
            re.DOTALL
        )
        
        for match in step_pattern.finditer(content):
            params.append({
                'step_type': match.group(1),
                'step_text': match.group(2),
                'method_name': match.group(3),
                'table_param_name': match.group(4),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        return params
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze project for table conversion usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        cs_files = list(project_path.rglob("*Steps.cs"))
        cs_files.extend(project_path.rglob("*StepDefinitions.cs"))
        
        all_operations = []
        all_converters = []
        all_table_params = []
        operation_counts = {}
        
        for cs_file in cs_files:
            operations = self.extract_table_operations(cs_file)
            all_operations.extend(operations)
            
            converters = self.detect_table_converters(cs_file)
            all_converters.extend(converters)
            
            table_params = self.extract_step_table_parameters(cs_file)
            all_table_params.extend(table_params)
            
            # Count operation types
            for op in operations:
                op_type = op['type']
                operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
        
        return {
            'operations': all_operations,
            'converters': all_converters,
            'table_parameters': all_table_params,
            'operation_counts': operation_counts,
            'files_analyzed': len(cs_files),
        }
    
    def convert_to_pytest(self, table_params: List[Dict]) -> str:
        """
        Convert SpecFlow table operations to pytest-bdd.
        
        Args:
            table_params: List of table parameter dictionaries
            
        Returns:
            Python code string
        """
        lines = []
        lines.append("from pytest_bdd import given, when, then, parsers")
        lines.append("from typing import List, Dict")
        lines.append("")
        
        for param in table_params[:3]:  # Show a few examples
            step_type = param['step_type'].lower()
            step_text = param['step_text']
            method_name = param['method_name']
            
            lines.append(f"@{step_type}(parsers.parse('{step_text}'))")
            lines.append(f"def {method_name.lower()}(datatable):")
            lines.append(f'    """')
            lines.append(f'    Step: {step_text}')
            lines.append(f'    Table parameter: {param["table_param_name"]}')
            lines.append(f'    """')
            lines.append("    # Convert datatable to list of dicts")
            lines.append("    data = [")
            lines.append("        dict(zip(datatable.headings, row))")
            lines.append("        for row in datatable.rows")
            lines.append("    ]")
            lines.append("    # Process table data")
            lines.append("    pass")
            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_table_helper_code(self) -> str:
        """
        Generate helper code for table operations.
        
        Returns:
            Python helper code
        """
        lines = []
        lines.append("from typing import List, Dict, Type, TypeVar")
        lines.append("from dataclasses import fields, is_dataclass")
        lines.append("")
        lines.append("T = TypeVar('T')")
        lines.append("")
        
        lines.append("class TableHelper:")
        lines.append('    """Helper for SpecFlow-style table operations."""')
        lines.append("")
        lines.append("    @staticmethod")
        lines.append("    def create_instance(model_class: Type[T], table_data: List[Dict]) -> T:")
        lines.append('        """Create single instance from table (first row)."""')
        lines.append("        if not table_data:")
        lines.append("            raise ValueError('Table data is empty')")
        lines.append("        ")
        lines.append("        first_row = table_data[0]")
        lines.append("        if is_dataclass(model_class):")
        lines.append("            # Handle dataclass")
        lines.append("            field_names = {f.name for f in fields(model_class)}")
        lines.append("            filtered_data = {k: v for k, v in first_row.items() if k in field_names}")
        lines.append("            return model_class(**filtered_data)")
        lines.append("        else:")
        lines.append("            # Handle regular class")
        lines.append("            instance = model_class()")
        lines.append("            for key, value in first_row.items():")
        lines.append("                if hasattr(instance, key):")
        lines.append("                    setattr(instance, key, value)")
        lines.append("            return instance")
        lines.append("")
        
        lines.append("    @staticmethod")
        lines.append("    def create_set(model_class: Type[T], table_data: List[Dict]) -> List[T]:")
        lines.append('        """Create list of instances from table (all rows)."""')
        lines.append("        return [TableHelper.create_instance(model_class, [row]) for row in table_data]")
        lines.append("")
        
        lines.append("    @staticmethod")
        lines.append("    def compare_to_instance(instance: T, table_data: List[Dict]) -> bool:")
        lines.append('        """Compare instance to table data."""')
        lines.append("        if not table_data:")
        lines.append("            return False")
        lines.append("        ")
        lines.append("        expected = table_data[0]")
        lines.append("        for key, expected_value in expected.items():")
        lines.append("            actual_value = getattr(instance, key, None)")
        lines.append("            if str(actual_value) != str(expected_value):")
        lines.append("                return False")
        lines.append("        return True")
        lines.append("")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for table conversion usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# SpecFlow Table Conversion Usage\n")
        
        lines.append("## Operation Summary\n")
        for op_type, count in analysis['operation_counts'].items():
            lines.append(f"- {op_type}: {count} occurrences")
        lines.append("")
        
        lines.append(f"## Custom Table Converters\n")
        lines.append(f"Found {len(analysis['converters'])} custom table converters\n")
        
        if analysis['converters']:
            for converter in analysis['converters'][:5]:
                lines.append(f"- {converter['class_name']}")
            lines.append("")
        
        lines.append(f"## Steps with Table Parameters\n")
        lines.append(f"Found {len(analysis['table_parameters'])} steps with table parameters\n")
        
        return '\n'.join(lines)
