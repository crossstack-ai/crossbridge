"""
Multi-line string handler for Behave.

Handles multi-line strings (docstrings) in Gherkin scenarios.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class MultiLineStringHandler:
    """Handle multi-line strings in Behave scenarios."""
    
    def __init__(self):
        """Initialize the multi-line string handler."""
        self.docstring_pattern = re.compile(r'"""(.*?)"""', re.DOTALL)
        
    def extract_multiline_strings(self, feature_content: str) -> List[Dict]:
        """
        Extract multi-line strings from feature file.
        
        Args:
            feature_content: Feature file content
            
        Returns:
            List of multi-line string dictionaries
        """
        strings = []
        
        for match in self.docstring_pattern.finditer(feature_content):
            content = match.group(1).strip()
            line_num = feature_content[:match.start()].count('\n') + 1
            
            strings.append({
                'content': content,
                'line': line_num,
                'length': len(content.split('\n')),
                'type': 'docstring',
            })
        
        return strings
    
    def parse_step_with_text(self, step_line: str, following_lines: List[str]) -> Dict:
        """
        Parse step with multi-line text block.
        
        Args:
            step_line: Step definition line
            following_lines: Lines following the step
            
        Returns:
            Step information with text block
        """
        text_block = []
        in_text = False
        
        for line in following_lines:
            stripped = line.strip()
            if stripped == '"""':
                if not in_text:
                    in_text = True
                else:
                    break
            elif in_text:
                text_block.append(line)
        
        return {
            'step': step_line,
            'text_block': '\n'.join(text_block),
            'has_multiline': bool(text_block),
        }
    
    def extract_from_feature_file(self, file_path: Path) -> Dict:
        """
        Extract all multi-line strings from a feature file.
        
        Args:
            file_path: Path to .feature file
            
        Returns:
            Dictionary with extraction results
        """
        if not file_path.exists():
            return {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
        except Exception:
            return {}
        
        result = {
            'file': str(file_path),
            'multiline_strings': [],
            'steps_with_text': [],
        }
        
        # Extract docstrings
        result['multiline_strings'] = self.extract_multiline_strings(content)
        
        # Extract steps with text blocks
        for i, line in enumerate(lines):
            if any(line.strip().startswith(kw) for kw in ['Given', 'When', 'Then', 'And', 'But']):
                remaining_lines = lines[i+1:]
                step_info = self.parse_step_with_text(line, remaining_lines)
                if step_info['has_multiline']:
                    step_info['line'] = i + 1
                    result['steps_with_text'].append(step_info)
        
        return result
    
    def convert_to_pytest_bdd(self, step_info: Dict) -> str:
        """
        Convert Behave multi-line step to pytest-bdd.
        
        Args:
            step_info: Step information with text block
            
        Returns:
            Python code string
        """
        step_line = step_info['step'].strip()
        text_block = step_info['text_block']
        
        # Parse step type
        step_type = 'given'
        for kw in ['Given', 'When', 'Then']:
            if step_line.startswith(kw):
                step_type = kw.lower()
                break
        
        # Generate pytest-bdd step
        step_text = step_line.split(' ', 1)[1] if ' ' in step_line else step_line
        
        code = f'''
from pytest_bdd import {step_type}

@{step_type}('{step_text}')
def step_impl(context):
    """Step with multi-line text."""
    text = """
{text_block}
    """
    # Use text in implementation
    pass
'''
        return code
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze all feature files for multi-line strings.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        feature_files = list(project_path.rglob("*.feature"))
        
        all_multiline = []
        all_steps_with_text = []
        
        for feature_file in feature_files:
            result = self.extract_from_feature_file(feature_file)
            if result:
                all_multiline.extend(result.get('multiline_strings', []))
                all_steps_with_text.extend(result.get('steps_with_text', []))
        
        return {
            'total_feature_files': len(feature_files),
            'total_multiline_strings': len(all_multiline),
            'total_steps_with_text': len(all_steps_with_text),
            'multiline_strings': all_multiline,
            'steps_with_text': all_steps_with_text,
        }
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for multi-line string usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Behave Multi-line String Usage\n")
        
        lines.append(f"## Summary\n")
        lines.append(f"- Feature files analyzed: {analysis['total_feature_files']}")
        lines.append(f"- Multi-line strings found: {analysis['total_multiline_strings']}")
        lines.append(f"- Steps with text blocks: {analysis['total_steps_with_text']}\n")
        
        if analysis['steps_with_text']:
            lines.append("## Examples\n")
            for step in analysis['steps_with_text'][:3]:
                lines.append(f"**{step['step']}**")
                lines.append(f"```\n{step['text_block'][:200]}\n```\n")
        
        return '\n'.join(lines)
