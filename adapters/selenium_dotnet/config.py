"""
Configuration for Selenium .NET adapter.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SeleniumDotNetConfig:
    """Configuration for Selenium .NET tests."""
    
    # Project settings
    project_file: str                    # Path to .csproj file
    test_framework: str = "nunit"        # nunit, mstest, or xunit
    
    # Test execution
    configuration: str = "Debug"         # Build configuration (Debug/Release)
    target_framework: Optional[str] = None  # Target framework (net6.0, net7.0, etc.)
    
    # Parallel execution
    parallel: bool = False
    max_parallel_threads: int = 1
    
    # Test filtering
    test_filter: Optional[str] = None    # dotnet test filter expression
    
    # Timeouts
    test_timeout: int = 300              # Test execution timeout (seconds)
    
    # Browser settings (if configured in environment)
    browser: str = "chrome"              # chrome, firefox, edge, etc.
    headless: bool = False
    
    # Reporting
    results_directory: str = "TestResults"
    logger: str = "trx"                  # trx, html, console
    
    def to_dict(self):
        """Convert config to dictionary."""
        return {
            "project_file": self.project_file,
            "test_framework": self.test_framework,
            "configuration": self.configuration,
            "target_framework": self.target_framework,
            "parallel": self.parallel,
            "max_parallel_threads": self.max_parallel_threads,
            "test_filter": self.test_filter,
            "test_timeout": self.test_timeout,
            "browser": self.browser,
            "headless": self.headless,
            "results_directory": self.results_directory,
            "logger": self.logger,
        }
