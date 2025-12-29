"""
Neutral test model for Java test frameworks.

Provides a framework-agnostic representation of Java test cases
that works uniformly across JUnit 4, JUnit 5, and TestNG.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class JavaTestFramework(Enum):
    """Java test framework types."""
    JUNIT4 = "junit4"
    JUNIT5 = "junit5"
    TESTNG = "testng"
    UNKNOWN = "unknown"


@dataclass
class JavaAnnotation:
    """
    Represents a Java annotation.
    
    Attributes:
        name: Annotation name (e.g., "Test", "DisplayName", "Tag")
        attributes: Key-value pairs of annotation attributes
    """
    name: str
    attributes: dict = field(default_factory=dict)
    
    def __str__(self):
        if not self.attributes:
            return f"@{self.name}"
        attrs = ", ".join(f"{k}={v}" for k, v in self.attributes.items())
        return f"@{self.name}({attrs})"


@dataclass
class JavaTestMethod:
    """
    Represents a single test method.
    
    Attributes:
        method_name: Name of the test method
        annotations: List of annotations on the method
        tags: Extracted tags/groups (from @Tag, @Category, @Groups)
        line_number: Starting line number in source file
        is_parameterized: Whether this is a parameterized test
        is_disabled: Whether the test is disabled/ignored
    """
    method_name: str
    annotations: List[JavaAnnotation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    line_number: Optional[int] = None
    is_parameterized: bool = False
    is_disabled: bool = False
    
    def get_annotation(self, name: str) -> Optional[JavaAnnotation]:
        """Get annotation by name."""
        for ann in self.annotations:
            if ann.name == name:
                return ann
        return None
    
    def has_annotation(self, name: str) -> bool:
        """Check if method has specific annotation."""
        return any(ann.name == name for ann in self.annotations)


@dataclass
class JavaTestClass:
    """
    Represents a test class.
    
    Attributes:
        class_name: Name of the test class
        package: Package name
        file_path: Absolute path to the source file
        framework: Detected framework (junit4, junit5, testng)
        test_methods: List of test methods in the class
        annotations: Class-level annotations
        tags: Class-level tags
        imports: Import statements (for framework detection)
    """
    class_name: str
    package: str
    file_path: str
    framework: JavaTestFramework
    test_methods: List[JavaTestMethod] = field(default_factory=list)
    annotations: List[JavaAnnotation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    
    def get_qualified_name(self) -> str:
        """Get fully qualified class name."""
        return f"{self.package}.{self.class_name}" if self.package else self.class_name
    
    def get_test_count(self) -> int:
        """Get number of test methods."""
        return len(self.test_methods)
    
    def get_annotation(self, name: str) -> Optional[JavaAnnotation]:
        """Get class-level annotation by name."""
        for ann in self.annotations:
            if ann.name == name:
                return ann
        return None


@dataclass
class JavaTestCase:
    """
    Represents a single executable test case (method within a class).
    
    This is the neutral representation used throughout CrossBridge AI.
    Maps to TestMetadata for the common adapter interface.
    
    Attributes:
        framework: Test framework (junit | testng)
        package: Package name
        class_name: Test class name
        method_name: Test method name
        annotations: All annotations on the method
        tags: Extracted tags/groups
        file_path: Source file path
        line_number: Line number of the test method
        is_parameterized: Whether this is a data-driven test
        is_disabled: Whether the test is disabled
    """
    framework: str  # "junit4", "junit5", "testng"
    package: str
    class_name: str
    method_name: str
    annotations: List[str]
    tags: List[str]
    file_path: str
    line_number: Optional[int] = None
    is_parameterized: bool = False
    is_disabled: bool = False
    
    def get_full_name(self) -> str:
        """Get fully qualified test name: package.Class.method"""
        if self.package:
            return f"{self.package}.{self.class_name}.{self.method_name}"
        return f"{self.class_name}.{self.method_name}"
    
    def get_display_name(self) -> str:
        """Get display name: Class.method"""
        return f"{self.class_name}.{self.method_name}"
    
    def to_test_metadata(self):
        """Convert to TestMetadata for CrossBridge adapter interface."""
        from adapters.common.models import TestMetadata
        
        # Determine test type based on tags
        test_type = "ui"  # Default for selenium-java
        if any(tag in ["unit", "integration", "api"] for tag in self.tags):
            test_type = "integration" if "integration" in self.tags else "unit"
        
        return TestMetadata(
            framework=f"selenium-java-{self.framework}",
            test_name=self.get_display_name(),
            file_path=self.file_path,
            tags=self.tags,
            test_type=test_type,
            language="java"
        )
    
    @classmethod
    def from_test_class(cls, test_class: JavaTestClass, method: JavaTestMethod) -> "JavaTestCase":
        """Create JavaTestCase from JavaTestClass and JavaTestMethod."""
        # Extract annotation names
        annotation_names = [ann.name for ann in method.annotations]
        
        # Combine class-level and method-level tags
        all_tags = list(set(test_class.tags + method.tags))
        
        return cls(
            framework=test_class.framework.value,
            package=test_class.package,
            class_name=test_class.class_name,
            method_name=method.method_name,
            annotations=annotation_names,
            tags=all_tags,
            file_path=test_class.file_path,
            line_number=method.line_number,
            is_parameterized=method.is_parameterized,
            is_disabled=method.is_disabled
        )
