"""
Log Router

Routes log parsing to appropriate adapters based on log source type.
Critical glue component that handles both automation and application logs.

GUARDRAILS:
- Must work with automation logs alone
- Must not fail if application logs missing
- Must gracefully handle parsing errors
"""

from typing import List, Dict, Optional
import logging
from pathlib import Path

from core.execution.intelligence.models import ExecutionEvent
from core.execution.intelligence.log_input_models import RawLogSource, LogSourceCollection
from core.execution.intelligence.log_sources import LogSourceType
from core.execution.intelligence.adapters import parse_logs as parse_automation_logs
from core.execution.intelligence.application_logs import parse_application_logs


logger = logging.getLogger(__name__)


class LogRouter:
    """
    Routes log parsing to appropriate adapters.
    
    Handles:
    - Automation logs (MANDATORY) → Framework-specific adapters
    - Application logs (OPTIONAL) → Application log adapter
    
    Philosophy:
    - Fail if no automation logs
    - Warn if application logs missing
    - Continue if application log parsing fails
    """
    
    def __init__(self):
        """Initialize log router"""
        self.stats = {
            'automation_logs_parsed': 0,
            'application_logs_parsed': 0,
            'parsing_errors': 0
        }
    
    def parse_logs(self, sources: List[RawLogSource]) -> List[ExecutionEvent]:
        """
        Parse all log sources into normalized ExecutionEvent objects.
        
        Args:
            sources: List of raw log sources to parse
            
        Returns:
            List of normalized ExecutionEvent objects
            
        Raises:
            ValueError: If no automation logs provided (MANDATORY)
        """
        # Separate automation and application logs
        automation_sources = [s for s in sources if s.source_type == LogSourceType.AUTOMATION]
        application_sources = [s for s in sources if s.source_type == LogSourceType.APPLICATION]
        
        # CRITICAL: Automation logs are MANDATORY
        if not automation_sources:
            raise ValueError(
                "Automation logs are required. At least one automation log source must be provided."
            )
        
        events = []
        
        # Parse automation logs (MANDATORY)
        for source in automation_sources:
            try:
                automation_events = self._parse_automation_log(source)
                events.extend(automation_events)
                self.stats['automation_logs_parsed'] += 1
                logger.info(f"Parsed {len(automation_events)} events from automation log: {source.path}")
            except Exception as e:
                logger.error(f"Failed to parse automation log {source.path}: {e}")
                self.stats['parsing_errors'] += 1
                # Re-raise for automation logs (they're mandatory)
                raise ValueError(f"Failed to parse mandatory automation log {source.path}: {e}")
        
        # Parse application logs (OPTIONAL)
        if application_sources:
            for source in application_sources:
                try:
                    app_events = self._parse_application_log(source)
                    events.extend(app_events)
                    self.stats['application_logs_parsed'] += 1
                    logger.info(f"Parsed {len(app_events)} events from application log: {source.path}")
                except Exception as e:
                    # CRITICAL: Do not fail on application log errors
                    logger.warning(f"Failed to parse optional application log {source.path}: {e}")
                    self.stats['parsing_errors'] += 1
                    # Continue processing - application logs are optional
        else:
            logger.info("No application logs provided (optional - system will work without them)")
        
        if not events:
            raise ValueError("No events extracted from any log sources")
        
        return events
    
    def parse_log_collection(self, collection: LogSourceCollection) -> List[ExecutionEvent]:
        """
        Parse a log source collection.
        
        Args:
            collection: LogSourceCollection with automation and application logs
            
        Returns:
            List of normalized ExecutionEvent objects
        """
        # Validate collection
        is_valid, error_msg = collection.validate()
        if not is_valid:
            raise ValueError(error_msg)
        
        # Parse all sources
        return self.parse_logs(collection.all_sources())
    
    def _parse_automation_log(self, source: RawLogSource) -> List[ExecutionEvent]:
        """
        Parse automation log using framework-specific adapter.
        
        Args:
            source: Raw automation log source
            
        Returns:
            List of ExecutionEvent objects
        """
        # Read log content
        log_content = self._read_log_file(source.path)
        
        # Use existing framework adapters (they auto-detect)
        events = parse_automation_logs(log_content)
        
        # Mark all events as automation logs
        for event in events:
            event.log_source_type = LogSourceType.AUTOMATION
        
        return events
    
    def _parse_application_log(self, source: RawLogSource) -> List[ExecutionEvent]:
        """
        Parse application log using application adapter.
        
        Args:
            source: Raw application log source
            
        Returns:
            List of ExecutionEvent objects
        """
        # Parse using application adapter
        events = parse_application_logs(source.path, service_name=source.service)
        
        # Mark all events as application logs (adapter should already do this)
        for event in events:
            event.log_source_type = LogSourceType.APPLICATION
            if source.service:
                event.service_name = source.service
        
        return events
    
    def _read_log_file(self, path: str) -> str:
        """Read log file content"""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Failed to read log file {path}: {e}")
    
    def get_stats(self) -> Dict:
        """Get parsing statistics"""
        return self.stats.copy()


# Convenience functions

def route_logs(sources: List[RawLogSource]) -> List[ExecutionEvent]:
    """
    Route log parsing (convenience function).
    
    Args:
        sources: List of raw log sources
        
    Returns:
        List of normalized ExecutionEvent objects
    """
    router = LogRouter()
    return router.parse_logs(sources)


def route_log_collection(collection: LogSourceCollection) -> List[ExecutionEvent]:
    """
    Route log collection parsing (convenience function).
    
    Args:
        collection: LogSourceCollection
        
    Returns:
        List of normalized ExecutionEvent objects
    """
    router = LogRouter()
    return router.parse_log_collection(collection)
