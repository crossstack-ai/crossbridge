"""
Framework Log Parser

Parses Java framework logs (log4j, slf4j, logback) for error/warning analysis.
Extracts ERROR and WARN level messages for root cause correlation.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.TESTING)


class FrameworkLogEntry:
    """Represents a single framework log entry"""
    
    def __init__(
        self,
        timestamp: str,
        level: str,
        logger_name: str,
        message: str,
        exception: Optional[str] = None,
        line_number: int = 0
    ):
        self.timestamp = timestamp
        self.level = level
        self.logger_name = logger_name
        self.message = message
        self.exception = exception
        self.line_number = line_number
    
    def __repr__(self):
        return f"<FrameworkLogEntry {self.level} at {self.timestamp}: {self.message[:50]}>"


class FrameworkLogParser:
    """
    Parser for Java framework logs (log4j/slf4j/logback).
    
    Extracts ERROR and WARN entries with timestamps for correlation.
    Handles common log patterns and multi-line stack traces.
    """
    
    # Common log4j/slf4j patterns
    LOG_PATTERNS = [
        # 2024-01-15 10:30:45,123 ERROR [com.example.Test] - Message
        re.compile(
            r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+'
            r'(ERROR|WARN|INFO|DEBUG)\s+'
            r'\[?([^\]]+)\]?\s*[-:]\s*(.+)$'
        ),
        # [ERROR] 2024-01-15 10:30:45 com.example.Test - Message
        re.compile(
            r'^\[(ERROR|WARN|INFO|DEBUG)\]\s+'
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]?\d*)\s+'
            r'([^\s]+)\s*[-:]\s*(.+)$'
        ),
        # ERROR [main] 2024-01-15 10:30:45 com.example.Test - Message
        re.compile(
            r'^(ERROR|WARN|INFO|DEBUG)\s+\[[^\]]+\]\s+'
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]?\d*)\s+'
            r'([^\s]+)\s*[-:]\s*(.+)$'
        ),
    ]
    
    # Infrastructure error patterns
    INFRA_PATTERNS = [
        re.compile(r'connection\s+(reset|refused|timeout|failed)', re.IGNORECASE),
        re.compile(r'session\s+not\s+created', re.IGNORECASE),
        re.compile(r'(timeout|timed\s+out)', re.IGNORECASE),
        re.compile(r'unable\s+to\s+connect', re.IGNORECASE),
        re.compile(r'network\s+is\s+unreachable', re.IGNORECASE),
        re.compile(r'no\s+such\s+session', re.IGNORECASE),
        re.compile(r'webdriver\s+exception', re.IGNORECASE),
    ]
    
    def __init__(self):
        """Initialize framework log parser"""
        self.entries: List[FrameworkLogEntry] = []
        self.error_entries: List[FrameworkLogEntry] = []
        self.warn_entries: List[FrameworkLogEntry] = []
    
    def parse(self, log_path: Path) -> List[FrameworkLogEntry]:
        """
        Parse framework log file.
        
        Args:
            log_path: Path to framework log file
            
        Returns:
            List of FrameworkLogEntry objects
        """
        logger.info(f"Parsing framework log: {log_path}")
        
        if not log_path.exists():
            logger.error(f"Framework log file not found: {log_path}")
            return []
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            self.entries = []
            self.error_entries = []
            self.warn_entries = []
            
            current_entry: Optional[FrameworkLogEntry] = None
            current_exception_lines = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.rstrip('\n')
                
                # Try to parse as new log entry
                parsed = self._parse_line(line, line_num)
                
                if parsed:
                    # Save previous entry if exists
                    if current_entry:
                        if current_exception_lines:
                            current_entry.exception = '\n'.join(current_exception_lines)
                        self._add_entry(current_entry)
                    
                    # Start new entry
                    current_entry = parsed
                    current_exception_lines = []
                else:
                    # Continuation of previous entry (stack trace)
                    if current_entry and line.strip():
                        # Looks like stack trace or continuation
                        if line.startswith('\t') or line.startswith('    ') or \
                           line.strip().startswith('at ') or \
                           line.strip().startswith('Caused by:'):
                            current_exception_lines.append(line)
            
            # Save last entry
            if current_entry:
                if current_exception_lines:
                    current_entry.exception = '\n'.join(current_exception_lines)
                self._add_entry(current_entry)
            
            logger.info(
                f"Parsed {len(self.entries)} log entries: "
                f"{len(self.error_entries)} errors, "
                f"{len(self.warn_entries)} warnings"
            )
            
            return self.entries
            
        except Exception as e:
            logger.error(f"Failed to parse framework log: {e}")
            return []
    
    def _parse_line(self, line: str, line_num: int) -> Optional[FrameworkLogEntry]:
        """
        Parse a single log line.
        
        Args:
            line: Log line
            line_num: Line number in file
            
        Returns:
            FrameworkLogEntry or None if not a log entry
        """
        for pattern in self.LOG_PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                
                # Different patterns have different group orders
                if pattern == self.LOG_PATTERNS[0]:
                    # Pattern 1: timestamp, level, logger, message
                    timestamp, level, logger_name, message = groups
                elif pattern == self.LOG_PATTERNS[1]:
                    # Pattern 2: level, timestamp, logger, message
                    level, timestamp, logger_name, message = groups
                else:
                    # Pattern 3: level, timestamp, logger, message
                    level, timestamp, logger_name, message = groups
                
                return FrameworkLogEntry(
                    timestamp=timestamp,
                    level=level,
                    logger_name=logger_name,
                    message=message,
                    line_number=line_num
                )
        
        return None
    
    def _add_entry(self, entry: FrameworkLogEntry):
        """Add entry to appropriate lists"""
        self.entries.append(entry)
        
        if entry.level == 'ERROR':
            self.error_entries.append(entry)
        elif entry.level == 'WARN':
            self.warn_entries.append(entry)
    
    def get_errors(self) -> List[FrameworkLogEntry]:
        """Get all ERROR level entries"""
        return self.error_entries
    
    def get_warnings(self) -> List[FrameworkLogEntry]:
        """Get all WARN level entries"""
        return self.warn_entries
    
    def get_infra_errors(self) -> List[FrameworkLogEntry]:
        """
        Get infrastructure-related errors.
        
        Returns:
            List of entries matching infrastructure patterns
        """
        infra_errors = []
        
        for entry in self.error_entries:
            combined_text = f"{entry.message} {entry.exception or ''}"
            
            if any(pattern.search(combined_text) for pattern in self.INFRA_PATTERNS):
                infra_errors.append(entry)
        
        return infra_errors
    
    def get_entries_in_timeframe(
        self,
        start_time: str,
        end_time: str
    ) -> List[FrameworkLogEntry]:
        """
        Get entries within a time window.
        
        Args:
            start_time: Start timestamp (ISO format or log format)
            end_time: End timestamp
            
        Returns:
            List of entries in timeframe
        """
        # Simple string comparison works for ISO timestamps
        return [
            e for e in self.entries
            if start_time <= e.timestamp <= end_time
        ]
    
    def get_summary(self) -> Dict:
        """
        Get log summary.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_entries': len(self.entries),
            'error_count': len(self.error_entries),
            'warning_count': len(self.warn_entries),
            'infra_error_count': len(self.get_infra_errors()),
        }
