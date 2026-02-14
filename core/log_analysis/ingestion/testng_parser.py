"""
TestNG XML Parser

Parses testng-results.xml files into structured failure objects.
Primary source of truth for TestNG test execution.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from core.logging import get_logger, LogCategory
from .log_artifacts import StructuredFailure, FailureCategory

logger = get_logger(__name__, category=LogCategory.TESTING)


class TestNGParser:
    """
    Parser for TestNG XML results.
    
    Extracts structured failure information from testng-results.xml files.
    Handles standard TestNG format: <testng-results> → <suite> → <test> → <class> → <test-method>
    """
    
    def __init__(self):
        """Initialize TestNG parser"""
        self.failures: List[StructuredFailure] = []
        self.stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
        }
    
    def parse(self, xml_path: Path) -> List[StructuredFailure]:
        """
        Parse TestNG XML file.
        
        Args:
            xml_path: Path to testng-results.xml
            
        Returns:
            List of StructuredFailure objects
        """
        logger.info(f"Parsing TestNG XML: {xml_path}")
        
        if not xml_path.exists():
            logger.error(f"TestNG XML file not found: {xml_path}")
            return []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Validate this is a TestNG XML file, not HTML or other format
            if root.tag.lower() in ['html', 'body', 'head']:
                raise ValueError(
                    "This appears to be an HTML file. TestNG HTML reports cannot be parsed. "
                    "Please use testng-results.xml instead (typically found in test-output/ directory)."
                )
            
            # Check for testng-results root element
            if root.tag not in ['testng-results', 'suite']:
                logger.warning(f"Unexpected root element '{root.tag}' - expected 'testng-results' or 'suite'")
            
            # Reset state
            self.failures = []
            self.stats = {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0}
            
            # Parse structure: <testng-results> → <suite> → <test> → <class> → <test-method>
            for suite in root.findall('.//suite'):
                suite_name = suite.get('name', 'Unknown Suite')
                logger.debug(f"Processing suite: {suite_name}")
                
                for test in suite.findall('.//test'):
                    test_name = test.get('name', 'Unknown Test')
                    
                    for cls in test.findall('.//class'):
                        class_name = cls.get('name', 'Unknown Class')
                        
                        for method in cls.findall('.//test-method'):
                            failure = self._parse_test_method(method, class_name, test_name)
                            if failure:
                                self.failures.append(failure)
            
            logger.info(
                f"Parsed {self.stats['total']} tests: "
                f"{self.stats['passed']} passed, "
                f"{self.stats['failed']} failed, "
                f"{self.stats['skipped']} skipped"
            )
            
            return self.failures
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse TestNG XML: {e}")
            raise ValueError(f"Invalid TestNG XML format: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error parsing TestNG XML: {e}")
            raise
    
    def _parse_test_method(
        self, 
        method_elem: ET.Element, 
        class_name: str,
        test_name: str
    ) -> Optional[StructuredFailure]:
        """
        Parse a single test method element.
        
        Args:
            method_elem: <test-method> XML element
            class_name: Fully qualified class name
            test_name: Test group name
            
        Returns:
            StructuredFailure object or None
        """
        method_name = method_elem.get('name', 'unknown')
        status = method_elem.get('status', 'FAIL')
        is_config = method_elem.get('is-config', 'false') == 'true'
        
        # Skip configuration methods unless they failed
        if is_config and status == 'PASS':
            return None
        
        # Duration in milliseconds
        duration_str = method_elem.get('duration-ms', '0')
        try:
            duration_ms = int(duration_str)
        except ValueError:
            duration_ms = 0
        
        # Timestamp
        started_at = method_elem.get('started-at', '')
        
        # Update stats
        self.stats['total'] += 1
        if status == 'PASS':
            self.stats['passed'] += 1
        elif status == 'SKIP':
            self.stats['skipped'] += 1
        else:
            self.stats['failed'] += 1
        
        # Extract exception details for failures
        failure_type = None
        error_message = None
        stack_trace = None
        
        exception_elem = method_elem.find('.//exception')
        if exception_elem is not None:
            failure_type = exception_elem.get('class', 'UnknownException')
            
            message_elem = exception_elem.find('.//message')
            if message_elem is not None and message_elem.text:
                error_message = message_elem.text.strip()
            
            # Full stack trace
            full_trace_elem = exception_elem.find('.//full-stacktrace')
            if full_trace_elem is not None and full_trace_elem.text:
                stack_trace = full_trace_elem.text.strip()
            elif exception_elem.text:
                # Fallback to exception text
                stack_trace = exception_elem.text.strip()
        
        # Create structured failure
        failure = StructuredFailure(
            test_name=f"{class_name}.{method_name}",
            class_name=class_name,
            method_name=method_name,
            status=status,
            failure_type=failure_type,
            error_message=error_message,
            stack_trace=stack_trace,
            duration_ms=duration_ms,
            timestamp=started_at,
            test_group=test_name,
            category=self._categorize_failure(failure_type, error_message, stack_trace)
        )
        
        return failure
    
    def _categorize_failure(
        self, 
        failure_type: Optional[str],
        error_message: Optional[str],
        stack_trace: Optional[str]
    ) -> FailureCategory:
        """
        Categorize failure based on exception type and message.
        
        Args:
            failure_type: Exception class name
            error_message: Exception message
            stack_trace: Full stack trace
            
        Returns:
            FailureCategory
        """
        if not failure_type:
            return FailureCategory.UNKNOWN
        
        failure_type_lower = failure_type.lower()
        message_lower = (error_message or "").lower()
        trace_lower = (stack_trace or "").lower()
        
        # Infrastructure failures
        infra_keywords = [
            'timeout', 'connection', 'network', 'socket', 'unreachable',
            'refused', 'reset', 'unavailable', 'session not created',
            'no such session', 'sessionnotcreated', 'webdriver'
        ]
        if any(kw in failure_type_lower or kw in message_lower for kw in infra_keywords):
            return FailureCategory.INFRASTRUCTURE
        
        # Test assertions
        assertion_keywords = ['assert', 'expected', 'actual', 'comparison']
        if any(kw in failure_type_lower for kw in assertion_keywords):
            return FailureCategory.TEST_ASSERTION
        
        # Environment issues
        env_keywords = [
            'filenotfound', 'nosuchfile', 'configuration', 'setup',
            'nullpointer', 'illegalstate', 'illegalargument'
        ]
        if any(kw in failure_type_lower for kw in env_keywords):
            return FailureCategory.ENVIRONMENT
        
        # Application errors
        app_keywords = ['500', 'error 500', 'internal server', 'application']
        if any(kw in message_lower for kw in app_keywords):
            return FailureCategory.APPLICATION
        
        return FailureCategory.UNKNOWN
    
    def get_summary(self) -> Dict:
        """
        Get execution summary.
        
        Returns:
            Dictionary with statistics
        """
        total = self.stats['total']
        passed = self.stats['passed']
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': self.stats['failed'],
            'skipped': self.stats['skipped'],
            'pass_rate': (passed / total * 100) if total > 0 else 0.0,
            'failure_count': len([f for f in self.failures if f.is_failed()]),
        }
    
    def get_failures(self) -> List[StructuredFailure]:
        """Get all failures"""
        return [f for f in self.failures if f.is_failed()]
    
    def get_passed(self) -> List[StructuredFailure]:
        """Get all passed tests"""
        return [f for f in self.failures if f.is_passed()]
