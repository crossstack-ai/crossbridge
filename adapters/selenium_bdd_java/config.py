"""
Configuration for Selenium BDD Java adapter.

Defines paths and runner types for Cucumber/Gherkin feature files.
"""

from dataclasses import dataclass


@dataclass
class SeleniumBDDJavaConfig:
    """Configuration for Selenium BDD Java test extraction."""
    
    features_dir: str = "src/test/resources/features"
    """Directory containing .feature files (default Maven/Gradle structure)."""
    
    runner_type: str = "cucumber-junit"
    """Runner type: cucumber-junit or cucumber-testng."""
    
    encoding: str = "utf-8"
    """Encoding for feature files."""
    
    ignore_patterns: list = None
    """Glob patterns to ignore (e.g., ['**/draft/**', '**/*.draft.feature'])."""
    
    def __post_init__(self):
        """Initialize default values."""
        if self.ignore_patterns is None:
            self.ignore_patterns = []
