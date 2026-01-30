"""
Log Source Types

Defines the types of logs that can be analyzed:
- AUTOMATION: Test framework logs (MANDATORY)
- APPLICATION: Product/service logs (OPTIONAL)

LOCKED ENUM - Do not modify without system-wide review.
"""

from enum import Enum


class LogSourceType(str, Enum):
    """
    Types of log sources for execution intelligence.
    
    AUTOMATION logs are MANDATORY - the system must work with these alone.
    APPLICATION logs are OPTIONAL - used to boost confidence in classifications.
    """
    AUTOMATION = "automation"
    APPLICATION = "application"
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def is_mandatory(self) -> bool:
        """Check if this log source type is mandatory"""
        return self == LogSourceType.AUTOMATION
    
    @property
    def is_optional(self) -> bool:
        """Check if this log source type is optional"""
        return self == LogSourceType.APPLICATION
