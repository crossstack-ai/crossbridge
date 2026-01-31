"""
Robot Framework Failure Classification Module.

Provides intelligent failure analysis for Robot Framework tests to enable
root cause analysis, failure grouping, and flaky test detection.

This module addresses Gap 6.1 in the Framework Gap Analysis:
- Categorizes keyword-driven test failures (keyword, library, locator, assertion)
- Detects intermittent failures (timeouts, network issues)
- Extracts resource files and libraries
- Distinguishes between test-level and library-level failures

Usage:
    from adapters.robot.failure_classifier import classify_robot_failure
    
    classification = classify_robot_failure(
        error_message="ElementNotFound: Element with locator 'id:submit-button' not found",
        stack_trace="test_login.robot:25\nSeleniumLibrary.Click Element",
        test_name="Login With Valid Credentials"
    )
    
    print(f"Type: {classification.failure_type}")
    print(f"Library: {classification.library_name}")
    print(f"Intermittent: {classification.is_intermittent}")
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

from adapters.common.failure_classification import (
    BaseFailureClassification,
    StackFrame,
    FailureLocation,
    ComponentType,
)


class RobotFailureType(Enum):
    """Robot Framework-specific failure types."""
    # Keyword failures
    KEYWORD_NOT_FOUND = "keyword_not_found"       # Keyword doesn't exist
    KEYWORD_FAILED = "keyword_failed"             # Keyword execution failed
    KEYWORD_TIMEOUT = "keyword_timeout"           # Keyword execution timeout
    
    # Library failures
    LIBRARY_IMPORT_FAILED = "library_import"       # Library import failed
    LIBRARY_NOT_FOUND = "library_not_found"       # Library doesn't exist
    LIBRARY_INIT_FAILED = "library_init_failed"   # Library initialization failed
    
    # SeleniumLibrary specific
    LOCATOR_NOT_FOUND = "locator_not_found"       # Element locator not found
    ELEMENT_NOT_VISIBLE = "element_not_visible"   # Element exists but not visible
    ELEMENT_NOT_CLICKABLE = "element_not_clickable" # Element exists but not clickable
    
    # Timeout failures
    TIMEOUT = "timeout"                            # Generic wait timeout
    PAGE_LOAD_TIMEOUT = "page_load_timeout"       # Page load timeout
    WAIT_UNTIL_TIMEOUT = "wait_until_timeout"     # Wait Until keyword timeout
    
    # Assertion failures
    ASSERTION_FAILED = "assertion"                 # Should Be Equal, Should Contain, etc.
    CONDITION_NOT_MET = "condition_not_met"       # Run Keyword If condition false
    
    # Variable failures
    VARIABLE_NOT_FOUND = "variable_not_found"     # ${VAR} not defined
    VARIABLE_ERROR = "variable_error"             # Variable evaluation error
    
    # Network/API failures
    NETWORK_ERROR = "network_error"                # RequestsLibrary network error
    HTTP_ERROR = "http_error"                      # HTTP status error (4xx, 5xx)
    
    # Browser/Driver failures
    BROWSER_ERROR = "browser_error"                # Browser/driver error
    BROWSER_CRASH = "browser_crash"                # Browser crashed
    DRIVER_ERROR = "driver_error"                  # WebDriver error
    
    # Resource failures
    RESOURCE_NOT_FOUND = "resource_not_found"     # Resource file missing
    RESOURCE_IMPORT_FAILED = "resource_import_failed" # Resource import failed
    
    # Setup/Teardown failures
    SETUP_FAILED = "setup_failed"                  # Test Setup or Suite Setup failed
    TEARDOWN_FAILED = "teardown_failed"            # Test Teardown or Suite Teardown failed
    
    # Other
    SYNTAX_ERROR = "syntax_error"                  # Robot syntax error
    UNKNOWN = "unknown"


@dataclass
class RobotFailureClassification(BaseFailureClassification):
    """Robot Framework-specific failure classification."""
    failure_type: RobotFailureType = RobotFailureType.UNKNOWN
    keyword_name: Optional[str] = None              # Failed keyword name
    library_name: Optional[str] = None              # Library containing keyword
    locator: Optional[str] = None                   # Locator string (for locator failures)
    locator_strategy: Optional[str] = None          # id, xpath, css, etc.
    variable_name: Optional[str] = None             # Variable name (for variable failures)
    resource_file: Optional[str] = None             # Resource file path
    timeout_value: Optional[str] = None             # Timeout value (e.g., "30s")
    assertion_type: Optional[str] = None            # Type of assertion (Should Be Equal, etc.)
    http_status: Optional[int] = None               # HTTP status code (for HTTP errors)
    test_phase: Optional[str] = None                # setup, test, teardown
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "keyword_name": self.keyword_name,
            "library_name": self.library_name,
            "locator": self.locator,
            "locator_strategy": self.locator_strategy,
            "variable_name": self.variable_name,
            "resource_file": self.resource_file,
            "timeout_value": self.timeout_value,
            "assertion_type": self.assertion_type,
            "http_status": self.http_status,
            "test_phase": self.test_phase,
        })
        return base_dict


# Pattern matching for failure types
FAILURE_PATTERNS = {
    # Keyword failures
    RobotFailureType.KEYWORD_NOT_FOUND: [
        r"No keyword with name '(.+?)' found",
        r"Keyword '(.+?)' could not be found",
        r"Unknown keyword '(.+?)'",
    ],
    
    # Library failures
    RobotFailureType.LIBRARY_IMPORT_FAILED: [
        r"Importing (?:test )?library '(.+?)' failed",
        r"ImportError: No module named '(.+?)'",
        r"ModuleNotFoundError: No module named '(.+?)'",
    ],
    RobotFailureType.LIBRARY_NOT_FOUND: [
        r"Test library '(.+?)' does not exist",
        r"Library '(.+?)' not found",
    ],
    
    # SeleniumLibrary locator failures
    RobotFailureType.LOCATOR_NOT_FOUND: [
        r"Element with locator '(.+?)' not found",
        r"Element '(.+?)' did not appear",
        r"No element with locator '(.+?)' found",
        r"Unable to locate element: (.+)",
    ],
    RobotFailureType.ELEMENT_NOT_VISIBLE: [
        r"Element '(.+?)' is not visible",
        r"Element with locator '(.+?)' not visible",
    ],
    RobotFailureType.ELEMENT_NOT_CLICKABLE: [
        r"Element '(.+?)' is not clickable",
        r"Element with locator '(.+?)' not clickable",
        r"element click intercepted",
    ],
    
    # Timeout failures
    RobotFailureType.TIMEOUT: [
        r"Timeout (\d+(?:ms|s)) exceeded",
        r"Timed out after (\d+) seconds",
        r"Timeout waiting for",
    ],
    RobotFailureType.WAIT_UNTIL_TIMEOUT: [
        r"'Wait Until .+?' failed after retrying for (\d+)",
        r"Condition .+? did not become true in (\d+)",
    ],
    
    # Assertion failures
    RobotFailureType.ASSERTION_FAILED: [
        r"Should Be Equal:",
        r"Should Contain:",
        r"Should Not Contain:",
        r"Should Be True:",
        r"Should Be False:",
        r"Should Match:",
        r"Should Start With:",
        r"Should End With:",
    ],
    
    # Variable failures
    RobotFailureType.VARIABLE_NOT_FOUND: [
        r"Variable '\$\{(.+?)\}' not found",
        r"Non-existing variable '\$\{(.+?)\}'",
    ],
    
    # Network/HTTP failures
    RobotFailureType.NETWORK_ERROR: [
        r"Connection refused",
        r"Connection timeout",
        r"Name or service not known",
        r"Failed to establish a new connection",
    ],
    RobotFailureType.HTTP_ERROR: [
        r"HTTPError: (\d{3})",
        r"HTTP request failed with status (\d{3})",
    ],
    
    # Browser failures
    RobotFailureType.BROWSER_CRASH: [
        r"Chrome|Firefox|Safari|Edge .+? crashed",
        r"Browser process exited unexpectedly",
        r"target frame detached",
    ],
    RobotFailureType.DRIVER_ERROR: [
        r"WebDriverException:",
        r"SessionNotCreatedException:",
        r"Unable to create new service",
    ],
    
    # Resource failures
    RobotFailureType.RESOURCE_NOT_FOUND: [
        r"Resource file '(.+?)' does not exist",
        r"Resource import failed: (.+?) not found",
    ],
    
    # Setup/Teardown
    RobotFailureType.SETUP_FAILED: [
        r"Setup failed:",
        r"Suite setup failed:",
    ],
    RobotFailureType.TEARDOWN_FAILED: [
        r"Teardown failed:",
        r"Suite teardown failed:",
    ],
}

# Library name extraction patterns
LIBRARY_PATTERNS = [
    r"(\w+Library)\.(.+)",  # SeleniumLibrary.Click Element
    r"(\w+)\.(.+)",          # RequestsLibrary.Get Request
    r"BuiltIn\.(.+)",        # BuiltIn.Should Be Equal
]

# Locator strategy patterns
LOCATOR_STRATEGIES = {
    'id': r'id[=:](.+)',
    'xpath': r'xpath[=:](.+)',
    'css': r'css[=:](.+)',
    'name': r'name[=:](.+)',
    'link': r'link[=:](.+)',
    'partial link': r'partial link[=:](.+)',
    'tag': r'tag[=:](.+)',
    'class': r'class[=:](.+)',
}

# Intermittent failure indicators
INTERMITTENT_KEYWORDS = [
    'timeout', 'timed out', 'connection', 'network',
    'stale element', 'detached', 'crashed', 'refused',
]


def classify_robot_failure(
    error_message: str,
    stack_trace: str = "",
    test_name: Optional[str] = None,
    test_tags: Optional[List[str]] = None,
) -> RobotFailureClassification:
    """
    Classify a Robot Framework test failure.
    
    Args:
        error_message: The error message from Robot Framework
        stack_trace: Stack trace or test log excerpt
        test_name: Name of the failed test
        test_tags: Test tags (for context)
        
    Returns:
        RobotFailureClassification with detailed failure information
    """
    classification = RobotFailureClassification(
        failure_type=RobotFailureType.UNKNOWN,
        exception_type="RobotFrameworkError",
        error_message=error_message,
    )
    
    # Extract failure type
    failure_type = _detect_failure_type(error_message)
    classification.failure_type = failure_type
    
    # Extract keyword information
    keyword_info = _extract_keyword_info(error_message, stack_trace)
    classification.keyword_name = keyword_info.get('keyword')
    classification.library_name = keyword_info.get('library')
    
    # Extract locator information (for locator failures)
    if failure_type in [RobotFailureType.LOCATOR_NOT_FOUND, 
                       RobotFailureType.ELEMENT_NOT_VISIBLE,
                       RobotFailureType.ELEMENT_NOT_CLICKABLE]:
        locator_info = _extract_locator_info(error_message)
        classification.locator = locator_info.get('locator')
        classification.locator_strategy = locator_info.get('strategy')
    
    # Extract variable name (for variable failures)
    if failure_type in [RobotFailureType.VARIABLE_NOT_FOUND, RobotFailureType.VARIABLE_ERROR]:
        classification.variable_name = _extract_variable_name(error_message)
    
    # Extract timeout value
    timeout_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:seconds?|s|ms)', error_message, re.IGNORECASE)
    if timeout_match:
        classification.timeout_value = timeout_match.group(1)
    
    # Extract HTTP status
    http_match = re.search(r'(?:status|HTTP).*?(\d{3})', error_message, re.IGNORECASE)
    if http_match:
        classification.http_status = int(http_match.group(1))
    
    # Extract assertion type
    if failure_type == RobotFailureType.ASSERTION_FAILED:
        classification.assertion_type = _extract_assertion_type(error_message)
    
    # Detect test phase (setup, test, teardown)
    classification.test_phase = _detect_test_phase(error_message, stack_trace)
    
    # Parse stack trace
    classification.stack_trace = _parse_robot_stack_trace(stack_trace)
    
    # Determine location
    if classification.stack_trace:
        top_frame = classification.stack_trace[0]
        classification.location = FailureLocation(
            file_path=top_frame.file_path,
            line_number=top_frame.line_number,
            function_name=top_frame.function_name,
        )
    
    # Determine component type
    classification.component = _determine_component_type(
        classification.library_name,
        classification.keyword_name,
        stack_trace
    )
    
    # Detect intermittent failures
    classification.is_intermittent = _is_intermittent_failure(error_message, failure_type)
    
    # Calculate confidence
    classification.confidence = _calculate_confidence(
        failure_type,
        classification.keyword_name,
        classification.library_name
    )
    
    # Add metadata
    classification.metadata = {
        "test_name": test_name,
        "test_tags": test_tags or [],
        "has_library_info": classification.library_name is not None,
        "has_locator_info": classification.locator is not None,
    }
    
    return classification


def _detect_failure_type(error_message: str) -> RobotFailureType:
    """Detect failure type from error message."""
    error_lower = error_message.lower()
    
    for failure_type, patterns in FAILURE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return failure_type
    
    # Check for generic patterns
    if 'keyword' in error_lower and ('not found' in error_lower or "could not be found" in error_lower):
        return RobotFailureType.KEYWORD_NOT_FOUND
    if 'import' in error_lower and 'failed' in error_lower:
        return RobotFailureType.LIBRARY_IMPORT_FAILED
    if 'timeout' in error_lower:
        return RobotFailureType.TIMEOUT
    if 'assertion' in error_lower or 'should be' in error_lower or 'should contain' in error_lower:
        return RobotFailureType.ASSERTION_FAILED
    
    return RobotFailureType.UNKNOWN


def _extract_keyword_info(error_message: str, stack_trace: str) -> Dict[str, Optional[str]]:
    """Extract keyword and library information."""
    info = {'keyword': None, 'library': None}
    
    # Try to extract from library patterns (e.g., "SeleniumLibrary.Click Element")
    for pattern in LIBRARY_PATTERNS:
        match = re.search(pattern, error_message)
        if match:
            if len(match.groups()) >= 2:
                info['library'] = match.group(1)
                info['keyword'] = match.group(2)
            break
    
    # Try to extract from stack trace
    if not info['keyword']:
        # Look for keyword calls in stack trace
        keyword_match = re.search(r"Keyword:\s+(.+)", stack_trace, re.IGNORECASE)
        if keyword_match:
            info['keyword'] = keyword_match.group(1).strip()
    
    # Try to extract keyword from error messages like "No keyword with name 'X' found"
    if not info['keyword']:
        match = re.search(r"[Kk]eyword\s+['\"](.+?)['\"]", error_message)
        if match:
            info['keyword'] = match.group(1)
    
    return info


def _extract_locator_info(error_message: str) -> Dict[str, Optional[str]]:
    """Extract locator and strategy information."""
    info = {'locator': None, 'strategy': None}
    
    # Extract locator string
    locator_match = re.search(r"locator ['\"](.+?)['\"]", error_message, re.IGNORECASE)
    if not locator_match:
        locator_match = re.search(r"[Ee]lement ['\"](.+?)['\"]", error_message)
    if not locator_match:
        locator_match = re.search(r"Unable to locate element:\s*(.+?)(?:\n|$)", error_message)
    
    if locator_match:
        locator_str = locator_match.group(1)
        info['locator'] = locator_str
        
        # Detect strategy from locator string
        for strategy, pattern in LOCATOR_STRATEGIES.items():
            if re.match(pattern, locator_str, re.IGNORECASE):
                info['strategy'] = strategy
                break
        
        # If no strategy prefix, determine from locator format
        if not info['strategy']:
            if locator_str.startswith('//') or locator_str.startswith('(//'):
                info['strategy'] = 'xpath'
            elif ':' not in locator_str and locator_str[0] in ('#', '.'):
                info['strategy'] = 'css'
            elif locator_str.startswith('id='):
                info['strategy'] = 'id'
    
    return info


def _extract_variable_name(error_message: str) -> Optional[str]:
    """Extract variable name from error message."""
    match = re.search(r"\$\{(.+?)\}", error_message)
    return match.group(1) if match else None


def _extract_assertion_type(error_message: str) -> Optional[str]:
    """Extract assertion type (Should Be Equal, Should Contain, etc.)."""
    match = re.search(r"(Should (?:Be|Contain|Match|Start|End|Not)[\w\s]+):", error_message, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _detect_test_phase(error_message: str, stack_trace: str) -> str:
    """Detect which test phase failed (setup, test, teardown)."""
    combined = (error_message + " " + stack_trace).lower()
    
    if 'setup failed' in combined or 'suite setup' in combined:
        return 'setup'
    if 'teardown failed' in combined or 'suite teardown' in combined:
        return 'teardown'
    
    return 'test'


def _parse_robot_stack_trace(stack_trace: str) -> List[StackFrame]:
    """Parse Robot Framework stack trace."""
    frames = []
    
    # Robot stack traces typically show:
    # test_file.robot:25
    # SeleniumLibrary.Click Element
    lines = stack_trace.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Match pattern: file.robot:line
        file_match = re.match(r'(.+\.robot):(\d+)', line)
        if file_match:
            frames.append(StackFrame(
                file_path=file_match.group(1),
                line_number=int(file_match.group(2)),
                function_name="test",
                is_framework_code=False,
            ))
            continue
        
        # Match pattern: Library.Keyword
        keyword_match = re.match(r'(\w+(?:Library)?)\.(.+)', line)
        if keyword_match:
            frames.append(StackFrame(
                file_path="<library>",
                line_number=0,
                function_name=keyword_match.group(2),
                module_name=keyword_match.group(1),
                is_framework_code=True,
            ))
    
    return frames


def _determine_component_type(
    library_name: Optional[str],
    keyword_name: Optional[str],
    stack_trace: str
) -> ComponentType:
    """Determine component type based on failure context."""
    if library_name:
        if library_name.lower() == 'builtin':
            return ComponentType.FRAMEWORK
        if 'library' in library_name.lower():
            return ComponentType.LIBRARY
    
    # Check if failure is in a resource file
    if '.robot' in stack_trace and 'resource' in stack_trace.lower():
        return ComponentType.HELPER
    
    # Check if in test file
    if '.robot' in stack_trace:
        return ComponentType.TEST_CODE
    
    return ComponentType.UNKNOWN


def _is_intermittent_failure(error_message: str, failure_type: RobotFailureType) -> bool:
    """Detect if failure is likely intermittent."""
    error_lower = error_message.lower()
    
    # Timeout and network errors are often intermittent
    intermittent_types = [
        RobotFailureType.TIMEOUT,
        RobotFailureType.WAIT_UNTIL_TIMEOUT,
        RobotFailureType.PAGE_LOAD_TIMEOUT,
        RobotFailureType.NETWORK_ERROR,
        RobotFailureType.BROWSER_CRASH,
    ]
    
    if failure_type in intermittent_types:
        return True
    
    # Check for intermittent keywords in message
    return any(keyword in error_lower for keyword in INTERMITTENT_KEYWORDS)


def _calculate_confidence(
    failure_type: RobotFailureType,
    keyword_name: Optional[str],
    library_name: Optional[str]
) -> float:
    """Calculate confidence score for classification."""
    confidence = 0.5  # Base confidence
    
    # High confidence if we matched a specific pattern
    if failure_type != RobotFailureType.UNKNOWN:
        confidence += 0.3
    
    # Extra confidence if we have keyword/library info
    if keyword_name:
        confidence += 0.1
    if library_name:
        confidence += 0.1
    
    return min(confidence, 1.0)
