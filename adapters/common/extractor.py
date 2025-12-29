"""
Base extractor contract for test metadata extraction.

Extractors are read-only parsers that extract test metadata from source code
without executing tests. This is different from adapters which both discover
and run tests.
"""

from abc import ABC, abstractmethod
from typing import List
from .models import TestMetadata


class BaseTestExtractor(ABC):
    """
    Abstract base class for test metadata extractors.
    
    Extractors parse source files to extract test metadata without execution.
    Use this for frameworks/languages where:
    - Tests cannot be easily discovered via CLI
    - You need static analysis of test code
    - You want to map tests to source code for impact analysis
    - Execution happens separately (e.g., Maven/Gradle for Java)
    """

    @abstractmethod
    def extract_tests(self) -> List[TestMetadata]:
        """
        Parse source files and return normalized test metadata.
        
        This method scans test source files, parses them (using AST, regex, or
        other parsing techniques), and extracts metadata about each test case
        including names, tags, annotations, and file locations.
        
        Returns:
            List[TestMetadata]: List of test metadata objects containing:
                - id: Unique test identifier
                - name: Test method/function name
                - framework: Framework name (e.g., 'selenium-java', 'junit')
                - file_path: Path to the test file
                - tags: List of tags/markers/annotations
        
        Example:
            >>> extractor = SeleniumJavaExtractor("/path/to/project")
            >>> tests = extractor.extract_tests()
            >>> for test in tests:
            ...     print(f"{test.name} in {test.file_path}")
        """
        pass
