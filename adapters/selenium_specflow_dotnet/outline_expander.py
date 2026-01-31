"""
SpecFlow Scenario Outline Expansion Module

Provides intelligent expansion of Scenario Outline into individual scenario instances
with data from Examples tables.

This module addresses Gap 3.1 in the Framework Gap Analysis:
- Expands Scenario Outline into individual test scenarios
- Links example data to each scenario instance
- Tracks source outline reference
- Maintains tags and metadata from outline

Usage:
    from adapters.selenium_specflow_dotnet.outline_expander import expand_scenario_outlines
    
    expanded = expand_scenario_outlines(feature_content)
    
    for scenario in expanded:
        print(f"Scenario: {scenario['name']}")
        print(f"Example data: {scenario['example_data']}")
        print(f"Source: {scenario['source_outline']}")
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ScenarioType(Enum):
    """Type of scenario."""
    SCENARIO = "Scenario"
    SCENARIO_OUTLINE = "Scenario Outline"


@dataclass
class ExamplesTable:
    """Represents an Examples table from Scenario Outline."""
    headers: List[str]
    rows: List[List[str]]
    tags: List[str] = field(default_factory=list)
    
    def to_dict_list(self) -> List[Dict[str, str]]:
        """Convert examples table to list of dictionaries."""
        return [
            {header: value for header, value in zip(self.headers, row)}
            for row in self.rows
        ]


@dataclass
class ScenarioOutline:
    """Represents a Scenario Outline before expansion."""
    name: str
    steps: List[str]
    tags: List[str]
    examples: List[ExamplesTable]
    description: Optional[str] = None
    line_number: Optional[int] = None
    
    def get_parameter_names(self) -> List[str]:
        """Extract parameter names from steps (e.g., <username>, <password>)."""
        params = set()
        for step in self.steps:
            # Find all <param> patterns
            matches = re.findall(r'<(\w+)>', step)
            params.update(matches)
        return sorted(params)


@dataclass
class ExpandedScenario:
    """Represents an expanded scenario instance."""
    name: str
    original_name: str  # Name of source Scenario Outline
    steps: List[str]  # Steps with parameters replaced
    tags: List[str]
    example_data: Dict[str, str]  # Parameter values for this instance
    example_index: int  # Which example row (0-based)
    examples_table_index: int  # Which Examples table (0-based)
    source_outline: str  # Name of source Scenario Outline
    description: Optional[str] = None
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "name": self.name,
            "original_name": self.original_name,
            "steps": self.steps,
            "tags": self.tags,
            "example_data": self.example_data,
            "example_index": self.example_index,
            "examples_table_index": self.examples_table_index,
            "source_outline": self.source_outline,
            "description": self.description,
            "line_number": self.line_number,
            "type": "expanded_scenario"
        }


class ScenarioOutlineExpander:
    """
    Expands Scenario Outline into individual scenarios.
    
    Similar to Selenium Java BDD implementation, this creates one scenario
    instance per example row, with all parameters replaced.
    """
    
    def __init__(self):
        self.scenario_outline_pattern = re.compile(
            r'^\s*Scenario Outline:\s*(.+)$',
            re.MULTILINE
        )
        self.examples_pattern = re.compile(
            r'^\s*Examples:\s*$',
            re.MULTILINE
        )
        self.table_row_pattern = re.compile(
            r'^\s*\|(.+)\|$'
        )
        self.step_pattern = re.compile(
            r'^\s*(Given|When|Then|And|But)\s+(.+)$'
        )
        self.tag_pattern = re.compile(r'@(\w+)')
    
    def parse_feature_file(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse feature file and identify scenarios and outlines.
        
        Args:
            content: Feature file content
            
        Returns:
            List of scenarios (both regular and outlines)
        """
        scenarios = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for Scenario Outline
            if line.startswith('Scenario Outline:'):
                outline, next_i = self._parse_scenario_outline(lines, i)
                if outline:
                    scenarios.append({
                        'type': 'outline',
                        'data': outline
                    })
                i = next_i
                continue
            
            # Check for regular Scenario
            elif line.startswith('Scenario:'):
                scenario, next_i = self._parse_regular_scenario(lines, i)
                if scenario:
                    scenarios.append({
                        'type': 'scenario',
                        'data': scenario
                    })
                i = next_i
                continue
            
            i += 1
        
        return scenarios
    
    def _parse_scenario_outline(
        self,
        lines: List[str],
        start_index: int
    ) -> tuple[Optional[ScenarioOutline], int]:
        """Parse a Scenario Outline from lines."""
        line = lines[start_index].strip()
        
        # Extract name
        name_match = re.match(r'Scenario Outline:\s*(.+)$', line)
        if not name_match:
            return None, start_index + 1
        
        name = name_match.group(1).strip()
        
        # Look backwards for tags
        tags = []
        tag_index = start_index - 1
        while tag_index >= 0:
            tag_line = lines[tag_index].strip()
            if tag_line.startswith('@'):
                tags.extend(self.tag_pattern.findall(tag_line))
                tag_index -= 1
            else:
                break
        tags.reverse()
        
        # Parse steps until Examples
        steps = []
        i = start_index + 1
        description_lines = []
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            if line.startswith('Examples:'):
                break
            
            if line.startswith('Scenario') or line.startswith('Feature:'):
                break
            
            # Check if it's a step
            step_match = self.step_pattern.match(line)
            if step_match:
                keyword = step_match.group(1)
                text = step_match.group(2)
                steps.append(f"{keyword} {text}")
            elif not line.startswith('|') and not line.startswith('@'):
                # Description line
                description_lines.append(line)
            
            i += 1
        
        description = ' '.join(description_lines) if description_lines else None
        
        # Parse Examples tables
        examples = []
        while i < len(lines) and lines[i].strip().startswith('Examples:'):
            examples_table, next_i = self._parse_examples_table(lines, i)
            if examples_table:
                examples.append(examples_table)
            i = next_i
        
        outline = ScenarioOutline(
            name=name,
            steps=steps,
            tags=tags,
            examples=examples,
            description=description,
            line_number=start_index + 1
        )
        
        return outline, i
    
    def _parse_examples_table(
        self,
        lines: List[str],
        start_index: int
    ) -> tuple[Optional[ExamplesTable], int]:
        """Parse an Examples table."""
        i = start_index
        
        # Look for tags before Examples
        tags = []
        tag_index = i - 1
        while tag_index >= 0:
            tag_line = lines[tag_index].strip()
            if tag_line.startswith('@') and not tag_line.startswith('Scenario'):
                tags.extend(self.tag_pattern.findall(tag_line))
                tag_index -= 1
            else:
                break
        
        # Skip "Examples:" line
        i += 1
        
        # Skip empty lines
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        if i >= len(lines):
            return None, i
        
        # Parse header row
        header_line = lines[i].strip()
        if not header_line.startswith('|'):
            return None, i
        
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        i += 1
        
        # Parse data rows
        rows = []
        while i < len(lines):
            line = lines[i].strip()
            
            if not line.startswith('|'):
                break
            
            values = [v.strip() for v in line.split('|') if v.strip()]
            if len(values) == len(headers):
                rows.append(values)
            
            i += 1
        
        examples_table = ExamplesTable(
            headers=headers,
            rows=rows,
            tags=tags
        )
        
        return examples_table, i
    
    def _parse_regular_scenario(
        self,
        lines: List[str],
        start_index: int
    ) -> tuple[Optional[Dict], int]:
        """Parse a regular Scenario (not expanded, just identified)."""
        line = lines[start_index].strip()
        
        name_match = re.match(r'Scenario:\s*(.+)$', line)
        if not name_match:
            return None, start_index + 1
        
        name = name_match.group(1).strip()
        
        # Look backwards for tags
        tags = []
        tag_index = start_index - 1
        while tag_index >= 0:
            tag_line = lines[tag_index].strip()
            if tag_line.startswith('@'):
                tags.extend(self.tag_pattern.findall(tag_line))
                tag_index -= 1
            else:
                break
        tags.reverse()
        
        # Parse steps
        steps = []
        i = start_index + 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            if line.startswith('Scenario') or line.startswith('Feature:') or line.startswith('Examples:'):
                break
            
            step_match = self.step_pattern.match(line)
            if step_match:
                keyword = step_match.group(1)
                text = step_match.group(2)
                steps.append(f"{keyword} {text}")
            
            i += 1
        
        return {
            'name': name,
            'steps': steps,
            'tags': tags,
            'line_number': start_index + 1
        }, i
    
    def expand_outline(self, outline: ScenarioOutline) -> List[ExpandedScenario]:
        """
        Expand a Scenario Outline into individual scenarios.
        
        Args:
            outline: ScenarioOutline to expand
            
        Returns:
            List of ExpandedScenario instances
        """
        expanded_scenarios = []
        
        for table_index, examples_table in enumerate(outline.examples):
            # Combine outline tags with examples tags
            combined_tags = list(outline.tags)
            combined_tags.extend(examples_table.tags)
            
            for row_index, example_dict in enumerate(examples_table.to_dict_list()):
                # Replace parameters in steps
                expanded_steps = []
                for step in outline.steps:
                    expanded_step = step
                    for param, value in example_dict.items():
                        # Replace <param> with value
                        expanded_step = expanded_step.replace(f'<{param}>', value)
                    expanded_steps.append(expanded_step)
                
                # Generate instance name
                instance_name = self._generate_instance_name(
                    outline.name,
                    example_dict,
                    row_index
                )
                
                expanded = ExpandedScenario(
                    name=instance_name,
                    original_name=outline.name,
                    steps=expanded_steps,
                    tags=combined_tags,
                    example_data=example_dict,
                    example_index=row_index,
                    examples_table_index=table_index,
                    source_outline=outline.name,
                    description=outline.description,
                    line_number=outline.line_number
                )
                
                expanded_scenarios.append(expanded)
        
        return expanded_scenarios
    
    def _generate_instance_name(
        self,
        outline_name: str,
        example_data: Dict[str, str],
        row_index: int
    ) -> str:
        """Generate a unique name for scenario instance."""
        # Approach: Outline name + example values
        # Example: "Login with credentials [user=admin, pass=secret]"
        
        # Limit to first 3 parameters to avoid overly long names
        params_str = ', '.join([
            f"{k}={v}" for k, v in list(example_data.items())[:3]
        ])
        
        if len(example_data) > 3:
            params_str += ', ...'
        
        return f"{outline_name} [{params_str}]"
    
    def expand_all_outlines(
        self,
        feature_content: str
    ) -> Dict[str, Any]:
        """
        Parse feature file and expand all Scenario Outlines.
        
        Args:
            feature_content: Content of .feature file
            
        Returns:
            Dictionary with regular scenarios and expanded outlines
        """
        parsed = self.parse_feature_file(feature_content)
        
        regular_scenarios = []
        expanded_scenarios = []
        
        for item in parsed:
            if item['type'] == 'scenario':
                regular_scenarios.append(item['data'])
            elif item['type'] == 'outline':
                outline = item['data']
                expanded = self.expand_outline(outline)
                expanded_scenarios.extend(expanded)
        
        return {
            'regular_scenarios': regular_scenarios,
            'expanded_scenarios': [s.to_dict() for s in expanded_scenarios],
            'total_regular': len(regular_scenarios),
            'total_expanded': len(expanded_scenarios),
            'total_scenarios': len(regular_scenarios) + len(expanded_scenarios)
        }


def expand_scenario_outlines(feature_content: str) -> Dict[str, Any]:
    """
    Convenience function to expand all Scenario Outlines in a feature file.
    
    Args:
        feature_content: Content of .feature file
        
    Returns:
        Dictionary with expansion results
    
    Example:
        content = Path('login.feature').read_text()
        result = expand_scenario_outlines(content)
        
        print(f"Total scenarios: {result['total_scenarios']}")
        for scenario in result['expanded_scenarios']:
            print(f"  - {scenario['name']}")
            print(f"    Data: {scenario['example_data']}")
    """
    expander = ScenarioOutlineExpander()
    return expander.expand_all_outlines(feature_content)
