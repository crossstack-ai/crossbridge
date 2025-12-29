"""
Gradle test runner for Selenium-Java tests.

Delegates execution to Gradle test task.
Supports JUnit 4, JUnit 5, and TestNG.
"""

import subprocess
import re
import time
from pathlib import Path
from typing import List, Optional
from .models import TestExecutionRequest, TestExecutionResult


class GradleRunner:
    """
    Executes Selenium tests using Gradle (gradle test command).
    
    Gradle uses the test task to execute JUnit or TestNG tests.
    This runner delegates to native Gradle rather than reimplementing test execution.
    """
    
    def __init__(self, working_dir: str):
        self.working_dir = Path(working_dir)
        self.gradle_cmd = self._detect_gradle_command()
    
    def _detect_gradle_command(self) -> str:
        """Detect Gradle command (gradle or gradlew)."""
        # Check for Gradle wrapper first (preferred)
        if (self.working_dir / "gradlew").exists():
            return "./gradlew"
        elif (self.working_dir / "gradlew.bat").exists():
            return "gradlew.bat"
        return "gradle"
    
    def run_tests(self, request: TestExecutionRequest) -> TestExecutionResult:
        """
        Execute tests using Gradle.
        
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
        Build Gradle command with selective execution options.
        
        Gradle Test Task Parameters:
        - --tests TestClass                : Run specific test class
        - --tests TestClass.method         : Run specific method
        - --tests *Test                    : Pattern matching
        - -DincludeTags=smoke              : Run by JUnit 5 tag
        - -Dgroups=smoke                   : Run by TestNG group
        """
        cmd = [self.gradle_cmd, "test", "--console=plain"]
        
        # Selective test execution
        if request.tests:
            for test in request.tests:
                cmd.extend(["--tests", test])
        
        if request.test_methods:
            for method in request.test_methods:
                # Convert JUnit-style TestClass#method to Gradle format TestClass.method
                gradle_format = method.replace('#', '.')
                cmd.extend(["--tests", gradle_format])
        
        # JUnit 5 tags (requires build.gradle configuration)
        if request.tags:
            tags = ','.join(request.tags)
            cmd.append(f"-DincludeTags={tags}")
        
        # TestNG groups (requires build.gradle configuration)
        if request.groups:
            groups = ','.join(request.groups)
            cmd.append(f"-Dgroups={groups}")
        
        # JUnit 4 categories (requires build.gradle configuration)
        if request.categories:
            categories = ','.join(request.categories)
            cmd.append(f"-Dcategories={categories}")
        
        # Parallel execution
        if request.parallel:
            if request.thread_count:
                cmd.append(f"-Dorg.gradle.workers.max={request.thread_count}")
            cmd.append("-Dparallel=true")
        
        # Additional properties
        if request.properties:
            for key, value in request.properties.items():
                cmd.append(f"-D{key}={value}")
        
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute Gradle command and capture output."""
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
                stderr=f"Error executing Gradle: {str(e)}"
            )
    
    def _parse_result(
        self, 
        result: subprocess.CompletedProcess, 
        execution_time: float,
        working_dir: str
    ) -> TestExecutionResult:
        """
        Parse Gradle output and create TestExecutionResult.
        
        Gradle output format:
        BUILD SUCCESSFUL in 5s
        3 actionable tasks: 3 executed
        
        Or:
        > Task :test FAILED
        5 tests completed, 1 failed
        """
        output = result.stdout + result.stderr
        
        # Parse test statistics from Gradle output
        tests_run = 0
        tests_failed = 0
        tests_skipped = 0
        
        # Look for pattern: "X tests completed, Y failed, Z skipped"
        match = re.search(
            r'(\d+) tests? completed(?:, (\d+) failed)?(?:, (\d+) skipped)?',
            output
        )
        
        if match:
            tests_run = int(match.group(1))
            tests_failed = int(match.group(2)) if match.group(2) else 0
            tests_skipped = int(match.group(3)) if match.group(3) else 0
        else:
            # Alternative pattern: "X tests, Y failures, Z skipped"
            match = re.search(
                r'(\d+) tests?, (\d+) failures?(?:, (\d+) skipped)?',
                output
            )
            if match:
                tests_run = int(match.group(1))
                tests_failed = int(match.group(2))
                tests_skipped = int(match.group(3)) if match.group(3) else 0
        
        tests_passed = tests_run - tests_failed - tests_skipped
        
        # Determine status
        if result.returncode == 0:
            status = "passed"
        elif "BUILD FAILED" in output or "FAILURE" in output:
            if tests_run > 0:
                status = "failed"
            else:
                status = "error"
        else:
            status = "failed"
        
        # Extract error message if present
        error_message = None
        if status == "error":
            error_lines = [line for line in output.split('\n') if 'FAILURE' in line or 'ERROR' in line]
            if error_lines:
                error_message = '\n'.join(error_lines[:5])  # First 5 error lines
        
        # Report path
        report_path = str(Path(working_dir) / "build" / "test-results" / "test")
        
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
    
    def verify_gradle_available(self) -> bool:
        """Check if Gradle is available and working."""
        try:
            result = subprocess.run(
                [self.gradle_cmd, "-version"],
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
