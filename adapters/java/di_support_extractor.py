"""
Dependency Injection (DI) support extractor for Java tests.

Handles Guice and Spring DI patterns commonly used in test frameworks.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import re


class JavaDependencyInjectionExtractor:
    """Extract dependency injection patterns from Java test code."""
    
    def __init__(self):
        """Initialize the DI extractor."""
        self.guice_patterns = {
            'inject_annotation': re.compile(r'@Inject\s+(?:private\s+)?(\w+)\s+(\w+);'),
            'module_class': re.compile(r'class\s+(\w+)\s+extends\s+AbstractModule'),
            'bind_statement': re.compile(r'bind\((\w+)\.class\)\.to\((\w+)\.class\)'),
            'provider_method': re.compile(r'@Provides\s+(?:\w+\s+)?(\w+)\s+(\w+)\('),
        }
        
        self.spring_patterns = {
            'autowired': re.compile(r'@Autowired\s+(?:private\s+)?(\w+)\s+(\w+);'),
            'component': re.compile(r'@Component\s+(?:class|interface)\s+(\w+)'),
            'configuration': re.compile(r'@Configuration\s+(?:class)\s+(\w+)'),
            'bean_method': re.compile(r'@Bean\s+(?:public\s+)?(\w+)\s+(\w+)\('),
            'qualifier': re.compile(r'@Qualifier\("([^"]+)"\)'),
        }
    
    def detect_di_framework(self, file_path: Path) -> Optional[str]:
        """
        Detect which DI framework is being used.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            'guice', 'spring', or None
        """
        if not file_path.exists():
            return None
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        has_guice = any([
            'com.google.inject' in content,
            '@Inject' in content and 'AbstractModule' in content,
            '@Provides' in content,
        ])
        
        has_spring = any([
            'org.springframework' in content,
            '@Autowired' in content,
            '@Component' in content,
            '@Configuration' in content,
            '@Bean' in content,
        ])
        
        if has_guice:
            return 'guice'
        elif has_spring:
            return 'spring'
        return None
    
    def extract_guice_injections(self, file_path: Path) -> List[Dict]:
        """
        Extract Guice @Inject fields and dependencies.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of injection dictionaries
        """
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        injections = []
        
        # Find @Inject fields
        for match in self.guice_patterns['inject_annotation'].finditer(content):
            type_name = match.group(1)
            field_name = match.group(2)
            
            injections.append({
                'framework': 'guice',
                'annotation': '@Inject',
                'type': type_name,
                'field': field_name,
                'line': content[:match.start()].count('\n') + 1,
            })
        
        return injections
    
    def extract_guice_modules(self, file_path: Path) -> List[Dict]:
        """
        Extract Guice module definitions.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of module dictionaries
        """
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        modules = []
        
        # Find Module classes
        for match in self.guice_patterns['module_class'].finditer(content):
            module_name = match.group(1)
            
            # Find bind statements in this module
            bindings = []
            for bind_match in self.guice_patterns['bind_statement'].finditer(content):
                interface = bind_match.group(1)
                implementation = bind_match.group(2)
                bindings.append({
                    'interface': interface,
                    'implementation': implementation,
                })
            
            # Find @Provides methods
            providers = []
            for prov_match in self.guice_patterns['provider_method'].finditer(content):
                return_type = prov_match.group(1)
                method_name = prov_match.group(2)
                providers.append({
                    'return_type': return_type,
                    'method': method_name,
                })
            
            modules.append({
                'name': module_name,
                'bindings': bindings,
                'providers': providers,
                'file': str(file_path),
            })
        
        return modules
    
    def extract_spring_injections(self, file_path: Path) -> List[Dict]:
        """
        Extract Spring @Autowired fields and dependencies.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of injection dictionaries
        """
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        injections = []
        
        # Find @Autowired fields
        for match in self.spring_patterns['autowired'].finditer(content):
            type_name = match.group(1)
            field_name = match.group(2)
            
            # Check for @Qualifier
            qualifier = None
            qualifier_match = self.spring_patterns['qualifier'].search(
                content[max(0, match.start() - 100):match.start()]
            )
            if qualifier_match:
                qualifier = qualifier_match.group(1)
            
            injections.append({
                'framework': 'spring',
                'annotation': '@Autowired',
                'type': type_name,
                'field': field_name,
                'qualifier': qualifier,
                'line': content[:match.start()].count('\n') + 1,
            })
        
        return injections
    
    def extract_spring_configuration(self, file_path: Path) -> Dict:
        """
        Extract Spring @Configuration class details.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            Configuration dictionary
        """
        if not file_path.exists():
            return {}
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Find @Configuration class
        config_match = self.spring_patterns['configuration'].search(content)
        if not config_match:
            return {}
        
        config_name = config_match.group(1)
        
        # Find @Bean methods
        beans = []
        for bean_match in self.spring_patterns['bean_method'].finditer(content):
            return_type = bean_match.group(1)
            method_name = bean_match.group(2)
            
            beans.append({
                'return_type': return_type,
                'method': method_name,
                'line': content[:bean_match.start()].count('\n') + 1,
            })
        
        # Find @Component classes
        components = []
        for comp_match in self.spring_patterns['component'].finditer(content):
            component_name = comp_match.group(1)
            components.append(component_name)
        
        return {
            'configuration_class': config_name,
            'beans': beans,
            'components': components,
            'file': str(file_path),
        }
    
    def extract_all_dependencies(self, project_path: Path) -> Dict:
        """
        Extract all DI dependencies from a project.
        
        Args:
            project_path: Root path of Java project
            
        Returns:
            Dictionary with all DI information
        """
        java_files = list(project_path.rglob("*.java"))
        
        result = {
            'guice': {
                'injections': [],
                'modules': [],
            },
            'spring': {
                'injections': [],
                'configurations': [],
            },
            'files_analyzed': len(java_files),
        }
        
        for java_file in java_files:
            framework = self.detect_di_framework(java_file)
            
            if framework == 'guice':
                injections = self.extract_guice_injections(java_file)
                modules = self.extract_guice_modules(java_file)
                
                result['guice']['injections'].extend(injections)
                result['guice']['modules'].extend(modules)
            
            elif framework == 'spring':
                injections = self.extract_spring_injections(java_file)
                config = self.extract_spring_configuration(java_file)
                
                result['spring']['injections'].extend(injections)
                if config:
                    result['spring']['configurations'].append(config)
        
        return result
    
    def convert_to_pytest_fixtures(self, di_info: Dict) -> str:
        """
        Convert DI patterns to pytest fixtures.
        
        Args:
            di_info: DI information dictionary
            
        Returns:
            Python pytest fixture code
        """
        fixtures = []
        fixtures.append("import pytest\n")
        
        # Convert Guice injections
        for injection in di_info.get('guice', {}).get('injections', []):
            fixture_name = injection['field'].lower()
            type_name = injection['type']
            
            fixtures.append(f"""
