"""
Log Source Builder

Builds log source collections from various inputs:
- Configuration files (YAML)
- CLI arguments
- Framework defaults
- Programmatic API

PRIORITY ORDER:
1. CLI arguments (highest)
2. Configuration file
3. Framework defaults (lowest)
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from core.execution.intelligence.log_input_models import LogSourceCollection, RawLogSource
from core.execution.intelligence.log_sources import LogSourceType
from core.execution.intelligence.config_loader import ExecutionConfig
from core.execution.intelligence.framework_defaults import (
    get_default_automation_paths,
    find_existing_automation_logs,
    find_existing_application_logs
)

logger = logging.getLogger(__name__)


class LogSourceBuilder:
    """
    Builds log source collections using priority-based resolution.
    
    Priority order:
    1. Explicit paths provided (CLI/API)
    2. Configuration file paths
    3. Framework defaults
    """
    
    def __init__(
        self,
        framework: Optional[str] = None,
        config: Optional[ExecutionConfig] = None,
        search_root: str = "."
    ):
        """
        Initialize log source builder.
        
        Args:
            framework: Framework name (optional)
            config: ExecutionConfig (optional)
            search_root: Root directory for searching default paths
        """
        self.framework = framework
        self.config = config
        self.search_root = search_root
        
        # Resolve framework from config if not provided
        if not self.framework and self.config:
            self.framework = self.config.framework
    
    def build(
        self,
        automation_log_paths: Optional[List[str]] = None,
        application_log_paths: Optional[List[str]] = None
    ) -> LogSourceCollection:
        """
        Build log source collection using priority resolution.
        
        Priority:
        1. Explicit paths provided to this method
        2. Paths from configuration file
        3. Framework defaults
        
        Args:
            automation_log_paths: Explicit automation log paths (CLI/API)
            application_log_paths: Explicit application log paths (CLI/API)
            
        Returns:
            LogSourceCollection with resolved log sources
        """
        collection = LogSourceCollection()
        
        # Resolve automation log paths
        resolved_automation = self._resolve_automation_paths(automation_log_paths)
        
        for path in resolved_automation:
            collection.add_automation_log(
                path=path,
                framework=self.framework or "unknown"
            )
        
        # Resolve application log paths (optional)
        resolved_application = self._resolve_application_paths(application_log_paths)
        
        for path in resolved_application:
            # Infer service name from path
            service_name = Path(path).stem
            collection.add_application_log(
                path=path,
                service=service_name
            )
        
        return collection
    
    def _resolve_automation_paths(self, explicit_paths: Optional[List[str]]) -> List[str]:
        """
        Resolve automation log paths using priority order.
        
        Args:
            explicit_paths: Explicitly provided paths (highest priority)
            
        Returns:
            List of resolved automation log paths
        """
        # Priority 1: Explicit paths (CLI/API)
        if explicit_paths:
            logger.info(f"Using explicit automation log paths: {explicit_paths}")
            return explicit_paths
        
        # Priority 2: Configuration file
        if self.config and self.config.has_automation_logs():
            logger.info(f"Using automation log paths from configuration: {self.config.automation_log_paths}")
            return self.config.automation_log_paths
        
        # Priority 3: Framework defaults
        if self.framework:
            logger.info(f"Searching for default automation logs for framework: {self.framework}")
            existing = find_existing_automation_logs(self.framework, self.search_root)
            
            if existing:
                logger.info(f"Found existing automation logs: {existing}")
                return existing
            
            # Return default paths even if they don't exist yet
            # (they might be created by test execution)
            defaults = get_default_automation_paths(self.framework)
            if defaults:
                logger.warning(f"No existing automation logs found, using defaults: {defaults}")
                return defaults
        
        # No paths resolved - this will cause validation error later
        logger.warning("No automation log paths resolved from any source")
        return []
    
    def _resolve_application_paths(self, explicit_paths: Optional[List[str]]) -> List[str]:
        """
        Resolve application log paths using priority order.
        
        Application logs are OPTIONAL - empty result is acceptable.
        
        Args:
            explicit_paths: Explicitly provided paths (highest priority)
            
        Returns:
            List of resolved application log paths (may be empty)
        """
        # Priority 1: Explicit paths (CLI/API)
        if explicit_paths:
            logger.info(f"Using explicit application log paths: {explicit_paths}")
            return explicit_paths
        
        # Priority 2: Configuration file
        if self.config and self.config.has_application_logs():
            logger.info(f"Using application log paths from configuration: {self.config.application_log_paths}")
            return self.config.application_log_paths
        
        # Priority 3: Search for existing application logs
        logger.info("Searching for existing application logs...")
        existing = find_existing_application_logs(self.search_root)
        
        if existing:
            logger.info(f"Found existing application logs: {existing}")
            return existing
        
        # No application logs found - this is OK (they're optional)
        logger.info("No application logs found (optional - system will work without them)")
        return []


def build_log_sources(
    framework: Optional[str] = None,
    automation_log_paths: Optional[List[str]] = None,
    application_log_paths: Optional[List[str]] = None,
    config: Optional[ExecutionConfig] = None,
    search_root: str = "."
) -> LogSourceCollection:
    """
    Build log source collection (convenience function).
    
    Args:
        framework: Framework name
        automation_log_paths: Explicit automation log paths (CLI)
        application_log_paths: Explicit application log paths (CLI)
        config: Configuration object
        search_root: Root directory for searching
        
    Returns:
        LogSourceCollection
    """
    builder = LogSourceBuilder(
        framework=framework,
        config=config,
        search_root=search_root
    )
    
    return builder.build(
        automation_log_paths=automation_log_paths,
        application_log_paths=application_log_paths
    )


def build_from_config(config: ExecutionConfig) -> LogSourceCollection:
    """
    Build log source collection from configuration only.
    
    Args:
        config: ExecutionConfig object
        
    Returns:
        LogSourceCollection
    """
    return config.to_log_source_collection()
