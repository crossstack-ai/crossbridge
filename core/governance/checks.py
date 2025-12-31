"""
Automated policy checks for various aspects of test automation.

Provides ready-to-use checks for common governance scenarios.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import re
import ast


@dataclass
class CheckResult:
    """
    Result of a policy check.
    
    Attributes:
        passed: Whether the check passed
        message: Description of the result
        details: Additional details about findings
    """
    passed: bool
    message: str
    details: Dict[str, Any]


class PolicyChecker:
    """Automated checks for policy compliance."""
    
    @staticmethod
    def check_test_coverage(coverage_data: Dict[str, Any], threshold: float = 80.0) -> CheckResult:
        """
        Check if test coverage meets threshold.
        
        Args:
            coverage_data: Coverage statistics
            threshold: Minimum required coverage percentage
            
        Returns:
            CheckResult indicating pass/fail
        """
        coverage = coverage_data.get('coverage_percent', 0.0)
        passed = coverage >= threshold
        
        return CheckResult(
            passed=passed,
            message=f"Coverage is {coverage:.1f}% (threshold: {threshold}%)",
            details={
                'coverage': coverage,
                'threshold': threshold,
                'covered_lines': coverage_data.get('covered_lines', 0),
                'total_lines': coverage_data.get('total_lines', 0)
            }
        )
    
    @staticmethod
    def check_no_hardcoded_secrets(file_path: Path) -> CheckResult:
        """
        Check for hardcoded secrets in test files.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            CheckResult indicating if secrets found
        """
        # Patterns that might indicate secrets
        secret_patterns = [
            r'password\s*=\s*["\'](?!<|{|\$)[^"\']{8,}["\']',  # password = "literal"
            r'api_key\s*=\s*["\'][^"\']{20,}["\']',
            r'token\s*=\s*["\'][^"\']{20,}["\']',
            r'secret\s*=\s*["\'][^"\']{20,}["\']',
            r'aws_secret_access_key\s*=\s*["\'][^"\']+["\']',
        ]
        
        try:
            content = file_path.read_text(encoding='utf-8')
            findings = []
            
            for pattern in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1
                    findings.append({
                        'line': line_num,
                        'pattern': pattern,
                        'text': match.group(0)[:50]  # Truncate for safety
                    })
            
            passed = len(findings) == 0
            message = "No hardcoded secrets found" if passed else f"Found {len(findings)} potential hardcoded secrets"
            
            return CheckResult(
                passed=passed,
                message=message,
                details={'findings': findings, 'file': str(file_path)}
            )
            
        except Exception as e:
            return CheckResult(
                passed=False,
                message=f"Check failed: {str(e)}",
                details={'error': str(e)}
            )
    
    @staticmethod
    def check_test_naming_convention(test_files: List[Path], pattern: str = r'^test_.*\.py$') -> CheckResult:
        """
        Check if test files follow naming convention.
        
        Args:
            test_files: List of test file paths
            pattern: Regex pattern for valid test file names
            
        Returns:
            CheckResult indicating compliance
        """
        non_compliant = []
        compiled_pattern = re.compile(pattern)
        
        for file_path in test_files:
            if not compiled_pattern.match(file_path.name):
                non_compliant.append(str(file_path))
        
        passed = len(non_compliant) == 0
        message = "All test files follow naming convention" if passed else f"{len(non_compliant)} files don't follow convention"
        
        return CheckResult(
            passed=passed,
            message=message,
            details={
                'pattern': pattern,
                'non_compliant_files': non_compliant,
                'total_files': len(test_files)
            }
        )
    
    @staticmethod
    def check_test_has_assertions(test_file: Path) -> CheckResult:
        """
        Check if test file contains assertion statements.
        
        Args:
            test_file: Path to test file
            
        Returns:
            CheckResult indicating if assertions found
        """
        try:
            content = test_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            tests_without_assertions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    has_assertion = False
                    
                    for child in ast.walk(node):
                        # Check for assert statements
                        if isinstance(child, ast.Assert):
                            has_assertion = True
                            break
                        # Check for assertion method calls (pytest, unittest)
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Attribute):
                                method_name = child.func.attr
                                if method_name.startswith('assert') or method_name in ['assertEqual', 'assertTrue', 'assertFalse']:
                                    has_assertion = True
                                    break
                    
                    if not has_assertion:
                        tests_without_assertions.append(node.name)
            
            passed = len(tests_without_assertions) == 0
            message = "All tests have assertions" if passed else f"{len(tests_without_assertions)} tests lack assertions"
            
            return CheckResult(
                passed=passed,
                message=message,
                details={
                    'tests_without_assertions': tests_without_assertions,
                    'file': str(test_file)
                }
            )
            
        except Exception as e:
            return CheckResult(
                passed=False,
                message=f"Check failed: {str(e)}",
                details={'error': str(e)}
            )
    
    @staticmethod
    def check_documentation_exists(project_root: Path, required_docs: List[str] = None) -> CheckResult:
        """
        Check if required documentation exists.
        
        Args:
            project_root: Root directory of project
            required_docs: List of required documentation files
            
        Returns:
            CheckResult indicating compliance
        """
        if required_docs is None:
            required_docs = ['README.md', 'CONTRIBUTING.md']
        
        missing_docs = []
        
        for doc in required_docs:
            if not (project_root / doc).exists():
                missing_docs.append(doc)
        
        passed = len(missing_docs) == 0
        message = "All required documentation exists" if passed else f"Missing {len(missing_docs)} required documents"
        
        return CheckResult(
            passed=passed,
            message=message,
            details={
                'required_docs': required_docs,
                'missing_docs': missing_docs
            }
        )
    
    @staticmethod
    def check_flaky_tests(test_results: List[Dict[str, Any]], threshold: float = 0.95) -> CheckResult:
        """
        Check for flaky tests based on historical pass rates.
        
        Args:
            test_results: Historical test execution results
            threshold: Minimum pass rate to not be considered flaky
            
        Returns:
            CheckResult indicating flaky tests
        """
        test_pass_rates = {}
        
        for result in test_results:
            test_name = result.get('test_name')
            passed = result.get('passed', False)
            
            if test_name not in test_pass_rates:
                test_pass_rates[test_name] = {'total': 0, 'passed': 0}
            
            test_pass_rates[test_name]['total'] += 1
            if passed:
                test_pass_rates[test_name]['passed'] += 1
        
        flaky_tests = []
        for test_name, stats in test_pass_rates.items():
            if stats['total'] > 1:  # Only consider tests run multiple times
                pass_rate = stats['passed'] / stats['total']
                if pass_rate < threshold:
                    flaky_tests.append({
                        'test': test_name,
                        'pass_rate': pass_rate,
                        'runs': stats['total']
                    })
        
        passed = len(flaky_tests) == 0
        message = "No flaky tests detected" if passed else f"Found {len(flaky_tests)} flaky tests"
        
        return CheckResult(
            passed=passed,
            message=message,
            details={
                'flaky_tests': flaky_tests,
                'threshold': threshold
            }
        )
    
    @staticmethod
    def check_test_execution_time(execution_times: Dict[str, float], max_time: float = 300.0) -> CheckResult:
        """
        Check if tests complete within time limits.
        
        Args:
            execution_times: Map of test names to execution times (seconds)
            max_time: Maximum allowed execution time
            
        Returns:
            CheckResult indicating compliance
        """
        slow_tests = []
        
        for test_name, duration in execution_times.items():
            if duration > max_time:
                slow_tests.append({
                    'test': test_name,
                    'duration': duration,
                    'max_allowed': max_time
                })
        
        passed = len(slow_tests) == 0
        avg_time = sum(execution_times.values()) / len(execution_times) if execution_times else 0
        
        message = "All tests execute within time limits" if passed else f"{len(slow_tests)} tests exceed time limit"
        
        return CheckResult(
            passed=passed,
            message=message,
            details={
                'slow_tests': slow_tests,
                'avg_execution_time': avg_time,
                'max_allowed_time': max_time
            }
        )
