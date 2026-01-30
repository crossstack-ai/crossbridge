"""
Health Status Integration for Log Adapters

Integrates log ingestion system with CrossBridge health monitoring framework.
Provides health checks, metrics, and status reporting.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class LogIngestionHealth:
    """Health status for log ingestion system."""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    timestamp: datetime
    
    # Ingestion metrics
    total_logs_ingested: int
    logs_per_second: float
    parse_error_rate: float
    storage_error_rate: float
    
    # Sampling metrics
    sampling_enabled: bool
    overall_sampling_rate: float
    rate_limited_count: int
    
    # Correlation metrics
    correlation_enabled: bool
    correlation_success_rate: float
    avg_correlated_logs: float
    
    # Storage metrics
    storage_latency_ms: float
    batch_success_rate: float
    
    # Circuit breaker status
    circuit_breaker_state: str  # 'CLOSED', 'OPEN', 'HALF_OPEN'
    
    # Health indicators
    warnings: list
    errors: list
    last_error: Optional[str] = None


class LogIngestionHealthMonitor:
    """
    Monitors health of log ingestion system.
    
    Tracks metrics and provides health status for observability.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self.start_time = datetime.now(UTC)
        self.total_logs = 0
        self.parse_errors = 0
        self.storage_errors = 0
        self.rate_limited = 0
        self.correlation_attempts = 0
        self.correlation_successes = 0
        self.total_correlated_logs = 0
        self.storage_latencies = []
        self.batch_attempts = 0
        self.batch_successes = 0
        self.last_error = None
        self.warnings = []
        self.errors = []
    
    def record_ingestion(self, count: int = 1):
        """Record successful log ingestion."""
        self.total_logs += count
    
    def record_parse_error(self, error: str):
        """Record log parsing error."""
        self.parse_errors += 1
        self.last_error = error
        self.errors.append(f"Parse error: {error}")
    
    def record_storage_error(self, error: str):
        """Record storage error."""
        self.storage_errors += 1
        self.last_error = error
        self.errors.append(f"Storage error: {error}")
    
    def record_rate_limited(self, count: int = 1):
        """Record rate limiting event."""
        self.rate_limited += count
    
    def record_correlation(self, success: bool, correlated_count: int = 0):
        """Record correlation attempt."""
        self.correlation_attempts += 1
        if success:
            self.correlation_successes += 1
            self.total_correlated_logs += correlated_count
    
    def record_storage_latency(self, latency_ms: float):
        """Record storage operation latency."""
        self.storage_latencies.append(latency_ms)
        # Keep only recent latencies (last 1000)
        if len(self.storage_latencies) > 1000:
            self.storage_latencies = self.storage_latencies[-1000:]
    
    def record_batch_operation(self, success: bool):
        """Record batch storage operation."""
        self.batch_attempts += 1
        if success:
            self.batch_successes += 1
    
    def add_warning(self, warning: str):
        """Add health warning."""
        self.warnings.append(warning)
        logger.warning(f"Log ingestion warning: {warning}")
    
    def get_health_status(
        self,
        sampling_enabled: bool = True,
        overall_sampling_rate: float = 0.0,
        correlation_enabled: bool = True,
        circuit_breaker_state: str = 'CLOSED'
    ) -> LogIngestionHealth:
        """
        Get current health status.
        
        Args:
            sampling_enabled: Whether sampling is enabled
            overall_sampling_rate: Current sampling rate
            correlation_enabled: Whether correlation is enabled
            circuit_breaker_state: Current circuit breaker state
        
        Returns:
            LogIngestionHealth status object
        """
        now = datetime.now(UTC)
        elapsed = (now - self.start_time).total_seconds()
        
        # Calculate rates
        logs_per_second = self.total_logs / max(elapsed, 1)
        parse_error_rate = self.parse_errors / max(self.total_logs, 1)
        storage_error_rate = self.storage_errors / max(self.total_logs, 1)
        
        # Correlation metrics
        correlation_success_rate = (
            self.correlation_successes / max(self.correlation_attempts, 1)
        )
        avg_correlated_logs = (
            self.total_correlated_logs / max(self.correlation_successes, 1)
            if self.correlation_successes > 0 else 0.0
        )
        
        # Storage metrics
        avg_latency = (
            sum(self.storage_latencies) / len(self.storage_latencies)
            if self.storage_latencies else 0.0
        )
        batch_success_rate = (
            self.batch_successes / max(self.batch_attempts, 1)
        )
        
        # Determine overall status
        status = self._determine_status(
            parse_error_rate,
            storage_error_rate,
            batch_success_rate,
            circuit_breaker_state
        )
        
        return LogIngestionHealth(
            status=status,
            timestamp=now,
            total_logs_ingested=self.total_logs,
            logs_per_second=logs_per_second,
            parse_error_rate=parse_error_rate,
            storage_error_rate=storage_error_rate,
            sampling_enabled=sampling_enabled,
            overall_sampling_rate=overall_sampling_rate,
            rate_limited_count=self.rate_limited,
            correlation_enabled=correlation_enabled,
            correlation_success_rate=correlation_success_rate,
            avg_correlated_logs=avg_correlated_logs,
            storage_latency_ms=avg_latency,
            batch_success_rate=batch_success_rate,
            circuit_breaker_state=circuit_breaker_state,
            warnings=self.warnings.copy(),
            errors=self.errors.copy(),
            last_error=self.last_error
        )
    
    def _determine_status(
        self,
        parse_error_rate: float,
        storage_error_rate: float,
        batch_success_rate: float,
        circuit_breaker_state: str
    ) -> str:
        """
        Determine overall health status.
        
        Args:
            parse_error_rate: Parsing error rate (0-1)
            storage_error_rate: Storage error rate (0-1)
            batch_success_rate: Batch operation success rate (0-1)
            circuit_breaker_state: Circuit breaker state
        
        Returns:
            Health status: 'healthy', 'degraded', or 'unhealthy'
        """
        # Unhealthy conditions
        if circuit_breaker_state == 'OPEN':
            return 'unhealthy'
        
        if storage_error_rate > 0.5:  # >50% storage failures
            return 'unhealthy'
        
        if batch_success_rate < 0.5:  # <50% batch success
            return 'unhealthy'
        
        # Degraded conditions
        if parse_error_rate > 0.2:  # >20% parse errors
            return 'degraded'
        
        if storage_error_rate > 0.1:  # >10% storage errors
            return 'degraded'
        
        if circuit_breaker_state == 'HALF_OPEN':
            return 'degraded'
        
        # Healthy
        return 'healthy'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health status to dictionary."""
        health = self.get_health_status()
        return asdict(health)
    
    def reset_metrics(self):
        """Reset all metrics (for testing or periodic resets)."""
        self.start_time = datetime.now(UTC)
        self.total_logs = 0
        self.parse_errors = 0
        self.storage_errors = 0
        self.rate_limited = 0
        self.correlation_attempts = 0
        self.correlation_successes = 0
        self.total_correlated_logs = 0
        self.storage_latencies = []
        self.batch_attempts = 0
        self.batch_successes = 0
        self.last_error = None
        self.warnings = []
        self.errors = []


# Global health monitor instance
_health_monitor = LogIngestionHealthMonitor()


def get_health_monitor() -> LogIngestionHealthMonitor:
    """Get global health monitor instance."""
    return _health_monitor
