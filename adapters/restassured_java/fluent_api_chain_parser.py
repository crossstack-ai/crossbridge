"""
Fluent API chain parser for RestAssured.

Parses RestAssured fluent API chains and method chaining patterns.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re
import ast


class FluentApiChainParser:
    """Parse RestAssured fluent API chains."""
    
    def __init__(self):
        """Initialize the fluent API parser."""
        self.chain_methods = {
            # Request specification
            'request': ['given', 'when', 'with', 'request'],
            'headers': ['header', 'headers'],
            'params': ['param', 'params', 'queryParam', 'queryParams'],
            'body': ['body', 'contentType', 'content'],
            'auth': ['auth', 'basic', 'oauth', 'oauth2'],
            'cookies': ['cookie', 'cookies'],
            'filters': ['filter', 'filters'],
            # HTTP methods
            'http': ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'],
            # Response validation
            'assertions': ['then', 'expect', 'assertThat'],
            'body_validation': ['body', 'statusCode', 'statusLine'],
            'header_validation': ['header', 'headers', 'cookie', 'cookies'],
            'time_validation': ['time', 'timeout'],
            # Extraction
            'extraction': ['extract', 'path', 'jsonPath', 'xmlPath'],
        }
        
    def extract_chain_from_java(self, file_path: Path) -> List[Dict]:
        """
        Extract fluent API chains from Java file.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of chain dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        chains = []
        
        # Pattern to match RestAssured chains
        # given().header().param().when().get().then().statusCode()
        pattern = re.compile(
            r'(?:given|when|expect|with)\(\)(?:\s*\.[\w<>]+\([^;]*\))+',
            re.MULTILINE | re.DOTALL
        )
        
        for match in pattern.finditer(content):
            chain_text = match.group(0)
            methods = self._parse_chain_methods(chain_text)
            
            if methods:
                chains.append({
                    'text': chain_text[:200],  # First 200 chars
                    'methods': methods,
                    'line': content[:match.start()].count('\n') + 1,
                    'file': str(file_path),
                })
        
        return chains
    
    def _parse_chain_methods(self, chain_text: str) -> List[Dict]:
        """
        Parse individual methods from chain text.
        
        Args:
            chain_text: Fluent API chain text
            
        Returns:
            List of method dictionaries
        """
        methods = []
        
        # Pattern to match method calls: .methodName(args)
        method_pattern = re.compile(r'\.(\w+)\(([^)]*)\)')
        
        for match in method_pattern.finditer(chain_text):
            method_name = match.group(1)
            args_text = match.group(2).strip()
            
            method_info = {
                'name': method_name,
                'category': self._categorize_method(method_name),
                'has_args': bool(args_text),
            }
            
            # Try to extract argument values
            if args_text:
                method_info['args'] = self._parse_arguments(args_text)
            
            methods.append(method_info)
        
        return methods
    
    def _categorize_method(self, method_name: str) -> str:
        """
        Categorize a method based on its name.
        
        Args:
            method_name: Method name
            
        Returns:
            Category string
        """
        for category, methods in self.chain_methods.items():
            if method_name in methods:
                return category
        return 'unknown'
    
    def _parse_arguments(self, args_text: str) -> List[str]:
        """
        Parse method arguments.
        
        Args:
            args_text: Argument text
            
        Returns:
            List of argument strings
        """
        # Simple argument parsing (doesn't handle complex nested calls)
        args = []
        
        # Split by comma, but respect quotes and parentheses
        depth = 0
        current_arg = []
        in_quotes = False
        quote_char = None
        
        for char in args_text:
            if char in ['"', "'"]:
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                current_arg.append(char)
            elif char == '(' and not in_quotes:
                depth += 1
                current_arg.append(char)
            elif char == ')' and not in_quotes:
                depth -= 1
                current_arg.append(char)
            elif char == ',' and depth == 0 and not in_quotes:
                args.append(''.join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)
        
        if current_arg:
            args.append(''.join(current_arg).strip())
        
        return args
    
    def analyze_chains(self, project_path: Path) -> Dict:
        """
        Analyze all fluent API chains in a project.
        
        Args:
            project_path: Root path of Java project
            
        Returns:
            Analysis dictionary
        """
        java_files = list(project_path.rglob("*.java"))
        
        all_chains = []
        method_usage = {}
        
        for java_file in java_files:
            chains = self.extract_chain_from_java(java_file)
            all_chains.extend(chains)
            
            # Count method usage
            for chain in chains:
                for method in chain['methods']:
                    method_name = method['name']
                    method_usage[method_name] = method_usage.get(method_name, 0) + 1
        
        # Analyze chain patterns
        patterns = self._identify_common_patterns(all_chains)
        
        return {
            'chains': all_chains,
            'method_usage': method_usage,
            'patterns': patterns,
            'total_chains': len(all_chains),
            'files_analyzed': len(java_files),
        }
    
    def _identify_common_patterns(self, chains: List[Dict]) -> List[Dict]:
        """
        Identify common chain patterns.
        
        Args:
            chains: List of chain dictionaries
            
        Returns:
            List of pattern dictionaries
        """
        patterns = {}
        
        for chain in chains:
            # Create pattern signature from method categories
            signature = ' -> '.join(
                method['category'] for method in chain['methods']
            )
            
            if signature not in patterns:
                patterns[signature] = {
                    'signature': signature,
                    'count': 0,
                    'examples': [],
                }
            
            patterns[signature]['count'] += 1
            if len(patterns[signature]['examples']) < 3:
                patterns[signature]['examples'].append(chain['text'])
        
        # Sort by frequency
        return sorted(patterns.values(), key=lambda x: x['count'], reverse=True)
    
    def convert_to_python_requests(self, chain_info: Dict) -> str:
        """
        Convert RestAssured chain to Python requests equivalent.
        
        Args:
            chain_info: Chain information dictionary
            
        Returns:
            Python requests code
        """
        lines = []
        lines.append("import requests\n")
        
        # Build requests call
        headers = {}
        params = {}
        body = None
        auth = None
        method = 'get'
        url = 'BASE_URL'
        
        for method_info in chain_info['methods']:
            method_name = method_info['name']
            category = method_info['category']
            
            if category == 'headers' and method_info.get('args'):
                # Extract header key-value
                args = method_info['args']
                if len(args) >= 2:
                    headers[args[0].strip('"')] = args[1].strip('"')
            
            elif category == 'params' and method_info.get('args'):
                args = method_info['args']
                if len(args) >= 2:
                    params[args[0].strip('"')] = args[1].strip('"')
            
            elif category == 'body' and method_name == 'body':
                if method_info.get('args'):
                    body = method_info['args'][0]
            
            elif category == 'http':
                method = method_name
                if method_info.get('args'):
                    url = method_info['args'][0].strip('"')
        
        # Generate Python code
        request_args = [f'"{url}"']
        
        if headers:
            request_args.append(f'headers={headers}')
        if params:
            request_args.append(f'params={params}')
        if body:
            request_args.append(f'json={body}')
        if auth:
            request_args.append(f'auth={auth}')
        
        lines.append(f"response = requests.{method}({', '.join(request_args)})")
        lines.append("assert response.status_code == 200")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for fluent API usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# RestAssured Fluent API Usage\n")
        
        # Most used methods
        lines.append("## Most Used Methods\n")
        top_methods = sorted(
            analysis['method_usage'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for method, count in top_methods:
            lines.append(f"- `{method}()`: {count} occurrences")
        lines.append("")
        
        # Common patterns
        lines.append("## Common Chain Patterns\n")
        for i, pattern in enumerate(analysis['patterns'][:5], 1):
            lines.append(f"### Pattern {i} (used {pattern['count']} times)")
            lines.append(f"```\n{pattern['signature']}\n```")
            if pattern['examples']:
                lines.append("Example:")
                lines.append(f"```java\n{pattern['examples'][0]}\n```")
            lines.append("")
        
        return '\n'.join(lines)
