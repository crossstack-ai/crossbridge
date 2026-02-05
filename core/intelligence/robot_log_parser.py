"""
Robot Framework Log Parser.

Parses Robot Framework output.xml files to extract detailed execution information,
including test results, keywords, variables, and failure signals.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class RobotStatus(Enum):
    """Robot test/keyword status"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


@dataclass
class RobotKeyword:
    """Represents a Robot Framework keyword execution."""
    name: str
    library: str
    status: RobotStatus
    start_time: str
    end_time: str
    elapsed_ms: int
    arguments: List[str]
    messages: List[str]
    error_message: Optional[str] = None


@dataclass
class RobotTest:
    """Represents a Robot Framework test execution."""
    name: str
    suite: str
    status: RobotStatus
    start_time: str
    end_time: str
    elapsed_ms: int
    tags: List[str]
    keywords: List[RobotKeyword]
    setup: Optional[RobotKeyword] = None
    teardown: Optional[RobotKeyword] = None
    error_message: Optional[str] = None
    critical: bool = True


@dataclass
class RobotSuite:
    """Represents a Robot Framework test suite."""
    name: str
    source: str
    status: RobotStatus
    start_time: str
    end_time: str
    elapsed_ms: int
    tests: List[RobotTest]
    suites: List['RobotSuite']  # Nested suites
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0


