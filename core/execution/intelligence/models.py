"""
Core Execution Intelligence Models

Defines the normalized data structures for execution analysis.
These models are framework-agnostic and used throughout the analysis pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime

try:
    from core.execution.intelligence.log_sources import LogSourceType
except ImportError:
    # For backward compatibility during migration
    from enum import Enum as _Enum
    class LogSourceType(str, _Enum):
        AUTOMATION = "automation"
        APPLICATION = "application"


class EventType(Enum):
    """
    Event type classification.
    
    Categorizes execution events by their semantic meaning.
    Aligned with industry-standard execution intelligence patterns.
    """
    TEST_START = "test_start"
    TEST_END = "test_end"
    STEP = "step"
    ASSERTION = "assertion"
    LOG = "log"
    FAILURE = "failure"
    RETRY = "retry"
    METRIC = "metric"
    SETUP = "setup"
    TEARDOWN = "teardown"


class LogLevel(Enum):
    """Log severity level"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class FailureType(Enum):
    """
    Failure taxonomy - LOCKED
    
    This classification is critical for CI decisions and team routing.
    """
    PRODUCT_DEFECT = "PRODUCT_DEFECT"  # Application bug
    AUTOMATION_DEFECT = "AUTOMATION_DEFECT"  # Test code issue
    CONFIGURATION_ISSUE = "CONFIGURATION_ISSUE"  # Config problem
    ENVIRONMENT_ISSUE = "ENVIRONMENT_ISSUE"  # Infrastructure/network
    UNKNOWN = "UNKNOWN"  # Unable to classify


class SignalType(Enum):
    """Types of failure signals extracted from logs"""
    TIMEOUT = "timeout"
    ASSERTION = "assertion"
    LOCATOR = "locator"
    NULL_POINTER = "null_pointer"
    HTTP_ERROR = "http_error"
    CONNECTION_ERROR = "connection_error"
    DNS_ERROR = "dns_error"
    PERMISSION_ERROR = "permission_error"
    FILE_NOT_FOUND = "file_not_found"
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    MEMORY_ERROR = "memory_error"
    PERFORMANCE = "performance"  # NEW: Performance-related signals
    INFRASTRUCTURE = "infrastructure"  # NEW: Infrastructure health signals
    # Selenium-specific signals
    UI_TIMEOUT = "ui_timeout"
    UI_LOCATOR = "ui_locator"
    UI_STALE = "ui_stale"
    ELEMENT_NOT_FOUND = "element_not_found"
    # Robot-specific signals
    KEYWORD_NOT_FOUND = "keyword_not_found"
    LIBRARY_ERROR = "library_error"
    # Pytest-specific signals
    FIXTURE_ERROR = "fixture_error"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """
    Entity type for execution signals.
    
    Different frameworks have different granularities:
    - BDD: Feature → Scenario → Step
    - Robot: Suite → Test → Keyword
    - Pytest: Module → Test → Assertion
    """
    # BDD entities
    FEATURE = "feature"
    SCENARIO = "scenario"
    STEP = "step"
    
    # Robot entities
    SUITE = "suite"
    TEST = "test"
    KEYWORD = "keyword"
    
    # Pytest entities
    MODULE = "module"
    FUNCTION = "function"
    ASSERTION = "assertion"
    FIXTURE = "fixture"
    
    # Generic
    TEST_CASE = "test_case"
    UNKNOWN = "unknown"


