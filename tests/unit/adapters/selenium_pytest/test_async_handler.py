"""
Tests for async test handler.
"""

import pytest
from pathlib import Path
from adapters.selenium_pytest.async_handler import PytestAsyncTestHandler


@pytest.fixture
def handler():
    return PytestAsyncTestHandler()


@pytest.fixture
def async_test_file(tmp_path):
    """Create a sample async test file."""
    test_file = tmp_path / "test_async.py"
    test_file.write_text("""
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result == expected

async def test_async_no_marker():
    # Async without marker
    await another_function()

def test_sync_function():
    # Regular sync test
    assert True

@pytest.fixture
async def async_fixture():
    # Setup
    resource = await setup_resource()
    yield resource
    # Teardown
    await cleanup_resource(resource)
    """)
    return test_file


def test_extract_async_tests(handler, async_test_file):
    """Test extraction of async tests."""
    async_tests = handler.extract_async_tests(async_test_file)
    
    assert len(async_tests) >= 2
    
    # Check test with marker
    marked_test = next(
        (t for t in async_tests if t['name'] == 'test_async_operation'),
        None
    )
    assert marked_test is not None
    assert marked_test['has_async_marker'] is True
    assert marked_test['is_async_def'] is True
    
    # Check test without marker
    unmarked_test = next(
        (t for t in async_tests if t['name'] == 'test_async_no_marker'),
        None
    )
    assert unmarked_test is not None
    assert unmarked_test['is_async_def'] is True


def test_detect_async_fixtures(handler, async_test_file):
    """Test detection of async fixtures."""
    async_fixtures = handler.detect_async_fixtures(async_test_file)
    
    assert 'async_fixture' in async_fixtures


def test_requires_pytest_asyncio(handler, tmp_path):
    """Test detection of pytest-asyncio requirement."""
    # Create test file with async test
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("""
@pytest.mark.asyncio
async def test_something():
    await some_async_call()
    """)
    
    result = handler.requires_pytest_asyncio(tmp_path)
    assert result is True


def test_get_async_config(handler):
    """Test getting async configuration."""
    config = handler.get_async_config()
    
    assert 'asyncio_mode' in config
    assert config['asyncio_mode'] == 'auto'


def test_no_async_tests(handler, tmp_path):
    """Test file with no async tests."""
    test_file = tmp_path / "test_sync.py"
    test_file.write_text("""
def test_regular():
    assert True

def test_another():
    value = 42
    assert value == 42
    """)
    
    async_tests = handler.extract_async_tests(test_file)
    assert len(async_tests) == 0
