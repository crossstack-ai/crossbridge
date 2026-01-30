"""
Framework Log Adapters

Each adapter converts framework-specific logs into normalized ExecutionEvent objects.
NO CLASSIFICATION OR AI HERE - only normalization.

Adapters are pluggable and framework-agnostic.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import re
from datetime import datetime

from core.execution.intelligence.models import ExecutionEvent, LogLevel


class LogAdapter(ABC):
    """Base class for all log adapters"""
    
    @abstractmethod
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """
        Parse raw logs into normalized ExecutionEvent objects.
        
        Args:
            raw_log: Raw log content as string
            
        Returns:
            List of ExecutionEvent objects
        """
        pass
    
    @abstractmethod
    def can_handle(self, raw_log: str) -> bool:
        """Check if this adapter can handle the given log format"""
        pass
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line"""
        # Common timestamp patterns
        patterns = [
            r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',  # ISO format
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',      # US format
            r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}',      # EU format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(0)
        
        return datetime.now().isoformat()
    
    def _parse_log_level(self, text: str) -> LogLevel:
        """Parse log level from text"""
        text_upper = text.upper()
        
        if any(x in text_upper for x in ['ERROR', 'FAIL', 'FAILED']):
            return LogLevel.ERROR
        elif any(x in text_upper for x in ['WARN', 'WARNING']):
            return LogLevel.WARN
        elif any(x in text_upper for x in ['DEBUG']):
            return LogLevel.DEBUG
        elif any(x in text_upper for x in ['FATAL', 'CRITICAL']):
            return LogLevel.FATAL
        else:
            return LogLevel.INFO


class SeleniumLogAdapter(LogAdapter):
    """Adapter for Selenium WebDriver logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a Selenium log"""
        indicators = [
            'selenium',
            'webdriver',
            'NoSuchElementException',
            'TimeoutException',
            'StaleElementReferenceException',
        ]
        return any(ind.lower() in raw_log.lower() for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse Selenium logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_stacktrace = []
        current_exception = None
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # Detect exceptions
            if 'Exception' in line or 'Error' in line:
                event = ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='selenium',
                    message=line.strip(),
                    exception_type=self._extract_exception_type(line)
                )
                
                # Collect stacktrace
                stacktrace_lines = []
                for j in range(i+1, min(i+20, len(lines))):
                    if lines[j].strip().startswith('at ') or lines[j].strip().startswith('File '):
                        stacktrace_lines.append(lines[j])
                    elif lines[j].strip() and not lines[j].strip().startswith(' '):
                        break
                
                if stacktrace_lines:
                    event.stacktrace = '\n'.join(stacktrace_lines)
                
                events.append(event)
            
            # Regular log lines
            elif any(marker in line for marker in ['INFO', 'DEBUG', 'WARN']):
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=self._parse_log_level(line),
                    source='selenium',
                    message=line.strip()
                ))
        
        return events
    
    def _extract_exception_type(self, line: str) -> Optional[str]:
        """Extract exception type from line"""
        match = re.search(r'(\w+Exception|\w+Error)', line)
        return match.group(1) if match else None


class PytestLogAdapter(LogAdapter):
    """Adapter for Pytest logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a Pytest log"""
        indicators = [
            'pytest',
            'PASSED',
            'FAILED',
            '===',
            'test session starts',
            'AssertionError',
        ]
        return any(ind in raw_log for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse Pytest logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_test = None
        in_failure_section = False
        
        for line in lines:
            if not line.strip():
                continue
            
            # Test start/result
            if '::' in line and any(x in line for x in ['PASSED', 'FAILED', 'SKIPPED']):
                test_name = line.split('::')[1].split()[0] if '::' in line else None
                status = 'PASSED' if 'PASSED' in line else 'FAILED' if 'FAILED' in line else 'SKIPPED'
                
                event = ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR if status == 'FAILED' else LogLevel.INFO,
                    source='pytest',
                    message=line.strip(),
                    test_name=test_name
                )
                events.append(event)
                current_test = test_name
            
            # Failure details
            elif 'FAILED' in line or 'ERROR' in line:
                in_failure_section = True
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='pytest',
                    message=line.strip(),
                    test_name=current_test
                ))
            
            # Assertion errors
            elif 'AssertionError' in line:
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='pytest',
                    message=line.strip(),
                    test_name=current_test,
                    exception_type='AssertionError'
                ))
            
            # Regular log lines
            elif in_failure_section and line.strip():
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=self._parse_log_level(line),
                    source='pytest',
                    message=line.strip(),
                    test_name=current_test
                ))
        
        return events


