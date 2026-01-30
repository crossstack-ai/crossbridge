"""
Sidecar Structured Logging Utilities

Provides structured JSON logging with correlation IDs, context tracking, and
automatic field enrichment.

All logs are emitted in JSON format for easy parsing and indexing.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextvars import ContextVar

# Context variables for correlation tracking
_run_id: ContextVar[Optional[str]] = ContextVar('run_id', default=None)
_test_id: ContextVar[Optional[str]] = ContextVar('test_id', default=None)
_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


# ============================================================================
# Context Management
# ============================================================================

def set_run_id(run_id: str):
    """Set current run ID for correlation."""
    _run_id.set(run_id)


def get_run_id() -> Optional[str]:
    """Get current run ID."""
    return _run_id.get()


def set_test_id(test_id: str):
    """Set current test ID for correlation."""
    _test_id.set(test_id)


def get_test_id() -> Optional[str]:
    """Get current test ID."""
    return _test_id.get()


def set_session_id(session_id: str):
    """Set current session ID for correlation."""
    _session_id.set(session_id)


def get_session_id() -> Optional[str]:
    """Get current session ID."""
    return _session_id.get()


def clear_context():
    """Clear all context variables."""
    _run_id.set(None)
    _test_id.set(None)
    _session_id.set(None)


# ============================================================================
# JSON Formatter
# ============================================================================

class SidecarJSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Automatically enriches log records with:
    - Timestamp (ISO 8601 UTC)
    - Correlation IDs (run_id, test_id, session_id)
    - Logger name
    - Log level
    - Message
    - Extra fields from record
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
        
        Returns:
            JSON string
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add correlation IDs if set
        if run_id := get_run_id():
            log_data['run_id'] = run_id
        
        if test_id := get_test_id():
            log_data['test_id'] = test_id
        
        if session_id := get_session_id():
            log_data['session_id'] = session_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            log_data.update(record.extra)
        
        # Add other custom attributes
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info', 'extra']:
                log_data[key] = value
        
        return json.dumps(log_data)


# ============================================================================
# Logging Setup
# ============================================================================

def setup_sidecar_logging(level: int = logging.INFO):
    """
    Setup sidecar logging with JSON formatter.
    
    Args:
        level: Logging level (default: INFO)
    """
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SidecarJSONFormatter())
    
    # Setup sidecar logger
    logger = logging.getLogger('crossbridge.sidecar')
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False  # Don't propagate to root logger


# ============================================================================
# Convenience Functions
# ============================================================================

def log_sidecar_event(
    event_type: str,
    level: int = logging.INFO,
    **kwargs
):
    """
    Log a sidecar event with structured context.
    
    Args:
        event_type: Type of event (e.g., 'event_queued', 'event_processed')
        level: Log level
        **kwargs: Additional fields to include
    """
    logger = logging.getLogger('crossbridge.sidecar')
    
    # Build log record
    log_data = {
        'event_type': event_type,
        **kwargs
    }
    
    logger.log(level, event_type, extra=log_data)


def log_event_queued(event: Dict[str, Any]):
    """Log event queued."""
    log_sidecar_event(
        'event_queued',
        event_type_detail=event.get('type'),
        event_id=event.get('id')
    )


def log_event_processed(event: Dict[str, Any], duration_ms: float):
    """Log event processed successfully."""
    log_sidecar_event(
        'event_processed',
        event_type_detail=event.get('type'),
        event_id=event.get('id'),
        duration_ms=duration_ms
    )


def log_event_dropped(event: Dict[str, Any], reason: str):
    """Log event dropped."""
    log_sidecar_event(
        'event_dropped',
        level=logging.WARNING,
        event_type_detail=event.get('type'),
        event_id=event.get('id'),
        reason=reason
    )


def log_event_sampled_out(event: Dict[str, Any]):
    """Log event sampled out."""
    log_sidecar_event(
        'event_sampled_out',
        level=logging.DEBUG,
        event_type_detail=event.get('type'),
        event_id=event.get('id')
    )


def log_error(
    operation: str,
    error: Exception,
    **kwargs
):
    """
    Log an error with structured context.
    
    Args:
        operation: Operation that failed
        error: Exception that occurred
        **kwargs: Additional context
    """
    logger = logging.getLogger('crossbridge.sidecar')
    
    log_data = {
        'operation': operation,
        'error_type': type(error).__name__,
        'error_message': str(error),
        **kwargs
    }
    
    logger.error(
        f"Sidecar error in {operation}",
        extra=log_data,
        exc_info=True
    )


def log_resource_budget_exceeded(resource: str, current: float, limit: float):
    """Log resource budget exceeded."""
    log_sidecar_event(
        'resource_budget_exceeded',
        level=logging.WARNING,
        resource=resource,
        current=current,
        limit=limit
    )


def log_config_reloaded(old_config: Dict[str, Any], new_config: Dict[str, Any]):
    """Log configuration reload."""
    log_sidecar_event(
        'config_reloaded',
        old_config=old_config,
        new_config=new_config
    )


def log_profiling_disabled(reason: str):
    """Log profiling disabled."""
    log_sidecar_event(
        'profiling_disabled',
        level=logging.WARNING,
        reason=reason
    )


def log_profiling_enabled():
    """Log profiling enabled."""
    log_sidecar_event(
        'profiling_enabled'
    )


# ============================================================================
# Initialize Logging
# ============================================================================

# Setup logging on module import
setup_sidecar_logging()
