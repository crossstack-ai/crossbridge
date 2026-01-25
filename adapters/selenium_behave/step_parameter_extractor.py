"""
Step parameter extractor for Behave.

Extracts regex groups and step parameters from Behave step definitions.
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import ast
import re


class StepParameterExtractor:
    """Extract step parameters from Behave step definitions."""
    
    def __init__(self):
        """Initialize the step parameter extractor."""
        self.parameter_patterns = {
            'string': r'(["\'])([^"\']+)\1',
            'number': r'(\d+(?:\.\d+)?)',
            'word': r'(\w+)',
            'any': r'(.+)',
        }
        
    def extract_step_parameters(self, step_text: str) -> List[Dict]:
        """
        Extract parameters from a step text.
        
        Args:
            step_text: Step definition text with regex patterns
            
        Returns:
            List of parameter dictionaries
        """
        parameters = []
        
        # Find all capturing groups in the regex
        pattern = re.compile(r'\(([^)]+)\)')
        matches = pattern.finditer(step_text)
        
        for i, match in enumerate(matches):
            param_pattern = match.group(1)
            param_info = {
                'index': i,
                'pattern': param_pattern,
                'start': match.start(),
                'end': match.end(),
                'type': self._infer_parameter_type(param_pattern),
            }
            parameters.append(param_info)
        
        return parameters
    
    def _infer_parameter_type(self, pattern: str) -> str:
        """
        Infer the type of a parameter from its regex pattern.
        
        Args:
            pattern: Regex pattern string
            
        Returns:
            Type string
        """
        if pattern in [r'\d+', r'\d+\.\d+', r'\d+(?:\.\d+)?']:
            return 'number'
        elif pattern in [r'\w+']:
            return 'word'
        elif pattern in [r'.+', r'.*']:
            return 'any'
        elif pattern.startswith('[') and pattern.endswith(']'):
            return 'choice'
        else:
            return 'custom'
    
    def extract_from_decorator(self, node: ast.FunctionDef) -> Optional[Dict]:
        """
        Extract step information from step decorator.
        
        Args:
            node: AST function node
            
        Returns:
            Step information dictionary or None
        """
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                # Check if it's a step decorator
                if isinstance(decorator.func, ast.Attribute):
                    step_type = decorator.func.attr
                    if step_type in ['given', 'when', 'then', 'step']:
                        # Get step text
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            step_text = decorator.args[0].value
                            
                            return {
                                'type': step_type,
                                'text': step_text,
                                'function': node.name,
                                'parameters': self.extract_step_parameters(step_text),
                                'line': node.lineno,
                            }
        return None
    
    def extract_function_parameters(self, node: ast.FunctionDef) -> List[str]:
        """
        Extract function parameter names.
        
        Args:
            node: AST function node
            
        Returns:
            List of parameter names
        """
        params = []
        for arg in node.args.args:
            if arg.arg != 'context':  # Skip context parameter
                params.append(arg.arg)
        return params
    
    def match_step_to_function_params(self, step_info: Dict, func_params: List[str]) -> List[Dict]:
        """
        Match step parameters to function parameters.
        
        Args:
            step_info: Step information dictionary
            func_params: List of function parameter names
            
        Returns:
            List of matched parameter dictionaries
        """
        step_params = step_info['parameters']
        matched = []
        
        for i, (step_param, func_param) in enumerate(zip(step_params, func_params)):
            matched.append({
                'step_pattern': step_param['pattern'],
                'step_type': step_param['type'],
                'function_param': func_param,
                'index': i,
            })
        
        return matched
    
    def extract_from_file(self, file_path: Path) -> List[Dict]:
        """
        Extract all step parameters from a file.
        
        Args:
            file_path: Path to step definition file
            
        Returns:
            List of step information dictionaries
        """
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []
        
        steps = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                step_info = self.extract_from_decorator(node)
                if step_info:
                    func_params = self.extract_function_parameters(node)
                    step_info['function_params'] = func_params
                    step_info['matched_params'] = self.match_step_to_function_params(
                        step_info, func_params
                    )
                    step_info['file'] = str(file_path)
                    steps.append(step_info)
        
        return steps
    
    def extract_all_steps(self, project_path: Path) -> Dict:
        """
        Extract all step parameters from a project.
        
        Args:
            project_path: Root path of project
            
        Returns:
            Dictionary with all step information
        """
        # Find step definition files (usually in steps/ directory)
        step_files = []
        step_files.extend(project_path.rglob("steps/*.py"))
        step_files.extend(project_path.rglob("step_defs/*.py"))
        step_files.extend(project_path.rglob("*_steps.py"))
        
        all_steps = []
        for step_file in step_files:
            steps = self.extract_from_file(step_file)
            all_steps.extend(steps)
        
        # Group by step type
        by_type = {'given': [], 'when': [], 'then': [], 'step': []}
        for step in all_steps:
            by_type[step['type']].append(step)
        
        # Find parameter type distribution
        param_types = {}
        for step in all_steps:
            for param in step['parameters']:
                param_type = param['type']
                param_types[param_type] = param_types.get(param_type, 0) + 1
        
        return {
            'steps': all_steps,
            'by_type': by_type,
            'param_types': param_types,
            'total_steps': len(all_steps),
            'files_analyzed': len(step_files),
        }
    
    def convert_to_pytest_bdd(self, step_info: Dict) -> str:
        """
        Convert Behave step to pytest-bdd format.
        
        Args:
            step_info: Step information dictionary
            
        Returns:
            Python pytest-bdd code
        """
        step_type = step_info['type']
        step_text = step_info['text']
        func_name = step_info['function']
        func_params = step_info['function_params']
        
        # Build parameter list
        params_str = ', '.join(func_params) if func_params else ''
        
        code = f"""