class RobotFrameworkLogAdapter(LogAdapter):
    """Adapter for Robot Framework logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a Robot Framework log"""
        indicators = [
            'Robot Framework',
            '| PASS |',
            '| FAIL |',
            'Test Cases',
            'Keywords',
        ]
        return any(ind in raw_log for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse Robot Framework logs"""
        events = []
        lines = raw_log.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # Test results
            if '| PASS |' in line or '| FAIL |' in line:
                status = 'PASSED' if '| PASS |' in line else 'FAILED'
                parts = line.split('|')
                test_name = parts[0].strip() if len(parts) > 0 else None
                
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR if status == 'FAILED' else LogLevel.INFO,
                    source='robot',
                    message=line.strip(),
                    test_name=test_name
                ))
            
            # Error messages
            elif any(x in line for x in ['ERROR', 'FAIL', 'Exception']):
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='robot',
                    message=line.strip()
                ))
            
            # Info lines
            elif line.strip().startswith('[') or line.strip().startswith('20'):
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=self._parse_log_level(line),
                    source='robot',
                    message=line.strip()
                ))
        
        return events


class PlaywrightLogAdapter(LogAdapter):
    """Adapter for Playwright logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a Playwright log"""
        indicators = [
            'playwright',
            'page.',
            'browser.',
            'locator',
            'Test timeout',
        ]
        return any(ind.lower() in raw_log.lower() for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse Playwright logs"""
        events = []
        lines = raw_log.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # Error lines
            if any(x in line for x in ['Error', 'Failed', 'timeout']):
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='playwright',
                    message=line.strip(),
                    exception_type=self._extract_exception_type(line)
                ))
            
            # Regular log lines
            else:
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=self._parse_log_level(line),
                    source='playwright',
                    message=line.strip()
                ))
        
        return events
    
    def _extract_exception_type(self, line: str) -> Optional[str]:
        """Extract exception type from line"""
        if 'timeout' in line.lower():
            return 'TimeoutError'
        match = re.search(r'(\w+Error|\w+Exception)', line)
        return match.group(1) if match else None


class CypressLogAdapter(LogAdapter):
    """Adapter for Cypress logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a Cypress log"""
        indicators = [
            'cypress',
            'cy.',
            'CypressError',
            'spec.js',
            'spec.ts',
        ]
        return any(ind.lower() in raw_log.lower() for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse Cypress logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_test = None
        
        for line in lines:
            if not line.strip():
                continue
            
            # Test results (✓ or ✗)
            if any(marker in line for marker in ['✓', '✗', 'PASS', 'FAIL']):
                status = 'PASSED' if '✓' in line or 'PASS' in line else 'FAILED'
                test_name = line.split('✓')[-1].split('✗')[-1].strip() if '✓' in line or '✗' in line else None
                
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR if status == 'FAILED' else LogLevel.INFO,
                    source='cypress',
                    message=line.strip(),
                    test_name=test_name
                ))
                current_test = test_name
            
            # Cypress errors
            elif 'CypressError' in line or 'AssertionError' in line:
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='cypress',
                    message=line.strip(),
                    test_name=current_test,
                    exception_type='CypressError' if 'CypressError' in line else 'AssertionError'
                ))
            
            # Command logs
            elif 'cy.' in line.lower():
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=self._parse_log_level(line),
                    source='cypress',
                    message=line.strip(),
                    test_name=current_test
                ))
        
        return events


class RestAssuredLogAdapter(LogAdapter):
    """Adapter for RestAssured Java logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a RestAssured log"""
        indicators = [
            'io.restassured',
            'RestAssured',
            'given()',
            'Request method:',
            'Request URI:',
            'Status code:',
        ]
        return any(ind in raw_log for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse RestAssured logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_test = None
        
        for line in lines:
            if not line.strip():
                continue
            
            # Test execution
            if '@Test' in line or 'test' in line.lower():
                match = re.search(r'test\w+\(', line, re.IGNORECASE)
                if match:
                    current_test = match.group(0)[:-1]
            
            # HTTP Request/Response
            if any(x in line for x in ['Request method:', 'Request URI:', 'Status code:', 'Response body:']):
                level = LogLevel.INFO
                if 'Status code:' in line:
                    status_match = re.search(r'Status code: (\d+)', line)
                    if status_match:
                        status_code = int(status_match.group(1))
                        if status_code >= 400:
                            level = LogLevel.ERROR
                
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=level,
                    source='restassured',
                    message=line.strip(),
                    test_name=current_test
                ))
            
            # Java exceptions
            elif any(x in line for x in ['Exception', 'Error', 'at ']):
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='restassured',
                    message=line.strip(),
                    test_name=current_test,
                    exception_type=self._extract_java_exception(line)
                ))
            
            # Assertions
            elif 'assert' in line.lower() or 'expected' in line.lower():
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR if 'failed' in line.lower() else LogLevel.INFO,
                    source='restassured',
                    message=line.strip(),
                    test_name=current_test
                ))
        
        return events
    
    def _extract_java_exception(self, line: str) -> Optional[str]:
        """Extract Java exception type"""
        match = re.search(r'(\w+Exception|\w+Error)', line)
        return match.group(1) if match else None


