"""
Logging service for CrossBridge.

Implements dual-layer logging:
- Console: High-level steps, human-readable
- File: Full debug, stack traces, API payloads (no secrets)

Logs stored at: ~/.crossbridge/logs/run-<timestamp>.log
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(
    log_level: str = "WARNING",
    log_dir: Optional[Path] = None
) -> Path:
    """
    Setup logging for CrossBridge.
    
    Args:
        log_level: Console log level (DEBUG, INFO, WARNING, ERROR). Default: WARNING
                  Set CROSSBRIDGE_LOG_LEVEL=INFO for verbose console output
        log_dir: Optional custom log directory
    
    Returns:
        Path to log file
    """
    # Determine log directory
    if log_dir is None:
        # Check environment variable first (for Docker/CI)
        import os
        log_dir_env = os.getenv("CROSSBRIDGE_LOG_DIR")
        if log_dir_env:
            log_dir = Path(log_dir_env)
        else:
            log_dir = Path.home() / ".crossbridge" / "logs"
    
    # Ensure directory exists with proper permissions
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        # Ensure directory is writable
        log_dir.chmod(0o777)
    except (PermissionError, OSError) as e:
        # Fall back to temp directory if mount point is not writable
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / "crossbridge" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.getLogger(__name__).warning(
            f"Could not write to {log_dir_env}, using temp dir: {log_dir}"
        )
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"run-{timestamp}.log"
    
    # Root logger configuration
    root_logger = logging.getLogger()
    
    # Clear any existing handlers (e.g., from basicConfig at module load)
    root_logger.handlers.clear()
    
    root_logger.setLevel(logging.DEBUG)  # Capture everything
    
    # File handler - Full debug
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler - High-level only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(
        fmt="%(message)s"  # Clean, no timestamp for console
    )
    console_handler.setFormatter(console_formatter)
    
    # Add filter to console to suppress ERROR and above (we show those via Rich UI)
    class ConsoleFilter(logging.Filter):
        """Filter to suppress ERROR and CRITICAL from console (shown via Rich UI)."""
        def filter(self, record):
            return record.levelno < logging.ERROR
    
    console_handler.addFilter(ConsoleFilter())
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log startup
    root_logger.info(f"CrossBridge by CrossStack AI - Session started")
    root_logger.info(f"Log file: {log_file}")
    
    return log_file


def get_log_file_path() -> Optional[Path]:
    """Get current log file path from handlers."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    return None


class SensitiveDataFilter(logging.Filter):
    """
    Filter sensitive data from logs.
    
    Redacts:
    - API keys
    - Tokens
    - Passwords
    - Authorization headers
    """
    
    SENSITIVE_KEYS = [
        "token",
        "api_key",
        "password",
        "authorization",
        "secret",
        "credentials"
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log record."""
        message = record.getMessage()
        
        # Simple redaction - replace sensitive patterns
        for key in self.SENSITIVE_KEYS:
            if key in message.lower():
                # Redact value after key
                import re
                pattern = rf'({key}["\']?\s*[:=]\s*["\']?)([^"\'\s,}}]+)'
                message = re.sub(
                    pattern,
                    r'\1***REDACTED***',
                    message,
                    flags=re.IGNORECASE
                )
        
        record.msg = message
        return True


def configure_secure_logging():
    """Enable sensitive data filtering on all handlers."""
    root_logger = logging.getLogger()
    sensitive_filter = SensitiveDataFilter()
    
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)
