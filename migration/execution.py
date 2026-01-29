"""
Automated Test Execution Module

Executes generated tests automatically to verify they work correctly.
Provides execution reports and identifies runtime issues.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time


class ExecutionStatus(Enum):
    """Test execution status"""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestExecutionResult:
    """Result of a single test execution"""
    test_name: str
    status: ExecutionStatus
    duration: float
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class ExecutionReport:
    """Complete execution report"""
    framework: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    results: List[TestExecutionResult] = field(default_factory=list)
    
    def compute_stats(self):
        """Compute statistics from results"""
        self.total = len(self.results)
        self.passed = len([r for r in self.results if r.status == ExecutionStatus.SUCCESS])
        self.failed = len([r for r in self.results if r.status == ExecutionStatus.FAILURE])
        self.errors = len([r for r in self.results if r.status == ExecutionStatus.ERROR])
        self.skipped = len([r for r in self.results if r.status == ExecutionStatus.SKIPPED])
        self.duration = sum(r.duration for r in self.results)
    
    def get_pass_rate(self) -> float:
        """Calculate pass rate percentage"""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100


class PytestExecutor:
    """
    Executes pytest-bdd tests.
    
    Runs generated pytest tests and collects results.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """Check if required dependencies are installed"""
        missing = []
        
        try:
            subprocess.run(["pytest", "--version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing.append("pytest")
        
        try:
            result = subprocess.run(
                ["python", "-c", "import pytest_bdd"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                missing.append("pytest-bdd")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing.append("pytest-bdd")
        
        try:
            result = subprocess.run(
                ["python", "-c", "import playwright"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                missing.append("playwright")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing.append("playwright")
        
        return len(missing) == 0, missing
    
    def execute_tests(
        self,
        dry_run: bool = False,
        timeout: int = 300
    ) -> ExecutionReport:
        """
        Execute pytest tests.
        
        Args:
            dry_run: If True, collect tests without running them
            timeout: Timeout in seconds for test execution
            
        Returns:
            ExecutionReport with results
        """
        report = ExecutionReport(framework="pytest-bdd")
        
        # Check dependencies first
        deps_ok, missing = self.check_dependencies()
        if not deps_ok:
            report.results.append(TestExecutionResult(
                test_name="dependency_check",
                status=ExecutionStatus.ERROR,
                duration=0.0,
                error_message=f"Missing dependencies: {', '.join(missing)}"
            ))
            report.compute_stats()
            return report
        
        # Build pytest command
        cmd = ["pytest", str(self.output_dir), "-v", "--tb=short", "--json-report", "--json-report-file=report.json"]
        
        if dry_run:
            cmd.append("--collect-only")
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.output_dir,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            duration = time.time() - start_time
            
            # Parse output
            self._parse_pytest_output(result, report, duration)
            
        except subprocess.TimeoutExpired:
            report.results.append(TestExecutionResult(
                test_name="execution",
                status=ExecutionStatus.TIMEOUT,
                duration=timeout,
                error_message=f"Test execution timed out after {timeout}s"
            ))
        except Exception as e:
            report.results.append(TestExecutionResult(
                test_name="execution",
                status=ExecutionStatus.ERROR,
                duration=0.0,
                error_message=f"Execution failed: {str(e)}"
            ))
        
        report.compute_stats()
        return report
    
    def _parse_pytest_output(self, result, report: ExecutionReport, duration: float):
        """Parse pytest output"""
        # Try to parse JSON report if available
        json_report = self.output_dir / "report.json"
        if json_report.exists():
            try:
                with open(json_report) as f:
                    data = json.load(f)
                    
                for test in data.get("tests", []):
                    status = ExecutionStatus.SUCCESS
                    if test.get("outcome") == "passed":
                        status = ExecutionStatus.SUCCESS
                    elif test.get("outcome") == "failed":
                        status = ExecutionStatus.FAILURE
                    elif test.get("outcome") == "skipped":
                        status = ExecutionStatus.SKIPPED
                    else:
                        status = ExecutionStatus.ERROR
                    
                    report.results.append(TestExecutionResult(
                        test_name=test.get("nodeid", "unknown"),
                        status=status,
                        duration=test.get("duration", 0.0),
                        error_message=test.get("call", {}).get("longrepr") if status != ExecutionStatus.SUCCESS else None
                    ))
                
                report.duration = data.get("duration", duration)
                return
            except (IOError, json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Failed to parse pytest JSON report: {e}")
        
        # Fallback: parse text output
        output = result.stdout
        if "collected" in output:
            # Tests were collected
            if result.returncode == 0:
                status = ExecutionStatus.SUCCESS
            else:
                status = ExecutionStatus.FAILURE
            
            report.results.append(TestExecutionResult(
                test_name="test_suite",
                status=status,
                duration=duration,
                stdout=output,
                stderr=result.stderr
            ))


class RobotExecutor:
    """
    Executes Robot Framework tests.
    
    Runs generated Robot tests and collects results.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """Check if required dependencies are installed"""
        missing = []
        
        try:
            subprocess.run(["robot", "--version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing.append("robotframework")
        
        try:
            result = subprocess.run(
                ["python", "-c", "import Browser"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                missing.append("robotframework-browser")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing.append("robotframework-browser")
        
        return len(missing) == 0, missing
    
    def execute_tests(
        self,
        dry_run: bool = False,
        timeout: int = 300
    ) -> ExecutionReport:
        """
        Execute Robot Framework tests.
        
        Args:
            dry_run: If True, perform dry run
            timeout: Timeout in seconds for test execution
            
        Returns:
            ExecutionReport with results
        """
        report = ExecutionReport(framework="robot-framework")
        
        # Check dependencies first
        deps_ok, missing = self.check_dependencies()
        if not deps_ok:
            report.results.append(TestExecutionResult(
                test_name="dependency_check",
                status=ExecutionStatus.ERROR,
                duration=0.0,
                error_message=f"Missing dependencies: {', '.join(missing)}"
            ))
            report.compute_stats()
            return report
        
        # Build robot command
        tests_dir = self.output_dir / "tests"
        cmd = ["robot", "--outputdir", str(self.output_dir / "results")]
        
        if dry_run:
            cmd.append("--dryrun")
        
        cmd.append(str(tests_dir))
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            duration = time.time() - start_time
            
            # Parse output
            self._parse_robot_output(result, report, duration)
            
        except subprocess.TimeoutExpired:
            report.results.append(TestExecutionResult(
                test_name="execution",
                status=ExecutionStatus.TIMEOUT,
                duration=timeout,
                error_message=f"Test execution timed out after {timeout}s"
            ))
        except Exception as e:
            report.results.append(TestExecutionResult(
                test_name="execution",
                status=ExecutionStatus.ERROR,
                duration=0.0,
                error_message=f"Execution failed: {str(e)}"
            ))
        
        report.compute_stats()
        return report
    
    def _parse_robot_output(self, result, report: ExecutionReport, duration: float):
        """Parse Robot Framework output"""
        # Try to parse output.xml if available
        output_xml = self.output_dir / "results" / "output.xml"
        if output_xml.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(output_xml)
                root = tree.getroot()
                
                # Parse test cases
                for test in root.findall(".//test"):
                    test_name = test.get("name", "unknown")
                    status_elem = test.find("status")
                    
                    if status_elem is not None:
                        status_text = status_elem.get("status", "FAIL")
                        if status_text == "PASS":
                            status = ExecutionStatus.SUCCESS
                        elif status_text == "SKIP":
                            status = ExecutionStatus.SKIPPED
                        else:
                            status = ExecutionStatus.FAILURE
                    else:
                        status = ExecutionStatus.ERROR
                    
                    report.results.append(TestExecutionResult(
                        test_name=test_name,
                        status=status,
                        duration=0.0  # Robot doesn't provide per-test duration easily
                    ))
                
                report.duration = duration
                return
            except (IOError, ET.ParseError, KeyError) as e:
                logger.debug(f"Failed to parse Robot Framework XML report: {e}")
        
        # Fallback: parse text output
        output = result.stdout
        if result.returncode == 0:
            status = ExecutionStatus.SUCCESS
        else:
            status = ExecutionStatus.FAILURE
        
        report.results.append(TestExecutionResult(
            test_name="test_suite",
            status=status,
            duration=duration,
            stdout=output,
            stderr=result.stderr
        ))


class TestExecutor:
    """
    High-level test execution orchestrator.
    
    Executes tests for any migration target.
    """
    
    def __init__(self):
        self.pytest_executor = None
        self.robot_executor = None
    
    def execute(
        self,
        output_dir: Path,
        framework: str,
        dry_run: bool = False,
        timeout: int = 300
    ) -> ExecutionReport:
        """
        Execute tests for given framework.
        
        Args:
            output_dir: Directory containing generated tests
            framework: Framework type ("pytest-bdd" or "robot-framework")
            dry_run: If True, perform dry run only
            timeout: Execution timeout in seconds
            
        Returns:
            ExecutionReport with results
        """
        if framework == "pytest-bdd":
            executor = PytestExecutor(output_dir)
            return executor.execute_tests(dry_run=dry_run, timeout=timeout)
        elif framework == "robot-framework":
            executor = RobotExecutor(output_dir)
            return executor.execute_tests(dry_run=dry_run, timeout=timeout)
        else:
            report = ExecutionReport(framework=framework)
            report.results.append(TestExecutionResult(
                test_name="execution",
                status=ExecutionStatus.ERROR,
                duration=0.0,
                error_message=f"Unsupported framework: {framework}"
            ))
            report.compute_stats()
            return report
    
    def print_report(self, report: ExecutionReport, verbose: bool = True):
        """Print execution report to console"""
        print("\n" + "=" * 70)
        print(f"TEST EXECUTION REPORT - {report.framework.upper()}")
        print("=" * 70)
        
        print(f"\nResults:")
        print(f"  Total: {report.total}")
        print(f"  Passed: {report.passed} ✅")
        print(f"  Failed: {report.failed} ❌")
        print(f"  Errors: {report.errors} 🔥")
        print(f"  Skipped: {report.skipped} ⏭️")
        print(f"  Duration: {report.duration:.2f}s")
        print(f"  Pass Rate: {report.get_pass_rate():.1f}%")
        
        if verbose and report.results:
            print("\nTest Details:")
            for result in report.results:
                icon = "✅" if result.status == ExecutionStatus.SUCCESS else "❌" if result.status == ExecutionStatus.FAILURE else "🔥"
                print(f"\n{icon} {result.test_name}")
                print(f"   Status: {result.status.value}")
                print(f"   Duration: {result.duration:.3f}s")
                if result.error_message:
                    print(f"   Error: {result.error_message}")
        
        print("\n" + "=" * 70)
