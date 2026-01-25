"""
Component testing support for Cypress.

Handles React and Vue component test detection and conversion.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re
import json


class ComponentTestingSupport:
    """Handle Cypress component testing."""
    
    def __init__(self):
        """Initialize component testing support."""
        self.react_patterns = {
            'mount': re.compile(r'mount\(<(\w+)[^>]*>'),
            'import_react': re.compile(r'import\s+React\s+from\s+["\']react["\']'),
            'import_component': re.compile(r'import\s+\{?\s*(\w+)\s*\}?\s+from\s+["\']([^"\']+)["\']'),
            'cy_mount': re.compile(r'cy\.mount\('),
        }
        
        self.vue_patterns = {
            'mount': re.compile(r'mount\((\w+)'),
            'import_vue': re.compile(r'import\s+\{[^}]*createApp[^}]*\}\s+from\s+["\']vue["\']'),
            'import_component': re.compile(r'import\s+(\w+)\s+from\s+["\']([^"\']+\.vue)["\']'),
            'cy_mount': re.compile(r'cy\.mount\('),
        }
        
    def detect_framework(self, file_path: Path) -> Optional[str]:
        """
        Detect component testing framework (React or Vue).
        
        Args:
            file_path: Path to test file
            
        Returns:
            Framework name or None
        """
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        # Check for React
        if self.react_patterns['import_react'].search(content):
            return 'react'
        
        # Check for Vue
        if self.vue_patterns['import_vue'].search(content):
            return 'vue'
        
        # Check file extension
        if '.jsx' in file_path.suffix or '.tsx' in file_path.suffix:
            return 'react'
        
        return None
    
    def extract_react_components(self, file_path: Path) -> List[Dict]:
        """
        Extract React component tests.
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of component test dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        components = []
        
        # Find imported components
        for match in self.react_patterns['import_component'].finditer(content):
            component_name = match.group(1)
            import_path = match.group(2)
            
            # Check if component is mounted in tests
            mount_pattern = re.compile(rf'mount\(<{component_name}[^>]*>')
            if mount_pattern.search(content):
                components.append({
                    'name': component_name,
                    'import_path': import_path,
                    'framework': 'react',
                    'line': content[:match.start()].count('\n') + 1,
                })
        
        return components
    
    def extract_vue_components(self, file_path: Path) -> List[Dict]:
        """
        Extract Vue component tests.
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of component test dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        components = []
        
        # Find imported Vue components
        for match in self.vue_patterns['import_component'].finditer(content):
            component_name = match.group(1)
            import_path = match.group(2)
            
            # Check if component is mounted
            mount_pattern = re.compile(rf'mount\({component_name}')
            if mount_pattern.search(content):
                components.append({
                    'name': component_name,
                    'import_path': import_path,
                    'framework': 'vue',
                    'line': content[:match.start()].count('\n') + 1,
                })
        
        return components
    
    def extract_component_props(self, file_path: Path, component_name: str) -> List[Dict]:
        """
        Extract props passed to component in tests.
        
        Args:
            file_path: Path to test file
            component_name: Component name
            
        Returns:
            List of prop dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        props = []
        
        # Pattern for props in JSX/TSX
        props_pattern = re.compile(
            rf'<{component_name}\s+([^>]+)>',
            re.DOTALL
        )
        
        for match in props_pattern.finditer(content):
            props_str = match.group(1)
            
            # Extract individual props
            prop_pattern = re.compile(r'(\w+)=\{([^}]+)\}')
            for prop_match in prop_pattern.finditer(props_str):
                props.append({
                    'name': prop_match.group(1),
                    'value': prop_match.group(2),
                    'component': component_name,
                })
        
        return props
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze project for component testing usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        # Find component test files
        test_files = list(project_path.rglob("*.cy.jsx"))
        test_files.extend(project_path.rglob("*.cy.tsx"))
        test_files.extend(project_path.rglob("*.component.spec.js"))
        test_files.extend(project_path.rglob("*.component.spec.ts"))
        
        react_components = []
        vue_components = []
        all_props = []
        
        for test_file in test_files:
            framework = self.detect_framework(test_file)
            
            if framework == 'react':
                components = self.extract_react_components(test_file)
                react_components.extend(components)
                
                for component in components:
                    props = self.extract_component_props(test_file, component['name'])
                    all_props.extend(props)
            
            elif framework == 'vue':
                components = self.extract_vue_components(test_file)
                vue_components.extend(components)
                
                for component in components:
                    props = self.extract_component_props(test_file, component['name'])
                    all_props.extend(props)
        
        return {
            'test_files': len(test_files),
            'react_components': react_components,
            'vue_components': vue_components,
            'component_props': all_props,
            'total_components': len(react_components) + len(vue_components),
        }
    
    def generate_playwright_component_test(self, component: Dict) -> str:
        """
        Convert Cypress component test to Playwright component test.
        
        Args:
            component: Component dictionary
            
        Returns:
            Playwright test code
        """
        framework = component['framework']
        component_name = component['name']
        
        if framework == 'react':
            code = f'''
import {{ test, expect }} from '@playwright/experimental-ct-react';
import {component_name} from '{component['import_path']}';

test.describe('{component_name} Component', () => {{
    test('should render component', async ({{ mount }}) => {{
        const component = await mount(<{component_name} />);
        await expect(component).toBeVisible();
    }});
    
    test('should handle props', async ({{ mount }}) => {{
        const component = await mount(
            <{component_name} 
                prop1="value1"
                prop2="value2"
            />
        );
        await expect(component).toBeVisible();
    }});
}});
'''
        elif framework == 'vue':
            code = f'''
import {{ test, expect }} from '@playwright/experimental-ct-vue';
import {component_name} from '{component['import_path']}';

test.describe('{component_name} Component', () => {{
    test('should render component', async ({{ mount }}) => {{
        const component = await mount({component_name});
        await expect(component).toBeVisible();
    }});
    
    test('should handle props', async ({{ mount }}) => {{
        const component = await mount({component_name}, {{
            props: {{
                prop1: 'value1',
                prop2: 'value2',
            }},
        }});
        await expect(component).toBeVisible();
    }});
}});
'''
        else:
            code = "// Unsupported framework"
        
        return code
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for component testing usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Cypress Component Testing Usage\n")
        
        lines.append("## Summary\n")
        lines.append(f"- Test files analyzed: {analysis['test_files']}")
        lines.append(f"- React components: {len(analysis['react_components'])}")
        lines.append(f"- Vue components: {len(analysis['vue_components'])}")
        lines.append(f"- Total components: {analysis['total_components']}\n")
        
        if analysis['react_components']:
            lines.append("## React Components\n")
            for comp in analysis['react_components'][:5]:
                lines.append(f"- {comp['name']} (from {comp['import_path']})")
            lines.append("")
        
        if analysis['vue_components']:
            lines.append("## Vue Components\n")
            for comp in analysis['vue_components'][:5]:
                lines.append(f"- {comp['name']} (from {comp['import_path']})")
            lines.append("")
        
        return '\n'.join(lines)
