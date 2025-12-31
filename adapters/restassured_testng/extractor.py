"""
RestAssured + TestNG test metadata extractor.

Extracts test metadata from RestAssured API test files without execution.
"""

from pathlib import Path
from typing import List, Optional
import re

from ..common.extractor import BaseTestExtractor
from ..common.models import TestMetadata
from .config import RestAssuredConfig
from .patterns import (
    CLASS_PATTERN,
    TEST_METHOD_PATTERN,
    GROUPS_PATTERN,
    SINGLE_GROUP_PATTERN,
    PRIORITY_PATTERN,
    ENABLED_PATTERN,
    DESCRIPTION_PATTERN,
    PACKAGE_PATTERN,
    IMPORT_PATTERN,
    RESTASSURED_METHODS,
)


class RestAssuredExtractor(BaseTestExtractor):
    """Extracts metadata from RestAssured + TestNG test files."""
    
    def __init__(self, config: Optional[RestAssuredConfig] = None):
        """
        Initialize extractor.
        
        Args:
            config: RestAssured configuration
        """
        self.config = config or RestAssuredConfig()
    
    def extract_tests(self, project_root: Optional[str] = None) -> List[TestMetadata]:
        """
        Extract all test metadata from project.
        
        Args:
            project_root: Project root directory (uses config if not provided)
            
        Returns:
            List of test metadata
        """
        if project_root:
            self.config.project_root = project_root
        
        results = []
        src_path = Path(self.config.project_root) / self.config.src_root
        
        if not src_path.exists():
            return results
        
        # Find all Java files
        for java_file in src_path.rglob("*.java"):
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
                
                # Check if it's a RestAssured test file
                if not self._is_restassured_test(content):
                    continue
                
                # Extract tests from this file
                file_tests = self._extract_from_file(java_file, content)
                results.extend(file_tests)
                
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return results
    
    def _is_restassured_test(self, content: str) -> bool:
        """Check if file contains RestAssured tests."""
        # Must have RestAssured imports
        if not IMPORT_PATTERN.search(content):
            return False
        
        # Must have @Test annotation
        if '@Test' not in content:
            return False
        
        # Should have RestAssured method calls
        has_restassured_calls = any(
            method in content for method in RESTASSURED_METHODS
        )
        
        return has_restassured_calls
    
    def _extract_from_file(self, java_file: Path, content: str) -> List[TestMetadata]:
        """Extract all tests from a single file."""
        results = []
        
        # Extract class name
        class_match = CLASS_PATTERN.search(content)
        if not class_match:
            return results
        
        class_name = class_match.group(1)
        
        # Extract package
        package = self._extract_package(content)
        full_class_name = f"{package}.{class_name}" if package else class_name
        
        # Extract class-level groups (if any)
        class_groups = self._extract_class_groups(content)
        
        # Extract test methods
        for method_match in TEST_METHOD_PATTERN.finditer(content):
            method_name = method_match.group(1)
            method_start = method_match.start()
            
            # Find the @Test annotation for this method
            test_annotation = self._find_test_annotation(content, method_start)
            
            if test_annotation:
                # Extract method-level details
                groups = self._extract_method_groups(test_annotation)
                priority = self._extract_priority(test_annotation)
                enabled = self._extract_enabled(test_annotation)
                description = self._extract_description(test_annotation)
                
                # Combine class and method groups
                all_groups = list(set(class_groups + groups))
                
                # Build metadata
                metadata = TestMetadata(
                    framework="restassured-testng",
                    test_name=method_name,  # Just method name
                    file_path=str(java_file.relative_to(Path(self.config.project_root))),
                    tags=all_groups,
                    test_type="api",
                    language="java"
                )
                
                results.append(metadata)
        
        return results
    
    def _extract_package(self, content: str) -> Optional[str]:
        """Extract package name from file."""
        match = PACKAGE_PATTERN.search(content)
        return match.group(1) if match else None
    
    def _extract_class_groups(self, content: str) -> List[str]:
        """Extract groups from class-level @Test annotation."""
        # Look for @Test on class definition
        class_test_match = re.search(
            r'@Test\s*\([^)]*\)\s*(?:public\s+)?class',
            content,
            re.MULTILINE | re.DOTALL
        )
        
        if not class_test_match:
            return []
        
        test_annotation = class_test_match.group(0)
        return self._extract_groups_from_annotation(test_annotation)
    
    def _find_test_annotation(self, content: str, method_start: int) -> Optional[str]:
        """Find the @Test annotation before a method."""
        # Look backwards from method start to find @Test
        before_method = content[:method_start]
        
        # Find the last @Test annotation before this method
        matches = list(re.finditer(r'@Test\s*(?:\([^)]*\))?', before_method))
        
        if matches:
            return matches[-1].group(0)
        
        return None
    
    def _extract_method_groups(self, test_annotation: str) -> List[str]:
        """Extract groups from method-level @Test annotation."""
        return self._extract_groups_from_annotation(test_annotation)
    
    def _extract_groups_from_annotation(self, annotation: str) -> List[str]:
        """Extract groups from @Test annotation string."""
        groups = []
        
        # Try multiple groups: groups = {"group1", "group2"}
        match = GROUPS_PATTERN.search(annotation)
        if match:
            groups_str = match.group(1)
            # Split and clean
            groups = [
                g.strip().strip('"').strip("'")
                for g in groups_str.split(',')
                if g.strip()
            ]
        else:
            # Try single group: groups = "group1"
            match = SINGLE_GROUP_PATTERN.search(annotation)
            if match:
                groups = [match.group(1)]
        
        return groups
    
    def _extract_priority(self, test_annotation: str) -> Optional[int]:
        """Extract priority from @Test annotation."""
        match = PRIORITY_PATTERN.search(test_annotation)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
    
    def _extract_enabled(self, test_annotation: str) -> Optional[bool]:
        """Extract enabled status from @Test annotation."""
        match = ENABLED_PATTERN.search(test_annotation)
        if match:
            return match.group(1).lower() == 'true'
        return None  # Default is enabled
    
    def _extract_description(self, test_annotation: str) -> Optional[str]:
        """Extract description from @Test annotation."""
        match = DESCRIPTION_PATTERN.search(test_annotation)
        return match.group(1) if match else None