@dataclass
class ExecutionEvent:
    """
    Normalized execution event.
    
    All framework-specific logs MUST be converted to this model.
    This is the universal contract for execution intelligence.
    
    UPDATED: Now includes log_source_type to distinguish between:
    - AUTOMATION logs (test framework) - MANDATORY
    - APPLICATION logs (product/service) - OPTIONAL for enrichment
    
    ALIGNED: Field names match industry-standard execution intelligence patterns
    for better interoperability and clarity.
    """
    timestamp: str
    level: LogLevel
    source: str  # Framework/runner (selenium, pytest, robot, etc.) or service name
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Execution context (NEW - aligned with standard patterns)
    run_id: Optional[str] = None  # Unique execution run identifier
    event_type: Optional['EventType'] = None  # Semantic event categorization
    duration_ms: Optional[int] = None  # Event duration in milliseconds
    
    # Log source classification
    log_source_type: 'LogSourceType' = None  # AUTOMATION or APPLICATION
    
    # Optional structured fields
    test_name: Optional[str] = None
    test_file: Optional[str] = None
    exception_type: Optional[str] = None
    stacktrace: Optional[str] = None
    service_name: Optional[str] = None  # For application logs
    
    def __post_init__(self):
        """Set default log source type if not specified"""
        if self.log_source_type is None:
            # Default to AUTOMATION for backward compatibility
            try:
                from core.execution.intelligence.log_sources import LogSourceType
                self.log_source_type = LogSourceType.AUTOMATION
            except ImportError:
                pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "metadata": self.metadata,
            "run_id": self.run_id,
            "duration_ms": self.duration_ms,
            "test_name": self.test_name,
            "test_file": self.test_file,
            "exception_type": self.exception_type,
            "stacktrace": self.stacktrace,
            "service_name": self.service_name,
        }
        
        # Add log_source_type if available
        if self.log_source_type is not None:
            result["log_source_type"] = str(self.log_source_type)
        
        # Add event_type if available
        if self.event_type is not None:
            result["event_type"] = self.event_type.value
        
        return result


@dataclass
class FailureSignal:
    """
    Extracted failure signal - deterministic, no AI.
    
    Multiple signals can be extracted from a single failure.
    
    ENHANCED: Now includes semantic flags for better CI/CD decision making:
    - is_retryable: Whether this failure can be automatically retried
    - is_infra_related: Whether this is infrastructure vs product issue
    """
    signal_type: SignalType
    message: str
    confidence: float = 1.0  # Confidence in signal extraction (0.0-1.0)
    
    # Context
    stacktrace: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    
    # Semantic flags (NEW - aligned with industry patterns)
    is_retryable: bool = False  # Can this be auto-retried?
    is_infra_related: bool = False  # Infrastructure vs product issue?
    
    # Evidence
    keywords: List[str] = field(default_factory=list)
    patterns_matched: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Auto-infer semantic flags from signal_type if not explicitly set"""
        # Retryable signals (transient failures)
        if self.signal_type in [SignalType.TIMEOUT, SignalType.CONNECTION_ERROR, 
                                 SignalType.DNS_ERROR, SignalType.HTTP_ERROR]:
            if not self.is_retryable:  # Only set if not explicitly set
                self.is_retryable = True
        
        # Infrastructure-related signals
        if self.signal_type in [SignalType.TIMEOUT, SignalType.CONNECTION_ERROR,
                                 SignalType.DNS_ERROR, SignalType.HTTP_ERROR,
                                 SignalType.PERMISSION_ERROR, SignalType.MEMORY_ERROR]:
            if not self.is_infra_related:  # Only set if not explicitly set
                self.is_infra_related = True
        
        # Product/automation-related signals (NOT infrastructure)
        if self.signal_type in [SignalType.ASSERTION, SignalType.LOCATOR,
                                 SignalType.NULL_POINTER, SignalType.SYNTAX_ERROR,
                                 SignalType.IMPORT_ERROR]:
            self.is_retryable = False
            self.is_infra_related = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "signal_type": self.signal_type.value,
            "message": self.message,
            "confidence": self.confidence,
            "stacktrace": self.stacktrace,
            "file": self.file,
            "line": self.line,
            "is_retryable": self.is_retryable,
            "is_infra_related": self.is_infra_related,
            "keywords": self.keywords,
            "patterns_matched": self.patterns_matched,
            "metadata": self.metadata,
        }


@dataclass
class CodeReference:
    """
    Code path and snippet for automation failures.
    
    This is a killer feature - shows EXACTLY where test code failed.
    """
    file: str
    line: int
    snippet: str  # 5-10 lines of code context
    function: Optional[str] = None
    class_name: Optional[str] = None
    
    # Additional context
    repository: Optional[str] = None
    commit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
            "function": self.function,
            "class_name": self.class_name,
            "repository": self.repository,
            "commit": self.commit,
        }


@dataclass
class FailureClassification:
    """
    Classification result - deterministic + optional AI enhancement.
    
    This is the CONTRACT that CI/CD systems depend on.
    """
    failure_type: FailureType
    confidence: float  # 0.0-1.0
    reason: str  # Human-readable explanation
    evidence: List[str] = field(default_factory=list)  # Supporting evidence
    
    # Optional code reference (for automation defects)
    code_reference: Optional[CodeReference] = None
    
    # Classification metadata
    rule_matched: Optional[str] = None  # Which rule was matched
    ai_enhanced: bool = False  # Was AI reasoning applied?
    ai_reasoning: Optional[str] = None  # AI's additional insights
    
    # Historical context
    similar_failures_count: int = 0
    last_seen: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CI/CD integration"""
        result = {
            "failure_type": self.failure_type.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "evidence": self.evidence,
            "code_reference": self.code_reference.to_dict() if self.code_reference else None,
            "rule_matched": self.rule_matched,
            "ai_enhanced": self.ai_enhanced,
            "ai_reasoning": self.ai_reasoning,
            "similar_failures_count": self.similar_failures_count,
            "last_seen": self.last_seen,
        }
        return result


