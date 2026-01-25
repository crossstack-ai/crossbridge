"""
TypeScript type generation for Cypress tests.

Generates TypeScript type definitions for Cypress custom commands and fixtures.
"""

from typing import List, Dict, Optional
from pathlib import Path
import ast
import re
import json


class TypeScriptTypeGenerator:
    """Generate TypeScript type definitions for Cypress."""
    
    def __init__(self):
        """Initialize the type generator."""
        self.custom_commands = []
        self.fixtures = {}
        
    def extract_custom_commands(self, file_path: Path) -> List[Dict]:
        """
        Extract custom Cypress commands from support files.
        
        Args:
            file_path: Path to Cypress support file
            
        Returns:
            List of custom command dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return []
        
        commands = []
        
        # Pattern for Cypress.Commands.add()
        pattern = re.compile(
            r'Cypress\.Commands\.add\(["\'](\w+)["\']\s*,\s*(?:\{[^}]*\}\s*,\s*)?\(?([^)]*)\)?\s*=>\s*\{'
        )
        
        for match in pattern.finditer(content):
            command_name = match.group(1)
            params_str = match.group(2).strip()
            
            # Parse parameters
            params = []
            if params_str:
                for param in params_str.split(','):
                    param = param.strip()
                    if param:
                        # Handle default values
                        if '=' in param:
                            param_name = param.split('=')[0].strip()
                            default_value = param.split('=')[1].strip()
                            params.append({
                                'name': param_name,
                                'optional': True,
                                'default': default_value,
                            })
                        else:
                            params.append({
                                'name': param,
                                'optional': False,
                            })
            
            commands.append({
                'name': command_name,
                'parameters': params,
                'line': content[:match.start()].count('\n') + 1,
            })
        
        return commands
    
    def infer_parameter_type(self, param_name: str, default_value: Optional[str] = None) -> str:
        """
        Infer TypeScript type from parameter name and default value.
        
        Args:
            param_name: Parameter name
            default_value: Default value string
            
        Returns:
            TypeScript type string
        """
        # Type hints from naming conventions
        if 'url' in param_name.lower() or 'path' in param_name.lower():
            return 'string'
        elif 'count' in param_name.lower() or 'timeout' in param_name.lower():
            return 'number'
        elif 'is' in param_name.lower() or 'has' in param_name.lower():
            return 'boolean'
        elif 'options' in param_name.lower() or 'config' in param_name.lower():
            return 'object'
        
        # Type hints from default values
        if default_value:
            if default_value in ['true', 'false']:
                return 'boolean'
            elif default_value.isdigit():
                return 'number'
            elif default_value.startswith('"') or default_value.startswith("'"):
                return 'string'
            elif default_value.startswith('{'):
                return 'object'
            elif default_value.startswith('['):
                return 'any[]'
        
        return 'any'
    
    def generate_command_types(self, commands: List[Dict]) -> str:
        """
        Generate TypeScript type definitions for custom commands.
        
        Args:
            commands: List of command dictionaries
            
        Returns:
            TypeScript type definition string
        """
        lines = []
        lines.append("/// <reference types=\"cypress\" />")
        lines.append("")
        lines.append("declare namespace Cypress {")
        lines.append("  interface Chainable {")
        
        for command in commands:
            # Build parameter list
            params = []
            for param in command['parameters']:
                param_name = param['name']
                param_type = self.infer_parameter_type(
                    param_name,
                    param.get('default')
                )
                optional_marker = '?' if param.get('optional') else ''
                params.append(f"{param_name}{optional_marker}: {param_type}")
            
            params_str = ', '.join(params)
            
            # Generate JSDoc comment
            lines.append(f"    /**")
            lines.append(f"     * Custom command: {command['name']}")
            for param in command['parameters']:
                param_name = param['name']
                param_type = self.infer_parameter_type(
                    param_name,
                    param.get('default')
                )
                lines.append(f"     * @param {param_name} - {param_type}")
            lines.append(f"     */")
            
            # Generate method signature
            lines.append(f"    {command['name']}({params_str}): Chainable<any>;")
            lines.append("")
        
        lines.append("  }")
        lines.append("}")
        lines.append("")
        
        return '\n'.join(lines)
    
    def extract_fixture_schemas(self, fixtures_path: Path) -> Dict[str, Dict]:
        """
        Extract fixture schemas from JSON files.
        
        Args:
            fixtures_path: Path to fixtures directory
            
        Returns:
            Dictionary mapping fixture names to schemas
        """
        if not fixtures_path.exists():
            return {}
        
        schemas = {}
        
        for fixture_file in fixtures_path.rglob("*.json"):
            try:
                with open(fixture_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                fixture_name = fixture_file.stem
                schema = self._infer_schema_from_data(data)
                schemas[fixture_name] = schema
            except (json.JSONDecodeError, OSError):
                continue
        
        return schemas
    
    def _infer_schema_from_data(self, data: any) -> Dict:
        """
        Infer TypeScript interface from JSON data.
        
        Args:
            data: JSON data
            
        Returns:
            Schema dictionary
        """
        if isinstance(data, dict):
            properties = {}
            for key, value in data.items():
                properties[key] = self._infer_type(value)
            return {'type': 'object', 'properties': properties}
        elif isinstance(data, list):
            if data:
                item_type = self._infer_type(data[0])
                return {'type': 'array', 'items': item_type}
            return {'type': 'array', 'items': 'any'}
        else:
            return {'type': self._infer_type(data)}
    
    def _infer_type(self, value: any) -> str:
        """
        Infer TypeScript type from value.
        
        Args:
            value: Value to infer type from
            
        Returns:
            TypeScript type string
        """
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int) or isinstance(value, float):
            return 'number'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, list):
            return 'any[]'
        elif isinstance(value, dict):
            return 'object'
        elif value is None:
            return 'null'
        else:
            return 'any'
    
    def generate_fixture_types(self, schemas: Dict[str, Dict]) -> str:
        """
        Generate TypeScript interfaces for fixtures.
        
        Args:
            schemas: Dictionary of fixture schemas
            
        Returns:
            TypeScript interface definitions
        """
        lines = []
        lines.append("// Fixture type definitions")
        lines.append("")
        
        for fixture_name, schema in schemas.items():
            interface_name = self._to_pascal_case(fixture_name)
            
            if schema['type'] == 'object':
                lines.append(f"export interface {interface_name} {{")
                for prop_name, prop_type in schema.get('properties', {}).items():
                    if isinstance(prop_type, dict):
                        type_str = prop_type.get('type', 'any')
                    else:
                        type_str = prop_type
                    lines.append(f"  {prop_name}: {type_str};")
                lines.append("}")
                lines.append("")
            else:
                lines.append(f"export type {interface_name} = {schema['type']};")
                lines.append("")
        
        return '\n'.join(lines)
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """
        Convert string to PascalCase.
        
        Args:
            snake_str: String in snake_case
            
        Returns:
            String in PascalCase
        """
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)
    
    def generate_all_types(self, cypress_path: Path) -> Dict[str, str]:
        """
        Generate all TypeScript type definitions for Cypress project.
        
        Args:
            cypress_path: Path to Cypress directory
            
        Returns:
            Dictionary mapping file names to type definition content
        """
        result = {}
        
        # Extract custom commands
        support_path = cypress_path / "support"
        if support_path.exists():
            all_commands = []
            for support_file in support_path.rglob("*.js"):
                commands = self.extract_custom_commands(support_file)
                all_commands.extend(commands)
            
            if all_commands:
                result['commands.d.ts'] = self.generate_command_types(all_commands)
        
        # Extract fixture schemas
        fixtures_path = cypress_path / "fixtures"
        if fixtures_path.exists():
            schemas = self.extract_fixture_schemas(fixtures_path)
            if schemas:
                result['fixtures.d.ts'] = self.generate_fixture_types(schemas)
        
        return result
    
    def write_type_definitions(self, cypress_path: Path, types: Dict[str, str]) -> List[Path]:
        """
        Write type definition files to disk.
        
        Args:
            cypress_path: Path to Cypress directory
            types: Dictionary of type definitions
            
        Returns:
            List of written file paths
        """
        support_path = cypress_path / "support"
        support_path.mkdir(parents=True, exist_ok=True)
        
        written_files = []
        
        for filename, content in types.items():
            file_path = support_path / filename
            file_path.write_text(content, encoding='utf-8')
            written_files.append(file_path)
        
        return written_files
    
    def generate_tsconfig(self) -> str:
        """
        Generate tsconfig.json for Cypress.
        
        Returns:
            JSON configuration string
        """
        config = {
            "compilerOptions": {
                "target": "es5",
                "lib": ["es5", "dom"],
                "types": ["cypress", "node"],
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
            },
            "include": [
                "**/*.ts",
                "**/*.d.ts"
            ],
            "exclude": [
                "node_modules"
            ]
        }
        
        return json.dumps(config, indent=2)
