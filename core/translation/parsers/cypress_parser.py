"""
Cypress Parser.

Extracts TestIntent from Cypress JavaScript/TypeScript test code.
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


class CypressParser(SourceParser):
    """Parser for Cypress JavaScript/TypeScript tests."""
    
    def __init__(self):
        """Initialize Cypress parser."""
        super().__init__("cypress")
        
        # Cypress selector patterns
        self.selector_patterns = [
            r'cy\.get\([\'"]([^\'"]+)[\'"]\)',  # cy.get('selector')
            r'cy\.contains\([\'"]([^\'"]+)[\'"]\)',  # cy.contains('text')
        ]
        
        # Action patterns
        self.action_patterns = {
            r'cy\.visit\([\'"]([^\'"]+)[\'"]\)': ActionType.NAVIGATE,
            r'cy\.go\([\'"]back[\'"]\)': ActionType.NAVIGATE,
            r'cy\.reload\(\)': ActionType.NAVIGATE,
            r'\.click\(\)': ActionType.CLICK,
            r'\.dblclick\(\)': ActionType.CLICK,
            r'\.type\([\'"]([^\'"]+)[\'"]\)': ActionType.FILL,
            r'\.clear\(\)': ActionType.FILL,
            r'\.select\([\'"]([^\'"]+)[\'"]\)': ActionType.SELECT,
            r'\.check\(\)': ActionType.CLICK,
            r'\.uncheck\(\)': ActionType.CLICK,
        }
        
        # Assertion patterns
        self.assertion_patterns = {
            r'\.should\([\'"]be\.visible[\'"]\)': AssertionType.VISIBLE,
            r'\.should\([\'"]exist[\'"]\)': AssertionType.VISIBLE,
            r'\.should\([\'"]have\.text[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)': AssertionType.TEXT_CONTENT,
            r'\.should\([\'"]contain[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)': AssertionType.CONTAINS,
            r'\.should\([\'"]have\.value[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)': AssertionType.EQUALS,
            r'\.should\([\'"]be\.checked[\'"]\)': AssertionType.EQUALS,
            r'\.should\([\'"]be\.disabled[\'"]\)': AssertionType.EQUALS,
            r'\.should\([\'"]be\.enabled[\'"]\)': AssertionType.EQUALS,
            r'\.should\([\'"]have\.class[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)': AssertionType.CONTAINS,
            r'\.should\([\'"]have\.attr[\'"]\s*,\s*[\'"]([^\'",]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)': AssertionType.EQUALS,
            r'\.should\([\'"]have\.length[\'"]\s*,\s*(\d+)\)': AssertionType.EQUALS,
        }
    
    def can_parse(self, source_code: str) -> bool:
        """Check if this is Cypress code."""
        indicators = [
            "cy.",
            "describe(",
            "it(",
            "Cypress",
            "cy.visit",
            "cy.get",
        ]
        # Check for at least 2 indicators to avoid false positives
        matches = sum(1 for indicator in indicators if indicator in source_code)
        return matches >= 2
    
    def parse(self, source_code: str, source_file: str = "") -> TestIntent:
        """Parse Cypress code into TestIntent."""
        # Extract test name
        test_name = self._extract_test_name(source_code)
        
        # Create intent
        intent = TestIntent(
            name=test_name,
            test_type=IntentType.UI,
            source_framework=self.framework,
            source_file=source_file,
        )
        
        # Parse actions and assertions
        actions = self._parse_actions(source_code)
        for action in actions:
            intent.add_step(action)
        
        assertions = self._parse_assertions(source_code)
        for assertion in assertions:
            intent.add_assertion(assertion)
        
        return intent
    
    def _extract_test_name(self, source_code: str) -> str:
        """Extract test name from describe/it blocks."""
        # Try to find it() block first (more specific than describe)
        it_match = re.search(r'it\([\'"]([^\'"]+)[\'"]', source_code)
        if it_match:
            name = it_match.group(1)
            # Avoid extracting URLs as test names
            if not name.startswith('http'):
                return self._sanitize_name(name)
        
        # Try to find test() block (alternative to it)
        test_match = re.search(r'test\([\'"]([^\'"]+)[\'"]', source_code)
        if test_match:
            name = test_match.group(1)
            if not name.startswith('http'):
                return self._sanitize_name(name)
        
        # Try to find describe() block
        describe_match = re.search(r'describe\([\'"]([^\'"]+)[\'"]', source_code)
        if describe_match:
            name = describe_match.group(1)
            if not name.startswith('http'):
                return self._sanitize_name(name)
        
        return "cypress_test"
    
    def _parse_actions(self, source_code: str) -> List[ActionIntent]:
        """Parse Cypress actions."""
        actions = []
        
        # Parse cy.visit (navigation)
        for match in re.finditer(r'cy\.visit\([\'"]([^\'"]+)[\'"]\)', source_code):
            url = match.group(1)
            actions.append(ActionIntent(
                action_type=ActionType.NAVIGATE,
                target=url,
                description=f"Navigate to {url}",
            ))
        
        # Parse cy.go('back') / cy.go('forward')
        for match in re.finditer(r'cy\.go\([\'"]([^\'"]+)[\'"]\)', source_code):
            direction = match.group(1)
            actions.append(ActionIntent(
                action_type=ActionType.NAVIGATE,
                target=direction,
                description=f"Navigate {direction}",
            ))
        
        # Parse cy.reload()
        if 'cy.reload()' in source_code:
            actions.append(ActionIntent(
                action_type=ActionType.NAVIGATE,
                target="reload",
                description="Reload page",
            ))
        
        # Parse chained actions: cy.get('selector').action()
        # Pattern: cy.get('selector').click()
        for match in re.finditer(
            r'cy\.get\([\'"]([^\'"]+)[\'"]\)([^\n;]+)',
            source_code
        ):
            selector = match.group(1)
            chain = match.group(2)
            
            # Parse click actions
            if '.click()' in chain:
                actions.append(ActionIntent(
                    action_type=ActionType.CLICK,
                    target=selector,
                    description=f"Click {selector}",
                ))
            
            # Parse type (fill) actions
            type_match = re.search(r'\.type\([\'"]([^\'"]+)[\'"]\)', chain)
            if type_match:
                value = type_match.group(1)
                actions.append(ActionIntent(
                    action_type=ActionType.FILL,
                    target=selector,
                    value=value,
                    description=f"Fill {selector} with {value}",
                ))
            
            # Parse clear actions
            if '.clear()' in chain:
                actions.append(ActionIntent(
                    action_type=ActionType.FILL,
                    target=selector,
                    value="",
                    description=f"Clear {selector}",
                ))
            
            # Parse select actions
            select_match = re.search(r'\.select\([\'"]([^\'"]+)[\'"]\)', chain)
            if select_match:
                value = select_match.group(1)
                actions.append(ActionIntent(
                    action_type=ActionType.SELECT,
                    target=selector,
                    value=value,
                    description=f"Select {value} in {selector}",
                ))
            
            # Parse check/uncheck actions
            if '.check()' in chain:
                actions.append(ActionIntent(
                    action_type=ActionType.CLICK,
                    target=selector,
                    description=f"Check {selector}",
                ))
            
            if '.uncheck()' in chain:
                actions.append(ActionIntent(
                    action_type=ActionType.CLICK,
                    target=selector,
                    description=f"Uncheck {selector}",
                ))
        
        # Parse cy.contains actions
        for match in re.finditer(
            r'cy\.contains\([\'"]([^\'"]+)[\'"]\)\.click\(\)',
            source_code
        ):
            text = match.group(1)
            actions.append(ActionIntent(
                action_type=ActionType.CLICK,
                target=f"text={text}",
                description=f"Click element containing '{text}'",
            ))
        
        return actions
    
    def _parse_assertions(self, source_code: str) -> List[AssertionIntent]:
        """Parse Cypress assertions."""
        assertions = []
        
        # Parse cy.get().should() assertions
        for match in re.finditer(
            r'cy\.get\([\'"]([^\'"]+)[\'"]\)\.should\(([^\)]+)\)',
            source_code
        ):
            selector = match.group(1)
            assertion_content = match.group(2)
            
            # Parse be.visible
            if "'be.visible'" in assertion_content or '"be.visible"' in assertion_content:
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.VISIBLE,
                    target=selector,
                    expected="visible",
                    description=f"Assert {selector} is visible",
                ))
            
            # Parse exist
            if "'exist'" in assertion_content or '"exist"' in assertion_content:
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.VISIBLE,
                    target=selector,
                    expected="exists",
                    description=f"Assert {selector} exists",
                ))
            
            # Parse have.text
            text_match = re.search(r'[\'"]have\.text[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]', assertion_content)
            if text_match:
                expected_text = text_match.group(1)
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.TEXT_CONTENT,
                    target=selector,
                    expected=expected_text,
                    description=f"Assert {selector} has text '{expected_text}'",
                ))
            
            # Parse contain
            contain_match = re.search(r'[\'"]contain[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]', assertion_content)
            if contain_match:
                expected_text = contain_match.group(1)
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.CONTAINS,
                    target=selector,
                    expected=expected_text,
                    description=f"Assert {selector} contains '{expected_text}'",
                ))
            
            # Parse have.value
            value_match = re.search(r'[\'"]have\.value[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]', assertion_content)
            if value_match:
                expected_value = value_match.group(1)
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.EQUALS,
                    target=selector,
                    expected=expected_value,
                    description=f"Assert {selector} value equals '{expected_value}'",
                ))
            
            # Parse be.checked
            if "'be.checked'" in assertion_content or '"be.checked"' in assertion_content:
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.EQUALS,
                    target=selector,
                    expected="true",
                    description=f"Assert {selector} is checked",
                ))
            
            # Parse be.disabled
            if "'be.disabled'" in assertion_content or '"be.disabled"' in assertion_content:
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.EQUALS,
                    target=selector,
                    expected="disabled",
                    description=f"Assert {selector} is disabled",
                ))
            
            # Parse be.enabled
            if "'be.enabled'" in assertion_content or '"be.enabled"' in assertion_content:
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.EQUALS,
                    target=selector,
                    expected="enabled",
                    description=f"Assert {selector} is enabled",
                ))
            
            # Parse have.class
            class_match = re.search(r'[\'"]have\.class[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]', assertion_content)
            if class_match:
                class_name = class_match.group(1)
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.CONTAINS,
                    target=selector,
                    expected=class_name,
                    description=f"Assert {selector} has class '{class_name}'",
                ))
            
            # Parse have.attr
            attr_match = re.search(
                r'[\'"]have\.attr[\'"]\s*,\s*[\'"]([^\'",]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]',
                assertion_content
            )
            if attr_match:
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2)
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.EQUALS,
                    target=selector,
                    expected=f"{attr_name}={attr_value}",
                    description=f"Assert {selector} has {attr_name}='{attr_value}'",
                ))
            
            # Parse have.length
            length_match = re.search(r'[\'"]have\.length[\'"]\s*,\s*(\d+)', assertion_content)
            if length_match:
                expected_length = length_match.group(1)
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.EQUALS,
                    target=selector,
                    expected=expected_length,
                    description=f"Assert {selector} has length {expected_length}",
                ))
        
        # Parse cy.url().should() assertions
        url_match = re.search(r'cy\.url\(\)\.should\([\'"]include[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)', source_code)
        if url_match:
            expected_url = url_match.group(1)
            assertions.append(AssertionIntent(
                assertion_type=AssertionType.CONTAINS,
                target="url",
                expected=expected_url,
                description=f"Assert URL contains '{expected_url}'",
            ))
        
        return assertions
    
    def _sanitize_name(self, name: str) -> str:
        """Convert test name to Python-friendly format."""
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Remove special characters
        name = re.sub(r'[^\w_]', '', name)
        # Convert to lowercase
        return name.lower()