@dataclass
class AnalysisResult:
    """
    Complete analysis result for a test execution.
    
    This is what CLI commands return and what CI/CD systems consume.
    """
    # Test identification
    test_name: str
    test_file: Optional[str] = None
    status: str = "FAILED"  # PASSED, FAILED, SKIPPED, ERROR
    
    # Timing
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    
    # Analysis results
    classification: Optional[FailureClassification] = None
    signals: List[FailureSignal] = field(default_factory=list)
    events: List[ExecutionEvent] = field(default_factory=list)
    
    # Metadata
    framework: str = "unknown"
    environment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for output"""
        return {
            "test_name": self.test_name,
            "test_file": self.test_file,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "classification": self.classification.to_dict() if self.classification else None,
            "signals": [s.to_dict() for s in self.signals],
            "framework": self.framework,
            "environment": self.environment,
            "metadata": self.metadata,
        }
    
    def is_product_defect(self) -> bool:
        """Check if this is a product defect"""
        return (
            self.classification is not None
            and self.classification.failure_type == FailureType.PRODUCT_DEFECT
        )
    
    def is_automation_defect(self) -> bool:
        """Check if this is an automation defect"""
        return (
            self.classification is not None
            and self.classification.failure_type == FailureType.AUTOMATION_DEFECT
        )
    
    def is_environment_issue(self) -> bool:
        """Check if this is an environment issue"""
        return (
            self.classification is not None
            and self.classification.failure_type == FailureType.ENVIRONMENT_ISSUE
        )
    
    def should_fail_ci(self, fail_on: List[FailureType]) -> bool:
        """
        Determine if CI should fail based on failure type.
        
        Example: fail_on=[FailureType.PRODUCT_DEFECT]
        """
        if self.classification is None:
            return True  # Default to failing on unknown
        
        return self.classification.failure_type in fail_on


# ============================================================================
# CANONICAL EXECUTION SIGNAL SCHEMA - Framework Parity
# ============================================================================

@dataclass
class ExecutionSignal:
    """
    Canonical execution signal schema for framework parity.
    
    All frameworks (Selenium Java BDD, Robot, Pytest, etc.) must emit 
    signals in this normalized format for consistent analytics.
    
    This enables:
    - Cross-framework comparison
    - Unified analytics
    - Consistent confidence scoring
    - Framework-agnostic ML models
    """
    # Core identification
    framework: str  # selenium_java_bdd, robot, pytest, etc.
    entity_type: EntityType  # scenario, step, keyword, test, etc.
    name: str  # Entity name (test name, step text, keyword name)
    
    # Execution metrics
    duration_ms: int
    status: str  # PASSED, FAILED, SKIPPED, ERROR
    
    # Failure analysis
    failure_type: Optional[str] = None  # From SignalType enum
    error_message: Optional[str] = None
    stacktrace: Optional[str] = None
    
    # Confidence & metadata
    confidence: float = 1.0  # 0.0-1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timing & context
    timestamp: Optional[str] = None
    run_id: Optional[str] = None
    
    # Retry & infrastructure flags
    is_retryable: bool = False
    is_infra_related: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for analytics pipeline"""
        return {
            "framework": self.framework,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "failure_type": self.failure_type,
            "error_message": self.error_message,
            "stacktrace": self.stacktrace,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "is_retryable": self.is_retryable,
            "is_infra_related": self.is_infra_related,
        }


