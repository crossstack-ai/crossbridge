"""
Application Log Adapter

Parses application/product logs (OPTIONAL).
This adapter enriches failure analysis but is NOT required.

The system MUST work without application logs.
"""

from typing import List, Optional
import re
from pathlib import Path

from core.execution.intelligence.models import ExecutionEvent, LogLevel
from core.execution.intelligence.log_sources import LogSourceType


class ApplicationLogAdapter:
    """
    Adapter for parsing application/service logs.
    
    CRITICAL: This adapter is OPTIONAL.
    - System must not fail if no application logs provided
    - Used to boost confidence in product defect classifications
    - Provides additional context for failures
    
    Supports common log formats:
    - Standard Java logs (log4j, slf4j)
    - .NET logs
    - Python logs
    - JSON structured logs
    - Generic text logs
    """
    
    # Common error patterns in application logs
    ERROR_PATTERNS = [
        r'ERROR',
        r'FATAL',
        r'Exception',
        r'Error:',
        r'Failed to',
        r'Cannot',
        r'Unable to',
        r'Stack trace:',
    ]
    
    # Timestamp patterns
    TIMESTAMP_PATTERNS = [
        r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',  # ISO format
        r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',      # US format
        r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}',      # EU format
    ]
    
    def __init__(self, service_name: Optional[str] = None):
        """
        Initialize application log adapter.
        
        Args:
            service_name: Name of the service/application (optional)
        """
        self.service_name = service_name or "application"
    
    def can_handle(self, log_path: str) -> bool:
        """
        Check if this adapter can handle the log file.
        
        Application logs are typically in these locations:
        - */logs/*.log
        - */app/logs/*.log
        - */service/logs/*.log
        """
        path = Path(log_path)
        
        # Check file extension
        if path.suffix not in ['.log', '.txt', '.out']:
            return False
        
        # Check if it's in a logs directory
        return 'logs' in str(path).lower() or 'app' in str(path).lower()
    
    def parse(self, log_path: str) -> List[ExecutionEvent]:
        """
        Parse application logs into normalized ExecutionEvent objects.
        
        Args:
            log_path: Path to the application log file
            
        Returns:
            List of ExecutionEvent objects
        """
        events = []
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            # CRITICAL: Do not fail if log file cannot be read
            # Application logs are optional
            return events
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # Check if line contains error
            is_error = any(re.search(pattern, line, re.IGNORECASE) for pattern in self.ERROR_PATTERNS)
            
            if is_error:
                # Extract timestamp
                timestamp = self._extract_timestamp(line)
                
                # Determine log level
                level = self._parse_log_level(line)
                
                # Extract exception type if present
                exception_type = self._extract_exception_type(line)
                
                # Check if this is start of a stack trace
                stacktrace = None
                if 'Stack trace:' in line or 'Traceback' in line or exception_type:
                    stacktrace = self._extract_stacktrace(lines, i)
                
                event = ExecutionEvent(
                    timestamp=timestamp,
                    level=level,
                    source=self.service_name,
                    message=line.strip(),
                    log_source_type=LogSourceType.APPLICATION,  # MARK AS APPLICATION LOG
                    exception_type=exception_type,
                    stacktrace=stacktrace,
                    service_name=self.service_name,
                    metadata={
                        'line_number': i + 1,
                        'log_file': log_path
                    }
                )
                events.append(event)
        
        return events
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line"""
        for pattern in self.TIMESTAMP_PATTERNS:
            match = re.search(pattern, line)
            if match:
                return match.group(0)
        return None
    
    def _parse_log_level(self, line: str) -> LogLevel:
        """Parse log level from line"""
        line_upper = line.upper()
        
        if 'FATAL' in line_upper:
            return LogLevel.FATAL
        elif 'ERROR' in line_upper:
            return LogLevel.ERROR
        elif 'WARN' in line_upper:
            return LogLevel.WARN
        elif 'INFO' in line_upper:
            return LogLevel.INFO
        elif 'DEBUG' in line_upper:
            return LogLevel.DEBUG
        else:
            return LogLevel.ERROR  # Default to ERROR for application logs
    
    def _extract_exception_type(self, line: str) -> Optional[str]:
        """Extract exception type from line"""
        # Java exceptions
        java_match = re.search(r'(\w+Exception|\w+Error):', line)
        if java_match:
            return java_match.group(1)
        
        # Python exceptions
        python_match = re.search(r'(\w+Error):', line)
        if python_match:
            return python_match.group(1)
        
        # .NET exceptions
        dotnet_match = re.search(r'System\.(\w+Exception)', line)
        if dotnet_match:
            return dotnet_match.group(1)
        
        return None
    
    def _extract_stacktrace(self, lines: List[str], start_idx: int, max_lines: int = 50) -> str:
        """Extract stack trace starting from the given line"""
        stacktrace_lines = []
        
        for i in range(start_idx, min(start_idx + max_lines, len(lines))):
            line = lines[i].strip()
            
            # Stop at empty line or new log entry
            if not line or self._is_new_log_entry(line):
                break
            
            stacktrace_lines.append(line)
        
        return '\n'.join(stacktrace_lines) if stacktrace_lines else None
    
    def _is_new_log_entry(self, line: str) -> bool:
        """Check if line starts a new log entry"""
        # Check for timestamp at start
        for pattern in self.TIMESTAMP_PATTERNS:
            if re.match(pattern, line):
                return True
        return False


def parse_application_logs(log_path: str, service_name: Optional[str] = None) -> List[ExecutionEvent]:
    """
    Parse application logs into ExecutionEvent objects.
    
    CRITICAL: This is an OPTIONAL operation.
    System must not fail if this returns empty or encounters errors.
    
    Args:
        log_path: Path to application log file
        service_name: Optional service name
        
    Returns:
        List of ExecutionEvent objects (may be empty)
    """
    adapter = ApplicationLogAdapter(service_name=service_name)
    
    try:
        return adapter.parse(log_path)
    except Exception:
        # CRITICAL: Gracefully handle all errors
        # Application logs are optional
        return []
