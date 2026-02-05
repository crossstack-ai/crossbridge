"""
Rule-Based Classification Engine

Deterministic failure classification using pattern matching and heuristics.
NO AI - this ensures the system works offline and is fully explainable.

Classification rules map failure signals to failure types with confidence scores.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re

from core.execution.intelligence.models import (
    FailureSignal,
    FailureType,
    FailureClassification,
    SignalType
)


@dataclass
class ClassificationRule:
    """
    A single classification rule.
    
    Rules are checked in order of priority (higher first).
    """
    name: str
    conditions: List[str]  # Keywords/patterns that must be present
    failure_type: FailureType
    confidence: float
    priority: int = 0  # Higher priority rules are checked first
    
    # Optional conditions
    signal_types: Optional[List[SignalType]] = None  # Specific signal types
    exclude_patterns: Optional[List[str]] = None  # Patterns that disqualify this rule
    
    def matches(self, signals: List[FailureSignal], context: Dict[str, Any]) -> bool:
        """Check if this rule matches the given signals and context"""
        if not signals:
            return False
        
        # Check signal types if specified
        if self.signal_types:
            signal_type_set = {s.signal_type for s in signals}
            if not any(st in signal_type_set for st in self.signal_types):
                return False
        
        # Check conditions (keywords must be present)
        all_text = ' '.join([s.message.lower() for s in signals])
        
        # At least one condition must match
        matches_condition = any(
            cond.lower() in all_text for cond in self.conditions
        )
        
        if not matches_condition:
            return False
        
        # Check exclusion patterns
        if self.exclude_patterns:
            if any(re.search(pattern, all_text, re.IGNORECASE) for pattern in self.exclude_patterns):
                return False
        
        return True
    
    def apply(self, signals: List[FailureSignal], context: Dict[str, Any]) -> FailureClassification:
        """Apply this rule to create a classification"""
        # Gather evidence from matching signals
        evidence = []
        for signal in signals:
            if any(cond.lower() in signal.message.lower() for cond in self.conditions):
                evidence.append(signal.message[:200])  # First 200 chars
        
        # Build reason
        reason = self._build_reason(signals, context)
        
        return FailureClassification(
            failure_type=self.failure_type,
            confidence=self.confidence,
            reason=reason,
            evidence=evidence[:5],  # Max 5 pieces of evidence
            rule_matched=self.name
        )
    
    def _build_reason(self, signals: List[FailureSignal], context: Dict[str, Any]) -> str:
        """Build human-readable reason for classification"""
        signal_types_str = ', '.join(set(s.signal_type.value for s in signals[:3]))
        return f"{self.failure_type.value}: Detected {signal_types_str} based on rule '{self.name}'"


class RuleBasedClassifier:
    """
    Rule-based classifier for failure analysis.
    
    This is the deterministic backbone that ensures the system works
    without AI and provides explainable classifications.
    """
    
    def __init__(self):
        self.rules = self._load_default_rules()
    
    def classify(
        self,
        signals: List[FailureSignal],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[FailureClassification]:
        """
        Classify failure based on signals and context.
        
        Args:
            signals: Extracted failure signals
            context: Additional context (test metadata, environment, etc.)
            
        Returns:
            FailureClassification or None if no rules match
        """
        if not signals:
            return None
        
        context = context or {}
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        # Try each rule in order
        for rule in sorted_rules:
            if rule.matches(signals, context):
                classification = rule.apply(signals, context)
                
                # Enhance with signal-specific details
                classification = self._enhance_classification(classification, signals)
                
                return classification
        
        # No rules matched - return UNKNOWN
        return FailureClassification(
            failure_type=FailureType.UNKNOWN,
            confidence=0.5,
            reason="Unable to classify failure - no matching rules",
            evidence=[s.message[:200] for s in signals[:3]],
            rule_matched=None
        )
    
    def classify_with_reasoning(
        self,
        signals: List[FailureSignal],
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[FailureType, float, str]:
        """
        Classify failure and return simple tuple.
        
        Convenience method for enhanced analyzer.
        
        Args:
            signals: Extracted failure signals
            context: Additional context
            
        Returns:
            (failure_type, confidence, reasoning) tuple
        """
        classification = self.classify(signals, context)
        
        if classification:
            return (
                classification.failure_type,
                classification.confidence,
                classification.reason
            )
        else:
            return (
                FailureType.UNKNOWN,
                0.0,
                "No failure signals detected"
            )
    
    def add_rule(self, rule: ClassificationRule):
        """Add a custom classification rule"""
        self.rules.append(rule)
    
    def _enhance_classification(
        self,
        classification: FailureClassification,
        signals: List[FailureSignal]
    ) -> FailureClassification:
        """Enhance classification with signal-specific details"""
        
        # For locator failures, provide more specific reason
        if any(s.signal_type == SignalType.LOCATOR for s in signals):
            locator_signals = [s for s in signals if s.signal_type == SignalType.LOCATOR]
            if locator_signals and locator_signals[0].metadata:
                locator_value = locator_signals[0].metadata.get('locator_value')
                if locator_value:
                    classification.reason = (
                        f"Automation defect: Unable to locate element with locator '{locator_value}'. "
                        f"Likely due to UI changes or incorrect selector."
                    )
        
        # For assertion failures, provide expected vs actual
        elif any(s.signal_type == SignalType.ASSERTION for s in signals):
            assertion_signals = [s for s in signals if s.signal_type == SignalType.ASSERTION]
            if assertion_signals and assertion_signals[0].metadata:
                metadata = assertion_signals[0].metadata
                expected = metadata.get('expected')
                actual = metadata.get('actual')
                if expected and actual:
                    classification.reason = (
                        f"Product defect: Assertion failed - expected '{expected}' but got '{actual}'"
                    )
        
        # For timeout failures, provide duration info
        elif any(s.signal_type == SignalType.TIMEOUT for s in signals):
            timeout_signals = [s for s in signals if s.signal_type == SignalType.TIMEOUT]
            if timeout_signals and timeout_signals[0].metadata:
                duration = timeout_signals[0].metadata.get('timeout_duration')
                if duration:
                    classification.reason = (
                        f"Environment issue: Operation timed out after {duration}s. "
                        f"Check network connectivity and system resources."
                    )
        
        return classification
    
    def _load_default_rules(self) -> List[ClassificationRule]:
        """Load default classification rules"""
        return [
            # ========== AUTOMATION DEFECTS (Priority 90-100) ==========
            
            ClassificationRule(
                name="locator_not_found",
                conditions=["NoSuchElementException", "NoSuchElement", "locator", "selector"],
                failure_type=FailureType.AUTOMATION_DEFECT,
                confidence=0.92,
                priority=95,
                signal_types=[SignalType.LOCATOR],
                exclude_patterns=[r'network', r'connection', r'dns']
            ),
            
            ClassificationRule(
                name="stale_element",
                conditions=["StaleElementReferenceException", "stale element", "element is stale"],
                failure_type=FailureType.AUTOMATION_DEFECT,
                confidence=0.90,
                priority=90
            ),
            
            ClassificationRule(
                name="invalid_selector",
                conditions=["InvalidSelectorException", "invalid xpath", "invalid css", "syntax error"],
                failure_type=FailureType.AUTOMATION_DEFECT,
                confidence=0.95,
                priority=95,
                signal_types=[SignalType.LOCATOR, SignalType.SYNTAX_ERROR]
            ),
            
            ClassificationRule(
                name="webdriver_error",
                conditions=["WebDriverException", "driver", "session"],
                failure_type=FailureType.AUTOMATION_DEFECT,
                confidence=0.85,
                priority=80
            ),
            
            # ========== PRODUCT DEFECTS (Priority 80-90) ==========
            
            ClassificationRule(
                name="assertion_failure",
                conditions=["AssertionError", "assert", "expected", "actual"],
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.88,
                priority=85,
                signal_types=[SignalType.ASSERTION],
                exclude_patterns=[r'NoSuchElement', r'timeout', r'connection']
            ),
            
            ClassificationRule(
                name="job_operation_failure",
                conditions=["job.*failed", "operation.*failed", "ended with status.*failed", "status: failed"],
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.82,
                priority=80,
                signal_types=[SignalType.ASSERTION],
                exclude_patterns=[r'NoSuchElement', r'timeout', r'connection']
            ),
            
            ClassificationRule(
                name="unexpected_value",
                conditions=["expected", "but was", "but got", "should be"],
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.85,
                priority=80,
                exclude_patterns=[r'timeout', r'connection', r'NoSuchElement']
            ),
            
            ClassificationRule(
                name="http_server_error",
                conditions=["500", "502", "503", "504", "Internal Server Error"],
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.80,
                priority=75,
                signal_types=[SignalType.HTTP_ERROR]
            ),
            
            ClassificationRule(
                name="http_client_error",
                conditions=["400", "401", "403", "404", "422"],
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.75,
                priority=70,
                signal_types=[SignalType.HTTP_ERROR],
                exclude_patterns=[r'configuration', r'credentials']
            ),
            
            ClassificationRule(
                name="null_pointer_error",
                conditions=["NullPointerException", "null reference", "None has no attribute"],
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.82,
                priority=75,
                signal_types=[SignalType.NULL_POINTER]
            ),
            
            # ========== ENVIRONMENT ISSUES (Priority 85-95) ==========
            
            ClassificationRule(
                name="network_timeout",
                conditions=["timeout", "timed out", "TimeoutException"],
                failure_type=FailureType.ENVIRONMENT_ISSUE,
                confidence=0.75,
                priority=70,
                signal_types=[SignalType.TIMEOUT],
                exclude_patterns=[r'element.*not.*found', r'locator']
            ),
            
            ClassificationRule(
                name="connection_refused",
                conditions=["connection refused", "connection reset", "ConnectionError"],
                failure_type=FailureType.ENVIRONMENT_ISSUE,
                confidence=0.92,
                priority=90,
                signal_types=[SignalType.CONNECTION_ERROR]
            ),
            
            ClassificationRule(
                name="dns_failure",
                conditions=["DNS", "name resolution", "host not found", "cannot resolve"],
                failure_type=FailureType.ENVIRONMENT_ISSUE,
                confidence=0.95,
                priority=95,
                signal_types=[SignalType.DNS_ERROR]
            ),
            
            ClassificationRule(
                name="network_unreachable",
                conditions=["network unreachable", "network error", "no route to host"],
                failure_type=FailureType.ENVIRONMENT_ISSUE,
                confidence=0.90,
                priority=90
            ),
            
            ClassificationRule(
                name="memory_error",
                conditions=["MemoryError", "OutOfMemoryError", "out of memory"],
                failure_type=FailureType.ENVIRONMENT_ISSUE,
                confidence=0.90,
                priority=85,
                signal_types=[SignalType.MEMORY_ERROR]
            ),
            
            # ========== CONFIGURATION ISSUES (Priority 75-85) ==========
            
            ClassificationRule(
                name="permission_denied",
                conditions=["permission denied", "access denied", "PermissionError"],
                failure_type=FailureType.CONFIGURATION_ISSUE,
                confidence=0.88,
                priority=85,
                signal_types=[SignalType.PERMISSION_ERROR]
            ),
            
            ClassificationRule(
                name="file_not_found",
                conditions=["file not found", "no such file", "FileNotFoundError"],
                failure_type=FailureType.CONFIGURATION_ISSUE,
                confidence=0.85,
                priority=80,
                signal_types=[SignalType.FILE_NOT_FOUND]
            ),
            
            ClassificationRule(
                name="import_error",
                conditions=["ImportError", "ModuleNotFoundError", "cannot import"],
                failure_type=FailureType.CONFIGURATION_ISSUE,
                confidence=0.90,
                priority=85,
                signal_types=[SignalType.IMPORT_ERROR]
            ),
            
            ClassificationRule(
                name="authentication_error",
                conditions=["401", "Unauthorized", "authentication failed", "invalid credentials"],
                failure_type=FailureType.CONFIGURATION_ISSUE,
                confidence=0.85,
                priority=80
            ),
            
            ClassificationRule(
                name="missing_dependency",
                conditions=["module not found", "package not found", "dependency", "not installed"],
                failure_type=FailureType.CONFIGURATION_ISSUE,
                confidence=0.88,
                priority=80,
                signal_types=[SignalType.IMPORT_ERROR]
            ),
            
            ClassificationRule(
                name="data_not_found",
                conditions=["not found", "missing", "unavailable", "does not exist", "cannot find"],
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.75,
                priority=70,
                signal_types=[SignalType.ASSERTION, SignalType.INFRASTRUCTURE],
                exclude_patterns=[r'NoSuchElement', r'element.*not.*found', r'locator', r'selector']
            ),
        ]
