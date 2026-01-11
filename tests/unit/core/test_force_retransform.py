"""
Unit tests for force retransform and transformation tier functionality.

Tests the flexible transformation system:
- Force retransform flag to override skip logic
- Transformation tier selection (TIER 1, 2, 3)
- Smart defaults (skip already-enhanced files)
- All three options working harmoniously
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import (
    MigrationRequest,
    MigrationType,
    OperationType,
    TransformationMode,
    TransformationTier,
    RepositoryAuth,
    AuthType
)


def create_test_auth():
    """Helper to create test auth."""
    return RepositoryAuth(auth_type=AuthType.AZURE_PAT, token="test_token")


class TestForceRetransformFlag:
    """Test force_retransform flag functionality."""
    
    def test_skip_already_enhanced_by_default(self):
        """Test that already-enhanced files are skipped by default."""
        orchestrator = MigrationOrchestrator()
        
        already_enhanced_content = """*** Settings ***
Documentation    Test - Enhanced with CrossStack Platform Integration
...              Generated: 2026-01-01 12:00:00

*** Test Cases ***
Test Case 1
    Log    Hello World
"""
        
        # Without force, should return unchanged
        result = orchestrator._apply_enhanced_formatting(
            already_enhanced_content,
            "test.robot",
            force=False,
            tier=1
        )
        
        assert result == already_enhanced_content
    
    def test_force_retransform_overrides_skip(self):
        """Test that force=True re-applies transformation to enhanced files."""
        orchestrator = MigrationOrchestrator()
        
        already_enhanced_content = """*** Settings ***
Documentation    Test - Enhanced with CrossStack Platform Integration
...              Generated: 2026-01-01 12:00:00

*** Test Cases ***
Test Case 1
    Log    Hello World
"""
        
        # With force=True, should re-apply transformation
        result = orchestrator._apply_enhanced_formatting(
            already_enhanced_content,
            "test.robot",
            force=True,
            tier=1
        )
        
        # Content should be different (new timestamp, updated headers)
        assert result != already_enhanced_content
        assert "CrossStack Platform Integration" in result
    
    def test_fresh_file_always_transformed(self):
        """Test that non-enhanced files are always transformed."""
        orchestrator = MigrationOrchestrator()
        
        plain_content = """*** Settings ***
Library    Browser

*** Test Cases ***
Test Case 1
    Log    Hello World
"""
        
        # Should transform regardless of force flag
        result_no_force = orchestrator._apply_enhanced_formatting(
            plain_content,
            "test.robot",
            force=False,
            tier=1
        )
        
        result_force = orchestrator._apply_enhanced_formatting(
            plain_content,
            "test.robot",
            force=True,
            tier=1
        )
        
        # Both should be enhanced
        assert result_no_force != plain_content
        assert result_force != plain_content
        assert "CrossStack Platform Integration" in result_no_force
        assert "CrossStack Platform Integration" in result_force


class TestTransformationTiers:
    """Test transformation tier functionality."""
    
    def test_tier1_quick_header_refresh(self):
        """Test TIER 1: Quick header refresh."""
        orchestrator = MigrationOrchestrator()
        
        content = """*** Settings ***
Library    Browser

*** Test Cases ***
Test Case 1
    Log    Hello
"""
        
        result = orchestrator._apply_tier1_formatting(content, "test.robot")
        
        # Should have enhanced header
        assert "CrossStack Platform Integration" in result
        assert "AI-Ready: True" in result
        assert "Generated:" in result
        
        # Original content should be preserved
        assert "*** Test Cases ***" in result
        assert "Test Case 1" in result
        assert "Log    Hello" in result
    
    def test_tier2_content_validation(self):
        """Test TIER 2: Content validation and optimization."""
        orchestrator = MigrationOrchestrator()
        
        content = """*** Settings ***
Library    Browser

*** Test Cases ***
Test Case 1
    Log    Hello
"""
        
        result = orchestrator._apply_tier2_formatting(content, "test.robot")
        
        # Should have TIER 1 enhancements
        assert "CrossStack Platform Integration" in result
        
        # Should have TIER 2 validation marker
        assert "Tier 2 Validation" in result
        
        # Content should be validated
        assert "*** Test Cases ***" in result
    
    def test_tier3_deep_regeneration(self):
        """Test TIER 3: Deep re-generation."""
        orchestrator = MigrationOrchestrator()
        
        content = """*** Settings ***
Library    Browser

*** Test Cases ***
Test Case 1
    Log    Hello
"""
        
        result = orchestrator._apply_tier3_formatting(content, "test.robot")
        
        # Should have TIER 1 and TIER 2 enhancements
        assert "CrossStack Platform Integration" in result
        
        # Should have TIER 3 marker
        assert "Tier 3 Deep" in result
    
    def test_tier_parameter_respected(self):
        """Test that tier parameter is properly respected."""
        orchestrator = MigrationOrchestrator()
        
        content = """*** Test Cases ***
Test
    Log    Hi