# ============================================================================
# BDD-SPECIFIC MODELS (Selenium Java BDD / Cucumber)
# ============================================================================

@dataclass
class StepBinding:
    """
    Cucumber step definition binding (Step → Java Method mapping).
    
    Maps natural language steps to Java implementation for:
    - Impact analysis
    - Coverage mapping
    - Root cause analysis
    """
    step_pattern: str  # Regex pattern from @Given/@When/@Then
    annotation_type: str  # Given, When, Then, And, But
    class_name: str
    method_name: str
    file_path: str
    
    # Optional metadata
    parameters: List[str] = field(default_factory=list)
    line_number: Optional[int] = None
    
    def matches(self, step_text: str) -> bool:
        """Check if step text matches this binding's pattern"""
        import re
        try:
            return bool(re.search(self.step_pattern, step_text))
        except re.error:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_pattern": self.step_pattern,
            "annotation_type": self.annotation_type,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "file_path": self.file_path,
            "parameters": self.parameters,
            "line_number": self.line_number,
        }


@dataclass
class CucumberStep:
    """
    Cucumber step execution result.
    
    Step-level signals are CRITICAL for BDD parity.
    """
    keyword: str  # Given, When, Then, And, But
    text: str  # Step text
    status: str  # passed, failed, skipped, pending
    duration_ms: int
    
    # Failure details
    error_message: Optional[str] = None
    stacktrace: Optional[str] = None
    
    # Binding (if resolved)
    binding: Optional[StepBinding] = None
    
    # Retry tracking
    retry_count: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_signal(self, scenario_name: str, run_id: Optional[str] = None) -> ExecutionSignal:
        """Convert to canonical ExecutionSignal"""
        failure_type = None
        if self.status == "failed":
            # Infer failure type from error message
            if self.error_message:
                msg_lower = self.error_message.lower()
                if "timeout" in msg_lower:
                    failure_type = SignalType.UI_TIMEOUT.value
                elif "element" in msg_lower and "not found" in msg_lower:
                    failure_type = SignalType.ELEMENT_NOT_FOUND.value
                elif "stale" in msg_lower:
                    failure_type = SignalType.UI_STALE.value
                elif "assertion" in msg_lower or "assert" in msg_lower:
                    failure_type = SignalType.ASSERTION.value
        
        return ExecutionSignal(
            framework="selenium_java_bdd",
            entity_type=EntityType.STEP,
            name=f"{self.keyword} {self.text}",
            duration_ms=self.duration_ms,
            status=self.status,
            failure_type=failure_type,
            error_message=self.error_message,
            stacktrace=self.stacktrace,
            run_id=run_id,
            metadata={
                "scenario_name": scenario_name,
                "retry_count": self.retry_count,
                "binding": self.binding.to_dict() if self.binding else None,
                **self.metadata
            }
        )


