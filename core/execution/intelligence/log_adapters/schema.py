"""
Normalized Log Schema

Canonical structure that all log adapters must emit.
This ensures consistent processing across different log formats.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(str, Enum):
    """Standard log levels (normalized)."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


@dataclass
class NormalizedLogEvent:
    """
    Canonical normalized log event structure.
    
    ALL log adapters (JSON, ELK, Fluentd, plain text) must emit this structure.
    
    This is the universal format for log processing, anomaly detection,
    and correlation with test execution events.
    """
    
    # Core fields (required)
    timestamp: datetime
    level: LogLevel
    message: str
    
    # Service identification
    service: Optional[str] = None
    component: Optional[str] = None
    
    # Error tracking
    error_type: Optional[str] = None
    exception_class: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Distributed tracing
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    
    # Infrastructure
    host: Optional[str] = None
    container_id: Optional[str] = None
    pod_name: Optional[str] = None
    
    # Application context
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    response_code: Optional[int] = None
    
    # Original payload (NEVER lose the raw log)
    raw: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'service': self.service,
            'component': self.component,
            'message': self.message,
            'error_type': self.error_type,
            'exception_class': self.exception_class,
            'stack_trace': self.stack_trace,
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'host': self.host,
            'container_id': self.container_id,
            'pod_name': self.pod_name,
            'user_id': self.user_id,
            'request_id': self.request_id,
            'session_id': self.session_id,
            'duration_ms': self.duration_ms,
            'response_code': self.response_code,
            'raw': self.raw,
            'metadata': self.metadata,
        }
    
    def is_error(self) -> bool:
        """Check if this is an error-level log."""
        return self.level in [LogLevel.ERROR, LogLevel.FATAL]
    
    def has_trace(self) -> bool:
        """Check if distributed tracing information is available."""
        return self.trace_id is not None
    
    def has_exception(self) -> bool:
        """Check if exception information is present."""
        return self.error_type is not None or self.exception_class is not None


@dataclass
class ExtractedSignals:
    """
    Anomaly-relevant signals extracted from log events.
    
    These signals feed into anomaly detection, flakiness scoring,
    and correlation pipelines.
    """
    
    # Error indicators
    is_error: bool = False
    is_timeout: bool = False
    is_retry: bool = False
    is_circuit_breaker: bool = False
    
    # Error classification
    error_type: Optional[str] = None
    error_category: Optional[str] = None  # network, database, auth, etc.
    
    # Performance indicators
    is_slow: bool = False
    duration_ms: Optional[float] = None
    
    # Message characteristics
    message_length: int = 0
    message_entropy: Optional[float] = None
    
    # Frequency patterns
    occurrence_count: int = 1
    
    # Infrastructure signals
    service: Optional[str] = None
    component: Optional[str] = None
    host: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'is_error': self.is_error,
            'is_timeout': self.is_timeout,
            'is_retry': self.is_retry,
            'is_circuit_breaker': self.is_circuit_breaker,
            'error_type': self.error_type,
            'error_category': self.error_category,
            'is_slow': self.is_slow,
            'duration_ms': self.duration_ms,
            'message_length': self.message_length,
            'message_entropy': self.message_entropy,
            'occurrence_count': self.occurrence_count,
            'service': self.service,
            'component': self.component,
            'host': self.host,
        }


__all__ = [
    'LogLevel',
    'NormalizedLogEvent',
    'ExtractedSignals',
]
