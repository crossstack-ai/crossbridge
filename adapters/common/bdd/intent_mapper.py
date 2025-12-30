"""
Map expanded BDD scenarios to framework-agnostic IntentModel.

Converts ExpandedScenario objects from outline expansion into IntentModel
objects suitable for migration, AI analysis, and cross-framework processing.
"""
from typing import List, Optional
import re
from adapters.common.models import IntentModel, TestStep, Assertion, AssertionType
from .models import ExpandedScenario


# Optional import for step-to-code mapping integration
try:
    from adapters.common.mapping import StepMappingResolver
    MAPPING_AVAILABLE = True
except ImportError:
    MAPPING_AVAILABLE = False
    StepMappingResolver = None


def map_expanded_scenario_to_intent(
    scenario: ExpandedScenario,
    resolver: Optional['StepMappingResolver'] = None
) -> IntentModel:
    """
    Convert an ExpandedScenario to an IntentModel for migration pipeline.
    
    Extracts structured intent representation from expanded BDD scenarios:
    - Intent = scenario name without parameter suffix
    - Steps = expanded steps with action/target parsing
    - Assertions = extracted from 'Then' steps as placeholders
    - Code Paths = resolved from steps if resolver is provided (NEW)
    
    Args:
        scenario: ExpandedScenario with concrete parameter values
        resolver: Optional StepMappingResolver to populate code_paths
        
    Returns:
        IntentModel with populated test_name, intent, steps, assertions, and code_paths
        
    Example:
        >>> scenario = ExpandedScenario(
        ...     name="User logs in [admin/admin123]",
        ...     steps=("Given user is on login page",
        ...            "When user logs in with admin and admin123",
        ...            "Then login should be success"),
        ...     parameters={"username": "admin", "password": "admin123", "result": "success"},
        ...     original_outline_name="User logs in"
        ... )
        >>> intent = map_expanded_scenario_to_intent(scenario)
        >>> intent.test_name
        'User logs in [admin/admin123]'
        >>> intent.intent
        'User logs in'
        >>> len(intent.steps)
        3
        
        # With resolver for code path mapping
        >>> from adapters.common.mapping import StepMappingResolver, StepSignalRegistry
        >>> registry = StepSignalRegistry()
        >>> # ... register signals ...
        >>> resolver = StepMappingResolver(registry)
        >>> intent = map_expanded_scenario_to_intent(scenario, resolver)
        >>> intent.code_paths
        ['pages/login_page.py::LoginPage.open', 'pages/login_page.py::LoginPage.login']
    """
    # Extract intent from original outline name (without parameter suffix)
    intent_description = scenario.original_outline_name or _remove_parameter_suffix(scenario.name)
    
    # Parse steps into structured TestStep objects
    test_steps = _parse_steps_to_test_steps(scenario.steps)
    
    # Extract assertions from 'Then' steps
    assertions = _extract_assertions_from_steps(scenario.steps)
    
    # Resolve code paths if resolver is provided
    code_paths = []
    if resolver is not None and MAPPING_AVAILABLE:
        code_paths = _resolve_code_paths_for_steps(scenario.steps, resolver)
    
    return IntentModel(
        test_name=scenario.name,
        intent=intent_description,
        steps=test_steps,
        assertions=assertions,
        code_paths=code_paths
    )


def _remove_parameter_suffix(scenario_name: str) -> str:
    """
    Remove parameter suffix from scenario name.
    
    Converts "User logs in [admin/admin123]" -> "User logs in"
    
    Args:
        scenario_name: Scenario name with parameter suffix
        
    Returns:
        Scenario name without parameter suffix
    """
    # Pattern matches "[anything]" at the end of the string
    pattern = r'\s*\[.+\]\s*$'
    return re.sub(pattern, '', scenario_name).strip()


def _parse_steps_to_test_steps(steps: tuple[str, ...]) -> List[TestStep]:
    """
    Parse BDD steps into structured TestStep objects.
    
    Extracts action (Given/When/Then/And/But) and description from each step.
    
    Args:
        steps: Tuple of BDD step strings
        
    Returns:
        List of TestStep objects with parsed action and description
        
    Example:
        >>> steps = ("Given user is on login page",
        ...          "When user logs in with admin and admin123",
        ...          "Then login should be success")
        >>> test_steps = _parse_steps_to_test_steps(steps)
        >>> test_steps[0].action
        'Given'
        >>> test_steps[0].description
        'user is on login page'
    """
    test_steps = []
    
    for step in steps:
        parsed = _parse_single_step(step)
        if parsed:
            test_steps.append(parsed)
    
    return test_steps


