"""
Adapter Interface (shared across frameworks)
This is the contract that pytest and Robot both follow.
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path
from .models import TestMetadata


class TestResult:
    def __init__(self, name: str, status: str, duration_ms: int, message: str = ""):
        self.name = name
        self.status = status  # pass | fail | skip
        self.duration_ms = duration_ms
        self.message = message


class BaseTestAdapter(ABC):

    @abstractmethod
    def discover_tests(self) -> List[str]:
        pass

    @abstractmethod
    def run_tests(
        self,
        tests: List[str] = None,
        tags: List[str] = None
    ) -> List[TestResult]:
        pass


class BaseTestExtractor(ABC):
    """
    Base class for test extractors.
    
    Test extractors parse test files and extract metadata without executing tests.
    Used by CLI discovery and persistence layer.
    """
    
    @abstractmethod
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract test metadata from test files.
        
        Returns:
            List of TestMetadata objects describing discovered tests
        """
        pass


class TestFrameworkAdapter(ABC):
    """
    Full adapter interface for test frameworks.
    
    Combines discovery, execution, and intent extraction capabilities.
    """
    
    @abstractmethod
    def discover_tests(self) -> List[TestMetadata]:
        """Discover all tests in the project."""
        pass
    
    @abstractmethod
    def run_tests(self, test_ids: List[str]) -> List[TestResult]:
        """Run specified tests and return results."""
        pass
    
    @abstractmethod
    def extract_intent(self, test_id: str):
        """Extract intent model from a test."""
        pass
