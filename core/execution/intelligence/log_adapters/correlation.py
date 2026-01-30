"""
Log Correlation System

Correlates test execution events with application logs using:
- Trace ID correlation (best)
- Timestamp window correlation
- Service/component correlation
- Test execution ID correlation

This enables dual log analysis for improved classification confidence.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from core.execution.intelligence.models import ExecutionEvent

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Result of log correlation."""
    test_event: ExecutionEvent
    correlated_logs: List[Dict[str, Any]]
    correlation_method: str  # trace_id, timestamp, service, execution_id
    correlation_confidence: float  # 0.0-1.0
    

class LogCorrelator:
    """
    Correlates test events with application logs.
    
    Uses multiple correlation strategies with confidence scoring.
    """
    
    # Correlation confidence scores
    TRACE_ID_CONFIDENCE = 1.0      # Perfect match
    TIMESTAMP_CONFIDENCE = 0.7     # Good match within window
    SERVICE_CONFIDENCE = 0.5       # Moderate match
    EXECUTION_ID_CONFIDENCE = 0.9  # High confidence
    
    def __init__(
        self,
        timestamp_window_seconds: int = 5,
        enable_trace_id: bool = True,
        enable_timestamp: bool = True,
        enable_service: bool = True,
        enable_execution_id: bool = True
    ):
        """
        Initialize log correlator.
        
        Args:
            timestamp_window_seconds: Time window for timestamp correlation
            enable_trace_id: Enable trace ID correlation
            enable_timestamp: Enable timestamp window correlation
            enable_service: Enable service/component correlation
            enable_execution_id: Enable test execution ID correlation
        """
        self.timestamp_window = timedelta(seconds=timestamp_window_seconds)
        self.enable_trace_id = enable_trace_id
        self.enable_timestamp = enable_timestamp
        self.enable_service = enable_service
        self.enable_execution_id = enable_execution_id
    
    def correlate(
        self,
        test_event: ExecutionEvent,
        app_logs: List[Dict[str, Any]]
    ) -> CorrelationResult:
        """
        Correlate test event with application logs.
        
        Tries multiple strategies in order of confidence:
        1. Trace ID (if available)
        2. Test execution ID (if available)
        3. Timestamp window
        4. Service/component match
        
        Args:
            test_event: Test execution event
            app_logs: List of normalized application log events
            
        Returns:
            CorrelationResult with matched logs and confidence
        """
        correlated = []
        method = "none"
        confidence = 0.0
        
        # Extract trace_id from test event (check both attribute and metadata)
        trace_id = getattr(test_event, 'trace_id', None) or test_event.metadata.get('trace_id')
        execution_id = getattr(test_event, 'execution_id', None) or test_event.metadata.get('execution_id')
        
        # Strategy 1: Trace ID correlation (best)
        if self.enable_trace_id and trace_id:
            correlated = self._correlate_by_trace_id_value(trace_id, app_logs)
            if correlated:
                method = "trace_id"
                confidence = self.TRACE_ID_CONFIDENCE
                logger.debug(f"Correlated {len(correlated)} logs by trace_id")
                return CorrelationResult(test_event, correlated, method, confidence)
        
        # Strategy 2: Test execution ID correlation
        if self.enable_execution_id and execution_id:
            correlated = self._correlate_by_execution_id_value(execution_id, app_logs)
            if correlated:
                method = "execution_id"
                confidence = self.EXECUTION_ID_CONFIDENCE
                logger.debug(f"Correlated {len(correlated)} logs by execution_id")
                return CorrelationResult(test_event, correlated, method, confidence)
        
        # Strategy 3: Timestamp window correlation
        if self.enable_timestamp:
            correlated = self._correlate_by_timestamp(test_event, app_logs)
            if correlated:
                method = "timestamp"
                confidence = self.TIMESTAMP_CONFIDENCE
                logger.debug(f"Correlated {len(correlated)} logs by timestamp")
                return CorrelationResult(test_event, correlated, method, confidence)
        
        # Strategy 4: Service/component correlation
        if self.enable_service:
            correlated = self._correlate_by_service(test_event, app_logs)
            if correlated:
                method = "service"
                confidence = self.SERVICE_CONFIDENCE
                logger.debug(f"Correlated {len(correlated)} logs by service")
                return CorrelationResult(test_event, correlated, method, confidence)
        
        # No correlation found
        return CorrelationResult(test_event, [], "none", 0.0)
    
    def _correlate_by_trace_id_value(
        self,
        trace_id: str,
        app_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate by distributed trace ID value."""
        return [
            log for log in app_logs
            if log.get('trace_id') == trace_id
        ]
    
    def _correlate_by_trace_id(
        self,
        test_event: ExecutionEvent,
        app_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate by distributed trace ID."""
        trace_id = getattr(test_event, 'trace_id', None) or test_event.metadata.get('trace_id')
        if not trace_id:
            return []
        
        return [
            log for log in app_logs
            if log.get('trace_id') == trace_id
        ]
    
    def _correlate_by_execution_id_value(
        self,
        execution_id: str,
        app_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate by test execution ID value."""
        return [
            log for log in app_logs
            if log.get('metadata', {}).get('execution_id') == execution_id
        ]
    
    def _correlate_by_execution_id(
        self,
        test_event: ExecutionEvent,
        app_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate by test execution ID."""
        execution_id = getattr(test_event, 'execution_id', None) or test_event.metadata.get('execution_id')
        if not execution_id:
            return []
        
        return [
            log for log in app_logs
            if log.get('metadata', {}).get('execution_id') == execution_id
        ]
    
    def _correlate_by_timestamp(
        self,
        test_event: ExecutionEvent,
        app_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate by timestamp window."""
        if not test_event.timestamp:
            return []
        
        # Parse test event timestamp
        if isinstance(test_event.timestamp, str):
            test_time = datetime.fromisoformat(test_event.timestamp.replace('Z', '+00:00'))
        else:
            test_time = test_event.timestamp
        
        # Find logs within window
        correlated = []
        for log in app_logs:
            log_time_str = log.get('timestamp')
            if not log_time_str:
                continue
            
            try:
                log_time = datetime.fromisoformat(log_time_str.replace('Z', '+00:00'))
                time_diff = abs(log_time - test_time)
                
                if time_diff <= self.timestamp_window:
                    correlated.append(log)
            except (ValueError, AttributeError):
                continue
        
        return correlated
    
    def _correlate_by_service(
        self,
        test_event: ExecutionEvent,
        app_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate by service/component name."""
        # Extract service from test event metadata
        test_service = test_event.service_name
        if not test_service:
            return []
        
        return [
            log for log in app_logs
            if log.get('service') == test_service or
               log.get('component') == test_service
        ]
    
    def correlate_batch(
        self,
        test_events: List[ExecutionEvent],
        app_logs: List[Dict[str, Any]]
    ) -> List[CorrelationResult]:
        """
        Correlate multiple test events with application logs.
        
        Args:
            test_events: List of test execution events
            app_logs: List of application log events
            
        Returns:
            List of CorrelationResult objects
        """
        results = []
        for test_event in test_events:
            result = self.correlate(test_event, app_logs)
            results.append(result)
        return results
    
    def get_correlation_stats(
        self,
        results: List[CorrelationResult]
    ) -> Dict[str, Any]:
        """
        Get statistics about correlation results.
        
        Args:
            results: List of CorrelationResult objects
            
        Returns:
            Dictionary with correlation statistics
        """
        total = len(results)
        if total == 0:
            return {}
        
        # Count by method
        method_counts = {}
        for result in results:
            method = result.correlation_method
            method_counts[method] = method_counts.get(method, 0) + 1
        
        # Calculate averages
        avg_confidence = sum(r.correlation_confidence for r in results) / total
        avg_logs_per_event = sum(len(r.correlated_logs) for r in results) / total
        
        # Correlation rate
        correlated_count = sum(1 for r in results if r.correlated_logs)
        correlation_rate = correlated_count / total
        
        return {
            'total_events': total,
            'correlated_count': correlated_count,
            'correlation_rate': correlation_rate,
            'avg_confidence': avg_confidence,
            'avg_logs_per_event': avg_logs_per_event,
            'method_distribution': method_counts,
        }


__all__ = ['LogCorrelator', 'CorrelationResult']
