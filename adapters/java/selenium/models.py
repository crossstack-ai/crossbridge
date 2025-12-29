"""
Data models for Selenium-Java test execution.

These models define the contract between the adapter and runners.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class TestExecutionRequest:
    """
    Request to execute Selenium-Java tests.
    
    This is a framework-agnostic model that the adapter translates
    into specific Maven/Gradle/JUnit/TestNG commands.
    """
    working_dir: str
    tests: Optional[List[str]] = None           # Fully qualified test names (e.g., com.example.LoginTest)
    test_methods: Optional[List[str]] = None    # Specific methods (e.g., LoginTest#testValidLogin)
    tags: Optional[List[str]] = None            # JUnit 5 tags
    groups: Optional[List[str]] = None          # TestNG groups
    categories: Optional[List[str]] = None      # JUnit 4 categories
    parallel: bool = False                      # Enable parallel execution
    thread_count: Optional[int] = None          # Number of threads for parallel execution
    properties: Optional[dict] = None           # Additional properties (-Dprop=value)
    
    def __post_init__(self):
        """Validate and normalize paths."""
        self.working_dir = str(Path(self.working_dir).resolve())


@dataclass
class TestExecutionResult:
    """
    Result of test execution.
    
    Normalized format regardless of build tool or framework.
    """
    status: str                                 # passed | failed | error
    exit_code: int
    report_path: Optional[str] = None           # Path to test reports (JUnit XML, HTML)
    raw_output: str = ""                        # Combined stdout + stderr
    tests_run: int = 0                          # Total tests executed
    tests_passed: int = 0                       # Tests that passed
    tests_failed: int = 0                       # Tests that failed
    tests_skipped: int = 0                      # Tests that were skipped
    execution_time: float = 0.0                 # Total execution time in seconds
    error_message: Optional[str] = None         # Error message if status is error
    
    def is_successful(self) -> bool:
        """Check if execution was successful (all tests passed)."""
        return self.status == "passed" and self.exit_code == 0
    
    def to_dict(self) -> dict:
        """Convert result to dictionary for serialization."""
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "report_path": self.report_path,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_skipped": self.tests_skipped,
            "execution_time": self.execution_time,
            "error_message": self.error_message
        }


@dataclass
class BuildToolConfig:
    """
    Configuration for detected build tool.
    """
    tool: str                                   # maven | gradle
    version: Optional[str] = None               # Build tool version
    test_output_dir: str = ""                   # Where test reports are generated
    test_source_dir: str = ""                   # Where test sources are located
    
    def get_report_path(self, project_root: str) -> str:
        """Get the path to test reports relative to project root."""
        if self.tool == "maven":
            return str(Path(project_root) / "target" / "surefire-reports")
        elif self.tool == "gradle":
            return str(Path(project_root) / "build" / "test-results" / "test")
        return ""


@dataclass
class TestFrameworkConfig:
    """
    Configuration for detected test framework.
    """
    framework: str                              # junit4 | junit5 | testng
    version: Optional[str] = None               # Framework version
    supports_tags: bool = False                 # Whether framework supports tags
    supports_groups: bool = False               # Whether framework supports groups
    supports_categories: bool = False           # Whether framework supports categories
    
    def get_selective_execution_support(self) -> dict:
        """Get which selective execution features are supported."""
        return {
            "tests": True,                      # All frameworks support test class selection
            "methods": True,                    # All frameworks support method selection
            "tags": self.supports_tags,
            "groups": self.supports_groups,
            "categories": self.supports_categories
        }
