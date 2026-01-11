"""
Robot Framework Code Generator
Converts Gherkin scenarios to Robot Framework test cases.
"""

import re
from typing import List, Dict, Optional, Set
from pathlib import Path
from .gherkin_parser import GherkinFeature, GherkinScenario, GherkinStep


class RobotFrameworkGenerator:
    """Generates Robot Framework code from Gherkin features."""
    
    def __init__(self):
        self.keyword_mappings = {}
        self.locators = {}
        self.resources = set()
    
    def generate_test_file(
        self,
        feature: GherkinFeature,
        source_path: str,
        include_browser_library: bool = True
    ) -> str:
        """
        Generate Robot Framework test file from Gherkin feature.
        
        Args:
            feature: Parsed GherkinFeature object
            source_path: Original feature file path for documentation
            include_browser_library: Whether to include Browser library
            
        Returns:
            Robot Framework test file content
        """
        lines = []
        
        # Settings Section
        lines.append("*** Settings ***")
        lines.append(f"Documentation    {feature.name}")
        if feature.description:
            lines.append(f"...              {feature.description}")
        lines.append(f"...              Migrated from: {source_path}")
        
        if include_browser_library:
            lines.append("Library          Browser")
        
        # Add resource imports (will be populated by step mapper)
        for resource in sorted(self.resources):
            lines.append(f"Resource         {resource}")
        
        # Add feature tags as test tags
        if feature.tags:
            tags_str = "    ".join(tag.replace('@', '') for tag in feature.tags)
            lines.append(f"Test Tags        {tags_str}")
        
        lines.append("")
        
        # Variables Section (if any locators defined)
        if self.locators:
            lines.append("*** Variables ***")
            for var_name, value in sorted(self.locators.items()):
                lines.append(f"${{{var_name}}}    {value}")
            lines.append("")
        
        # Test Cases Section
        lines.append("*** Test Cases ***")
        
        for scenario in feature.scenarios:
            lines.extend(self._generate_test_case(scenario, feature.background_steps))
        
        # Keywords Section (for local keywords)
        if self.keyword_mappings:
            lines.append("")
            lines.append("*** Keywords ***")
            for keyword_name, keyword_impl in sorted(self.keyword_mappings.items()):
                lines.append(f"{keyword_name}")
                for impl_line in keyword_impl:
                    lines.append(f"    {impl_line}")
                lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_test_case(
        self,
        scenario: GherkinScenario,
        background_steps: List[GherkinStep]
    ) -> List[str]:
        """
        Generate Robot Framework test case from Gherkin scenario.
        
        Args:
            scenario: GherkinScenario object
            background_steps: Background steps to include
            
        Returns:
            List of Robot Framework lines
        """
        lines = []
        
        # Test case name
        test_name = self._sanitize_name(scenario.name)
        lines.append(f"{test_name}")
        
        # Test documentation
        lines.append(f"    [Documentation]    {scenario.name}")
        
        # Test tags
        if scenario.tags:
            tags_str = "    ".join(tag.replace('@', '') for tag in scenario.tags)
            lines.append(f"    [Tags]    {tags_str}")
        
        # Handle Scenario Outline with examples
        if scenario.type == "Scenario Outline" and scenario.examples:
            lines.extend(self._generate_template_test(scenario, background_steps))
        else:
            # Regular scenario
            # Add background steps
            for step in background_steps:
                lines.append(f"    {self._convert_step_to_keyword(step)}")
            
            # Add scenario steps
            previous_keyword = None
            for step in scenario.steps:
                robot_line = self._convert_step_to_keyword(step, previous_keyword)
                lines.append(f"    {robot_line}")
                previous_keyword = step.keyword
        
        lines.append("")
        return lines
    
    def _generate_template_test(
        self,
        scenario: GherkinScenario,
        background_steps: List[GherkinStep]
    ) -> List[str]:
        """
        Generate test template for Scenario Outline.
        
        Args:
            scenario: Scenario Outline
            background_steps: Background steps
            
        Returns:
            List of Robot Framework lines
        """
        lines = []
        
        # Template definition
        if scenario.examples:
            example_data = scenario.examples[0]
            headers = list(example_data.keys())
            template_line = f"    [Template]    {self._sanitize_name(scenario.name)}_Template"
            lines.append(template_line)
            
            # Add example rows
            for i in range(len(example_data[headers[0]])):
                row_values = [example_data[header][i] for header in headers]
                row_line = "    " + "    ".join(row_values)
                lines.append(row_line)
        
        return lines
    
    def _convert_step_to_keyword(
        self,
        step: GherkinStep,
        previous_keyword: str = None
    ) -> str:
        """
        Convert Gherkin step to Robot Framework keyword call.
        
        Args:
            step: GherkinStep object
            previous_keyword: Previous step keyword (for And/But)
            
        Returns:
            Robot Framework keyword call
        """
        # Normalize keyword
        keyword = step.keyword
        if keyword in ['And', 'But']:
            keyword = previous_keyword or 'Given'
        
        # Convert step text to keyword name
        keyword_name = self._step_text_to_keyword(step.text)
        
        return keyword_name
    
    def _step_text_to_keyword(self, step_text: str) -> str:
        """
        Convert Gherkin step text to Robot Framework keyword.
        
        Args:
            step_text: Gherkin step text
            
        Returns:
            Robot Framework keyword call
        """
        # Extract quoted parameters
        params = re.findall(r'"([^"]*)"', step_text)
        
        # Extract <parameter> style (Scenario Outline)
        angle_params = re.findall(r'<([^>]+)>', step_text)
        
        # Remove quoted strings and create base keyword
        keyword_base = step_text
        for param in params:
            keyword_base = keyword_base.replace(f'"{param}"', '${PARAM}', 1)
        for param in angle_params:
            keyword_base = keyword_base.replace(f'<{param}>', f'${{{param}}}', 1)
        
        # Convert to title case and handle parameters
        if '${PARAM}' in keyword_base:
            # Has parameters - create keyword with arguments
            parts = keyword_base.split('${PARAM}')
            keyword_name = parts[0].strip()
            keyword_name = ' '.join(word.capitalize() for word in keyword_name.split())
            
            # Add parameters
            result = keyword_name
            for param in params:
                result += f"    {param}"
            
            return result
        else:
            # No parameters - simple keyword
            keyword_name = ' '.join(word.capitalize() for word in step_text.split())
            return keyword_name
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize name for Robot Framework.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name
        """
        # Remove special characters but keep spaces
        sanitized = re.sub(r'[^\w\s-]', '', name)
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        return sanitized
    
    def add_keyword_mapping(self, step_pattern: str, keyword_impl: List[str]):
        """
        Add a custom keyword implementation.
        
        Args:
            step_pattern: Step pattern (e.g., "user enters {param}")
            keyword_impl: List of Robot Framework lines for implementation
        """
        keyword_name = self._sanitize_name(step_pattern)
        self.keyword_mappings[keyword_name] = keyword_impl
    
    def add_locator(self, name: str, selector: str):
        """
        Add a locator variable.
        
        Args:
            name: Variable name (without ${})
            selector: CSS/XPath selector
        """
        self.locators[name] = selector
    
    def add_resource(self, resource_path: str):
        """
        Add a resource file import.
        
        Args:
            resource_path: Path to resource file
        """
        self.resources.add(resource_path)
    
    def generate_resource_file(
        self,
        page_name: str,
        keywords: Dict[str, List[str]],
        locators: Dict[str, str],
        library_imports: List[str] = None
    ) -> str:
        """
        Generate a Robot Framework resource file (page object).
        
        Args:
            page_name: Name of the page
            keywords: Dictionary of keyword name -> implementation lines
            locators: Dictionary of locator name -> selector
            library_imports: Optional list of library imports
            
        Returns:
            Resource file content
        """
        lines = []
        
        # Settings Section
        lines.append("*** Settings ***")
        lines.append(f"Documentation    {page_name} Page Object")
        
        if library_imports is None:
            library_imports = ["Browser"]
        
        for library in library_imports:
            lines.append(f"Library          {library}")
        
        lines.append("")
        
        # Variables Section
        if locators:
            lines.append("*** Variables ***")
            for var_name, selector in sorted(locators.items()):
                lines.append(f"${{{var_name}}}    {selector}")
            lines.append("")
        
        # Keywords Section
        if keywords:
            lines.append("*** Keywords ***")
            for keyword_name, impl_lines in sorted(keywords.items()):
                lines.append(f"{keyword_name}")
                for impl_line in impl_lines:
                    lines.append(f"    {impl_line}")
                lines.append("")
        
        return '\n'.join(lines)
    
    def generate_placeholder_keywords(self, steps: List[GherkinStep]) -> Dict[str, List[str]]:
        """
        Generate placeholder keyword implementations for steps.
        
        Args:
            steps: List of Gherkin steps
            
        Returns:
            Dictionary of keyword implementations
        """
        keywords = {}
        
        for step in steps:
            keyword_name = self._step_text_to_keyword(step.text)
            base_name = keyword_name.split('    ')[0]  # Remove parameters
            
            if base_name not in keywords:
                # Create placeholder implementation
                keywords[base_name] = [
                    "[Arguments]    # Add arguments as needed",
                    "[Documentation]    TODO: Implement step logic",
                    f"Log    Executing: {step.keyword} {step.text}"
                ]
        
        return keywords


def generate_robot_test_from_feature(
    feature_path: str,
    output_path: str,
    feature: GherkinFeature
) -> bool:
    """
    Convenience function to generate Robot test file from feature.
    
    Args:
        feature_path: Original feature file path
        output_path: Output Robot file path
        feature: Parsed GherkinFeature
        
    Returns:
        True if successful
    """
    try:
        generator = RobotFrameworkGenerator()
        content = generator.generate_test_file(feature, feature_path)
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error generating Robot file: {e}")
        return False
