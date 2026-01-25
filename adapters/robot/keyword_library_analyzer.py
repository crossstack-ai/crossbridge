"""
Robot Framework keyword library analyzer.

Analyzes custom keyword libraries and resource files.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import re


class KeywordLibraryAnalyzer:
    """Analyze Robot Framework keyword libraries."""
    
    def __init__(self):
        """Initialize the analyzer."""
        pass
    
    def extract_custom_keywords(self, file_path: Path) -> List[Dict]:
        """
        Extract custom keywords from .robot or .resource file.
        
        Args:
            file_path: Path to Robot file
            
        Returns:
            List of keyword dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        keywords = []
        lines = content.split('\n')
        
        in_keywords_section = False
        current_keyword = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for Keywords section
            if stripped == '*** Keywords ***' or stripped == '***Keywords***':
                in_keywords_section = True
                continue
            
            # Check for other sections (end of Keywords)
            if stripped.startswith('***') and 'Keywords' not in stripped:
                in_keywords_section = False
                if current_keyword:
                    keywords.append(current_keyword)
                    current_keyword = None
                continue
            
            if in_keywords_section:
                # New keyword (no leading whitespace)
                if line and not line[0].isspace() and stripped:
                    if current_keyword:
                        keywords.append(current_keyword)
                    
                    current_keyword = {
                        'name': stripped,
                        'line': i + 1,
                        'arguments': [],
                        'steps': [],
                        'documentation': '',
                        'file': str(file_path),
                    }
                
                # Keyword content (indented)
                elif current_keyword and line and line[0].isspace():
                    if '[Arguments]' in stripped:
                        # Extract arguments
                        args_str = stripped.replace('[Arguments]', '').strip()
                        args = [a.strip() for a in args_str.split() if a.strip()]
                        current_keyword['arguments'] = args
                    elif '[Documentation]' in stripped:
                        doc = stripped.replace('[Documentation]', '').strip()
                        current_keyword['documentation'] = doc
                    elif stripped and not stripped.startswith('['):
                        # Step
                        current_keyword['steps'].append(stripped)
        
        # Add last keyword
        if current_keyword:
            keywords.append(current_keyword)
        
        return keywords
    
    def extract_library_imports(self, file_path: Path) -> List[Dict]:
        """
        Extract library imports from Robot file.
        
        Args:
            file_path: Path to Robot file
            
        Returns:
            List of library import dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        imports = []
        lines = content.split('\n')
        
        in_settings = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped == '*** Settings ***' or stripped == '***Settings***':
                in_settings = True
                continue
            
            if stripped.startswith('***') and 'Settings' not in stripped:
                in_settings = False
                continue
            
            if in_settings and 'Library' in stripped:
                # Extract library name
                library_match = re.search(r'Library\s+(\S+)', stripped)
                if library_match:
                    library_name = library_match.group(1)
                    
                    # Extract arguments if any
                    args = []
                    if '  ' in stripped:
                        parts = stripped.split()
                        if len(parts) > 2:
                            args = parts[2:]
                    
                    imports.append({
                        'library': library_name,
                        'arguments': args,
                        'line': i + 1,
                        'file': str(file_path),
                    })
        
        return imports
    
    def extract_resource_imports(self, file_path: Path) -> List[Dict]:
        """
        Extract resource file imports.
        
        Args:
            file_path: Path to Robot file
            
        Returns:
            List of resource import dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        resources = []
        
        resource_pattern = re.compile(r'Resource\s+(\S+)')
        
        for match in resource_pattern.finditer(content):
            resource_path = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            resources.append({
                'resource': resource_path,
                'line': line_num,
                'file': str(file_path),
            })
        
        return resources
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze Robot Framework project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        robot_files = list(project_path.rglob("*.robot"))
        resource_files = list(project_path.rglob("*.resource"))
        
        all_keywords = []
        all_library_imports = []
        all_resource_imports = []
        library_usage_counts = {}
        
        for robot_file in robot_files + resource_files:
            keywords = self.extract_custom_keywords(robot_file)
            all_keywords.extend(keywords)
            
            lib_imports = self.extract_library_imports(robot_file)
            all_library_imports.extend(lib_imports)
            
            res_imports = self.extract_resource_imports(robot_file)
            all_resource_imports.extend(res_imports)
            
            # Count library usage
            for lib_import in lib_imports:
                lib = lib_import['library']
                library_usage_counts[lib] = library_usage_counts.get(lib, 0) + 1
        
        return {
            'total_keywords': len(all_keywords),
            'total_library_imports': len(all_library_imports),
            'total_resource_imports': len(all_resource_imports),
            'keywords': all_keywords,
            'library_imports': all_library_imports,
            'resource_imports': all_resource_imports,
            'library_usage_counts': library_usage_counts,
            'most_used_libraries': sorted(library_usage_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        }
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for keyword library usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Robot Framework Keyword Library Analysis\n")
        
        lines.append("## Summary\n")
        lines.append(f"- Total custom keywords: {analysis['total_keywords']}")
        lines.append(f"- Library imports: {analysis['total_library_imports']}")
        lines.append(f"- Resource imports: {analysis['total_resource_imports']}\n")
        
        lines.append("## Most Used Libraries\n")
        for lib, count in analysis['most_used_libraries']:
            lines.append(f"- {lib}: {count} imports")
        lines.append("")
        
        if analysis['keywords']:
            lines.append("## Sample Custom Keywords\n")
            for keyword in analysis['keywords'][:5]:
                lines.append(f"### {keyword['name']}")
                if keyword['arguments']:
                    lines.append(f"- Arguments: {', '.join(keyword['arguments'])}")
                if keyword['documentation']:
                    lines.append(f"- Documentation: {keyword['documentation']}")
                lines.append(f"- Steps: {len(keyword['steps'])}")
                lines.append("")
        
        return '\n'.join(lines)
