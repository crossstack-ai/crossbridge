"""
Core logging functionality for CrossStack-AI CrossBridge.

Provides intelligent logging with verbosity levels, categories, and context.
"""

import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class LogLevel(Enum):
    """
    Logging levels with extended verbosity control.
    
    TRACE: Most detailed, for debugging internal operations
    DEBUG: Detailed information for debugging
    INFO: General informational messages
    SUCCESS: Success operations (custom level)
    WARNING: Warning messages
    ERROR: Error messages
    CRITICAL: Critical errors requiring immediate attention
    """
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogCategory(Enum):
    """
    Log categories for filtering and organization.
    """
    GENERAL = "general"
    CLI = "cli"
    AI = "ai"
    ADAPTER = "adapter"
    MIGRATION = "migration"
    GOVERNANCE = "governance"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    ORCHESTRATION = "orchestration"
    TESTING = "testing"
    PERFORMANCE = "performance"
    SECURITY = "security"
    OBSERVER = "observer"  # Sidecar observer logging


# Add custom log levels to logging module
logging.addLevelName(LogLevel.TRACE.value, 'TRACE')
logging.addLevelName(LogLevel.SUCCESS.value, 'SUCCESS')


class CrossBridgeLogger:
    """
    Main logger for CrossStack-AI CrossBridge platform.
    
    Features:
    - Multiple verbosity levels
    - Category-based filtering
    - File and console output
    - AI-specific logging
    - Context management
    - Performance tracking
    """
    
    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        category: LogCategory = LogCategory.GENERAL,
        log_dir: Optional[Path] = None,
        enable_console: bool = True,
        enable_file: bool = True,
    ):
        """
        Initialize CrossBridge logger.
        
        Args:
            name: Logger name (usually module name)
            level: Minimum log level
            category: Log category
            log_dir: Directory for log files
            enable_console: Enable console output
            enable_file: Enable file output
        """
        self.name = name
        self.category = category
        self._logger = logging.getLogger(f"crossbridge.{name}")
        self._logger.setLevel(level.value)
        # Enable propagation by default so logs reach root logger's handlers
        # This allows centralized file logging while maintaining custom formatting
        self._logger.propagate = True
        
        # Context for rich logging
        self._context: Dict[str, Any] = {
            'category': category.value,
            'brand': 'CrossStack-AI CrossBridge',
        }
        
        # Setup handlers
        self._handlers: List[logging.Handler] = []
        
        if enable_console:
            self._add_console_handler()
        
        if enable_file and log_dir:
            self._add_file_handler(log_dir)
        
        # Auto-enable sidecar handler if sidecar is available
        self._try_add_sidecar_handler()
    
    def _try_add_sidecar_handler(self) -> None:
        """Add sidecar handler if sidecar is available (auto-detection)."""
        import os
        
        # Check if sidecar is configured
        sidecar_host = os.getenv('CROSSBRIDGE_API_HOST')
        sidecar_port = os.getenv('CROSSBRIDGE_API_PORT', '8765')
        
        if not sidecar_host:
            return  # No sidecar configured
        
        sidecar_url = f"http://{sidecar_host}:{sidecar_port}"
        
        try:
            from .handlers import SidecarLogHandler
            
            # Only forward INFO+ logs for AI and CLI categories to reduce noise
            handler = SidecarLogHandler(
                sidecar_url=sidecar_url,
                min_level=logging.INFO,
                categories=['ai', 'cli'],  # Only AI and CLI logs
                timeout=0.5  # Fast timeout to avoid blocking
            )
            
            if handler._enabled:  # Only add if sidecar is reachable
                self._logger.addHandler(handler)
                self._handlers.append(handler)
        except Exception:
            # Silently fail - sidecar handler is optional
            pass
    
    def _add_console_handler(self) -> None:
        """Add console handler with colored output."""
        from .formatters import ConsoleFormatter
        from .handlers import ConsoleHandler
        
        handler = ConsoleHandler()
        handler.setFormatter(ConsoleFormatter())
        self._logger.addHandler(handler)
        self._handlers.append(handler)
    
    def _add_file_handler(self, log_dir: Path) -> None:
        """Add rotating file handler."""
        from .formatters import FileFormatter
        from .handlers import RotatingFileHandler
        
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create category-specific log file
        log_file = log_dir / f"{self.category.value}.log"
        
        handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(FileFormatter())
        self._logger.addHandler(handler)
        self._handlers.append(handler)
    
    def set_level(self, level: LogLevel) -> None:
        """Set logging level."""
        self._logger.setLevel(level.value)
    
    def add_context(self, **kwargs) -> None:
        """Add context to all log messages."""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear context except brand and category."""
        self._context = {
            'category': self.category.value,
            'brand': 'CrossStack-AI CrossBridge',
        }
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context."""
        context = {**self._context, **kwargs}
        if context:
            ctx_str = " ".join(f"{k}={v}" for k, v in context.items() if k not in ['category', 'brand'])
            if ctx_str:
                return f"{message} [{ctx_str}]"
        return message
    
    def _log(self, level: int, message: str, exc_info: bool = False, **kwargs) -> None:
        """Internal logging method that attaches category to record."""
        # Create extra dict for logger
        extra = {'category': self.category}
        
        # Add any additional kwargs as record attributes
        for key, value in kwargs.items():
            if key not in ['category', 'brand']:
                extra[key] = value
        
        self._logger.log(level, self._format_message(message, **kwargs), exc_info=exc_info, extra=extra)
    
    def trace(self, message: str, **kwargs) -> None:
        """Log trace message (most detailed)."""
        self._log(LogLevel.TRACE.value, message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
    
    def success(self, message: str, **kwargs) -> None:
        """Log success message (custom level)."""
        self._log(LogLevel.SUCCESS.value, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)
    
    # AI-specific logging methods
    def ai_operation(self, operation: str, status: str, **kwargs) -> None:
        """Log AI operation."""
        self.info(f"🤖 AI Operation: {operation} - {status}", operation=operation, **kwargs)
    
    def ai_prompt(self, prompt: str, model: str = None, **kwargs) -> None:
        """Log AI prompt."""
        msg = f"🤖 AI Prompt sent"
        if model:
            msg += f" to {model}"
        self.debug(msg, prompt_length=len(prompt), **kwargs)
    
    def ai_response(self, response: str, tokens: int = None, **kwargs) -> None:
        """Log AI response."""
        msg = f"🤖 AI Response received"
        if tokens:
            msg += f" ({tokens} tokens)"
        self.debug(msg, response_length=len(response), **kwargs)
    
    def ai_error(self, error: str, operation: str = None, **kwargs) -> None:
        """Log AI error."""
        msg = f"🤖 AI Error"
        if operation:
            msg += f" during {operation}"
        self.error(msg + f": {error}", **kwargs)
    
    # Adapter-specific logging
    def adapter_operation(self, adapter: str, operation: str, **kwargs) -> None:
        """Log adapter operation."""
        self.info(f"🔌 Adapter [{adapter}]: {operation}", adapter=adapter, **kwargs)
    
    def adapter_detection(self, adapter: str, detected: bool, **kwargs) -> None:
        """Log adapter detection."""
        status = "✅ detected" if detected else "❌ not detected"
        self.debug(f"🔌 Adapter [{adapter}] {status}", adapter=adapter, **kwargs)
    
    # Test execution logging
    def test_started(self, test_name: str, **kwargs) -> None:
        """Log test start."""
        self.info(f"▶️  Test started: {test_name}", test=test_name, **kwargs)
    
    def test_passed(self, test_name: str, duration: float = None, **kwargs) -> None:
        """Log test pass."""
        msg = f"✅ Test passed: {test_name}"
        if duration:
            msg += f" ({duration:.2f}s)"
        self.success(msg, test=test_name, **kwargs)
    
    def test_failed(self, test_name: str, reason: str = None, **kwargs) -> None:
        """Log test failure."""
        msg = f"❌ Test failed: {test_name}"
        if reason:
            msg += f" - {reason}"
        self.error(msg, test=test_name, **kwargs)
    
    # Performance logging
    def performance(self, operation: str, duration: float, **kwargs) -> None:
        """Log performance metrics."""
        self.info(f"⏱️  {operation}: {duration:.3f}s", operation=operation, duration=duration, **kwargs)


# Global logger registry
_loggers: Dict[str, CrossBridgeLogger] = {}
_global_level: LogLevel = LogLevel.INFO
_log_dir: Optional[Path] = None
_console_enabled: bool = True
_file_enabled: bool = False


def configure_logging(
    level: Optional[LogLevel] = None,
    log_dir: Optional[Path] = None,
    enable_console: Optional[bool] = None,
    enable_file: Optional[bool] = None,
    use_config_file: bool = True,
) -> None:
    """
    Configure global logging settings.
    
    Reads configuration from crossbridge.yml and environment variables if use_config_file=True.
    Explicit parameters override config file settings.
    
    Environment variables (highest priority):
    - CROSSBRIDGE_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - CROSSBRIDGE_LOG_TO_FILE: Enable file logging (true/false)
    - CROSSBRIDGE_LOG_TO_CONSOLE: Enable console logging (true/false)
    - CROSSBRIDGE_LOG_DIR: Log directory path
    
    Args:
        level: Global log level (overrides config)
        log_dir: Directory for log files (overrides config)
        enable_console: Enable console output (overrides config)
        enable_file: Enable file output (overrides config)
        use_config_file: Whether to read from crossbridge.yml (default: True)
    """
    global _global_level, _log_dir, _console_enabled, _file_enabled
    
    # Read from config file if enabled
    if use_config_file:
        from .config_reader import read_logging_config
        config = read_logging_config()
        
        # Apply config values if not explicitly overridden
        if level is None:
            _global_level = config['level']
        else:
            _global_level = level
            
        if log_dir is None and config.get('log_file_path'):
            _log_dir = Path(config['log_file_path']).parent
        elif log_dir is not None:
            _log_dir = Path(log_dir)
            
        if enable_console is None:
            _console_enabled = config.get('log_to_console', True)
        else:
            _console_enabled = enable_console
            
        if enable_file is None:
            _file_enabled = config.get('log_to_file', True)
        else:
            _file_enabled = enable_file
    else:
        # Use provided values or defaults
        _global_level = level or LogLevel.INFO
        _log_dir = Path(log_dir) if log_dir else None
        _console_enabled = enable_console if enable_console is not None else True
        _file_enabled = enable_file if enable_file is not None else True
    
    # Update existing loggers
    for logger in _loggers.values():
        logger.set_level(_global_level)


def set_global_log_level(level: LogLevel) -> None:
    """Set global log level for all loggers."""
    global _global_level
    _global_level = level
    
    for logger in _loggers.values():
        logger.set_level(level)


def get_global_log_level() -> LogLevel:
    """Get current global log level."""
    return _global_level


def get_logger(
    name: str,
    category: LogCategory = LogCategory.GENERAL,
    level: Optional[LogLevel] = None,
) -> CrossBridgeLogger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        category: Log category
        level: Log level (uses global if not specified)
        
    Returns:
        CrossBridgeLogger instance
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = CrossBridgeLogger(
        name=name,
        level=level or _global_level,
        category=category,
        log_dir=_log_dir,
        enable_console=_console_enabled,
        enable_file=_file_enabled,
    )
    
    _loggers[name] = logger
    return logger
