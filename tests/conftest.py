"""
Pytest configuration and shared fixtures for CrossBridge tests.
"""

import pytest
import sys
from pathlib import Path

# Ensure the project root is at the front of sys.path
# This prevents test directories from shadowing actual packages
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_pytest_project():
    """Fixture providing a sample pytest project structure."""
    pass


@pytest.fixture
def sample_robot_project():
    """Fixture providing a sample Robot Framework project structure."""
    pass