class CucumberBDDLogAdapter(LogAdapter):
    """Adapter for Cucumber/BDD logs (Gherkin syntax)"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a Cucumber/BDD log"""
        indicators = [
            'Feature:',
            'Scenario:',
            'Given ',
            'When ',
            'Then ',
            'And ',
            'cucumber',
        ]
        return any(ind in raw_log for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse Cucumber/BDD logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_feature = None
        current_scenario = None
        
        for line in lines:
            if not line.strip():
                continue
            
            # Feature
            if line.strip().startswith('Feature:'):
                current_feature = line.split('Feature:')[1].strip()
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.INFO,
                    source='cucumber',
                    message=line.strip(),
                    metadata={'feature': current_feature}
                ))
            
            # Scenario
            elif line.strip().startswith('Scenario:'):
                current_scenario = line.split('Scenario:')[1].strip()
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.INFO,
                    source='cucumber',
                    message=line.strip(),
                    test_name=current_scenario,
                    metadata={'feature': current_feature, 'scenario': current_scenario}
                ))
            
            # Steps (Given, When, Then, And)
            elif any(line.strip().startswith(x) for x in ['Given ', 'When ', 'Then ', 'And ', 'But ']):
                # Check for pass/fail markers
                level = LogLevel.INFO
                if '✗' in line or 'FAILED' in line or 'failed' in line.lower():
                    level = LogLevel.ERROR
                elif '✓' in line or 'PASSED' in line:
                    level = LogLevel.INFO
                
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=level,
                    source='cucumber',
                    message=line.strip(),
                    test_name=current_scenario,
                    metadata={'feature': current_feature}
                ))
            
            # Errors
            elif 'Error' in line or 'Exception' in line or 'failed' in line.lower():
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='cucumber',
                    message=line.strip(),
                    test_name=current_scenario,
                    metadata={'feature': current_feature}
                ))
        
        return events


class SpecFlowLogAdapter(LogAdapter):
    """Adapter for SpecFlow (.NET BDD) logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a SpecFlow log"""
        indicators = [
            'SpecFlow',
            'TechTalk.SpecFlow',
            'Feature:',
            'Scenario:',
            '[Given]',
            '[When]',
            '[Then]',
        ]
        return any(ind in raw_log for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse SpecFlow logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_scenario = None
        
        for line in lines:
            if not line.strip():
                continue
            
            # Scenario execution
            if 'Scenario:' in line:
                current_scenario = line.split('Scenario:')[1].strip()
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.INFO,
                    source='specflow',
                    message=line.strip(),
                    test_name=current_scenario
                ))
            
            # Steps with attributes
            elif any(x in line for x in ['[Given]', '[When]', '[Then]', '[And]']):
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=self._parse_log_level(line),
                    source='specflow',
                    message=line.strip(),
                    test_name=current_scenario
                ))
            
            # .NET exceptions
            elif any(x in line for x in ['Exception', 'at ', 'in ']) and '.cs:' in line:
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='specflow',
                    message=line.strip(),
                    test_name=current_scenario,
                    exception_type=self._extract_dotnet_exception(line)
                ))
            
            # Test results
            elif any(x in line for x in ['Passed', 'Failed', 'Skipped']):
                level = LogLevel.ERROR if 'Failed' in line else LogLevel.INFO
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=level,
                    source='specflow',
                    message=line.strip(),
                    test_name=current_scenario
                ))
        
        return events
    
    def _extract_dotnet_exception(self, line: str) -> Optional[str]:
        """Extract .NET exception type"""
        match = re.search(r'(\w+Exception|\w+Error)', line)
        return match.group(1) if match else None


