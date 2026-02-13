"""
Correlation Engine

Links TestNG failures with framework log entries and driver logs.
Builds unified failure representation with root cause analysis.
"""

from typing import List, Optional
from dataclasses import dataclass, field

from core.logging import get_logger, LogCategory
from .log_artifacts import StructuredFailure, FailureCategory
from .framework_log_parser import FrameworkLogEntry, FrameworkLogParser

logger = get_logger(__name__, category=LogCategory.ANALYSIS)


@dataclass
class CorrelatedFailure:
    """
    Unified failure representation with correlated log context.
    
    Combines TestNG failure with related framework logs for root cause.
    """
    # Core failure
    structured_failure: StructuredFailure
    
    # Correlated logs
    framework_errors: List[FrameworkLogEntry] = field(default_factory=list)
    framework_warnings: List[FrameworkLogEntry] = field(default_factory=list)
    
    # Analysis
    category: FailureCategory = FailureCategory.UNKNOWN
    root_cause: Optional[str] = None
    infra_related: bool = False
    flaky_probability: float = 0.0
    
    # Confidence
    correlation_confidence: float = 0.0  # 0.0 - 1.0
    
    def get_combined_context(self) -> str:
        """Get combined error context from all sources"""
        parts = []
        
        if self.structured_failure.error_message:
            parts.append(f"Test Error: {self.structured_failure.error_message}")
        
        if self.framework_errors:
            parts.append(f"\nFramework Errors ({len(self.framework_errors)}):")
            for err in self.framework_errors[:3]:  # Limit to 3
                parts.append(f"  - {err.message}")
        
        if self.framework_warnings:
            parts.append(f"\nFramework Warnings ({len(self.framework_warnings)}):")
            for warn in self.framework_warnings[:2]:  # Limit to 2
                parts.append(f"  - {warn.message}")
        
        return '\n'.join(parts)
    
    def has_logs(self) -> bool:
        """Check if correlated logs exist"""
        return len(self.framework_errors) > 0 or len(self.framework_warnings) > 0


