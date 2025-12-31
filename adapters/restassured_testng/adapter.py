"""
RestAssured + TestNG adapter for CrossBridge.

Executes REST API tests using RestAssured with TestNG framework.
"""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..common.base import BaseTestAdapter, TestResult
from ..common.models import TestMetadata
from .config import RestAssuredConfig
from .extractor import RestAssuredExtractor
from .detector import RestAssuredDetector


class RestAssuredTestNGAdapter(BaseTestAdapter):
    """Adapter for RestAssured + TestNG API tests."""
    
    def __init__(self, project_root: str, config: Optional[RestAssuredConfig] = None):
        """
        Initialize RestAssured + TestNG adapter.
        
        Args:
            project_root: Path to project root directory
            config: Optional RestAssured configuration
        """
        self.project_root = project_root
        self.config = config or RestAssuredConfig(project_root=project_root)
        self.extractor = RestAssuredExtractor(self.config)
        self.detector = RestAssuredDetector()
    
    def discover_tests(
        self,
        tags: Optional[List[str]] = None,
        pattern: Optional[str] = None
    ) -> List[TestMetadata]:
        """
        Discover RestAssured tests without running them.
        
        Args:
            tags: TestNG groups to filter by
            pattern: File pattern to match
            
        Returns:
            List of discovered test metadata
        """
        all_tests = self.extractor.extract_tests(self.project_root)
        
        # Filter by tags (TestNG groups)
        if tags:
            all_tests = [
                test for test in all_tests
                if any(tag in test.tags for tag in tags)
            ]
        
        # Filter by pattern
        if pattern:
            all_tests = [
                test for test in all_tests
                if pattern in test.test_name or pattern in test.file_path
            ]
        
        return all_tests
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> List[TestResult]:
        """
        Execute RestAssured tests.
        
        Args:
            tests: Specific test names to run (format: ClassName#methodName)
            tags: TestNG groups to run
            **kwargs: Additional arguments
            
        Returns:
            List of test results
        """
        # Build command based on build tool
        if self.config.build_tool == "maven":
            cmd = self._build_maven_command(tests, tags)
        elif self.config.build_tool == "gradle":
            cmd = self._build_gradle_command(tests, tags)
        else:
            raise ValueError(f"Unsupported build tool: {self.config.build_tool}")
        
        # Execute tests
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        # Parse results
        return self._parse_results()
    
    def _build_maven_command(
        self,
        tests: Optional[List[str]],
        tags: Optional[List[str]]
    ) -> List[str]:
        """Build Maven command for test execution."""
        cmd = [self.config.maven_command, "test"]
        
        # Add groups filter
        if tags:
            groups_str = ",".join(tags)
            cmd.append(f"-Dgroups={groups_str}")
        
        # Add specific tests
        if tests:
            # Convert test names to Maven format
            test_classes = set()
            for test in tests:
                if '#' in test:
                    class_name = test.split('#')[0]
                    test_classes.add(class_name)
                else:
                    test_classes.add(test)
            
            if test_classes:
                test_str = ",".join(test_classes)
                cmd.append(f"-Dtest={test_str}")
        
        # Add TestNG suite file if specified
        if self.config.testng_xml and not tests and not tags:
            cmd.append(f"-DsuiteXmlFile={self.config.testng_xml}")
        
        # Add parallel execution
        if self.config.parallel_threads > 1:
            cmd.append(f"-Dparallel=methods")
            cmd.append(f"-DthreadCount={self.config.parallel_threads}")
        
        return cmd
    
    def _build_gradle_command(
        self,
        tests: Optional[List[str]],
        tags: Optional[List[str]]
    ) -> List[str]:
        """Build Gradle command for test execution."""
        cmd = [self.config.gradle_command, "test"]
        
        # Add groups filter
        if tags:
            groups_str = ",".join(tags)
            cmd.append(f"--tests")
            cmd.append(f"*[{groups_str}]")
        
        # Add specific tests
        if tests:
            for test in tests:
                cmd.append("--tests")
                if '#' in test:
                    # Convert ClassName#methodName to Gradle format
                    class_name, method_name = test.split('#')
                    cmd.append(f"{class_name}.{method_name}")
                else:
                    cmd.append(test)
        
        # Add parallel execution
        if self.config.parallel_threads > 1:
            cmd.append(f"--parallel")
            cmd.append(f"--max-workers={self.config.parallel_threads}")
        
        return cmd
    
    def _parse_results(self) -> List[TestResult]:
        """Parse test results from Surefire reports or TestNG output."""
        results = []
        
        # Try Surefire reports first (Maven)
        surefire_path = Path(self.project_root) / self.config.surefire_reports
        if surefire_path.exists():
            results.extend(self._parse_surefire_reports(surefire_path))
        
        # Try TestNG output (Gradle or direct TestNG)
        testng_path = Path(self.project_root) / self.config.testng_output
        if testng_path.exists():
            results.extend(self._parse_testng_results(testng_path))
        
        return results
    
    def _parse_surefire_reports(self, reports_dir: Path) -> List[TestResult]:
        """Parse Maven Surefire XML reports."""
        results = []
        
        for xml_file in reports_dir.glob("TEST-*.xml"):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                
                # Parse each test case
                for testcase in root.findall('.//testcase'):
                    class_name = testcase.get('classname', '')
                    method_name = testcase.get('name', '')
                    time_str = testcase.get('time', '0')
                    
                    try:
                        duration_ms = float(time_str) * 1000
                    except ValueError:
                        duration_ms = 0
                    
                    # Determine status
                    failure = testcase.find('failure')
                    error = testcase.find('error')
                    skipped = testcase.find('skipped')
                    
                    if failure is not None:
                        status = 'fail'
                        message = failure.get('message', '')
                    elif error is not None:
                        status = 'error'
                        message = error.get('message', '')
                    elif skipped is not None:
                        status = 'skip'
                        message = skipped.get('message', '')
                    else:
                        status = 'pass'
                        message = ""
                    
                    result = TestResult(
                        name=f"{class_name}#{method_name}",
                        status=status,
                        duration_ms=duration_ms,
                        message=message
                    )
                    results.append(result)
                    
            except Exception as e:
                print(f"Failed to parse {xml_file}: {e}")
                continue
        
        return results
    
    def _parse_testng_results(self, testng_dir: Path) -> List[TestResult]:
        """Parse TestNG XML results."""
        results = []
        
        # TestNG creates testng-results.xml
        results_file = testng_dir / "testng-results.xml"
        if not results_file.exists():
            return results
        
        try:
            tree = ET.parse(results_file)
            root = tree.getroot()
            
            # Parse test methods
            for test_method in root.findall('.//test-method'):
                # Skip configuration methods
                if test_method.get('is-config') == 'true':
                    continue
                
                method_name = test_method.get('name', '')
                class_name = test_method.get('signature', '').split('(')[0].rsplit('.', 1)[0]
                
                # Get duration
                duration_str = test_method.get('duration-ms', '0')
                try:
                    duration_ms = float(duration_str)
                except ValueError:
                    duration_ms = 0
                
                # Determine status
                status_attr = test_method.get('status', 'PASS')
                if status_attr == 'PASS':
                    status = 'pass'
                    message = ""
                elif status_attr == 'FAIL':
                    status = 'fail'
                    exception = test_method.find('.//exception')
                    if exception is not None:
                        message = exception.get('class', '')
                        message_elem = exception.find('message')
                        if message_elem is not None and message_elem.text:
                            message = message_elem.text
                    else:
                        message = ""
                elif status_attr == 'SKIP':
                    status = 'skip'
                    message = ""
                else:
                    status = 'error'
                    message = ""
                
                result = TestResult(
                    name=f"{class_name}#{method_name}",
                    status=status,
                    duration_ms=duration_ms,
                    message=message
                )
                results.append(result)
                
        except Exception as e:
            print(f"Failed to parse TestNG results: {e}")
        
        return results
    
    @staticmethod
    def detect_project(project_root: str) -> bool:
        """
        Detect if project uses RestAssured + TestNG.
        
        Args:
            project_root: Path to project root
            
        Returns:
            True if RestAssured + TestNG is detected
        """
        return RestAssuredDetector.detect(project_root)
