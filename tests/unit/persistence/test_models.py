"""
Unit tests for persistence models and data conversion.

Tests cover:
- Model instantiation
- Conversion from adapter models
- Edge cases and validation
"""

import pytest
from datetime import datetime
import uuid
from persistence.models import (
    DiscoveryRun,
    TestCase,
    PageObject,
    TestPageMapping,
    DiscoveryTestCase,
    from_test_metadata,
    from_page_object_reference
)
from adapters.common.models import TestMetadata


class TestDiscoveryRunModel:
    """Test DiscoveryRun model."""
    
    def test_create_discovery_run(self):
        """Test creating a discovery run."""
        run = DiscoveryRun(
            project_name="my-project",
            git_commit="abc123",
            git_branch="main",
            triggered_by="cli"
        )
        
        assert run.project_name == "my-project"
        assert run.git_commit == "abc123"
        assert run.git_branch == "main"
        assert run.triggered_by == "cli"
        assert isinstance(run.id, uuid.UUID)
        assert isinstance(run.created_at, datetime)
    
    def test_discovery_run_defaults(self):
        """Test discovery run with defaults."""
        run = DiscoveryRun(project_name="my-project")
        
        assert run.project_name == "my-project"
        assert run.triggered_by == "cli"  # Default
        assert run.git_commit is None
        assert run.git_branch is None


class TestTestCaseModel:
    """Test TestCase model."""
    
    def test_create_test_case(self):
        """Test creating a test case."""
        test = TestCase(
            framework="junit5",
            package="com.example",
            class_name="LoginTest",
            method_name="testValidLogin",
            file_path="src/test/java/LoginTest.java",
            tags=["smoke"]
        )
        
        assert test.framework == "junit5"
        assert test.package == "com.example"
        assert test.class_name == "LoginTest"
        assert test.method_name == "testValidLogin"
        assert test.file_path == "src/test/java/LoginTest.java"
        assert test.tags == ["smoke"]
        assert isinstance(test.id, uuid.UUID)
    
    def test_test_case_full_name(self):
        """Test full_name property."""
        test = TestCase(
            framework="junit5",
            class_name="LoginTest",
            method_name="testValidLogin",
            file_path="test.java"
        )
        
        assert test.full_name == "LoginTest.testValidLogin"
    
    def test_test_case_full_name_no_class(self):
        """Test full_name without class name."""
        test = TestCase(
            framework="pytest",
            method_name="test_login",
            file_path="test.py"
        )
        
        assert test.full_name == "test_login"


class TestPageObjectModel:
    """Test PageObject model."""
    
    def test_create_page_object(self):
        """Test creating a page object."""
        page = PageObject(
            name="LoginPage",
            file_path="src/main/java/pages/LoginPage.java",
            framework="selenium",
            package="com.example.pages"
        )
        
        assert page.name == "LoginPage"
        assert page.file_path == "src/main/java/pages/LoginPage.java"
        assert page.framework == "selenium"
        assert page.package == "com.example.pages"
        assert isinstance(page.id, uuid.UUID)


class TestTestPageMappingModel:
    """Test TestPageMapping model."""
    
    def test_create_mapping(self):
        """Test creating a test-page mapping."""
        test_id = uuid.uuid4()
        page_id = uuid.uuid4()
        run_id = uuid.uuid4()
        
        mapping = TestPageMapping(
            test_case_id=test_id,
            page_object_id=page_id,
            source="static_ast",
            discovery_run_id=run_id,
            confidence=0.95
        )
        
        assert mapping.test_case_id == test_id
        assert mapping.page_object_id == page_id
        assert mapping.source == "static_ast"
        assert mapping.discovery_run_id == run_id
        assert mapping.confidence == 0.95
        assert isinstance(mapping.id, uuid.UUID)
    
    def test_mapping_default_confidence(self):
        """Test default confidence value."""
        mapping = TestPageMapping(
            test_case_id=uuid.uuid4(),
            page_object_id=uuid.uuid4(),
            source="manual",
            discovery_run_id=uuid.uuid4()
        )
        
        assert mapping.confidence == 1.0


