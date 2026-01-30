"""
Log Storage System

Manages persistent storage of application logs with:
- PostgreSQL table for structured logs
- JSONB for flexible metadata
- Indexes for performance
- Retry logic and error handling
- Circuit breaker protection
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, Text, TIMESTAMP, Integer, Float, Boolean, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .error_handling import (
    with_retry,
    with_error_handling,
    LogStorageError,
    RetryConfig,
    get_circuit_breaker
)

logger = logging.getLogger(__name__)

Base = declarative_base()


class ApplicationLog(Base):
    """
    Application log storage model.
    
    Stores normalized application logs for correlation and analysis.
    """
    __tablename__ = 'application_logs'
    
    # Primary key
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Timestamps
    timestamp = Column(TIMESTAMP, nullable=False, index=True)
    ingested_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Core fields
    level = Column(Text, nullable=False, index=True)
    service = Column(Text, index=True)
    component = Column(Text, index=True)
    message = Column(Text, nullable=False)
    
    # Error tracking
    error_type = Column(Text, index=True)
    exception_class = Column(Text)
    stack_trace = Column(Text)
    
    # Distributed tracing
    trace_id = Column(Text, index=True)
    span_id = Column(Text)
    parent_span_id = Column(Text)
    
    # Infrastructure
    host = Column(Text)
    container_id = Column(Text)
    pod_name = Column(Text)
    
    # Application context
    user_id = Column(Text)
    request_id = Column(Text, index=True)
    session_id = Column(Text)
    
    # Performance
    duration_ms = Column(Float)
    response_code = Column(Integer)
    
    # Original payload (JSONB for flexible querying)
    raw = Column(JSON, nullable=False)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
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


class LogStorage:
    """
    Manages log storage operations.
    
    Provides high-performance batch insertion and querying.
    """
    
    def __init__(self, session: Session):
        """
        Initialize log storage.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.circuit_breaker = get_circuit_breaker(
            'log_storage',
            failure_threshold=5,
            timeout=60.0
        )
    
    @with_error_handling(error_type=LogStorageError, default_return=None)
    @with_retry(RetryConfig(
        max_attempts=3,
        retry_on_exceptions=(SQLAlchemyError,)
    ))
    def store(self, log_event: Dict[str, Any]) -> ApplicationLog:
        """
        Store a single log event.
        
        Args:
            log_event: Normalized log event dict
            
        Returns:
            Stored ApplicationLog instance
        """
        # Parse timestamp
        timestamp_str = log_event.get('timestamp')
        if timestamp_str:
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = timestamp_str
        else:
            timestamp = datetime.utcnow()
        
        # Create log record
        log = ApplicationLog(
            timestamp=timestamp,
            level=log_event.get('level', 'INFO'),
            service=log_event.get('service'),
            component=log_event.get('component'),
            message=log_event.get('message', ''),
            error_type=log_event.get('error_type'),
            exception_class=log_event.get('exception_class'),
            stack_trace=log_event.get('stack_trace'),
            trace_id=log_event.get('trace_id'),
            span_id=log_event.get('span_id'),
            parent_span_id=log_event.get('parent_span_id'),
            host=log_event.get('host'),
            container_id=log_event.get('container_id'),
            pod_name=log_event.get('pod_name'),
            user_id=log_event.get('user_id'),
            request_id=log_event.get('request_id'),
            session_id=log_event.get('session_id'),
            duration_ms=log_event.get('duration_ms'),
            response_code=log_event.get('response_code'),
            raw=log_event.get('raw', {}),
            metadata=log_event.get('metadata', {}),
        )
        
        self.session.add(log)
        self.session.commit()
        
        return log
    
    @with_error_handling(error_type=LogStorageError, default_return=0)
    @with_retry(RetryConfig(
        max_attempts=3,
        retry_on_exceptions=(SQLAlchemyError,)
    ))
    def store_batch(self, log_events: List[Dict[str, Any]]) -> int:
        """
        Store multiple log events in batch (optimized).
        
        Args:
            log_events: List of normalized log event dicts
            
        Returns:
            Number of logs stored
        """
        if not log_events:
            return 0
        
        logs = []
        for log_event in log_events:
            # Parse timestamp
            timestamp_str = log_event.get('timestamp')
            if timestamp_str:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str
            else:
                timestamp = datetime.utcnow()
            
            log = ApplicationLog(
                timestamp=timestamp,
                level=log_event.get('level', 'INFO'),
                service=log_event.get('service'),
                component=log_event.get('component'),
                message=log_event.get('message', ''),
                error_type=log_event.get('error_type'),
                exception_class=log_event.get('exception_class'),
                stack_trace=log_event.get('stack_trace'),
                trace_id=log_event.get('trace_id'),
                span_id=log_event.get('span_id'),
                parent_span_id=log_event.get('parent_span_id'),
                host=log_event.get('host'),
                container_id=log_event.get('container_id'),
                pod_name=log_event.get('pod_name'),
                user_id=log_event.get('user_id'),
                request_id=log_event.get('request_id'),
                session_id=log_event.get('session_id'),
                duration_ms=log_event.get('duration_ms'),
                response_code=log_event.get('response_code'),
                raw=log_event.get('raw', {}),
                metadata=log_event.get('metadata', {}),
            )
            logs.append(log)
        
        self.session.bulk_save_objects(logs)
        self.session.commit()
        
        logger.info(f"Stored {len(logs)} application logs")
        return len(logs)
    
    def query_by_trace_id(self, trace_id: str) -> List[ApplicationLog]:
        """Query logs by trace ID."""
        return self.session.query(ApplicationLog).filter(
            ApplicationLog.trace_id == trace_id
        ).all()
    
    def query_by_service(
        self,
        service: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ApplicationLog]:
        """Query logs by service and optional time range."""
        query = self.session.query(ApplicationLog).filter(
            ApplicationLog.service == service
        )
        
        if start_time:
            query = query.filter(ApplicationLog.timestamp >= start_time)
        if end_time:
            query = query.filter(ApplicationLog.timestamp <= end_time)
        
        return query.all()
    
    def query_errors(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ApplicationLog]:
        """Query error-level logs."""
        query = self.session.query(ApplicationLog).filter(
            ApplicationLog.level.in_(['ERROR', 'FATAL'])
        )
        
        if start_time:
            query = query.filter(ApplicationLog.timestamp >= start_time)
        if end_time:
            query = query.filter(ApplicationLog.timestamp <= end_time)
        
        return query.order_by(ApplicationLog.timestamp.desc()).limit(limit).all()


__all__ = [
    'ApplicationLog',
    'LogStorage',
]
