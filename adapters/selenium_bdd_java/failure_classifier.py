"""
Selenium Java BDD - Failure Classification System

Provides structured failure analysis for Cucumber test results:
- Categorizes failures by type (timeout, assertion, locator, etc.)
- Parses Java stack traces
- Extracts failure location and component
- Supports intelligent failure grouping and analysis
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple


class FailureType(Enum):
    """Categorizes test failures by root cause."""
    
    # Selenium-specific failures
    TIMEOUT = "timeout"                    # WebDriverWait, implicit/explicit waits
    LOCATOR_NOT_FOUND = "locator_not_found"  # NoSuchElementException
    STALE_ELEMENT = "stale_element"        # StaleElementReferenceException
    ELEMENT_NOT_VISIBLE = "element_not_visible"  # ElementNotVisibleException
    ELEMENT_NOT_INTERACTABLE = "element_not_interactable"  # ElementNotInteractableException
    
    # Assertion failures
    ASSERTION = "assertion"                # Assert.*, assertThat, assertEquals
    VERIFICATION = "verification"          # Soft assertions, verifications
    
    # Network/Browser failures
    NETWORK_ERROR = "network_error"        # Connection errors, 404, 500
    BROWSER_ERROR = "browser_error"        # Browser crash, driver issues
    PAGE_LOAD_TIMEOUT = "page_load_timeout"  # Page load timing out
    
    # Code/Logic failures
    NULL_POINTER = "null_pointer"          # NullPointerException
    JAVASCRIPT_ERROR = "javascript_error"  # JS execution errors
    UNEXPECTED_ALERT = "unexpected_alert"  # UnhandledAlertException
    
    # Test infrastructure
    SETUP_FAILURE = "setup_failure"        # @Before, @BeforeClass failures
    TEARDOWN_FAILURE = "teardown_failure"  # @After, @AfterClass failures
    CONFIGURATION_ERROR = "configuration_error"  # Config/environment issues
    
    # Generic/Unknown
    UNKNOWN = "unknown"                    # Cannot determine type


class FailureComponent(Enum):
    """Identifies which component failed."""
    
    PAGE_OBJECT = "page_object"    # Failure in page object method
    STEP_DEFINITION = "step_definition"  # Failure in step implementation
    TEST_FIXTURE = "test_fixture"  # @Before/@After hooks
    ASSERTION_LIBRARY = "assertion_library"  # Assert.*, Hamcrest
    WEBDRIVER = "webdriver"        # Selenium WebDriver calls
    APPLICATION = "application"    # Application under test
    UNKNOWN = "unknown"


@dataclass
class FailureLocation:
    """Precise location of failure in code."""
    
    file_path: str = ""
    line_number: int = 0
    class_name: str = ""
    method_name: str = ""
    package: str = ""
    
    @property
    def fully_qualified_method(self) -> str:
        """Returns fully qualified method name."""
        if self.package and self.class_name and self.method_name:
            return f"{self.package}.{self.class_name}.{self.method_name}"
        elif self.class_name and self.method_name:
            return f"{self.class_name}.{self.method_name}"
        return self.method_name or ""


@dataclass
class StackTraceFrame:
    """Represents a single stack trace frame."""
    
    class_name: str
    method_name: str
    file_name: str = ""
    line_number: int = 0
    is_native: bool = False
    
    def __str__(self) -> str:
        if self.is_native:
            return f"{self.class_name}.{self.method_name}(Native Method)"
        elif self.file_name and self.line_number:
            return f"{self.class_name}.{self.method_name}({self.file_name}:{self.line_number})"
        return f"{self.class_name}.{self.method_name}(Unknown Source)"


@dataclass
class FailureClassification:
    """Complete classification of a test failure."""
    
    # Basic failure info
    failure_type: FailureType
    exception_type: str  # e.g., "NoSuchElementException"
    error_message: str
    
    # Parsed stack trace
    stack_trace: List[StackTraceFrame] = field(default_factory=list)
    root_cause: Optional[str] = None  # For nested exceptions
    
    # Failure location
    location: Optional[FailureLocation] = None
    component: FailureComponent = FailureComponent.UNKNOWN
    
    # Contextual info
    locator: Optional[str] = None  # For locator-related failures
    timeout_duration: Optional[float] = None  # For timeout failures
    http_status: Optional[int] = None  # For network failures
    
    # Confidence scoring
    confidence: float = 1.0  # 0.0-1.0, how confident we are in classification
    
    # Additional metadata
    metadata: Dict[str, str] = field(default_factory=dict)
    
    @property
    def is_intermittent(self) -> bool:
        """Indicates if failure type is typically intermittent/flaky."""
        flaky_types = {
            FailureType.TIMEOUT,
            FailureType.STALE_ELEMENT,
            FailureType.NETWORK_ERROR,
            FailureType.PAGE_LOAD_TIMEOUT,
            FailureType.ELEMENT_NOT_VISIBLE,
        }
        return self.failure_type in flaky_types
    
    @property
    def summary(self) -> str:
        """One-line failure summary."""
        parts = [
            f"{self.failure_type.value}",
            f"{self.exception_type}" if self.exception_type else "",
            f"in {self.component.value}" if self.component != FailureComponent.UNKNOWN else "",
        ]
        return " - ".join(filter(None, parts))


class FailureClassifier:
    """
    Analyzes and classifies test failures from Java stack traces.
    
    Provides structured failure information for intelligent analysis,
    grouping, and flaky test detection.
    """
    
    # Exception type to FailureType mapping
    EXCEPTION_MAPPINGS = {
        # Selenium exceptions
        "NoSuchElementException": FailureType.LOCATOR_NOT_FOUND,
        "ElementNotFoundException": FailureType.LOCATOR_NOT_FOUND,
        "StaleElementReferenceException": FailureType.STALE_ELEMENT,
        "ElementNotVisibleException": FailureType.ELEMENT_NOT_VISIBLE,
        "ElementNotInteractableException": FailureType.ELEMENT_NOT_INTERACTABLE,
        "TimeoutException": FailureType.TIMEOUT,
        "WebDriverException": FailureType.BROWSER_ERROR,
        "UnhandledAlertException": FailureType.UNEXPECTED_ALERT,
        
        # Network/HTTP
        "HttpException": FailureType.NETWORK_ERROR,
        "ConnectException": FailureType.NETWORK_ERROR,
        "SocketTimeoutException": FailureType.NETWORK_ERROR,
        
        # Assertions
        "AssertionError": FailureType.ASSERTION,
        "ComparisonFailure": FailureType.ASSERTION,
        "AssertionFailedError": FailureType.ASSERTION,
        
        # Java common
        "NullPointerException": FailureType.NULL_POINTER,
        "IllegalStateException": FailureType.CONFIGURATION_ERROR,
        "IllegalArgumentException": FailureType.CONFIGURATION_ERROR,
    }
    
    # Stack trace parsing patterns
    STACK_FRAME_PATTERN = re.compile(
        r'at\s+([\w.$]+)\.([\w<>]+)\(([^:)]+)(?::(\d+))?\)'
    )
    
    NATIVE_METHOD_PATTERN = re.compile(
        r'at\s+([\w.$]+)\.([\w<>]+)\(Native Method\)'
    )
    
    LOCATOR_PATTERN = re.compile(
        r'By\.(\w+):\s*([^\s]+)|locator:\s*([^\s]+)'
    )
    
    TIMEOUT_PATTERN = re.compile(
        r'timeout.*?(\d+(?:\.\d+)?)\s*(second|ms|millisecond)',
        re.IGNORECASE
    )
    
    HTTP_STATUS_PATTERN = re.compile(r'HTTP\s*(\d{3})|status\s*code\s*(\d{3})')
    
    def classify(self, error_message: Optional[str], step_name: str = "") -> FailureClassification:
        """
        Classify a test failure from error message.
        
        Args:
            error_message: Full error message with stack trace
            step_name: Name of failed step (for context)
            
        Returns:
            FailureClassification with structured failure info
        """
        if not error_message:
            return FailureClassification(
                failure_type=FailureType.UNKNOWN,
                exception_type="",
                error_message="",
                confidence=0.0
            )
        
        # Extract exception type
        exception_type = self._extract_exception_type(error_message)
        
        # Determine failure type
        failure_type = self._determine_failure_type(exception_type, error_message)
        
        # Parse stack trace
        stack_trace = self._parse_stack_trace(error_message)
        
        # Extract failure location
        location = self._extract_location(stack_trace)
        
        # Determine component
        component = self._determine_component(stack_trace, step_name)
        
        # Extract contextual info
        locator = self._extract_locator(error_message)
        timeout = self._extract_timeout(error_message)
        http_status = self._extract_http_status(error_message)
        
        # Extract root cause
        root_cause = self._extract_root_cause(error_message)
        
        # Calculate confidence
        confidence = self._calculate_confidence(failure_type, exception_type, stack_trace)
        
        return FailureClassification(
            failure_type=failure_type,
            exception_type=exception_type,
            error_message=error_message,
            stack_trace=stack_trace,
            root_cause=root_cause,
            location=location,
            component=component,
            locator=locator,
            timeout_duration=timeout,
            http_status=http_status,
            confidence=confidence
        )
    
    def _extract_exception_type(self, error_message: str) -> str:
        """Extract exception class name from error message."""
        # Look for exception class name at start of message
        match = re.search(r'^([\w.]+Exception|[\w.]+Error)', error_message, re.MULTILINE)
        if match:
            full_name = match.group(1)
            # Return simple name (last part after dot)
            return full_name.split('.')[-1]
        return ""
    
    def _determine_failure_type(self, exception_type: str, error_message: str) -> FailureType:
        """Determine FailureType from exception and message content."""
        # Check exception mappings first
        if exception_type in self.EXCEPTION_MAPPINGS:
            return self.EXCEPTION_MAPPINGS[exception_type]
        
        # Check message content for keywords
        message_lower = error_message.lower()
        
        if any(word in message_lower for word in ['timeout', 'timed out', 'wait']):
            return FailureType.TIMEOUT
        
        if any(word in message_lower for word in ['no such element', 'unable to locate', 'cannot find']):
            return FailureType.LOCATOR_NOT_FOUND
        
        if 'stale element' in message_lower:
            return FailureType.STALE_ELEMENT
        
        if any(word in message_lower for word in ['not visible', 'not displayed']):
            return FailureType.ELEMENT_NOT_VISIBLE
        
        if any(word in message_lower for word in ['assert', 'expected', 'actual']):
            return FailureType.ASSERTION
        
        if any(word in message_lower for word in ['connection', 'network', 'http']):
            return FailureType.NETWORK_ERROR
        
        if 'javascript' in message_lower or 'js error' in message_lower:
            return FailureType.JAVASCRIPT_ERROR
        
        if 'alert' in message_lower:
            return FailureType.UNEXPECTED_ALERT
        
        return FailureType.UNKNOWN
    
    def _parse_stack_trace(self, error_message: str) -> List[StackTraceFrame]:
        """Parse Java stack trace into structured frames."""
        frames = []
        
        lines = error_message.split('\n')
        for line in lines:
            # Try native method pattern
            match = self.NATIVE_METHOD_PATTERN.search(line)
            if match:
                frames.append(StackTraceFrame(
                    class_name=match.group(1),
                    method_name=match.group(2),
                    is_native=True
                ))
                continue
            
            # Try regular stack frame pattern
            match = self.STACK_FRAME_PATTERN.search(line)
            if match:
                class_name = match.group(1)
                method_name = match.group(2)
                file_name = match.group(3)
                line_number = int(match.group(4)) if match.group(4) else 0
                
                frames.append(StackTraceFrame(
                    class_name=class_name,
                    method_name=method_name,
                    file_name=file_name,
                    line_number=line_number
                ))
        
        return frames
    
    def _extract_location(self, stack_trace: List[StackTraceFrame]) -> Optional[FailureLocation]:
        """Extract failure location from stack trace."""
        if not stack_trace:
            return None
        
        # Find first non-framework frame (user code)
        for frame in stack_trace:
            if self._is_user_code(frame.class_name):
                package_parts = frame.class_name.split('.')
                class_name = package_parts[-1] if package_parts else frame.class_name
                package = '.'.join(package_parts[:-1]) if len(package_parts) > 1 else ""
                
                return FailureLocation(
                    file_path=frame.file_name,
                    line_number=frame.line_number,
                    class_name=class_name,
                    method_name=frame.method_name,
                    package=package
                )
        
        # Fallback to first frame
        first_frame = stack_trace[0]
        package_parts = first_frame.class_name.split('.')
        class_name = package_parts[-1] if package_parts else first_frame.class_name
        package = '.'.join(package_parts[:-1]) if len(package_parts) > 1 else ""
        
        return FailureLocation(
            file_path=first_frame.file_name,
            line_number=first_frame.line_number,
            class_name=class_name,
            method_name=first_frame.method_name,
            package=package
        )
    
    def _is_user_code(self, class_name: str) -> bool:
        """Check if class is user code (not framework)."""
        framework_packages = [
            'org.openqa.selenium',
            'cucumber.runtime',
            'org.junit',
            'org.testng',
            'java.lang',
            'java.util',
            'sun.',
            'jdk.internal'
        ]
        return not any(class_name.startswith(pkg) for pkg in framework_packages)
    
    def _determine_component(self, stack_trace: List[StackTraceFrame], step_name: str) -> FailureComponent:
        """Determine which component failed based on stack trace."""
        if not stack_trace:
            return FailureComponent.UNKNOWN
        
        # Check for page object patterns
        for frame in stack_trace[:5]:  # Check first 5 frames
            if 'page' in frame.class_name.lower() or 'Page' in frame.class_name:
                return FailureComponent.PAGE_OBJECT
        
        # Check for step definitions
        if 'step' in step_name.lower() or any('steps' in f.class_name.lower() for f in stack_trace[:5]):
            return FailureComponent.STEP_DEFINITION
        
        # Check for assertions
        for frame in stack_trace[:3]:
            if 'assert' in frame.method_name.lower() or 'Assert' in frame.class_name:
                return FailureComponent.ASSERTION_LIBRARY
        
        # Check for WebDriver
        for frame in stack_trace[:5]:
            if 'selenium' in frame.class_name.lower() or 'webdriver' in frame.class_name.lower():
                return FailureComponent.WEBDRIVER
        
        return FailureComponent.UNKNOWN
    
    def _extract_locator(self, error_message: str) -> Optional[str]:
        """Extract locator from error message."""
        match = self.LOCATOR_PATTERN.search(error_message)
        if match:
            if match.group(1) and match.group(2):
                return f"By.{match.group(1)}: {match.group(2)}"
            elif match.group(3):
                return match.group(3)
        return None
    
    def _extract_timeout(self, error_message: str) -> Optional[float]:
        """Extract timeout duration from error message."""
        match = self.TIMEOUT_PATTERN.search(error_message)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            # Convert to seconds
            if 'ms' in unit or 'millisecond' in unit:
                return value / 1000.0
            return value
        return None
    
    def _extract_http_status(self, error_message: str) -> Optional[int]:
        """Extract HTTP status code from error message."""
        match = self.HTTP_STATUS_PATTERN.search(error_message)
        if match:
            status = match.group(1) or match.group(2)
            return int(status)
        return None
    
    def _extract_root_cause(self, error_message: str) -> Optional[str]:
        """Extract root cause from nested exceptions."""
        # Look for "Caused by:" pattern
        match = re.search(r'Caused by:\s*([\w.]+Exception[^\n]*)', error_message)
        if match:
            return match.group(1).strip()
        return None
    
    def _calculate_confidence(
        self,
        failure_type: FailureType,
        exception_type: str,
        stack_trace: List[StackTraceFrame]
    ) -> float:
        """Calculate confidence score for classification."""
        confidence = 0.5  # Base confidence
        
        # High confidence if exception type matched
        if exception_type and exception_type in self.EXCEPTION_MAPPINGS:
            confidence = 0.9
        
        # Medium-high if failure type determined from message
        elif failure_type != FailureType.UNKNOWN:
            confidence = 0.7
        
        # Increase confidence if we have stack trace
        if stack_trace:
            confidence += 0.1
        
        # Decrease confidence for UNKNOWN
        if failure_type == FailureType.UNKNOWN:
            confidence = 0.3
        
        return min(confidence, 1.0)


def classify_failure(error_message: Optional[str], step_name: str = "") -> FailureClassification:
    """
    Convenience function to classify a failure.
    
    Args:
        error_message: Full error message with stack trace
        step_name: Name of failed step
        
    Returns:
        FailureClassification object
    """
    classifier = FailureClassifier()
    return classifier.classify(error_message, step_name)
