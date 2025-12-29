"""
Maven test runner for Selenium-Java tests.

Delegates execution to Maven Surefire/Failsafe plugins.
Supports JUnit 4, JUnit 5, and TestNG.
"""

import subprocess
import re
import time
from pathlib import Path
from typing import List, Optional
from .models import TestExecutionRequest, TestExecutionResult


class MavenRunner:
    """
    Executes Selenium tests using Maven (mvn test command).
    
    Maven uses:
    - Surefire plugin for unit tests (test phase)
    - Failsafe plugin for integration tests (verify phase)
    
    This runner delegates to native Maven rather than reimplementing test execution.
    """
    
    def __init__(self, working_dir: str):
        self.working_dir = Path(working_dir)
        self.maven_cmd = self._detect_maven_command()
    
    def _detect_maven_command(self) -> str:
        """Detect Maven command (mvn or mvnw)."""
        # Use mvn by default
        return "mvn"
    
    def run_tests(self, request: TestExecutionRequest) -> TestExecutionResult:
        """
        Execute tests using Maven.
        
        Args:
            request: Test execution request with selective execution options
            
        Returns:
            TestExecutionResult with status, exit code, and reports
        """
        cmd = self._build_command(request)
        
        start_time = time.time()
        result = self._execute_command(cmd)
        execution_time = time.time() - start_time
        
        return self._parse_result(result, execution_time, request.working_dir)
    
    def _build_command(self, request: TestExecutionRequest) -> List[str]:
        """
        Build Maven command with selective execution options.
        
        Maven Surefire Parameters:
        - -Dtest=TestClass              : Run specific test class
        - -Dtest=TestClass#method       : Run specific method
        - -Dtest=Test1,Test2            : Run multiple tests
        - -Dgroups=smoke                : Run by JUnit 5 tag or TestNG group
        - -DexcludedGroups=slow         : Exclude by tag/group
        - -Dcategories=Smoke            : Run by JUnit 4 category
        """
        cmd = [self.maven_cmd, "test", "-B"]  # -B = batch mode (non-interactive)
        
        # Selective test execution
        if request.tests or request.test_methods:
            test_patterns = []
            
            if request.tests:
                test_patterns.extend(request.tests)
            
            if request.test_methods:
                test_patterns.extend(request.test_methods)
            
            cmd.append(f"-Dtest={','.join(test_patterns)}")
        
        # JUnit 5 tags or TestNG groups
        if request.tags:
            cmd.append(f"-Dgroups={','.join(request.tags)}")
        
        if request.groups:
            cmd.append(f"-Dgroups={','.join(request.groups)}")
        
        # JUnit 4 categories
        if request.categories:
            cmd.append(f"-Dcategories={','.join(request.categories)}")
        
        # Parallel execution
        if request.parallel:
            cmd.append("-Dparallel=methods")
            if request.thread_count:
                cmd.append(f"-DthreadCount={request.thread_count}")
        
        # Additional properties
        if request.properties:
            for key, value in request.properties.items():
                cmd.append(f"-D{key}={value}")
        
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute Maven command and capture output."""
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            return result
        except subprocess.TimeoutExpired as e:
            # Handle timeout
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout=str(e.stdout) if e.stdout else "",
                stderr=f"Test execution timed out after {e.timeout} seconds"
            )
        except Exception as e:
            # Handle other errors
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=f"Error executing Maven: {str(e)}"
            )
    
    def _parse_result(
        self, 
        result: subprocess.CompletedProcess, 
        execution_time: float,
        working_dir: str
    ) -> TestExecutionResult:
        """
        Parse Maven output and create TestExecutionResult.
        
        Maven output format:
        [INFO] Tests run: 5, Failures: 1, Errors: 0, Skipped: 0
        """
        output = result.stdout + result.stderr
        
        # Parse test statistics from Maven output
        tests_run = 0
        tests_failed = 0
        tests_skipped = 0
        
        # Look for pattern: "Tests run: X, Failures: Y, Errors: Z, Skipped: W"
        match = re.search(
            r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)',
            output
        )
        
        if match:
            tests_run = int(match.group(1))
            failures = int(match.group(2))
            errors = int(match.group(3))
            tests_skipped = int(match.group(4))
            tests_failed = failures + errors
        
        tests_passed = tests_run - tests_failed - tests_skipped
        
        # Determine status
        if result.returncode == 0:
            status = "passed"
        elif "BUILD FAILURE" in output or "BUILD ERROR" in output:
            status = "error"
        else:
            status = "failed"
        
        # Extract error message if present
        error_message = None
        if status == "error":
            error_lines = [line for line in output.split('\n') if 'ERROR' in line]
            if error_lines:
                error_message = '\n'.join(error_lines[:5])  # First 5 error lines
        
        # Report path
        report_path = str(Path(working_dir) / "target" / "surefire-reports")
        
        return TestExecutionResult(
            status=status,
            exit_code=result.returncode,
            report_path=report_path if Path(report_path).exists() else None,
            raw_output=output,
            tests_run=tests_run,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            tests_skipped=tests_skipped,
            execution_time=execution_time,
            error_message=error_message
        )
    
    def verify_maven_available(self) -> bool:
        """Check if Maven is available and working."""
        try:
            result = subprocess.run(
                [self.maven_cmd, "-version"],
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
