"""
Log Artifacts Data Models

Defines data structures for structured log ingestion and failure representation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from enum import Enum


class FailureCategory(str, Enum):
    """Categories of test failures"""
    TEST_ASSERTION = "test_assertion"  # Test logic failure
    INFRASTRUCTURE = "infrastructure"  # Network, timeout, connection issues
    ENVIRONMENT = "environment"  # Config, data, environment setup
    APPLICATION = "application"  # Application errors (500, crashes)
    FLAKY = "flaky"  # Intermittent failures
    UNKNOWN = "unknown"


@dataclass
class LogArtifacts:
    """
    Collection of log artifacts for a test run.
    
    Identifies all available log sources for structured analysis.
    """
    testng_xml_path: Optional[Path] = None
    framework_log_path: Optional[Path] = None
    driver_log_paths: List[Path] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate paths"""
        if self.testng_xml_path:
            self.testng_xml_path = Path(self.testng_xml_path)
        if self.framework_log_path:
            self.framework_log_path = Path(self.framework_log_path)
        self.driver_log_paths = [Path(p) for p in self.driver_log_paths]
    
    def validate(self) -> bool:
        """Check if at least one artifact exists"""
        has_testng = self.testng_xml_path and self.testng_xml_path.exists()
        has_framework = self.framework_log_path and self.framework_log_path.exists()
        has_driver = any(p.exists() for p in self.driver_log_paths)
        return has_testng or has_framework or has_driver
    
    def available_sources(self) -> List[str]:
        """List available log sources"""
        sources = []
        if self.testng_xml_path and self.testng_xml_path.exists():
            sources.append("testng_xml")
        if self.framework_log_path and self.framework_log_path.exists():
            sources.append("framework_log")
        if any(p.exists() for p in self.driver_log_paths):
            sources.append("driver_logs")
        return sources


@dataclass
class StructuredFailure:
    """
    Normalized representation of a test failure.
    
    Extracted from structured sources (TestNG XML, JUnit XML, etc.)
    """
    # Test identification
    test_name: str
    class_name: str
    method_name: Optional[str] = None
    
    # Status
    status: str = "FAIL"  # PASS, FAIL, SKIP, ERROR
    
    # Failure details
    failure_type: Optional[str] = None  # AssertionError, NullPointerException, etc.
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Timing
    duration_ms: int = 0
    timestamp: Optional[str] = None
    
    # Classification
    category: FailureCategory = FailureCategory.UNKNOWN
    infra_related: bool = False
    
    # Context
    test_group: Optional[str] = None
    parameters: Optional[str] = None
    
    def short_error(self) -> str:
        """Get first line of error message"""
        if not self.error_message:
            return ""
        return self.error_message.split('\n')[0][:100]
    
    def is_passed(self) -> bool:
        """Check if test passed"""
        return self.status.upper() == "PASS"
    
    def is_failed(self) -> bool:
        """Check if test failed"""
        return self.status.upper() in ["FAIL", "ERROR"]
    
    def is_skipped(self) -> bool:
        """Check if test was skipped"""
        return self.status.upper() == "SKIP"
