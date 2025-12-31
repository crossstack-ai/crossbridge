"""
Playwright Python Generator.

Generates Playwright Python test code from TestIntent.
"""

from typing import List

from core.translation.intent_model import (
    ActionIntent,
    ActionType,
    AssertionIntent,
    AssertionType,
    TestIntent,
)
from core.translation.pipeline import TargetGenerator


class PlaywrightGenerator(TargetGenerator):
    """Generator for Playwright Python tests."""
    
    def __init__(self, framework: str = "playwright-python", config = None):
        """Initialize Playwright generator."""
        # Make config optional for backward compatibility
        if config is None:
            from core.translation.pipeline import TranslationConfig
            config = TranslationConfig(
                source_framework="selenium-java",
                target_framework=framework,
            )
        super().__init__(framework, config)
        
        # Selector conversion
        self.selector_conversions = {
            "id": "#{0}",
            "class": ".{0}",
            "css": "{0}",
            "xpath": "{0}",
            "text": "text='{0}'",
            "name": "[name='{0}']",
        }
    
    def can_generate(self, intent: TestIntent) -> bool:
        """Check if we can generate Playwright code."""
        return intent.test_type in [
            intent.test_type.UI,
            intent.test_type.BDD,
        ]
    
    def generate(self, intent: TestIntent) -> str:
        """
        Generate Playwright Python test from TestIntent.
        
        Produces:
        - pytest-style test function
        - Playwright page fixture
        - Idiomatic locators (prefer role-based)
        - Auto-waiting (no explicit waits)
        - Clean assertions
        """
        lines = []
        
        # Add header comment
        lines.append(f'"""')
        lines.append(f'{intent.name}')
        lines.append(f'')
        lines.append(f'Translated from: {intent.source_framework}')
        if intent.source_file:
            lines.append(f'Source file: {intent.source_file}')
        lines.append(f'Confidence: {intent.confidence:.2f}')
        lines.append(f'"""')
        lines.append('')
        
        # Add imports
        lines.extend(self._generate_imports(intent))
        lines.append('')
        
        # Add test function
        lines.extend(self._generate_test_function(intent))
        
        return '\n'.join(lines)
    
    def _generate_imports(self, intent: TestIntent) -> List[str]:
        """Generate import statements."""
        imports = [
            'from playwright.sync_api import Page, expect',
        ]
        
        # Add pytest if needed
        if intent.has_data_driven():
            imports.append('import pytest')
        
        return imports
    
    def _generate_test_function(self, intent: TestIntent) -> List[str]:
        """Generate the main test function."""
        lines = []
        
        # Function signature
        function_name = self._convert_test_name(intent.name)
        lines.append(f'def {function_name}(page: Page):')
        
        # Add docstring if we have description
        if intent.description:
            lines.append(f'    """')
            lines.append(f'    {intent.description}')
            lines.append(f'    """')
        
        # Add TODOs if present
        if intent.todos:
            for todo in intent.todos:
                lines.append(f'    # TODO: {todo}')
            lines.append('')
        
        # Setup steps
        if intent.setup_steps:
            lines.append('    # Setup')
            for action in intent.setup_steps:
                action_lines = self._generate_action(action)
                lines.extend([f'    {line}' for line in action_lines])
            lines.append('')
        
        # Main test steps
        for action in intent.steps:
            action_lines = self._generate_action(action)
            lines.extend([f'    {line}' for line in action_lines])
        
        # Assertions
        if intent.assertions:
            lines.append('')
            lines.append('    # Assertions')
            for assertion in intent.assertions:
                assertion_lines = self._generate_assertion(assertion)
                lines.extend([f'    {line}' for line in assertion_lines])
        
        # Teardown (usually not needed in Playwright)
        if intent.teardown_steps:
            lines.append('')
            lines.append('    # Teardown (handled by Playwright)')
            for action in intent.teardown_steps:
                # Skip driver.quit() - Playwright handles it
                if action.target != "teardown_driver":
                    action_lines = self._generate_action(action)
                    lines.extend([f'    {line}' for line in action_lines])
        
        return lines
    
    def _generate_action(self, action: ActionIntent) -> List[str]:
        """Generate code for an action."""
        lines = []
        
        # Add source line reference if available
        if action.line_number:
            lines.append(f'# Source line: {action.line_number}')
        
        # Add low confidence warning
        if action.confidence < 0.8:
            lines.append(f'# ⚠️ Confidence: {action.confidence:.2f} - Review needed')
        
        # Generate action based on type
        if action.action_type == ActionType.NAVIGATE:
            lines.append(f'page.goto("{action.value}")')
        
        elif action.action_type == ActionType.CLICK:
            locator = self._generate_locator(action)
            lines.append(f'{locator}.click()')
        
        elif action.action_type == ActionType.FILL:
            locator = self._generate_locator(action)
            lines.append(f'{locator}.fill("{action.value}")')
        
        elif action.action_type == ActionType.SELECT:
            locator = self._generate_locator(action)
            lines.append(f'{locator}.select_option("{action.value}")')
        
        elif action.action_type == ActionType.WAIT:
            # Skip explicit waits - Playwright auto-waits
            if action.wait_strategy == "explicit":
                lines.append('# Explicit wait removed - Playwright auto-waits')
            elif action.target == "sleep":
                lines.append('# Sleep removed - Playwright auto-waits')
                lines.append('# TODO: If this sleep was intentional, use page.wait_for_timeout()')
        
        elif action.action_type == ActionType.CUSTOM:
            # Custom actions need manual review
            lines.append(f'# TODO: Implement custom action: {action.description}')
            if action.target == "setup_driver":
                lines.append('# Browser setup handled by Playwright fixture')
        
        else:
            lines.append(f'# TODO: Implement {action.action_type.value}: {action.description}')
        
        return lines
    
    def _generate_assertion(self, assertion: AssertionIntent) -> List[str]:
        """Generate code for an assertion."""
        lines = []
        
        # Add source line reference
        if assertion.line_number:
            lines.append(f'# Source line: {assertion.line_number}')
        
        # Add low confidence warning
        if assertion.confidence < 0.8:
            lines.append(f'# ⚠️ Confidence: {assertion.confidence:.2f} - Review needed')
        
        # Generate assertion based on type
        if assertion.assertion_type == AssertionType.VISIBLE:
            locator = self._generate_locator(assertion)
            lines.append(f'expect({locator}).to_be_visible()')
        
        elif assertion.assertion_type == AssertionType.TEXT_CONTENT:
            locator = self._generate_locator(assertion)
            lines.append(f'expect({locator}).to_have_text("{assertion.expected}")')
        
        elif assertion.assertion_type == AssertionType.EQUALS:
            locator = self._generate_locator(assertion)
            lines.append(f'expect({locator}).to_have_value("{assertion.expected}")')
        
        elif assertion.assertion_type == AssertionType.CONTAINS:
            locator = self._generate_locator(assertion)
            lines.append(f'expect({locator}).to_contain_text("{assertion.expected}")')
        
        elif assertion.assertion_type == AssertionType.URL:
            lines.append(f'expect(page).to_have_url("{assertion.expected}")')
        
        elif assertion.assertion_type == AssertionType.TITLE:
            lines.append(f'expect(page).to_have_title("{assertion.expected}")')
        
        elif assertion.assertion_type == AssertionType.CUSTOM:
            lines.append(f'# TODO: Implement custom assertion: {assertion.description}')
        
        else:
            lines.append(f'# TODO: Implement {assertion.assertion_type.value} assertion')
        
        return lines
    
    def _generate_locator(self, intent) -> str:
        """
        Generate Playwright locator from selector.
        
        Prefers role-based locators when possible.
        """
        selector = intent.selector
        
        if not selector:
            return f'page.locator("[data-testid=\'{intent.target}\']")'
        
        # Role-based selectors (preferred)
        if 'button' in intent.target.lower():
            return f'page.get_by_role("button", name="{intent.target}")'
        elif 'link' in intent.target.lower():
            return f'page.get_by_role("link", name="{intent.target}")'
        elif 'input' in intent.target.lower() or 'field' in intent.target.lower():
            return f'page.get_by_label("{intent.target}")'
        
        # Text-based
        if selector.startswith('text='):
            text = selector[5:].strip("'\"")
            return f'page.get_by_text("{text}")'
        
        # ID selector
        if selector.startswith('#'):
            return f'page.locator("{selector}")'
        
        # CSS selector
        if selector.startswith('.') or selector.startswith('['):
            return f'page.locator("{selector}")'
        
        # XPath
        if selector.startswith('//') or selector.startswith('(//'):
            return f'page.locator("xpath={selector}")'
        
        # Default: use as CSS selector
        return f'page.locator("{selector}")'
    
    def _convert_test_name(self, name: str) -> str:
        """Convert Java test name to Python snake_case."""
        # Convert camelCase to snake_case
        import re
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        name = name.lower()
        
        # Ensure it starts with 'test_'
        if not name.startswith('test_'):
            name = f'test_{name}'
        
        return name
