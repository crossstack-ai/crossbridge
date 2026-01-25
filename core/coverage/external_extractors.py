"""
External Test Case Reference Extractors.

Extract external test case IDs (TestRail, Zephyr, etc.) from:
- Annotations (@TestRail, @ExternalTestCase)
- Tags (@testrail:C12345)
- File patterns
- API integration (future)

Supports:
- Java (JUnit, TestNG)
- Python (pytest, Robot Framework)
- Cucumber
"""

import re
from typing import List, Optional
from dataclasses import dataclass

from core.logging import get_logger, LogCategory
from .functional_models import ExternalTestRef

logger = get_logger(__name__, category=LogCategory.TESTING)


@dataclass
class AnnotationPattern:
    """Pattern for matching annotations."""
    pattern: str
    system: str
    group_index: int = 1


@dataclass
class TagPattern:
    """Pattern for matching tags."""
    pattern: str
    system: str


class ExternalTestCaseExtractor:
    """
    Base class for extracting external test case references.
    """
    
    # Common annotation patterns
    ANNOTATION_PATTERNS = [
        # @TestRail(id = "C12345")
        AnnotationPattern(
            pattern=r'@TestRail\s*\(\s*id\s*=\s*["\']([^"\']+)["\']\s*\)',
            system="testrail"
        ),
        # @ExternalTestCase("C12345")
        AnnotationPattern(
            pattern=r'@ExternalTestCase\s*\(\s*["\']([^"\']+)["\']\s*\)',
            system="testrail"  # Default
        ),
        # @Zephyr(id = "T-1234")
        AnnotationPattern(
            pattern=r'@Zephyr\s*\(\s*id\s*=\s*["\']([^"\']+)["\']\s*\)',
            system="zephyr"
        ),
        # @QTest(id = "TC-1234")
        AnnotationPattern(
            pattern=r'@QTest\s*\(\s*id\s*=\s*["\']([^"\']+)["\']\s*\)',
            system="qtest"
        ),
    ]
    
    # Common tag patterns
    TAG_PATTERNS = [
        # testrail:C12345, @testrail:C12345
        TagPattern(pattern=r'@?testrail:([^\s,]+)', system="testrail"),
        # zephyr:T-1234, @zephyr:T-1234
        TagPattern(pattern=r'@?zephyr:([^\s,]+)', system="zephyr"),
        # qtest:TC-1234, @qtest:TC-1234
        TagPattern(pattern=r'@?qtest:([^\s,]+)', system="qtest"),
        # jira:TEST-1234
        TagPattern(pattern=r'@?jira:([^\s,]+)', system="jira"),
    ]
    
    def extract_from_annotations(
        self,
        annotations: List[str]
    ) -> List[ExternalTestRef]:
        """
        Extract external test case refs from annotations.
        
        Args:
            annotations: List of annotation strings
            
        Returns:
            List of ExternalTestRef objects
        """
        refs = []
        
        for annotation in annotations:
            for pattern in self.ANNOTATION_PATTERNS:
                match = re.search(pattern.pattern, annotation)
                if match:
                    refs.append(ExternalTestRef(
                        system=pattern.system,
                        external_id=match.group(pattern.group_index),
                        source="annotation"
                    ))
        
        return refs
    
    def extract_from_tags(
        self,
        tags: List[str]
    ) -> List[ExternalTestRef]:
        """
        Extract external test case refs from tags.
        
        Args:
            tags: List of tag strings
            
        Returns:
            List of ExternalTestRef objects
        """
        refs = []
        
        for tag in tags:
            for pattern in self.TAG_PATTERNS:
                match = re.search(pattern.pattern, tag)
                if match:
                    refs.append(ExternalTestRef(
                        system=pattern.system,
                        external_id=match.group(1),
                        source="tag"
                    ))
        
        return refs
    
    def extract_from_test(
        self,
        test_source: str,
        tags: List[str]
    ) -> List[ExternalTestRef]:
        """
        Extract external test case refs from test source code and tags.
        
        Args:
            test_source: Test source code
            tags: List of tags
            
        Returns:
            List of ExternalTestRef objects
        """
        refs = []
        
        # Extract from source (annotations)
        annotations = self._extract_annotations(test_source)
        refs.extend(self.extract_from_annotations(annotations))
        
        # Extract from tags
        refs.extend(self.extract_from_tags(tags))
        
        return refs
    
    def _extract_annotations(self, source: str) -> List[str]:
        """
        Extract annotation strings from source code.
        
        Args:
            source: Source code
            
        Returns:
            List of annotation strings
        """
        # Find all annotations (@AnnotationName(...))
        annotation_pattern = r'@[A-Z][A-Za-z0-9]*\s*\([^)]*\)'
        return re.findall(annotation_pattern, source)


