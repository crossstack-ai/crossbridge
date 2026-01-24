"""
RestAssured + Java test metadata extractor.

Extracts test metadata from RestAssured API test files (TestNG or JUnit 5) without execution.
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
    DISPLAY_NAME_PATTERN,
    JUNIT_TAG_PATTERN,
    JUNIT_TAGS_PATTERN,
    DISABLED_PATTERN,
    PACKAGE_PATTERN,
    RESTASSURED_IMPORT_PATTERN,
    TESTNG_IMPORT_PATTERN,
    JUNIT5_IMPORT_PATTERN,
    RESTASSURED_METHODS,
    AUTH_BASIC_PATTERN,
    AUTH_OAUTH2_PATTERN,
    AUTH_BEARER_PATTERN,
    JWT_VARIABLE_PATTERN,
    OAUTH_CLIENT_PATTERN,
)


class RestAssuredExtractor(BaseTestExtractor):
    """Extracts metadata from RestAssured + Java test files (TestNG or JUnit 5)."""
    
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
                
                # Detect framework and check if it's a RestAssured test file
                framework = self._detect_framework(content)
                if not framework or not self._is_restassured_test(content):
                    continue
                
                # Extract tests from this file
                file_tests = self._extract_from_file(java_file, content, framework)
                results.extend(file_tests)
                
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return results
    
    def _detect_framework(self, content: str) -> Optional[str]:
        """Detect which test framework is being used."""
        has_testng = TESTNG_IMPORT_PATTERN.search(content) is not None
        has_junit5 = JUNIT5_IMPORT_PATTERN.search(content) is not None
        
        if has_testng and has_junit5:
            return "both"  # Rare but possible
        elif has_testng:
            return "testng"
        elif has_junit5:
            return "junit5"
        return None
    
    def _is_restassured_test(self, content: str) -> bool:
        """Check if file contains RestAssured tests."""
        # Must have RestAssured imports
        if not RESTASSURED_IMPORT_PATTERN.search(content):
            return False
        
        # Must have @Test annotation
        if '@Test' not in content:
            return False
        
        # Should have RestAssured method calls
        has_restassured_calls = any(
            method in content for method in RESTASSURED_METHODS
        )
        
        return has_restassured_calls
    
    def extract_authentication_info(self, content: str) -> dict:
        """Extract authentication information from test code.
        
        Returns:
            Dictionary with authentication type and credentials/tokens
        """
        auth_info = {
            'type': None,
            'username': None,
            'password': None,
            'token': None,
            'client_id': None,
            'has_oauth': False,
            'has_jwt': False
        }
        
        # Check for basic auth
        basic_match = AUTH_BASIC_PATTERN.search(content)
        if basic_match:
            auth_info['type'] = 'basic'
            auth_info['username'] = basic_match.group(1)
            auth_info['password'] = basic_match.group(2)
        
        # Check for OAuth2
        oauth2_match = AUTH_OAUTH2_PATTERN.search(content)
        if oauth2_match:
            auth_info['type'] = 'oauth2'
            auth_info['token'] = oauth2_match.group(1)
            auth_info['has_oauth'] = True
        
        # Check for Bearer/JWT tokens
        bearer_match = AUTH_BEARER_PATTERN.search(content)
        if bearer_match:
            if not auth_info['type']:
                auth_info['type'] = 'bearer'
            auth_info['token'] = bearer_match.group(1)
            auth_info['has_jwt'] = True
        
        # Check for JWT variables
        jwt_var_match = JWT_VARIABLE_PATTERN.search(content)
        if jwt_var_match:
            auth_info['has_jwt'] = True
            if not auth_info['token']:
                auth_info['token'] = jwt_var_match.group(2)
        
        # Check for OAuth client credentials
        client_match = OAUTH_CLIENT_PATTERN.search(content)
        if client_match:
            auth_info['client_id'] = client_match.group(2)
            auth_info['has_oauth'] = True
        
        return auth_info
    
    def _extract_from_file(self, java_file: Path, content: str, framework: str) -> List[TestMetadata]:
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
        
        # Extract class-level tags/groups
        if framework == "testng" or framework == "both":
            class_tags = self._extract_class_groups(content)
        else:
            class_tags = self._extract_class_junit_tags(content)
        
        # Determine framework name for metadata
        fw_name = f"restassured-{framework}"
        
        # Extract test methods
        for method_match in TEST_METHOD_PATTERN.finditer(content):
            method_name = method_match.group(1)
            method_start = method_match.start()
            
            # Get annotation area before method
            # Look back up to 500 chars, but find boundaries
            area_start = max(0, method_start-500)
            before_method = content[area_start:method_start]
            
            # Find method-closing braces (end of previous method)
            # Pattern: } that's at the end of a line (method body end), not inline like {"smoke"}
            method_brace_matches = list(re.finditer(r'\}\s*[\r\n]', before_method))
            
            if method_brace_matches:
                # Start from after the last method-closing brace
                last_brace_end = method_brace_matches[-1].end()
                test_annotation_area = before_method[last_brace_end:]
            else:
                # No previous method, look for class opening brace followed by newline
                class_brace_match = re.search(r'\{\s*[\r\n]', before_method)
                if class_brace_match:
                    test_annotation_area = before_method[class_brace_match.end():]
                else:
                    test_annotation_area = before_method
            
            # Check if this method has @Test annotation
            if not re.search(r'@Test\b', test_annotation_area):
                continue
            
            # Check if disabled/enabled
            is_disabled = DISABLED_PATTERN.search(test_annotation_area) is not None
            
            # Skip disabled tests unless it's TestNG with enabled=false
            if is_disabled and framework == "junit5":
                continue
            
            # Extract tags based on framework
            if framework == "testng" or framework == "both":
                tags = self._extract_testng_tags(test_annotation_area, class_tags)
            elif framework == "junit5":
                tags = self._extract_junit5_tags(test_annotation_area, class_tags)
            else:
                tags = list(class_tags)
            
            # Extract authentication information from file
            auth_info = self.extract_authentication_info(content)
            
            # Build metadata
            metadata = TestMetadata(
                framework=fw_name,
                test_name=method_name,
                file_path=str(java_file.relative_to(Path(self.config.project_root))),
                tags=tags,
                test_type="api",
                language="java",
                metadata={
                    'authentication': auth_info if auth_info['type'] else None,
                    'has_oauth': auth_info['has_oauth'],
                    'has_jwt': auth_info['has_jwt']
                }
            )
            
            results.append(metadata)
        
        return results
    
    def _extract_package(self, content: str) -> Optional[str]:
        """Extract package name from file."""
        match = PACKAGE_PATTERN.search(content)
        return match.group(1) if match else None
    
    def _extract_class_groups(self, content: str) -> List[str]:
        """Extract TestNG groups from class-level @Test annotation."""
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
    
    def _extract_class_junit_tags(self, content: str) -> List[str]:
        """Extract JUnit 5 tags from class-level annotations."""
        tags = []
        
        # Look for class definition
        class_match = re.search(r'(?:public\s+)?class\s+\w+', content)
        if not class_match:
            return tags
        
        # Get area before class
        class_area = content[:class_match.start()]
        
        # Extract @Tag annotations
        for match in JUNIT_TAG_PATTERN.finditer(class_area):
            tags.append(match.group(1))
        
        # Extract @Tags annotations
        for match in JUNIT_TAGS_PATTERN.finditer(class_area):
            tags_str = match.group(1)
            tag_list = [t.strip().strip('"').strip("'") for t in tags_str.split(',') if t.strip()]
            tags.extend(tag_list)
        
        return tags
    
    def _extract_testng_tags(self, annotation_area: str, class_tags: List[str]) -> List[str]:
        """Extract TestNG groups/tags from method annotation area."""
        tags = list(class_tags)  # Start with class-level tags
        
        # Extract method-level groups
        groups_match = GROUPS_PATTERN.search(annotation_area)
        if groups_match:
            groups_str = groups_match.group(1)
            method_groups = [
                g.strip().strip('"').strip("'")
                for g in groups_str.split(',')
                if g.strip()
            ]
            tags.extend(method_groups)
        else:
            # Try single group
            single_match = SINGLE_GROUP_PATTERN.search(annotation_area)
            if single_match:
                tags.append(single_match.group(1))
        
        return list(set(tags))  # Remove duplicates
    
    def _extract_junit5_tags(self, annotation_area: str, class_tags: List[str]) -> List[str]:
        """Extract JUnit 5 tags from method annotation area."""
        tags = list(class_tags)  # Start with class-level tags
        
        # Extract @Tag annotations
        for match in JUNIT_TAG_PATTERN.finditer(annotation_area):
            tags.append(match.group(1))
        
        # Extract @Tags annotations
        for match in JUNIT_TAGS_PATTERN.finditer(annotation_area):
            tags_str = match.group(1)
            tag_list = [t.strip().strip('"').strip("'") for t in tags_str.split(',') if t.strip()]
            tags.extend(tag_list)
        
        return list(set(tags))  # Remove duplicates
    
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
