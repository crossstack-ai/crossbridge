"""
Multi-configuration file handler for Cypress.

Handles multiple cypress.config.js files and environment-specific configs.
"""

from typing import List, Dict, Optional
from pathlib import Path
import json
import re


class MultiConfigHandler:
    """Handle multiple Cypress configuration files."""
    
    def __init__(self):
        """Initialize the config handler."""
        self.config_patterns = {
            'define_config': re.compile(r'defineConfig\(\{([^}]+(?:\{[^}]+\})*[^}]+)\}\)'),
            'base_url': re.compile(r'baseUrl:\s*["\']([^"\']+)["\']'),
            'env_vars': re.compile(r'env:\s*\{([^}]+)\}'),
        }
        
    def find_config_files(self, project_path: Path) -> List[Path]:
        """
        Find all Cypress configuration files.
        
        Args:
            project_path: Project root path
            
        Returns:
            List of config file paths
        """
        config_files = []
        
        # Standard config files
        standard_configs = [
            'cypress.config.js',
            'cypress.config.ts',
            'cypress.json',  # Legacy
        ]
        
        for config_name in standard_configs:
            config_path = project_path / config_name
            if config_path.exists():
                config_files.append(config_path)
        
        # Environment-specific configs
        config_files.extend(project_path.glob('cypress.*.config.js'))
        config_files.extend(project_path.glob('cypress.*.config.ts'))
        
        # Config directory
        config_dir = project_path / 'cypress' / 'config'
        if config_dir.exists():
            config_files.extend(config_dir.glob('*.config.js'))
            config_files.extend(config_dir.glob('*.config.ts'))
        
        return config_files
    
    def parse_config_file(self, file_path: Path) -> Dict:
        """
        Parse Cypress configuration file.
        
        Args:
            file_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        if not file_path.exists():
            return {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return {}
        
        config = {
            'file': str(file_path),
            'base_url': None,
            'env_vars': {},
            'e2e_config': {},
            'component_config': {},
        }
        
        # Extract base URL
        base_url_match = self.config_patterns['base_url'].search(content)
        if base_url_match:
            config['base_url'] = base_url_match.group(1)
        
        # Extract environment variables
        env_match = self.config_patterns['env_vars'].search(content)
        if env_match:
            env_str = env_match.group(1)
            # Simple key-value extraction
            kv_pattern = re.compile(r'(\w+):\s*["\']([^"\']+)["\']')
            for kv_match in kv_pattern.finditer(env_str):
                config['env_vars'][kv_match.group(1)] = kv_match.group(2)
        
        # Check for e2e configuration
        if 'e2e:' in content or 'e2e {' in content:
            config['e2e_config']['enabled'] = True
            
            # Extract spec pattern
            spec_pattern = re.search(r'specPattern:\s*["\']([^"\']+)["\']', content)
            if spec_pattern:
                config['e2e_config']['spec_pattern'] = spec_pattern.group(1)
        
        # Check for component configuration
        if 'component:' in content or 'component {' in content:
            config['component_config']['enabled'] = True
            
            # Extract dev server
            if 'devServer' in content:
                config['component_config']['has_dev_server'] = True
        
        return config
    
    def merge_configs(self, base_config: Dict, override_config: Dict) -> Dict:
        """
        Merge two configuration dictionaries.
        
        Args:
            base_config: Base configuration
            override_config: Override configuration
            
        Returns:
            Merged configuration
        """
        merged = base_config.copy()
        
        # Merge base_url
        if override_config.get('base_url'):
            merged['base_url'] = override_config['base_url']
        
        # Merge env vars
        merged['env_vars'].update(override_config.get('env_vars', {}))
        
        # Merge e2e config
        merged['e2e_config'].update(override_config.get('e2e_config', {}))
        
        # Merge component config
        merged['component_config'].update(override_config.get('component_config', {}))
        
        return merged
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze project for multi-config usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        config_files = self.find_config_files(project_path)
        
        configs = []
        base_config = None
        environment_configs = {}
        
        for config_file in config_files:
            config = self.parse_config_file(config_file)
            configs.append(config)
            
            file_name = config_file.name
            if file_name in ['cypress.config.js', 'cypress.config.ts']:
                base_config = config
            else:
                # Extract environment name
                env_match = re.search(r'cypress\.(\w+)\.config', file_name)
                if env_match:
                    env_name = env_match.group(1)
                    environment_configs[env_name] = config
        
        return {
            'config_files': len(config_files),
            'base_config': base_config,
            'environment_configs': environment_configs,
            'all_configs': configs,
        }
    
    def generate_playwright_configs(self, analysis: Dict) -> Dict[str, str]:
        """
        Generate Playwright configuration files from Cypress configs.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Dictionary of {filename: content}
        """
        playwright_configs = {}
        
        # Generate base config
        if analysis['base_config']:
            base_config = self._generate_playwright_config(
                analysis['base_config'],
                'playwright.config.ts'
            )
            playwright_configs['playwright.config.ts'] = base_config
        
        # Generate environment configs
        for env_name, config in analysis['environment_configs'].items():
            pw_config = self._generate_playwright_config(
                config,
                f'playwright.{env_name}.config.ts'
            )
            playwright_configs[f'playwright.{env_name}.config.ts'] = pw_config
        
        return playwright_configs
    
    def _generate_playwright_config(self, cypress_config: Dict, filename: str) -> str:
        """
        Generate Playwright config from Cypress config.
        
        Args:
            cypress_config: Cypress configuration
            filename: Output filename
            
        Returns:
            Playwright config content
        """
        lines = []
        lines.append("import { defineConfig, devices } from '@playwright/test';")
        lines.append("")
        lines.append("export default defineConfig({")
        
        # Test directory
        if cypress_config.get('e2e_config', {}).get('spec_pattern'):
            lines.append("  testDir: './tests',")
        else:
            lines.append("  testDir: './e2e',")
        
        # Timeout
        lines.append("  timeout: 30000,")
        
        # Base URL
        if cypress_config.get('base_url'):
            lines.append(f"  use: {{")
            lines.append(f"    baseURL: '{cypress_config['base_url']}',")
            lines.append("  },")
        
        # Projects
        lines.append("  projects: [")
        lines.append("    {")
        lines.append("      name: 'chromium',")
        lines.append("      use: { ...devices['Desktop Chrome'] },")
        lines.append("    },")
        lines.append("  ],")
        
        lines.append("});")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for multi-config usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Cypress Multi-Configuration Usage\n")
        
        lines.append(f"## Configuration Files\n")
        lines.append(f"Found {analysis['config_files']} configuration files\n")
        
        if analysis['base_config']:
            lines.append("### Base Configuration\n")
            base = analysis['base_config']
            if base.get('base_url'):
                lines.append(f"- Base URL: {base['base_url']}")
            if base.get('env_vars'):
                lines.append(f"- Environment variables: {len(base['env_vars'])}")
            lines.append("")
        
        if analysis['environment_configs']:
            lines.append("### Environment Configurations\n")
            for env_name in analysis['environment_configs'].keys():
                lines.append(f"- {env_name}")
            lines.append("")
        
        return '\n'.join(lines)
