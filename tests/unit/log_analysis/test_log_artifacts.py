"""
Unit Tests for Log Artifacts

Tests log artifact data models and validation.
"""

import pytest
from pathlib import Path
import tempfile

from core.log_analysis.ingestion import (
    LogArtifacts,
    StructuredFailure,
    FailureCategory
)


class TestLogArtifacts:
    """Test LogArtifacts data model"""
    
    def test_basic_creation(self, tmp_path):
        """Test creating basic log artifacts"""
        artifacts = LogArtifacts(
            testng_xml_path=tmp_path / "testng-results.xml",
            framework_log_path=tmp_path / "framework.log"
        )
        
        assert artifacts.testng_xml_path is not None
        assert artifacts.framework_log_path is not None
        assert len(artifacts.driver_log_paths) == 0
    
    def test_path_conversion(self, tmp_path):
        """Test automatic path conversion"""
        artifacts = LogArtifacts(
            testng_xml_path=str(tmp_path / "test.xml")
        )
        
        # Should convert string to Path
        assert isinstance(artifacts.testng_xml_path, Path)
    
    def test_driver_logs_conversion(self, tmp_path):
        """Test driver log paths conversion"""
        artifacts = LogArtifacts(
            driver_log_paths=[
                str(tmp_path / "chrome.log"),
                str(tmp_path / "firefox.log")
            ]
        )
        
        assert len(artifacts.driver_log_paths) == 2
        assert all(isinstance(p, Path) for p in artifacts.driver_log_paths)
    
    def test_validate_with_existing_files(self, tmp_path):
        """Test validation with existing files"""
        # Create actual files
        testng_file = tmp_path / "testng-results.xml"
        testng_file.write_text("<testng-results></testng-results>")
        
        framework_file = tmp_path / "framework.log"
        framework_file.write_text("Log content")
        
        artifacts = LogArtifacts(
            testng_xml_path=testng_file,
            framework_log_path=framework_file
        )
        
        assert artifacts.validate()
    
    def test_validate_with_nonexistent_files(self, tmp_path):
        """Test validation with nonexistent files"""
        artifacts = LogArtifacts(
            testng_xml_path=tmp_path / "does-not-exist.xml",
            framework_log_path=tmp_path / "does-not-exist.log"
        )
        
        assert not artifacts.validate()
    
    def test_validate_with_mixed_files(self, tmp_path):
        """Test validation with some existing files"""
        testng_file = tmp_path / "testng-results.xml"
        testng_file.write_text("<testng-results></testng-results>")
        
        artifacts = LogArtifacts(
            testng_xml_path=testng_file,
            framework_log_path=tmp_path / "does-not-exist.log"
        )
        
        # Should validate true if at least one exists
        assert artifacts.validate()
    
    def test_available_sources_all(self, tmp_path):
        """Test available sources with all logs"""
        # Create all files
        testng_file = tmp_path / "testng.xml"
        testng_file.write_text("<testng-results></testng-results>")
        
        framework_file = tmp_path / "framework.log"
        framework_file.write_text("logs")
        
        driver_file = tmp_path / "driver.log"
        driver_file.write_text("driver logs")
        
        artifacts = LogArtifacts(
            testng_xml_path=testng_file,
            framework_log_path=framework_file,
            driver_log_paths=[driver_file]
        )
        
        sources = artifacts.available_sources()
        assert len(sources) == 3
        assert "testng_xml" in sources
        assert "framework_log" in sources
        assert "driver_logs" in sources
    
    def test_available_sources_partial(self, tmp_path):
        """Test available sources with some logs"""
        testng_file = tmp_path / "testng.xml"
        testng_file.write_text("<testng-results></testng-results>")
        
        artifacts = LogArtifacts(
            testng_xml_path=testng_file,
            framework_log_path=tmp_path / "does-not-exist.log"
        )
        
        sources = artifacts.available_sources()
        assert len(sources) == 1
        assert "testng_xml" in sources


