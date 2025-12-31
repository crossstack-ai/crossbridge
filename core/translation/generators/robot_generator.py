"""
Robot Framework Generator.

Generates Robot Framework tests from TestIntent.
"""

from typing import List

from core.translation.intent_model import (
    ActionIntent,
    ActionType,
    AssertionIntent,
    AssertionType,
    TestIntent,
    IntentType,
)
from core.translation.pipeline import TargetGenerator


class RobotGenerator(TargetGenerator):
    """Generator for Robot Framework tests."""
    
    def __init__(self, framework: str = "robot", config=None):
        """Initialize Robot generator."""
        if config is None:
            from core.translation.pipeline import TranslationConfig
            config = TranslationConfig(
                source_framework="selenium-java-bdd",
                target_framework=framework,
            )
        super().__init__(framework, config)
    
    def can_generate(self, intent: TestIntent) -> bool:
        """Check if we can generate Robot Framework code."""
        return intent.test_type in [
            IntentType.UI,
            IntentType.API,
            IntentType.BDD,
            IntentType.INTEGRATION,
        ]
    
    def generate(self, intent: TestIntent) -> str:
        """
        Generate Robot Framework test from TestIntent.
        
        Produces:
        - Robot Framework keyword-driven test
        - Settings section with library imports
        - Test Cases section
        - BDD-style Given/When/Then if applicable
        """
        lines = []
        
        # *** Settings *** section
        lines.append('*** Settings ***')
        lines.extend(self._generate_settings(intent))
        lines.append('')
        
        # *** Variables *** section (if needed)
        if intent.data:
            lines.append('*** Variables ***')
            for key, value in intent.data.items():
                lines.append(f'${{{key.upper()}}}    {value}')
            lines.append('')
        
        # *** Test Cases *** section
        lines.append('*** Test Cases ***')
        lines.extend(self._generate_test_case(intent))
        
        return '\n'.join(lines)
    
    def _generate_settings(self, intent: TestIntent) -> List[str]:
        """Generate Robot Framework settings."""
        lines = []
        
        # Documentation
        lines.append(f'Documentation    {intent.name}')
        if intent.source_framework:
            lines.append(f'...              Translated from: {intent.source_framework}')
        if intent.source_file:
            lines.append(f'...              Source file: {intent.source_file}')
        if intent.scenario:
            lines.append(f'...              Scenario: {intent.scenario.strip()}')
        lines.append(f'...              Confidence: {intent.confidence:.2f}')
        lines.append('')
        
        # Determine which libraries to import
        if intent.test_type in [IntentType.UI, IntentType.BDD]:
            # Check if using API actions
            has_api = any(action.action_type == ActionType.REQUEST for action in intent.steps)
            if has_api:
                lines.append('Library    RequestsLibrary')
            else:
                lines.append('Library    Browser    timeout=10s')
        elif intent.test_type == IntentType.API:
            lines.append('Library    RequestsLibrary')
            lines.append('Library    Collections')
        
        # Additional libraries
        lines.append('Library    BuiltIn')
        
        return lines
    
    def _generate_test_case(self, intent: TestIntent) -> List[str]:
        """Generate Robot Framework test case."""
        lines = []
        
        # Test case name
        test_name = self._convert_test_name(intent.name)
        lines.append(test_name)
        
        # Documentation
        if intent.description:
            lines.append(f'    [Documentation]    {intent.description}')
        
        # Tags
        if intent.tags:
            tags_str = '    '.join(intent.tags)
            lines.append(f'    [Tags]    {tags_str}')
        
        # TODOs
        if intent.todos:
            for todo in intent.todos:
                lines.append(f'    # TODO: {todo}')
        
        lines.append('')
        
        # Generate test steps based on type
        if intent.test_type == IntentType.BDD and (intent.given_steps or intent.when_steps or intent.then_steps):
            lines.extend(self._generate_bdd_keywords(intent))
        else:
            lines.extend(self._generate_regular_keywords(intent))
        
        return lines
    
    def _generate_bdd_keywords(self, intent: TestIntent) -> List[str]:
        """Generate BDD-style keywords (Given/When/Then)."""
        lines = []
        
        # Given
        if intent.given_steps:
            for i, action in enumerate(intent.given_steps):
                keyword = 'Given' if i == 0 else 'And'
                action_line = self._generate_action_keyword(action)
                lines.append(f'    {keyword}    {action_line}')
        
        # When
        if intent.when_steps:
            for i, action in enumerate(intent.when_steps):
                keyword = 'When' if i == 0 else 'And'
                action_line = self._generate_action_keyword(action)
                lines.append(f'    {keyword}    {action_line}')
        
        # Then
        if intent.then_steps:
            for i, assertion in enumerate(intent.then_steps):
                keyword = 'Then' if i == 0 else 'And'
                assertion_line = self._generate_assertion_keyword(assertion)
                lines.append(f'    {keyword}    {assertion_line}')
        
        # Fallback to regular structure if BDD steps not populated
        if not lines:
            lines.extend(self._generate_regular_keywords(intent))
        
        return lines
    
    def _generate_regular_keywords(self, intent: TestIntent) -> List[str]:
        """Generate regular Robot keywords."""
        lines = []
        
        # Setup
        for action in intent.setup_steps:
            lines.append(f'    {self._generate_action_keyword(action)}')
        
        # Main actions
        for action in intent.steps:
            action_line = self._generate_action_keyword(action)
            if action.line_number:
                lines.append(f'    # Source line: {action.line_number}')
            if action.confidence < 0.8:
                lines.append(f'    # Confidence: {action.confidence:.2f}')
            lines.append(f'    {action_line}')
        
        # Assertions
        for assertion in intent.assertions:
            assertion_line = self._generate_assertion_keyword(assertion)
            if assertion.line_number:
                lines.append(f'    # Source line: {assertion.line_number}')
            if assertion.confidence < 0.8:
                lines.append(f'    # Confidence: {assertion.confidence:.2f}')
            lines.append(f'    {assertion_line}')
        
        # Teardown
        for action in intent.teardown_steps:
            lines.append(f'    {self._generate_action_keyword(action)}')
        
        return lines
    
    def _generate_action_keyword(self, action: ActionIntent) -> str:
        """Generate Robot keyword for an action."""
        # Map action types to Robot keywords
        if action.action_type == ActionType.NAVIGATE:
            return f"New Page    {action.value}"
        
        elif action.action_type == ActionType.CLICK:
            selector = self._convert_selector(action.selector)
            return f"Click    {selector}"
        
        elif action.action_type == ActionType.FILL:
            selector = self._convert_selector(action.selector)
            return f"Fill Text    {selector}    {action.value}"
        
        elif action.action_type == ActionType.SELECT:
            selector = self._convert_selector(action.selector)
            return f"Select Options By    {selector}    value    {action.value}"
        
        elif action.action_type == ActionType.REQUEST:
            # API request
            method = action.semantics.get('method', 'GET')
            endpoint = action.value
            
            if method == 'GET':
                return f"GET    {endpoint}"
            elif method == 'POST':
                body = action.semantics.get('body', '{{}}')
                return f"POST    {endpoint}    json={body}"
            elif method == 'PUT':
                body = action.semantics.get('body', '{{}}')
                return f"PUT    {endpoint}    json={body}"
            elif method == 'DELETE':
                return f"DELETE    {endpoint}"
        
        elif action.action_type == ActionType.WAIT:
            if action.wait_strategy == "explicit":
                return f"# Wait removed - Robot auto-waits"
            else:
                return f"Sleep    {action.timeout or 1}s"
        
        elif action.action_type == ActionType.AUTH:
            if 'basic' in action.target.lower():
                username, password = action.value.split(':')
                return f"Create Session    api    auth=({username}, {password})"
        
        else:
            return f"# TODO: {action.description}"
    
    def _generate_assertion_keyword(self, assertion: AssertionIntent) -> str:
        """Generate Robot keyword for an assertion."""
        if assertion.assertion_type == AssertionType.VISIBLE:
            selector = self._convert_selector(assertion.selector)
            return f"Get Element State    {selector}    visible"
        
        elif assertion.assertion_type == AssertionType.TEXT_CONTENT:
            selector = self._convert_selector(assertion.selector)
            return f"Get Text    {selector}    ==    {assertion.expected}"
        
        elif assertion.assertion_type == AssertionType.EQUALS:
            selector = self._convert_selector(assertion.selector)
            return f"Get Value    {selector}    ==    {assertion.expected}"
        
        elif assertion.assertion_type == AssertionType.STATUS_CODE:
            return f"Status Should Be    {assertion.expected}"
        
        elif assertion.assertion_type == AssertionType.RESPONSE_BODY:
            # JSON path assertion
            json_path = assertion.target
            return f"Should Be Equal    ${{response.json()}}.{json_path}    {assertion.expected}"
        
        elif assertion.assertion_type == AssertionType.CONTAINS:
            return f"Should Contain    ${{response.text}}    {assertion.expected}"
        
        else:
            return f"# TODO: {assertion.description}"
    
    def _convert_selector(self, selector: str) -> str:
        """Convert selector to Robot Framework format."""
        if not selector:
            return "# TODO: Add selector"
        
        # Already in good format
        if selector.startswith('id=') or selector.startswith('css=') or selector.startswith('xpath='):
            return selector
        
        # Convert CSS selectors
        if selector.startswith('#'):
            return f"id={selector[1:]}"
        elif selector.startswith('.'):
            return f"css={selector}"
        elif selector.startswith('//'):
            return f"xpath={selector}"
        elif selector.startswith('['):
            return f"css={selector}"
        else:
            return f"css={selector}"
    
    def _convert_test_name(self, name: str) -> str:
        """Convert test name to Robot Framework format."""
        # Convert camelCase to Title Case with spaces
        import re
        name = re.sub('([a-z0-9])([A-Z])', r'\1 \2', name)
        name = name.replace('_', ' ')
        name = name.title()
        
        # Remove "Test" prefix if present
        if name.startswith('Test '):
            name = name[5:]
        
        return name
