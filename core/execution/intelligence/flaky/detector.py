"""
Flaky Detector

Detects and classifies failures as flaky or deterministic.
"""

from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta

from core.execution.intelligence.flaky.models import (
    FailureHistory,
    FailureSignature,
    FailureNature,
    simplify_error_pattern
)

logger = logging.getLogger(__name__)


class FlakyDetector:
    """
    Detector for flaky vs deterministic failures.
    
    Maintains history of failures and determines their nature.
    """
    
    def __init__(self, history_window_days: int = 30):
        """
        Initialize flaky detector.
        
        Args:
            history_window_days: Days to keep in history
        """
        self.history_window_days = history_window_days
        self.failure_history: Dict[str, FailureHistory] = {}
    
    def analyze_failure(
        self,
        test_name: str,
        failure_type: str,
        error_message: str,
        signals: List = None
    ) -> tuple[FailureNature, float, FailureHistory]:
        """
        Analyze a failure and determine its nature.
        
        Args:
            test_name: Name of the test
            failure_type: Type of failure (PRODUCT_DEFECT, etc.)
            error_message: Error message
            signals: Optional list of failure signals
            
        Returns:
            Tuple of (nature, confidence, history)
        """
        # Generate signature
        signature = FailureSignature.from_failure(test_name, failure_type, error_message)
        
        # Get or create history
        if signature.signature_hash not in self.failure_history:
            history = FailureHistory(
                signature=signature.signature_hash,
                test_name=test_name,
                failure_type=failure_type
            )
            self.failure_history[signature.signature_hash] = history
        else:
            history = self.failure_history[signature.signature_hash]
        
        # Record occurrence
        history.record_occurrence()
        
        # Update nature determination
        nature = history.update_nature()
        
        logger.info(
            f"Failure analysis for {test_name}: {nature.value} "
            f"(confidence: {history.confidence:.2f}, occurrences: {history.occurrences})"
        )
        
        return nature, history.confidence, history
    
    def record_pass(self, test_name: str, last_failure_signature: Optional[str] = None):
        """
        Record that a test passed.
        
        This breaks consecutive failure streaks and indicates potential flakiness.
        
        Args:
            test_name: Name of the test
            last_failure_signature: Signature of last failure (if known)
        """
        if last_failure_signature and last_failure_signature in self.failure_history:
            history = self.failure_history[last_failure_signature]
            history.record_pass()
            logger.debug(f"Test {test_name} passed, breaking failure streak")
    
    def is_flaky(self, signature: str) -> bool:
        """
        Check if a failure signature is classified as flaky.
        
        Args:
            signature: Failure signature hash
            
        Returns:
            True if flaky
        """
        if signature not in self.failure_history:
            return False
        
        history = self.failure_history[signature]
        return history.nature == FailureNature.FLAKY
    
    def is_deterministic(self, signature: str) -> bool:
        """
        Check if a failure signature is classified as deterministic.
        
        Args:
            signature: Failure signature hash
            
        Returns:
            True if deterministic
        """
        if signature not in self.failure_history:
            return False
        
        history = self.failure_history[signature]
        return history.nature == FailureNature.DETERMINISTIC
    
    def get_history(self, signature: str) -> Optional[FailureHistory]:
        """Get history for a signature"""
        return self.failure_history.get(signature)
    
    def get_flaky_tests(self) -> List[FailureHistory]:
        """
        Get all tests classified as flaky.
        
        Returns:
            List of flaky failure histories
        """
        return [
            h for h in self.failure_history.values()
            if h.nature == FailureNature.FLAKY
        ]
    
    def get_deterministic_tests(self) -> List[FailureHistory]:
        """
        Get all tests classified as deterministic.
        
        Returns:
            List of deterministic failure histories
        """
        return [
            h for h in self.failure_history.values()
            if h.nature == FailureNature.DETERMINISTIC
        ]
    
    def cleanup_old_history(self):
        """Remove history entries older than window"""
        cutoff = datetime.utcnow() - timedelta(days=self.history_window_days)
        cutoff_iso = cutoff.isoformat()
        
        to_remove = []
        for signature, history in self.failure_history.items():
            if history.last_seen and history.last_seen < cutoff_iso:
                to_remove.append(signature)
        
        for signature in to_remove:
            del self.failure_history[signature]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old history entries")
    
    def export_history(self) -> Dict:
        """Export all history for persistence"""
        return {
            sig: history.to_dict()
            for sig, history in self.failure_history.items()
        }
    
    def import_history(self, data: Dict):
        """Import history from persistence"""
        for sig, hist_data in data.items():
            history = FailureHistory(
                signature=hist_data['signature'],
                test_name=hist_data['test_name'],
                failure_type=hist_data['failure_type'],
                occurrences=hist_data['occurrences'],
                consecutive_failures=hist_data['consecutive_failures'],
                first_seen=hist_data.get('first_seen'),
                last_seen=hist_data.get('last_seen'),
                pass_count=hist_data.get('pass_count', 0),
                different_errors_count=hist_data.get('different_errors_count', 0),
                metadata=hist_data.get('metadata', {})
            )
            history.nature = FailureNature(hist_data.get('nature', 'UNKNOWN'))
            history.confidence = hist_data.get('confidence', 0.0)
            
            self.failure_history[sig] = history


# ============================================================================
# Functional Interface
# ============================================================================

def generate_failure_signature(test_name: str, failure_type: str, error_message: str) -> str:
    """
    Generate failure signature hash.
    
    Args:
        test_name: Name of the test
        failure_type: Type of failure
        error_message: Error message
        
    Returns:
        Signature hash
    """
    signature = FailureSignature.from_failure(test_name, failure_type, error_message)
    return signature.signature_hash


def is_flaky(history: FailureHistory) -> bool:
    """
    Determine if failure history indicates flakiness.
    
    Args:
        history: FailureHistory object
        
    Returns:
        True if flaky
    """
    if history.occurrences < 3:
        return False
    
    # Flaky if passes between failures
    if history.pass_count > 0:
        return True
    
    # Environment issues often flaky
    if history.failure_type == "ENVIRONMENT_ISSUE":
        return True
    
    # Multiple different errors = flaky
    if history.different_errors_count > 0:
        return True
    
    return False


def is_deterministic(history: FailureHistory) -> bool:
    """
    Determine if failure history indicates deterministic behavior.
    
    Args:
        history: FailureHistory object
        
    Returns:
        True if deterministic
    """
    if history.occurrences < 3:
        return False
    
    # Consistently failing = deterministic
    if history.consecutive_failures >= 3:
        return True
    
    # Product/automation defects usually deterministic
    if history.failure_type in ["PRODUCT_DEFECT", "AUTOMATION_DEFECT"]:
        if history.occurrences >= 3 and history.pass_count == 0:
            return True
    
    return False
