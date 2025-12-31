"""
Pytest Generator (API variant).

Generates pytest tests with requests library from TestIntent.
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


class PytestGenerator(TargetGenerator):
    """Generator for pytest tests (API and unit tests)."""
    
    def __init__(self, framework: str = "pytest", config=None):
        """Initialize pytest generator."""
        if config is None:
            from core.translation.pipeline import TranslationConfig
            config = TranslationConfig(
                source_framework="restassured",
                target_framework=framework,
            )
        super().__init__(framework, config)
    
    def can_generate(self, intent: TestIntent) -> bool:
        """Check if we can generate pytest code."""
        return intent.test_type in [
            IntentType.API,
            IntentType.UNIT,
            IntentType.INTEGRATION,
            IntentType.BDD,
        ]
    
    def generate(self, intent: TestIntent) -> str:
        """
        Generate pytest test from TestIntent.
        
        Produces:
        - pytest-style test function
        - requests library for API tests
        - Clean AAA pattern (Arrange, Act, Assert)
        - Idiomatic Python assertions
        """
        lines = []
        
        # Add header comment
        lines.append(f'"""')
        lines.append(f'{intent.name}')
        lines.append(f'')
        lines.append(f'Translated from: {intent.source_framework}')
        if intent.source_file:
            lines.append(f'Source file: {intent.source_file}')
        if intent.scenario:
            lines.append(f'')
            lines.append(f'Scenario:')
            for line in intent.scenario.strip().split('\n'):
                lines.append(f'{line}')
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
        imports = []
        
        if intent.test_type == IntentType.API:
            imports.append('import requests')
            imports.append('import pytest')
        elif intent.test_type == IntentType.BDD:
            imports.append('import pytest')
            # Check if UI or API
            if any(action.action_type == ActionType.REQUEST for action in intent.steps):
                imports.append('import requests')
            else:
                imports.append('from playwright.sync_api import Page, expect')
        else:
            imports.append('import pytest')
        
        return imports
    
    def _generate_test_function(self, intent: TestIntent) -> List[str]:
        """Generate the main test function."""
        lines = []
        
        # Function signature
        function_name = self._convert_test_name(intent.name)
        
        # Add fixtures based on test type
        if intent.test_type == IntentType.API:
            lines.append(f'def {function_name}():')
        elif intent.test_type == IntentType.BDD and self._is_api_bdd(intent):
            lines.append(f'def {function_name}():')
        else:
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
        
        # Generate based on test type
        if intent.test_type == IntentType.BDD:
            lines.extend(self._generate_bdd_test(intent))
        else:
            lines.extend(self._generate_api_test(intent))
        
        return lines
    
    def _generate_bdd_test(self, intent: TestIntent) -> List[str]:
        """Generate BDD-style test with AAA pattern."""
        lines = []
        
        # Given (Arrange)
        if intent.given_steps:
            lines.append('    # Given - Arrange')
            for action in intent.given_steps:
                action_lines = self._generate_action(action)
                lines.extend([f'    {line}' for line in action_lines])
            lines.append('')
        
        # When (Act)
        if intent.when_steps:
            lines.append('    # When - Act')
            for action in intent.when_steps:
                action_lines = self._generate_action(action)
                lines.extend([f'    {line}' for line in action_lines])
            lines.append('')
        
        # Then (Assert)
        if intent.then_steps:
            lines.append('    # Then - Assert')
            for assertion in intent.then_steps:
                assertion_lines = self._generate_assertion(assertion)
                lines.extend([f'    {line}' for line in assertion_lines])
        
        # Fallback to regular structure if BDD steps not populated
        if not (intent.given_steps or intent.when_steps or intent.then_steps):
            lines.extend(self._generate_api_test(intent))
        
        return lines
    
    def _generate_api_test(self, intent: TestIntent) -> List[str]:
        """Generate API test with AAA pattern."""
        lines = []
        
        # Arrange (setup)
        if intent.setup_steps:
            lines.append('    # Arrange')
            for action in intent.setup_steps:
                action_lines = self._generate_action(action)
                lines.extend([f'    {line}' for line in action_lines])
            lines.append('')
        
        # Act (main actions)
        for action in intent.steps:
            action_lines = self._generate_action(action)
            lines.extend([f'    {line}' for line in action_lines])
        
        # Assert
        if intent.assertions:
            lines.append('')
            lines.append('    # Assert')
            for assertion in intent.assertions:
                assertion_lines = self._generate_assertion(assertion)
                lines.extend([f'    {line}' for line in assertion_lines])
        
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
        if action.action_type == ActionType.REQUEST:
            # HTTP request
            method = action.semantics.get('method', 'GET')
            endpoint = action.value
            
            # Build request parameters
            params = []
            
            # Auth
            if action.semantics.get('auth'):
                auth = action.semantics['auth']
                if auth[0] == 'basic':
                    params.append(f"auth=('{auth[1]}', '{auth[2]}')")
            
            # Headers
            if action.semantics.get('headers'):
                headers = action.semantics['headers']
                headers_str = ', '.join([f"'{k}': '{v}'" for k, v in headers.items()])
                params.append(f"headers={{{headers_str}}}")
            
            # Body (for POST/PUT)
            if action.semantics.get('body'):
                body = action.semantics['body']
                if body.startswith('$'):
                    # Variable
                    params.append(f"json={body[2:-1]}")
                else:
                    params.append(f"json={body}")
            
            params_str = ', '.join(params)
            if params_str:
                lines.append(f"response = requests.{method.lower()}('{endpoint}', {params_str})")
            else:
                lines.append(f"response = requests.{method.lower()}('{endpoint}')")
        
        elif action.action_type == ActionType.AUTH:
            # Auth setup
            lines.append(f"# Authentication: {action.target}")
            if 'basic' in action.target.lower():
                username, password = action.value.split(':')
                lines.append(f"auth = ('{username}', '{password}')")
        
        elif action.action_type == ActionType.CUSTOM:
            lines.append(f'# TODO: Implement custom action: {action.description}')
        
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
        if assertion.assertion_type == AssertionType.STATUS_CODE:
            lines.append(f'assert response.status_code == {assertion.expected}')
        
        elif assertion.assertion_type == AssertionType.RESPONSE_BODY:
            # JSON path assertion
            json_path = assertion.target
            # Convert dot notation to bracket notation
            path_parts = json_path.split('.')
            access_chain = 'response.json()'
            for part in path_parts:
                if part:
                    access_chain += f"['{part}']"
            lines.append(f"assert {access_chain} == '{assertion.expected}'")
        
        elif assertion.assertion_type == AssertionType.HEADER:
            lines.append(f"assert response.headers['{assertion.target}'] == '{assertion.expected}'")
        
        elif assertion.assertion_type == AssertionType.CONTAINS:
            lines.append(f"assert '{assertion.expected}' in response.text")
        
        elif assertion.assertion_type == AssertionType.CUSTOM:
            lines.append(f'# TODO: Implement custom assertion: {assertion.description}')
        
        else:
            lines.append(f'# TODO: Implement {assertion.assertion_type.value} assertion')
        
        return lines
    
    def _convert_test_name(self, name: str) -> str:
        """Convert test name to Python snake_case."""
        import re
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        name = name.lower()
        
        if not name.startswith('test_'):
            name = f'test_{name}'
        
        return name
    
    def _is_api_bdd(self, intent: TestIntent) -> bool:
        """Check if BDD test is API-based."""
        return any(action.action_type == ActionType.REQUEST 
                   for action in intent.steps + intent.given_steps + intent.when_steps)
