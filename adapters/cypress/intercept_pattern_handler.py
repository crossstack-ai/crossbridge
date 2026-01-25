"""
Advanced intercept pattern handler for Cypress.

Handles cy.intercept() patterns, route matching, and response stubbing.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class InterceptPatternHandler:
    """Handle Cypress cy.intercept() patterns."""
    
    def __init__(self):
        """Initialize the handler."""
        self.intercept_pattern = re.compile(
            r'cy\.intercept\(\s*([^)]+)\s*\)',
            re.DOTALL
        )
        
    def extract_intercepts(self, file_path: Path) -> List[Dict]:
        """
        Extract cy.intercept() calls from Cypress test.
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of intercept dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        intercepts = []
        
        for match in self.intercept_pattern.finditer(content):
            args = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            intercept_info = {
                'args': args,
                'line': line_num,
                'file': str(file_path),
                'type': self._classify_intercept(args),
            }
            
            # Try to extract route pattern
            route_match = re.search(r'["\']([^"\']+)["\']', args)
            if route_match:
                intercept_info['route'] = route_match.group(1)
            
            # Check for alias
            alias_match = re.search(r'\.as\(["\'](\w+)["\']\)', content[match.end():match.end()+100])
            if alias_match:
                intercept_info['alias'] = alias_match.group(1)
            
            intercepts.append(intercept_info)
        
        return intercepts
    
    def _classify_intercept(self, args: str) -> str:
        """Classify intercept type."""
        if 'method:' in args or 'Method:' in args:
            return 'method_specific'
        elif '{' in args and 'statusCode' in args:
            return 'with_response'
        elif 'fixture:' in args or 'fixture(' in args:
            return 'with_fixture'
        elif 'req =>' in args or 'request =>' in args:
            return 'with_handler'
        else:
            return 'basic'
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze intercept usage in project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        test_files = list(project_path.rglob("*.cy.js"))
        test_files.extend(project_path.rglob("*.cy.ts"))
        test_files.extend(project_path.rglob("*.spec.js"))
        test_files.extend(project_path.rglob("*.spec.ts"))
        
        all_intercepts = []
        intercept_types = {}
        routes_intercepted = set()
        aliases_used = set()
        
        for test_file in test_files:
            intercepts = self.extract_intercepts(test_file)
            all_intercepts.extend(intercepts)
            
            for intercept in intercepts:
                # Count types
                i_type = intercept['type']
                intercept_types[i_type] = intercept_types.get(i_type, 0) + 1
                
                # Collect routes and aliases
                if 'route' in intercept:
                    routes_intercepted.add(intercept['route'])
                if 'alias' in intercept:
                    aliases_used.add(intercept['alias'])
        
        return {
            'total_intercepts': len(all_intercepts),
            'intercepts': all_intercepts,
            'intercept_types': intercept_types,
            'routes_intercepted': sorted(routes_intercepted),
            'aliases_used': sorted(aliases_used),
        }
    
    def convert_to_playwright(self, intercept: Dict) -> str:
        """
        Convert Cypress intercept to Playwright route.
        
        Args:
            intercept: Intercept dictionary
            
        Returns:
            Playwright code
        """
        route = intercept.get('route', '**/*')
        intercept_type = intercept['type']
        
        lines = []
        
        if intercept_type == 'with_response':
            lines.append(f"await page.route('{route}', (route) => {{")
            lines.append("    route.fulfill({")
            lines.append("        status: 200,")
            lines.append("        body: JSON.stringify({ data: 'mock' }),")
            lines.append("    });")
            lines.append("});")
        elif intercept_type == 'with_fixture':
            lines.append(f"await page.route('{route}', (route) => {{")
            lines.append("    route.fulfill({")
            lines.append("        path: './fixtures/data.json',")
            lines.append("    });")
            lines.append("});")
        else:
            lines.append(f"await page.route('{route}', (route) => route.continue());")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for intercept usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Cypress Intercept Usage\n")
        
        lines.append("## Summary\n")
        lines.append(f"- Total intercepts: {analysis['total_intercepts']}")
        lines.append(f"- Unique routes: {len(analysis['routes_intercepted'])}")
        lines.append(f"- Aliases used: {len(analysis['aliases_used'])}\n")
        
        lines.append("## Intercept Types\n")
        for i_type, count in analysis['intercept_types'].items():
            lines.append(f"- {i_type}: {count}")
        lines.append("")
        
        if analysis['routes_intercepted']:
            lines.append("## Common Routes\n")
            for route in analysis['routes_intercepted'][:10]:
                lines.append(f"- `{route}`")
        
        return '\n'.join(lines)
