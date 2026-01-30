"""
JSON Structured Log Adapter

Universal adapter for JSON-formatted application logs including:
- Application JSON logs
- ELK/Elasticsearch logs
- Fluentd/FluentBit logs
- Kubernetes container logs (JSON)
- CloudWatch logs (JSON)
- Custom JSON formats

All JSON formats are normalized into the canonical NormalizedLogEvent structure.
"""

import json
import logging
import re
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List

from core.execution.intelligence.log_adapters import BaseLogAdapter
from core.execution.intelligence.log_adapters.schema import (
    NormalizedLogEvent,
    LogLevel,
    ExtractedSignals
)

logger = logging.getLogger(__name__)


class JSONLogAdapter(BaseLogAdapter):
    """
    Adapter for JSON structured logs.
    
    Supports multiple JSON log formats with intelligent field mapping:
    - Standard: timestamp, level, message
    - ELK: @timestamp, severity
    - Fluentd: time, level, msg
    - Custom: flexible field mapping
    """
    
    # Known timestamp field names (checked in order)
    TIMESTAMP_FIELDS = [
        'timestamp',
        '@timestamp',
        'time',
        'datetime',
        'ts',
        'event_time',
        'log_timestamp',
    ]
    
    # Known log level field names
    LEVEL_FIELDS = [
        'level',
        'severity',
        'log_level',
        'priority',
    ]
    
    # Known message field names
    MESSAGE_FIELDS = [
        'message',
        'msg',
        'text',
        'log',
        'content',
    ]
    
    # Known service field names
    SERVICE_FIELDS = [
        'service',
        'service_name',
        'app',
        'application',
        'app_name',
    ]
    
    # Known component/logger field names
    COMPONENT_FIELDS = [
        'component',
        'logger',
        'logger_name',
        'class',
        'category',
    ]
    
    # Error type patterns
    ERROR_TYPE_PATTERNS = [
        r'(\w+Exception)',
        r'(\w+Error)',
        r'Error:\s*(\w+)',
        r'Exception:\s*(\w+)',
    ]
    
    # Timeout indicators
    TIMEOUT_KEYWORDS = [
        'timeout',
        'timed out',
        'deadline exceeded',
        'connection timeout',
        'read timeout',
        'write timeout',
    ]
    
    # Retry indicators
    RETRY_KEYWORDS = [
        'retry',
        'retrying',
        'retry attempt',
        'attempt',
        're-trying',
    ]
    
    # Circuit breaker indicators
    CIRCUIT_BREAKER_KEYWORDS = [
        'circuit breaker',
        'circuit open',
        'circuit closed',
        'circuit half-open',
        'breaker tripped',
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize JSON log adapter.
        
        Args:
            config: Optional configuration for custom field mappings
        """
        self.config = config or {}
        
        # Custom field mappings (override defaults)
        self.timestamp_fields = self.config.get('timestamp_fields', self.TIMESTAMP_FIELDS)
        self.level_fields = self.config.get('level_fields', self.LEVEL_FIELDS)
        self.message_fields = self.config.get('message_fields', self.MESSAGE_FIELDS)
        self.service_fields = self.config.get('service_fields', self.SERVICE_FIELDS)
        self.component_fields = self.config.get('component_fields', self.COMPONENT_FIELDS)
    
    def can_handle(self, source: str) -> bool:
        """
        Check if this adapter can handle the given source.
        
        Args:
            source: Log file path or format identifier
            
        Returns:
            True if source is JSON format
        """
        # Check file extension
        if source.endswith('.json') or source.endswith('.jsonl'):
            return True
        
        # Check format identifier
        if source.lower() in ['json', 'jsonl', 'elk', 'fluentd', 'fluentbit']:
            return True
        
        return False
    
    def parse(self, raw_line: str) -> Optional[dict]:
        """
        Parse a single JSON log line.
        
        Args:
            raw_line: JSON log line as string
            
        Returns:
            Normalized log event dict or None if parsing fails
        """
        if not raw_line or not raw_line.strip():
            return None
        
        try:
            data = json.loads(raw_line)
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse JSON log line: {e}")
            return None
        
        # Normalize the log event
        return self._normalize(data)
    
    def _normalize(self, data: Dict[str, Any]) -> dict:
        """
        Normalize JSON log data into canonical structure.
        
        Args:
            data: Raw JSON log data
            
        Returns:
            Normalized log event dict
        """
        event = NormalizedLogEvent(
            timestamp=self._parse_timestamp(data),
            level=self._parse_level(data),
            message=self._parse_message(data),
            service=self._parse_service(data),
            component=self._parse_component(data),
            error_type=self._extract_error_type(data),
            exception_class=self._extract_exception_class(data),
            stack_trace=self._extract_stack_trace(data),
            trace_id=self._extract_trace_id(data),
            span_id=self._extract_span_id(data),
            parent_span_id=self._extract_parent_span_id(data),
            host=self._extract_host(data),
            container_id=self._extract_container_id(data),
            pod_name=self._extract_pod_name(data),
            user_id=self._extract_user_id(data),
            request_id=self._extract_request_id(data),
            session_id=self._extract_session_id(data),
            duration_ms=self._extract_duration(data),
            response_code=self._extract_response_code(data),
            raw=data  # NEVER lose the original payload
        )
        
        return event.to_dict()
    
    def _parse_timestamp(self, data: Dict[str, Any]) -> datetime:
        """
        Parse timestamp from log data.
        
        Tries multiple field names and formats.
        """
        for field in self.timestamp_fields:
            if field in data:
                ts_value = data[field]
                
                # Try parsing as ISO format
                try:
                    # Handle timezone Z suffix
                    if isinstance(ts_value, str):
                        ts_value = ts_value.replace('Z', '+00:00')
                        return datetime.fromisoformat(ts_value)
                    # Handle Unix timestamp (seconds or milliseconds)
                    elif isinstance(ts_value, (int, float)):
                        # If > 1e10, it's probably milliseconds
                        if ts_value > 1e10:
                            ts_value = ts_value / 1000
                        return datetime.fromtimestamp(ts_value)
                except (ValueError, OSError) as e:
                    logger.debug(f"Failed to parse timestamp {ts_value}: {e}")
                    continue
        
        # Fallback to current time if no timestamp found
        return datetime.now(UTC)
    
    def _parse_level(self, data: Dict[str, Any]) -> LogLevel:
        """Parse log level from data."""
        for field in self.level_fields:
            if field in data:
                level_str = str(data[field]).upper()
                
                # Map to standard levels
                if 'DEBUG' in level_str:
                    return LogLevel.DEBUG
                elif 'INFO' in level_str or 'INFORMATION' in level_str:
                    return LogLevel.INFO
                elif 'WARN' in level_str or 'WARNING' in level_str:
                    return LogLevel.WARN
                elif 'ERROR' in level_str:
                    return LogLevel.ERROR
                elif 'FATAL' in level_str or 'CRITICAL' in level_str:
                    return LogLevel.FATAL
        
        # Default to INFO if no level found
        return LogLevel.INFO
    
    def _parse_message(self, data: Dict[str, Any]) -> str:
        """Parse message from data."""
        for field in self.message_fields:
            if field in data:
                message = data[field]
                if message:
                    return str(message)
        
        # Fallback: stringify entire data if no message field
        return json.dumps(data)
    
    def _parse_service(self, data: Dict[str, Any]) -> Optional[str]:
        """Parse service name from data."""
        for field in self.service_fields:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _parse_component(self, data: Dict[str, Any]) -> Optional[str]:
        """Parse component/logger name from data."""
        for field in self.component_fields:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_error_type(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract error type from log data."""
        # Check direct error_type field
        if 'error_type' in data:
            return str(data['error_type'])
        
        # Check exception field
        if 'exception' in data:
            exc = data['exception']
            if isinstance(exc, dict) and 'type' in exc:
                return str(exc['type'])
            elif isinstance(exc, str):
                return exc
        
        # Check error field
        if 'error' in data:
            error = data['error']
            if isinstance(error, dict) and 'type' in error:
                return str(error['type'])
            elif isinstance(error, str):
                # Try to extract exception type from string
                for pattern in self.ERROR_TYPE_PATTERNS:
                    match = re.search(pattern, error)
                    if match:
                        return match.group(1)
        
        # Try extracting from message
        message = self._parse_message(data)
        for pattern in self.ERROR_TYPE_PATTERNS:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_exception_class(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract exception class name."""
        if 'exception' in data:
            exc = data['exception']
            if isinstance(exc, dict):
                return exc.get('class') or exc.get('type')
        return self._extract_error_type(data)
    
    def _extract_stack_trace(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract stack trace from log data."""
        # Check common stack trace fields
        for field in ['stack_trace', 'stacktrace', 'stack', 'trace']:
            if field in data and data[field]:
                return str(data[field])
        
        # Check exception.stack
        if 'exception' in data:
            exc = data['exception']
            if isinstance(exc, dict) and 'stack' in exc:
                return str(exc['stack'])
        
        return None
    
    def _extract_trace_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract distributed trace ID."""
        for field in ['trace_id', 'traceId', 'trace', 'x-trace-id']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_span_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract span ID."""
        for field in ['span_id', 'spanId', 'span', 'x-span-id']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_parent_span_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract parent span ID."""
        for field in ['parent_span_id', 'parentSpanId', 'parent_span', 'x-parent-span-id']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_host(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract host/hostname."""
        for field in ['host', 'hostname', 'server', 'machine']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_container_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract container ID."""
        for field in ['container_id', 'containerId', 'container', 'docker_id']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_pod_name(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract Kubernetes pod name."""
        for field in ['pod_name', 'podName', 'pod', 'kubernetes_pod']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_user_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract user ID."""
        for field in ['user_id', 'userId', 'user', 'username']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_request_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract request ID."""
        for field in ['request_id', 'requestId', 'req_id', 'x-request-id']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_session_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID."""
        for field in ['session_id', 'sessionId', 'session']:
            if field in data and data[field]:
                return str(data[field])
        return None
    
    def _extract_duration(self, data: Dict[str, Any]) -> Optional[float]:
        """Extract duration in milliseconds."""
        for field in ['duration_ms', 'duration', 'elapsed_ms', 'elapsed']:
            if field in data and data[field]:
                try:
                    duration = float(data[field])
                    # Convert to milliseconds if in seconds
                    if field == 'duration' and duration < 1000:
                        duration *= 1000
                    return duration
                except (ValueError, TypeError):
                    continue
        return None
    
    def _extract_response_code(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract HTTP response code."""
        for field in ['response_code', 'status_code', 'status', 'http_status']:
            if field in data and data[field]:
                try:
                    return int(data[field])
                except (ValueError, TypeError):
                    continue
        return None
    
    def extract_signals(self, log_event: dict) -> dict:
        """
        Extract anomaly-relevant signals from normalized log event.
        
        These signals feed into:
        - Anomaly detection
        - Flakiness scoring
        - Product defect correlation
        
        Args:
            log_event: Normalized log event dict
            
        Returns:
            ExtractedSignals dict
        """
        message = log_event.get('message', '').lower()
        level = log_event.get('level', 'INFO')
        
        # Error indicators
        is_error = level in ['ERROR', 'FATAL']
        is_timeout = any(keyword in message for keyword in self.TIMEOUT_KEYWORDS)
        is_retry = any(keyword in message for keyword in self.RETRY_KEYWORDS)
        is_circuit_breaker = any(keyword in message for keyword in self.CIRCUIT_BREAKER_KEYWORDS)
        
        # Performance indicators
        duration_ms = log_event.get('duration_ms')
        is_slow = False
        if duration_ms:
            # Consider slow if > 5 seconds
            is_slow = duration_ms > 5000
        
        # Message characteristics
        message_length = len(message)
        
        # Error categorization
        error_category = None
        if is_error:
            if 'timeout' in message or 'connection' in message:
                error_category = 'network'
            elif 'database' in message or 'sql' in message:
                error_category = 'database'
            elif 'auth' in message or 'permission' in message:
                error_category = 'auth'
            elif 'null' in message or 'undefined' in message:
                error_category = 'null_reference'
            else:
                error_category = 'application'
        
        signals = ExtractedSignals(
            is_error=is_error,
            is_timeout=is_timeout,
            is_retry=is_retry,
            is_circuit_breaker=is_circuit_breaker,
            error_type=log_event.get('error_type'),
            error_category=error_category,
            is_slow=is_slow,
            duration_ms=duration_ms,
            message_length=message_length,
            service=log_event.get('service'),
            component=log_event.get('component'),
            host=log_event.get('host'),
        )
        
        return signals.to_dict()


__all__ = ['JSONLogAdapter']
