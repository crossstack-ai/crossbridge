"""
Configuration for Selenium-Java extractor.
"""

from dataclasses import dataclass
from typing import Set
from .build_detection import get_primary_framework, detect_java_test_frameworks


@dataclass
class SeleniumJavaConfig:
    root_dir: str = "src/test/java"
    test_framework: str = None  # Specific framework: "junit" or "testng"
    project_root: str = "."  # Root directory for framework detection
    
    def __post_init__(self):
        """Auto-detect test framework if not specified."""
        if self.test_framework is None:
            self.test_framework = get_primary_framework(self.project_root, self.root_dir)
    
    @staticmethod
    def detect_all_frameworks(project_root: str = ".", source_root: str = "src/test/java") -> Set[str]:
        """Detect all Java test frameworks in a project."""
        return detect_java_test_frameworks(project_root, source_root)
