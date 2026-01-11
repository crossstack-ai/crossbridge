"""
Phase 2: Page Object & Locator Awareness Module

Semantic-aware migration that preserves Page Object boundaries and locator intent.
This is NOT "AI magic rewrite" - it's intelligent preservation and modernization.

Key Principles:
- Detect Page Objects using AST parsing
- Extract locator metadata (not just strings)
- Track usage: Test → PageObject → Method → Locator
- Preserve locator identity
- Re-emit using Playwright idioms
- NO automatic locator "improvement" (that's Phase 3+)

This builds enterprise trust through transparency and correctness.
"""

from .models import Locator, PageObject, LocatorUsage, LocatorInventory, LocatorStrategy
from .detectors import PageObjectDetector, LocatorExtractor
from .generators import PlaywrightPageObjectGenerator, RobotFrameworkPageObjectGenerator
from .mappers import UsageMapper

__all__ = [
    'Locator',
    'PageObject',
    'LocatorUsage',
    'LocatorInventory',
    'LocatorStrategy',
    'PageObjectDetector',
    'LocatorExtractor',
    'PlaywrightPageObjectGenerator',
    'RobotFrameworkPageObjectGenerator',
    'UsageMapper'
]