class BehaveLogAdapter(LogAdapter):
    """Adapter for Behave (Python BDD) logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a Behave log"""
        indicators = [
            'behave',
            'Feature:',
            'Scenario:',
            '@given',
            '@when',
            '@then',
            'steps/',
        ]
        return any(ind.lower() in raw_log.lower() for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse Behave logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_feature = None
        current_scenario = None
        
        for line in lines:
            if not line.strip():
                continue
            
            # Feature
            if 'Feature:' in line:
                current_feature = line.split('Feature:')[1].strip()
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.INFO,
                    source='behave',
                    message=line.strip(),
                    metadata={'feature': current_feature}
                ))
            
            # Scenario
            elif 'Scenario:' in line:
                current_scenario = line.split('Scenario:')[1].strip()
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.INFO,
                    source='behave',
                    message=line.strip(),
                    test_name=current_scenario,
                    metadata={'feature': current_feature}
                ))
            
            # Steps with pass/fail
            elif any(x in line for x in ['Given', 'When', 'Then', 'And']) and any(y in line for y in ['✓', '✗', 'passed', 'failed']):
                level = LogLevel.ERROR if '✗' in line or 'failed' in line.lower() else LogLevel.INFO
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=level,
                    source='behave',
                    message=line.strip(),
                    test_name=current_scenario
                ))
            
            # Python exceptions
            elif 'Traceback' in line or 'Error' in line or 'Exception' in line:
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='behave',
                    message=line.strip(),
                    test_name=current_scenario
                ))
        
        return events


class JavaTestNGLogAdapter(LogAdapter):
    """Adapter for Java TestNG logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Check if this is a TestNG log"""
        indicators = [
            'org.testng',
            'TestNG',
            '@Test',
            'PASSED:',
            'FAILED:',
            'SKIPPED:',
        ]
        return any(ind in raw_log for ind in indicators)
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse TestNG logs"""
        events = []
        lines = raw_log.split('\n')
        
        current_test = None
        
        for line in lines:
            if not line.strip():
                continue
            
            # Test results
            if any(x in line for x in ['PASSED:', 'FAILED:', 'SKIPPED:']):
                status = 'PASSED' if 'PASSED:' in line else 'FAILED' if 'FAILED:' in line else 'SKIPPED'
                test_name = line.split(':')[1].strip() if ':' in line else None
                
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR if status == 'FAILED' else LogLevel.INFO,
                    source='testng',
                    message=line.strip(),
                    test_name=test_name
                ))
                current_test = test_name
            
            # Java exceptions
            elif any(x in line for x in ['Exception', 'Error', 'at ']):
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=LogLevel.ERROR,
                    source='testng',
                    message=line.strip(),
                    test_name=current_test,
                    exception_type=self._extract_java_exception(line)
                ))
            
            # Assertions
            elif 'assert' in line.lower():
                events.append(ExecutionEvent(
                    timestamp=self._extract_timestamp(line),
                    level=self._parse_log_level(line),
                    source='testng',
                    message=line.strip(),
                    test_name=current_test
                ))
        
        return events
    
    def _extract_java_exception(self, line: str) -> Optional[str]:
        """Extract Java exception type"""
        match = re.search(r'(\w+Exception|\w+Error)', line)
        return match.group(1) if match else None


class GenericLogAdapter(LogAdapter):
    """Generic adapter for unknown log formats"""
    
    def can_handle(self, raw_log: str) -> bool:
        """Generic adapter handles everything"""
        return True
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        """Parse generic logs"""
        events = []
        lines = raw_log.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            events.append(ExecutionEvent(
                timestamp=self._extract_timestamp(line),
                level=self._parse_log_level(line),
                source='generic',
                message=line.strip()
            ))
        
        return events


class JUnitLogAdapter(LogAdapter):
    """Adapter for JUnit test logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        return bool(re.search(r'(junit\.framework|org\.junit|@Test|JUnit)', raw_log, re.IGNORECASE))
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        events = []
        lines = raw_log.split('\n')
        
        for i, line in enumerate(lines):
            # Test start
            if re.search(r'(@Test|testStarted|Running\s+\w+)', line):
                match = re.search(r'(Running|testStarted)[\s:]+(\w+)', line)
                if match:
                    events.append(ExecutionEvent(
                        test_name=match.group(2),
                        message=line.strip(),
                        log_level=LogLevel.INFO,
                        event_type=EventType.TEST_START
                    ))
            
            # Failures and errors
            elif 'FAILURE' in line or 'ERROR' in line or 'AssertionError' in line:
                test_match = re.search(r'(\w+)\s*\(.*?\)', line)
                test_name = test_match.group(1) if test_match else "unknown"
                
                # Look for stacktrace
                stacktrace = []
                for j in range(i, min(i+20, len(lines))):
                    if lines[j].strip().startswith('at '):
                        stacktrace.append(lines[j].strip())
                
                events.append(ExecutionEvent(
                    test_name=test_name,
                    message=line.strip(),
                    log_level=LogLevel.ERROR,
                    stacktrace='\n'.join(stacktrace) if stacktrace else None,
                    event_type=EventType.FAILURE
                ))
            
            # Assertions
            elif 'assert' in line.lower() and ('expected' in line.lower() or 'actual' in line.lower()):
                events.append(ExecutionEvent(
                    test_name="unknown",
                    message=line.strip(),
                    log_level=LogLevel.ERROR,
                    event_type=EventType.ASSERTION
                ))
        
        return events