@dataclass
class CucumberScenario:
    """
    Cucumber scenario execution result.
    
    Scenario-level aggregation for analytics.
    """
    name: str
    feature_name: str
    tags: List[str] = field(default_factory=list)
    steps: List[CucumberStep] = field(default_factory=list)
    status: str = "passed"
    duration_ms: int = 0
    
    # Metadata
    line_number: Optional[int] = None
    description: Optional[str] = None
    
    def to_signal(self, run_id: Optional[str] = None) -> ExecutionSignal:
        """Convert to canonical ExecutionSignal"""
        # Aggregate step failures
        failure_types = [
            step.error_message for step in self.steps 
            if step.status == "failed" and step.error_message
        ]
        
        return ExecutionSignal(
            framework="selenium_java_bdd",
            entity_type=EntityType.SCENARIO,
            name=self.name,
            duration_ms=self.duration_ms,
            status=self.status,
            error_message="; ".join(failure_types) if failure_types else None,
            run_id=run_id,
            metadata={
                "feature_name": self.feature_name,
                "tags": self.tags,
                "step_count": len(self.steps),
                "failed_steps": sum(1 for s in self.steps if s.status == "failed"),
                "description": self.description,
            }
        )


# ============================================================================
# ROBOT FRAMEWORK MODELS
# ============================================================================

@dataclass
class RobotKeyword:
    """
    Robot Framework keyword execution result.
    
    Keyword-level signals are CRITICAL for Robot parity.
    """
    name: str
    library: str  # BuiltIn, SeleniumLibrary, custom, etc.
    arguments: List[str] = field(default_factory=list)
    status: str = "PASS"
    duration_ms: int = 0
    
    # Failure details
    error_message: Optional[str] = None
    stacktrace: Optional[str] = None
    
    # Metadata
    keyword_type: str = "KEYWORD"  # KEYWORD, SETUP, TEARDOWN
    doc: Optional[str] = None
    
    def to_signal(self, test_name: str, suite_name: str, run_id: Optional[str] = None) -> ExecutionSignal:
        """Convert to canonical ExecutionSignal"""
        failure_type = None
        if self.status == "FAIL":
            if self.error_message:
                msg_lower = self.error_message.lower()
                # Check for timeout patterns
                if any(pattern in msg_lower for pattern in ["timeout", "timed out", "did not become visible", "element not visible", "wait until"]):
                    failure_type = SignalType.TIMEOUT.value
                # Check for assertion/comparison patterns
                elif any(pattern in msg_lower for pattern in ["should be", "should not", "!=", "==", "assertion"]) or self.name.lower().startswith("should"):
                    failure_type = SignalType.ASSERTION.value
                # Check for keyword not found
                elif "keyword" in msg_lower and "not found" in msg_lower:
                    failure_type = SignalType.KEYWORD_NOT_FOUND.value
                # Check for library errors
                elif "library" in msg_lower:
                    failure_type = SignalType.LIBRARY_ERROR.value
        
        return ExecutionSignal(
            framework="robot",
            entity_type=EntityType.KEYWORD,
            name=self.name,
            duration_ms=self.duration_ms,
            status=self.status,
            failure_type=failure_type,
            error_message=self.error_message,
            stacktrace=self.stacktrace,
            run_id=run_id,
            metadata={
                "library": self.library,
                "arguments": self.arguments,
                "test_name": test_name,
                "suite_name": suite_name,
                "keyword_type": self.keyword_type,
            }
        )


@dataclass
class RobotTest:
    """
    Robot Framework test case execution result.
    """
    name: str
    suite_name: str
    keywords: List[RobotKeyword] = field(default_factory=list)
    status: str = "PASS"
    duration_ms: int = 0
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    doc: Optional[str] = None
    
    def to_signal(self, run_id: Optional[str] = None) -> ExecutionSignal:
        """Convert to canonical ExecutionSignal"""
        # Aggregate keyword failures
        failure_messages = [
            kw.error_message for kw in self.keywords
            if kw.status == "FAIL" and kw.error_message
        ]
        
        return ExecutionSignal(
            framework="robot",
            entity_type=EntityType.TEST,
            name=self.name,
            duration_ms=self.duration_ms,
            status=self.status,
            error_message="; ".join(failure_messages) if failure_messages else None,
            run_id=run_id,
            metadata={
                "suite_name": self.suite_name,
                "tags": self.tags,
                "keyword_count": len(self.keywords),
                "failed_keywords": sum(1 for kw in self.keywords if kw.status == "FAIL"),
            }
        )


