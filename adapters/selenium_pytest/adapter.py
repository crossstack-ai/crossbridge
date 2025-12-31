"""
Selenium + Pytest adapter implementation.

Handles Selenium WebDriver tests that use pytest as the test runner.
Supports:
- Page Object Model pattern
- Fixtures for driver management
- Parametrized tests
- Markers/tags
- Pytest plugins (pytest-selenium, pytest-html, etc.)
"""

import subprocess
import json
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
import ast

from ..common.base import BaseTestAdapter, TestResult
from ..common.models import TestMetadata


class SeleniumPytestAdapter(BaseTestAdapter):
    """
    Adapter for Selenium tests using pytest framework.
    
    Handles discovery and execution of Selenium WebDriver tests with pytest runner.
    """

    def __init__(self, project_root: str, driver_type: str = "chrome"):
        """
        Initialize the Selenium pytest adapter.
        
        Args:
            project_root: Root directory of the project
            driver_type: WebDriver type (chrome, firefox, edge, safari)
        """
        self.project_root = Path(project_root)
        self.driver_type = driver_type
        self._verify_pytest_installed()

    def _verify_pytest_installed(self):
        """Verify pytest is installed."""
        try:
            result = subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("pytest is not properly installed")
        except FileNotFoundError:
            raise RuntimeError("pytest is not installed. Install with: pip install pytest pytest-selenium")

    def discover_tests(self) -> List[str]:
        """
        Discover Selenium tests using pytest collection.
        
        Returns:
            List of test identifiers in pytest format (file::class::method)
        """
        tests = []
        
        try:
            # Use pytest collection with verbose output
            result = subprocess.run(
                ["pytest", "--collect-only", "-q", "--no-header"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse pytest collection output
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('=') or 'passed' in line.lower():
                    continue
                
                # Parse test item (format: path/file.py::TestClass::test_method)
                if '::' in line:
                    # Remove <Module> and <Class> prefixes if present
                    test_id = re.sub(r'<[^>]+>\s*', '', line)
                    tests.append(test_id.strip())
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("Test discovery timed out")
        except Exception as e:
            raise RuntimeError(f"Failed to discover tests: {e}")
        
        return tests

    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """
        Run Selenium tests using pytest.
        
        Args:
            tests: Specific tests to run (None = all tests)
            tags: Pytest markers to filter by
        
        Returns:
            List of TestResult objects
        """
        cmd = ["pytest", "-v", "--tb=short", "--json-report", "--json-report-file=report.json"]
        
        # Add marker filtering
        if tags:
            marker_expr = " or ".join(tags)
            cmd.extend(["-m", marker_expr])
        
        # Add specific tests
        if tests:
            cmd.extend(tests)
        
        # Add driver configuration via environment or command line
        # pytest-selenium uses --driver flag
        cmd.extend(["--driver", self.driver_type])
        
        try:
            # Run pytest
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse JSON report if available
            report_path = self.project_root / "report.json"
            if report_path.exists():
                with open(report_path, 'r') as f:
                    report_data = json.load(f)
                    return self._parse_json_report(report_data)
            
            # Fallback to parsing stdout
            return self._parse_pytest_output(result.stdout)
        
        except subprocess.TimeoutExpired:
            return [TestResult(
                name="execution_timeout",
                status="fail",
                duration_ms=300000,
                message="Test execution timed out"
            )]
        except Exception as e:
            return [TestResult(
                name="execution_error",
                status="fail",
                duration_ms=0,
                message=f"Execution failed: {e}"
            )]

    def _parse_json_report(self, report: Dict[str, Any]) -> List[TestResult]:
        """Parse pytest JSON report."""
        results = []
        
        for test in report.get('tests', []):
            # Extract test name (nodeid in pytest)
            test_name = test.get('nodeid', 'unknown')
            
            # Map pytest outcome to our status
            outcome = test.get('outcome', 'failed')
            status_map = {
                'passed': 'pass',
                'failed': 'fail',
                'skipped': 'skip',
                'error': 'fail'
            }
            status = status_map.get(outcome, 'fail')
            
            # Duration in milliseconds
            duration_ms = int(test.get('duration', 0) * 1000)
            
            # Error message if failed
            message = ""
            if outcome in ['failed', 'error']:
                call = test.get('call', {})
                longrepr = call.get('longrepr', '')
                if longrepr:
                    message = str(longrepr)[:500]  # Truncate long messages
            
            results.append(TestResult(
                name=test_name,
                status=status,
                duration_ms=duration_ms,
                message=message
            ))
        
        return results

    def _parse_pytest_output(self, output: str) -> List[TestResult]:
        """Parse pytest stdout as fallback."""
        results = []
        
        # Parse pytest output format
        lines = output.split('\n')
        
        for line in lines:
            # Match test result lines (e.g., "test_login.py::test_valid_login PASSED [100%]")
            match = re.match(r'(.+?)\s+(PASSED|FAILED|SKIPPED|ERROR)', line)
            if match:
                test_name = match.group(1).strip()
                outcome = match.group(2).strip()
                
                status_map = {
                    'PASSED': 'pass',
                    'FAILED': 'fail',
                    'SKIPPED': 'skip',
                    'ERROR': 'fail'
                }
                status = status_map.get(outcome, 'fail')
                
                results.append(TestResult(
                    name=test_name,
                    status=status,
                    duration_ms=0,  # Not available in stdout
                    message=""
                ))
        
        return results

    def get_driver_info(self) -> Dict[str, str]:
        """Get WebDriver information."""
        return {
            'driver_type': self.driver_type,
            'framework': 'selenium',
            'runner': 'pytest'
        }


class SeleniumPytestExtractor:
    """
    Extractor for Selenium + pytest tests.
    
    Parses Python test files to extract metadata without execution.
    """
    
    def __init__(self, project_root: str):
        """
        Initialize extractor.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
    
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract test metadata from Python files.
        
        Returns:
            List of TestMetadata objects
        """
        tests = []
        
        # Find all test files
        test_files = list(self.project_root.rglob("test_*.py")) + \
                     list(self.project_root.rglob("*_test.py"))
        
        for test_file in test_files:
            try:
                file_tests = self._parse_test_file(test_file)
                tests.extend(file_tests)
            except Exception as e:
                # Log but continue with other files
                print(f"Warning: Failed to parse {test_file}: {e}")
                continue
        
        return tests
    
    def _parse_test_file(self, file_path: Path) -> List[TestMetadata]:
        """Parse a single test file using AST."""
        tests = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return tests
        
        # Track which test methods belong to classes to avoid duplicates
        class_methods = set()
        
        # First pass: find test classes and their methods
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                # Test class
                class_tags = self._extract_markers(node)
                
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'):
                        class_methods.add(method.name)
                        method_tags = self._extract_markers(method)
                        all_tags = list(set(class_tags + method_tags))
                        
                        tests.append(TestMetadata(
                            framework="selenium-pytest",
                            test_name=f"{file_path.name}::{node.name}::{method.name}",
                            file_path=str(file_path),
                            tags=all_tags,
                            test_type="ui",
                            language="python"
                        ))
        
        # Second pass: find standalone test functions (not in classes)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_') and node.name not in class_methods:
                    # Standalone test function
                    tags = self._extract_markers(node)
                    
                    tests.append(TestMetadata(
                        framework="selenium-pytest",
                        test_name=f"{file_path.name}::{node.name}",
                        file_path=str(file_path),
                        tags=tags,
                        test_type="ui",
                        language="python"
                    ))
        
        return tests
    
    def _extract_markers(self, node: ast.AST) -> List[str]:
        """Extract pytest markers from decorators."""
        markers = []
        
        if not hasattr(node, 'decorator_list'):
            return markers
        
        for decorator in node.decorator_list:
            # Handle @pytest.mark.marker_name
            if isinstance(decorator, ast.Attribute):
                if isinstance(decorator.value, ast.Attribute):
                    if (hasattr(decorator.value, 'attr') and 
                        decorator.value.attr == 'mark'):
                        markers.append(decorator.attr)
            
            # Handle @pytest.mark.marker_name()
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if isinstance(decorator.func.value, ast.Attribute):
                        if (hasattr(decorator.func.value, 'attr') and 
                            decorator.func.value.attr == 'mark'):
                            markers.append(decorator.func.attr)
        
        return markers


class SeleniumPytestDetector:
    """
    Detector for Selenium + pytest projects.
    
    Identifies if a project uses Selenium with pytest.
    """
    
    @staticmethod
    def detect(project_root: str) -> bool:
        """
        Detect if project uses Selenium + pytest.
        
        Args:
            project_root: Root directory to check
        
        Returns:
            True if Selenium + pytest project detected
        """
        root = Path(project_root)
        
        # Check for pytest indicators
        has_pytest = any([
            (root / "pytest.ini").exists(),
            (root / "pyproject.toml").exists(),
            (root / "setup.cfg").exists(),
            (root / "tox.ini").exists(),
        ])
        
        # Check for Selenium imports in test files
        has_selenium = False
        test_files = list(root.rglob("test_*.py")) + list(root.rglob("*_test.py"))
        
        for test_file in test_files[:10]:  # Check first 10 files
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'from selenium' in content or 'import selenium' in content:
                        has_selenium = True
                        break
            except:
                continue
        
        # Check requirements files
        if not has_selenium:
            for req_file in ['requirements.txt', 'requirements-test.txt', 'test-requirements.txt']:
                req_path = root / req_file
                if req_path.exists():
                    try:
                        with open(req_path, 'r') as f:
                            content = f.read()
                            if 'selenium' in content.lower():
                                has_selenium = True
                                break
                    except:
                        continue
        
        return has_pytest and has_selenium
