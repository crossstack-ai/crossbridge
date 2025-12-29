"""
Data models for persistence layer.

Simple dataclasses that map to database tables.
These are separate from adapter models to maintain separation of concerns.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import uuid


@dataclass
class DiscoveryRun:
    """Represents a test discovery run."""
    project_name: str
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    triggered_by: str = "cli"  # cli | ci | jira | manual
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


@dataclass
class TestCase:
    """Represents a discovered test case."""
    framework: str  # junit | testng | pytest | robot
    method_name: str
    file_path: str
    package: Optional[str] = None
    class_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def full_name(self) -> str:
        """Get fully qualified test name."""
        if self.class_name:
            return f"{self.class_name}.{self.method_name}"
        return self.method_name


@dataclass
class PageObject:
    """Represents a discovered page object."""
    name: str
    file_path: str
    framework: Optional[str] = None
    package: Optional[str] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestPageMapping:
    """Represents a test-to-page-object relationship."""
    test_case_id: uuid.UUID
    page_object_id: uuid.UUID
    source: str  # static_ast | coverage | ai | manual
    discovery_run_id: uuid.UUID
    confidence: float = 1.0  # 0.0 to 1.0
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


@dataclass
class DiscoveryTestCase:
    """Links a test case to a discovery run."""
    discovery_run_id: uuid.UUID
    test_case_id: uuid.UUID
    created_at: datetime = field(default_factory=datetime.utcnow)


# Conversion helpers for adapter models

def from_test_metadata(metadata, framework_hint: Optional[str] = None) -> TestCase:
    """
    Convert from adapters.common.models.TestMetadata to persistence TestCase.
    
    Args:
        metadata: TestMetadata from extractor
        framework_hint: Optional framework name if not in metadata
        
    Returns:
        TestCase ready for persistence
    """
    # Parse test_name to extract class and method
    test_name = metadata.test_name
    package = None
    class_name = None
    method_name = test_name
    
    # Try to parse ClassName.methodName format
    if '.' in test_name:
        parts = test_name.rsplit('.', 1)
        if len(parts) == 2:
            class_name = parts[0]
            method_name = parts[1]
            
            # Check if class_name has package prefix
            if '.' in class_name:
                class_parts = class_name.rsplit('.', 1)
                package = class_parts[0]
                class_name = class_parts[1]
    
    framework = framework_hint or metadata.framework.replace('selenium-java-', '')
    
    return TestCase(
        framework=framework,
        package=package,
        class_name=class_name,
        method_name=method_name,
        file_path=metadata.file_path,
        tags=metadata.tags
    )


def from_page_object_reference(name: str, file_path: str, framework: Optional[str] = None) -> PageObject:
    """
    Create PageObject from reference in test code.
    
    Args:
        name: PageObject class name
        file_path: File path where referenced
        framework: Optional framework name
        
    Returns:
        PageObject ready for persistence
    """
    # Try to extract package from name if it's fully qualified
    package = None
    simple_name = name
    
    if '.' in name:
        parts = name.rsplit('.', 1)
        package = parts[0]
        simple_name = parts[1]
    
    return PageObject(
        name=simple_name,
        file_path=file_path,
        framework=framework,
        package=package
    )