class TestConversionHelpers:
    """Test conversion helpers for adapter models."""
    
    def test_from_test_metadata_with_class(self):
        """Test converting TestMetadata with class name."""
        metadata = TestMetadata(
            framework="selenium-java-junit5",
            test_name="LoginTest.testValidLogin",
            file_path="src/test/java/LoginTest.java",
            tags=["smoke", "regression"]
        )
        
        test_case = from_test_metadata(metadata)
        
        assert test_case.framework == "junit5"
        assert test_case.class_name == "LoginTest"
        assert test_case.method_name == "testValidLogin"
        assert test_case.file_path == "src/test/java/LoginTest.java"
        assert test_case.tags == ["smoke", "regression"]
    
    def test_from_test_metadata_with_package(self):
        """Test converting TestMetadata with package prefix."""
        metadata = TestMetadata(
            framework="selenium-java-junit5",
            test_name="com.example.LoginTest.testValidLogin",
            file_path="src/test/java/com/example/LoginTest.java",
            tags=[]
        )
        
        test_case = from_test_metadata(metadata)
        
        assert test_case.package == "com.example"
        assert test_case.class_name == "LoginTest"
        assert test_case.method_name == "testValidLogin"
    
    def test_from_test_metadata_no_class(self):
        """Test converting TestMetadata without class name."""
        metadata = TestMetadata(
            framework="pytest",
            test_name="test_login",
            file_path="tests/test_login.py",
            tags=[]
        )
        
        test_case = from_test_metadata(metadata, framework_hint="pytest")
        
        assert test_case.framework == "pytest"
        assert test_case.class_name is None
        assert test_case.method_name == "test_login"
    
    def test_from_test_metadata_framework_hint(self):
        """Test using framework_hint."""
        metadata = TestMetadata(
            framework="custom-framework",
            test_name="testMethod",
            file_path="test.java",
            tags=[]
        )
        
        test_case = from_test_metadata(metadata, framework_hint="junit4")
        
        assert test_case.framework == "junit4"
    
    def test_from_page_object_reference_simple(self):
        """Test converting simple page object reference."""
        page = from_page_object_reference(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            framework="selenium"
        )
        
        assert page.name == "LoginPage"
        assert page.file_path == "pages/LoginPage.java"
        assert page.framework == "selenium"
        assert page.package is None
    
    def test_from_page_object_reference_with_package(self):
        """Test converting page object reference with package."""
        page = from_page_object_reference(
            name="com.example.pages.LoginPage",
            file_path="pages/LoginPage.java"
        )
        
        assert page.name == "LoginPage"
        assert page.package == "com.example.pages"
        assert page.file_path == "pages/LoginPage.java"


class TestEdgeCases:
    """Test edge cases in models."""
    
    def test_test_case_empty_tags(self):
        """Test test case with empty tags list."""
        test = TestCase(
            framework="junit5",
            method_name="testMethod",
            file_path="test.java",
            tags=[]
        )
        
        assert test.tags == []
    
    def test_page_object_no_framework(self):
        """Test page object without framework."""
        page = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java"
        )
        
        assert page.framework is None
        assert page.package is None
    
    def test_mapping_with_metadata(self):
        """Test mapping with additional metadata."""
        mapping = TestPageMapping(
            test_case_id=uuid.uuid4(),
            page_object_id=uuid.uuid4(),
            source="ai",
            discovery_run_id=uuid.uuid4(),
            confidence=0.85,
            metadata={"model": "gpt-4", "reasoning": "High similarity"}
        )
        
        assert mapping.metadata == {"model": "gpt-4", "reasoning": "High similarity"}
    
    def test_discovery_run_with_metadata(self):
        """Test discovery run with metadata."""
        run = DiscoveryRun(
            project_name="my-project",
            metadata={"environment": "ci", "build": "123"}
        )
        
        assert run.metadata == {"environment": "ci", "build": "123"}


class TestContractStability:
    """Test that model contracts remain stable."""
    
    def test_test_case_has_required_attributes(self):
        """Test TestCase has all required attributes."""
        test = TestCase(
            framework="junit5",
            method_name="test",
            file_path="test.java"
        )
        
        assert hasattr(test, "id")
        assert hasattr(test, "framework")
        assert hasattr(test, "method_name")
        assert hasattr(test, "file_path")
        assert hasattr(test, "package")
        assert hasattr(test, "class_name")
        assert hasattr(test, "tags")
        assert hasattr(test, "created_at")
        assert hasattr(test, "updated_at")
    
    def test_page_object_has_required_attributes(self):
        """Test PageObject has all required attributes."""
        page = PageObject(name="Page", file_path="page.java")
        
        assert hasattr(page, "id")
        assert hasattr(page, "name")
        assert hasattr(page, "file_path")
        assert hasattr(page, "framework")
        assert hasattr(page, "package")
        assert hasattr(page, "created_at")
        assert hasattr(page, "updated_at")
    
    def test_mapping_has_required_attributes(self):
        """Test TestPageMapping has all required attributes."""
        mapping = TestPageMapping(
            test_case_id=uuid.uuid4(),
            page_object_id=uuid.uuid4(),
            source="static_ast",
            discovery_run_id=uuid.uuid4()
        )
        
        assert hasattr(mapping, "id")
        assert hasattr(mapping, "test_case_id")
        assert hasattr(mapping, "page_object_id")
        assert hasattr(mapping, "source")
        assert hasattr(mapping, "confidence")
        assert hasattr(mapping, "discovery_run_id")
        assert hasattr(mapping, "created_at")
        assert hasattr(mapping, "metadata")
