"""
Deterministic expansion of BDD Scenario Outlines into concrete scenarios.

This module provides framework-agnostic logic to expand Scenario Outlines
with Examples tables into individual concrete scenarios.
"""
import re
from typing import List
from .models import ScenarioOutline, ExamplesTable, ExpandedScenario


def expand_scenario_outline(
    outline: ScenarioOutline,
    examples: ExamplesTable
) -> List[ExpandedScenario]:
    """
    Expand a Scenario Outline into concrete scenarios based on Examples table.
    
    Each row in the Examples table produces one ExpandedScenario with:
    - Placeholders (<param>) replaced with row values
    - Scenario name including parameter values
    - Parameters dictionary for structured access
    
    Rules:
    - Each Examples row produces one ExpandedScenario
    - Replace <param> placeholders in steps with row values
    - Expanded scenario name must include parameter values
    - Do not mutate input objects
    - Deterministic output order (same as example row order)
    - No framework-specific logic
    
    Args:
        outline: The Scenario Outline with parameterized steps
        examples: The Examples table with parameter values
        
    Returns:
        List of ExpandedScenario objects, one per Examples row,
        in the same order as the rows in the Examples table
        
    Raises:
        ValueError: If a step contains a placeholder not in examples headers
        
    Example:
        >>> outline = ScenarioOutline(
        ...     name="User logs in",
        ...     steps=("login with <username> and <password>",),
        ...     tags=("auth",)
        ... )
        >>> examples = ExamplesTable(
        ...     headers=("username", "password", "result"),
        ...     rows=(("admin", "admin123", "success"),
        ...           ("user", "wrong123", "failure"))
        ... )
        >>> scenarios = expand_scenario_outline(outline, examples)
        >>> len(scenarios)
        2
        >>> scenarios[0].name
        'User logs in [admin/admin123]'
        >>> scenarios[0].steps[0]
        'login with admin and admin123'
    """
    # Validate placeholders in steps
    _validate_placeholders(outline.steps, examples.headers)
    
    expanded_scenarios = []
    
    # Process each row in the Examples table
    for row_index in range(len(examples.rows)):
        row_dict = examples.get_row_dict(row_index)
        
        # Replace placeholders in each step
        expanded_steps = []
        for step_template in outline.steps:
            expanded_step = _replace_placeholders(step_template, row_dict)
            expanded_steps.append(expanded_step)
        
        # Create scenario name with parameter values
        # Format: "Original Name [value1/value2/...]"
        param_suffix = _create_parameter_suffix(row_dict)
        scenario_name = f"{outline.name} {param_suffix}"
        
        # Create ExpandedScenario
        expanded = ExpandedScenario(
            name=scenario_name,
            steps=tuple(expanded_steps),
            parameters=row_dict,
            tags=outline.tags,
            original_outline_name=outline.name
        )
        expanded_scenarios.append(expanded)
    
    return expanded_scenarios


def _validate_placeholders(steps: tuple[str, ...], headers: tuple[str, ...]) -> None:
    """
    Validate that all placeholders in steps are present in examples headers.
    
    Args:
        steps: Step templates with placeholders
        headers: Available parameter names from Examples table
        
    Raises:
        ValueError: If a step contains a placeholder not in headers
    """
    header_set = set(headers)
    placeholder_pattern = re.compile(r'<(\w+)>')
    
    for step in steps:
        placeholders = placeholder_pattern.findall(step)
        for placeholder in placeholders:
            if placeholder not in header_set:
                raise ValueError(
                    f"Step contains placeholder '<{placeholder}>' "
                    f"but Examples table only has: {', '.join(headers)}"
                )


def _replace_placeholders(template: str, parameters: dict) -> str:
    """
    Replace <param> placeholders in a template string with actual values.
    
    Args:
        template: String with placeholders like "login with <username>"
        parameters: Dictionary mapping parameter names to values
        
    Returns:
        String with all placeholders replaced
        
    Example:
        >>> _replace_placeholders("login with <username> and <password>",
        ...                       {"username": "admin", "password": "admin123"})
        'login with admin and admin123'
    """
    result = template
    for param_name, param_value in parameters.items():
        placeholder = f"<{param_name}>"
        result = result.replace(placeholder, str(param_value))
    return result


def _create_parameter_suffix(parameters: dict) -> str:
    """
    Create a readable suffix for scenario name from parameters.
    
    Format: [value1/value2/value3]
    Values are ordered alphabetically by key name for determinism.
    
    Args:
        parameters: Dictionary of parameter name -> value
        
    Returns:
        Formatted suffix string
        
    Example:
        >>> _create_parameter_suffix({"password": "admin123", "username": "admin"})
        '[admin123/admin]'  # password comes first alphabetically
    """
    # Use consistent ordering (alphabetical by key) for determinism
    sorted_keys = sorted(parameters.keys())
    sorted_values = [str(parameters[key]) for key in sorted_keys]
    return f"[{'/'.join(sorted_values)}]"
