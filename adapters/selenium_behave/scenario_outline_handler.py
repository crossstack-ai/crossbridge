"""
Scenario Outline handler for Behave.

Handles Scenario Outline with Examples tables and parameterization.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import re


class ScenarioOutlineHandler:
    """Handle Behave Scenario Outline and Examples."""
    
    def __init__(self):
        """Initialize the handler."""
        self.placeholder_pattern = re.compile(r'<(\w+)>')
        
    def extract_scenario_outlines(self, feature_file: Path) -> List[Dict]:
        """
        Extract Scenario Outline from feature file.
        
        Args:
            feature_file: Path to feature file
            
        Returns:
            List of outline dictionaries
        """
        if not feature_file.exists():
            return []
        
        try:
            feature_content = feature_file.read_text(encoding='utf-8')
        except Exception:
            return []
        
        lines = feature_content.split('\n')
        outlines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('Scenario Outline:'):
                outline_name = line.split(':', 1)[1].strip()
                
                # Extract steps
                steps = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('Examples:'):
                    step_line = lines[i].strip()
                    if step_line and any(step_line.startswith(kw) for kw in ['Given', 'When', 'Then', 'And', 'But']):
                        steps.append(step_line)
                    i += 1
                
                # Extract examples
                examples = []
                if i < len(lines) and lines[i].strip().startswith('Examples:'):
                    i += 1
                    # Skip empty lines
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    
                    # Extract header
                    if i < len(lines) and '|' in lines[i]:
                        header_line = lines[i].strip()
                        headers = [h.strip() for h in header_line.split('|') if h.strip()]
                        i += 1
                        
                        # Extract data rows
                        while i < len(lines) and '|' in lines[i]:
                            data_line = lines[i].strip()
                            if data_line and not data_line.startswith('|'):
                                break
                            values = [v.strip() for v in data_line.split('|') if v.strip()]
                            if values and len(values) == len(headers):
                                examples.append(dict(zip(headers, values)))
                            i += 1
                
                outlines.append({
                    'name': outline_name,
                    'steps': steps,
                    'examples': examples,
                    'placeholders': self._extract_placeholders(steps),
                })
            
            i += 1
        
        return outlines
    
    def _extract_placeholders(self, steps: List[str]) -> Set[str]:
        """Extract placeholders from steps."""
        placeholders = set()
        for step in steps:
            matches = self.placeholder_pattern.findall(step)
            placeholders.update(matches)
        return placeholders
    
    def expand_scenario_outline(self, outline: Dict) -> List[Dict]:
        """
        Expand Scenario Outline to concrete scenarios.
        
        Args:
            outline: Scenario outline dictionary
            
        Returns:
            List of expanded scenario dictionaries
        """
        expanded = []
        
        for i, example in enumerate(outline['examples']):
            scenario_name = f"{outline['name']} (Example {i+1})"
            
            # Replace placeholders in steps
            expanded_steps = []
            for step in outline['steps']:
                expanded_step = step
                for placeholder, value in example.items():
                    expanded_step = expanded_step.replace(f'<{placeholder}>', value)
                expanded_steps.append(expanded_step)
            
            expanded.append({
                'name': scenario_name,
                'steps': expanded_steps,
                'example_data': example,
            })
        
        return expanded
    
    def convert_to_pytest_parametrize(self, outline: Dict) -> str:
        """
        Convert Scenario Outline to pytest.mark.parametrize.
        
        Args:
            outline: Scenario outline dictionary
            
        Returns:
            Python code with parametrize
        """
        lines = []
        lines.append("import pytest")
        lines.append("from pytest_bdd import scenario, given, when, then")
        lines.append("")
        
        # Extract parameter names
        if outline['examples']:
            param_names = list(outline['examples'][0].keys())
            
            # Build parametrize decorator
            params_str = ', '.join(param_names)
            
            # Build test data
            test_data = []
            for example in outline['examples']:
                values = [example[name] for name in param_names]
                test_data.append(tuple(values))
            
            lines.append(f"@pytest.mark.parametrize('{params_str}', [")
            for data in test_data:
                lines.append(f"    {data},")
            lines.append("])")
            lines.append(f"def test_{outline['name'].lower().replace(' ', '_')}({params_str}):")
            lines.append('    """Generated from Scenario Outline."""')
            
            # Generate step implementations
            for step in outline['steps']:
                lines.append(f"    # {step}")
            
            lines.append("    pass")
        
        return '\n'.join(lines)
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze Scenario Outline usage in project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        feature_files = list(project_path.rglob("*.feature"))
        
        all_outlines = []
        total_examples = 0
        placeholders_used = set()
        
        for feature_file in feature_files:
            try:
                content = feature_file.read_text(encoding='utf-8')
            except Exception:
                continue
            
            outlines = self.extract_scenario_outlines(content)
            for outline in outlines:
                outline['file'] = str(feature_file)
                all_outlines.append(outline)
                total_examples += len(outline['examples'])
                placeholders_used.update(outline['placeholders'])
        
        return {
            'total_outlines': len(all_outlines),
            'total_examples': total_examples,
            'outlines': all_outlines,
            'common_placeholders': sorted(placeholders_used),
        }
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for Scenario Outline usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Behave Scenario Outline Usage\n")
        
        lines.append("## Summary\n")
        lines.append(f"- Total Scenario Outlines: {analysis['total_outlines']}")
        lines.append(f"- Total Examples: {analysis['total_examples']}")
        lines.append(f"- Common Placeholders: {', '.join(analysis['common_placeholders'])}\n")
        
        if analysis['outlines']:
            lines.append("## Example Outlines\n")
            for outline in analysis['outlines'][:3]:
                lines.append(f"### {outline['name']}")
                lines.append(f"- Steps: {len(outline['steps'])}")
                lines.append(f"- Examples: {len(outline['examples'])}")
                lines.append(f"- Placeholders: {', '.join(outline['placeholders'])}\n")
        
        return '\n'.join(lines)
