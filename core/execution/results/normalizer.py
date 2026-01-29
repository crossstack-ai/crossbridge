"""
Result normalization across test frameworks.

Converts framework-specific results to unified TestResult format.
Supports pytest, JUnit, TestNG, Robot Framework, Cypress, Playwright, etc.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import xml.etree.ElementTree as ET

from .models import (
    TestResult,
    TestRunResult,
    TestStatus,
    FrameworkType,
    ResultMetadata,
)
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.EXECUTION)


class FrameworkAdapter(ABC):
    """
    Base adapter for framework-specific result parsing.
    
    Each framework implements this to convert its results to unified format.
    """
    
    @abstractmethod
    def parse_results(self, result_file: Path) -> TestRunResult:
        """Parse framework-specific result file."""
        pass
    
    @abstractmethod
    def normalize_status(self, status: str) -> TestStatus:
        """Normalize framework-specific status to TestStatus."""
        pass
    
    @abstractmethod
    def get_framework_type(self) -> FrameworkType:
        """Get framework type."""
        pass


class PytestAdapter(FrameworkAdapter):
    """Adapter for pytest results (JSON format)."""
    
    def get_framework_type(self) -> FrameworkType:
        return FrameworkType.PYTEST
    
    def normalize_status(self, status: str) -> TestStatus:
        """Normalize pytest status."""
        status_map = {
            'passed': TestStatus.PASSED,
            'failed': TestStatus.FAILED,
            'skipped': TestStatus.SKIPPED,
            'error': TestStatus.ERROR,
            'xfailed': TestStatus.XFAIL,
            'xpassed': TestStatus.XPASS,
        }
        return status_map.get(status.lower(), TestStatus.UNKNOWN)
    
    def parse_results(self, result_file: Path) -> TestRunResult:
        """Parse pytest JSON report."""
        logger.debug(f"Parsing pytest results from {result_file}")
        
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        run_id = f"pytest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        tests = []
        
        for test_data in data.get('tests', []):
            test_result = TestResult(
                test_id=test_data.get('nodeid', ''),
                test_name=test_data.get('name', ''),
                test_file=Path(test_data.get('file', '')) if test_data.get('file') else None,
                test_class=test_data.get('class'),
                test_method=test_data.get('function'),
                status=self.normalize_status(test_data.get('outcome', 'unknown')),
                duration=test_data.get('duration', 0.0),
                error_message=test_data.get('call', {}).get('longrepr'),
                tags=set(test_data.get('markers', [])),
                framework_data={'pytest': test_data}
            )
            tests.append(test_result)
        
        # Extract metadata
        metadata = ResultMetadata(
            framework=FrameworkType.PYTEST,
            framework_version=data.get('pytest_version'),
            python_version=data.get('python_version'),
        )
        
        return TestRunResult(
            run_id=run_id,
            start_time=datetime.fromtimestamp(data.get('created', 0)),
            duration=data.get('duration', 0.0),
            tests=tests,
            metadata=metadata,
        )


class JUnitAdapter(FrameworkAdapter):
    """Adapter for JUnit XML results (JUnit 4/5)."""
    
    def __init__(self, version: int = 5):
        self.version = version
    
    def get_framework_type(self) -> FrameworkType:
        return FrameworkType.JUNIT5 if self.version == 5 else FrameworkType.JUNIT4
    
    def normalize_status(self, status: str) -> TestStatus:
        """Normalize JUnit status."""
        status_map = {
            'success': TestStatus.PASSED,
            'failure': TestStatus.FAILED,
            'error': TestStatus.ERROR,
            'skipped': TestStatus.SKIPPED,
        }
        return status_map.get(status.lower(), TestStatus.UNKNOWN)
    
    def parse_results(self, result_file: Path) -> TestRunResult:
        """Parse JUnit XML report."""
        logger.debug(f"Parsing JUnit results from {result_file}")
        
        tree = ET.parse(result_file)
        root = tree.getroot()
        
        run_id = f"junit{self.version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        tests = []
        
        # Handle both <testsuite> root and <testsuites> root
        testsuites = root.findall('.//testsuite') if root.tag == 'testsuites' else [root]
        
        for testsuite in testsuites:
            suite_name = testsuite.get('name', '')
            
            for testcase in testsuite.findall('testcase'):
                # Determine status
                if testcase.find('failure') is not None:
                    status = TestStatus.FAILED
                    error_elem = testcase.find('failure')
                    error_message = error_elem.get('message', '')
                    error_type = error_elem.get('type', '')
                    stacktrace = error_elem.text
                elif testcase.find('error') is not None:
                    status = TestStatus.ERROR
                    error_elem = testcase.find('error')
                    error_message = error_elem.get('message', '')
                    error_type = error_elem.get('type', '')
                    stacktrace = error_elem.text
                elif testcase.find('skipped') is not None:
                    status = TestStatus.SKIPPED
                    error_message = None
                    error_type = None
                    stacktrace = None
                else:
                    status = TestStatus.PASSED
                    error_message = None
                    error_type = None
                    stacktrace = None
                
                test_result = TestResult(
                    test_id=f"{testcase.get('classname', '')}.{testcase.get('name', '')}",
                    test_name=testcase.get('name', ''),
                    test_class=testcase.get('classname', ''),
                    test_method=testcase.get('name', ''),
                    status=status,
                    duration=float(testcase.get('time', 0)),
                    error_message=error_message,
                    error_type=error_type,
                    stacktrace=stacktrace,
                    framework_data={'junit': dict(testcase.attrib)}
                )
                tests.append(test_result)
        
        metadata = ResultMetadata(
            framework=self.get_framework_type(),
        )
        
        return TestRunResult(
            run_id=run_id,
            start_time=datetime.now(),
            tests=tests,
            metadata=metadata,
        )


class TestNGAdapter(FrameworkAdapter):
    """Adapter for TestNG XML results."""
    
    def get_framework_type(self) -> FrameworkType:
        return FrameworkType.TESTNG
    
    def normalize_status(self, status: str) -> TestStatus:
        """Normalize TestNG status."""
        status_map = {
            'pass': TestStatus.PASSED,
            'fail': TestStatus.FAILED,
            'skip': TestStatus.SKIPPED,
        }
        return status_map.get(status.lower(), TestStatus.UNKNOWN)
    
    def parse_results(self, result_file: Path) -> TestRunResult:
        """Parse TestNG XML report."""
        logger.debug(f"Parsing TestNG results from {result_file}")
        
        tree = ET.parse(result_file)
        root = tree.getroot()
        
        run_id = f"testng_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        tests = []
        
        for suite in root.findall('.//test'):
            for test_class in suite.findall('.//class'):
                class_name = test_class.get('name', '')
                
                for test_method in test_class.findall('test-method'):
                    if test_method.get('is-config') == 'true':
                        continue  # Skip config methods
                    
                    status_str = test_method.get('status', 'PASS')
                    duration_ms = int(test_method.get('duration-ms', 0))
                    
                    # Get exception if failed
                    exception = test_method.find('exception')
                    error_message = None
                    error_type = None
                    stacktrace = None
                    
                    if exception is not None:
                        error_message = exception.find('message').text if exception.find('message') is not None else None
                        error_type = exception.get('class')
                        stacktrace = exception.find('full-stacktrace').text if exception.find('full-stacktrace') is not None else None
                    
                    # Get groups/tags
                    tags = set()
                    groups = test_method.find('groups')
                    if groups is not None:
                        tags = {g.get('name') for g in groups.findall('group')}
                    
                    test_result = TestResult(
                        test_id=f"{class_name}.{test_method.get('name', '')}",
                        test_name=test_method.get('name', ''),
                        test_class=class_name,
                        test_method=test_method.get('name', ''),
                        status=self.normalize_status(status_str),
                        duration=duration_ms / 1000.0,  # Convert to seconds
                        error_message=error_message,
                        error_type=error_type,
                        stacktrace=stacktrace,
                        tags=tags,
                        framework_data={'testng': dict(test_method.attrib)}
                    )
                    tests.append(test_result)
        
        metadata = ResultMetadata(
            framework=FrameworkType.TESTNG,
        )
        
        return TestRunResult(
            run_id=run_id,
            start_time=datetime.now(),
            tests=tests,
            metadata=metadata,
        )


class RobotAdapter(FrameworkAdapter):
    """Adapter for Robot Framework XML results."""
    
    def get_framework_type(self) -> FrameworkType:
        return FrameworkType.ROBOT
    
    def normalize_status(self, status: str) -> TestStatus:
        """Normalize Robot Framework status."""
        return TestStatus.PASSED if status.upper() == 'PASS' else TestStatus.FAILED
    
    def parse_results(self, result_file: Path) -> TestRunResult:
        """Parse Robot Framework output.xml."""
        logger.debug(f"Parsing Robot Framework results from {result_file}")
        
        tree = ET.parse(result_file)
        root = tree.getroot()
        
        run_id = f"robot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        tests = []
        
        for suite in root.findall('.//suite'):
            suite_name = suite.get('name', '')
            
            for test in suite.findall('.//test'):
                status_elem = test.find('status')
                status_str = status_elem.get('status', 'FAIL') if status_elem is not None else 'FAIL'
                
                # Parse timestamps
                start_time_str = status_elem.get('starttime') if status_elem is not None else None
                end_time_str = status_elem.get('endtime') if status_elem is not None else None
                
                # Calculate duration (Robot uses elapsed ms)
                duration = 0.0
                if status_elem is not None and status_elem.get('elapsed'):
                    duration = int(status_elem.get('elapsed')) / 1000.0
                
                # Get error message if failed
                error_message = None
                if status_str == 'FAIL':
                    msg_elem = test.find('.//msg')
                    if msg_elem is not None:
                        error_message = msg_elem.text
                
                # Get tags
                tags = set()
                for tag in test.findall('.//tag'):
                    if tag.text:
                        tags.add(tag.text)
                
                test_result = TestResult(
                    test_id=f"{suite_name}.{test.get('name', '')}",
                    test_name=test.get('name', ''),
                    test_class=suite_name,
                    status=self.normalize_status(status_str),
                    duration=duration,
                    error_message=error_message,
                    tags=tags,
                    framework_data={'robot': dict(test.attrib)}
                )
                tests.append(test_result)
        
        metadata = ResultMetadata(
            framework=FrameworkType.ROBOT,
        )
        
        return TestRunResult(
            run_id=run_id,
            start_time=datetime.now(),
            tests=tests,
            metadata=metadata,
        )


class ResultNormalizer:
    """
    Main normalizer that handles all frameworks.
    
    Automatically detects framework and normalizes results.
    """
    
    def __init__(self):
        self.adapters: Dict[FrameworkType, FrameworkAdapter] = {
            FrameworkType.PYTEST: PytestAdapter(),
            FrameworkType.JUNIT4: JUnitAdapter(version=4),
            FrameworkType.JUNIT5: JUnitAdapter(version=5),
            FrameworkType.TESTNG: TestNGAdapter(),
            FrameworkType.ROBOT: RobotAdapter(),
        }
        self.logger = get_logger(__name__, category=LogCategory.EXECUTION)
    
    def detect_framework(self, result_file: Path) -> Optional[FrameworkType]:
        """
        Auto-detect framework from result file.
        
        Args:
            result_file: Path to result file
            
        Returns:
            Detected framework type or None
        """
        filename = result_file.name.lower()
        
        # Check file extension and name patterns
        if filename.endswith('.json'):
            # Try to read and check structure
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    if 'pytest_version' in data or 'tests' in data:
                        return FrameworkType.PYTEST
            except (IOError, json.JSONDecodeError, KeyError) as e:
                self.logger.debug(f"Failed to parse JSON result file: {e}")
        
        elif filename.endswith('.xml'):
            # Parse XML and check root element
            try:
                tree = ET.parse(result_file)
                root = tree.getroot()
                
                if root.tag == 'robot':
                    return FrameworkType.ROBOT
                elif root.tag in ['testsuites', 'testsuite']:
                    # Could be JUnit or TestNG
                    if 'testng' in filename:
                        return FrameworkType.TESTNG
                    return FrameworkType.JUNIT5  # Default to JUnit5
                elif root.tag == 'testng-results':
                    return FrameworkType.TESTNG
            except (IOError, ET.ParseError) as e:
                self.logger.debug(f"Failed to parse XML result file: {e}")
        
        self.logger.warning(f"Could not detect framework for {result_file}")
        return None
    
    def normalize(
        self,
        result_file: Path,
        framework: Optional[FrameworkType] = None
    ) -> Optional[TestRunResult]:
        """
        Normalize test results from any framework.
        
        Args:
            result_file: Path to result file
            framework: Framework type (auto-detected if None)
            
        Returns:
            Normalized TestRunResult or None if failed
        """
        # Auto-detect if not specified
        if framework is None:
            framework = self.detect_framework(result_file)
            if framework is None:
                self.logger.error(f"Could not detect framework for {result_file}")
                return None
        
        # Get adapter
        adapter = self.adapters.get(framework)
        if adapter is None:
            self.logger.error(f"No adapter for framework {framework}")
            return None
        
        # Parse results
        try:
            self.logger.info(f"Normalizing {framework.value} results from {result_file}")
            result = adapter.parse_results(result_file)
            self.logger.success(f"Normalized {len(result.tests)} tests from {framework.value}")
            return result
        except Exception as e:
            self.logger.exception(f"Failed to normalize results from {result_file}")
            return None
    
    def normalize_batch(
        self,
        result_files: List[Path],
        framework: Optional[FrameworkType] = None
    ) -> List[TestRunResult]:
        """
        Normalize multiple result files.
        
        Args:
            result_files: List of result file paths
            framework: Framework type (auto-detected if None)
            
        Returns:
            List of normalized results
        """
        results = []
        for result_file in result_files:
            result = self.normalize(result_file, framework)
            if result:
                results.append(result)
        
        self.logger.info(f"Normalized {len(results)}/{len(result_files)} result files")
        return results
