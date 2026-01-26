"""
Unit tests for Integration Testing Framework (Phase 4).
"""

import pytest
import shutil
from core.testing.integration_framework import IntegrationTestFramework


class TestIntegrationFramework:
    """Test integration testing framework."""
    
    def test_create_test_project(self):
        """Test test project creation."""
        framework = IntegrationTestFramework()
        
        test_project = framework.create_test_project('pytest')
        
        assert test_project.exists()
        assert (test_project / 'tests').exists()
        
        # Cleanup
        if test_project.exists():
            shutil.rmtree(test_project)
    
    def test_get_test_statistics(self):
        """Test statistics calculation."""
        framework = IntegrationTestFramework()
        
        framework.test_results = [
            {'adapter': 'pytest', 'success': True, 'duration': 1.0},
            {'adapter': 'behave', 'success': True, 'duration': 2.0},
            {'adapter': 'cypress', 'success': False, 'duration': 0.5},
        ]
        
        stats = framework.get_test_statistics()
        
        assert stats['total'] == 3
        assert stats['successful'] == 2
        assert stats['failed'] == 1
