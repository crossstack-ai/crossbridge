"""
Robot Framework adapter for CrossBridge.

This adapter supports Robot Framework tests with enhanced features.
"""

from .robot_adapter import RobotAdapter, RobotExtractor, RobotDetector
from .config import RobotConfig
from .keyword_library_analyzer import KeywordLibraryAnalyzer

__all__ = [
    'RobotAdapter',
    'RobotExtractor',
    'RobotDetector',
    'RobotConfig',
    'KeywordLibraryAnalyzer',
]
