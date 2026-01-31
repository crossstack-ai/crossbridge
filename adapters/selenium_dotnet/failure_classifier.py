"""
Selenium .NET Failure Classification Module.

Provides intelligent failure analysis for Selenium .NET tests to enable
root cause analysis, failure grouping, and flaky test detection.

This module addresses Gap 5.2 in the Framework Gap Analysis:
- Categorizes WebDriver failures (timeout, locator, stale element, etc.)
- Detects intermittent failures
- Maps .NET exceptions (WebDriverException, NoSuchElementException, etc.)
- Parses C# stack traces
- Extracts Page Objects and test components

Usage:
    from adapters.selenium_dotnet.failure_classifier import classify_selenium_dotnet_failure
    
    classification = classify_selenium_dotnet_failure(
        error_message="OpenQA.Selenium.NoSuchElementException: no such element",
        stack_trace=stack_trace,
        test_name="TestUserLogin"
    )
    
    print(f"Type: {classification.failure_type}")
    print(f"Locator: {classification.locator}")
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


class SeleniumDotNetFailureType(Enum):
    """Selenium .NET-specific failure types."""
    # Locator/Element failures
    NO_SUCH_ELEMENT = "no_such_element"           # Element not found
    STALE_ELEMENT = "stale_element"               # Element reference stale
    ELEMENT_NOT_VISIBLE = "element_not_visible"   # Element not visible
    ELEMENT_NOT_INTERACTABLE = "element_not_interactable"  # Element not clickable/interactable
    INVALID_SELECTOR = "invalid_selector"         # Invalid CSS/XPath selector
    
    # Timeout failures
    TIMEOUT = "timeout"                           # Generic timeout
    ELEMENT_TIMEOUT = "element_timeout"           # Wait for element timeout
    PAGE_LOAD_TIMEOUT = "page_load_timeout"       # Page load timeout
    SCRIPT_TIMEOUT = "script_timeout"             # JavaScript execution timeout
    
    # Navigation failures
    NAVIGATION_ERROR = "navigation_error"         # Navigation failed
    INVALID_URL = "invalid_url"                   # Invalid URL
    
    # Window/Frame failures
    NO_SUCH_WINDOW = "no_such_window"            # Window/tab not found
    NO_SUCH_FRAME = "no_such_frame"              # Frame not found
    NO_ALERT = "no_alert"                        # No alert present
    
    # Driver/Session failures
    SESSION_NOT_CREATED = "session_not_created"   # Failed to create WebDriver session
    INVALID_SESSION = "invalid_session"           # WebDriver session invalid
    DRIVER_ERROR = "driver_error"                 # WebDriver/ChromeDriver error
    BROWSER_CRASH = "browser_crash"               # Browser crashed
    
    # Network failures
    NETWORK_ERROR = "network_error"               # Network connection error
    
    # Assertion failures
    ASSERTION = "assertion"                       # Test assertion failed
    
    # JavaScript failures
    JAVASCRIPT_ERROR = "javascript_error"         # JavaScript execution error
    
    # Other
    UNKNOWN = "unknown"


@dataclass
class SeleniumDotNetFailureClassification(BaseFailureClassification):
    """Selenium .NET-specific failure classification."""
    failure_type: SeleniumDotNetFailureType = SeleniumDotNetFailureType.UNKNOWN
    locator: Optional[str] = None                  # Selector/locator string
    locator_strategy: Optional[str] = None         # By.Id, By.XPath, By.CssSelector, etc.
    page_object: Optional[str] = None              # Page Object class name
    element_name: Optional[str] = None             # Element/property name
    browser_name: Optional[str] = None             # Chrome, Firefox, Edge, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "locator": self.locator,
            "locator_strategy": self.locator_strategy,
            "page_object": self.page_object,
            "element_name": self.element_name,
            "browser_name": self.browser_name,
        })
        return base_dict


# .NET Exception type mapping
EXCEPTION_TYPE_MAP = {
    "NoSuchElementException": SeleniumDotNetFailureType.NO_SUCH_ELEMENT,
    "StaleElementReferenceException": SeleniumDotNetFailureType.STALE_ELEMENT,
    "ElementNotVisibleException": SeleniumDotNetFailureType.ELEMENT_NOT_VISIBLE,
    "ElementNotInteractableException": SeleniumDotNetFailureType.ELEMENT_NOT_INTERACTABLE,
    "InvalidSelectorException": SeleniumDotNetFailureType.INVALID_SELECTOR,
    "TimeoutException": SeleniumDotNetFailureType.TIMEOUT,
    "WebDriverTimeoutException": SeleniumDotNetFailureType.TIMEOUT,
    "NoSuchWindowException": SeleniumDotNetFailureType.NO_SUCH_WINDOW,
    "NoSuchFrameException": SeleniumDotNetFailureType.NO_SUCH_FRAME,
    "NoAlertPresentException": SeleniumDotNetFailureType.NO_ALERT,
    "SessionNotCreatedException": SeleniumDotNetFailureType.SESSION_NOT_CREATED,
    "InvalidSessionIdException": SeleniumDotNetFailureType.INVALID_SESSION,
    "WebDriverException": SeleniumDotNetFailureType.DRIVER_ERROR,
    "JavaScriptException": SeleniumDotNetFailureType.JAVASCRIPT_ERROR,
}

# Error message patterns for failure classification
FAILURE_PATTERNS = {
    SeleniumDotNetFailureType.NO_SUCH_ELEMENT: [
        r"no such element",
        r"Unable to locate element",
        r"element could not be found",
        r"Cannot find element",
    ],
    SeleniumDotNetFailureType.STALE_ELEMENT: [
        r"stale element reference",
        r"element is no longer attached to the DOM",
        r"element reference is stale",
    ],
    SeleniumDotNetFailureType.ELEMENT_NOT_VISIBLE: [
        r"element not visible",
        r"element is not currently visible",
        r"element not displayed",
    ],
    SeleniumDotNetFailureType.ELEMENT_NOT_INTERACTABLE: [
        r"element not interactable",
        r"element click intercepted",
        r"element is not clickable",
        r"not clickable at point",
    ],
    SeleniumDotNetFailureType.TIMEOUT: [
        r"timeout",
        r"timed out",
        r"exceeded",
        r"after \d+ seconds",
    ],
    SeleniumDotNetFailureType.BROWSER_CRASH: [
        r"chrome not reachable",
        r"session deleted because of page crash",
        r"target frame detached",
        r"renderer.*?crashed",
    ],
    SeleniumDotNetFailureType.NETWORK_ERROR: [
        r"connection refused",
        r"could not connect to remote server",
        r"network.*?error",
    ],
}

# Locator strategy patterns (C#)
LOCATOR_STRATEGY_PATTERNS = {
    'Id': r'By\.Id\("([^"]+)"\)',
    'XPath': r'By\.XPath\("([^"]+)"\)',
    'CssSelector': r'By\.CssSelector\("([^"]+)"\)',
    'Name': r'By\.Name\("([^"]+)"\)',
    'ClassName': r'By\.ClassName\("([^"]+)"\)',
    'TagName': r'By\.TagName\("([^"]+)"\)',
    'LinkText': r'By\.LinkText\("([^"]+)"\)',
    'PartialLinkText': r'By\.PartialLinkText\("([^"]+)"\)',
}

# Intermittent failure indicators
INTERMITTENT_KEYWORDS = [
    'timeout', 'timed out', 'stale', 'connection',
    'network', 'crashed', 'detached', 'intercepted'
]


def classify_selenium_dotnet_failure(
    error_message: str,
    stack_trace: str = "",
    test_name: Optional[str] = None,
    exception_type: Optional[str] = None,
) -> SeleniumDotNetFailureClassification:
    """
    Classify a Selenium .NET test failure.
    
    Args:
        error_message: The error message from the test
        stack_trace: C# stack trace
        test_name: Name of the failed test
        exception_type: .NET exception type (e.g., "NoSuchElementException")
        
    Returns:
        SeleniumDotNetFailureClassification with detailed failure information
    """
    classification = SeleniumDotNetFailureClassification(
        failure_type=SeleniumDotNetFailureType.UNKNOWN,
        exception_type=exception_type or "Exception",
        error_message=error_message,
    )
    
    # Extract exception type from error message if not provided
    if not exception_type:
        exception_type = _extract_exception_type(error_message)
        classification.exception_type = exception_type
    
    # Map exception type to failure type
    for exc_name, failure_type in EXCEPTION_TYPE_MAP.items():
        if exc_name in exception_type:
            classification.failure_type = failure_type
            break
    
    # If not mapped by exception, try pattern matching on error message
    if classification.failure_type == SeleniumDotNetFailureType.UNKNOWN:
        classification.failure_type = _detect_failure_type_from_message(error_message)
    
    # Extract locator information
    locator_info = _extract_locator_info(error_message, stack_trace)
    classification.locator = locator_info.get('locator')
    classification.locator_strategy = locator_info.get('strategy')
    
    # Extract page object information
    page_object_info = _extract_page_object_info(stack_trace)
    classification.page_object = page_object_info.get('page_object')
    classification.element_name = page_object_info.get('element')
    
    # Extract browser name
    classification.browser_name = _extract_browser_name(error_message, stack_trace)
    
    # Parse stack trace
    classification.stack_trace = _parse_csharp_stack_trace(stack_trace)
    
    # Determine location
    if classification.stack_trace:
        top_frame = classification.stack_trace[0]
        classification.location = FailureLocation(
            file_path=top_frame.file_path,
            line_number=top_frame.line_number,
            function_name=top_frame.function_name,
            class_name=top_frame.class_name,
        )
    
    # Determine component type
    classification.component = _determine_component_type(
        classification.page_object,
        classification.stack_trace
    )
    
    # Detect intermittent failures
    classification.is_intermittent = _is_intermittent_failure(
        error_message,
        classification.failure_type
    )
    
    # Calculate confidence
    classification.confidence = _calculate_confidence(
        classification.failure_type,
        classification.locator,
        classification.page_object
    )
    
    # Add metadata
    classification.metadata = {
        "test_name": test_name,
        "has_locator": classification.locator is not None,
        "has_page_object": classification.page_object is not None,
    }
    
    return classification


def _extract_exception_type(error_message: str) -> str:
    """Extract .NET exception type from error message."""
    # Look for OpenQA.Selenium.ExceptionType or just ExceptionType
    match = re.search(r'(?:OpenQA\.Selenium\.)?(\w+Exception)', error_message)
    if match:
        return match.group(1)
    
    # Look for assertion exceptions
    if "Assert." in error_message or "NUnit.Framework" in error_message:
        return "AssertionException"
    
    return "Exception"


def _detect_failure_type_from_message(error_message: str) -> SeleniumDotNetFailureType:
    """Detect failure type from error message patterns."""
    error_lower = error_message.lower()
    
    for failure_type, patterns in FAILURE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, error_lower):
                return failure_type
    
    # Check for assertion
    if any(word in error_lower for word in ['assert', 'expected', 'actual']):
        return SeleniumDotNetFailureType.ASSERTION
    
    return SeleniumDotNetFailureType.UNKNOWN


def _extract_locator_info(error_message: str, stack_trace: str) -> Dict[str, Optional[str]]:
    """Extract locator and strategy information."""
    info = {'locator': None, 'strategy': None}
    combined = error_message + "\n" + stack_trace
    
    # Try to extract from By.Strategy patterns in stack trace
    for strategy, pattern in LOCATOR_STRATEGY_PATTERNS.items():
        match = re.search(pattern, combined)
        if match:
            info['strategy'] = strategy
            info['locator'] = match.group(1)
            return info
    
    # Try to extract from error message
    # Pattern: "Using: id, value: username"
    using_match = re.search(r'Using:\s*(\w+),\s*value:\s*(.+?)(?:\n|$)', error_message, re.IGNORECASE)
    if using_match:
        strategy_map = {
            'id': 'Id',
            'xpath': 'XPath',
            'css selector': 'CssSelector',
            'name': 'Name',
            'class name': 'ClassName',
            'tag name': 'TagName',
            'link text': 'LinkText',
        }
        strategy = using_match.group(1).lower()
        info['strategy'] = strategy_map.get(strategy, strategy)
        info['locator'] = using_match.group(2).strip()
    
    # Try generic selector extraction
    if not info['locator']:
        # Look for quoted selectors
        selector_match = re.search(r'selector[:\s]+["\']([^"\']+)["\']', error_message, re.IGNORECASE)
        if selector_match:
            info['locator'] = selector_match.group(1)
            # Guess strategy from selector format
            if info['locator'].startswith('//') or info['locator'].startswith('(//'):
                info['strategy'] = 'XPath'
            elif info['locator'].startswith('#') or info['locator'].startswith('.'):
                info['strategy'] = 'CssSelector'
    
    return info


def _extract_page_object_info(stack_trace: str) -> Dict[str, Optional[str]]:
    """Extract Page Object class and element information from stack trace."""
    info = {'page_object': None, 'element': None}
    
    # Look for common Page Object patterns
    # Example: at MyProject.Pages.LoginPage.UsernameField.get()
    page_patterns = [
        r'at\s+[\w.]+\.Pages\.(\w+)\.(\w+)',
        r'at\s+[\w.]+\.PageObjects\.(\w+)\.(\w+)',
        r'at\s+[\w.]+\.(\w+Page)\.(\w+)',
    ]
    
    for pattern in page_patterns:
        match = re.search(pattern, stack_trace)
        if match:
            info['page_object'] = match.group(1)
            info['element'] = match.group(2)
            break
    
    return info


def _extract_browser_name(error_message: str, stack_trace: str) -> Optional[str]:
    """Extract browser name from error message or stack trace."""
    combined = (error_message + " " + stack_trace).lower()
    
    browsers = ['chrome', 'firefox', 'edge', 'safari', 'internetexplorer', 'ie']
    
    for browser in browsers:
        if browser in combined:
            return browser.title() if browser != 'ie' else 'InternetExplorer'
    
    return None


def _parse_csharp_stack_trace(stack_trace: str) -> List[StackFrame]:
    """Parse C# stack trace into StackFrame objects."""
    frames = []
    
    # C# stack trace format:
    # at Namespace.Class.Method() in C:\path\file.cs:line 42
    lines = stack_trace.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line.startswith('at '):
            continue
        
        # Extract method info
        match = re.match(r'at\s+([\w.]+)\.(\w+)\([^)]*\)', line)
        if not match:
            continue
        
        full_path = match.group(1)
        method_name = match.group(2)
        
        # Split into namespace and class
        path_parts = full_path.split('.')
        class_name = path_parts[-1] if path_parts else None
        module_name = '.'.join(path_parts[:-1]) if len(path_parts) > 1 else None
        
        # Extract file and line number
        file_match = re.search(r'in\s+(.+?):line\s+(\d+)', line)
        if file_match:
            file_path = file_match.group(1)
            line_number = int(file_match.group(2))
        else:
            file_path = "<unknown>"
            line_number = 0
        
        # Determine if framework code
        is_framework = any(fw in full_path for fw in [
            'OpenQA.Selenium', 'NUnit', 'MSTest', 'Xunit', 'System.', 'Microsoft.'
        ])
        
        frames.append(StackFrame(
            file_path=file_path,
            line_number=line_number,
            function_name=method_name,
            class_name=class_name,
            module_name=module_name,
            is_framework_code=is_framework,
        ))
    
    return frames


