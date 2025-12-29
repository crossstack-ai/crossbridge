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
    id: str
    name: str
    framework: str
    file_path: str
    tags: List[str] = field(default_factory=list)


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
