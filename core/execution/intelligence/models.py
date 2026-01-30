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
    """
    timestamp: str
    level: LogLevel
    source: str  # Framework/runner (selenium, pytest, robot, etc.) or service name
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Log source classification (NEW)
    log_source_type: 'LogSourceType' = None  # AUTOMATION or APPLICATION
    
    # Optional structured fields
    test_name: Optional[str] = None
    test_file: Optional[str] = None
    exception_type: Optional[str] = None
    stacktrace: Optional[str] = None
    service_name: Optional[str] = None  # NEW: For application logs
    
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
            "test_name": self.test_name,
            "test_file": self.test_file,
            "exception_type": self.exception_type,
            "stacktrace": self.stacktrace,
            "service_name": self.service_name,
        }
        
        # Add log_source_type if available
        if self.log_source_type is not None:
            result["log_source_type"] = str(self.log_source_type)
        
        return result


@dataclass
class FailureSignal:
    """
    Extracted failure signal - deterministic, no AI.
    
    Multiple signals can be extracted from a single failure.
    """
    signal_type: SignalType
    message: str
    confidence: float = 1.0  # Confidence in signal extraction (0.0-1.0)
    
    # Context
    stacktrace: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    
    # Evidence
    keywords: List[str] = field(default_factory=list)
    patterns_matched: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "signal_type": self.signal_type.value,
            "message": self.message,
            "confidence": self.confidence,
            "stacktrace": self.stacktrace,
            "file": self.file,
            "line": self.line,
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
