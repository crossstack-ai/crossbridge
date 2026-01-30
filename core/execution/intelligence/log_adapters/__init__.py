"""
Unified Log Adapter System

Extensible adapter registry for parsing different log formats:
- JSON structured logs (application/ELK/Fluentd)
- Framework-specific automation logs
- Plain text logs

All adapters normalize logs into ExecutionEvent objects.
"""

from typing import List, Optional, Type
from abc import ABC, abstractmethod

from core.execution.intelligence.models import ExecutionEvent


class BaseLogAdapter(ABC):
    """
    Base interface for all log adapters.
    
    All log formats (JSON, ELK, Fluentd, plain text) must implement this interface.
    """
    
    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """
        Check if this adapter can handle the given log source.
        
        Args:
            source: Log file path or format identifier
            
        Returns:
            True if adapter supports this source
        """
        pass
    
    @abstractmethod
    def parse(self, raw_line: str) -> Optional[dict]:
        """
        Parse a single log line into normalized schema.
        
        Args:
            raw_line: Single log line as string
            
        Returns:
            Normalized log event dict or None if parsing fails
        """
        pass
    
    @abstractmethod
    def extract_signals(self, log_event: dict) -> dict:
        """
        Extract anomaly-relevant signals from normalized log event.
        
        Args:
            log_event: Normalized log event dictionary
            
        Returns:
            Dictionary of extracted signals for anomaly detection
        """
        pass
    
    def parse_batch(self, raw_lines: List[str]) -> List[dict]:
        """
        Parse multiple log lines (default implementation).
        
        Args:
            raw_lines: List of log lines
            
        Returns:
            List of normalized log events
        """
        events = []
        for line in raw_lines:
            event = self.parse(line)
            if event:
                events.append(event)
        return events


class LogAdapterRegistry:
    """
    Registry for log adapters with automatic adapter selection.
    
    Adapters are registered and selected based on their can_handle() response.
    """
    
    def __init__(self):
        self._adapters: List[BaseLogAdapter] = []
    
    def register(self, adapter: BaseLogAdapter) -> None:
        """
        Register a new log adapter.
        
        Args:
            adapter: Adapter instance to register
        """
        self._adapters.append(adapter)
    
    def register_class(self, adapter_class: Type[BaseLogAdapter]) -> None:
        """
        Register an adapter class (instantiates automatically).
        
        Args:
            adapter_class: Adapter class to instantiate and register
        """
        adapter = adapter_class()
        self.register(adapter)
    
    def get_adapter(self, source: str) -> Optional[BaseLogAdapter]:
        """
        Get appropriate adapter for the given source.
        
        Args:
            source: Log file path or format identifier
            
        Returns:
            Adapter that can handle the source, or None
        """
        for adapter in self._adapters:
            if adapter.can_handle(source):
                return adapter
        return None
    
    def list_adapters(self) -> List[str]:
        """
        List all registered adapter names.
        
        Returns:
            List of adapter class names
        """
        return [adapter.__class__.__name__ for adapter in self._adapters]


# Global adapter registry instance
_registry = LogAdapterRegistry()


def get_registry() -> LogAdapterRegistry:
    """Get the global adapter registry."""
    return _registry


def register_adapter(adapter: BaseLogAdapter) -> None:
    """Register an adapter with the global registry."""
    _registry.register(adapter)


def get_adapter_for(source: str) -> Optional[BaseLogAdapter]:
    """Get adapter for the given source from global registry."""
    return _registry.get_adapter(source)


__all__ = [
    'BaseLogAdapter',
    'LogAdapterRegistry',
    'get_registry',
    'register_adapter',
    'get_adapter_for',
]
