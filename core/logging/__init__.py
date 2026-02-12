"""
CrossStack-AI CrossBridge Logging Framework.

Provides comprehensive, centralized logging with multiple verbosity levels,
file and console output, AI-specific logging, and intelligent log management.
"""

from .logger import (
    CrossBridgeLogger,
    LogLevel,
    LogCategory,
    get_logger,
    configure_logging,
    set_global_log_level,
    get_global_log_level,
)
from .formatters import (
    ConsoleFormatter,
    FileFormatter,
    JSONFormatter,
    AIFormatter,
)
from .handlers import (
    RotatingFileHandler,
    TimedRotatingFileHandler,
    ConsoleHandler,
    AILogHandler,
)
from .filters import (
    CategoryFilter,
    LevelFilter,
    AIOperationFilter,
)
from .config_reader import read_logging_config

__all__ = [
    # Core logger
    'CrossBridgeLogger',
    'LogLevel',
    'LogCategory',
    'get_logger',
    'configure_logging',
    'set_global_log_level',
    'get_global_log_level',
    
    # Formatters
    'ConsoleFormatter',
    'FileFormatter',
    'JSONFormatter',
    'AIFormatter',
    
    # Handlers
    'RotatingFileHandler',
    'TimedRotatingFileHandler',
    'ConsoleHandler',
    'AILogHandler',
    
    # Filters
    'CategoryFilter',
    'LevelFilter',
    'AIOperationFilter',
    
    # Config reader
    'read_logging_config',
]

# Version and branding
__version__ = '1.0.0'
__brand__ = 'CrossStack-AI CrossBridge'
