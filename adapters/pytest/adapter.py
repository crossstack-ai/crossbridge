"""
Pytest adapter implementation for CrossBridge AI.

This adapter translates between pytest-specific test structure and the
framework-agnostic internal model.
"""

import subprocess
import time
from typing import List
from pathlib import Path

from ..common.base import BaseTestAdapter, TestResult


class PytestAdapter(BaseTestAdapter):
    """
    Adapter for pytest framework.
    
    Translates pytest tests to and from the framework-agnostic internal model.
    """

    def __init__(self, project_root: str):
        """
        Initialize the pytest adapter.
        
        Args:
            project_root: Root directory of the pytest project.
        """
        self.project_root = Path(project_root)

    def discover_tests(self) -> List[str]:
        """
        Discover all pytest tests using pytest --collect-only.
        
        Returns:
            List[str]: List of discovered test names.
        """
        tests = []
        
        try:
            # Run pytest collection
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
                    
                # Parse test item (format: path/file.py::TestClass::test_method or path/file.py::test_function)
                if '::' in line:
                    # Use the last part (test name) as the test identifier
                    test_name = line.split('::')[-1]
                    tests.append(test_name)
                    
        except subprocess.TimeoutExpired:
            print("Warning: Pytest collection timed out")
        except FileNotFoundError:
            print("Warning: Pytest not found. Please ensure pytest is installed.")
        except Exception as e:
            print(f"Warning: Error discovering tests: {e}")
            
        return tests

    def run_tests(
        self,
        tests: List[str] = None,
        tags: List[str] = None
    ) -> List[TestResult]:
        """
        Execute pytest tests.
        
        Args:
            tests: List of test names to run. If None, runs all tests.
            tags: List of pytest markers to filter tests by.
            
        Returns:
            List[TestResult]: Execution results for each test.
        """
        results = []
        
        try:
            # Build pytest command
            cmd = ["pytest", "-v", "--tb=short"]
            
            # Add test filtering if specified
            if tests:
                # Use -k to filter by test names
                test_filter = " or ".join(tests)
                cmd.extend(["-k", test_filter])
            
            # Add marker filtering if specified
            if tags:
                for tag in tags:
                    cmd.extend(["-m", tag])
            
            # Execute pytest
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse output for test results
            output = result.stdout + result.stderr
            
            # Simple parsing - look for PASSED/FAILED lines
            for line in output.split('\n'):
                if 'PASSED' in line or 'FAILED' in line or 'SKIPPED' in line:
                    # Extract test name and status
                    if 'PASSED' in line:
                        status = 'pass'
                        test_name = line.split('::')[-1].split(' ')[0] if '::' in line else 'unknown'
                    elif 'FAILED' in line:
                        status = 'fail'
                        test_name = line.split('::')[-1].split(' ')[0] if '::' in line else 'unknown'
                    else:
                        status = 'skip'
                        test_name = line.split('::')[-1].split(' ')[0] if '::' in line else 'unknown'
                    
                    results.append(TestResult(
                        name=test_name,
                        status=status,
                        duration_ms=duration_ms // max(len(results) + 1, 1),  # Rough estimate
                        message=line.strip()
                    ))
            
            # If no specific results parsed, return overall result
            if not results:
                status = 'pass' if result.returncode == 0 else 'fail'
                results.append(TestResult(
                    name="pytest suite",
                    status=status,
                    duration_ms=duration_ms,
                    message=output[:200] if output else ""
                ))
                    
        except subprocess.TimeoutExpired:
            results.append(TestResult(
                name="pytest suite",
                status="fail",
                duration_ms=300000,
                message="Test execution timed out"
            ))
        except FileNotFoundError:
            results.append(TestResult(
                name="pytest suite",
                status="fail",
                duration_ms=0,
                message="Pytest not found"
            ))
        except Exception as e:
            results.append(TestResult(
                name="pytest suite",
                status="fail",
                duration_ms=0,
                message=f"Error executing tests: {str(e)}"
            ))
        
        return results
