"""
Python Selenium BDD Parser.

Extracts TestIntent from Python Selenium tests with BDD structure (Behave or pytest-bdd style).
"""

import re
from typing import List, Optional

from core.translation.intent_model import (
    ActionIntent,
    ActionType,
    AssertionIntent,
    AssertionType,
    IntentType,
    TestIntent,
)
from core.translation.pipeline import SourceParser


class PythonSeleniumBDDParser(SourceParser):
    """Parser for Python Selenium BDD tests (Behave/pytest-bdd)."""
    
    def __init__(self):
        """Initialize Python Selenium BDD parser."""
        super().__init__("python-selenium-bdd")
        
        # Selenium locator patterns
        self.locator_patterns = {
            r'find_element\(By\.ID,\s*["\']([^"\']+)["\']\)': ("id", "#{0}"),
            r'find_element\(By\.NAME,\s*["\']([^"\']+)["\']\)': ("name", "[name='{0}']"),
            r'find_element\(By\.CLASS_NAME,\s*["\']([^"\']+)["\']\)': ("class", ".{0}"),
            r'find_element\(By\.CSS_SELECTOR,\s*["\']([^"\']+)["\']\)': ("css", "{0}"),
            r'find_element\(By\.XPATH,\s*["\']([^"\']+)["\']\)': ("xpath", "{0}"),
            r'find_element\(By\.LINK_TEXT,\s*["\']([^"\']+)["\']\)': ("linkText", "text='{0}'"),
            r'find_element_by_id\(["\']([^"\']+)["\']\)': ("id", "#{0}"),
            r'find_element_by_name\(["\']([^"\']+)["\']\)': ("name", "[name='{0}']"),
            r'find_element_by_class_name\(["\']([^"\']+)["\']\)': ("class", ".{0}"),
            r'find_element_by_css_selector\(["\']([^"\']+)["\']\)': ("css", "{0}"),
            r'find_element_by_xpath\(["\']([^"\']+)["\']\)': ("xpath", "{0}"),
        }
    
    def can_parse(self, source_code: str) -> bool:
        """Check if this is Python Selenium BDD code."""
        indicators = [
            "@given" in source_code.lower() or "@when" in source_code.lower() or "@then" in source_code.lower(),
            "from behave import" in source_code or "from pytest_bdd import" in source_code,
            "from selenium" in source_code,
            "driver.find_element" in source_code or "find_element_by_" in source_code,
        ]
        # Need at least 2 indicators
        return sum(indicators) >= 2
    
    def parse(self, source_code: str, source_file: str = "") -> TestIntent:
        """Parse Python Selenium BDD code into TestIntent."""
        # Extract scenario name
        scenario_name = self._extract_scenario_name(source_code)
        
        # Create intent
        intent = TestIntent(
            name=scenario_name,
            test_type=IntentType.BDD,
            source_framework=self.framework,
            source_file=source_file,
        )
        
        # Parse BDD steps
        bdd_structure = self._parse_bdd_steps(source_code)
        intent.scenario = scenario_name
        
        # Parse actions and assertions from step functions
        actions, assertions = self._parse_selenium_code(source_code)
        
        # Categorize actions into BDD phases
        self._categorize_bdd_actions(intent, actions, assertions, bdd_structure)
        
        return intent
    
    def _extract_scenario_name(self, source_code: str) -> str:
        """Extract scenario name from decorators or docstrings."""
        # Try to find @scenario decorator (pytest-bdd)
        scenario_match = re.search(r'@scenario\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)', source_code)
        if scenario_match:
            return self._sanitize_name(scenario_match.group(2))
        
        # Try to find # Scenario: comment (Behave)
        scenario_comment = re.search(r'#\s*Scenario:\s*(.+)', source_code)
        if scenario_comment:
            return self._sanitize_name(scenario_comment.group(1))
        
        # Try to find Feature: comment
        feature_match = re.search(r'#\s*Feature:\s*(.+)', source_code)
        if feature_match:
            return self._sanitize_name(feature_match.group(1))
        
        # Try to find class name
        class_match = re.search(r'class\s+(\w+)', source_code)
        if class_match:
            return self._sanitize_name(class_match.group(1))
        
        return "python_bdd_test"
    
    def _parse_bdd_steps(self, source_code: str) -> dict:
        """Parse BDD step definitions."""
        bdd_structure = {
            "given": [],
            "when": [],
            "then": [],
        }
        
        # Parse @given, @when, @then decorators
        for match in re.finditer(r'@(given|when|then)\(["\']([^"\']+)["\']\)', source_code, re.IGNORECASE):
            step_type = match.group(1).lower()
            step_text = match.group(2)
            bdd_structure[step_type].append(step_text)
        
        return bdd_structure
    
    def _parse_selenium_code(self, source_code: str) -> tuple:
        """Parse Selenium actions and assertions."""
        actions_with_pos = []  # Store (position, ActionIntent) tuples
        assertions = []
        
        # Parse navigation
        for match in re.finditer(r'driver\.get\(["\']([^"\']+)["\']\)', source_code):
            url = match.group(1)
            actions_with_pos.append((match.start(), ActionIntent(
                action_type=ActionType.NAVIGATE,
                target=url,
                description=f"Navigate to {url}",
            )))
        
        # Parse click actions - use raw strings for regex
        # Handle XPath with nested quotes specially
        xpath_click_patterns = [
            (r'find_element\(By\.XPATH,\s*(["\'])(.+?)\1\)\.click\(\)', 'xpath'),
            (r'find_element_by_xpath\((["\'])(.+?)\1\)\.click\(\)', 'xpath'),
        ]
        
        for pattern, locator_type in xpath_click_patterns:
            for match in re.finditer(pattern, source_code):
                value = match.group(2)  # XPath is in group 2
                selector = f'xpath={value}'
                actions_with_pos.append((match.start(), ActionIntent(
                    action_type=ActionType.CLICK,
                    target=selector,
                    description=f"Click {selector}",
                )))
        
        # Other click patterns
        click_patterns = [
            (r'find_element\(By\.ID,\s*["\']([^"\']+)["\']\)\.click\(\)', 'id'),
            (r'find_element\(By\.NAME,\s*["\']([^"\']+)["\']\)\.click\(\)', 'name'),
            (r'find_element\(By\.CLASS_NAME,\s*["\']([^"\']+)["\']\)\.click\(\)', 'class'),
            (r'find_element\(By\.CSS_SELECTOR,\s*["\']([^"\']+)["\']\)\.click\(\)', 'css'),
            (r'find_element_by_id\(["\']([^"\']+)["\']\)\.click\(\)', 'id'),
            (r'find_element_by_class_name\(["\']([^"\']+)["\']\)\.click\(\)', 'class'),
        ]
        
        for pattern, locator_type in click_patterns:
            for match in re.finditer(pattern, source_code):
                value = match.group(1)
                # Determine selector based on locator type
                if locator_type == 'id':
                    selector = f'#{value}'
                elif locator_type == 'name':
                    selector = f"[name='{value}']"
                elif locator_type == 'class':
                    selector = f'.{value}'
                elif locator_type == 'css':
                    selector = value
                elif locator_type == 'xpath':
                    selector = f'xpath={value}'
                else:
                    selector = value
                
                actions_with_pos.append((match.start(), ActionIntent(
                    action_type=ActionType.CLICK,
                    target=selector,
                    description=f"Click {selector}",
                )))
        
        # Parse send_keys (fill) actions
        send_keys_patterns = [
            (r'find_element\(By\.ID,\s*["\']([^"\']+)["\']\)\.send_keys\(["\']([^"\']+)["\']\)', 'id'),
            (r'find_element\(By\.NAME,\s*["\']([^"\']+)["\']\)\.send_keys\(["\']([^"\']+)["\']\)', 'name'),
            (r'find_element\(By\.CLASS_NAME,\s*["\']([^"\']+)["\']\)\.send_keys\(["\']([^"\']+)["\']\)', 'class'),
            (r'find_element_by_id\(["\']([^"\']+)["\']\)\.send_keys\(["\']([^"\']+)["\']\)', 'id'),
        ]
        
        for pattern, locator_type in send_keys_patterns:
            for match in re.finditer(pattern, source_code):
                selector_value = match.group(1)
                text_value = match.group(2)
                
                if locator_type == 'id':
                    selector = f'#{selector_value}'
                elif locator_type == 'name':
                    selector = f"[name='{selector_value}']"
                elif locator_type == 'class':
                    selector = f'.{selector_value}'
                else:
                    selector = selector_value
                
                actions_with_pos.append((match.start(), ActionIntent(
                    action_type=ActionType.FILL,
                    target=selector,
                    value=text_value,
                    description=f"Fill {selector} with {text_value}",
                )))
        
        # Parse clear actions
        clear_patterns = [
            (r'find_element\(By\.ID,\s*["\']([^"\']+)["\']\)\.clear\(\)', 'id'),
            (r'find_element_by_id\(["\']([^"\']+)["\']\)\.clear\(\)', 'id'),
        ]
        
        for pattern, locator_type in clear_patterns:
            for match in re.finditer(pattern, source_code):
                value = match.group(1)
                selector = f'#{value}' if locator_type == 'id' else value
                actions_with_pos.append((match.start(), ActionIntent(
                    action_type=ActionType.FILL,
                    target=selector,
                    value="",
                    description=f"Clear {selector}",
                )))
        
        # Parse Select dropdown - handle both inline and multi-line
        # Pattern 1: Select(...).select_by_visible_text(...)
        select_pattern_inline = r'Select\([^)]*find_element\(By\.ID,\s*["\']([^"\']+)["\'][^)]*\)[^)]*\)\.select_by_visible_text\(["\']([^"\']+)["\']\)'
        for match in re.finditer(select_pattern_inline, source_code):
            selector_value = match.group(1)
            option_text = match.group(2)
            selector = f'#{selector_value}'
            actions_with_pos.append((match.start(), ActionIntent(
                action_type=ActionType.SELECT,
                target=selector,
                value=option_text,
                description=f"Select '{option_text}' in {selector}",
            )))
        
        # Pattern 2: variable = Select(find_element(...)); variable.select_by_visible_text(...)
        # First find Select assignments
        select_assignment_pattern = r'(\w+)\s*=\s*Select\([^)]*find_element\(By\.ID,\s*["\']([^"\']+)["\'][^)]*\)[^)]*\)'
        select_vars = {}
        for match in re.finditer(select_assignment_pattern, source_code):
            var_name = match.group(1)
            selector_value = match.group(2)
            select_vars[var_name] = f'#{selector_value}'
        
        # Then find select_by_visible_text calls
        for var_name, selector in select_vars.items():
            select_call_pattern = rf'{var_name}\.select_by_visible_text\(["\']([^"\']+)["\']\)'
            for match in re.finditer(select_call_pattern, source_code):
                option_text = match.group(1)
                actions_with_pos.append((match.start(), ActionIntent(
                    action_type=ActionType.SELECT,
                    target=selector,
                    value=option_text,
                    description=f"Select '{option_text}' in {selector}",
                )))
        
        # Sort actions by their position in source code
        actions_with_pos.sort(key=lambda x: x[0])
        actions = [action for _, action in actions_with_pos]
        
        # Parse assertions - visibility
        visibility_patterns = [
            (r'find_element\(By\.ID,\s*["\']([^"\']+)["\']\)\.is_displayed\(\)', 'id'),
            (r'find_element_by_id\(["\']([^"\']+)["\']\)\.is_displayed\(\)', 'id'),
        ]
        
        for pattern, locator_type in visibility_patterns:
            for match in re.finditer(pattern, source_code):
                value = match.group(1)
                selector = f'#{value}' if locator_type == 'id' else value
                
                # Check if it's in an assert statement
                line_start = source_code.rfind('\n', 0, match.start()) + 1
                line_end = source_code.find('\n', match.end())
                if line_end == -1:
                    line_end = len(source_code)
                line = source_code[line_start:line_end]
                
                if 'assert' in line.lower():
                    assertions.append(AssertionIntent(
                        assertion_type=AssertionType.VISIBLE,
                        target=selector,
                        expected="visible",
                        description=f"Assert {selector} is visible",
                    ))
        
        # Parse assertions - text content
        text_assert_patterns = [
            (r'find_element\(By\.ID,\s*["\']([^"\']+)["\']\)\.text', 'id'),
            (r'find_element_by_id\(["\']([^"\']+)["\']\)\.text', 'id'),
        ]
        
        for pattern, locator_type in text_assert_patterns:
            for match in re.finditer(pattern, source_code):
                value = match.group(1)
                selector = f'#{value}' if locator_type == 'id' else value
                
                # Find the assert statement - could be on same line or next line
                line_start = source_code.rfind('\n', 0, match.start()) + 1
                # Look ahead a few lines for the assertion
                rest_of_code = source_code[match.end():]
                lines_ahead = rest_of_code[:300]  # Look ahead ~5-10 lines
                
                # Check if this .text access is in an assignment followed by an assert
                # e.g., message = driver.find_element(...).text\n    assert message == 'Expected'
                text_var_match = re.search(r'(\w+)\s*=.*?' + re.escape(match.group(0)), source_code[:match.end()])
                if text_var_match:
                    var_name = text_var_match.group(1)
                    # Look for assert with this variable
                    assert_pattern = rf'assert\s+{var_name}\s*==\s*["\']([^"\']+)["\']'
                    assert_match = re.search(assert_pattern, lines_ahead)
                    if assert_match:
                        expected_text = assert_match.group(1)
                        assertions.append(AssertionIntent(
                            assertion_type=AssertionType.TEXT_CONTENT,
                            target=selector,
                            expected=expected_text,
                            description=f"Assert {selector} text equals '{expected_text}'",
                        ))
                        continue
                
                # Original inline check
                line_end = source_code.find('\n', match.end())
                if line_end == -1:
                    line_end = len(source_code)
                line = source_code[line_start:line_end]
                
                if 'assert' in line.lower():
                    # Extract expected text
                    expected_match = re.search(r'==\s*["\']([^"\']+)["\']', line)
                    if expected_match:
                        expected_text = expected_match.group(1)
                        assertions.append(AssertionIntent(
                            assertion_type=AssertionType.TEXT_CONTENT,
                            target=selector,
                            expected=expected_text,
                            description=f"Assert {selector} text equals '{expected_text}'",
                        ))
        
        return actions, assertions
    
    def _categorize_bdd_actions(self, intent: TestIntent, actions: List[ActionIntent], 
                                 assertions: List[AssertionIntent], bdd_structure: dict):
        """Categorize actions into Given/When/Then phases."""
        # For simplicity, we'll distribute actions based on their position and type
        total_actions = len(actions)
        
        if total_actions == 0:
            # No actions, just add assertions to then
            intent.then_steps = assertions
            for assertion in assertions:
                intent.add_assertion(assertion)
            return
        
        # Heuristic: First 1/3 are Given, middle 1/3 are When, last 1/3 are Then
        # Navigation and setup typically go in Given
        # Interactions go in When
        # Assertions go in Then
        
        for i, action in enumerate(actions):
            if action.action_type == ActionType.NAVIGATE:
                intent.given_steps.append(action)
            elif action.action_type in [ActionType.CLICK, ActionType.FILL, ActionType.SELECT]:
                intent.when_steps.append(action)
            else:
                intent.add_step(action)
        
        # All assertions go to Then
        intent.then_steps = assertions
        
        # Also add to main lists
        for action in actions:
            intent.add_step(action)
        for assertion in assertions:
            intent.add_assertion(assertion)
    
    def _sanitize_name(self, name: str) -> str:
        """Convert name to Python-friendly format."""
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Remove special characters
        name = re.sub(r'[^\w_]', '', name)
        # Convert to lowercase
        return name.lower()
