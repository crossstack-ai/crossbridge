"""
Gherkin Feature File Parser
Extracts scenarios, steps, tags, and metadata from Cucumber/BDD feature files.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GherkinStep:
    """Represents a single Gherkin step."""
    keyword: str  # Given, When, Then, And, But
    text: str
    argument: Optional[str] = None  # Doc string or data table
    line_number: int = 0


@dataclass
class GherkinScenario:
    """Represents a Gherkin scenario or scenario outline."""
    name: str
    type: str  # "Scenario" or "Scenario Outline"
    steps: List[GherkinStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, List[str]]] = field(default_factory=list)
    line_number: int = 0


@dataclass
class GherkinFeature:
    """Represents a complete Gherkin feature file."""
    name: str
    description: str
    scenarios: List[GherkinScenario] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    background_steps: List[GherkinStep] = field(default_factory=list)
    line_number: int = 0


class GherkinParser:
    """Parser for Gherkin/Cucumber feature files."""
    
    # Gherkin keywords
    FEATURE_KEYWORD = r'^\s*Feature:'
    SCENARIO_KEYWORD = r'^\s*(Scenario|Scenario Outline):'
    BACKGROUND_KEYWORD = r'^\s*Background:'
    EXAMPLES_KEYWORD = r'^\s*Examples:'
    STEP_KEYWORDS = r'^\s*(Given|When|Then|And|But)'
    TAG_PATTERN = r'@\w+'
    
    def __init__(self):
        self.current_line = 0
    
    def parse_file(self, file_path: str) -> Optional[GherkinFeature]:
        """
        Parse a Gherkin feature file.
        
        Args:
            file_path: Path to the .feature file
            
        Returns:
            GherkinFeature object or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_content(content)
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            return None
    
    def parse_content(self, content: str) -> Optional[GherkinFeature]:
        """
        Parse Gherkin content from string.
        
        Args:
            content: Feature file content as string
            
        Returns:
            GherkinFeature object or None if parsing fails
        """
        lines = content.split('\n')
        self.current_line = 0
        
        feature = None
        current_scenario = None
        current_tags = []
        in_background = False
        in_examples = False
        example_table = []
        collecting_step_argument = False
        step_argument_lines = []
        current_step = None
        
        while self.current_line < len(lines):
            line = lines[self.current_line]
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                self.current_line += 1
                continue
            
            # Collect tags
            if stripped.startswith('@'):
                tags = re.findall(self.TAG_PATTERN, stripped)
                current_tags.extend(tags)
                self.current_line += 1
                continue
            
            # Parse Feature
            if re.match(self.FEATURE_KEYWORD, line):
                feature_name = re.sub(self.FEATURE_KEYWORD, '', line).strip()
                feature = GherkinFeature(
                    name=feature_name,
                    description="",
                    tags=current_tags.copy(),
                    line_number=self.current_line + 1
                )
                current_tags = []
                
                # Collect feature description
                self.current_line += 1
                description_lines = []
                while self.current_line < len(lines):
                    desc_line = lines[self.current_line].strip()
                    if (not desc_line or 
                        re.match(self.SCENARIO_KEYWORD, lines[self.current_line]) or
                        re.match(self.BACKGROUND_KEYWORD, lines[self.current_line]) or
                        desc_line.startswith('@')):
                        break
                    if desc_line and not desc_line.startswith('#'):
                        description_lines.append(desc_line)
                    self.current_line += 1
                feature.description = ' '.join(description_lines)
                continue
            
            # Parse Background
            if re.match(self.BACKGROUND_KEYWORD, line):
                in_background = True
                self.current_line += 1
                continue
            
            # Parse Scenario/Scenario Outline
            if re.match(self.SCENARIO_KEYWORD, line):
                # Save previous scenario
                if current_scenario and feature:
                    feature.scenarios.append(current_scenario)
                
                in_background = False
                in_examples = False
                match = re.match(r'^\s*(Scenario|Scenario Outline):\s*(.+)', line)
                scenario_type = match.group(1)
                scenario_name = match.group(2).strip()
                
                current_scenario = GherkinScenario(
                    name=scenario_name,
                    type=scenario_type,
                    tags=current_tags.copy(),
                    line_number=self.current_line + 1
                )
                current_tags = []
                self.current_line += 1
                continue
            
            # Parse Examples
            if re.match(self.EXAMPLES_KEYWORD, line):
                in_examples = True
                example_table = []
                self.current_line += 1
                continue
            
            # Parse example table
            if in_examples and stripped.startswith('|'):
                row = [cell.strip() for cell in stripped.split('|')[1:-1]]
                example_table.append(row)
                self.current_line += 1
                
                # Check if next line is not a table row
                if (self.current_line >= len(lines) or 
                    not lines[self.current_line].strip().startswith('|')):
                    # Convert table to dict format
                    if example_table and current_scenario:
                        headers = example_table[0]
                        examples_dict = {header: [] for header in headers}
                        for row in example_table[1:]:
                            for i, value in enumerate(row):
                                if i < len(headers):
                                    examples_dict[headers[i]].append(value)
                        current_scenario.examples.append(examples_dict)
                    in_examples = False
                    example_table = []
                continue
            
            # Parse Steps
            if re.match(self.STEP_KEYWORDS, line):
                # Save previous step's argument if any
                if current_step and step_argument_lines:
                    current_step.argument = '\n'.join(step_argument_lines)
                    step_argument_lines = []
                
                match = re.match(r'^\s*(Given|When|Then|And|But)\s+(.+)', line)
                keyword = match.group(1)
                text = match.group(2).strip()
                
                current_step = GherkinStep(
                    keyword=keyword,
                    text=text,
                    line_number=self.current_line + 1
                )
                
                # Add step to appropriate collection
                if in_background and feature:
                    feature.background_steps.append(current_step)
                elif current_scenario:
                    current_scenario.steps.append(current_step)
                
                self.current_line += 1
                continue
            
            # Parse step arguments (doc strings or tables)
            if current_step and (stripped.startswith('"""') or stripped.startswith('|')):
                if not collecting_step_argument and stripped.startswith('"""'):
                    collecting_step_argument = True
                    self.current_line += 1
                    continue
                elif collecting_step_argument and stripped.startswith('"""'):
                    collecting_step_argument = False
                    current_step.argument = '\n'.join(step_argument_lines)
                    step_argument_lines = []
                    self.current_line += 1
                    continue
                elif collecting_step_argument:
                    step_argument_lines.append(line)
                    self.current_line += 1
                    continue
                elif stripped.startswith('|'):
                    # Data table row
                    step_argument_lines.append(line)
                    self.current_line += 1
                    continue
            
            self.current_line += 1
        
        # Save last scenario
        if current_scenario and feature:
            feature.scenarios.append(current_scenario)
        
        return feature
    
    def extract_parameters(self, step_text: str) -> Tuple[str, List[str]]:
        """
        Extract parameters from step text.
        
        Args:
            step_text: Step text with parameters
            
        Returns:
            Tuple of (template_text, parameters)
            
        Example:
            'user enters "john" and "doe"' -> ('user enters {param1} and {param2}', ['john', 'doe'])
        """
        # Extract quoted strings
        quoted_params = re.findall(r'"([^"]*)"', step_text)
        
        # Extract <parameter> style (for Scenario Outline)
        angle_params = re.findall(r'<([^>]+)>', step_text)
        
        # Replace with placeholders
        template = step_text
        params = []
        
        for i, param in enumerate(quoted_params):
            template = template.replace(f'"{param}"', f'{{param{i+1}}}', 1)
            params.append(param)
        
        for i, param in enumerate(angle_params):
            template = template.replace(f'<{param}>', f'<{param}>')
            # Keep angle brackets for scenario outline parameters
        
        return template, params
    
    def normalize_step_keyword(self, keyword: str, previous_keyword: str = None) -> str:
        """
        Normalize step keywords (And/But -> previous keyword).
        
        Args:
            keyword: Current step keyword
            previous_keyword: Previous step keyword
            
        Returns:
            Normalized keyword
        """
        if keyword in ['And', 'But']:
            return previous_keyword or 'Given'
        return keyword


def parse_feature_file(file_path: str) -> Optional[GherkinFeature]:
    """
    Convenience function to parse a feature file.
    
    Args:
        file_path: Path to .feature file
        
    Returns:
        GherkinFeature object or None
    """
    parser = GherkinParser()
    return parser.parse_file(file_path)