def _determine_component_type(
    page_object: Optional[str],
    stack_trace: List[StackFrame]
) -> ComponentType:
    """Determine component type based on failure context."""
    if page_object:
        return ComponentType.PAGE_OBJECT
    
    # Check stack trace for component indicators
    for frame in stack_trace:
        if frame.is_framework_code:
            continue
        
        if frame.module_name:
            module_lower = frame.module_name.lower()
            if 'page' in module_lower:
                return ComponentType.PAGE_OBJECT
            if 'helper' in module_lower or 'util' in module_lower:
                return ComponentType.HELPER
            if 'test' in module_lower:
                return ComponentType.TEST_CODE
    
    return ComponentType.UNKNOWN


def _is_intermittent_failure(
    error_message: str,
    failure_type: SeleniumDotNetFailureType
) -> bool:
    """Detect if failure is likely intermittent."""
    error_lower = error_message.lower()
    
    # These failure types are often intermittent
    intermittent_types = [
        SeleniumDotNetFailureType.TIMEOUT,
        SeleniumDotNetFailureType.ELEMENT_TIMEOUT,
        SeleniumDotNetFailureType.STALE_ELEMENT,
        SeleniumDotNetFailureType.ELEMENT_NOT_INTERACTABLE,
        SeleniumDotNetFailureType.NETWORK_ERROR,
        SeleniumDotNetFailureType.BROWSER_CRASH,
    ]
    
    if failure_type in intermittent_types:
        return True
    
    # Check for intermittent keywords
    return any(keyword in error_lower for keyword in INTERMITTENT_KEYWORDS)


def _calculate_confidence(
    failure_type: SeleniumDotNetFailureType,
    locator: Optional[str],
    page_object: Optional[str]
) -> float:
    """Calculate confidence score for classification."""
    confidence = 0.5  # Base confidence
    
    # High confidence if we identified a specific failure type
    if failure_type != SeleniumDotNetFailureType.UNKNOWN:
        confidence += 0.3
    
    # Extra confidence if we have locator info
    if locator:
        confidence += 0.1
    
    # Extra confidence if we have page object info
    if page_object:
        confidence += 0.1
    
    return min(confidence, 1.0)