class NUnitLogAdapter(LogAdapter):
    """Adapter for NUnit test logs"""
    
    def can_handle(self, raw_log: str) -> bool:
        return bool(re.search(r'(NUnit|nunit\.framework|TestFixture|TestCase)', raw_log, re.IGNORECASE))
    
    def parse(self, raw_log: str) -> List[ExecutionEvent]:
        events = []
        lines = raw_log.split('\n')
        
        for i, line in enumerate(lines):
            # Test start
            if 'Test started' in line or '[Test]' in line:
                match = re.search(r'Test\s+started:\s+(\w+)|^\s*(\w+)\s*\[Test\]', line)
                if match:
                    test_name = match.group(1) or match.group(2)
                    events.append(ExecutionEvent(
                        test_name=test_name,
                        message=line.strip(),
                        log_level=LogLevel.INFO,
                        event_type=EventType.TEST_START
                    ))
            
            # Test failures
            elif 'Failed' in line or 'Error' in line or 'Exception' in line:
                test_match = re.search(r'(\w+)\.(\w+)', line)
                test_name = test_match.group(2) if test_match else "unknown"
                
                # Look for stacktrace
                stacktrace = []
                for j in range(i, min(i+20, len(lines))):
                    if lines[j].strip().startswith('at ') or '--->' in lines[j]:
                        stacktrace.append(lines[j].strip())
                
                events.append(ExecutionEvent(
                    test_name=test_name,
                    message=line.strip(),
                    log_level=LogLevel.ERROR,
                    stacktrace='\n'.join(stacktrace) if stacktrace else None,
                    event_type=EventType.FAILURE
                ))
            
            # Assertions
            elif 'Assert.' in line or 'Expected:' in line or 'Actual:' in line:
                events.append(ExecutionEvent(
                    test_name="unknown",
                    message=line.strip(),
                    log_level=LogLevel.ERROR,
                    event_type=EventType.ASSERTION
                ))
        
        return events


class AdapterRegistry:
    """Registry for all framework-specific adapters"""
    
    def __init__(self):
        self.adapters: List[LogAdapter] = [
            SeleniumLogAdapter(),
            PytestLogAdapter(),
            RobotFrameworkLogAdapter(),
            PlaywrightLogAdapter(),
            CypressLogAdapter(),
            RestAssuredLogAdapter(),
            CucumberBDDLogAdapter(),
            SpecFlowLogAdapter(),
            BehaveLogAdapter(),
            JavaTestNGLogAdapter(),
            JUnitLogAdapter(),
            NUnitLogAdapter(),
            GenericLogAdapter(),  # Always last (fallback)
        ]
    
    def get_adapter(self, raw_log: str) -> LogAdapter:
        """Get the best adapter for the given log"""
        for adapter in self.adapters:
            if adapter.can_handle(raw_log):
                return adapter
        
        # Should never reach here due to GenericLogAdapter
        return self.adapters[-1]
    
    def register_adapter(self, adapter: LogAdapter, priority: int = 0):
        """Register a new custom adapter"""
        if priority == 0:
            # Insert before GenericLogAdapter
            self.adapters.insert(-1, adapter)
        else:
            self.adapters.insert(priority, adapter)


# Global registry instance
_registry = AdapterRegistry()


def parse_logs(raw_log: str) -> List[ExecutionEvent]:
    """
    Parse raw logs into ExecutionEvent objects.
    
    Automatically detects the log format and uses the appropriate adapter.
    
    Args:
        raw_log: Raw log content
        
    Returns:
        List of normalized ExecutionEvent objects
    """
    adapter = _registry.get_adapter(raw_log)
    return adapter.parse(raw_log)


def register_custom_adapter(adapter: LogAdapter, priority: int = 0):
    """Register a custom log adapter"""
    _registry.register_adapter(adapter, priority)
