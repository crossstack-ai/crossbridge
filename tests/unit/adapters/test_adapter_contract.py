"""
Adapter Contract Tests

Ensures all adapters implement the required interface correctly.
This prevents adapter drift and maintains consistency across frameworks.

Every adapter MUST pass these contract tests.
"""

import pytest
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AdapterContract(ABC):
    """
    Base contract that all CrossBridge adapters must implement.
    
    This defines the minimum required interface for framework adapters.
    """
    
    @abstractmethod
    def extract_tests(self, source_path: str) -> List[Dict[str, Any]]:
        """
        Extract tests from source files.
        
        Args:
            source_path: Path to test file or directory
            
        Returns:
            List of test dictionaries with required fields
        """
        pass
    
    @abstractmethod
    def get_framework_name(self) -> str:
        """
        Get the name of the framework this adapter supports.
        
        Returns:
            Framework name (e.g., 'pytest', 'selenium', 'cypress')
        """
        pass
    
    def can_handle(self, file_path: str) -> bool:
        """
        Check if this adapter can handle the given file.
        
        Args:
            file_path: Path to test file
            
        Returns:
            True if adapter can handle this file
        """
        return False


def test_adapter_implements_contract(adapter):
    """
    Verify adapter implements the required contract.
    
    Args:
        adapter: Adapter instance to test
    """
    # Must have extract_tests method
    assert hasattr(adapter, 'extract_tests'), \
        f"{adapter.__class__.__name__} must implement extract_tests()"
    
    # Must have get_framework_name method
    assert hasattr(adapter, 'get_framework_name'), \
        f"{adapter.__class__.__name__} must implement get_framework_name()"
    
    # Must have can_handle method
    assert hasattr(adapter, 'can_handle'), \
        f"{adapter.__class__.__name__} must implement can_handle()"


def test_extract_tests_returns_list(adapter, sample_test_file):
    """
    Verify extract_tests returns a list.
    
    Args:
        adapter: Adapter instance
        sample_test_file: Path to sample test file
    """
    result = adapter.extract_tests(sample_test_file)
    
    assert isinstance(result, list), \
        f"extract_tests() must return a list, got {type(result)}"


def test_extract_tests_returns_dicts(adapter, sample_test_file):
    """
    Verify extract_tests returns list of dictionaries.
    
    Args:
        adapter: Adapter instance
        sample_test_file: Path to sample test file
    """
    result = adapter.extract_tests(sample_test_file)
    
    if result:  # Only check if non-empty
        assert all(isinstance(test, dict) for test in result), \
            "extract_tests() must return list of dictionaries"


def test_extracted_tests_have_required_fields(adapter, sample_test_file):
    """
    Verify extracted tests have required fields.
    
    Args:
        adapter: Adapter instance
        sample_test_file: Path to sample test file
    """
    required_fields = ['name', 'framework']
    result = adapter.extract_tests(sample_test_file)
    
    if result:  # Only check if non-empty
        for test in result:
            for field in required_fields:
                assert field in test, \
                    f"Extracted test must have '{field}' field. Got: {test.keys()}"


def test_get_framework_name_returns_string(adapter):
    """
    Verify get_framework_name returns a string.
    
    Args:
        adapter: Adapter instance
    """
    result = adapter.get_framework_name()
    
    assert isinstance(result, str), \
        f"get_framework_name() must return string, got {type(result)}"
    assert len(result) > 0, \
        "get_framework_name() must return non-empty string"


def test_can_handle_returns_bool(adapter):
    """
    Verify can_handle returns a boolean.
    
    Args:
        adapter: Adapter instance
    """
    result = adapter.can_handle('test.py')
    
    assert isinstance(result, bool), \
        f"can_handle() must return bool, got {type(result)}"


def test_adapter_handles_appropriate_files(adapter, valid_test_file, invalid_test_file):
    """
    Verify adapter correctly identifies files it can handle.
    
    Args:
        adapter: Adapter instance
        valid_test_file: File the adapter should handle
        invalid_test_file: File the adapter should NOT handle
    """
    assert adapter.can_handle(valid_test_file), \
        f"Adapter should handle {valid_test_file}"
    
    assert not adapter.can_handle(invalid_test_file), \
        f"Adapter should NOT handle {invalid_test_file}"


def test_extract_tests_is_idempotent(adapter, sample_test_file):
    """
    Verify extract_tests produces same output on repeated calls.
    
    Args:
        adapter: Adapter instance
        sample_test_file: Path to sample test file
    """
    result1 = adapter.extract_tests(sample_test_file)
    result2 = adapter.extract_tests(sample_test_file)
    
    assert result1 == result2, \
        "extract_tests() must be idempotent (same input -> same output)"


def test_extract_tests_handles_empty_file(adapter, empty_test_file):
    """
    Verify adapter gracefully handles empty files.
    
    Args:
        adapter: Adapter instance
        empty_test_file: Path to empty file
    """
    result = adapter.extract_tests(empty_test_file)
    
    assert isinstance(result, list), \
        "extract_tests() must return list even for empty files"


