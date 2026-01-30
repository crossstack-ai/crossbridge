"""
Framework-Specific Signal Extractors

Additional extractors for Selenium Java BDD, Robot Framework, and Pytest
to achieve framework parity in signal quality.
"""

from typing import List
import re

from core.execution.intelligence.extractor import FailureSignalExtractor
from core.execution.intelligence.models import (
    ExecutionEvent,
    FailureSignal,
    SignalType,
    LogLevel
)


# ============================================================================
# SELENIUM-SPECIFIC EXTRACTORS
# ============================================================================

class SeleniumTimeoutExtractor(FailureSignalExtractor):
    """
    Extract Selenium-specific timeout failures.
    
    Selenium timeouts have specific characteristics:
    - ElementNotVisibleException
    - NoSuchElementException after wait
    - StaleElementReferenceException
    - TimeoutException from WebDriverWait
    """
    
    SELENIUM_TIMEOUT_PATTERNS = [
        (r'TimeoutException.*waiting for', 'explicit_wait_timeout', 0.95),
        (r'NoSuchElementException.*timeout', 'element_wait_timeout', 0.9),
        (r'ElementNotVisibleException', 'visibility_timeout', 0.9),
        (r'element\s+(?:is\s+)?not\s+(?:clickable|interactable)', 'interaction_timeout', 0.85),
        (r'page\s+load\s+timeout', 'page_load_timeout', 0.95),
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        signals = []
        
        for event in events:
            if event.level != LogLevel.ERROR:
                continue
            
            for pattern, issue_type, confidence in self.SELENIUM_TIMEOUT_PATTERNS:
                if re.search(pattern, event.message, re.IGNORECASE):
                    # Extract locator if present
                    locator_match = re.search(
                        r'(?:By\.)?(\w+):\s*["\']?([^"\')\s]+)["\']?',
                        event.message
                    )
                    
                    metadata = {
                        'issue_type': issue_type,
                        'test_name': event.test_name,
                    }
                    
                    if locator_match:
                        metadata['locator_type'] = locator_match.group(1)
                        metadata['locator_value'] = locator_match.group(2)
                    
                    signals.append(FailureSignal(
                        signal_type=SignalType.UI_TIMEOUT,
                        message=f"Selenium timeout ({issue_type}): {event.message}",
                        confidence=confidence,
                        stacktrace=event.stacktrace,
                        file=event.test_file,
                        metadata=metadata,
                        is_retryable=True,  # UI timeouts are often retryable
                        is_infra_related=False,  # This is a test stability issue
                    ))
                    break
        
        return signals


class SeleniumLocatorExtractor(FailureSignalExtractor):
    """
    Extract Selenium locator failures.
    
    Locator failures indicate:
    - Element not found
    - Incorrect selector
    - DOM structure changed
    """
    
    LOCATOR_PATTERNS = [
        (r'NoSuchElementException', 'element_not_found', 0.95),
        (r'Unable\s+to\s+locate\s+element', 'element_not_found', 0.9),
        (r'Element\s+.*\s+(?:is\s+)?not\s+found', 'element_not_found', 0.85),
        (r'InvalidSelectorException', 'invalid_selector', 0.95),
        (r'(?:xpath|css|id|name|class)\s+.*\s+not\s+found', 'locator_not_found', 0.9),
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        signals = []
        
        for event in events:
            if event.level != LogLevel.ERROR:
                continue
            
            for pattern, issue_type, confidence in self.LOCATOR_PATTERNS:
                if re.search(pattern, event.message, re.IGNORECASE):
                    # Extract locator details
                    locator_match = re.search(
                        r'(?:By\.)?(\w+):\s*["\']?([^"\')\s]+)["\']?',
                        event.message
                    )
                    
                    # Extract browser if present
                    browser_match = re.search(
                        r'(chrome|firefox|safari|edge|ie)',
                        event.message,
                        re.IGNORECASE
                    )
                    
                    metadata = {
                        'issue_type': issue_type,
                        'test_name': event.test_name,
                    }
                    
                    if locator_match:
                        metadata['locator_type'] = locator_match.group(1)
                        metadata['locator_value'] = locator_match.group(2)
                    
                    if browser_match:
                        metadata['browser'] = browser_match.group(1).lower()
                    
                    signals.append(FailureSignal(
                        signal_type=SignalType.UI_LOCATOR,
                        message=f"Locator failure ({issue_type}): {event.message}",
                        confidence=confidence,
                        stacktrace=event.stacktrace,
                        file=event.test_file,
                        metadata=metadata,
                        is_retryable=False,  # Locator issues need fixing
                        is_infra_related=False,
                    ))
                    break
        
        return signals


class SeleniumStaleElementExtractor(FailureSignalExtractor):
    """
    Extract Selenium stale element failures.
    
    Stale element indicates:
    - DOM was updated after element was found
    - Page refresh
    - AJAX update
    - Dynamic content
    """
    
    STALE_PATTERNS = [
        (r'StaleElementReferenceException', 0.95),
        (r'stale\s+element\s+reference', 0.9),
        (r'element\s+is\s+no\s+longer\s+attached', 0.85),
        (r'Element\s+.*\s+is\s+not\s+attached\s+to\s+the\s+DOM', 0.9),
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        signals = []
        
        for event in events:
            if event.level != LogLevel.ERROR:
                continue
            
            for pattern, confidence in self.STALE_PATTERNS:
                if re.search(pattern, event.message, re.IGNORECASE):
                    # Try to extract action that failed
                    action_match = re.search(
                        r'(click|sendKeys|getText|getAttribute)',
                        event.message
                    )
                    
                    metadata = {
                        'test_name': event.test_name,
                        'issue': 'stale_element',
                    }
                    
                    if action_match:
                        metadata['failed_action'] = action_match.group(1)
                    
                    signals.append(FailureSignal(
                        signal_type=SignalType.UI_STALE,
                        message=f"Stale element: {event.message}",
                        confidence=confidence,
                        stacktrace=event.stacktrace,
                        file=event.test_file,
                        metadata=metadata,
                        is_retryable=True,  # Stale elements can often be re-found
                        is_infra_related=False,
                    ))
                    break
        
        return signals


class SeleniumBrowserExtractor(FailureSignalExtractor):
    """
    Extract Selenium browser-specific failures.
    
    Browser failures indicate:
    - Browser crash
    - Driver issue
    - Browser version mismatch
    """
    
    BROWSER_PATTERNS = [
        (r'(?:chrome|firefox|edge|safari)driver.*not\s+found', 'driver_not_found', 0.95, True),
        (r'browser\s+(?:crashed|terminated|closed)', 'browser_crash', 0.9, True),
        (r'WebDriverException.*disconnected', 'browser_disconnected', 0.9, True),
        (r'session\s+(?:deleted|not\s+found)', 'session_lost', 0.85, True),
        (r'browser\s+version.*driver\s+version', 'version_mismatch', 0.9, False),
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        signals = []
        
        for event in events:
            if event.level not in [LogLevel.ERROR, LogLevel.FATAL]:
                continue
            
            for pattern, issue_type, confidence, is_retryable in self.BROWSER_PATTERNS:
                if re.search(pattern, event.message, re.IGNORECASE):
                    # Extract browser type
                    browser_match = re.search(
                        r'(chrome|firefox|safari|edge|ie)',
                        event.message,
                        re.IGNORECASE
                    )
                    
                    metadata = {
                        'issue_type': issue_type,
                        'test_name': event.test_name,
                    }
                    
                    if browser_match:
                        metadata['browser'] = browser_match.group(1).lower()
                    
                    signals.append(FailureSignal(
                        signal_type=SignalType.INFRASTRUCTURE,
                        message=f"Browser/driver issue ({issue_type}): {event.message}",
                        confidence=confidence,
                        stacktrace=event.stacktrace,
                        file=event.test_file,
                        metadata=metadata,
                        is_retryable=is_retryable,
                        is_infra_related=True,
                    ))
                    break
        
        return signals


# ============================================================================
# ROBOT FRAMEWORK EXTRACTORS
# ============================================================================

class RobotKeywordExtractor(FailureSignalExtractor):
    """
    Extract Robot Framework keyword failures.
    
    Robot keyword failures indicate:
    - Keyword not found
    - Library not imported
    - Wrong arguments
    """
    
    KEYWORD_PATTERNS = [
        (r"No\s+keyword\s+with\s+name\s+'([^']+)'", 'keyword_not_found', 0.95),
        (r"Keyword\s+'([^']+)'\s+not\s+found", 'keyword_not_found', 0.9),
        (r"Keyword\s+'([^']+)'\s+got\s+\d+\s+arguments", 'wrong_arguments', 0.9),
    ]
    
    LIBRARY_PATTERNS = [
        (r"Importing\s+(?:test\s+)?library\s+'([^']+)'\s+failed", 'library_import_failed', 0.95),
        (r"No\s+library\s+'([^']+)'\s+found", 'library_not_found', 0.9),
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        signals = []
        
        for event in events:
            if event.level != LogLevel.ERROR:
                continue
            
            # Check keyword patterns
            for pattern, issue_type, confidence in self.KEYWORD_PATTERNS:
                match = re.search(pattern, event.message, re.IGNORECASE)
                if match:
                    keyword_name = match.group(1) if match.groups() else "unknown"
                    
                    signals.append(FailureSignal(
                        signal_type=SignalType.KEYWORD_NOT_FOUND,
                        message=f"Robot keyword issue ({issue_type}): {event.message}",
                        confidence=confidence,
                        stacktrace=event.stacktrace,
                        file=event.test_file,
                        metadata={
                            'issue_type': issue_type,
                            'keyword_name': keyword_name,
                            'test_name': event.test_name,
                        },
                        is_retryable=False,
                        is_infra_related=False,
                    ))
                    break
            
            # Check library patterns
            for pattern, issue_type, confidence in self.LIBRARY_PATTERNS:
                match = re.search(pattern, event.message, re.IGNORECASE)
                if match:
                    library_name = match.group(1) if match.groups() else "unknown"
                    
                    signals.append(FailureSignal(
                        signal_type=SignalType.LIBRARY_ERROR,
                        message=f"Robot library issue ({issue_type}): {event.message}",
                        confidence=confidence,
                        stacktrace=event.stacktrace,
                        file=event.test_file,
                        metadata={
                            'issue_type': issue_type,
                            'library_name': library_name,
                            'test_name': event.test_name,
                        },
                        is_retryable=False,
                        is_infra_related=False,
                    ))
                    break
        
        return signals


# ============================================================================
# PYTEST EXTRACTORS
# ============================================================================

class PytestFixtureExtractor(FailureSignalExtractor):
    """
    Extract Pytest fixture failures.
    
    Fixture failures indicate:
    - Setup/teardown issues
    - Dependency problems
    - Scope issues
    """
    
    FIXTURE_PATTERNS = [
        (r"fixture\s+'([^']+)'\s+not\s+found", 'fixture_not_found', 0.95),
        (r"Error\s+in\s+fixture\s+'([^']+)'", 'fixture_error', 0.9),
        (r"ScopeMismatch.*fixture\s+'([^']+)'", 'scope_mismatch', 0.85),
        (r"fixture\s+'([^']+)'.*setup", 'setup_failure', 0.9),
        (r"fixture\s+'([^']+)'.*teardown", 'teardown_failure', 0.9),
    ]
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        signals = []
        
        for event in events:
            if event.level != LogLevel.ERROR:
                continue
            
            for pattern, issue_type, confidence in self.FIXTURE_PATTERNS:
                match = re.search(pattern, event.message, re.IGNORECASE)
                if match:
                    fixture_name = match.group(1) if match.groups() else "unknown"
                    
                    signals.append(FailureSignal(
                        signal_type=SignalType.FIXTURE_ERROR,
                        message=f"Pytest fixture issue ({issue_type}): {event.message}",
                        confidence=confidence,
                        stacktrace=event.stacktrace,
                        file=event.test_file,
                        metadata={
                            'issue_type': issue_type,
                            'fixture_name': fixture_name,
                            'test_name': event.test_name,
                        },
                        is_retryable=False,
                        is_infra_related=False,
                    ))
                    break
        
        return signals


class PytestAssertionExtractor(FailureSignalExtractor):
    """
    Extract Pytest assertion failures with details.
    
    Pytest assertions provide rich information:
    - Expected vs actual values
    - Assertion expression
    - Comparison type
    """
    
    def extract(self, events: List[ExecutionEvent]) -> List[FailureSignal]:
        signals = []
        
        for event in events:
            if event.level != LogLevel.ERROR:
                continue
            
            # Look for assertion patterns
            if 'AssertionError' in event.message or 'assert ' in event.message.lower():
                # Try to extract assertion expression
                expression_match = re.search(
                    r'assert\s+(.+?)(?:\n|$)',
                    event.message,
                    re.IGNORECASE
                )
                
                # Try to extract comparison values
                comparison_match = re.search(
                    r'(.+?)\s*==\s*(.+?)(?:\n|where)',
                    event.message
                )
                
                metadata = {
                    'test_name': event.test_name,
                }
                
                if expression_match:
                    metadata['assertion_expression'] = expression_match.group(1).strip()
                
                if comparison_match:
                    metadata['left_value'] = comparison_match.group(1).strip()
                    metadata['right_value'] = comparison_match.group(2).strip()
                
                signals.append(FailureSignal(
                    signal_type=SignalType.ASSERTION,
                    message=f"Pytest assertion failure: {event.message}",
                    confidence=0.95,
                    stacktrace=event.stacktrace,
                    file=event.test_file,
                    metadata=metadata,
                    is_retryable=False,
                    is_infra_related=False,
                ))
        
        return signals
