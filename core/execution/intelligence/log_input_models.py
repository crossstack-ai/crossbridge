"""
Log Input Models

Models for representing raw log sources before parsing.
All logs (automation or application) use these unified models.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path

from core.execution.intelligence.log_sources import LogSourceType


@dataclass
class RawLogSource:
    """
    Represents a raw log source before parsing.
    
    This is the unified input model for all log types.
    Both automation and application logs use this structure.
    
    Attributes:
        source_type: Type of log source (automation or application)
        path: Path to the log file or directory
        framework: Framework name (for automation logs)
        service: Service name (for application logs)
        metadata: Additional metadata about the log source
    """
    source_type: LogSourceType
    path: str
    framework: Optional[str] = None
    service: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate the log source"""
        if not self.path:
            raise ValueError("Log source path cannot be empty")
        
        # Validate framework for automation logs
        if self.source_type == LogSourceType.AUTOMATION and not self.framework:
            # Framework can be auto-detected, so this is just a warning
            pass
        
        # Validate service for application logs
        if self.source_type == LogSourceType.APPLICATION and not self.service:
            # Service is optional, can be inferred from path
            self.service = Path(self.path).stem
    
    def exists(self) -> bool:
        """Check if the log source path exists"""
        return Path(self.path).exists()
    
    def is_directory(self) -> bool:
        """Check if the log source is a directory"""
        return Path(self.path).is_dir()
    
    def is_file(self) -> bool:
        """Check if the log source is a file"""
        return Path(self.path).is_file()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'source_type': self.source_type.value,
            'path': self.path,
            'framework': self.framework,
            'service': self.service,
            'metadata': self.metadata
        }


@dataclass
class LogSourceCollection:
    """
    Collection of log sources for analysis.
    
    Manages both automation and application logs together.
    """
    automation_logs: List[RawLogSource] = field(default_factory=list)
    application_logs: List[RawLogSource] = field(default_factory=list)
    
    def add_automation_log(self, path: str, framework: Optional[str] = None, **metadata):
        """Add an automation log source"""
        source = RawLogSource(
            source_type=LogSourceType.AUTOMATION,
            path=path,
            framework=framework,
            metadata=metadata
        )
        self.automation_logs.append(source)
        return source
    
    def add_application_log(self, path: str, service: Optional[str] = None, **metadata):
        """Add an application log source"""
        source = RawLogSource(
            source_type=LogSourceType.APPLICATION,
            path=path,
            service=service,
            metadata=metadata
        )
        self.application_logs.append(source)
        return source
    
    def all_sources(self) -> List[RawLogSource]:
        """Get all log sources (automation + application)"""
        return self.automation_logs + self.application_logs
    
    def has_automation_logs(self) -> bool:
        """Check if automation logs are present"""
        return len(self.automation_logs) > 0
    
    def has_application_logs(self) -> bool:
        """Check if application logs are present"""
        return len(self.application_logs) > 0
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate the log source collection.
        
        Returns:
            (is_valid, error_message)
        """
        # CRITICAL: Automation logs are MANDATORY
        if not self.has_automation_logs():
            return False, "Automation logs are required - at least one automation log source must be provided"
        
        # Check if any automation logs exist
        existing_automation = [src for src in self.automation_logs if src.exists()]
        if not existing_automation:
            return False, f"No automation log files found at specified paths: {[src.path for src in self.automation_logs]}"
        
        # Application logs are optional - no validation required
        return True, ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'automation_logs': [src.to_dict() for src in self.automation_logs],
            'application_logs': [src.to_dict() for src in self.application_logs],
            'has_automation_logs': self.has_automation_logs(),
            'has_application_logs': self.has_application_logs()
        }
