"""
Cypress plugin integration and runtime hook support.

Handles Cypress plugin detection, configuration extraction, and hook transformation.
"""

import re
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CypressPlugin:
    """Represents a Cypress plugin configuration."""
    name: str
    package_name: str
    config: Dict[str, any]
    hooks: List[str]
    file_path: Path


class CypressPluginHandler:
    """Handle Cypress plugin detection and integration."""
    
    def __init__(self):
        # Common Cypress plugins
        self.known_plugins = {
            'cypress-mochawesome-reporter',
            'cypress-multi-reporters',
            '@badeball/cypress-cucumber-preprocessor',
            'cypress-file-upload',
            'cypress-axe',
            'cypress-real-events',
            'cypress-visual-regression',
            '@cypress/code-coverage',
            'cypress-grep',
            'cypress-terminal-report'
        }
        
        # Plugin registration patterns
        self.plugin_register_pattern = re.compile(
            r'on\s*\(\s*[\'"](\w+)[\'"]\s*,\s*([^)]+)\s*\)',
            re.DOTALL
        )
    
    def detect_plugins(self, project_root: Path) -> List[CypressPlugin]:
        """
        Detect installed Cypress plugins.
        
        Args:
            project_root: Root directory of Cypress project
            
        Returns:
            List of detected plugins
        """
        plugins = []
        
        # Check package.json for plugin dependencies
        package_json = project_root / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                
                dependencies = {**data.get('dependencies', {}), 
                              **data.get('devDependencies', {})}
                
                for plugin_name in self.known_plugins:
                    if plugin_name in dependencies:
                        # Look for plugin configuration
                        plugin_config = self._find_plugin_config(
                            project_root,
                            plugin_name
                        )
                        
                        plugins.append(CypressPlugin(
                            name=plugin_name.replace('cypress-', '').replace('@', ''),
                            package_name=plugin_name,
                            config=plugin_config,
                            hooks=self._get_plugin_hooks(plugin_name),
                            file_path=project_root / 'cypress' / 'plugins' / 'index.js'
                        ))
            except (json.JSONDecodeError, IOError):
                pass
        
        return plugins
    
    def _find_plugin_config(
        self,
        project_root: Path,
        plugin_name: str
    ) -> Dict[str, any]:
        """Find configuration for a specific plugin."""
        config = {}
        
        # Check cypress.config.js/ts
        for config_file in ['cypress.config.js', 'cypress.config.ts', 'cypress.json']:
            config_path = project_root / config_file
            if config_path.exists():
                content = config_path.read_text(encoding='utf-8')
                
                # Extract plugin-specific config
                plugin_key = plugin_name.replace('cypress-', '').replace('@', '').replace('/', '-')
                pattern = re.compile(
                    rf'{plugin_key}\s*:\s*\{{([^}}]+)\}}',
                    re.DOTALL | re.IGNORECASE
                )
                match = pattern.search(content)
                if match:
                    # Parse config (simplified)
                    config_str = match.group(1)
                    config = self._parse_config_object(config_str)
                    break
        
        return config
    
    def _parse_config_object(self, config_str: str) -> Dict[str, any]:
        """Parse a JavaScript config object string (simplified)."""
        config = {}
        
        # Extract key-value pairs (simplified parser)
        pairs = re.findall(r'(\w+)\s*:\s*([^,}]+)', config_str)
        for key, value in pairs:
            value = value.strip()
            # Handle simple types
            if value.lower() in ('true', 'false'):
                config[key] = value.lower() == 'true'
            elif value.isdigit():
                config[key] = int(value)
            elif value.startswith('"') or value.startswith("'"):
                config[key] = value.strip('"\'')
            else:
                config[key] = value
        
        return config
    
    def _get_plugin_hooks(self, plugin_name: str) -> List[str]:
        """Get lifecycle hooks provided by a plugin."""
        hook_map = {
            'cypress-mochawesome-reporter': ['after:run', 'after:spec'],
            '@badeball/cypress-cucumber-preprocessor': ['file:preprocessor'],
            'cypress-file-upload': [],
            'cypress-axe': [],
            '@cypress/code-coverage': ['after:run', 'task'],
            'cypress-grep': ['before:run'],
            'cypress-terminal-report': ['task', 'after:run']
        }
        return hook_map.get(plugin_name, [])
    
    def extract_plugin_hooks(self, plugins_file: Path) -> List[Dict[str, any]]:
        """
        Extract plugin hook registrations from plugins file.
        
        Args:
            plugins_file: Path to cypress/plugins/index.js or config file
            
        Returns:
            List of hook registrations
        """
        if not plugins_file.exists():
            return []
        
        content = plugins_file.read_text(encoding='utf-8')
        hooks = []
        
        for match in self.plugin_register_pattern.finditer(content):
            event_name = match.group(1)
            handler = match.group(2).strip()
            
            hooks.append({
                'event': event_name,
                'handler': handler,
                'line': content[:match.start()].count('\n') + 1
            })
        
        return hooks
    
    def has_plugin(self, project_root: Path, plugin_name: str) -> bool:
        """Check if a specific plugin is installed."""
        plugins = self.detect_plugins(project_root)
        return any(p.package_name == plugin_name for p in plugins)
    
    def get_plugin_setup_code(self, plugin: CypressPlugin) -> str:
        """
        Generate setup code for a plugin in Robot Framework or Playwright.
        
        Args:
            plugin: CypressPlugin object
            
        Returns:
            Setup code as string
        """
        if 'mochawesome' in plugin.package_name:
            return "# Setup HTML reporter equivalent\n" \
                   "# Consider: pytest-html or robotframework-reportportal"
        
        elif 'cucumber' in plugin.package_name:
            return "# BDD features already supported natively\n" \
                   "# No additional setup needed"
        
        elif 'file-upload' in plugin.package_name:
            return "# File upload keyword:\n" \
                   "# Choose File    id=file-input    ${EXECDIR}/testfile.pdf"
        
        elif 'axe' in plugin.package_name:
            return "# Accessibility testing:\n" \
                   "# Consider: axe-selenium-python or axe-playwright-python"
        
        elif 'coverage' in plugin.package_name:
            return "# Code coverage already available via coverage.py\n" \
                   "# See: pytest --cov or Robot Framework coverage plugin"
        
        else:
            return f"# Plugin: {plugin.name}\n" \
                   f"# Manual configuration may be required"
