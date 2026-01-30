"""
Configuration Loader

Loads execution intelligence configuration from YAML files.
Supports crossbridge.yml for centralized configuration.

Configuration structure:
```yaml
execution:
  framework: selenium
  source_root: ./src/test/java
  
  logs:
    automation:
      - ./target/surefire-reports
      - ./logs/test.log
    
    application:
      - ./app/logs/service.log
      - ./logs/backend.log
```
"""

import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from core.execution.intelligence.log_input_models import LogSourceCollection
from core.execution.intelligence.log_sources import LogSourceType

logger = logging.getLogger(__name__)


class ExecutionConfig:
    """
    Execution intelligence configuration.
    
    Loaded from crossbridge.yml or provided programmatically.
    """
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
        """
        self.raw_config = config_dict
        
        # Extract execution section
        self.execution = config_dict.get('execution', {})
        
        # Framework settings
        self.framework = self.execution.get('framework', 'unknown')
        self.source_root = self.execution.get('source_root', '.')
        
        # Log paths
        self.logs = self.execution.get('logs', {})
        self.automation_log_paths = self.logs.get('automation', [])
        self.application_log_paths = self.logs.get('application', [])
    
    def to_log_source_collection(self) -> LogSourceCollection:
        """
        Convert configuration to LogSourceCollection.
        
        Returns:
            LogSourceCollection with configured log sources
        """
        collection = LogSourceCollection()
        
        # Add automation logs
        for path in self.automation_log_paths:
            collection.add_automation_log(
                path=path,
                framework=self.framework
            )
        
        # Add application logs
        for path in self.application_log_paths:
            # Try to infer service name from path
            service_name = Path(path).stem
            collection.add_application_log(
                path=path,
                service=service_name
            )
        
        return collection
    
    def has_automation_logs(self) -> bool:
        """Check if automation logs are configured"""
        return len(self.automation_log_paths) > 0
    
    def has_application_logs(self) -> bool:
        """Check if application logs are configured"""
        return len(self.application_log_paths) > 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'framework': self.framework,
            'source_root': self.source_root,
            'automation_log_paths': self.automation_log_paths,
            'application_log_paths': self.application_log_paths,
            'has_automation_logs': self.has_automation_logs(),
            'has_application_logs': self.has_application_logs()
        }


def load_config(config_path: str = "crossbridge.yml") -> ExecutionConfig:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file (default: crossbridge.yml)
        
    Returns:
        ExecutionConfig object
        
    Raises:
        FileNotFoundError: If configuration file not found
        yaml.YAMLError: If YAML parsing fails
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        if not config_dict:
            raise ValueError("Configuration file is empty")
        
        logger.info(f"Loaded configuration from {config_path}")
        return ExecutionConfig(config_dict)
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML configuration: {e}")


def load_config_or_default(config_path: str = "crossbridge.yml") -> Optional[ExecutionConfig]:
    """
    Load configuration if file exists, otherwise return None.
    
    This is useful for optional configuration loading.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ExecutionConfig object if file exists, None otherwise
    """
    try:
        return load_config(config_path)
    except FileNotFoundError:
        logger.info(f"Configuration file not found: {config_path} (optional)")
        return None
    except Exception as e:
        logger.warning(f"Failed to load configuration: {e}")
        return None


def create_default_config(
    framework: str,
    automation_log_paths: List[str],
    application_log_paths: Optional[List[str]] = None,
    source_root: str = "."
) -> ExecutionConfig:
    """
    Create a default configuration programmatically.
    
    Useful for creating configuration in code without YAML file.
    
    Args:
        framework: Framework name
        automation_log_paths: List of automation log paths
        application_log_paths: Optional list of application log paths
        source_root: Source root directory
        
    Returns:
        ExecutionConfig object
    """
    config_dict = {
        'execution': {
            'framework': framework,
            'source_root': source_root,
            'logs': {
                'automation': automation_log_paths,
                'application': application_log_paths or []
            }
        }
    }
    
    return ExecutionConfig(config_dict)


def merge_configs(base_config: ExecutionConfig, overrides: Dict[str, Any]) -> ExecutionConfig:
    """
    Merge configuration with overrides (e.g., from CLI).
    
    CLI arguments take precedence over configuration file.
    
    Args:
        base_config: Base configuration from file
        overrides: Override dictionary (e.g., from CLI arguments)
        
    Returns:
        New ExecutionConfig with merged settings
    """
    merged = base_config.raw_config.copy()
    
    # Merge execution section
    if 'execution' in overrides:
        execution_overrides = overrides['execution']
        
        # Update framework
        if 'framework' in execution_overrides:
            merged['execution']['framework'] = execution_overrides['framework']
        
        # Update log paths
        if 'logs' in execution_overrides:
            logs_overrides = execution_overrides['logs']
            
            if 'automation' in logs_overrides:
                merged['execution']['logs']['automation'] = logs_overrides['automation']
            
            if 'application' in logs_overrides:
                merged['execution']['logs']['application'] = logs_overrides['application']
    
    return ExecutionConfig(merged)
