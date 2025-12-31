"""
Log formatters for CrossStack-AI CrossBridge.

Provides various formatting options for console, file, JSON, and AI-specific logs.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any


class ConsoleFormatter(logging.Formatter):
    """
    Colored console formatter with emojis and clean output.
    
    Features:
    - Color-coded by level
    - Emoji indicators
    - Timestamp
    - Clean, readable format
    """
    
    # ANSI color codes
    COLORS = {
        'TRACE': '\033[90m',      # Gray
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[37m',       # White
        'SUCCESS': '\033[32m',    # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }
    
    EMOJIS = {
        'TRACE': '🔍',
        'DEBUG': '🐛',
        'INFO': 'ℹ️ ',
        'SUCCESS': '✅',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }
    
    def __init__(self, use_colors: bool = True, use_emojis: bool = True):
        """
        Initialize console formatter.
        
        Args:
            use_colors: Enable ANSI colors
            use_emojis: Enable emoji indicators
        """
        super().__init__()
        self.use_colors = use_colors
        self.use_emojis = use_emojis
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        # Get level name
        levelname = record.levelname
        
        # Add emoji
        if self.use_emojis:
            emoji = self.EMOJIS.get(levelname, 'ℹ️ ')
        else:
            emoji = ''
        
        # Add color
        if self.use_colors:
            color = self.COLORS.get(levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
        else:
            color = ''
            reset = ''
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Build message
        parts = []
        
        # Timestamp and level
        parts.append(f"{color}[{timestamp}] {emoji} {levelname:8s}{reset}")
        
        # Module name (abbreviated)
        module = record.name.replace('crossbridge.', '')
        if len(module) > 30:
            module = module[:27] + '...'
        parts.append(f"[{module}]")
        
        # Message
        parts.append(record.getMessage())
        
        # Exception info
        if record.exc_info:
            parts.append('\n' + self.formatException(record.exc_info))
        
        return ' '.join(parts)


class FileFormatter(logging.Formatter):
    """
    Detailed file formatter for persistent logs.
    
    Features:
    - Detailed timestamp
    - Process/thread info
    - Full module path
    - Clean, parseable format
    """
    
    def __init__(self):
        """Initialize file formatter."""
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(process)d:%(thread)d | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Features:
    - Machine-readable JSON
    - All metadata included
    - Easy parsing and analysis
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'brand': 'CrossStack-AI CrossBridge',
        }
        
        # Add exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add custom attributes
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data)


class AIFormatter(logging.Formatter):
    """
    Specialized formatter for AI operations.
    
    Features:
    - AI operation tracking
    - Token counting
    - Model information
    - Prompt/response metadata
    """
    
    def __init__(self):
        """Initialize AI formatter."""
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format AI-specific log record."""
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Base message
        parts = [
            f"[{timestamp}]",
            f"🤖 CrossStack-AI",
            f"[{record.levelname}]",
            record.getMessage()
        ]
        
        # Add AI-specific metadata
        if hasattr(record, 'model'):
            parts.append(f"(model: {record.model})")
        
        if hasattr(record, 'tokens'):
            parts.append(f"({record.tokens} tokens)")
        
        if hasattr(record, 'duration'):
            parts.append(f"({record.duration:.2f}s)")
        
        message = ' '.join(parts)
        
        # Add exception if present
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        
        return message
