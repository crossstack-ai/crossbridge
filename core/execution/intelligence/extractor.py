"""
Failure Signal Extractors

Extract specific failure signals from normalized ExecutionEvent objects.
This is DETERMINISTIC - no AI, pure pattern matching and logic.

Each extractor focuses on one type of failure signal.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import re

from core.execution.intelligence.models import (
    ExecutionEvent,
    FailureSignal,
    SignalType,
    LogLevel
)


class FailureSignalExtractor(ABC):
    """Base class for all signal extractors"""
    
    @abstractmethod
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        """
        Extract failure signals from execution events.
        
        Args:
            events: List of normalized execution events
            
        Returns:
            List of extracted failure signals
        """
        pass
    
    def _find_stacktrace(self, events: List[ExecutionEvent], start_idx: int) -> Optional[str]:
        """Find stacktrace following an error event"""
        stacktraces = []
        for i in range(start_idx, min(start_idx + 20, len(events))):
            if events[i].stacktrace:
                return events[i].stacktrace
        return None


class TimeoutExtractor(FailureSignalExtractor):
    """Extract timeout-related failures"""
    
    TIMEOUT_PATTERNS = [
        r'timeout',
        r'timed out',
        r'time limit exceeded',
        r'waited (\d+) seconds',
        r'TimeoutException',
        r'TimeoutError',
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        """Extract timeout signals"""
        signals = []
        
        for i, event in enumerate(events):
            if event.level not in [LogLevel.ERROR, LogLevel.WARN]:
                continue
            
            message_lower = event.message.lower()
            
            # Check for timeout patterns
            matched_patterns = []
            for pattern in self.TIMEOUT_PATTERNS:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    matched_patterns.append(pattern)
            
            if matched_patterns:
                # Determine confidence based on specificity
                confidence = 0.9 if 'TimeoutException' in event.message else 0.8
                
                # Extract timeout duration if present
                duration_match = re.search(r'(\d+)\s*(?:seconds?|ms|milliseconds?)', message_lower)
                metadata = {}
                if duration_match:
                    metadata['timeout_duration'] = duration_match.group(1)
                
                signal = FailureSignal(
                    signal_type=SignalType.TIMEOUT,
                    message=event.message,
                    confidence=confidence,
                    stacktrace=event.stacktrace or self._find_stacktrace(events, i),
                    file=event.test_file,
                    keywords=['timeout', 'wait', 'duration'],
                    patterns_matched=matched_patterns,
                    metadata=metadata
                )
                signals.append(signal)
        
        return signals


class AssertionExtractor(FailureSignalExtractor):
    """Extract assertion failures"""
    
    ASSERTION_PATTERNS = [
        r'AssertionError',
        r'assert\s+',
        r'expected.*but\s+(?:was|got)',
        r'expected:\s*.*\s*actual:',
        r'should\s+(?:be|equal|contain)',
        r'assertEqual',
        r'assertNotEqual',
        r'assertTrue',
        r'assertFalse',
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        """Extract assertion signals"""
        signals = []
        
        for i, event in enumerate(events):
            if event.level != LogLevel.ERROR:
                continue
            
            message = event.message
            
            # Check for assertion patterns
            matched_patterns = []
            for pattern in self.ASSERTION_PATTERNS:
                if re.search(pattern, message, re.IGNORECASE):
                    matched_patterns.append(pattern)
            
            if matched_patterns or event.exception_type == 'AssertionError':
                # Extract expected vs actual values
                expected = self._extract_expected(message)
                actual = self._extract_actual(message)
                
                metadata = {}
                if expected:
                    metadata['expected'] = expected
                if actual:
                    metadata['actual'] = actual
                
                signal = FailureSignal(
                    signal_type=SignalType.ASSERTION,
                    message=event.message,
                    confidence=0.95 if event.exception_type == 'AssertionError' else 0.85,
                    stacktrace=event.stacktrace or self._find_stacktrace(events, i),
                    file=event.test_file,
                    keywords=['assertion', 'expected', 'actual', 'verify'],
                    patterns_matched=matched_patterns,
                    metadata=metadata
                )
                signals.append(signal)
        
        return signals
    
    def _extract_expected(self, message: str) -> Optional[str]:
        """Extract expected value from assertion message"""
        patterns = [
            r'expected:\s*([^\n,]+)',
            r'expected\s+([^\s]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_actual(self, message: str) -> Optional[str]:
        """Extract actual value from assertion message"""
        patterns = [
            r'actual:\s*([^\n,]+)',
            r'but\s+(?:was|got)\s+([^\n,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None


class LocatorExtractor(FailureSignalExtractor):
    """Extract locator/selector failures"""
    
    LOCATOR_PATTERNS = [
        r'NoSuchElementException',
        r'ElementNotFound',
        r'could not find element',
        r'unable to locate',
        r'element.*not found',
        r'XPath',
        r'cssSelector',
        r'css selector',
        r'by\.id',
        r'by\.name',
        r'by\.xpath',
        r'by\.css',
        r'locator',
    ]
    
    LOCATOR_STRATEGIES = [
        r'xpath[=:]?\s*["\']([^"\']+)["\']',
        r'css[=:]?\s*["\']([^"\']+)["\']',
        r'id[=:]?\s*["\']([^"\']+)["\']',
        r'name[=:]?\s*["\']([^"\']+)["\']',
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        """Extract locator signals"""
        signals = []
        
        for i, event in enumerate(events):
            if event.level != LogLevel.ERROR:
                continue
            
            message = event.message
            
            # Check for locator patterns
            matched_patterns = []
            for pattern in self.LOCATOR_PATTERNS:
                if re.search(pattern, message, re.IGNORECASE):
                    matched_patterns.append(pattern)
            
            if matched_patterns or 'NoSuchElementException' in str(event.exception_type):
                # Extract locator strategy and value
                locator_strategy, locator_value = self._extract_locator(message)
                
                metadata = {}
                if locator_strategy:
                    metadata['locator_strategy'] = locator_strategy
                if locator_value:
                    metadata['locator_value'] = locator_value
                
                signal = FailureSignal(
                    signal_type=SignalType.LOCATOR,
                    message=event.message,
                    confidence=0.95 if 'NoSuchElementException' in message else 0.85,
                    stacktrace=event.stacktrace or self._find_stacktrace(events, i),
                    file=event.test_file,
                    keywords=['locator', 'element', 'selector', 'xpath', 'css'],
                    patterns_matched=matched_patterns,
                    metadata=metadata
                )
                signals.append(signal)
        
        return signals
    
    def _extract_locator(self, message: str) -> tuple[Optional[str], Optional[str]]:
        """Extract locator strategy and value from message"""
        for pattern in self.LOCATOR_STRATEGIES:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                strategy = pattern.split('[')[0]  # Extract strategy name
                value = match.group(1)
                return strategy, value
        return None, None


class HttpErrorExtractor(FailureSignalExtractor):
    """Extract HTTP/API errors"""
    
    HTTP_PATTERNS = [
        r'HTTP\s+(\d{3})',
        r'status\s+code:\s*(\d{3})',
        r'(\d{3})\s+(?:error|failed)',
        r'ConnectionError',
        r'HTTPError',
        r'RequestException',
        r'failed to connect',
        r'connection refused',
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        """Extract HTTP error signals"""
        signals = []
        
        for i, event in enumerate(events):
            if event.level not in [LogLevel.ERROR, LogLevel.WARN]:
                continue
            
            message = event.message
            
            # Check for HTTP patterns
            matched_patterns = []
            status_code = None
            
            for pattern in self.HTTP_PATTERNS:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    matched_patterns.append(pattern)
                    # Try to extract status code
                    if match.groups():
                        try:
                            status_code = int(match.group(1))
                        except (ValueError, IndexError):
                            pass
            
            if matched_patterns:
                metadata = {}
                if status_code:
                    metadata['status_code'] = status_code
                    metadata['status_category'] = self._categorize_status(status_code)
                
                signal = FailureSignal(
                    signal_type=SignalType.HTTP_ERROR,
                    message=event.message,
                    confidence=0.9,
                    stacktrace=event.stacktrace or self._find_stacktrace(events, i),
                    file=event.test_file,
                    keywords=['http', 'api', 'status', 'request', 'response'],
                    patterns_matched=matched_patterns,
                    metadata=metadata
                )
                signals.append(signal)
        
        return signals
    
    def _categorize_status(self, status_code: int) -> str:
        """Categorize HTTP status code"""
        if 400 <= status_code < 500:
            return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        elif 300 <= status_code < 400:
            return "redirect"
        elif 200 <= status_code < 300:
            return "success"
        else:
            return "unknown"


class InfraErrorExtractor(FailureSignalExtractor):
    """Extract infrastructure/environment errors"""
    
    INFRA_PATTERNS = [
        r'connection refused',
        r'connection reset',
        r'network.*(?:unreachable|error)',
        r'DNS.*(?:failed|error)',
        r'name resolution failed',
        r'host.*not found',
        r'cannot resolve',
        r'permission denied',
        r'access denied',
        r'file not found',
        r'no such file',
        r'module not found',
        r'ImportError',
        r'ModuleNotFoundError',
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        """Extract infrastructure error signals"""
        signals = []
        
        for i, event in enumerate(events):
            if event.level != LogLevel.ERROR:
                continue
            
            message = event.message.lower()
            
            # Check for infrastructure patterns
            matched_patterns = []
            signal_type = SignalType.UNKNOWN
            
            for pattern in self.INFRA_PATTERNS:
                if re.search(pattern, message, re.IGNORECASE):
                    matched_patterns.append(pattern)
                    # Categorize specific infra issue
                    if 'dns' in pattern.lower() or 'resolve' in pattern.lower():
                        signal_type = SignalType.DNS_ERROR
                    elif 'connection' in pattern.lower():
                        signal_type = SignalType.CONNECTION_ERROR
                    elif 'permission' in pattern.lower() or 'access' in pattern.lower():
                        signal_type = SignalType.PERMISSION_ERROR
                    elif 'file' in pattern.lower():
                        signal_type = SignalType.FILE_NOT_FOUND
                    elif 'import' in pattern.lower() or 'module' in pattern.lower():
                        signal_type = SignalType.IMPORT_ERROR
            
            if matched_patterns:
                signal = FailureSignal(
                    signal_type=signal_type,
                    message=event.message,
                    confidence=0.85,
                    stacktrace=event.stacktrace or self._find_stacktrace(events, i),
                    file=event.test_file,
                    keywords=['infrastructure', 'environment', 'network', 'system'],
                    patterns_matched=matched_patterns,
                    metadata={}
                )
                signals.append(signal)
        
        return signals


class CompositeExtractor:
    """Composite extractor that runs all extractors"""
    
    def __init__(self):
        self.extractors = [
            TimeoutExtractor(),
            AssertionExtractor(),
            LocatorExtractor(),
            HttpErrorExtractor(),
            InfraErrorExtractor(),
        ]
    
    def extract_all(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        """Extract all failure signals from events"""
        all_signals = []
        
        for extractor in self.extractors:
            signals = extractor.extract(events)
            all_signals.extend(signals)
        
        # Remove duplicates based on message similarity
        return self._deduplicate(all_signals)
    
    def _deduplicate(self, signals: List[FailureSignal]) -> List[FailureSignal]:
        """Remove duplicate signals"""
        if not signals:
            return []
        
        unique_signals = []
        seen_messages = set()
        
        for signal in signals:
            # Use first 100 chars of message as key
            key = signal.message[:100].lower()
            if key not in seen_messages:
                seen_messages.add(key)
                unique_signals.append(signal)
        
        return unique_signals
