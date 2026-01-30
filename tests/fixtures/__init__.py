"""
Golden Test Fixtures for CrossBridge

Canonical, deterministic fixtures used across all test suites.
These fixtures ensure consistent, repeatable test behavior.

Rules:
- No randomness
- No timestamps (use fixed dates)
- No environment-specific data
- Deterministic outputs
"""

# Export all fixtures
from .sample_tests import *
from .sample_scenarios import *
from .sample_failures import *

__all__ = [
    # Sample tests
    'sample_test',
    'sample_pytest_test',
    'sample_selenium_test',
    'sample_robot_test',
    'sample_cypress_test',
    
    # Sample scenarios
    'sample_login_scenario',
    'sample_api_scenario',
    'sample_bdd_scenario',
    
    # Sample failures
    'sample_timeout_failure',
    'sample_assertion_failure',
    'sample_locator_failure',
    'sample_network_failure',
]
