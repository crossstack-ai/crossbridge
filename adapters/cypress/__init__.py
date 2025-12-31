"""
Cypress adapter package for CrossBridge.

Provides comprehensive support for Cypress E2E and component testing
with both JavaScript and TypeScript.

Main Classes:
    - CypressAdapter: Main adapter for test discovery and execution
    - CypressExtractor: Extract metadata from Cypress tests
    - CypressProjectDetector: Auto-detect Cypress project configuration
    - CypressTestParser: Parse Cypress test files

Example:
    from adapters.cypress import CypressAdapter
    
    adapter = CypressAdapter("/path/to/cypress/project")
    tests = adapter.discover_tests()
    results = adapter.run_tests()
"""

from .adapter import (
    CypressAdapter,
    CypressExtractor,
    CypressProjectDetector,
    CypressTestParser,
    CypressConfig,
    CypressTestType,
)

__all__ = [
    'CypressAdapter',
    'CypressExtractor',
    'CypressProjectDetector',
    'CypressTestParser',
    'CypressConfig',
    'CypressTestType',
]