from pytest_bdd import {step_type}, parsers

@{step_type}(parsers.re(r'{step_text}'))
def {func_name}({params_str}):
    \"\"\"Step: {step_text}\"\"\"
    pass
"""
        return code
    
    def generate_parameter_documentation(self, steps_info: Dict) -> str:
        """
        Generate documentation for step parameters.
        
        Args:
            steps_info: Steps information dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Behave Step Parameters\n")
        
        # Parameter type distribution
        lines.append("## Parameter Types\n")
        for param_type, count in sorted(steps_info['param_types'].items()):
            lines.append(f"- {param_type}: {count} occurrences")
        lines.append("")
        
        # Examples by type
        lines.append("## Step Examples\n")
        for step_type, steps in steps_info['by_type'].items():
            if steps:
                lines.append(f"### {step_type.title()} Steps\n")
                for step in steps[:5]:  # Show first 5
                    lines.append(f"**{step['text']}**")
                    if step['matched_params']:
                        lines.append("Parameters:")
                        for param in step['matched_params']:
                            lines.append(
                                f"- `{param['function_param']}`: "
                                f"{param['step_type']} ({param['step_pattern']})"
                            )
                    lines.append("")
        
        return '\n'.join(lines)
    
    def detect_parameter_conflicts(self, steps_info: Dict) -> List[Dict]:
        """
        Detect conflicting step definitions.
        
        Args:
            steps_info: Steps information dictionary
            
        Returns:
            List of conflict dictionaries
        """
        conflicts = []
        
        # Group steps by normalized text
        by_text = {}
        for step in steps_info['steps']:
            # Normalize by replacing parameters with placeholder
            normalized = re.sub(r'\([^)]+\)', '(PARAM)', step['text'])
            if normalized not in by_text:
                by_text[normalized] = []
            by_text[normalized].append(step)
        
        # Find duplicates
        for normalized_text, steps in by_text.items():
            if len(steps) > 1:
                conflicts.append({
                    'pattern': normalized_text,
                    'definitions': [
                        {'file': s['file'], 'line': s['line'], 'function': s['function']}
                        for s in steps
                    ],
                })
        
        return conflicts
    
    def generate_cucumber_expressions(self, step_info: Dict) -> str:
        """
        Convert regex patterns to Cucumber expressions.
        
        Args:
            step_info: Step information dictionary
            
        Returns:
            Cucumber expression string
        """
        text = step_info['text']
        
        # Replace common regex patterns with Cucumber expressions
        replacements = {
            r'(\d+)': '{int}',
            r'(\d+\.\d+)': '{float}',
            r'(\w+)': '{word}',
            r'(.+)': '{string}',
            r'(["\'])([^"\']+)\1': '"{string}"',
        }
        
        cucumber_expr = text
        for regex, cucumber in replacements.items():
            cucumber_expr = re.sub(regex, cucumber, cucumber_expr)
        
        return cucumber_expr
