"""
Phase 2: Playwright Page Object Generator

Generates Playwright-idiomatic Page Objects while preserving locator semantics.

Key principle: We change the API, NOT the locators.
"""

import logging
from typing import List
from pathlib import Path

from .models import PageObject, Locator

logger = logging.getLogger(__name__)


class PlaywrightPageObjectGenerator:
    """
    Generates modern Playwright Page Objects.
    
    CRITICAL: Preserves locator values exactly.
    We only modernize the execution layer, not the locators themselves.
    
    This is what makes Phase 2 trustworthy.
    """
    
    def __init__(self, target_language: str = "python"):
        self.target_language = target_language
    
    def generate(self, page_object: PageObject) -> str:
        """
        Generate Playwright Page Object code.
        
        Args:
            page_object: PageObject model with locators
            
        Returns:
            Generated code string
        """
        if self.target_language == "python":
            return self._generate_python(page_object)
        else:
            raise ValueError(f"Unsupported target language: {self.target_language}")
    
    def _generate_python(self, page_object: PageObject) -> str:
        """Generate Python Playwright Page Object."""
        lines = []
        
        # Header comment
        lines.append('"""')
        lines.append(f'{page_object.name} - Migrated by CrossStack Phase 2')
        lines.append('')
        lines.append('Semantic Preservation:')
        lines.append('- All locators preserved exactly as-is')
        lines.append('- Only execution layer modernized')
        lines.append('- Original semantics maintained')
        lines.append('')
        lines.append(f'Source: {page_object.file_path}')
        lines.append(f'Detected by: {", ".join(page_object.detection_reasons)}')
        lines.append('"""')
        lines.append('')
        
        # Imports
        lines.append('from playwright.sync_api import Page, Locator')
        lines.append('')
        lines.append('')
        
        # Class definition
        class_name = self._pythonize_class_name(page_object.name)
        lines.append(f'class {class_name}:')
        lines.append('    """')
        lines.append(f'    {page_object.name} Page Object')
        lines.append('')
        lines.append(f'    Contains {len(page_object.locators)} locators (preserved from Selenium)')
        lines.append('    """')
        lines.append('')
        
        # Constructor
        lines.append('    def __init__(self, page: Page):')
        lines.append('        self.page = page')
        lines.append('')
        
        # Locators as properties
        if page_object.locators:
            lines.append('        # Locators (preserved exactly from Selenium)')
            for locator in page_object.locators:
                locator_expr = self._generate_locator_expression(locator)
                comment = f'  # {locator.strategy.value}: {locator.value}'
                lines.append(f'        self.{self._pythonize_name(locator.name)} = {locator_expr}{comment}')
            lines.append('')
        
        # Methods
        if page_object.methods:
            lines.append('    # Page actions')
            for method_info in page_object.methods:
                method_code = self._generate_method(method_info, page_object)
                lines.extend(method_code)
                lines.append('')
        
        # Default navigation method if not exists
        if not any(m.get('name') == 'navigate' for m in page_object.methods):
            lines.append('    def navigate(self, url: str):')
            lines.append('        """Navigate to this page."""')
            lines.append('        self.page.goto(url)')
        
        return '\n'.join(lines)
    
    def _generate_locator_expression(self, locator: Locator) -> str:
        """
        Generate Playwright locator expression.
        
        PRESERVES the locator value exactly.
        """
        from .models import LocatorStrategy
        
        if locator.strategy == LocatorStrategy.ID:
            return f'page.locator("#{locator.value}")'
        elif locator.strategy == LocatorStrategy.CSS_SELECTOR:
            return f'page.locator("{locator.value}")'
        elif locator.strategy == LocatorStrategy.XPATH:
            return f'page.locator("{locator.value}")'
        elif locator.strategy == LocatorStrategy.NAME:
            return f'page.locator("[name=\\"{locator.value}\\"]")'
        elif locator.strategy == LocatorStrategy.CLASS_NAME:
            return f'page.locator(".{locator.value}")'
        elif locator.strategy == LocatorStrategy.DATA_TESTID:
            return f'page.get_by_test_id("{locator.value}")'
        else:
            # Fallback
            return f'page.locator("{locator.value}")'
    
    def _generate_method(self, method_info: dict, page_object: PageObject) -> List[str]:
        """Generate a method stub."""
        method_name = self._pythonize_name(method_info['name'])
        
        lines = []
        lines.append(f'    def {method_name}(self):')
        lines.append(f'        """')
        lines.append(f'        {method_info["name"]} action')
        lines.append(f'        ')
        lines.append(f'        Migrated from: {page_object.name}.{method_info["name"]}')
        lines.append(f'        """')
        lines.append('        # TODO: Implement action logic')
        lines.append('        pass')
        
        return lines
    
    def _pythonize_class_name(self, name: str) -> str:
        """Convert Java class name to Python convention."""
        # Already in PascalCase, just ensure it
        return name
    
    def _pythonize_name(self, name: str) -> str:
        """Convert Java camelCase to Python snake_case."""
        import re
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()


class RobotFrameworkPageObjectGenerator:
    """
    Generates Robot Framework resource files from Page Objects.
    
    Same principle: Preserve locators, modernize execution.
    """
    
    def generate(self, page_object: PageObject) -> str:
        """Generate Robot Framework resource file."""
        lines = []
        
        # Header
        lines.append('*** Settings ***')
        lines.append(f'Documentation    {page_object.name} - Migrated by CrossStack Phase 2')
        lines.append('...              All locators preserved exactly as-is')
        lines.append('...              Only execution layer modernized')
        lines.append(f'...              Source: {page_object.file_path}')
        lines.append('')
        lines.append('Library          Browser')
        lines.append('')
        lines.append('')
        
        # Variables section with locators
        if page_object.locators:
            lines.append('*** Variables ***')
            lines.append('# Locators preserved from Selenium')
            for locator in page_object.locators:
                var_name = f'${{{locator.name.upper()}}}'
                locator_value = self._generate_robot_locator(locator)
                comment = f'    # {locator.strategy.value}'
                lines.append(f'{var_name:<30} {locator_value}{comment}')
            lines.append('')
            lines.append('')
        
        # Keywords section
        lines.append('*** Keywords ***')
        
        if page_object.methods:
            for method_info in page_object.methods:
                lines.extend(self._generate_robot_keyword(method_info, page_object))
                lines.append('')
        
        # Default navigation keyword
        lines.append(f'Navigate To {page_object.name}')
        lines.append('    [Arguments]    ${url}')
        lines.append(f'    [Documentation]    Navigate to {page_object.name}')
        lines.append('    Go To    ${url}')
        
        return '\n'.join(lines)
    
    def _generate_robot_locator(self, locator: Locator) -> str:
        """Convert to Robot Framework locator format."""
        return locator.to_robot_locator()
    
    def _generate_robot_keyword(self, method_info: dict, page_object: PageObject) -> List[str]:
        """Generate Robot Framework keyword."""
        # Convert camelCase to Title Case
        method_name = method_info['name']
        keyword_name = ''.join(' ' + c if c.isupper() else c for c in method_name).strip().title()
        
        lines = []
        lines.append(keyword_name)
        lines.append(f'    [Documentation]    {method_info["name"]} from {page_object.name}')
        lines.append('    # TODO: Implement keyword logic')
        lines.append('    Log    Action: ${keyword_name}')
        
        return lines
