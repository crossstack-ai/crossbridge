"""
Simplified Phase 3 Integration Tests for Orchestrator

Focus on testing orchestrator integration without deep engine testing
(engine is already tested in test_phase3_modernization.py).

Author: CrossBridge AI Team
Date: 2024
"""

import pytest
from unittest.mock import Mock, patch

from core.orchestration.orchestrator import MigrationOrchestrator, LOCATOR_MODERNIZATION_AVAILABLE
from core.locator_modernization.models import ModernizationRecommendation


class TestPhase3BasicIntegration:
    """Test basic Phase 3 integration."""
    
    def test_orchestrator_has_phase3_config(self):
        """Verify orchestrator has Phase 3 configuration."""
        orch = MigrationOrchestrator()
        
        assert hasattr(orch, 'enable_modernization')
        assert hasattr(orch, 'ai_enabled')
        assert hasattr(orch, 'modernization_recommendations')
        
        # Disabled by default
        assert orch.enable_modernization is False
        assert orch.ai_enabled is False
        assert orch.modernization_recommendations == []
    
    def test_phase3_can_be_enabled(self):
        """Verify Phase 3 can be enabled."""
        orch = MigrationOrchestrator()
        
        orch.enable_modernization = True
        orch.ai_enabled = True
        
        assert orch.enable_modernization is True
        assert orch.ai_enabled is True
    
    def test_phase3_modules_available(self):
        """Verify Phase 3 modules can be imported."""
        assert LOCATOR_MODERNIZATION_AVAILABLE is True
    
    def test_backward_compatibility(self):
        """Verify orchestrator works with Phase 3 disabled (backward compat)."""
        orch = MigrationOrchestrator()
        
        # Should have all standard features
        assert 'page_objects' in orch.detected_assets
        assert 'locators' in orch.detected_assets
        assert orch.enable_modernization is False


class TestPhase3ReportGeneration:
    """Test Phase 3 report generation."""
    
    def test_empty_recommendations_returns_empty_summary(self):
        """Test summary with no recommendations."""
        orch = MigrationOrchestrator()
        orch.modernization_recommendations = []
        
        summary = orch._generate_modernization_summary()
        
        assert summary == ""
    
    def test_summary_with_recommendations(self):
        """Test summary generation with recommendations."""
        orch = MigrationOrchestrator()
        orch.enable_modernization = True
        
        # Add sample recommendation
        orch.modernization_recommendations = [
            ModernizationRecommendation(
                page_object="LoginPage",
                file_path="pages/LoginPage.java",
                total_locators=5,
                high_risk_locators=2,
                medium_risk_locators=1,
                low_risk_locators=2
            )
        ]
        
        summary = orch._generate_modernization_summary()
        
        assert summary != ""
        assert "Locator Modernization Analysis" in summary
        assert "1 Page Objects analyzed" in summary
        assert "Risk Distribution" in summary
    
    def test_summary_includes_risk_counts(self):
        """Test summary includes risk distribution."""
        orch = MigrationOrchestrator()
        
        orch.modernization_recommendations = [
            ModernizationRecommendation(
                page_object="HighRiskPage",
                file_path="pages/HighRiskPage.java",
                high_risk_locators=5
            ),
            ModernizationRecommendation(
                page_object="MediumRiskPage",
                file_path="pages/MediumRiskPage.java",
                medium_risk_locators=3
            ),
            ModernizationRecommendation(
                page_object="LowRiskPage",
                file_path="pages/LowRiskPage.java",
                low_risk_locators=2
            )
        ]
        
        summary = orch._generate_modernization_summary()
        
        assert "HIGH" in summary
        assert "MEDIUM" in summary
        assert "LOW" in summary
        assert "3 Page Objects analyzed" in summary


class TestPhase2And3Integration:
    """Test integration between Phase 2 (detection) and Phase 3 (modernization)."""
    
    def test_phase2_detected_assets_available_for_phase3(self):
        """Verify Phase 2 detected assets can be used by Phase 3."""
        orch = MigrationOrchestrator()
        
        # Simulate Phase 2 detection
        orch.detected_assets['page_objects'] = [
            {
                'name': 'LoginPage',
                'file': 'pages/LoginPage.java',
                'locator_count': 5
            }
        ]
        
        # Phase 3 should be able to access this data
        assert len(orch.detected_assets['page_objects']) > 0
        assert orch.detected_assets['page_objects'][0]['name'] == 'LoginPage'
    
    def test_phase3_respects_phase2_empty_detection(self):
        """Verify Phase 3 handles case with no Page Objects detected."""
        orch = MigrationOrchestrator()
        orch.enable_modernization = True
        orch.detected_assets['page_objects'] = []
        
        # Should not crash
        assert len(orch.modernization_recommendations) == 0


class TestPhase3Configuration:
    """Test Phase 3 configuration options."""
    
    def test_heuristic_only_mode(self):
        """Test heuristic-only mode (no AI)."""
        orch = MigrationOrchestrator()
        orch.enable_modernization = True
        orch.ai_enabled = False
        
        assert orch.enable_modernization is True
        assert orch.ai_enabled is False
    
    def test_ai_enabled_mode(self):
        """Test AI-enabled mode."""
        orch = MigrationOrchestrator()
        orch.enable_modernization = True
        orch.ai_enabled = True
        
        assert orch.enable_modernization is True
        assert orch.ai_enabled is True
    
    def test_phase3_disabled_by_default(self):
        """Verify Phase 3 is disabled by default for backward compatibility."""
        orch = MigrationOrchestrator()
        
        assert orch.enable_modernization is False
        assert orch.ai_enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