class JavaExternalTestCaseExtractor(ExternalTestCaseExtractor):
    """
    Extractor for Java tests (JUnit, TestNG).
    """
    
    # Java-specific annotation patterns
    JAVA_ANNOTATION_PATTERNS = ExternalTestCaseExtractor.ANNOTATION_PATTERNS + [
        # @TestRailCase(value = "C12345")
        AnnotationPattern(
            pattern=r'@TestRailCase\s*\(\s*value\s*=\s*["\']([^"\']+)["\']\s*\)',
            system="testrail"
        ),
        # @TestRail("C12345")
        AnnotationPattern(
            pattern=r'@TestRail\s*\(\s*["\']([^"\']+)["\']\s*\)',
            system="testrail"
        ),
    ]
    
    def __init__(self):
        super().__init__()
        self.ANNOTATION_PATTERNS = self.JAVA_ANNOTATION_PATTERNS
    
    def extract_from_java_file(self, file_path: str) -> List[ExternalTestRef]:
        """
        Extract external test case refs from Java file.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of ExternalTestRef objects
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Extract from annotations
        refs = self.extract_from_test(source, [])
        
        # Also check for tags in comments (JavaDoc)
        javadoc_tags = self._extract_javadoc_tags(source)
        refs.extend(self.extract_from_tags(javadoc_tags))
        
        return refs
    
    def _extract_javadoc_tags(self, source: str) -> List[str]:
        """
        Extract tags from JavaDoc comments.
        
        Args:
            source: Java source code
            
        Returns:
            List of tag strings
        """
        tags = []
        
        # Find JavaDoc comments (/** ... */)
        javadoc_pattern = r'/\*\*(.*?)\*/'
        javadocs = re.findall(javadoc_pattern, source, re.DOTALL)
        
        for javadoc in javadocs:
            # Look for @tag patterns in JavaDoc
            tag_pattern = r'@(\w+):([^\s]+)'
            matches = re.findall(tag_pattern, javadoc)
            for system, external_id in matches:
                tags.append(f"{system}:{external_id}")
        
        return tags


class PytestExternalTestCaseExtractor(ExternalTestCaseExtractor):
    """
    Extractor for pytest tests.
    """
    
    # pytest-specific patterns
    PYTEST_MARKER_PATTERNS = [
        # @pytest.mark.testrail("C12345")
        AnnotationPattern(
            pattern=r'@pytest\.mark\.testrail\s*\(\s*["\']([^"\']+)["\']\s*\)',
            system="testrail"
        ),
        # @pytest.mark.external_id("C12345")
        AnnotationPattern(
            pattern=r'@pytest\.mark\.external_id\s*\(\s*["\']([^"\']+)["\']\s*\)',
            system="testrail"  # Default
        ),
    ]
    
    def __init__(self):
        super().__init__()
        self.ANNOTATION_PATTERNS = (
            self.ANNOTATION_PATTERNS + self.PYTEST_MARKER_PATTERNS
        )
    
    def extract_from_pytest_file(self, file_path: str) -> List[ExternalTestRef]:
        """
        Extract external test case refs from pytest file.
        
        Args:
            file_path: Path to pytest file
            
        Returns:
            List of ExternalTestRef objects
        """
        refs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Extract from pytest.mark decorators
        for pattern_obj in self.PYTEST_MARKER_PATTERNS:
            matches = re.findall(pattern_obj.pattern, source)
            for external_id in matches:
                refs.append(ExternalTestRef(
                    system=pattern_obj.system,
                    external_id=external_id,
                    source="annotation"
                ))
        
        # Also extract from other annotations
        annotations = self._extract_annotations(source)
        refs.extend(self.extract_from_annotations(annotations))
        
        return refs


class RobotFrameworkExternalTestCaseExtractor(ExternalTestCaseExtractor):
    """
    Extractor for Robot Framework tests.
    """
    
    def extract_from_robot_file(self, file_path: str) -> List[ExternalTestRef]:
        """
        Extract external test case refs from Robot Framework file.
        
        Args:
            file_path: Path to .robot file
            
        Returns:
            List of ExternalTestRef objects
        """
        refs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Robot Framework uses [Tags] section
        # Example: [Tags]    testrail:C12345    smoke
        tags_pattern = r'\[Tags\]\s+([^\n]+)'
        matches = re.findall(tags_pattern, content, re.IGNORECASE)
        
        for tag_line in matches:
            # Split by whitespace
            tags = tag_line.split()
            refs.extend(self.extract_from_tags(tags))
        
        return refs


class CucumberExternalTestCaseExtractor(ExternalTestCaseExtractor):
    """
    Extractor for Cucumber/Gherkin tests.
    """
    
    def extract_from_feature_file(self, file_path: str) -> List[ExternalTestRef]:
        """
        Extract external test case refs from Cucumber feature file.
        
        Args:
            file_path: Path to .feature file
            
        Returns:
            List of ExternalTestRef objects
        """
        refs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cucumber uses @tags before scenarios
        # Example: @testrail:C12345 @smoke
        tag_pattern = r'@([^\s]+)'
        tags = re.findall(tag_pattern, content)
        
        refs.extend(self.extract_from_tags(tags))
        
        return refs


class ExternalTestCaseExtractorFactory:
    """
    Factory for creating appropriate extractors based on framework.
    """
    
    _extractors = {
        'java': JavaExternalTestCaseExtractor,
        'junit': JavaExternalTestCaseExtractor,
        'testng': JavaExternalTestCaseExtractor,
        'pytest': PytestExternalTestCaseExtractor,
        'robot': RobotFrameworkExternalTestCaseExtractor,
        'cucumber': CucumberExternalTestCaseExtractor,
        'gherkin': CucumberExternalTestCaseExtractor,
    }
    
    @classmethod
    def get_extractor(cls, framework: str) -> ExternalTestCaseExtractor:
        """
        Get extractor for framework.
        
        Args:
            framework: Framework name (java, pytest, robot, cucumber)
            
        Returns:
            ExternalTestCaseExtractor instance
        """
        framework_lower = framework.lower()
        extractor_class = cls._extractors.get(framework_lower)
        
        if not extractor_class:
            # Return base extractor as fallback
            return ExternalTestCaseExtractor()
        
        return extractor_class()


# Convenience functions

def extract_external_refs_from_test(
    test_source: str,
    tags: List[str],
    framework: str = "java"
) -> List[ExternalTestRef]:
    """
    Extract external test case refs from test source and tags.
    
    Args:
        test_source: Test source code
        tags: List of tags
        framework: Framework name
        
    Returns:
        List of ExternalTestRef objects
    """
    extractor = ExternalTestCaseExtractorFactory.get_extractor(framework)
    return extractor.extract_from_test(test_source, tags)


def extract_external_refs_from_file(
    file_path: str,
    framework: str = "java"
) -> List[ExternalTestRef]:
    """
    Extract external test case refs from file.
    
    Args:
        file_path: Path to test file
        framework: Framework name
        
    Returns:
        List of ExternalTestRef objects
    """
    extractor = ExternalTestCaseExtractorFactory.get_extractor(framework)
    
    if framework.lower() in ['java', 'junit', 'testng']:
        return extractor.extract_from_java_file(file_path)
    elif framework.lower() == 'pytest':
        return extractor.extract_from_pytest_file(file_path)
    elif framework.lower() == 'robot':
        return extractor.extract_from_robot_file(file_path)
    elif framework.lower() in ['cucumber', 'gherkin']:
        return extractor.extract_from_feature_file(file_path)
    else:
        # Generic extraction
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        return extractor.extract_from_test(source, [])
