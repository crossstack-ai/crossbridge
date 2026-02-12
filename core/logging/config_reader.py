"""
Configuration reader for logging settings.

Reads logging configuration from crossbridge.yml and environment variables.
Environment variables take precedence over config file.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .logger import LogLevel


def _find_config_file() -> Optional[Path]:
    """Find crossbridge.yml configuration file."""
    # Check environment variable first
    config_path = os.getenv("CROSSBRIDGE_CONFIG")
    if config_path:
        path = Path(config_path)
        if path.exists():
            return path
    
    # Check default locations
    default_paths = [
        Path("crossbridge.yml"),
        Path("crossbridge.yaml"),
        Path.cwd() / "crossbridge.yml",
        Path.cwd() / "crossbridge.yaml",
        Path.home() / ".crossbridge" / "crossbridge.yml",
    ]
    
    for path in default_paths:
        if path.exists():
            return path
    
    return None


def _parse_log_level(level_str: str) -> LogLevel:
    """Parse log level string to LogLevel enum."""
    level_map = {
        "TRACE": LogLevel.TRACE,
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "SUCCESS": LogLevel.SUCCESS,
        "WARNING": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR,
        "CRITICAL": LogLevel.CRITICAL,
    }
    return level_map.get(level_str.upper(), LogLevel.INFO)


def read_logging_config() -> Dict[str, Any]:
    """
    Read logging configuration from crossbridge.yml and environment variables.
    
    Environment variables take precedence over configuration file:
    - CROSSBRIDGE_LOG_LEVEL: Overall log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - CROSSBRIDGE_LOG_TO_FILE: Enable/disable file logging (true/false)
    - CROSSBRIDGE_LOG_TO_CONSOLE: Enable/disable console logging (true/false)
    - CROSSBRIDGE_LOG_DIR: Directory for log files
    
    Returns:
        Dictionary with logging configuration:
        {
            'level': LogLevel,
            'format': str,
            'log_to_file': bool,
            'log_to_console': bool,
            'log_file_path': str,
            'max_file_size_mb': int,
            'backup_count': int,
            'component_levels': dict
        }
    """
    # Default configuration
    config = {
        'level': LogLevel.INFO,
        'format': 'detailed',
        'log_to_file': True,
        'log_to_console': True,
        'log_file_path': 'logs/crossbridge.log',
        'max_file_size_mb': 10,
        'backup_count': 5,
        'component_levels': {}
    }
    
    # Read from crossbridge.yml if exists
    config_file = _find_config_file()
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                
            # Extract logging section
            if yaml_config and 'crossbridge' in yaml_config:
                logging_config = yaml_config['crossbridge'].get('logging', {})
                
                if logging_config:
                    # Update config from YAML
                    if 'level' in logging_config:
                        config['level'] = _parse_log_level(str(logging_config['level']))
                    
                    if 'format' in logging_config:
                        config['format'] = logging_config['format']
                    
                    if 'log_to_file' in logging_config:
                        config['log_to_file'] = bool(logging_config['log_to_file'])
                    
                    if 'log_to_console' in logging_config:
                        config['log_to_console'] = bool(logging_config['log_to_console'])
                    
                    if 'log_file_path' in logging_config:
                        config['log_file_path'] = logging_config['log_file_path']
                    
                    if 'max_file_size_mb' in logging_config:
                        config['max_file_size_mb'] = int(logging_config['max_file_size_mb'])
                    
                    if 'backup_count' in logging_config:
                        config['backup_count'] = int(logging_config['backup_count'])
                    
                    # Component-specific levels
                    component_levels = {}
                    for key in ['translation_level', 'ai_level', 'database_level', 'observer_level']:
                        if key in logging_config and logging_config[key]:
                            component_name = key.replace('_level', '')
                            component_levels[component_name] = _parse_log_level(str(logging_config[key]))
                    
                    config['component_levels'] = component_levels
                    
        except Exception:
            # Silently fall back to defaults if config file can't be read
            pass
    
    # Override with environment variables (highest priority)
    env_level = os.getenv('CROSSBRIDGE_LOG_LEVEL')
    if env_level:
        config['level'] = _parse_log_level(env_level)
    
    env_log_to_file = os.getenv('CROSSBRIDGE_LOG_TO_FILE')
    if env_log_to_file:
        config['log_to_file'] = env_log_to_file.lower() in ('true', '1', 'yes')
    
    env_log_to_console = os.getenv('CROSSBRIDGE_LOG_TO_CONSOLE')
    if env_log_to_console:
        config['log_to_console'] = env_log_to_console.lower() in ('true', '1', 'yes')
    
    env_log_dir = os.getenv('CROSSBRIDGE_LOG_DIR')
    if env_log_dir:
        config['log_file_path'] = str(Path(env_log_dir) / 'crossbridge.log')
    
    return config