# ============================================================================
# PYTEST MODELS
# ============================================================================

@dataclass
class PytestAssertion:
    """
    Pytest assertion execution result.
    
    Assertion-level signals are CRITICAL for Pytest parity.
    """
    expression: str  # The assertion expression
    status: str  # passed, failed
    
    # Failure details
    error_message: Optional[str] = None
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None
    
    # Location
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    
    def to_signal(self, test_name: str, run_id: Optional[str] = None) -> ExecutionSignal:
        """Convert to canonical ExecutionSignal"""
        return ExecutionSignal(
            framework="pytest",
            entity_type=EntityType.ASSERTION,
            name=self.expression,
            duration_ms=0,  # Assertions don't have individual duration
            status=self.status,
            failure_type=SignalType.ASSERTION.value if self.status == "failed" else None,
            error_message=self.error_message,
            run_id=run_id,
            metadata={
                "test_name": test_name,
                "actual_value": self.actual_value,
                "expected_value": self.expected_value,
                "file_path": self.file_path,
                "line_number": self.line_number,
            }
        )


@dataclass
class PytestFixture:
    """
    Pytest fixture execution result.
    
    Fixture awareness is CRITICAL for Pytest parity.
    """
    name: str
    scope: str  # function, class, module, package, session
    phase: str  # setup, teardown
    status: str  # passed, failed, skipped
    duration_ms: int = 0
    
    # Failure details
    error_message: Optional[str] = None
    stacktrace: Optional[str] = None
    
    def to_signal(self, test_name: str, run_id: Optional[str] = None) -> ExecutionSignal:
        """Convert to canonical ExecutionSignal"""
        return ExecutionSignal(
            framework="pytest",
            entity_type=EntityType.FIXTURE,
            name=self.name,
            duration_ms=self.duration_ms,
            status=self.status,
            failure_type=SignalType.FIXTURE_ERROR.value if self.status == "failed" else None,
            error_message=self.error_message,
            stacktrace=self.stacktrace,
            run_id=run_id,
            metadata={
                "test_name": test_name,
                "scope": self.scope,
                "phase": self.phase,
            }
        )


@dataclass
class PytestTest:
    """
    Pytest test function execution result.
    """
    name: str
    module: str
    markers: List[str] = field(default_factory=list)
    fixtures: List[PytestFixture] = field(default_factory=list)
    assertions: List[PytestAssertion] = field(default_factory=list)
    status: str = "passed"
    duration_ms: int = 0
    
    # Failure details
    error_message: Optional[str] = None
    stacktrace: Optional[str] = None
    
    def to_signal(self, run_id: Optional[str] = None) -> ExecutionSignal:
        """Convert to canonical ExecutionSignal"""
        # Determine failure type
        failure_type = None
        if self.status == "failed":
            # Check if fixture failure
            fixture_failures = [f for f in self.fixtures if f.status == "failed"]
            if fixture_failures:
                failure_type = SignalType.FIXTURE_ERROR.value
            # Check if assertion failure
            elif any(a.status == "failed" for a in self.assertions):
                failure_type = SignalType.ASSERTION.value
            # Check error message for other types
            elif self.error_message:
                msg_lower = self.error_message.lower()
                if "timeout" in msg_lower:
                    failure_type = SignalType.TIMEOUT.value
                elif "import" in msg_lower:
                    failure_type = SignalType.IMPORT_ERROR.value
        
        return ExecutionSignal(
            framework="pytest",
            entity_type=EntityType.FUNCTION,
            name=self.name,
            duration_ms=self.duration_ms,
            status=self.status,
            failure_type=failure_type,
            error_message=self.error_message,
            stacktrace=self.stacktrace,
            run_id=run_id,
            metadata={
                "module": self.module,
                "markers": self.markers,
                "fixture_count": len(self.fixtures),
                "assertion_count": len(self.assertions),
                "failed_fixtures": sum(1 for f in self.fixtures if f.status == "failed"),
                "failed_assertions": sum(1 for a in self.assertions if a.status == "failed"),
            }
        )

