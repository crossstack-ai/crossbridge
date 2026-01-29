"""
Base classes for alert notifications.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""
    CRITICAL = "critical"  # Breaking changes, high-risk changes
    HIGH = "high"          # Non-breaking but significant changes
    MEDIUM = "medium"      # Moderate changes
    LOW = "low"            # Minor changes, informational
    INFO = "info"          # General notifications


@dataclass
class Alert:
    """Represents an alert to be sent."""
    title: str
    message: str
    severity: AlertSeverity
    timestamp: datetime
    source: str  # e.g., "API Change Intelligence"
    details: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'details': self.details or {},
            'tags': self.tags or []
        }


class AlertNotifier(ABC):
    """
    Base class for alert notifiers.
    
    Subclasses must implement the send() method to deliver alerts
    via different channels (email, Slack, etc.)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize notifier with configuration.
        
        Args:
            config: Configuration dictionary specific to the notifier
        """
        self.config = config
        self.enabled = config.get('enabled', False)
    
    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send an alert via this notifier.
        
        Args:
            alert: Alert to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    def should_send(self, alert: Alert) -> bool:
        """
        Check if alert should be sent based on severity filters.
        
        Args:
            alert: Alert to check
        
        Returns:
            True if alert should be sent
        """
        if not self.enabled:
            return False
        
        # Check severity filter
        min_severity = self.config.get('min_severity', 'info')
        severity_order = ['info', 'low', 'medium', 'high', 'critical']
        
        try:
            alert_level = severity_order.index(alert.severity.value)
            min_level = severity_order.index(min_severity)
            return alert_level >= min_level
        except ValueError:
            return True
    
    def format_message(self, alert: Alert) -> str:
        """
        Format alert message for this notifier.
        
        Args:
            alert: Alert to format
        
        Returns:
            Formatted message string
        """
        return alert.message