class CorrelationEngine:
    """
    Correlates test failures with framework logs.
    
    Uses time windows and test name matching to link failures
    with relevant log entries.
    """
    
    # Time window for correlation (seconds before/after test)
    TIME_WINDOW_SECONDS = 30
    
    def __init__(self):
        """Initialize correlation engine"""
        self.correlated_failures: List[CorrelatedFailure] = []
    
    def correlate(
        self,
        structured_failures: List[StructuredFailure],
        framework_parser: Optional[FrameworkLogParser] = None
    ) -> List[CorrelatedFailure]:
        """
        Correlate test failures with framework logs.
        
        Args:
            structured_failures: Parsed TestNG failures
            framework_parser: Parsed framework logs (optional)
            
        Returns:
            List of CorrelatedFailure objects
        """
        logger.info(f"Correlating {len(structured_failures)} failures")
        
        self.correlated_failures = []
        
        for failure in structured_failures:
            # Skip passed tests
            if failure.is_passed():
                continue
            
            correlated = self._correlate_single(failure, framework_parser)
            self.correlated_failures.append(correlated)
        
        logger.info(
            f"Correlated {len(self.correlated_failures)} failures, "
            f"{sum(1 for c in self.correlated_failures if c.has_logs())} with framework logs"
        )
        
        return self.correlated_failures
    
    def _correlate_single(
        self,
        failure: StructuredFailure,
        framework_parser: Optional[FrameworkLogParser]
    ) -> CorrelatedFailure:
        """
        Correlate a single failure with logs.
        
        Args:
            failure: Structured failure from TestNG
            framework_parser: Framework log parser
            
        Returns:
            CorrelatedFailure with linked logs
        """
        correlated = CorrelatedFailure(
            structured_failure=failure,
            category=failure.category,
            infra_related=failure.infra_related,
        )
        
        # If no framework logs, return as-is
        if not framework_parser:
            correlated.root_cause = failure.short_error()
            correlated.correlation_confidence = 0.5  # Low confidence without logs
            return correlated
        
        # Find related framework errors
        framework_errors = self._find_related_logs(
            failure,
            framework_parser.get_errors()
        )
        
        framework_warnings = self._find_related_logs(
            failure,
            framework_parser.get_warnings()
        )
        
        correlated.framework_errors = framework_errors
        correlated.framework_warnings = framework_warnings
        
        # Refine categorization based on framework logs
        if framework_errors:
            correlated.category = self._refine_category(failure, framework_errors)
            correlated.infra_related = self._is_infra_related(framework_errors)
            correlated.root_cause = self._extract_root_cause(failure, framework_errors)
            correlated.correlation_confidence = self._calculate_confidence(
                failure, framework_errors
            )
        else:
            correlated.root_cause = failure.short_error()
            correlated.correlation_confidence = 0.6
        
        return correlated
    
    def _find_related_logs(
        self,
        failure: StructuredFailure,
        log_entries: List[FrameworkLogEntry]
    ) -> List[FrameworkLogEntry]:
        """
        Find framework log entries related to a test failure.
        
        Uses test name and class name matching.
        
        Args:
            failure: Test failure
            log_entries: Framework log entries
            
        Returns:
            List of related log entries
        """
        related = []
        
        test_class = failure.class_name.split('.')[-1] if failure.class_name else ""
        method_name = failure.method_name or ""
        
        for entry in log_entries:
            # Check if log entry mentions the test class or method
            if test_class and test_class in entry.logger_name:
                related.append(entry)
            elif method_name and method_name in entry.message:
                related.append(entry)
            elif test_class and test_class in entry.message:
                related.append(entry)
        
        # If no specific matches, include errors near the test
        # (in real implementation, use timestamp correlation)
        if not related and log_entries:
            # Return last few errors as context
            related = log_entries[-3:] if len(log_entries) >= 3 else log_entries
        
        return related
    
    def _refine_category(
        self,
        failure: StructuredFailure,
        framework_errors: List[FrameworkLogEntry]
    ) -> FailureCategory:
        """
        Refine failure category based on framework logs.
        
        Args:
            failure: Test failure
            framework_errors: Related framework errors
            
        Returns:
            Refined FailureCategory
        """
        # Check framework errors for infrastructure patterns
        infra_keywords = [
            'connection', 'timeout', 'network', 'session',
            'webdriver', 'selenium', 'chrome', 'firefox'
        ]
        
        for error in framework_errors:
            error_text = f"{error.message} {error.exception or ''}".lower()
            
            if any(kw in error_text for kw in infra_keywords):
                return FailureCategory.INFRASTRUCTURE
        
        # Keep original category if no strong indicators
        return failure.category
    
    def _is_infra_related(self, framework_errors: List[FrameworkLogEntry]) -> bool:
        """
        Check if errors indicate infrastructure issues.
        
        Args:
            framework_errors: Framework error entries
            
        Returns:
            True if infra-related
        """
        infra_patterns = [
            'connection refused', 'connection reset', 'timeout',
            'session not created', 'webdriver', 'no such session'
        ]
        
        for error in framework_errors:
            error_text = f"{error.message} {error.exception or ''}".lower()
            
            if any(pattern in error_text for pattern in infra_patterns):
                return True
        
        return False
    
    def _extract_root_cause(
        self,
        failure: StructuredFailure,
        framework_errors: List[FrameworkLogEntry]
    ) -> str:
        """
        Extract root cause from failure and logs.
        
        Args:
            failure: Test failure
            framework_errors: Related framework errors
            
        Returns:
            Root cause string
        """
        # Prioritize framework errors as they often have more context
        if framework_errors:
            first_error = framework_errors[0]
            if first_error.exception:
                # Extract first line of exception
                first_line = first_error.exception.split('\n')[0]
                return f"{first_error.message}: {first_line}"
            return first_error.message
        
        # Fallback to test failure message
        return failure.short_error()
    
    def _calculate_confidence(
        self,
        failure: StructuredFailure,
        framework_errors: List[FrameworkLogEntry]
    ) -> float:
        """
        Calculate correlation confidence score.
        
        Args:
            failure: Test failure
            framework_errors: Related framework errors
            
        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.5  # Base confidence
        
        # Boost confidence if framework errors found
        if framework_errors:
            confidence += 0.2
        
        # Boost if test class matches log logger
        test_class = failure.class_name.split('.')[-1] if failure.class_name else ""
        if any(test_class in err.logger_name for err in framework_errors):
            confidence += 0.2
        
        # Boost if exception types match
        if failure.failure_type:
            for err in framework_errors:
                if err.exception and failure.failure_type in err.exception:
                    confidence += 0.1
                    break
        
        return min(confidence, 1.0)
    
    def get_infra_failures(self) -> List[CorrelatedFailure]:
        """Get all infrastructure-related failures"""
        return [f for f in self.correlated_failures if f.infra_related]
    
    def get_test_failures(self) -> List[CorrelatedFailure]:
        """Get all test assertion failures"""
        return [
            f for f in self.correlated_failures
            if f.category == FailureCategory.TEST_ASSERTION
        ]
    
    def get_summary(self) -> dict:
        """Get correlation summary"""
        return {
            'total_failures': len(self.correlated_failures),
            'with_logs': sum(1 for f in self.correlated_failures if f.has_logs()),
            'infra_related': len(self.get_infra_failures()),
            'test_failures': len(self.get_test_failures()),
            'avg_confidence': (
                sum(f.correlation_confidence for f in self.correlated_failures) /
                len(self.correlated_failures)
                if self.correlated_failures else 0.0
            ),
        }
