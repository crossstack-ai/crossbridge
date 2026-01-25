"""
Scenario Outline extraction and transformation for Behave.

Handles complex scenario outlines with multiple examples tables.
"""

import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ExamplesTable:
    """Represents an Examples table in a Scenario Outline."""
    name: Optional[str]
    headers: List[str]
    rows: List[List[str]]
    tags: List[str]
    line_start: int


@dataclass
class ScenarioOutline:
    """Represents a Scenario Outline with Examples."""
    name: str
    steps: List[Dict[str, str]]
    examples: List[ExamplesTable]
    tags: List[str]
    description: Optional[str]
    line_start: int


class BehaveScenarioOutlineExtractor:
    """Extract and parse Scenario Outlines from Behave feature files."""
    
    def __init__(self):
        self.outline_pattern = re.compile(
            r'^\s*Scenario Outline:\s*(.+)$',
            re.MULTILINE | re.IGNORECASE
        )
        self.examples_pattern = re.compile(
            r'^\s*Examples:\s*(.*)$',
            re.MULTILINE | re.IGNORECASE
        )
        self.step_pattern = re.compile(
            r'^\s*(Given|When|Then|And|But)\s+(.+)$',
            re.MULTILINE | re.IGNORECASE
        )
        self.table_row_pattern = re.compile(
            r'^\s*\|(.+)\|$',
            re.MULTILINE
        )
        self.tag_pattern = re.compile(
            r'^\s*@([\w-]+)',
            re.MULTILINE
        )
        self.placeholder_pattern = re.compile(r'<(\w+)>')
    
    def extract_scenario_outlines(
        self,
        feature_file: Path
    ) -> List[ScenarioOutline]:
        """
        Extract all scenario outlines from a feature file.
        
        Args:
            feature_file: Path to .feature file
            
        Returns:
            List of ScenarioOutline objects
        """
        if not feature_file.exists():
            return []
        
        content = feature_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        outlines = []
        
        for match in self.outline_pattern.finditer(content):
            outline_name = match.group(1).strip()
            outline_start = match.start()
            outline_line = content[:outline_start].count('\n') + 1
            
            # Extract tags before scenario
            tags = self._extract_tags_before(content, outline_start)
            
            # Extract steps
            steps = self._extract_steps(content, outline_start)
            
            # Extract examples tables
            examples = self._extract_examples(content, outline_start)
            
            # Extract description (lines between Scenario Outline and first step/examples)
            description = self._extract_description(
                content,
                outline_start,
                steps[0]['line'] if steps else None
            )
            
            outlines.append(ScenarioOutline(
                name=outline_name,
                steps=steps,
                examples=examples,
                tags=tags,
                description=description,
                line_start=outline_line
            ))
        
        return outlines
    
    def _extract_tags_before(self, content: str, position: int) -> List[str]:
        """Extract tags appearing before a scenario outline."""
        # Look backwards for tags
        before_content = content[:position]
        lines_before = before_content.split('\n')
        
        tags = []
        for line in reversed(lines_before):
            line = line.strip()
            if line.startswith('@'):
                # Extract all tags from line
                line_tags = self.tag_pattern.findall(line)
                tags.extend(line_tags)
            elif line and not line.startswith('#'):
                # Stop at non-tag, non-comment line
                break
        
        return list(reversed(tags))
    
    def _extract_steps(
        self,
        content: str,
        outline_start: int
    ) -> List[Dict[str, str]]:
        """Extract steps from scenario outline."""
        # Find the section between outline declaration and Examples
        examples_match = self.examples_pattern.search(content[outline_start:])
        
        if examples_match:
            section_end = outline_start + examples_match.start()
        else:
            # No examples, look for next scenario or end of content
            next_scenario = re.search(
                r'^\s*(Scenario|Scenario Outline):',
                content[outline_start + 50:],
                re.MULTILINE | re.IGNORECASE
            )
            if next_scenario:
                section_end = outline_start + 50 + next_scenario.start()
            else:
                section_end = len(content)
        
        section = content[outline_start:section_end]
        
        steps = []
        for match in self.step_pattern.finditer(section):
            keyword = match.group(1)
            text = match.group(2).strip()
            
            # Extract placeholders
            placeholders = self.placeholder_pattern.findall(text)
            
            steps.append({
                'keyword': keyword,
                'text': text,
                'placeholders': placeholders,
                'line': content[:outline_start + match.start()].count('\n') + 1
            })
        
        return steps
    
    def _extract_examples(
        self,
        content: str,
        outline_start: int
    ) -> List[ExamplesTable]:
        """Extract Examples tables from scenario outline."""
        examples_tables = []
        
        # Find all Examples sections
        section = content[outline_start:]
        
        for match in self.examples_pattern.finditer(section):
            examples_name = match.group(1).strip() or None
            examples_start = outline_start + match.start()
            examples_line = content[:examples_start].count('\n') + 1
            
            # Extract tags before Examples
            tags = self._extract_tags_before(content, examples_start)
            
            # Extract table data
            table_start = match.end()
            table_section = section[table_start:]
            
            # Find end of table (next Examples, Scenario, or end)
            table_end_match = re.search(
                r'^\s*(Examples|Scenario|Scenario Outline|$)',
                table_section,
                re.MULTILINE | re.IGNORECASE
            )
            
            if table_end_match:
                table_section = table_section[:table_end_match.start()]
            
            # Parse table rows
            table_rows = []
            for row_match in self.table_row_pattern.finditer(table_section):
                row_data = row_match.group(1)
                cells = [cell.strip() for cell in row_data.split('|')]
                table_rows.append(cells)
            
            if table_rows:
                headers = table_rows[0]
                data_rows = table_rows[1:]
                
                examples_tables.append(ExamplesTable(
                    name=examples_name,
                    headers=headers,
                    rows=data_rows,
                    tags=tags,
                    line_start=examples_line
                ))
        
        return examples_tables
    
    def _extract_description(
        self,
        content: str,
        outline_start: int,
        first_step_line: Optional[int]
    ) -> Optional[str]:
        """Extract description text between outline and first step."""
        # Find content between Scenario Outline line and first step
        outline_end = content.find('\n', outline_start) + 1
        
        if first_step_line:
            # Convert line number to position
            lines_before_step = content.split('\n')[:first_step_line - 1]
            step_position = sum(len(line) + 1 for line in lines_before_step)
            
            description_section = content[outline_end:step_position].strip()
        else:
            # No steps, use examples start
            examples_match = self.examples_pattern.search(content[outline_start:])
            if examples_match:
                description_section = content[
                    outline_end:outline_start + examples_match.start()
                ].strip()
            else:
                return None
        
        # Remove leading/trailing whitespace and empty lines
        lines = [line.strip() for line in description_section.split('\n')]
        lines = [line for line in lines if line and not line.startswith('@')]
        
        return '\n'.join(lines) if lines else None
    
    def get_total_test_cases(self, outline: ScenarioOutline) -> int:
        """Calculate total test cases generated from scenario outline."""
        total = 0
        for examples_table in outline.examples:
            total += len(examples_table.rows)
        return total
    
    def expand_outline(self, outline: ScenarioOutline) -> List[Dict]:
        """
        Expand scenario outline into individual test cases.
        
        Args:
            outline: ScenarioOutline object
            
        Returns:
            List of expanded test case dictionaries
        """
        test_cases = []
        
        for examples_table in outline.examples:
            for row_idx, row_data in enumerate(examples_table.rows):
                # Create parameter mapping
                params = dict(zip(examples_table.headers, row_data))
                
                # Expand steps with parameters
                expanded_steps = []
                for step in outline.steps:
                    expanded_text = step['text']
                    for placeholder, value in params.items():
                        expanded_text = expanded_text.replace(
                            f'<{placeholder}>',
                            value
                        )
                    
                    expanded_steps.append({
                        'keyword': step['keyword'],
                        'text': expanded_text
                    })
                
                test_cases.append({
                    'name': f"{outline.name} (row {row_idx + 1})",
                    'steps': expanded_steps,
                    'parameters': params,
                    'tags': outline.tags + examples_table.tags,
                    'examples_table': examples_table.name
                })
        
        return test_cases
