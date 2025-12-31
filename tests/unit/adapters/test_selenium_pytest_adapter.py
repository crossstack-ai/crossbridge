"""
Tests for Selenium + Pytest adapter.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from adapters.selenium_pytest.adapter import (
    SeleniumPytestAdapter,
    SeleniumPytestExtractor,
    SeleniumPytestDetector
)


class TestSeleniumPytestAdapter:
    """Test Selenium + Pytest adapter functionality."""
    
    @patch('adapters.selenium_pytest.adapter.SeleniumPytestAdapter._verify_pytest_installed')
    def test_adapter_initialization(self, mock_verify, tmp_path):
        """Test adapter initialization."""
        adapter = SeleniumPytestAdapter(str(tmp_path), driver_type="chrome")
        
        assert adapter.project_root == tmp_path
        assert adapter.driver_type == "chrome"
    
    @patch('adapters.selenium_pytest.adapter.SeleniumPytestAdapter._verify_pytest_installed')
    @patch('subprocess.run')
    def test_discover_tests(self, mock_run, mock_verify, tmp_path):
        """Test test discovery."""
        # Mock pytest collection output
        mock_run.return_value = Mock(
            returncode=0,
            stdout=(
                "test_login.py::TestLogin::test_valid_login\n"
                "test_login.py::TestLogin::test_invalid_login\n"
                "test_search.py::test_search_product\n"
            )
        )
        
        adapter = SeleniumPytestAdapter(str(tmp_path))
        tests = adapter.discover_tests()
        
        assert len(tests) == 3
        assert "test_login.py::TestLogin::test_valid_login" in tests
        assert "test_search.py::test_search_product" in tests
    
    @patch('adapters.selenium_pytest.adapter.SeleniumPytestAdapter._verify_pytest_installed')
    @patch('subprocess.run')
    def test_run_tests_with_json_report(self, mock_run, mock_verify, tmp_path):
        """Test running tests with JSON report."""
        # Create mock JSON report
        report_data = {
            'tests': [
                {
                    'nodeid': 'test_login.py::test_valid_login',
                    'outcome': 'passed',
                    'duration': 2.5
                },
                {
                    'nodeid': 'test_login.py::test_invalid_login',
                    'outcome': 'failed',
                    'duration': 1.8,
                    'call': {
                        'longrepr': 'AssertionError: Expected error message not shown'
                    }
                }
            ]
        }
        
        # Write mock report
        report_path = tmp_path / "report.json"
        import json
        with open(report_path, 'w') as f:
            json.dump(report_data, f)
        
        mock_run.return_value = Mock(returncode=1, stdout="")
        
        adapter = SeleniumPytestAdapter(str(tmp_path))
        results = adapter.run_tests()
        
        assert len(results) == 2
        assert results[0].name == 'test_login.py::test_valid_login'
        assert results[0].status == 'pass'
        assert results[0].duration_ms == 2500
        
        assert results[1].name == 'test_login.py::test_invalid_login'
        assert results[1].status == 'fail'
        assert 'AssertionError' in results[1].message
    
    @patch('adapters.selenium_pytest.adapter.SeleniumPytestAdapter._verify_pytest_installed')
    @patch('subprocess.run')
    def test_run_tests_with_tags(self, mock_run, mock_verify, tmp_path):
        """Test running tests with marker filtering."""
        mock_run.return_value = Mock(returncode=0, stdout="")
        
        # Mock empty report
        report_path = tmp_path / "report.json"
        with open(report_path, 'w') as f:
            f.write('{"tests": []}')
        
        adapter = SeleniumPytestAdapter(str(tmp_path))
        adapter.run_tests(tags=["smoke", "critical"])
        
        # Verify pytest was called with markers
        call_args = mock_run.call_args[0][0]
        assert "-m" in call_args
        assert "smoke or critical" in call_args
    
    @patch('adapters.selenium_pytest.adapter.SeleniumPytestAdapter._verify_pytest_installed')
    def test_get_driver_info(self, mock_verify, tmp_path):
        """Test getting driver information."""
        adapter = SeleniumPytestAdapter(str(tmp_path), driver_type="firefox")
        
        info = adapter.get_driver_info()
        assert info['driver_type'] == 'firefox'
        assert info['framework'] == 'selenium'
        assert info['runner'] == 'pytest'


class TestSeleniumPytestExtractor:
    """Test Selenium pytest extractor."""
    
    def test_extract_test_functions(self, tmp_path):
        """Test extracting standalone test functions."""
        # Create test file
        test_file = tmp_path / "test_sample.py"
        test_file.write_text("""
