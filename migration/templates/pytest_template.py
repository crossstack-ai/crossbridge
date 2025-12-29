"""
Pytest test template generator.

This module provides deterministic template generation for pytest tests
from framework-agnostic IntentModel objects. Used by the migration pipeline
to generate pytest-compatible test code.
"""

from typing import Dict, Any

from adapters.common.models import IntentModel, AssertionType


def generate_pytest_test(intent: IntentModel, config: Dict[str, Any] = None) -> str:
    """
    Generate pytest test code from an IntentModel.
    
    This function creates a deterministic pytest test function from a
    framework-agnostic intent model. The generated code follows pytest
    conventions and includes placeholder comments for manual refinement.
    
    Args:
        intent: Framework-agnostic test intent model.
        config: Optional configuration for code generation. Supported keys:
            - 'indent_spaces': Number of spaces for indentation (default: 4)
            - 'add_imports': Whether to include import statements (default: True)
            - 'add_fixtures': List of fixture names to include as parameters
            
    Returns:
        str: Generated pytest test code as a string.
        
    Example:
        >>> intent = IntentModel(
        ...     test_name="login",
        ...     intent="Verify user can log in with valid credentials",
        ...     steps=[...],
        ...     assertions=[...]
        ... )
        >>> code = generate_pytest_test(intent)
        >>> print(code)
    """
    config = config or {}
    indent = ' ' * config.get('indent_spaces', 4)
    add_imports = config.get('add_imports', True)
    fixtures = config.get('add_fixtures', [])
    
    lines = []
    
    # Add imports if requested
    if add_imports:
        lines.append("import pytest")
        lines.append("")
        lines.append("")
    
    # Generate test function signature
    test_name = intent.test_name
    if not test_name.startswith('test_'):
        test_name = f'test_{test_name}'
    
    # Add fixtures to parameters if specified
    params = ', '.join(fixtures) if fixtures else ''
    lines.append(f"def {test_name}({params}):")
    
    # Add docstring with intent description
    lines.append(f'{indent}"""')
    lines.append(f'{indent}{intent.intent}')
    lines.append(f'{indent}"""')
    
    # Add test steps as comments and action placeholders
    if intent.steps:
        lines.append("")
        lines.append(f"{indent}# Test Steps")
        for i, step in enumerate(intent.steps, 1):
            lines.append(f"{indent}# Step {i}: {step.description}")
            
            # Generate action code placeholder
            action_name = _sanitize_action_name(step.action)
            if step.target:
                lines.append(f"{indent}{action_name}('{step.target}')  # TODO: Implement this step")
            else:
                lines.append(f"{indent}{action_name}()  # TODO: Implement this step")
            lines.append("")
    
    # Add assertions
    if intent.assertions:
        lines.append(f"{indent}# Assertions")
        for i, assertion in enumerate(intent.assertions, 1):
            assertion_code = _generate_assertion_code(assertion, indent)
            lines.append(f"{indent}# Assertion {i}: {assertion.type.value}")
            lines.append(f"{indent}{assertion_code}")
            if i < len(intent.assertions):
                lines.append("")
    
    # If no steps or assertions, add pass statement
    if not intent.steps and not intent.assertions:
        lines.append(f"{indent}# TODO: Implement test logic")
        lines.append(f"{indent}pass")
    
    lines.append("")
    
    return '\n'.join(lines)


def generate_pytest_module(intents: list[IntentModel], config: Dict[str, Any] = None) -> str:
    """
    Generate a complete pytest module with multiple test functions.
    
    Creates a pytest test file containing multiple test functions, one for
    each IntentModel in the provided list. Useful for migrating entire
    test suites or test classes.
    
    Args:
        intents: List of intent models to generate tests for.
        config: Optional configuration for code generation.
        
    Returns:
        str: Complete pytest module code with all test functions.
        
    Example:
        >>> intents = [intent1, intent2, intent3]
        >>> module_code = generate_pytest_module(intents)
        >>> with open('test_generated.py', 'w') as f:
        ...     f.write(module_code)
    """
    config = config or {}
    
    lines = []
    
    # Module-level docstring
    lines.append('"""')
    lines.append("Generated pytest tests from intent models.")
    lines.append("TODO: Review and customize generated code before use.")
    lines.append('"""')
    lines.append("")
    
    # Imports (only add once at module level)
    lines.append("import pytest")
    lines.append("")
    lines.append("")
    
    # Generate each test function
    test_config = config.copy()
    test_config['add_imports'] = False  # Don't add imports for each test
    
    for i, intent in enumerate(intents):
        test_code = generate_pytest_test(intent, test_config)
        lines.append(test_code)
        
        # Add spacing between tests
        if i < len(intents) - 1:
            lines.append("")
    
    return '\n'.join(lines)


def _sanitize_action_name(action: str) -> str:
    """
    Sanitize action name to be a valid Python identifier.
    
    Args:
        action: Raw action name from intent model.
        
    Returns:
        str: Sanitized action name suitable for use in code.
    """
    if not action:
        return "perform_action"
    
    # Replace spaces and special characters with underscores
    sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in action)
    
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f'action_{sanitized}'
    
    # Convert to lowercase
    sanitized = sanitized.lower()
    
    # Remove consecutive underscores
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    
    # Strip leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized or 'perform_action'


def _generate_assertion_code(assertion, indent: str) -> str:
    """
    Generate pytest assertion code from an Assertion model.
    
    Args:
        assertion: Assertion model to convert to code.
        indent: Indentation string for the assertion.
        
    Returns:
        str: Python assertion code as string.
    """
    assertion_type = assertion.type
    expected = assertion.expected
    
    # Generate appropriate assertion based on type
    if assertion_type == AssertionType.EQUALS:
        return f"assert actual == {repr(expected)}  # TODO: Replace 'actual' with actual value"
    
    elif assertion_type == AssertionType.NOT_EQUALS:
        return f"assert actual != {repr(expected)}  # TODO: Replace 'actual' with actual value"
    
    elif assertion_type == AssertionType.CONTAINS:
        return f"assert {repr(expected)} in actual  # TODO: Replace 'actual' with actual value"
    
    elif assertion_type == AssertionType.GREATER_THAN:
        return f"assert actual > {repr(expected)}  # TODO: Replace 'actual' with actual value"
    
    elif assertion_type == AssertionType.LESS_THAN:
        return f"assert actual < {repr(expected)}  # TODO: Replace 'actual' with actual value"
    
    elif assertion_type == AssertionType.EXISTS:
        return f"assert {expected}  # TODO: Verify existence condition"
    
    elif assertion_type == AssertionType.NOT_EXISTS:
        return f"assert not {expected}  # TODO: Verify non-existence condition"
    
    else:
        return f"assert True  # TODO: Implement {assertion_type.value} assertion"
