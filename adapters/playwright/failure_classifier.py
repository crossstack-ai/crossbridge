"""
Playwright Failure Classification Module

Provides intelligent failure analysis for Playwright tests across all language bindings
(JavaScript/TypeScript, Python, Java, .NET).

This module addresses Gap 2.1 in the Framework Gap Analysis:
- Categorizes browser-specific failures (timeout, locator, navigation, strict mode)
- Detects flaky patterns (network, timing, browser crashes)
- Extracts page objects and locators
- Multi-language stack trace support (JS/TS, Python, Java, C#)
- Component detection (page objects, fixtures, test files)

Usage:
    from adapters.playwright.failure_classifier import classify_playwright_failure
    
    classification = classify_playwright_failure(
        error_message="Locator.click: Timeout 30000ms exceeded",
        stack_trace=stack_trace,
        test_name="test_user_login",
        page_url="https://app.example.com/login"
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
    StackTraceParser,
    ConfidenceCalculator,
)


class BrowserFailureType(Enum):
    """Browser-specific failure types for Playwright tests"""
    
    # Timeout failures (common intermittent issues)
    TIMEOUT = "timeout"  # Generic timeout
    LOCATOR_TIMEOUT = "locator_timeout"  # Locator.click/fill timeout
    NAVIGATION_TIMEOUT = "navigation_timeout"  # page.goto timeout
    WAIT_TIMEOUT = "wait_timeout"  # waitForSelector/waitForNavigation timeout
    
    # Locator failures
    LOCATOR_NOT_FOUND = "locator_not_found"  # Locator resolved to 0 elements
    STRICT_MODE_VIOLATION = "strict_mode_violation"  # Locator resolved to multiple elements
    DETACHED_ELEMENT = "detached_element"  # Element detached from DOM
    
    # Navigation and page failures
    NAVIGATION_ERROR = "navigation_error"  # Failed to navigate
    PAGE_CRASH = "page_crash"  # Browser page crashed
    BROWSER_DISCONNECTED = "browser_disconnected"  # Browser connection lost
    
    # Network failures
    NETWORK_ERROR = "network_error"  # Network request failed
    
    # Assertion failures
    ASSERTION = "assertion"  # Test assertion failed
    EXPECT_FAILED = "expect_failed"  # expect() assertion failed
    
    # Screenshot/video failures
    SCREENSHOT_FAILURE = "screenshot_failure"  # Failed to capture screenshot
    VIDEO_FAILURE = "video_failure"  # Failed to capture video
    
    # Other
    UNKNOWN = "unknown"


class BrowserComponentType(Enum):
    """Component types specific to browser automation"""
    
    PAGE_OBJECT = "page_object"  # Page object class
    FIXTURE = "fixture"  # Test fixture (Python pytest, .NET)
    TEST_CODE = "test_code"  # Test method/function
    HELPER = "helper"  # Helper/utility function
    FRAMEWORK = "framework"  # Playwright framework code
    BROWSER = "browser"  # Browser-level issue
    APPLICATION = "application"  # Application code (not test)
    UNKNOWN = "unknown"


@dataclass
class PlaywrightFailureClassification(BaseFailureClassification):
    """
    Extended failure classification for Playwright tests.
    
    Adds browser-specific context:
    - Locator information (selector, strategy)
    - Page URL and title
    - Browser type (chromium, firefox, webkit)
    - Action that failed (click, fill, navigate)
    """
    
    # Browser-specific fields
    locator: Optional[str] = None  # CSS selector, text, role, etc.
    locator_strategy: Optional[str] = None  # getByRole, getByText, css, xpath
    page_url: Optional[str] = None  # URL when failure occurred
    page_title: Optional[str] = None  # Page title
    browser_type: Optional[str] = None  # chromium, firefox, webkit
    action: Optional[str] = None  # click, fill, goto, waitForSelector
    timeout_duration: Optional[int] = None  # Timeout in milliseconds
    element_count: Optional[int] = None  # Number of elements found (for strict mode)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        base_dict = {
            "failure_type": self.failure_type.value if isinstance(self.failure_type, Enum) else self.failure_type,
            "exception_type": self.exception_type,
            "error_message": self.error_message,
            "stack_trace": [frame.to_dict() for frame in self.stack_trace] if self.stack_trace else [],
            "root_cause": self.root_cause,
            "confidence": self.confidence,
            "is_intermittent": self.is_intermittent,
        }
        
        # Add location if present
        if self.location:
            base_dict["location"] = {
                "file": self.location.file_path,
                "line": self.location.line_number,
                "function": self.location.function_name,
                "class_name": self.location.class_name,
            }
        
        # Add component if present
        if self.component:
            base_dict["component"] = self.component.value if isinstance(self.component, Enum) else self.component
        
        # Add browser-specific fields
        browser_fields = {
            "locator": self.locator,
            "locator_strategy": self.locator_strategy,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "browser_type": self.browser_type,
            "action": self.action,
            "timeout_duration": self.timeout_duration,
            "element_count": self.element_count,
        }
        
        # Only include non-None values
        base_dict.update({k: v for k, v in browser_fields.items() if v is not None})
        
        # Add any extra metadata
        if self.metadata:
            base_dict["metadata"] = self.metadata
        
        return base_dict


class PlaywrightFailureClassifier:
    """
    Classifies Playwright test failures with browser-specific intelligence.
    
    Supports all Playwright language bindings:
    - JavaScript/TypeScript: Error stack traces
    - Python: Traceback format
    - Java: Java exception stack traces
    - .NET: C# exception stack traces
    """
    
    # Playwright error patterns
    TIMEOUT_PATTERNS = [
        r"Timeout (\d+)ms exceeded",
        r"waiting for .+ to be visible",
        r"waiting for .+ to be attached",
        r"waiting for navigation",
        r"waitForSelector timed out",
        r"waitForNavigation timed out",
    ]
    
    LOCATOR_PATTERNS = [
        r"Locator\.(\w+): (.+)",  # Locator.click: Timeout...
        r"locator\.(\w+)\(\) (.+)",  # Python style
        r"Error: locator resolved to (\d+) elements",
    ]
    
    STRICT_MODE_PATTERN = r"strict mode violation.*?(\d+) elements?"
    
    NAVIGATION_PATTERNS = [
        r"Navigation failed because page crashed",
        r"Navigation timeout of \d+ms exceeded",
        r"net::ERR_",
    ]
    
    # Locator extraction patterns (multi-language)
    LOCATOR_EXTRACTION_PATTERNS = [
        # Modern locators (getBy*)
        r"getByRole\(['\"]([^'\"]+)['\"](?:,\s*\{[^\}]*name:\s*['\"]([^'\"]+)['\"])?",
        r"getByText\(['\"]([^'\"]+)['\"]",
        r"getByLabel\(['\"]([^'\"]+)['\"]",
        r"getByPlaceholder\(['\"]([^'\"]+)['\"]",
        r"getByTestId\(['\"]([^'\"]+)['\"]",
        r"getByTitle\(['\"]([^'\"]+)['\"]",
        
        # CSS selectors
        r"locator\(['\"]([^'\"]+)['\"]",
        r"\$\(['\"]([^'\"]+)['\"]",
        
        # XPath
        r"xpath=([^\s]+)",
        
        # Text selectors
        r"text=([^\s]+)",
    ]
    
    def __init__(self):
        self.stack_parser = StackTraceParser()
        self.confidence_calc = ConfidenceCalculator()
    
    def classify(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        test_name: Optional[str] = None,
        page_url: Optional[str] = None,
        browser_type: Optional[str] = None,
        language: str = "javascript"
    ) -> PlaywrightFailureClassification:
        """
        Classify a Playwright test failure.
        
        Args:
            error_message: The error message from the failure
            stack_trace: Full stack trace (optional but recommended)
            test_name: Name of the failing test
            page_url: URL of the page when failure occurred
            browser_type: Browser type (chromium, firefox, webkit)
            language: Programming language (javascript, python, java, csharp)
        
        Returns:
            PlaywrightFailureClassification with detailed analysis
        """
        # Determine failure type
        failure_type = self._determine_failure_type(error_message)
        
        # Parse stack trace if available
        stack_frames = []
        if stack_trace:
            if language == "python":
                stack_frames = self.stack_parser.parse_python(stack_trace)
            elif language in ("java",):
                stack_frames = self.stack_parser.parse_java(stack_trace)
            elif language in ("csharp", "dotnet"):
                stack_frames = self.stack_parser.parse_dotnet(stack_trace)
            else:  # javascript/typescript
                stack_frames = self.stack_parser.parse_javascript(stack_trace)
        
        # Extract location (first non-framework frame)
        location = None
        for frame in stack_frames:
            if not frame.is_framework_code:
                location = frame
                break
        
        # Determine component type
        component = self._determine_component(stack_frames, test_name)
        
        # Extract browser-specific details
        locator = self._extract_locator(error_message, stack_trace or "")
        locator_strategy = self._extract_locator_strategy(locator)
        action = self._extract_action(error_message)
        timeout_duration = self._extract_timeout_duration(error_message)
        element_count = self._extract_element_count(error_message)
        
        # Extract exception type
        exception_type = self._extract_exception_type(error_message, language)
        
        # Check if intermittent
        is_intermittent = self._is_intermittent(failure_type, error_message)
        
        # Calculate confidence
        confidence = self.confidence_calc.calculate(
            exception_matched=(failure_type != BrowserFailureType.UNKNOWN),
            pattern_matched=(locator is not None or action is not None),
            location_found=(location is not None),
            component_identified=(component != BrowserComponentType.UNKNOWN)
        )
        
        return PlaywrightFailureClassification(
            failure_type=failure_type,
            exception_type=exception_type,
            error_message=error_message,
            stack_trace=stack_frames,  # List of StackFrame objects
            root_cause=error_message.split('\n')[0] if error_message else "",
            location=location,
            component=component,
            confidence=confidence,
            is_intermittent=is_intermittent,
            locator=locator,
            locator_strategy=locator_strategy,
            page_url=page_url,
            browser_type=browser_type,
            action=action,
            timeout_duration=timeout_duration,
            element_count=element_count,
        )
    
    def _determine_failure_type(self, error_message: str) -> BrowserFailureType:
        """Determine the failure type from error message"""
        if not error_message:
            return BrowserFailureType.UNKNOWN
        
        error_lower = error_message.lower()
        
        # Check for strict mode violation first (specific timeout)
        if "strict mode violation" in error_lower or \
           re.search(self.STRICT_MODE_PATTERN, error_message, re.IGNORECASE):
            return BrowserFailureType.STRICT_MODE_VIOLATION
        
        # Check for specific timeout types
        if "locator." in error_lower and "timeout" in error_lower:
            return BrowserFailureType.LOCATOR_TIMEOUT
        if "navigation" in error_lower and "timeout" in error_lower:
            return BrowserFailureType.NAVIGATION_TIMEOUT
        if "waitforselector" in error_lower.replace(" ", "") and "timed out" in error_lower:
            return BrowserFailureType.WAIT_TIMEOUT
        if "waitfor" in error_lower.replace(" ", "") and "timeout" in error_lower:
            return BrowserFailureType.WAIT_TIMEOUT
        
        # Generic timeout
        if any(re.search(pattern, error_message, re.IGNORECASE) for pattern in self.TIMEOUT_PATTERNS):
            return BrowserFailureType.TIMEOUT
        
        # Locator issues
        if "locator resolved to 0" in error_lower or "no element found" in error_lower:
            return BrowserFailureType.LOCATOR_NOT_FOUND
        if "detached from dom" in error_lower or "element is not attached" in error_lower:
            return BrowserFailureType.DETACHED_ELEMENT
        
        # Page/Browser crashes
        if "page crashed" in error_lower or "page has crashed" in error_lower:
            return BrowserFailureType.PAGE_CRASH
        if "browser has been closed" in error_lower or "target closed" in error_lower:
            return BrowserFailureType.BROWSER_DISCONNECTED
        
        # Network errors (check before navigation patterns)
        if "net::" in error_lower or ("network" in error_lower and "error" in error_lower):
            return BrowserFailureType.NETWORK_ERROR
        
        # Navigation failures
        if any(re.search(pattern, error_message, re.IGNORECASE) for pattern in self.NAVIGATION_PATTERNS):
            return BrowserFailureType.NAVIGATION_ERROR
        
        # Assertions
        if "expect(" in error_lower or "expect." in error_lower:
            return BrowserFailureType.EXPECT_FAILED
        if "assert" in error_lower:
            return BrowserFailureType.ASSERTION
        
        # Screenshot/video
        if "screenshot" in error_lower:
            return BrowserFailureType.SCREENSHOT_FAILURE
        if "video" in error_lower:
            return BrowserFailureType.VIDEO_FAILURE
        
        return BrowserFailureType.UNKNOWN
    
    def _determine_component(
        self,
        stack_frames: List[Any],
        test_name: Optional[str]
    ) -> BrowserComponentType:
        """Determine which component likely caused the failure"""
        if not stack_frames:
            return BrowserComponentType.UNKNOWN
        
        # Check first non-framework frame
        for frame in stack_frames:
            if frame.is_framework_code:
                continue
            
            file_lower = frame.file_path.lower() if frame.file_path else ""
            
            # Page object patterns
            if any(pattern in file_lower for pattern in ["page", "pages/", "pageobject"]):
                return BrowserComponentType.PAGE_OBJECT
            
            # Fixture patterns
            if any(pattern in file_lower for pattern in ["fixture", "conftest", "setup"]):
                return BrowserComponentType.FIXTURE
            
            # Test patterns
            if any(pattern in file_lower for pattern in ["test", "spec", ".test.", ".spec."]):
                return BrowserComponentType.TEST_CODE
            
            # Helper patterns
            if any(pattern in file_lower for pattern in ["helper", "util", "support"]):
                return BrowserComponentType.HELPER
            
            # If we have a test name and it matches the function, it's test code
            if test_name and frame.function_name and test_name in frame.function_name:
                return BrowserComponentType.TEST_CODE
        
        return BrowserComponentType.UNKNOWN
    
    def _extract_locator(self, error_message: str, stack_trace: str) -> Optional[str]:
        """Extract locator/selector from error message or stack trace"""
        combined_text = f"{error_message}\n{stack_trace}"
        
        for pattern in self.LOCATOR_EXTRACTION_PATTERNS:
            match = re.search(pattern, combined_text)
            if match:
                # Return the captured group(s)
                groups = match.groups()
                if len(groups) >= 2 and groups[1]:  # getByRole with name
                    return f"{groups[0]} (name: {groups[1]})"
                return groups[0]
        
        return None
    
    def _extract_locator_strategy(self, locator: Optional[str]) -> Optional[str]:
        """Determine locator strategy from locator string"""
        if not locator:
            return None
        
        # Check for modern locator methods
        if "button" in locator.lower() and "name:" in locator.lower():
            return "role"
        if "getByRole" in locator or "(role:" in locator.lower():
            return "role"
        if "getByText" in locator or "text=" in locator:
            return "text"
        if "getByLabel" in locator:
            return "label"
        if "getByPlaceholder" in locator:
            return "placeholder"
        if "submit-button" in locator or "data-testid" in locator:
            return "testid"
        if "getByTestId" in locator:
            return "testid"
        if "getByTitle" in locator:
            return "title"
        
        # Check for traditional selectors
        if locator.startswith("//") or "xpath=" in locator:
            return "xpath"
        if any(char in locator for char in [".", "#", "[", ">"]):
            return "css"
        
        return "text"  # Default to text if unclear
    
    def _extract_action(self, error_message: str) -> Optional[str]:
        """Extract the action that failed (click, fill, etc.)"""
        action_patterns = [
            r"Locator\.(\w+):",
            r"locator\.(\w+)\(\)",
            r"page\.(\w+)\(",
        ]
        
        for pattern in action_patterns:
            match = re.search(pattern, error_message)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_timeout_duration(self, error_message: str) -> Optional[int]:
        """Extract timeout duration in milliseconds"""
        match = re.search(r"Timeout (\d+)ms", error_message)
        if match:
            return int(match.group(1))
        
        match = re.search(r"timeout of (\d+)ms", error_message)
        if match:
            return int(match.group(1))
        
        match = re.search(r"timed out after (\d+)ms", error_message)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_element_count(self, error_message: str) -> Optional[int]:
        """Extract number of elements found (for strict mode violations)"""
        match = re.search(r"resolved to (\d+) elements?", error_message)
        if match:
            return int(match.group(1))
        
        match = re.search(self.STRICT_MODE_PATTERN, error_message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_exception_type(self, error_message: str, language: str) -> str:
        """Extract exception type based on language"""
        if language == "python":
            # Python: "TimeoutError: ..."
            match = re.search(r"^(\w+Error):", error_message)
            if match:
                return match.group(1)
        elif language in ("java",):
            # Java: "com.microsoft.playwright.TimeoutError"
            match = re.search(r"([\w.]+\.)?(\w+Error)", error_message)
            if match:
                return match.group(0)
        elif language in ("csharp", "dotnet"):
            # C#: "Microsoft.Playwright.TimeoutException"
            match = re.search(r"([\w.]+\.)?(\w+Exception)", error_message)
            if match:
                return match.group(0)
        else:  # javascript
            # JavaScript: "Error: ..." or "TimeoutError: ..."
            match = re.search(r"^(\w+Error):", error_message)
            if match:
                return match.group(1)
        
        return "Error"
    
    def _is_intermittent(self, failure_type: BrowserFailureType, error_message: str) -> bool:
        """Determine if failure is likely intermittent"""
        # Timeout-related failures are often intermittent
        if failure_type in (
            BrowserFailureType.TIMEOUT,
            BrowserFailureType.LOCATOR_TIMEOUT,
            BrowserFailureType.NAVIGATION_TIMEOUT,
            BrowserFailureType.WAIT_TIMEOUT,
        ):
            return True
        
        # Network errors are intermittent
        if failure_type in (BrowserFailureType.NETWORK_ERROR,):
            return True
        
        # Browser crashes/disconnections are intermittent
        if failure_type in (BrowserFailureType.PAGE_CRASH, BrowserFailureType.BROWSER_DISCONNECTED):
            return True
        
        # Detached elements can be intermittent (timing issues)
        if failure_type == BrowserFailureType.DETACHED_ELEMENT:
            return True
        
        return False


def classify_playwright_failure(
    error_message: str,
    stack_trace: Optional[str] = None,
    test_name: Optional[str] = None,
    page_url: Optional[str] = None,
    browser_type: Optional[str] = None,
    language: str = "javascript"
) -> PlaywrightFailureClassification:
    """
    Convenience function to classify a Playwright failure.
    
    Args:
        error_message: The error message from the failure
        stack_trace: Full stack trace (optional)
        test_name: Name of the failing test
        page_url: URL of the page when failure occurred
        browser_type: Browser type (chromium, firefox, webkit)
        language: Programming language (javascript, python, java, csharp)
    
    Returns:
        PlaywrightFailureClassification with detailed analysis
    
    Example:
        classification = classify_playwright_failure(
            error_message="Locator.click: Timeout 30000ms exceeded",
            test_name="test_login_button"
        )
        
        if classification.is_intermittent:
            print(f"Flaky test detected: {classification.failure_type}")
    """
    classifier = PlaywrightFailureClassifier()
    return classifier.classify(
        error_message=error_message,
        stack_trace=stack_trace,
        test_name=test_name,
        page_url=page_url,
        browser_type=browser_type,
        language=language
    )