import pytest
from selenium import webdriver

@pytest.mark.smoke
def test_homepage_loads():
    driver = webdriver.Chrome()
    driver.get("https://example.com")
    assert "Example" in driver.title
    driver.quit()

@pytest.mark.critical
def test_login():
    pass
""")
        
        extractor = SeleniumPytestExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        assert any('test_homepage_loads' in t.test_name for t in tests)
        assert any('test_login' in t.test_name for t in tests)
        
        # Check tags
        homepage_test = [t for t in tests if 'test_homepage_loads' in t.test_name][0]
        assert 'smoke' in homepage_test.tags
    
    def test_extract_test_classes(self, tmp_path):
        """Test extracting test classes."""
        test_file = tmp_path / "test_login.py"
        test_file.write_text("""
import pytest
from selenium import webdriver

@pytest.mark.integration
class TestLogin:
    
    @pytest.mark.smoke
    def test_valid_credentials(self):
        pass
    
    @pytest.mark.regression
    def test_invalid_credentials(self):
        pass
""")
        
        extractor = SeleniumPytestExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        
        # Check test names
        test_names = [t.test_name for t in tests]
        assert any('TestLogin::test_valid_credentials' in name for name in test_names)
        
        # Check tag inheritance
        for test in tests:
            assert 'integration' in test.tags  # Class-level tag
    
    def test_extract_markers(self, tmp_path):
        """Test extracting pytest markers."""
        test_file = tmp_path / "test_markers.py"
        test_file.write_text("""
import pytest

@pytest.mark.smoke
@pytest.mark.parametrize('browser', ['chrome', 'firefox'])
def test_cross_browser():
    pass
""")
        
        extractor = SeleniumPytestExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert 'smoke' in tests[0].tags
        assert 'parametrize' in tests[0].tags


class TestSeleniumPytestDetector:
    """Test Selenium pytest project detector."""
    
    def test_detect_valid_project(self, tmp_path):
        """Test detecting valid Selenium + pytest project."""
        # Create pytest.ini
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        
        # Create test file with selenium import
        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
from selenium import webdriver

def test_example():
    driver = webdriver.Chrome()
    driver.quit()
""")
        
        assert SeleniumPytestDetector.detect(str(tmp_path)) is True
    
    def test_detect_with_requirements(self, tmp_path):
        """Test detection via requirements.txt."""
        # Create pyproject.toml (pytest indicator)
        (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
        
        # Create requirements.txt with selenium
        (tmp_path / "requirements.txt").write_text("selenium==4.0.0\npytest>=7.0.0\n")
        
        # Create empty test file
        (tmp_path / "test_dummy.py").write_text("")
        
        assert SeleniumPytestDetector.detect(str(tmp_path)) is True
    
    def test_detect_no_selenium(self, tmp_path):
        """Test no detection when Selenium missing."""
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        (tmp_path / "test_example.py").write_text("def test_example(): pass")
        
        assert SeleniumPytestDetector.detect(str(tmp_path)) is False
    
    def test_detect_no_pytest(self, tmp_path):
        """Test no detection when pytest missing."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("from selenium import webdriver")
        
        assert SeleniumPytestDetector.detect(str(tmp_path)) is False


class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self, tmp_path):
        """Test complete workflow: detect -> extract -> discover."""
        # Setup project structure
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        
        test_file = tmp_path / "test_workflow.py"
        test_file.write_text("""
import pytest
from selenium import webdriver

@pytest.mark.smoke
class TestWorkflow:
    def test_step_one(self):
        pass
    
    def test_step_two(self):
        pass
""")
        
        # Detect
        detected = SeleniumPytestDetector.detect(str(tmp_path))
        assert detected is True
        
        # Extract
        extractor = SeleniumPytestExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        assert len(tests) == 2
        
        # Verify metadata
        assert all(t.framework == "selenium-pytest" for t in tests)
        assert all(t.test_type == "ui" for t in tests)
        assert all('smoke' in t.tags for t in tests)
