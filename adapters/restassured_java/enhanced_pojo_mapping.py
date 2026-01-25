"""
Enhanced POJO mapping for RestAssured.

Handles POJO serialization, deserialization, and Jackson/Gson annotations.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import re


class EnhancedPojoMapping:
    """Handle POJO mapping with Jackson/Gson."""
    
    def __init__(self):
        """Initialize POJO mapping handler."""
        self.jackson_annotations = {
            '@JsonProperty': re.compile(r'@JsonProperty\(["\']([^"\']+)["\']\)'),
            '@JsonIgnore': re.compile(r'@JsonIgnore'),
            '@JsonFormat': re.compile(r'@JsonFormat\(([^)]+)\)'),
            '@JsonInclude': re.compile(r'@JsonInclude\(([^)]+)\)'),
            '@JsonAlias': re.compile(r'@JsonAlias\(\{([^}]+)\}\)'),
        }
        
        self.gson_annotations = {
            '@SerializedName': re.compile(r'@SerializedName\(["\']([^"\']+)["\']\)'),
            '@Expose': re.compile(r'@Expose'),
            '@Since': re.compile(r'@Since\(([^)]+)\)'),
        }
        
    def extract_pojo_classes(self, file_path: Path) -> List[Dict]:
        """
        Extract POJO classes from Java file.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of POJO class dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        pojos = []
        
        # Find classes (simple heuristic: public class with getters/setters or fields)
        class_pattern = re.compile(
            r'public\s+class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{',
            re.MULTILINE
        )
        
        for match in class_pattern.finditer(content):
            class_name = match.group(0).split()[2]  # Get class name
            class_start = match.end()
            
            # Find class end (simplified - may not work for nested classes)
            brace_count = 1
            class_end = class_start
            for i, char in enumerate(content[class_start:], start=class_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        class_end = i
                        break
            
            class_content = content[class_start:class_end]
            
            # Extract fields
            fields = self._extract_fields(class_content)
            
            # Check for Jackson/Gson usage
            has_jackson = any(annot in class_content for annot in ['@JsonProperty', '@JsonIgnore', '@JsonFormat'])
            has_gson = any(annot in class_content for annot in ['@SerializedName', '@Expose'])
            
            if fields:  # Only consider classes with fields
                pojos.append({
                    'class_name': class_name,
                    'fields': fields,
                    'has_jackson': has_jackson,
                    'has_gson': has_gson,
                    'line': content[:match.start()].count('\n') + 1,
                    'file': str(file_path),
                })
        
        return pojos
    
    def _extract_fields(self, class_content: str) -> List[Dict]:
        """
        Extract fields from class content.
        
        Args:
            class_content: Class body content
            
        Returns:
            List of field dictionaries
        """
        fields = []
        
        # Pattern for field declarations
        field_pattern = re.compile(
            r'(?:@\w+(?:\([^)]*\))?[\s\n]*)*'  # Optional annotations
            r'(?:private|public|protected)\s+'  # Access modifier
            r'(?:static\s+)?(?:final\s+)?'  # Optional static/final
            r'(\w+(?:<[^>]+>)?)\s+'  # Type (with generic support)
            r'(\w+)\s*(?:=\s*[^;]+)?;',  # Field name and optional initialization
            re.MULTILINE
        )
        
        for match in field_pattern.finditer(class_content):
            field_type = match.group(1)
            field_name = match.group(2)
            
            # Check for Jackson annotations before this field
            field_start = match.start()
            lines_before = class_content[:field_start].split('\n')[-5:]  # Last 5 lines
            annotation_context = '\n'.join(lines_before)
            
            # Extract JsonProperty name
            json_property = None
            json_prop_match = self.jackson_annotations['@JsonProperty'].search(annotation_context)
            if json_prop_match:
                json_property = json_prop_match.group(1)
            
            # Extract SerializedName
            serialized_name = None
            serialized_match = self.gson_annotations['@SerializedName'].search(annotation_context)
            if serialized_match:
                serialized_name = serialized_match.group(1)
            
            # Check for @JsonIgnore
            is_ignored = '@JsonIgnore' in annotation_context
            
            fields.append({
                'name': field_name,
                'type': field_type,
                'json_property': json_property,
                'serialized_name': serialized_name,
                'is_ignored': is_ignored,
            })
        
        return fields
    
    def extract_as_method_usage(self, file_path: Path) -> List[Dict]:
        """
        Extract .as(PojoClass.class) usage for deserialization.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of deserialization dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        usages = []
        
        # Pattern for .as(PojoClass.class)
        as_pattern = re.compile(r'\.as\((\w+)\.class\)')
        
        for match in as_pattern.finditer(content):
            pojo_class = match.group(1)
            usages.append({
                'pojo_class': pojo_class,
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        return usages
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze project for POJO mapping usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        java_files = list(project_path.rglob("*.java"))
        
        all_pojos = []
        all_deserialization = []
        jackson_count = 0
        gson_count = 0
        
        for java_file in java_files:
            pojos = self.extract_pojo_classes(java_file)
            all_pojos.extend(pojos)
            
            deserialization = self.extract_as_method_usage(java_file)
            all_deserialization.extend(deserialization)
            
            # Count Jackson/Gson usage
            for pojo in pojos:
                if pojo['has_jackson']:
                    jackson_count += 1
                if pojo['has_gson']:
                    gson_count += 1
        
        return {
            'pojos': all_pojos,
            'deserialization_usage': all_deserialization,
            'jackson_count': jackson_count,
            'gson_count': gson_count,
            'files_analyzed': len(java_files),
        }
    
    def convert_to_python_dataclasses(self, pojos: List[Dict]) -> str:
        """
        Convert Java POJOs to Python dataclasses.
        
        Args:
            pojos: List of POJO dictionaries
            
        Returns:
            Python code string
        """
        lines = []
        lines.append("from dataclasses import dataclass, field")
        lines.append("from typing import Optional, List")
        lines.append("from datetime import datetime")
        lines.append("")
        
        for pojo in pojos[:5]:  # Show first 5 examples
            lines.append("@dataclass")
            lines.append(f"class {pojo['class_name']}:")
            lines.append(f'    """{pojo["class_name"]} data model."""')
            
            for f in pojo['fields']:
                if f['is_ignored']:
                    continue  # Skip ignored fields
                
                # Map Java types to Python types
                python_type = self._map_java_type_to_python(f['type'])
                
                # Use json_property or serialized_name as field name
                field_name = f['name']
                json_name = f.get('json_property') or f.get('serialized_name')
                
                if json_name and json_name != field_name:
                    # Add field with metadata for different JSON name
                    lines.append(f"    {field_name}: {python_type} = field(metadata={{'json_name': '{json_name}'}})")
                else:
                    lines.append(f"    {field_name}: {python_type} = None")
            
            lines.append("")
        
        return '\n'.join(lines)
    
    def _map_java_type_to_python(self, java_type: str) -> str:
        """
        Map Java type to Python type.
        
        Args:
            java_type: Java type string
            
        Returns:
            Python type string
        """
        type_mapping = {
            'String': 'str',
            'int': 'int',
            'Integer': 'Optional[int]',
            'long': 'int',
            'Long': 'Optional[int]',
            'double': 'float',
            'Double': 'Optional[float]',
            'boolean': 'bool',
            'Boolean': 'Optional[bool]',
            'Date': 'datetime',
            'LocalDateTime': 'datetime',
            'LocalDate': 'datetime',
        }
        
        # Handle List<T>
        if java_type.startswith('List<'):
            inner_type = re.search(r'List<(\w+)>', java_type)
            if inner_type:
                inner = inner_type.group(1)
                mapped_inner = type_mapping.get(inner, inner)
                return f'List[{mapped_inner}]'
        
        return type_mapping.get(java_type, 'Optional[str]')
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for POJO mapping usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# RestAssured POJO Mapping Usage\n")
        
        lines.append("## POJO Summary\n")
        lines.append(f"- Total POJOs found: {len(analysis['pojos'])}")
        lines.append(f"- POJOs with Jackson annotations: {analysis['jackson_count']}")
        lines.append(f"- POJOs with Gson annotations: {analysis['gson_count']}")
        lines.append(f"- Deserialization usages (.as()): {len(analysis['deserialization_usage'])}\n")
        
        if analysis['pojos']:
            lines.append("## Example POJOs\n")
            for pojo in analysis['pojos'][:3]:
                lines.append(f"### {pojo['class_name']}")
                lines.append(f"- Fields: {len(pojo['fields'])}")
                lines.append(f"- Jackson: {'Yes' if pojo['has_jackson'] else 'No'}")
                lines.append(f"- Gson: {'Yes' if pojo['has_gson'] else 'No'}")
                lines.append("")
        
        return '\n'.join(lines)
