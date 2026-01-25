"""
Dependency Injection container support for SpecFlow.

Handles .NET DI container integration (Microsoft.Extensions.DependencyInjection).
"""

from typing import List, Dict, Optional
from pathlib import Path
import re
import xml.etree.ElementTree as ET


class DIContainerSupport:
    """Handle DI container support in SpecFlow."""
    
    def __init__(self):
        """Initialize DI container support."""
        self.container_patterns = {
            'service_collection': re.compile(r'IServiceCollection\s+(\w+)'),
            'add_singleton': re.compile(r'\.AddSingleton<(\w+)(?:,\s*(\w+))?>'),
            'add_scoped': re.compile(r'\.AddScoped<(\w+)(?:,\s*(\w+))?>'),
            'add_transient': re.compile(r'\.AddTransient<(\w+)(?:,\s*(\w+))?>'),
            'dependency_injection': re.compile(r'\[ScenarioDependencies\]'),
        }
        
    def extract_di_configuration(self, file_path: Path) -> Dict:
        """
        Extract DI configuration from C# file.
        
        Args:
            file_path: Path to C# file
            
        Returns:
            DI configuration dictionary
        """
        if not file_path.exists():
            return {}
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return {}
        
        config = {
            'file': str(file_path),
            'singletons': [],
            'scoped': [],
            'transients': [],
            'has_scenario_dependencies': False,
        }
        
        # Check for ScenarioDependencies attribute
        if self.container_patterns['dependency_injection'].search(content):
            config['has_scenario_dependencies'] = True
        
        # Extract singleton registrations
        for match in self.container_patterns['add_singleton'].finditer(content):
            interface = match.group(1)
            implementation = match.group(2) if match.group(2) else interface
            config['singletons'].append({
                'interface': interface,
                'implementation': implementation,
            })
        
        # Extract scoped registrations
        for match in self.container_patterns['add_scoped'].finditer(content):
            interface = match.group(1)
            implementation = match.group(2) if match.group(2) else interface
            config['scoped'].append({
                'interface': interface,
                'implementation': implementation,
            })
        
        # Extract transient registrations
        for match in self.container_patterns['add_transient'].finditer(content):
            interface = match.group(1)
            implementation = match.group(2) if match.group(2) else interface
            config['transients'].append({
                'interface': interface,
                'implementation': implementation,
            })
        
        return config
    
    def detect_constructor_injection(self, file_path: Path) -> List[Dict]:
        """
        Detect constructor injection in step definition classes.
        
        Args:
            file_path: Path to C# file
            
        Returns:
            List of constructor injection dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return []
        
        injections = []
        
        # Pattern for constructor with parameters
        ctor_pattern = re.compile(
            r'public\s+(\w+)\s*\(\s*([^)]+)\s*\)',
            re.MULTILINE
        )
        
        for match in ctor_pattern.finditer(content):
            class_name = match.group(1)
            params_str = match.group(2)
            
            # Parse parameters
            params = []
            for param in params_str.split(','):
                param = param.strip()
                if param:
                    parts = param.split()
                    if len(parts) >= 2:
                        param_type = parts[0]
                        param_name = parts[1]
                        params.append({
                            'type': param_type,
                            'name': param_name,
                        })
            
            if params:
                injections.append({
                    'class': class_name,
                    'parameters': params,
                    'line': content[:match.start()].count('\n') + 1,
                })
        
        return injections
    
    def generate_di_setup_code(self, config: Dict) -> str:
        """
        Generate DI container setup code for SpecFlow.
        
        Args:
            config: DI configuration dictionary
            
        Returns:
            C# code string
        """
        lines = []
        lines.append("using Microsoft.Extensions.DependencyInjection;")
        lines.append("using SolidToken.SpecFlow.DependencyInjection;")
        lines.append("using TechTalk.SpecFlow;")
        lines.append("")
        lines.append("namespace YourProject.Specs")
        lines.append("{")
        lines.append("    [Binding]")
        lines.append("    public static class TestDependencies")
        lines.append("    {")
        lines.append("        [ScenarioDependencies]")
        lines.append("        public static IServiceCollection CreateServices()")
        lines.append("        {")
        lines.append("            var services = new ServiceCollection();")
        lines.append("")
        
        # Add singleton registrations
        for service in config.get('singletons', []):
            if service['interface'] == service['implementation']:
                lines.append(f"            services.AddSingleton<{service['interface']}>();")
            else:
                lines.append(f"            services.AddSingleton<{service['interface']}, {service['implementation']}>();")
        
        # Add scoped registrations
        for service in config.get('scoped', []):
            if service['interface'] == service['implementation']:
                lines.append(f"            services.AddScoped<{service['interface']}>();")
            else:
                lines.append(f"            services.AddScoped<{service['interface']}, {service['implementation']}>();")
        
        # Add transient registrations
        for service in config.get('transients', []):
            if service['interface'] == service['implementation']:
                lines.append(f"            services.AddTransient<{service['interface']}>();")
            else:
                lines.append(f"            services.AddTransient<{service['interface']}, {service['implementation']}>();")
        
        lines.append("")
        lines.append("            return services;")
        lines.append("        }")
        lines.append("    }")
        lines.append("}")
        
        return '\n'.join(lines)
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze project for DI container usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        cs_files = list(project_path.rglob("*.cs"))
        
        all_configs = []
        all_injections = []
        
        for cs_file in cs_files:
            config = self.extract_di_configuration(cs_file)
            if any([config.get('singletons'), config.get('scoped'), config.get('transients')]):
                all_configs.append(config)
            
            injections = self.detect_constructor_injection(cs_file)
            all_injections.extend(injections)
        
        # Count service lifetimes
        total_singletons = sum(len(c.get('singletons', [])) for c in all_configs)
        total_scoped = sum(len(c.get('scoped', [])) for c in all_configs)
        total_transients = sum(len(c.get('transients', [])) for c in all_configs)
        
        return {
            'configurations': all_configs,
            'constructor_injections': all_injections,
            'service_counts': {
                'singletons': total_singletons,
                'scoped': total_scoped,
                'transients': total_transients,
            },
            'files_analyzed': len(cs_files),
        }
    
    def convert_to_pytest_fixtures(self, analysis: Dict) -> str:
        """
        Convert .NET DI services to pytest fixtures.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Python fixture code
        """
        lines = []
        lines.append("import pytest")
        lines.append("")
        
        # Generate fixtures for services
        all_services = set()
        for config in analysis['configurations']:
            for service in config.get('singletons', []):
                all_services.add((service['interface'], 'session'))
            for service in config.get('scoped', []):
                all_services.add((service['interface'], 'function'))
            for service in config.get('transients', []):
                all_services.add((service['interface'], 'function'))
        
        for service_name, scope in sorted(all_services):
            fixture_name = service_name.lower().replace('i', '', 1) if service_name.startswith('I') else service_name.lower()
            lines.append(f"@pytest.fixture(scope='{scope}')")
            lines.append(f"def {fixture_name}():")
            lines.append(f'    """Fixture for {service_name}."""')
            lines.append(f"    return {service_name}()")
            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for DI usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# SpecFlow Dependency Injection Usage\n")
        
        lines.append("## Service Registration Summary\n")
        counts = analysis['service_counts']
        lines.append(f"- Singleton services: {counts['singletons']}")
        lines.append(f"- Scoped services: {counts['scoped']}")
        lines.append(f"- Transient services: {counts['transients']}")
        lines.append(f"- Total services: {sum(counts.values())}\n")
        
        lines.append("## Constructor Injection\n")
        lines.append(f"Found {len(analysis['constructor_injections'])} classes using constructor injection\n")
        
        if analysis['constructor_injections']:
            lines.append("### Examples:\n")
            for injection in analysis['constructor_injections'][:3]:
                lines.append(f"**{injection['class']}**")
                for param in injection['parameters']:
                    lines.append(f"- {param['type']} {param['name']}")
                lines.append("")
        
        return '\n'.join(lines)