"""
        
        # Test each tier
        tier1_result = orchestrator._apply_enhanced_formatting(
            content, "test.robot", force=False, tier=1
        )
        tier2_result = orchestrator._apply_enhanced_formatting(
            content, "test.robot", force=False, tier=2
        )
        tier3_result = orchestrator._apply_enhanced_formatting(
            content, "test.robot", force=False, tier=3
        )
        
        # All should be enhanced
        assert "CrossStack" in tier1_result
        assert "CrossStack" in tier2_result
        assert "CrossStack" in tier3_result
        
        # TIER 2 should have validation marker
        assert "Tier 2 Validation" in tier2_result
        
        # TIER 3 should have deep marker
        assert "Tier 3 Deep" in tier3_result


class TestMigrationRequestConfiguration:
    """Test MigrationRequest with new configuration options."""
    
    def test_default_values(self):
        """Test that defaults are correctly set."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://dev.azure.com/org/project/_git/repo",
            branch="main",
            auth=create_test_auth()
        )
        
        # Defaults
        assert request.force_retransform is False
        assert request.transformation_tier == TransformationTier.TIER_1
    
    def test_force_retransform_enabled(self):
        """Test force_retransform can be enabled."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://dev.azure.com/org/project/_git/repo",
            branch="main",
            auth=create_test_auth(),
            force_retransform=True
        )
        
        assert request.force_retransform is True
    
    def test_transformation_tier_selection(self):
        """Test all transformation tiers can be selected."""
        for tier in [TransformationTier.TIER_1, TransformationTier.TIER_2, TransformationTier.TIER_3]:
            request = MigrationRequest(
                migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
                repo_url="https://dev.azure.com/org/project/_git/repo",
                branch="main",
                auth=create_test_auth(),
                transformation_tier=tier
            )
            
            assert request.transformation_tier == tier
    
    def test_force_with_tier_combination(self):
        """Test force_retransform with specific tier."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://dev.azure.com/org/project/_git/repo",
            branch="main",
            auth=create_test_auth(),
            operation_type=OperationType.TRANSFORMATION,
            force_retransform=True,
            transformation_tier=TransformationTier.TIER_2
        )
        
        assert request.force_retransform is True
        assert request.transformation_tier == TransformationTier.TIER_2
        assert request.operation_type == OperationType.TRANSFORMATION


class TestIntegratedWorkflow:
    """Test integrated workflow combining all features."""
    
    def test_smart_default_workflow(self):
        """Test default workflow: skip already-enhanced files."""
        orchestrator = MigrationOrchestrator()
        
        enhanced_file = """*** Settings ***
Documentation    Test - Enhanced with CrossStack Platform Integration
*** Test Cases ***
Test
    Log    Hello
"""
        
        # Default behavior (no force, TIER 1)
        result = orchestrator._apply_enhanced_formatting(
            enhanced_file,
            "test.robot",
            force=False,
            tier=1
        )
        
        # Should skip transformation
        assert result == enhanced_file
    
    def test_force_tier1_workflow(self):
        """Test force + TIER 1: Quick header refresh."""
        orchestrator = MigrationOrchestrator()
        
        old_enhanced = """*** Settings ***
Documentation    Test - Enhanced with CrossStack Platform Integration
...              Generated: 2025-01-01 12:00:00
*** Test Cases ***
Test
    Log    Hello
"""
        
        result = orchestrator._apply_enhanced_formatting(
            old_enhanced,
            "test.robot",
            force=True,
            tier=1
        )
        
        # Should have new timestamp
        assert result != old_enhanced
        assert "Generated: 2026" in result  # Updated year
    
    def test_force_tier2_workflow(self):
        """Test force + TIER 2: Content validation."""
        orchestrator = MigrationOrchestrator()
        
        enhanced_file = """*** Settings ***
Documentation    Test - Enhanced with CrossStack Platform Integration
*** Test Cases ***
Test
    Log    Hello
"""
        
        result = orchestrator._apply_enhanced_formatting(
            enhanced_file,
            "test.robot",
            force=True,
            tier=2
        )
        
        # Should have validation marker
        assert "Tier 2 Validation" in result
    
    def test_force_tier3_workflow(self):
        """Test force + TIER 3: Deep re-generation."""
        orchestrator = MigrationOrchestrator()
        
        enhanced_file = """*** Settings ***
Documentation    Test - Enhanced with CrossStack Platform Integration
*** Test Cases ***
Test
    Log    Hello
"""
        
        result = orchestrator._apply_enhanced_formatting(
            enhanced_file,
            "test.robot",
            force=True,
            tier=3
        )
        
        # Should have deep marker
        assert "Tier 3 Deep" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_invalid_tier_fallback(self):
        """Test that invalid tier falls back to TIER 1."""
        orchestrator = MigrationOrchestrator()
        
        content = """*** Test Cases ***
Test
    Log    Hi
"""
        
        # Invalid tier number
        result = orchestrator._apply_enhanced_formatting(
            content,
            "test.robot",
            force=False,
            tier=99  # Invalid
        )
        
        # Should fallback to TIER 1
        assert "CrossStack Platform Integration" in result
    
    def test_empty_content(self):
        """Test handling of empty content."""
        orchestrator = MigrationOrchestrator()
        
        result = orchestrator._apply_tier1_formatting("", "empty.robot")
        
        # Should add header
        assert "*** Settings ***" in result
        assert "CrossStack" in result
    
    def test_malformed_robot_file(self):
        """Test handling of malformed Robot Framework file."""
        orchestrator = MigrationOrchestrator()
        
        malformed = """This is not valid Robot Framework syntax
Random text without structure
"""
        
        # Should still add header
        result = orchestrator._apply_tier1_formatting(malformed, "malformed.robot")
        
        assert "*** Settings ***" in result
        assert "This is not valid" in result  # Original content preserved


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
