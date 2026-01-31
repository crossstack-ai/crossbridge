"""
Shared Failure Classification Framework for CrossBridge Adapters.

This module provides reusable failure classification components that can be
used across different test framework adapters (Selenium, Playwright, RestAssured, etc.).

Key Features:
- Base failure classification dataclasses
- Common failure patterns
- Confidence scoring utilities
- Stack trace parsing utilities
- Component detection utilities
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Pattern
import re


class ComponentType(Enum):
    """Generic component types across all frameworks."""
    PAGE_OBJECT = "page_object"
    TEST_CODE = "test_code"
    STEP_DEFINITION = "step_definition"
    FIXTURE = "fixture"
    HELPER = "helper"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    DRIVER = "driver"
    APPLICATION = "application"
    UNKNOWN = "unknown"


@dataclass
class StackFrame:
    """Generic stack frame representation."""
    file_path: str
    line_number: int
    function_name: str
    class_name: Optional[str] = None
    module_name: Optional[str] = None
    is_framework_code: bool = False
    is_native: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file_path,
            "line": self.line_number,
            "function": self.function_name,
            "class": self.class_name,
            "module": self.module_name,
            "is_framework": self.is_framework_code,
            "is_native": self.is_native
        }


@dataclass
class FailureLocation:
    """Location where failure occurred."""
    file_path: str
    line_number: int
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    module_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file_path,
            "line": self.line_number,
            "function": self.function_name,
            "class": self.class_name,
            "module": self.module_name
        }


@dataclass
class BaseFailureClassification:
    """Base failure classification applicable to all frameworks."""
    failure_type: str  # Framework-specific enum value
    exception_type: str
    error_message: str
    stack_trace: List[StackFrame] = field(default_factory=list)
    root_cause: Optional[str] = None
    location: Optional[FailureLocation] = None
    component: ComponentType = ComponentType.UNKNOWN
    confidence: float = 0.0  # 0.0 to 1.0
    is_intermittent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "failure_type": self.failure_type,
            "exception_type": self.exception_type,
            "error_message": self.error_message,
            "stack_trace": [frame.to_dict() for frame in self.stack_trace],
            "root_cause": self.root_cause,
            "location": self.location.to_dict() if self.location else None,
            "component": self.component.value,
            "confidence": self.confidence,
            "is_intermittent": self.is_intermittent,
            "metadata": self.metadata
        }


class StackTraceParser:
    """Utility for parsing stack traces from different languages."""
    
    # Java stack trace pattern
    JAVA_FRAME_PATTERN = re.compile(
        r'\s*at\s+(?P<class>[\w.$]+)\.(?P<method>[\w<>]+)\((?P<file>[\w.]+):(?P<line>\d+)\)'
    )
    JAVA_NATIVE_PATTERN = re.compile(r'\s*at\s+.*\(Native Method\)')
    
    # Python stack trace pattern
    PYTHON_FRAME_PATTERN = re.compile(
        r'\s*File\s+"(?P<file>[^"]+)",\s+line\s+(?P<line>\d+),\s+in\s+(?P<function>\w+)'
    )
    
    # C# stack trace pattern
    DOTNET_FRAME_PATTERN = re.compile(
        r'\s*at\s+(?P<class>[\w.]+)\.(?P<method>[\w<>]+)\(.*\)\s+in\s+(?P<file>[^:]+):line\s+(?P<line>\d+)'
    )
    
    # JavaScript stack trace pattern
    JS_FRAME_PATTERN = re.compile(
        r'\s*at\s+(?P<function>[\w.]+)\s+\((?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+)\)'
    )
    
    @classmethod
    def parse_java(cls, stack_trace: str) -> List[StackFrame]:
        """Parse Java stack trace."""
        frames = []
        for line in stack_trace.split('\n'):
            # Check for native method
            if cls.JAVA_NATIVE_PATTERN.match(line):
                continue
            
            # Parse regular frame
            match = cls.JAVA_FRAME_PATTERN.match(line)
            if match:
                frames.append(StackFrame(
                    file_path=match.group('file'),
                    line_number=int(match.group('line')),
                    function_name=match.group('method'),
                    class_name=match.group('class'),
                    is_framework_code=cls._is_framework_class(match.group('class'))
                ))
        
        return frames
    
    @classmethod
    def parse_python(cls, stack_trace: str) -> List[StackFrame]:
        """Parse Python stack trace."""
        frames = []
        for line in stack_trace.split('\n'):
            match = cls.PYTHON_FRAME_PATTERN.match(line)
            if match:
                file_path = match.group('file')
                frames.append(StackFrame(
                    file_path=file_path,
                    line_number=int(match.group('line')),
                    function_name=match.group('function'),
                    is_framework_code=cls._is_framework_file(file_path)
                ))
        
        return frames
    
    @classmethod
    def parse_dotnet(cls, stack_trace: str) -> List[StackFrame]:
        """Parse .NET/C# stack trace."""
        frames = []
        for line in stack_trace.split('\n'):
            match = cls.DOTNET_FRAME_PATTERN.match(line)
            if match:
                frames.append(StackFrame(
                    file_path=match.group('file'),
                    line_number=int(match.group('line')),
                    function_name=match.group('method'),
                    class_name=match.group('class'),
                    is_framework_code=cls._is_framework_class(match.group('class'))
                ))
        
        return frames
    
    @classmethod
    def parse_javascript(cls, stack_trace: str) -> List[StackFrame]:
        """Parse JavaScript/TypeScript stack trace."""
        frames = []
        for line in stack_trace.split('\n'):
            match = cls.JS_FRAME_PATTERN.match(line)
            if match:
                file_path = match.group('file')
                frames.append(StackFrame(
                    file_path=file_path,
                    line_number=int(match.group('line')),
                    function_name=match.group('function'),
                    is_framework_code=cls._is_framework_file(file_path)
                ))
        
        return frames
    
    @classmethod
    def _is_framework_class(cls, class_name: str) -> bool:
        """Check if class is framework code (Java/C#)."""
        framework_prefixes = [
            'org.junit', 'org.testng', 'org.openqa.selenium',
            'io.restassured', 'com.microsoft.playwright',
            'NUnit', 'MSTest', 'Xunit', 'SpecFlow',
            'OpenQA.Selenium', 'RestSharp'
        ]
        return any(class_name.startswith(prefix) for prefix in framework_prefixes)
    
    @classmethod
    def _is_framework_file(cls, file_path: str) -> bool:
        """Check if file is framework code (Python/JS)."""
        framework_indicators = [
            'site-packages', 'node_modules', 'pytest', 'playwright',
            'selenium', 'cypress', 'robot', 'unittest'
        ]
        return any(indicator in file_path for indicator in framework_indicators)


