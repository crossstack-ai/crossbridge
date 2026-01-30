"""
Robot Framework Enhanced Parser

Parses Robot Framework output.xml files to extract keyword-level signals.

This provides parity with BDD step-level signals by capturing:
- Suite structure
- Test cases  
- Keyword executions (CRITICAL for parity)
- Library information
- Timing and status
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.logging import get_logger
from core.execution.intelligence.models import (
    RobotKeyword,
    RobotTest,
    ExecutionSignal,
)

logger = get_logger(__name__)


class RobotOutputParser:
    """
    Parse Robot Framework output.xml files.
    
    Robot Framework output.xml contains complete execution details:
    - Suite hierarchy
    - Test cases
    - Keywords with arguments
    - Timing (start/end/elapsed)
    - Status (PASS/FAIL)
    - Messages and logs
    """
    
    def parse_file(self, output_xml: str) -> List[RobotTest]:
        """
        Parse Robot Framework output.xml file.
        
        Args:
            output_xml: Path to output.xml file
            
        Returns:
            List of RobotTest objects with keyword-level details
        """
        try:
            tree = ET.parse(output_xml)
            root = tree.getroot()
            
            return self.parse_xml(root)
        except Exception as e:
            logger.error(f"Failed to parse Robot output.xml: {e}")
            return []
    
    def parse_xml(self, root: ET.Element) -> List[RobotTest]:
        """
        Parse Robot Framework XML root element.
        
        Args:
            root: XML root element
            
        Returns:
            List of RobotTest objects
        """
        tests = []
        
        # Find all test elements (could be nested in suites)
        for suite in root.iter('suite'):
            suite_name = suite.get('name', 'Unknown Suite')
            
            for test in suite.iter('test'):
                robot_test = self._parse_test(test, suite_name)
                if robot_test:
                    tests.append(robot_test)
        
        return tests
    
    def _parse_test(self, test_elem: ET.Element, suite_name: str) -> Optional[RobotTest]:
        """Parse a single Robot Framework test"""
        try:
            test_name = test_elem.get('name', 'Unknown Test')
            
            # Get status
            status_elem = test_elem.find('status')
            status = status_elem.get('status', 'PASS') if status_elem is not None else 'PASS'
            
            # Get duration (starttime/endtime)
            duration_ms = 0
            if status_elem is not None:
                start_time = status_elem.get('starttime')
                end_time = status_elem.get('endtime')
                if start_time and end_time:
                    # Convert Robot timestamps to duration
                    # Format: 20260130 12:34:56.789
                    duration_ms = self._calculate_duration(start_time, end_time)
            
            # Get tags
            tags = []
            for tag in test_elem.findall('tag'):
                if tag.text:
                    tags.append(tag.text)
            
            # Get doc
            doc_elem = test_elem.find('doc')
            doc = doc_elem.text if doc_elem is not None and doc_elem.text else None
            
            # Parse keywords (CRITICAL FOR PARITY)
            keywords = []
            for kw in test_elem.findall('kw'):
                keyword = self._parse_keyword(kw)
                if keyword:
                    keywords.append(keyword)
            
            return RobotTest(
                name=test_name,
                suite_name=suite_name,
                keywords=keywords,
                status=status,
                duration_ms=duration_ms,
                tags=tags,
                doc=doc
            )
        
        except Exception as e:
            logger.error(f"Failed to parse Robot test: {e}")
            return None
    
    def _parse_keyword(self, kw_elem: ET.Element) -> Optional[RobotKeyword]:
        """Parse a single Robot Framework keyword"""
        try:
            keyword_name = kw_elem.get('name', 'Unknown Keyword')
            keyword_type = kw_elem.get('type', 'KEYWORD')  # KEYWORD, SETUP, TEARDOWN
            
            # Get library (from 'library' or 'owner' attribute)
            library = kw_elem.get('library', kw_elem.get('owner', 'Unknown'))
            
            # Get arguments
            arguments = []
            args_elem = kw_elem.find('arguments')
            if args_elem is not None:
                for arg in args_elem.findall('arg'):
                    if arg.text:
                        arguments.append(arg.text)
            
            # Get status
            status_elem = kw_elem.find('status')
            status = 'PASS'
            error_message = None
            
            if status_elem is not None:
                status = status_elem.get('status', 'PASS')
                
                # Get duration
                start_time = status_elem.get('starttime')
                end_time = status_elem.get('endtime')
                duration_ms = 0
                if start_time and end_time:
                    duration_ms = self._calculate_duration(start_time, end_time)
            else:
                duration_ms = 0
            
            # Get error message if failed
            if status == 'FAIL':
                msg_elem = kw_elem.find('msg')
                if msg_elem is not None and msg_elem.text:
                    error_message = msg_elem.text
            
            # Get doc
            doc_elem = kw_elem.find('doc')
            doc = doc_elem.text if doc_elem is not None and doc_elem.text else None
            
            return RobotKeyword(
                name=keyword_name,
                library=library,
                arguments=arguments,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                keyword_type=keyword_type,
                doc=doc
            )
        
        except Exception as e:
            logger.error(f"Failed to parse Robot keyword: {e}")
            return None
    
    def _calculate_duration(self, start_time: str, end_time: str) -> int:
        """
        Calculate duration in milliseconds from Robot timestamps.
        
        Format: 20260130 12:34:56.789
        """
        try:
            from datetime import datetime
            
            # Parse timestamps
            fmt = "%Y%m%d %H:%M:%S.%f"
            start = datetime.strptime(start_time, fmt)
            end = datetime.strptime(end_time, fmt)
            
            # Calculate duration in milliseconds
            duration = (end - start).total_seconds() * 1000
            return int(duration)
        except Exception as e:
            logger.debug(f"Failed to calculate duration: {e}")
            return 0


def robot_to_signals(
    tests: List[RobotTest],
    run_id: Optional[str] = None,
    include_keywords: bool = True
) -> List[ExecutionSignal]:
    """
    Convert Robot tests to canonical ExecutionSignal format.
    
    Args:
        tests: List of RobotTest objects
        run_id: Optional run identifier
        include_keywords: Whether to include keyword-level signals (RECOMMENDED)
        
    Returns:
        List of ExecutionSignal objects
    """
    signals = []
    
    for test in tests:
        # Add test-level signal
        signals.append(test.to_signal(run_id))
        
        # Add keyword-level signals (CRITICAL FOR PARITY)
        if include_keywords:
            for keyword in test.keywords:
                signals.append(keyword.to_signal(test.name, test.suite_name, run_id))
    
    return signals


# Example usage
if __name__ == "__main__":
    parser = RobotOutputParser()
    tests = parser.parse_file("output.xml")
    
    print(f"Parsed {len(tests)} tests")
    
    for test in tests:
        print(f"\nTest: {test.name}")
        print(f"  Suite: {test.suite_name}")
        print(f"  Status: {test.status}")
        print(f"  Duration: {test.duration_ms}ms")
        print(f"  Keywords: {len(test.keywords)}")
        
        for kw in test.keywords:
            status_icon = "✓" if kw.status == "PASS" else "✗"
            print(f"    {status_icon} {kw.name} [{kw.library}] ({kw.duration_ms}ms)")
            if kw.arguments:
                print(f"       Args: {', '.join(kw.arguments)}")
    
    # Convert to canonical signals
    signals = robot_to_signals(tests)
    print(f"\nGenerated {len(signals)} execution signals")
    
    # Count keyword-level signals
    keyword_signals = [s for s in signals if s.entity_type.value == "keyword"]
    print(f"Keyword-level signals: {len(keyword_signals)}")
