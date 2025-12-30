"""
Framework-agnostic domain models for test automation platform.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class TestStatus(str, Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class AssertionType(str, Enum):
    """Assertion types."""
    EQUALS = "equals"
    CONTAINS = "contains"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


@dataclass
class TestMetadata:
    """Metadata describing a test case."""
    framework: str                 # selenium-java, pytest, robot, etc.
    test_name: str                 # LoginTest.testValidLogin
    file_path: str
    tags: List[str] = field(default_factory=list)
    test_type: str = "ui"
    language: str = "python"
    
    # Backward compatibility - auto-generate id from test_name if needed
    @property
    def id(self) -> str:
        """Generate test ID from test_name for backward compatibility."""
        return self.test_name
    
    @property
    def name(self) -> str:
        """Alias for test_name for backward compatibility."""
        return self.test_name


@dataclass
class TestStep:
    """Individual step in a test execution."""
    description: str
    action: str
    target: Optional[str] = None


@dataclass
class Assertion:
    """Test assertion definition."""
    type: AssertionType
    expected: Any


@dataclass
class IntentModel:
    """High-level intent representation of a test."""
    test_name: str
    intent: str
    steps: List[TestStep] = field(default_factory=list)
    assertions: List[Assertion] = field(default_factory=list)
    code_paths: List[str] = field(default_factory=list)  # Step → code mapping for impact analysis


@dataclass
class ExecutionResult:
    """Result of test execution."""
    test_id: str
    status: TestStatus
    duration_ms: int
    logs: List[str] = field(default_factory=list)


@dataclass
class CoverageData:
    """Code coverage information for a test."""
    test_id: str
    covered_files: List[str] = field(default_factory=list)
