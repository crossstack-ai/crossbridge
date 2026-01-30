"""
Flaky Detection Models

Data models for tracking and analyzing flaky vs deterministic failures.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum


class FailureNature(Enum):
    """Nature of failure - flaky or deterministic"""
    FLAKY = "FLAKY"                    # Non-actionable, intermittent
    DETERMINISTIC = "DETERMINISTIC"     # Actionable, consistent
    UNKNOWN = "UNKNOWN"                 # Not enough data


@dataclass
class FailureSignature:
    """
    Unique signature for a failure pattern.
    
    Used to track and identify recurring failures.
    """
    
    test_name: str
    failure_type: str
    error_pattern: str                 # Simplified error message pattern
    signature_hash: str                # Hash of the failure pattern
    
    @classmethod
    def from_failure(cls, test_name: str, failure_type: str, error_message: str) -> 'FailureSignature':
        """
        Generate signature from failure details.
        
        Args:
            test_name: Name of the test
            failure_type: Type of failure (PRODUCT_DEFECT, etc.)
            error_message: Error message
            
        Returns:
            FailureSignature object
        """
        import hashlib
        
        # Simplify error message to pattern (remove specifics like line numbers, timestamps)
        pattern = simplify_error_pattern(error_message)
        
        # Generate hash
        signature_str = f"{test_name}|{failure_type}|{pattern}"
        signature_hash = hashlib.md5(signature_str.encode()).hexdigest()
        
        return cls(
            test_name=test_name,
            failure_type=failure_type,
            error_pattern=pattern,
            signature_hash=signature_hash
        )


@dataclass
class FailureHistory:
    """
    Historical record of a failure pattern.
    
    Tracks occurrences and helps determine if failure is flaky or deterministic.
    """
    
    signature: str                     # Signature hash
    test_name: str
    failure_type: str
    occurrences: int = 0              # Total occurrences
    consecutive_failures: int = 0      # Consecutive failures (current streak)
    first_seen: Optional[str] = None   # ISO timestamp
    last_seen: Optional[str] = None    # ISO timestamp
    
    # Failure nature determination
    nature: FailureNature = FailureNature.UNKNOWN
    confidence: float = 0.0            # Confidence in nature classification
    
    # Additional tracking
    pass_count: int = 0                # Times test passed after this failure
    different_errors_count: int = 0    # Times test failed with different error
    
    # Metadata
    metadata: Dict = field(default_factory=dict)
    
    def record_occurrence(self, is_consecutive: bool = True):
        """
        Record a new occurrence of this failure.
        
        Args:
            is_consecutive: Whether this is consecutive to last failure
        """
        self.occurrences += 1
        self.last_seen = datetime.now(timezone.utc).isoformat()
        
        if self.first_seen is None:
            self.first_seen = self.last_seen
        
        if is_consecutive:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 1
    
    def record_pass(self):
        """Record that test passed (breaks consecutive failure streak)"""
        self.pass_count += 1
        self.consecutive_failures = 0
    
    def record_different_error(self):
        """Record that test failed with a different error"""
        self.different_errors_count += 1
        self.consecutive_failures = 0
    
    def update_nature(self) -> FailureNature:
        """
        Determine failure nature based on history.
        
        Returns:
            Updated FailureNature
        """
        # Not enough data
        if self.occurrences < 3:
            self.nature = FailureNature.UNKNOWN
            self.confidence = 0.3
            return self.nature
        
        # Flaky indicators
        flaky_score = 0
        
        # Intermittent failures (passes between failures)
        if self.pass_count > 0 and self.occurrences >= 3:
            flaky_score += 0.4
        
        # Multiple different errors
        if self.different_errors_count > 0:
            flaky_score += 0.3
        
        # Environment issues are often flaky
        if self.failure_type == "ENVIRONMENT_ISSUE":
            flaky_score += 0.3
        
        # Deterministic indicators
        deterministic_score = 0
        
        # Consistent failures
        if self.consecutive_failures >= 3:
            deterministic_score += 0.4
        
        # Product/automation defects are often deterministic
        if self.failure_type in ["PRODUCT_DEFECT", "AUTOMATION_DEFECT"]:
            deterministic_score += 0.3
        
        # High occurrence count without passes
        if self.occurrences >= 5 and self.pass_count == 0:
            deterministic_score += 0.3
        
        # Decide nature
        if flaky_score > deterministic_score:
            self.nature = FailureNature.FLAKY
            self.confidence = flaky_score
        elif deterministic_score > flaky_score:
            self.nature = FailureNature.DETERMINISTIC
            self.confidence = deterministic_score
        else:
            self.nature = FailureNature.UNKNOWN
            self.confidence = 0.5
        
        return self.nature
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'signature': self.signature,
            'test_name': self.test_name,
            'failure_type': self.failure_type,
            'occurrences': self.occurrences,
            'consecutive_failures': self.consecutive_failures,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'nature': self.nature.value,
            'confidence': self.confidence,
            'pass_count': self.pass_count,
            'different_errors_count': self.different_errors_count,
            'metadata': self.metadata
        }


def simplify_error_pattern(error_message: str) -> str:
    """
    Simplify error message to a pattern by removing specifics.
    
    Removes:
    - Line numbers
    - Timestamps
    - Memory addresses
    - File paths (keeps filename only)
    - Thread IDs
    
    Args:
        error_message: Original error message
        
    Returns:
        Simplified pattern
    """
    import re
    
    # Remove line numbers
    pattern = re.sub(r'line \d+', 'line N', error_message)
    pattern = re.sub(r':\d+', ':N', pattern)
    
    # Remove timestamps
    pattern = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', 'TIMESTAMP', pattern)
    
    # Remove memory addresses
    pattern = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', pattern)
    
    # Remove thread IDs
    pattern = re.sub(r'Thread-\d+', 'Thread-N', pattern)
    
    # Keep only last part of file paths
    pattern = re.sub(r'[\\/][\w\\/]+[\\/](\w+\.\w+)', r'\1', pattern)
    
    # Remove specific values in quotes
    pattern = re.sub(r'"[^"]*"', '"VALUE"', pattern)
    
    return pattern.strip()