class ConfidenceCalculator:
    """Calculate confidence scores for failure classifications."""
    
    @staticmethod
    def calculate(
        exception_matched: bool,
        pattern_matched: bool,
        location_found: bool,
        component_identified: bool
    ) -> float:
        """
        Calculate confidence score based on classification factors.
        
        Args:
            exception_matched: Exception type was identified
            pattern_matched: Error message pattern matched
            location_found: Failure location was extracted
            component_identified: Component was identified
            
        Returns:
            Confidence score from 0.0 to 1.0
        """
        score = 0.0
        
        # Exception type is most reliable (40%)
        if exception_matched:
            score += 0.4
        
        # Pattern matching is good indicator (30%)
        if pattern_matched:
            score += 0.3
        
        # Location helps but less critical (20%)
        if location_found:
            score += 0.2
        
        # Component identification adds context (10%)
        if component_identified:
            score += 0.1
        
        return min(score, 1.0)


class PatternMatcher:
    """Common pattern matching utilities for failure classification."""
    
    # HTTP status patterns
    HTTP_STATUS_PATTERN = re.compile(r'\b(?:status|code|HTTP)[\s:]*(\d{3})\b', re.IGNORECASE)
    
    # Timeout patterns
    TIMEOUT_PATTERN = re.compile(
        r'timeout|timed?\s*out|exceeded.*time|waiting.*(\d+)\s*(second|ms|millisecond)',
        re.IGNORECASE
    )
    TIMEOUT_DURATION_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(second|sec|ms|millisecond)', re.IGNORECASE)
    
    # Network patterns
    NETWORK_ERROR_PATTERN = re.compile(
        r'connection\s+refused|cannot\s+connect|network|socket|refused\s+to\s+connect',
        re.IGNORECASE
    )
    
    # Auth patterns
    AUTH_ERROR_PATTERN = re.compile(r'unauthorized|forbidden|authentication|401|403', re.IGNORECASE)
    
    @classmethod
    def extract_http_status(cls, text: str) -> Optional[int]:
        """Extract HTTP status code from text."""
        match = cls.HTTP_STATUS_PATTERN.search(text)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
        return None
    
    @classmethod
    def extract_timeout_duration(cls, text: str) -> Optional[float]:
        """Extract timeout duration in seconds."""
        match = cls.TIMEOUT_DURATION_PATTERN.search(text)
        if match:
            try:
                duration = float(match.group(1))
                unit = match.group(2).lower()
                if 'ms' in unit or 'millisecond' in unit:
                    duration = duration / 1000.0
                return duration
            except (ValueError, IndexError):
                pass
        return None
    
    @classmethod
    def is_timeout_error(cls, text: str) -> bool:
        """Check if text indicates timeout error."""
        return bool(cls.TIMEOUT_PATTERN.search(text))
    
    @classmethod
    def is_network_error(cls, text: str) -> bool:
        """Check if text indicates network error."""
        return bool(cls.NETWORK_ERROR_PATTERN.search(text))
    
    @classmethod
    def is_auth_error(cls, text: str) -> bool:
        """Check if text indicates authentication error."""
        return bool(cls.AUTH_ERROR_PATTERN.search(text))


def classify_failure_component(
    stack_frames: List[StackFrame],
    file_patterns: Optional[Dict[ComponentType, List[Pattern]]] = None
) -> ComponentType:
    """
    Classify which component caused the failure based on stack trace.
    
    Args:
        stack_frames: List of stack frames
        file_patterns: Optional patterns to match files to components
        
    Returns:
        ComponentType enum value
    """
    if not stack_frames:
        return ComponentType.UNKNOWN
    
    # Find first non-framework frame (user code)
    user_frames = [f for f in stack_frames if not f.is_framework_code]
    if not user_frames:
        return ComponentType.FRAMEWORK
    
    first_user_frame = user_frames[0]
    
    # Use custom patterns if provided
    if file_patterns:
        for component_type, patterns in file_patterns.items():
            for pattern in patterns:
                if pattern.search(first_user_frame.file_path):
                    return component_type
    
    # Default heuristics based on file path
    file_lower = first_user_frame.file_path.lower()
    
    if 'page' in file_lower or 'pageobject' in file_lower:
        return ComponentType.PAGE_OBJECT
    elif 'step' in file_lower:
        return ComponentType.STEP_DEFINITION
    elif 'fixture' in file_lower or 'conftest' in file_lower:
        return ComponentType.FIXTURE
    elif 'test' in file_lower or 'spec' in file_lower:
        return ComponentType.TEST_CODE
    elif 'helper' in file_lower or 'util' in file_lower:
        return ComponentType.HELPER
    
    return ComponentType.TEST_CODE  # Default to test code
