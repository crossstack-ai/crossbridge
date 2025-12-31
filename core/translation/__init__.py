"""
Framework-to-Framework Translation Core.

This module provides semantic test translation between frameworks
using a Neutral Intent Model (NIM) approach.
"""

from core.translation.intent_model import (
    ActionIntent,
    AssertionIntent,
    TestIntent,
    IntentType,
    ActionType,
    AssertionType,
)
from core.translation.pipeline import TranslationPipeline, TranslationResult
from core.translation.registry import IdiomRegistry, ApiMappingRegistry

__all__ = [
    "ActionIntent",
    "AssertionIntent",
    "TestIntent",
    "IntentType",
    "ActionType",
    "AssertionType",
    "TranslationPipeline",
    "TranslationResult",
    "IdiomRegistry",
    "ApiMappingRegistry",
]
