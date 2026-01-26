"""
Network stubbing handler for Cypress.

Handles network mocking, fixtures, and response manipulation.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re
import json


class NetworkStubbingHandler:
    """Handle Cypress network stubbing and mocking."""
    
    def __init__(self):
        """Initialize the handler."""
        self.stub_patterns = {
            'fixture': re.compile(r'fixture\(["\']([^"\']+)["\']\)'),
            'body': re.compile(r'body:\s*(\{[^}]+\}|"[^"]+")'),
            'status_code': re.compile(r'statusCode:\s*(\d+)'),
            'delay': re.compile(r'delay:\s*(\d+)'),
        }
        
    def extract_fixtures(self, project_path: Path) -> List[Dict]:
        """
        Extract fixture files and usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            List of fixture dictionaries
        """
        fixtures_dir = project_path / "cypress" / "fixtures"
        if not fixtures_dir.exists():
            return []
        
        fixtures = []
        
        for fixture_file in fixtures_dir.rglob("*.json"):
            try:
                content = fixture_file.read_text(encoding='utf-8')
                data = json.loads(content)
                
                fixtures.append({
                    'file': str(fixture_file.relative_to(project_path)),
                    'name': fixture_file.stem,
                    'size': len(content),
                    'keys': list(data.keys()) if isinstance(data, dict) else [],
                    'type': 'array' if isinstance(data, list) else 'object',
                })
            except (json.JSONDecodeError, IOError) as e:
                # Skip invalid or unreadable files
                continue
        
        return fixtures
    
    def extract_fixture_usage(self, file_path: Path) -> List[Dict]:
        """
        Extract fixture usage from test file.
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of fixture usage dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        usages = []
        
        for match in self.stub_patterns['fixture'].finditer(content):
            fixture_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            usages.append({
                'fixture': fixture_name,
                'line': line_num,
                'file': str(file_path),
            })
        
        return usages
    
    def extract_inline_stubs(self, file_path: Path) -> List[Dict]:
        """
        Extract inline response stubs.
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of stub dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        stubs = []
        
        # Find intercept with body
        intercept_pattern = re.compile(
            r'cy\.intercept\([^)]*\{([^}]+)\}[^)]*\)',
            re.DOTALL
        )
        
        for match in intercept_pattern.finditer(content):
            stub_config = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            stub_info = {
                'line': line_num,
                'file': str(file_path),
            }
            
            # Extract status code
            status_match = self.stub_patterns['status_code'].search(stub_config)
            if status_match:
                stub_info['status_code'] = int(status_match.group(1))
            
            # Extract delay
            delay_match = self.stub_patterns['delay'].search(stub_config)
            if delay_match:
                stub_info['delay'] = int(delay_match.group(1))
            
            # Check for body
            if 'body:' in stub_config:
                stub_info['has_body'] = True
            
            # Only add if we extracted something useful
            if stub_info.get('status_code') or stub_info.get('has_body'):
                stubs.append(stub_info)
        
        return stubs
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze network stubbing in project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        test_files = list(project_path.rglob("*.cy.js"))
        test_files.extend(project_path.rglob("*.cy.ts"))
        
        fixtures = self.extract_fixtures(project_path)
        
        all_fixture_usages = []
        all_inline_stubs = []
        
        for test_file in test_files:
            fixture_usages = self.extract_fixture_usage(test_file)
            all_fixture_usages.extend(fixture_usages)
            
            inline_stubs = self.extract_inline_stubs(test_file)
            all_inline_stubs.extend(inline_stubs)
        
        # Count fixture usage frequency
        fixture_usage_counts = {}
        for usage in all_fixture_usages:
            fixture = usage['fixture']
            fixture_usage_counts[fixture] = fixture_usage_counts.get(fixture, 0) + 1
        
        return {
            'fixtures': fixtures,
            'fixture_usages': all_fixture_usages,
            'inline_stubs': all_inline_stubs,
            'fixture_usage_counts': fixture_usage_counts,
            'total_fixtures': len(fixtures),
            'total_inline_stubs': len(all_inline_stubs),
        }
    
    def generate_playwright_mocks(self, analysis: Dict) -> str:
        """
        Generate Playwright mock setup from Cypress stubs.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Playwright code
        """
        lines = []
        lines.append("import { test, expect } from '@playwright/test';")
        lines.append("")
        
        lines.append("test.describe('API Mocking', () => {")
        lines.append("    test.beforeEach(async ({ page }) => {")
        
        # Generate fixture-based mocks
        for fixture in analysis['fixtures'][:3]:
            fixture_name = fixture['name']
            lines.append(f"        // Mock with fixture: {fixture_name}")
            lines.append(f"        await page.route('**/api/{fixture_name}', (route) => {{")
            lines.append(f"            route.fulfill({{")
            lines.append(f"                path: './fixtures/{fixture_name}.json',")
            lines.append(f"            }});")
            lines.append("        });")
            lines.append("")
        
        lines.append("    });")
        lines.append("});")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for network stubbing.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Cypress Network Stubbing Usage\n")
        
        lines.append("## Summary\n")
        lines.append(f"- Total fixtures: {analysis['total_fixtures']}")
        lines.append(f"- Fixture usages: {len(analysis['fixture_usages'])}")
        lines.append(f"- Inline stubs: {analysis['total_inline_stubs']}\n")
        
        if analysis['fixtures']:
            lines.append("## Fixtures\n")
            for fixture in analysis['fixtures'][:10]:
                lines.append(f"- {fixture['name']} ({fixture['type']}, {fixture['size']} bytes)")
        
        return '\n'.join(lines)