class TestStructuredFailure:
    """Test StructuredFailure data model"""
    
    def test_basic_creation(self):
        """Test creating basic structured failure"""
        failure = StructuredFailure(
            test_name="com.example.Test.testMethod",
            class_name="com.example.Test",
            method_name="testMethod",
            status="FAIL"
        )
        
        assert failure.test_name == "com.example.Test.testMethod"
        assert failure.class_name == "com.example.Test"
        assert failure.method_name == "testMethod"
        assert failure.status == "FAIL"
        assert failure.category == FailureCategory.UNKNOWN
    
    def test_is_passed(self):
        """Test is_passed() method"""
        passed = StructuredFailure(
            test_name="test",
            class_name="Test",
            status="PASS"
        )
        assert passed.is_passed()
        
        failed = StructuredFailure(
            test_name="test",
            class_name="Test",
            status="FAIL"
        )
        assert not failed.is_passed()
    
    def test_is_failed(self):
        """Test is_failed() method"""
        failed = StructuredFailure(
            test_name="test",
            class_name="Test",
            status="FAIL"
        )
        assert failed.is_failed()
        
        error = StructuredFailure(
            test_name="test",
            class_name="Test",
            status="ERROR"
        )
        assert error.is_failed()
        
        passed = StructuredFailure(
            test_name="test",
            class_name="Test",
            status="PASS"
        )
        assert not passed.is_passed() or not passed.is_failed()
    
    def test_is_skipped(self):
        """Test is_skipped() method"""
        skipped = StructuredFailure(
            test_name="test",
            class_name="Test",
            status="SKIP"
        )
        assert skipped.is_skipped()
        
        failed = StructuredFailure(
            test_name="test",
            class_name="Test",
            status="FAIL"
        )
        assert not failed.is_skipped()
    
    def test_short_error_single_line(self):
        """Test short_error() with single line"""
        failure = StructuredFailure(
            test_name="test",
            class_name="Test",
            error_message="Short error"
        )
        
        assert failure.short_error() == "Short error"
    
    def test_short_error_multiline(self):
        """Test short_error() with multiple lines"""
        failure = StructuredFailure(
            test_name="test",
            class_name="Test",
            error_message="First line\nSecond line\nThird line"
        )
        
        assert failure.short_error() == "First line"
    
    def test_short_error_truncation(self):
        """Test short_error() truncation"""
        long_message = "a" * 150  # More than 100 chars
        failure = StructuredFailure(
            test_name="test",
            class_name="Test",
            error_message=long_message
        )
        
        short = failure.short_error()
        assert len(short) == 100
    
    def test_short_error_empty(self):
        """Test short_error() with no message"""
        failure = StructuredFailure(
            test_name="test",
            class_name="Test"
        )
        
        assert failure.short_error() == ""
    
    def test_failure_with_all_fields(self):
        """Test failure with all fields populated"""
        failure = StructuredFailure(
            test_name="com.example.Test.testMethod",
            class_name="com.example.Test",
            method_name="testMethod",
            status="FAIL",
            failure_type="AssertionError",
            error_message="Expected true but was false",
            stack_trace="at Test.testMethod(Test.java:10)",
            duration_ms=1500,
            timestamp="2024-01-15T10:00:00",
            category=FailureCategory.TEST_ASSERTION,
            infra_related=False,
            test_group="Smoke Tests",
            parameters="param1=value1"
        )
        
        assert failure.test_name == "com.example.Test.testMethod"
        assert failure.failure_type == "AssertionError"
        assert failure.duration_ms == 1500
        assert failure.category == FailureCategory.TEST_ASSERTION
        assert not failure.infra_related
        assert failure.test_group == "Smoke Tests"


class TestFailureCategory:
    """Test FailureCategory enum"""
    
    def test_all_categories_defined(self):
        """Test all expected categories are defined"""
        categories = [
            FailureCategory.TEST_ASSERTION,
            FailureCategory.INFRASTRUCTURE,
            FailureCategory.ENVIRONMENT,
            FailureCategory.APPLICATION,
            FailureCategory.FLAKY,
            FailureCategory.UNKNOWN,
        ]
        
        assert len(categories) == 6
    
    def test_category_string_values(self):
        """Test category string values"""
        assert FailureCategory.TEST_ASSERTION == "test_assertion"
        assert FailureCategory.INFRASTRUCTURE == "infrastructure"
        assert FailureCategory.ENVIRONMENT == "environment"
        assert FailureCategory.APPLICATION == "application"
        assert FailureCategory.FLAKY == "flaky"
        assert FailureCategory.UNKNOWN == "unknown"