@pytest.fixture
def {fixture_name}():
    \"\"\"Fixture for {type_name}.\"\"\"
    return {type_name}()
""")
        
        # Convert Spring beans
        for config in di_info.get('spring', {}).get('configurations', []):
            for bean in config.get('beans', []):
                fixture_name = bean['method']
                return_type = bean['return_type']
                
                fixtures.append(f"""
@pytest.fixture
def {fixture_name}():
    \"\"\"Fixture for {return_type} bean.\"\"\"
    return {return_type}()
""")
        
        return '\n'.join(fixtures)
    
    def get_dependency_graph(self, di_info: Dict) -> Dict[str, Set[str]]:
        """
        Build dependency graph from DI information.
        
        Args:
            di_info: DI information dictionary
            
        Returns:
            Dictionary mapping types to their dependencies
        """
        graph = {}
        
        # Build from Guice bindings
        for module in di_info.get('guice', {}).get('modules', []):
            for binding in module.get('bindings', []):
                interface = binding['interface']
                implementation = binding['implementation']
                
                if implementation not in graph:
                    graph[implementation] = set()
                graph[implementation].add(interface)
        
        # Build from Spring beans
        for config in di_info.get('spring', {}).get('configurations', []):
            config_name = config['configuration_class']
            
            if config_name not in graph:
                graph[config_name] = set()
            
            for bean in config.get('beans', []):
                graph[config_name].add(bean['return_type'])
        
        return graph