class RobotLogParser:
    """
    Parser for Robot Framework output.xml files.
    
    Extracts comprehensive execution information from Robot Framework logs.
    """
    
    def __init__(self):
        """Initialize the parser."""
        self.root_suite: Optional[RobotSuite] = None
        self.all_tests: List[RobotTest] = []
        self.failed_tests: List[RobotTest] = []
    
    def parse(self, xml_path: Path) -> RobotSuite:
        """
        Parse Robot Framework output.xml file.
        
        Args:
            xml_path: Path to output.xml file
            
        Returns:
            Root RobotSuite with all execution data
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Parse root suite
            suite_element = root.find('suite')
            if suite_element is None:
                logger.warning("No suite element found in output.xml")
                return None
            
            self.root_suite = self._parse_suite(suite_element)
            
            # Collect all tests
            self._collect_tests(self.root_suite)
            
            logger.info(f"Parsed {len(self.all_tests)} tests from {xml_path}")
            return self.root_suite
        
        except Exception as e:
            logger.error(f"Failed to parse {xml_path}: {e}")
            return None
    
    def _parse_suite(self, suite_element: ET.Element) -> RobotSuite:
        """Parse a suite element."""
        # Get suite metadata
        name = suite_element.get('name', 'Unknown')
        source = suite_element.get('source', '')
        
        # Parse status
        status_element = suite_element.find('status')
        status = RobotStatus(status_element.get('status', 'FAIL')) if status_element is not None else RobotStatus.FAIL
        start_time = status_element.get('starttime', '') if status_element is not None else ''
        end_time = status_element.get('endtime', '') if status_element is not None else ''
        elapsed_ms = int(status_element.get('elapsedtime', '0')) if status_element is not None else 0
        
        # Parse tests
        tests = []
        for test_element in suite_element.findall('test'):
            test = self._parse_test(test_element, name)
            tests.append(test)
        
        # Parse nested suites
        nested_suites = []
        for nested_suite_element in suite_element.findall('suite'):
            nested_suite = self._parse_suite(nested_suite_element)
            nested_suites.append(nested_suite)
        
        # Calculate statistics
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests if t.status == RobotStatus.PASS)
        failed_tests = sum(1 for t in tests if t.status == RobotStatus.FAIL)
        
        # Add nested suite stats
        for nested in nested_suites:
            total_tests += nested.total_tests
            passed_tests += nested.passed_tests
            failed_tests += nested.failed_tests
        
        return RobotSuite(
            name=name,
            source=source,
            status=status,
            start_time=start_time,
            end_time=end_time,
            elapsed_ms=elapsed_ms,
            tests=tests,
            suites=nested_suites,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
        )
    
    def _parse_test(self, test_element: ET.Element, suite_name: str) -> RobotTest:
        """Parse a test element."""
        # Get test metadata
        name = test_element.get('name', 'Unknown')
        
        # Parse status
        status_element = test_element.find('status')
        status = RobotStatus(status_element.get('status', 'FAIL')) if status_element is not None else RobotStatus.FAIL
        start_time = status_element.get('starttime', '') if status_element is not None else ''
        end_time = status_element.get('endtime', '') if status_element is not None else ''
        elapsed_ms = int(status_element.get('elapsedtime', '0')) if status_element is not None else 0
        error_message = status_element.text if status_element is not None and status == RobotStatus.FAIL else None
        
        # Parse tags (check both direct children and nested in tags element)
        tags = []
        for tag_element in test_element.findall('tag'):
            tags.append(tag_element.text or '')
        for tag_element in test_element.findall('tags/tag'):
            tags.append(tag_element.text or '')
        
        # Check if critical
        critical = 'force-tags' not in tags and 'non-critical' not in tags
        
        # Parse keywords
        keywords = []
        for kw_element in test_element.findall('kw'):
            keyword = self._parse_keyword(kw_element)
            keywords.append(keyword)
        
        # Parse setup and teardown
        setup = None
        teardown = None
        
        setup_element = test_element.find('kw[@type="setup"]')
        if setup_element is not None:
            setup = self._parse_keyword(setup_element)
        
        teardown_element = test_element.find('kw[@type="teardown"]')
        if teardown_element is not None:
            teardown = self._parse_keyword(teardown_element)
        
        return RobotTest(
            name=name,
            suite=suite_name,
            status=status,
            start_time=start_time,
            end_time=end_time,
            elapsed_ms=elapsed_ms,
            tags=tags,
            keywords=keywords,
            setup=setup,
            teardown=teardown,
            error_message=error_message,
            critical=critical,
        )
    
    def _parse_keyword(self, kw_element: ET.Element) -> RobotKeyword:
        """Parse a keyword element."""
        # Get keyword metadata
        name = kw_element.get('name', 'Unknown')
        library = kw_element.get('library', '')
        
        # Parse status
        status_element = kw_element.find('status')
        status = RobotStatus(status_element.get('status', 'FAIL')) if status_element is not None else RobotStatus.FAIL
        start_time = status_element.get('starttime', '') if status_element is not None else ''
        end_time = status_element.get('endtime', '') if status_element is not None else ''
        elapsed_ms = int(status_element.get('elapsedtime', '0')) if status_element is not None else 0
        error_message = status_element.text if status_element is not None and status == RobotStatus.FAIL else None
        
        # Parse arguments (direct children, not nested)
        arguments = []
        for arg_element in kw_element.findall('arg'):
            arguments.append(arg_element.text or '')
        
        # Parse messages
        messages = []
        for msg_element in kw_element.findall('msg'):
            msg_text = msg_element.text or ''
            if msg_text:
                messages.append(msg_text)
        
        return RobotKeyword(
            name=name,
            library=library,
            status=status,
            start_time=start_time,
            end_time=end_time,
            elapsed_ms=elapsed_ms,
            arguments=arguments,
            messages=messages,
            error_message=error_message,
        )
    
    def _collect_tests(self, suite: RobotSuite):
        """Recursively collect all tests from suite and nested suites."""
        self.all_tests.extend(suite.tests)
        
        for test in suite.tests:
            if test.status == RobotStatus.FAIL:
                self.failed_tests.append(test)
        
        for nested_suite in suite.suites:
            self._collect_tests(nested_suite)
    
    def get_test_by_name(self, test_name: str) -> Optional[RobotTest]:
        """Find a test by its name."""
        for test in self.all_tests:
            if test.name == test_name:
                return test
        return None
    
    def get_failed_keywords(self) -> List[RobotKeyword]:
        """Get all failed keywords across all tests."""
        failed_keywords = []
        
        for test in self.all_tests:
            for keyword in test.keywords:
                if keyword.status == RobotStatus.FAIL:
                    failed_keywords.append(keyword)
        
        return failed_keywords
    
    def get_failed_tests(self) -> List[RobotTest]:
        """Get all failed tests with full details."""
        return [test for test in self.all_tests if test.status == RobotStatus.FAIL]
    
    def get_slowest_tests(self, count: int = 10) -> List[RobotTest]:
        """Get the slowest tests."""
        sorted_tests = sorted(self.all_tests, key=lambda t: t.elapsed_ms, reverse=True)
        return sorted_tests[:count]
    
    def get_slowest_keywords(self, count: int = 10) -> List[RobotKeyword]:
        """Get the slowest keywords across all tests."""
        all_keywords = []
        
        for test in self.all_tests:
            all_keywords.extend(test.keywords)
        
        sorted_keywords = sorted(all_keywords, key=lambda k: k.elapsed_ms, reverse=True)
        return sorted_keywords[:count]
    
    def get_statistics(self) -> Dict:
        """Get execution statistics."""
        if not self.root_suite:
            return {}
        
        total_keywords = sum(len(test.keywords) for test in self.all_tests)
        failed_keywords = len(self.get_failed_keywords())
        
        return {
            'total_tests': self.root_suite.total_tests,
            'passed_tests': self.root_suite.passed_tests,
            'failed_tests': self.root_suite.failed_tests,
            'pass_rate': f"{(self.root_suite.passed_tests / self.root_suite.total_tests * 100):.1f}%" if self.root_suite.total_tests > 0 else "0%",
            'total_keywords': total_keywords,
            'failed_keywords': failed_keywords,
            'total_duration_ms': self.root_suite.elapsed_ms,
            'suites': len(self.root_suite.suites),
        }


def parse_robot_output(xml_path: Path) -> RobotLogParser:
    """
    Convenience function to parse Robot Framework output.xml.
    
    Args:
        xml_path: Path to output.xml file
        
    Returns:
        RobotLogParser with parsed data
        
    Example:
        >>> parser = parse_robot_output(Path("output.xml"))
        >>> stats = parser.get_statistics()
        >>> print(f"Pass rate: {stats['pass_rate']}")
        >>> failed = parser.failed_tests
        >>> for test in failed:
        ...     print(f"Failed: {test.name} - {test.error_message}")
    """
    parser = RobotLogParser()
    parser.parse(xml_path)
    return parser
