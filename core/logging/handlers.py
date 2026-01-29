"""
Custom log handlers for CrossStack-AI CrossBridge.

Provides specialized handlers for different logging needs.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler as _RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler as _TimedRotatingFileHandler


class ConsoleHandler(logging.StreamHandler):
    """
    Enhanced console handler with smart output.
    
    Features:
    - Outputs to stderr for errors, stdout for others
    - Supports color detection
    - Smart TTY detection
    """
    
    def __init__(self):
        """Initialize console handler."""
        super().__init__(stream=sys.stdout)
        self.use_colors = self._supports_color()
    
    def _supports_color(self) -> bool:
        """Check if terminal supports colors."""
        # Check if running in TTY
        if not hasattr(sys.stdout, 'isatty'):
            return False
        
        if not sys.stdout.isatty():
            return False
        
        # Windows 10+ supports ANSI colors
        if sys.platform == 'win32':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except (AttributeError, OSError) as e:
                logger.debug(f"Failed to enable ANSI colors on Windows: {e}")
                return False
        
        return True
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record, using stderr for errors."""
        # Use stderr for errors and critical
        if record.levelno >= logging.ERROR:
            self.stream = sys.stderr
        else:
            self.stream = sys.stdout
        
        super().emit(record)


class RotatingFileHandler(_RotatingFileHandler):
    """
    Enhanced rotating file handler with compression.
    
    Features:
    - Automatic rotation by size
    - Configurable backup count
    - UTF-8 encoding
    """
    
    def __init__(
        self,
        filename: str,
        maxBytes: int = 10 * 1024 * 1024,  # 10MB
        backupCount: int = 5,
        encoding: str = 'utf-8',
    ):
        """
        Initialize rotating file handler.
        
        Args:
            filename: Log file path
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
        """
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        super().__init__(
            filename=filename,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding
        )


class TimedRotatingFileHandler(_TimedRotatingFileHandler):
    """
    Enhanced timed rotating file handler.
    
    Features:
    - Automatic rotation by time
    - Daily, hourly, or custom intervals
    - Configurable backup count
    """
    
    def __init__(
        self,
        filename: str,
        when: str = 'midnight',
        interval: int = 1,
        backupCount: int = 30,
        encoding: str = 'utf-8',
    ):
        """
        Initialize timed rotating file handler.
        
        Args:
            filename: Log file path
            when: When to rotate ('midnight', 'H', 'D', 'W0'-'W6')
            interval: Rotation interval
            backupCount: Number of backup files to keep
            encoding: File encoding
        """
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        super().__init__(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding
        )


class AILogHandler(logging.Handler):
    """
    Specialized handler for AI operations.
    
    Features:
    - Separate AI log file
    - Token counting
    - Cost tracking
    - Performance metrics
    """
    
    def __init__(self, log_dir: Path):
        """
        Initialize AI log handler.
        
        Args:
            log_dir: Directory for AI logs
        """
        super().__init__()
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create AI-specific log file
        log_file = self.log_dir / 'crossstack-ai.log'
        
        self.file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=50 * 1024 * 1024,  # 50MB for AI logs
            backupCount=10
        )
        
        from .formatters import AIFormatter
        self.file_handler.setFormatter(AIFormatter())
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit AI log record."""
        # Only handle AI-related logs
        if 'AI' in record.getMessage() or hasattr(record, 'ai_operation'):
            self.file_handler.emit(record)
