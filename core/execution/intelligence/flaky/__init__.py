"""
Flaky Test Detection System

Separates flaky (non-actionable) from deterministic (actionable) failures.
"""

from .models import FailureHistory, FailureSignature, FailureNature
from .detector import FlakyDetector, generate_failure_signature, is_flaky, is_deterministic

__all__ = [
    'FailureHistory',
    'FailureSignature',
    'FailureNature',
    'FlakyDetector',
    'generate_failure_signature',
    'is_flaky',
    'is_deterministic'
]
