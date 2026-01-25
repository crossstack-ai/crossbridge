"""
Request filter chain extractor for RestAssured.

Handles request and response filters, logging filters, and filter chains.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class RequestFilterChainExtractor:
    """Extract RestAssured filter chains."""
    
    def __init__(self):
        """Initialize the filter chain extractor."""
        self.filter_patterns = {
            'filter': re.compile(r'\.filter\(([^)]+)\)'),
            'log_filter': re.compile(r'new\s+(Request|Response)LoggingFilter\(\)'),
            'custom_filter': re.compile(r'new\s+(\w+Filter)\(\)'),
            'filter_class': re.compile(r'class\s+(\w+)\s+implements\s+(Filter|OrderedFilter)'),
            'filter_method': re.compile(r'public\s+(?:Response|void)\s+filter\('),
        }
        
    def extract_filters(self, file_path: Path) -> List[Dict]:
        """
        Extract filter usage from Java file.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of filter dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        filters = []
        
        # Extract filter() calls
        for match in self.filter_patterns['filter'].finditer(content):
            filter_arg = match.group(1).strip()
            filters.append({
                'type': 'filter_usage',
                'filter': filter_arg,
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        # Extract logging filters
        for match in self.filter_patterns['log_filter'].finditer(content):
            filter_type = match.group(1)
            filters.append({
                'type': 'logging_filter',
                'filter_class': f'{filter_type}LoggingFilter',
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        # Extract custom filters
        for match in self.filter_patterns['custom_filter'].finditer(content):
            filter_class = match.group(1)
            filters.append({
                'type': 'custom_filter',
                'filter_class': filter_class,
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        return filters
    
    def extract_filter_implementations(self, file_path: Path) -> List[Dict]:
        """
        Extract custom filter implementations.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of filter implementation dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        implementations = []
        
        # Find filter class definitions
        for match in self.filter_patterns['filter_class'].finditer(content):
            class_name = match.group(1)
            interface = match.group(2)
            
            # Check if it has a filter method
            has_filter_method = False
            class_content_match = re.search(
                rf'class\s+{class_name}.*?\{{(.*?)(?=\nclass|\Z)',
                content,
                re.DOTALL
            )
            
            if class_content_match:
                class_content = class_content_match.group(1)
                if self.filter_patterns['filter_method'].search(class_content):
                    has_filter_method = True
            
            implementations.append({
                'class_name': class_name,
                'interface': interface,
                'has_filter_method': has_filter_method,
                'line': content[:match.start()].count('\n') + 1,
                'file': str(file_path),
            })
        
        return implementations
    
    def extract_filter_chains(self, file_path: Path) -> List[Dict]:
        """
        Extract filter chains (multiple filters applied).
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of filter chain dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        chains = []
        
        # Find sequences of .filter() calls
        chain_pattern = re.compile(
            r'((?:\.filter\([^)]+\)\s*)+)',
            re.MULTILINE
        )
        
        for match in chain_pattern.finditer(content):
            chain_str = match.group(1)
            
            # Count filters in chain
            filter_count = chain_str.count('.filter(')
            
            if filter_count > 1:
                # Extract individual filters
                individual_filters = re.findall(r'\.filter\(([^)]+)\)', chain_str)
                
                chains.append({
                    'filter_count': filter_count,
                    'filters': individual_filters,
                    'chain': chain_str.strip(),
                    'line': content[:match.start()].count('\n') + 1,
                })
        
        return chains
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze project for filter usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        java_files = list(project_path.rglob("*.java"))
        
        all_filters = []
        all_implementations = []
        all_chains = []
        filter_types = {}
        
        for java_file in java_files:
            filters = self.extract_filters(java_file)
            all_filters.extend(filters)
            
            implementations = self.extract_filter_implementations(java_file)
            all_implementations.extend(implementations)
            
            chains = self.extract_filter_chains(java_file)
            all_chains.extend(chains)
            
            # Count filter types
            for f in filters:
                f_type = f['type']
                filter_types[f_type] = filter_types.get(f_type, 0) + 1
        
        return {
            'filters': all_filters,
            'implementations': all_implementations,
            'filter_chains': all_chains,
            'filter_types': filter_types,
            'files_analyzed': len(java_files),
        }
    
    def convert_to_python_interceptors(self, filters: List[Dict]) -> str:
        """
        Convert RestAssured filters to Python requests interceptors.
        
        Args:
            filters: List of filter dictionaries
            
        Returns:
            Python code string
        """
        lines = []
        lines.append("import requests")
        lines.append("from requests.adapters import HTTPAdapter")
        lines.append("from requests.hooks import dispatch_hook")
        lines.append("")
        
        lines.append("class RequestLoggingInterceptor:")
        lines.append('    """Request logging interceptor (like RequestLoggingFilter)."""')
        lines.append("")
        lines.append("    def __call__(self, r, *args, **kwargs):")
        lines.append("        print(f'Request: {r.method} {r.url}')")
        lines.append("        print(f'Headers: {r.headers}')")
        lines.append("        if r.body:")
        lines.append("            print(f'Body: {r.body}')")
        lines.append("        return r")
        lines.append("")
        
        lines.append("class ResponseLoggingInterceptor:")
        lines.append('    """Response logging interceptor (like ResponseLoggingFilter)."""')
        lines.append("")
        lines.append("    def __call__(self, r, *args, **kwargs):")
        lines.append("        print(f'Response: {r.status_code}')")
        lines.append("        print(f'Headers: {r.headers}')")
        lines.append("        print(f'Body: {r.text}')")
        lines.append("        return r")
        lines.append("")
        
        lines.append("# Usage example")
        lines.append("session = requests.Session()")
        lines.append("session.hooks['response'].append(RequestLoggingInterceptor())")
        lines.append("session.hooks['response'].append(ResponseLoggingInterceptor())")
        lines.append("")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for filter usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# RestAssured Filter Usage\n")
        
        lines.append("## Filter Summary\n")
        for filter_type, count in analysis['filter_types'].items():
            lines.append(f"- {filter_type}: {count} occurrences")
        lines.append("")
        
        lines.append(f"## Custom Filter Implementations\n")
        lines.append(f"Found {len(analysis['implementations'])} custom filter implementations\n")
        
        if analysis['implementations']:
            for impl in analysis['implementations'][:5]:
                lines.append(f"- {impl['class_name']} (implements {impl['interface']})")
            lines.append("")
        
        lines.append(f"## Filter Chains\n")
        lines.append(f"Found {len(analysis['filter_chains'])} filter chains (multiple filters)\n")
        
        if analysis['filter_chains']:
            lines.append("### Examples:\n")
            for chain in analysis['filter_chains'][:3]:
                lines.append(f"Chain with {chain['filter_count']} filters:")
                lines.append(f"```java\n{chain['chain'][:200]}\n```\n")
        
        return '\n'.join(lines)
