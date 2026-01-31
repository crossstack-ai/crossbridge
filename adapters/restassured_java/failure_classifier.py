"""
RestAssured API Test Failure Classification.

Provides intelligent classification of RestAssured test failures to enable
root cause analysis, failure grouping, and flaky test detection.

Gap 1.1 Implementation - RestAssured Failure Classification
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import re

from ..common.failure_classification import (
    BaseFailureClassification,
    StackFrame,
    FailureLocation,
    ComponentType,
    StackTraceParser,
    ConfidenceCalculator,
    PatternMatcher,
    classify_failure_component
)


class APIFailureType(Enum):
    """API-specific failure types for RestAssured tests."""
    # Schema/Contract failures
    CONTRACT_VIOLATION = "contract_violation"      # Schema/contract mismatch
    VALIDATION_FAILURE = "validation_failure"      # Response assertion failed
    
    # Network/Connection failures
    TIMEOUT = "timeout"                            # Connection/read timeout
    CONNECTION_ERROR = "connection_error"          # Cannot connect to server
    NETWORK_ERROR = "network_error"                # Generic network issue
    SSL_ERROR = "ssl_error"                        # Certificate/TLS issues
    
    # HTTP Status failures
    AUTH_FAILURE = "auth_failure"                  # 401, 403 responses
    CLIENT_ERROR = "client_error"                  # 4xx responses
    SERVER_ERROR = "server_error"                  # 5xx responses
    NOT_FOUND = "not_found"                        # 404 specifically
    
    # Data/Serialization failures
    SERIALIZATION_ERROR = "serialization_error"    # JSON/XML parsing failed
    DESERIALIZATION_ERROR = "deserialization_error" # Response parsing failed
    
    # Test/Assertion failures
    ASSERTION = "assertion"                        # Test assertion failed
    NULL_POINTER = "null_pointer"                  # NullPointerException
    
    # Other
    UNKNOWN = "unknown"


class APIComponentType(Enum):
    """API-specific component types."""
    API_CLIENT = "api_client"                  # RestAssured client code
    REQUEST_SPEC = "request_spec"              # RequestSpecification
    RESPONSE_SPEC = "response_spec"            # ResponseSpecification
    FILTER = "filter"                          # RequestFilter/ResponseFilter
    POJO_MAPPER = "pojo_mapper"                # POJO mapping code
    TEST_CODE = "test_code"                    # Test method
    HELPER = "helper"                          # Helper/utility method
    FRAMEWORK = "framework"                    # RestAssured framework
    API_SERVER = "api_server"                  # Server-side issue
    UNKNOWN = "unknown"


@dataclass
class APIFailureClassification(BaseFailureClassification):
    """
    Complete classification for RestAssured API test failures.
    
    Extends base classification with API-specific details.
    """
    # API-specific fields
    http_status: Optional[int] = None
    http_method: Optional[str] = None
    endpoint: Optional[str] = None
    response_time: Optional[float] = None
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    headers: Optional[Dict[str, str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        base_dict = super().to_dict()
        base_dict.update({
            "http_status": self.http_status,
            "http_method": self.http_method,
            "endpoint": self.endpoint,
            "response_time": self.response_time,
            "request_body": self.request_body,
            "response_body": self.response_body,
            "headers": self.headers
        })
        return base_dict


class RestAssuredFailureClassifier:
    """
    Classifier for RestAssured API test failures.
    
    Analyzes error messages, stack traces, and HTTP responses to categorize
    failures and extract relevant metadata.
    """
    
    # Exception type mappings
    EXCEPTION_MAPPINGS = {
        "AssertionError": APIFailureType.ASSERTION,
        "java.lang.AssertionError": APIFailureType.ASSERTION,
        
        "ConnectException": APIFailureType.CONNECTION_ERROR,
        "java.net.ConnectException": APIFailureType.CONNECTION_ERROR,
        "ConnectionException": APIFailureType.CONNECTION_ERROR,
        
        "SocketTimeoutException": APIFailureType.TIMEOUT,
        "java.net.SocketTimeoutException": APIFailureType.TIMEOUT,
        "ReadTimeoutException": APIFailureType.TIMEOUT,
        
        "SSLException": APIFailureType.SSL_ERROR,
        "javax.net.ssl.SSLException": APIFailureType.SSL_ERROR,
        "SSLHandshakeException": APIFailureType.SSL_ERROR,
        
        "JsonMappingException": APIFailureType.SERIALIZATION_ERROR,
        "JsonParseException": APIFailureType.SERIALIZATION_ERROR,
        "JsonProcessingException": APIFailureType.SERIALIZATION_ERROR,
        
        "NullPointerException": APIFailureType.NULL_POINTER,
        "java.lang.NullPointerException": APIFailureType.NULL_POINTER,
    }
    
    # Error message patterns
    CONTRACT_PATTERN = re.compile(
        r'schema|contract|specification|expected.*but\s+was|does\s+not\s+match',
        re.IGNORECASE
    )
    
    ENDPOINT_PATTERN = re.compile(
        r'(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\S+)',
        re.IGNORECASE
    )
    
    HTTP_METHOD_PATTERN = re.compile(
        r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b',
        re.IGNORECASE
    )
    
    RESPONSE_TIME_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|seconds?)',
        re.IGNORECASE
    )
    
    def classify(
        self,
        error_message: str,
        test_name: Optional[str] = None,
        http_status: Optional[int] = None,
        http_method: Optional[str] = None
    ) -> APIFailureClassification:
        """
        Classify an API test failure.
        
        Args:
            error_message: The error message/stack trace
            test_name: Optional test method name
            http_status: Optional HTTP status code
            http_method: Optional HTTP method
            
        Returns:
            Complete API failure classification
        """
        if not error_message:
            return self._create_unknown_classification("No error message")
        
        # Extract exception type
        exception_type = self._extract_exception_type(error_message)
        
        # Parse stack trace
        stack_trace = StackTraceParser.parse_java(error_message)
        
        # Determine failure type
        failure_type = self._determine_failure_type(
            error_message, exception_type, http_status
        )
        
        # Extract location
        location = self._extract_location(stack_trace)
        
        # Determine component
        component = self._determine_component(stack_trace, failure_type)
        
        # Extract API-specific metadata
        extracted_http_status = http_status or PatternMatcher.extract_http_status(error_message)
        extracted_method = http_method or self._extract_http_method(error_message)
        endpoint = self._extract_endpoint(error_message)
        response_time = self._extract_response_time(error_message)
        
        # Extract root cause
        root_cause = self._extract_root_cause(error_message)
        
        # Calculate confidence
        confidence = ConfidenceCalculator.calculate(
            exception_matched=exception_type in self.EXCEPTION_MAPPINGS,
            pattern_matched=self._has_pattern_match(error_message, failure_type),
            location_found=location is not None,
            component_identified=component != APIComponentType.UNKNOWN
        )
        
        # Determine if intermittent
        is_intermittent = self._is_intermittent(failure_type, extracted_http_status)
        
        return APIFailureClassification(
            failure_type=failure_type.value,
            exception_type=exception_type,
            error_message=error_message,
            stack_trace=stack_trace,
            root_cause=root_cause,
            location=location,
            component=self._api_component_to_base(component),
            confidence=confidence,
            is_intermittent=is_intermittent,
            http_status=extracted_http_status,
            http_method=extracted_method,
            endpoint=endpoint,
            response_time=response_time,
            metadata={"test_name": test_name} if test_name else {}
        )
    
    def _extract_exception_type(self, error_message: str) -> str:
        """Extract Java exception class name."""
        # Look for Java exception pattern
        match = re.search(r'([a-zA-Z_][\w.]*Exception|[a-zA-Z_][\w.]*Error)', error_message)
        if match:
            return match.group(1)
        return "Unknown"
    
    def _determine_failure_type(
        self,
        error_message: str,
        exception_type: str,
        http_status: Optional[int]
    ) -> APIFailureType:
        """Determine the failure type based on multiple signals."""
        # Check exception mapping first
        if exception_type in self.EXCEPTION_MAPPINGS:
            return self.EXCEPTION_MAPPINGS[exception_type]
        
        # Check HTTP status code
        if http_status:
            if http_status == 404:
                return APIFailureType.NOT_FOUND
            elif http_status in [401, 403]:
                return APIFailureType.AUTH_FAILURE
            elif 400 <= http_status < 500:
                return APIFailureType.CLIENT_ERROR
            elif 500 <= http_status < 600:
                return APIFailureType.SERVER_ERROR
        
        # Check error message patterns
        error_lower = error_message.lower()
        
        if PatternMatcher.is_timeout_error(error_message):
            return APIFailureType.TIMEOUT
        
        if PatternMatcher.is_network_error(error_message):
            return APIFailureType.CONNECTION_ERROR
        
        if PatternMatcher.is_auth_error(error_message):
            return APIFailureType.AUTH_FAILURE
        
        if self.CONTRACT_PATTERN.search(error_message):
            return APIFailureType.CONTRACT_VIOLATION
        
        if 'json' in error_lower or 'xml' in error_lower or 'parse' in error_lower:
            return APIFailureType.SERIALIZATION_ERROR
        
        if 'ssl' in error_lower or 'certificate' in error_lower or 'tls' in error_lower:
            return APIFailureType.SSL_ERROR
        
        if 'assert' in error_lower or 'expected' in error_lower:
            return APIFailureType.VALIDATION_FAILURE
        
        return APIFailureType.UNKNOWN
    
    def _extract_location(self, stack_trace: List[StackFrame]) -> Optional[FailureLocation]:
        """Extract failure location from stack trace."""
        # Find first non-framework frame
        user_frames = [f for f in stack_trace if not f.is_framework_code]
        if user_frames:
            frame = user_frames[0]
            return FailureLocation(
                file_path=frame.file_path,
                line_number=frame.line_number,
                function_name=frame.function_name,
                class_name=frame.class_name
            )
        return None
    
    def _determine_component(
        self,
        stack_trace: List[StackFrame],
        failure_type: APIFailureType
    ) -> APIComponentType:
        """Determine which component caused the failure."""
        if not stack_trace:
            # Infer from failure type
            if failure_type in [APIFailureType.SERVER_ERROR, APIFailureType.AUTH_FAILURE]:
                return APIComponentType.API_SERVER
            return APIComponentType.UNKNOWN
        
        # Find first user frame
        user_frames = [f for f in stack_trace if not f.is_framework_code]
        if not user_frames:
            return APIComponentType.FRAMEWORK
        
        frame = user_frames[0]
        file_lower = frame.file_path.lower()
        class_lower = (frame.class_name or "").lower()
        
        # API-specific heuristics
        if 'filter' in file_lower or 'filter' in class_lower:
            return APIComponentType.FILTER
        elif 'spec' in file_lower or 'specification' in class_lower:
            if 'request' in file_lower or 'request' in class_lower:
                return APIComponentType.REQUEST_SPEC
            elif 'response' in file_lower or 'response' in class_lower:
                return APIComponentType.RESPONSE_SPEC
        elif 'pojo' in file_lower or 'mapper' in class_lower or 'dto' in file_lower:
            return APIComponentType.POJO_MAPPER
        elif 'client' in file_lower or 'service' in class_lower:
            return APIComponentType.API_CLIENT
        elif 'test' in file_lower:
            return APIComponentType.TEST_CODE
        elif 'helper' in file_lower or 'util' in file_lower:
            return APIComponentType.HELPER
        
        return APIComponentType.TEST_CODE
    
    def _extract_http_method(self, error_message: str) -> Optional[str]:
        """Extract HTTP method from error message."""
        match = self.HTTP_METHOD_PATTERN.search(error_message)
        if match:
            return match.group(1).upper()
        return None
    
    def _extract_endpoint(self, error_message: str) -> Optional[str]:
        """Extract API endpoint from error message."""
        match = self.ENDPOINT_PATTERN.search(error_message)
        if match:
            return match.group(1)
        return None
    
    def _extract_response_time(self, error_message: str) -> Optional[float]:
        """Extract response time in milliseconds."""
        match = self.RESPONSE_TIME_PATTERN.search(error_message)
        if match:
            try:
                time_value = float(match.group(1))
                # Already in ms if pattern includes 'ms'
                return time_value
            except (ValueError, IndexError):
                pass
        return None
    
    def _extract_root_cause(self, error_message: str) -> Optional[str]:
        """Extract root cause from nested exceptions."""
        # Look for "Caused by:" pattern
        caused_by_match = re.search(r'Caused by:\s*([^\n]+)', error_message)
        if caused_by_match:
            return caused_by_match.group(1).strip()
        return None
    
    def _has_pattern_match(self, error_message: str, failure_type: APIFailureType) -> bool:
        """Check if error message has patterns matching the failure type."""
        if failure_type == APIFailureType.CONTRACT_VIOLATION:
            return bool(self.CONTRACT_PATTERN.search(error_message))
        elif failure_type == APIFailureType.TIMEOUT:
            return PatternMatcher.is_timeout_error(error_message)
        elif failure_type == APIFailureType.CONNECTION_ERROR:
            return PatternMatcher.is_network_error(error_message)
        return False
    
    def _is_intermittent(self, failure_type: APIFailureType, http_status: Optional[int]) -> bool:
        """Determine if failure type is typically intermittent."""
        # Network/timeout failures are usually intermittent
        intermittent_types = [
            APIFailureType.TIMEOUT,
            APIFailureType.CONNECTION_ERROR,
            APIFailureType.NETWORK_ERROR,
        ]
        
        if failure_type in intermittent_types:
            return True
        
        # 5xx errors are often intermittent
        if http_status and 500 <= http_status < 600:
            return True
        
        # 429 (Too Many Requests) is intermittent
        if http_status == 429:
            return True
        
        return False
    
    def _api_component_to_base(self, api_component: APIComponentType) -> ComponentType:
        """Convert API-specific component to base component type."""
        mapping = {
            APIComponentType.TEST_CODE: ComponentType.TEST_CODE,
            APIComponentType.HELPER: ComponentType.HELPER,
            APIComponentType.FRAMEWORK: ComponentType.FRAMEWORK,
            APIComponentType.API_CLIENT: ComponentType.LIBRARY,
            APIComponentType.REQUEST_SPEC: ComponentType.LIBRARY,
            APIComponentType.RESPONSE_SPEC: ComponentType.LIBRARY,
            APIComponentType.FILTER: ComponentType.LIBRARY,
            APIComponentType.POJO_MAPPER: ComponentType.LIBRARY,
            APIComponentType.API_SERVER: ComponentType.APPLICATION,
            APIComponentType.UNKNOWN: ComponentType.UNKNOWN,
        }
        return mapping.get(api_component, ComponentType.UNKNOWN)
    
    def _create_unknown_classification(self, reason: str) -> APIFailureClassification:
        """Create an unknown classification."""
        return APIFailureClassification(
            failure_type=APIFailureType.UNKNOWN.value,
            exception_type="Unknown",
            error_message=reason,
            confidence=0.0,
            metadata={"reason": reason}
        )


# Convenience function for quick classification
def classify_api_failure(
    error_message: str,
    test_name: Optional[str] = None,
    http_status: Optional[int] = None,
    http_method: Optional[str] = None
) -> APIFailureClassification:
    """
    Classify an API test failure.
    
    Args:
        error_message: The error message/stack trace
        test_name: Optional test method name
        http_status: Optional HTTP status code
        http_method: Optional HTTP method
        
    Returns:
        Complete API failure classification
    """
    classifier = RestAssuredFailureClassifier()
    return classifier.classify(error_message, test_name, http_status, http_method)