def _parse_single_step(step: str) -> TestStep:
    """
    Parse a single BDD step string into a TestStep.
    
    Extracts keyword (Given/When/Then/And/But) and the rest as description.
    
    Args:
        step: BDD step string (e.g., "Given user is on login page")
        
    Returns:
        TestStep with action and description populated
    """
    # Pattern to match BDD keywords at start of step
    keyword_pattern = r'^\s*(Given|When|Then|And|But)\s+(.+)$'
    match = re.match(keyword_pattern, step, re.IGNORECASE)
    
    if match:
        keyword = match.group(1).capitalize()
        description = match.group(2).strip()
        
        # Extract target if present (basic heuristic)
        target = _extract_target_from_description(description)
        
        return TestStep(
            description=step,  # Keep full step as description
            action=keyword,
            target=target
        )
    else:
        # No keyword found, treat entire step as description
        return TestStep(
            description=step,
            action="Step",
            target=None
        )


def _extract_target_from_description(description: str) -> str | None:
    """
    Extract target element from step description (basic heuristic).
    
    Looks for common patterns like quoted strings or specific UI elements.
    
    Args:
        description: Step description text
        
    Returns:
        Extracted target or None
        
    Example:
        >>> _extract_target_from_description('user clicks "Login" button')
        'Login'
        >>> _extract_target_from_description('user is on login page')
        'login page'
    """
    # Try to extract quoted text first
    quoted_pattern = r'["\']([^"\']+)["\']'
    quoted_match = re.search(quoted_pattern, description)
    if quoted_match:
        return quoted_match.group(1)
    
    # Try to extract common UI element patterns
    ui_patterns = [
        r'on\s+(\w+\s+page)',  # "on login page"
        r'clicks?\s+(\w+\s+button)',  # "clicks Login button"
        r'enters?\s+.+\s+into\s+(\w+\s+field)',  # "enters text into username field"
        r'selects?\s+.+\s+from\s+(\w+)',  # "selects option from dropdown"
    ]
    
    for pattern in ui_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def _extract_assertions_from_steps(steps: tuple[str, ...]) -> List[Assertion]:
    """
    Extract assertions from 'Then' steps as placeholders.
    
    Creates basic Assertion objects from Then steps for future refinement.
    
    Args:
        steps: Tuple of BDD step strings
        
    Returns:
        List of Assertion objects extracted from Then steps
        
    Example:
        >>> steps = ("Given user is on login page",
        ...          "Then login should be success")
        >>> assertions = _extract_assertions_from_steps(steps)
        >>> len(assertions)
        1
        >>> assertions[0].type
        <AssertionType.ELEMENT_VISIBLE: 'element_visible'>
    """
    assertions = []
    
    for step in steps:
        # Only process Then steps
        if re.match(r'^\s*Then\s+', step, re.IGNORECASE):
            # Create placeholder assertion (to be refined by AI or manual process)
            assertion = Assertion(
                type=AssertionType.EXISTS,  # Default type (element/condition exists)
                expected=step  # Store full step for now
            )
            assertions.append(assertion)
    
    return assertions


def _resolve_code_paths_for_steps(
    steps: tuple[str, ...],
    resolver: 'StepMappingResolver'
) -> List[str]:
    """
    Resolve code paths for all steps using the mapping resolver.
    
    Queries the resolver for each step and collects all unique code paths.
    
    Args:
        steps: Tuple of BDD step strings
        resolver: StepMappingResolver with registered signals
        
    Returns:
        List of unique code paths for all steps
        
    Example:
        >>> steps = ("Given user is on login page",
        ...          "When user logs in with admin and admin123")
        >>> code_paths = _resolve_code_paths_for_steps(steps, resolver)
        >>> code_paths
        ['pages/login_page.py::LoginPage.open', 'pages/login_page.py::LoginPage.login']
    """
    all_code_paths = []
    
    for step in steps:
        mapping = resolver.resolve_step(step)
        all_code_paths.extend(mapping.code_paths)
    
    # Return unique code paths (preserve order)
    seen = set()
    unique_paths = []
    for path in all_code_paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    
    return unique_paths
