"""
Playwright adapter package for CrossBridge.

Provides unified support for Playwright tests across all language bindings:
- JavaScript/TypeScript (@playwright/test)
- Python (pytest-playwright)
- Java (playwright-java with JUnit/TestNG)
- .NET (Microsoft.Playwright with NUnit/MSTest/xUnit)

Usage:
    # Auto-detect and use
    from adapters.playwright import PlaywrightAdapter
    
    adapter = PlaywrightAdapter("/path/to/playwright/project")
    tests = adapter.discover_tests()
    results = adapter.run_tests()
    
    # Get configuration info
    config_info = adapter.get_config_info()
    print(f"Detected: {config_info['language']} with {config_info['framework']}")
"""

from .adapter import (
    PlaywrightAdapter,
    PlaywrightExtractor,
    PlaywrightProjectDetector,
    PlaywrightProjectConfig,
    PlaywrightLanguage,
    PlaywrightTestFramework,
)

__all__ = [
    "PlaywrightAdapter",
    "PlaywrightExtractor",
    "PlaywrightProjectDetector",
    "PlaywrightProjectConfig",
    "PlaywrightLanguage",
    "PlaywrightTestFramework",
]
