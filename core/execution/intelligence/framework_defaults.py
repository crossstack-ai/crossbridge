"""
Framework Default Log Paths

Provides default log paths for each framework when not specified in config.
These are fallback values only - configuration and CLI take precedence.

PRIORITY ORDER:
1. CLI arguments (highest priority)
2. crossbridge.yml configuration
3. Framework defaults (lowest priority - fallback only)
"""

from typing import Dict, List
from pathlib import Path


# Default log paths by framework (automation logs)
DEFAULT_AUTOMATION_LOG_PATHS: Dict[str, List[str]] = {
    # Java frameworks
    "selenium": [
        "target/surefire-reports",
        "build/test-results",
    ],
    "selenium-java": [
        "target/surefire-reports",
        "build/test-results",
    ],
    "restassured": [
        "target/surefire-reports",
        "build/test-results",
    ],
    "testng": [
        "target/surefire-reports",
        "test-output",
    ],
    
    # Python frameworks
    "pytest": [
        "junit.xml",
        "test-results/junit.xml",
        "reports/junit.xml",
    ],
    "selenium-pytest": [
        "junit.xml",
        "test-results/junit.xml",
    ],
    "behave": [
        "reports/behave.json",
        "behave.json",
    ],
    
    # Robot Framework
    "robot": [
        "output.xml",
        "reports/output.xml",
    ],
    
    # JavaScript frameworks
    "playwright": [
        "test-results",
        "playwright-report",
    ],
    "cypress": [
        "cypress/results",
        "mochawesome-report",
    ],
    
    # BDD frameworks
    "cucumber": [
        "target/cucumber-reports",
        "reports/cucumber.json",
    ],
    "specflow": [
        "TestResults",
        "BDD/TestResults",
    ],
}


# Common application log paths (optional - for guidance)
DEFAULT_APPLICATION_LOG_PATHS: List[str] = [
    "logs/application.log",
    "app/logs/app.log",
    "service/logs/service.log",
    "logs/*.log",
]


def get_default_automation_paths(framework: str) -> List[str]:
    """
    Get default automation log paths for a framework.
    
    Args:
        framework: Framework name (lowercase)
        
    Returns:
        List of default paths (may be empty)
    """
    framework_normalized = framework.lower().replace("_", "-")
    return DEFAULT_AUTOMATION_LOG_PATHS.get(framework_normalized, [])


def get_default_application_paths() -> List[str]:
    """
    Get default application log paths (guidance only).
    
    Returns:
        List of common application log paths
    """
    return DEFAULT_APPLICATION_LOG_PATHS.copy()


def find_existing_automation_logs(framework: str, search_root: str = ".") -> List[str]:
    """
    Find existing automation log files for a framework.
    
    Searches for default log paths that actually exist on disk.
    
    Args:
        framework: Framework name
        search_root: Root directory to search from (default: current directory)
        
    Returns:
        List of existing log file/directory paths
    """
    default_paths = get_default_automation_paths(framework)
    root = Path(search_root)
    
    existing = []
    for path_str in default_paths:
        path = root / path_str
        if path.exists():
            existing.append(str(path))
    
    return existing


def find_existing_application_logs(search_root: str = ".") -> List[str]:
    """
    Find existing application log files.
    
    Searches for common application log paths that actually exist.
    
    Args:
        search_root: Root directory to search from (default: current directory)
        
    Returns:
        List of existing log file paths
    """
    root = Path(search_root)
    existing = []
    
    # Search for logs directory
    logs_dir = root / "logs"
    if logs_dir.exists() and logs_dir.is_dir():
        # Find all .log files
        for log_file in logs_dir.glob("*.log"):
            existing.append(str(log_file))
    
    # Search for app/logs directory
    app_logs_dir = root / "app" / "logs"
    if app_logs_dir.exists() and app_logs_dir.is_dir():
        for log_file in app_logs_dir.glob("*.log"):
            existing.append(str(log_file))
    
    return existing
