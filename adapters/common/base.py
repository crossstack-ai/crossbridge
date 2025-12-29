"""
Adapter Interface (shared across frameworks)
This is the contract that pytest and Robot both follow.
"""

from abc import ABC, abstractmethod
from typing import List, Dict


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
