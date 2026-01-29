"""
Test Template for CrossBridge Adapters

This module provides a standardized test template and utilities for testing
framework adapters. Ensures consistent test coverage across all adapters.
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from adapters.common.base import TestFrameworkAdapter
from adapters.common.models import TestMetadata, PageObjectMetadata


class AdapterTestTemplate(ABC):
    """
    Abstract base class for adapter tests.
    
    Inherit from this class to create tests for a specific adapter.
    Implements standard test scenarios that all adapters must pass.
    """
    
    @abstractmethod
    def get_adapter(self) -> TestFrameworkAdapter:
        """Return the adapter instance to test."""
        pass
    
    @abstractmethod
    def get_sample_test_file(self) -> Path:
        """Return path to a sample test file for this framework."""
        pass
    
    @abstractmethod
    def get_sample_page_object_file(self) -> Path:
        """Return path to a sample page object file for this framework."""
        pass
    
    @abstractmethod
    def get_expected_test_count(self) -> int:
        """Return expected number of tests in sample file."""
        pass
    
    @abstractmethod
    def get_expected_page_object_count(self) -> int:
        """Return expected number of page objects in sample file."""
        pass
    
    # Standard test methods that all adapters must pass
    
    def test_adapter_initialization(self):
        """Test adapter can be initialized."""
        adapter = self.get_adapter()
        assert adapter is not None
        assert hasattr(adapter, 'detect_framework')
        assert hasattr(adapter, 'extract_tests')
        assert hasattr(adapter, 'extract_page_objects')
    
    def test_framework_detection(self):
        """Test adapter correctly detects its framework."""
        adapter = self.get_adapter()
        test_file = self.get_sample_test_file()
        
        is_detected = adapter.detect_framework(str(test_file))
        assert is_detected, f"Failed to detect framework in {test_file}"
    
    def test_framework_detection_negative(self, tmp_path):
        """Test adapter rejects non-framework files."""
        adapter = self.get_adapter()
        
        # Create a Python file that's NOT from this framework
        wrong_file = tmp_path / "not_a_test.py"
        wrong_file.write_text("print('Hello World')\n")
        
        is_detected = adapter.detect_framework(str(wrong_file))
        assert not is_detected, "False positive: detected framework where none exists"
    
    def test_extract_tests(self):
        """Test extraction of tests from sample file."""
        adapter = self.get_adapter()
        test_file = self.get_sample_test_file()
        
        tests = adapter.extract_tests(str(test_file))
        
        assert isinstance(tests, list), "extract_tests must return a list"
        assert len(tests) == self.get_expected_test_count(), \
            f"Expected {self.get_expected_test_count()} tests, got {len(tests)}"
        
        # Validate each test metadata
        for test in tests:
            assert isinstance(test, TestMetadata), "Each test must be TestMetadata"
            assert test.test_name, "Test name must not be empty"
            assert test.file_path, "File path must not be empty"
    
    def test_extract_tests_empty_file(self, tmp_path):
        """Test extraction from empty file returns empty list."""
        adapter = self.get_adapter()
        
        empty_file = tmp_path / "empty_test.py"
        empty_file.write_text("")
        
        tests = adapter.extract_tests(str(empty_file))
        assert tests == [], "Empty file should return empty list"
    
    def test_extract_tests_invalid_file(self):
        """Test extraction from non-existent file raises exception."""
        adapter = self.get_adapter()
        
        with pytest.raises((FileNotFoundError, IOError)):
            adapter.extract_tests("/nonexistent/file.py")
    
    def test_extract_page_objects(self):
        """Test extraction of page objects from sample file."""
        adapter = self.get_adapter()
        po_file = self.get_sample_page_object_file()
        
        page_objects = adapter.extract_page_objects(str(po_file))
        
        assert isinstance(page_objects, list), "extract_page_objects must return a list"
        assert len(page_objects) == self.get_expected_page_object_count(), \
            f"Expected {self.get_expected_page_object_count()} page objects, got {len(page_objects)}"
        
        # Validate each page object metadata
        for po in page_objects:
            assert isinstance(po, PageObjectMetadata), "Each PO must be PageObjectMetadata"
            assert po.name, "Page object name must not be empty"
            assert po.file_path, "File path must not be empty"
    
    def test_test_metadata_completeness(self):
        """Test that extracted test metadata is complete."""
        adapter = self.get_adapter()
        test_file = self.get_sample_test_file()
        
        tests = adapter.extract_tests(str(test_file))
        
        for test in tests:
            # Required fields
            assert test.test_name is not None
            assert test.file_path is not None
            assert test.framework is not None
            
            # Fields should have reasonable values
            assert len(test.test_name) > 0
            assert len(test.file_path) > 0
            assert len(test.framework) > 0
    
    def test_page_object_metadata_completeness(self):
        """Test that extracted page object metadata is complete."""
        adapter = self.get_adapter()
        po_file = self.get_sample_page_object_file()
        
        page_objects = adapter.extract_page_objects(str(po_file))
        
        for po in page_objects:
            # Required fields
            assert po.name is not None
            assert po.file_path is not None
            
            # Fields should have reasonable values
            assert len(po.name) > 0
            assert len(po.file_path) > 0
    
    def test_adapter_supports_observation_mode(self):
        """Test adapter supports sidecar observation mode."""
        adapter = self.get_adapter()
        
        # Adapter should have hooks or observers
        assert hasattr(adapter, 'register_observer') or \
               hasattr(adapter, 'attach_hooks'), \
               "Adapter must support observation mode"
    
    def test_adapter_framework_name(self):
        """Test adapter reports correct framework name."""
        adapter = self.get_adapter()
        
        assert hasattr(adapter, 'framework_name')
        assert isinstance(adapter.framework_name, str)
        assert len(adapter.framework_name) > 0


class TestCoverageMetrics:
    """Utilities for measuring and reporting test coverage for adapters."""
    
    @staticmethod
    def calculate_adapter_coverage(adapter_name: str) -> Dict[str, Any]:
        """
        Calculate test coverage metrics for an adapter.
        
        Args:
            adapter_name: Name of adapter (e.g., 'playwright', 'selenium_pytest')
            
        Returns:
            Dictionary with coverage metrics
        """
        # This is a placeholder - integrate with actual coverage tools
        return {
            'adapter': adapter_name,
            'test_files': 0,
            'test_count': 0,
            'coverage_percent': 0.0,
            'missing_tests': [],
        }
    
    @staticmethod
    def generate_coverage_report(adapters: List[str]) -> str:
        """
        Generate a text-based coverage report for multiple adapters.
        
        Args:
            adapters: List of adapter names
            
        Returns:
            Formatted coverage report
        """
        report = ["CrossBridge Adapter Test Coverage Report", "=" * 60, ""]
        
        for adapter in adapters:
            metrics = TestCoverageMetrics.calculate_adapter_coverage(adapter)
            report.append(f"Adapter: {adapter}")
            report.append(f"  Test Files: {metrics['test_files']}")
            report.append(f"  Test Count: {metrics['test_count']}")
            report.append(f"  Coverage: {metrics['coverage_percent']:.1f}%")
            report.append("")
        
        return "\n".join(report)


# Example usage for pytest adapter
class TestPytestAdapter(AdapterTestTemplate):
    """Tests for pytest adapter."""
    
    def get_adapter(self):
        from adapters.selenium_pytest.adapter import SeleniumPytestAdapter
        return SeleniumPytestAdapter()
    
    def get_sample_test_file(self) -> Path:
        return Path(__file__).parent / "fixtures" / "sample_pytest_test.py"
    
    def get_sample_page_object_file(self) -> Path:
        return Path(__file__).parent / "fixtures" / "sample_pytest_page.py"
    
    def get_expected_test_count(self) -> int:
        return 3  # Adjust based on fixture
    
    def get_expected_page_object_count(self) -> int:
        return 1  # Adjust based on fixture


# Pytest configuration
def pytest_generate_tests(metafunc):
    """Generate test cases for all adapters."""
    if "adapter_class" in metafunc.fixturenames:
        # List all adapter test classes
        adapter_test_classes = [
            # Add your adapter test classes here
            # TestPlaywrightAdapter,
            # TestSeleniumAdapter,
            # TestRobotAdapter,
            # etc.
        ]
        metafunc.parametrize("adapter_class", adapter_test_classes)
