"""
Log filters for CrossStack-AI CrossBridge.

Provides filtering capabilities for selective logging.
"""

import logging
from typing import Set, Optional
from .logger import LogLevel, LogCategory


class CategoryFilter(logging.Filter):
    """
    Filter logs by category.
    
    Allows only logs from specified categories.
    """
    
    def __init__(self, categories: Set[LogCategory]):
        """
        Initialize category filter.
        
        Args:
            categories: Set of allowed categories
        """
        super().__init__()
        self.categories = {cat.value for cat in categories}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter by category."""
        category = getattr(record, 'category', 'general')
        return category in self.categories


class LevelFilter(logging.Filter):
    """
    Filter logs by level range.
    
    Allows logs within specified level range.
    """
    
    def __init__(
        self,
        min_level: Optional[LogLevel] = None,
        max_level: Optional[LogLevel] = None
    ):
        """
        Initialize level filter.
        
        Args:
            min_level: Minimum log level (inclusive)
            max_level: Maximum log level (inclusive)
        """
        super().__init__()
        self.min_level = min_level.value if min_level else 0
        self.max_level = max_level.value if max_level else 100
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter by level range."""
        return self.min_level <= record.levelno <= self.max_level


class AIOperationFilter(logging.Filter):
    """
    Filter for AI-specific operations.
    
    Allows only AI-related log messages.
    """
    
    def __init__(self):
        """Initialize AI operation filter."""
        super().__init__()
        self.ai_keywords = {'AI', 'ai', '🤖', 'prompt', 'model', 'token', 'crossstack'}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter AI operations."""
        message = record.getMessage().lower()
        return any(keyword.lower() in message for keyword in self.ai_keywords)


class PerformanceFilter(logging.Filter):
    """
    Filter for performance-related logs.
    
    Allows only logs with performance metrics.
    """
    
    def __init__(self, min_duration: float = 0.0):
        """
        Initialize performance filter.
        
        Args:
            min_duration: Minimum duration to log (seconds)
        """
        super().__init__()
        self.min_duration = min_duration
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter by performance threshold."""
        duration = getattr(record, 'duration', None)
        if duration is None:
            return False
        return duration >= self.min_duration


class NoiseReductionFilter(logging.Filter):
    """
    Filter to reduce log noise.
    
    Blocks repetitive or unimportant messages.
    """
    
    def __init__(self, max_repeats: int = 3):
        """
        Initialize noise reduction filter.
        
        Args:
            max_repeats: Maximum times to allow same message
        """
        super().__init__()
        self.max_repeats = max_repeats
        self.message_counts: dict = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter repetitive messages."""
        message = record.getMessage()
        
        # Allow errors and critical always
        if record.levelno >= logging.ERROR:
            return True
        
        # Track message count
        count = self.message_counts.get(message, 0)
        self.message_counts[message] = count + 1
        
        # Allow up to max_repeats
        if count < self.max_repeats:
            return True
        
        # Show reminder every 100 occurrences
        if count % 100 == 0:
            record.msg = f"{message} (repeated {count} times, suppressing further occurrences)"
            return True
        
        return False