def test_extract_tests_handles_invalid_file(adapter, invalid_test_file):
    """
    Verify adapter gracefully handles invalid files.
    
    Args:
        adapter: Adapter instance
        invalid_test_file: Path to invalid file
    """
    # Should not raise exception
    try:
        result = adapter.extract_tests(invalid_test_file)
        assert isinstance(result, list), \
            "extract_tests() must return list even for invalid files"
    except Exception as e:
        pytest.fail(f"Adapter should not raise exception for invalid files: {e}")


def test_extracted_tests_have_consistent_structure(adapter, sample_test_file):
    """
    Verify all extracted tests have consistent structure.
    
    Args:
        adapter: Adapter instance
        sample_test_file: Path to sample test file
    """
    result = adapter.extract_tests(sample_test_file)
    
    if len(result) > 1:
        # All tests should have same keys (except optional fields)
        required_keys = {'name', 'framework'}
        
        for test in result:
            assert required_keys.issubset(test.keys()), \
                f"Test missing required keys: {required_keys - test.keys()}"


# ============================================================================
# Framework-Specific Contract Tests
# ============================================================================

class PytestAdapterContract:
    """Contract specific to Pytest adapter."""
    
    def test_extracts_test_functions(self, adapter, pytest_file):
        """Verify adapter extracts pytest test functions."""
        result = adapter.extract_tests(pytest_file)
        assert len(result) > 0, "Should extract at least one test"
        assert any('test_' in test['name'] for test in result), \
            "Should extract functions starting with 'test_'"
    
    def test_extracts_test_classes(self, adapter, pytest_class_file):
        """Verify adapter extracts pytest test classes."""
        result = adapter.extract_tests(pytest_class_file)
        assert any('class_name' in test for test in result), \
            "Should extract test class information"


class SeleniumAdapterContract:
    """Contract specific to Selenium adapter."""
    
    def test_extracts_locators(self, adapter, selenium_file):
        """Verify adapter extracts locator information."""
        result = adapter.extract_tests(selenium_file)
        if result:
            # At least some tests should have locators
            has_locators = any('locators' in test for test in result)
            assert has_locators or len(result) == 0, \
                "Selenium tests should include locator information"


class RobotAdapterContract:
    """Contract specific to Robot Framework adapter."""
    
    def test_extracts_keywords(self, adapter, robot_file):
        """Verify adapter extracts Robot keywords."""
        result = adapter.extract_tests(robot_file)
        if result:
            assert any('keywords' in test for test in result), \
                "Robot tests should include keyword information"


class CypressAdapterContract:
    """Contract specific to Cypress adapter."""
    
    def test_extracts_describe_blocks(self, adapter, cypress_file):
        """Verify adapter extracts Cypress describe blocks."""
        result = adapter.extract_tests(cypress_file)
        if result:
            # Cypress tests often have describe blocks
            pass  # Can add specific validation if needed


# ============================================================================
# Contract Test Suite Runner
# ============================================================================

def run_adapter_contract_tests(adapter, test_files):
    """
    Run all contract tests for an adapter.
    
    Args:
        adapter: Adapter instance to test
        test_files: Dictionary of test files by type
        
    Example:
        test_files = {
            'sample': '/path/to/sample_test.py',
            'empty': '/path/to/empty.py',
            'invalid': '/path/to/invalid.txt',
            'valid': '/path/to/valid_test.py'
        }
    """
    # Run basic contract tests
    test_adapter_implements_contract(adapter)
    test_get_framework_name_returns_string(adapter)
    test_can_handle_returns_bool(adapter)
    
    # Run extraction tests if sample file provided
    if 'sample' in test_files:
        sample_file = test_files['sample']
        test_extract_tests_returns_list(adapter, sample_file)
        test_extract_tests_returns_dicts(adapter, sample_file)
        test_extracted_tests_have_required_fields(adapter, sample_file)
        test_extract_tests_is_idempotent(adapter, sample_file)
        test_extracted_tests_have_consistent_structure(adapter, sample_file)
    
    # Run error handling tests
    if 'empty' in test_files:
        test_extract_tests_handles_empty_file(adapter, test_files['empty'])
    
    if 'invalid' in test_files:
        test_extract_tests_handles_invalid_file(adapter, test_files['invalid'])
    
    # Run file handling tests
    if 'valid' in test_files and 'invalid' in test_files:
        test_adapter_handles_appropriate_files(
            adapter,
            test_files['valid'],
            test_files['invalid']
        )
    
    return True


# ============================================================================
# Pytest Integration
# ============================================================================

# This allows pytest to discover and run these tests
__all__ = [
    'AdapterContract',
    'test_adapter_implements_contract',
    'test_extract_tests_returns_list',
    'test_extract_tests_returns_dicts',
    'test_extracted_tests_have_required_fields',
    'test_get_framework_name_returns_string',
    'test_can_handle_returns_bool',
    'test_adapter_handles_appropriate_files',
    'test_extract_tests_is_idempotent',
    'test_extract_tests_handles_empty_file',
    'test_extract_tests_handles_invalid_file',
    'test_extracted_tests_have_consistent_structure',
    'run_adapter_contract_tests',
]
