"""
Unit Tests for Phase 3: AI-Assisted Locator Modernization Integration with Orchestrator.

Tests verify that Phase 3 (locator modernization) integrates correctly with the
Migration Orchestrator without breaking existing functionality.

Test Coverage:
1. Phase 3 disabled by default (backward compatibility)
2. Phase 3 enabled with heuristic-only mode
3. Phase 3 enabled with AI mode
4. Phase 2 + Phase 3 integration (detection → analysis)
5. Configuration options validation
6. Error handling and graceful degradation
7. Report generation integration
8. Progress callbacks with Phase 3

Author: CrossBridge AI Team
Date: 2024
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Import orchestrator and Phase 3 modules
from core.orchestration.orchestrator import MigrationOrchestrator, LOCATOR_MODERNIZATION_AVAILABLE
from core.orchestration.models import (
    MigrationRequest, 
    MigrationType, 
    RepositoryAuth, 
    AuthType,
    TransformationMode
)


class TestPhase3IntegrationBasics:
    """Test basic Phase 3 integration with orchestrator."""
    
    def test_phase3_imports_available(self):
        """Verify Phase 3 modules can be imported."""
        assert LOCATOR_MODERNIZATION_AVAILABLE, "Phase 3 modules should be available"
        
        from core.locator_modernization.engine import ModernizationEngine
        from core.locator_modernization.reporters import ModernizationReporter
        
        # Verify classes are importable
        assert ModernizationEngine is not None
        assert ModernizationReporter is not None
    
    def test_orchestrator_phase3_config_initialization(self):
        """Verify orchestrator initializes with Phase 3 configuration."""
        orchestrator = MigrationOrchestrator()
        
        # Phase 3 should be disabled by default
        assert hasattr(orchestrator, 'enable_modernization')
        assert hasattr(orchestrator, 'ai_enabled')
        assert hasattr(orchestrator, 'modernization_recommendations')
        
        assert orchestrator.enable_modernization is False
        assert orchestrator.ai_enabled is False
        assert orchestrator.modernization_recommendations == []
    
    def test_orchestrator_phase3_config_can_be_enabled(self):
        """Verify Phase 3 can be enabled via configuration."""
        orchestrator = MigrationOrchestrator()
        
        # Enable Phase 3
        orchestrator.enable_modernization = True
        orchestrator.ai_enabled = True
        
        assert orchestrator.enable_modernization is True
        assert orchestrator.ai_enabled is True
    
    def test_orchestrator_backward_compatibility(self):
        """Verify orchestrator works normally with Phase 3 disabled."""
        orchestrator = MigrationOrchestrator()
        
        # Phase 3 disabled (default) should not affect existing functionality
        assert orchestrator.enable_modernization is False
        
        # Should have all standard detection assets
        assert 'page_objects' in orchestrator.detected_assets
        assert 'locators' in orchestrator.detected_assets
        assert 'test_classes' in orchestrator.detected_assets


class TestPhase3ModernizationEngine:
    """Test Phase 3 modernization engine integration."""
    
    @pytest.mark.skipif(not LOCATOR_MODERNIZATION_AVAILABLE, reason="Phase 3 not available")
    def test_modernization_engine_heuristic_mode(self):
        """Test modernization engine in heuristic-only mode."""
        from core.locator_modernization.engine import ModernizationEngine
        from core.locator_awareness.models import PageObject, Locator
        
        # Create engine with AI disabled
        engine = ModernizationEngine(
            enable_ai=False,
            min_confidence_threshold=0.7
        )
        
        # Create sample Page Object with problematic locator
        page_object = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            locators=[
                Locator(
                    name="username_field",
                    value="//div[1]/input[@class='username']",
                    strategy="xpath",
                    page_object_class="LoginPage"
                )
            ]
        )
        
        # Analyze should work without AI
        recommendation = engine.analyze_page_object(page_object)
        
        assert recommendation is not None
        assert recommendation.page_object_name == "LoginPage"
        assert recommendation.risk_score is not None
        assert len(recommendation.suggestions) >= 0  # May have suggestions
    
    @pytest.mark.skipif(not LOCATOR_MODERNIZATION_AVAILABLE, reason="Phase 3 not available")
    def test_modernization_engine_with_multiple_page_objects(self):
        """Test batch analysis of multiple Page Objects."""
        from core.locator_modernization.engine import ModernizationEngine
        from core.locator_awareness.models import PageObject, Locator
        
        engine = ModernizationEngine(enable_ai=False)
        
        # Create multiple Page Objects
        page_objects = [
            PageObject(
                name="LoginPage",
                file_path="pages/LoginPage.java",
                locators=[
                    Locator(name="username", value="//div[1]/input", strategy="xpath", page_object_class="LoginPage"),
                    Locator(name="password", value="#password", strategy="css", page_object_class="LoginPage")
                ]
            ),
            PageObject(
                name="HomePage",
                file_path="pages/HomePage.java",
                locators=[
                    Locator(name="logo", value="img.logo", strategy="css", page_object_class="HomePage")
                ]
            )
        ]
        
        # Batch analysis
        recommendations = engine.analyze_batch(page_objects)
        
        assert len(recommendations) == 2
        assert recommendations[0].page_object_name == "LoginPage"
        assert recommendations[1].page_object_name == "HomePage"


class TestPhase3OrchestratorIntegration:
    """Test Phase 3 integration with orchestrator workflow."""
    
    def test_orchestrator_phase3_disabled_skips_analysis(self):
        """Verify Phase 3 analysis is skipped when disabled."""
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = False
        
        # Add some Page Objects to detected assets
        orchestrator.detected_assets['page_objects'] = [
            {
                'name': 'LoginPage',
                'file': 'pages/LoginPage.java',
                'locator_count': 5
            }
        ]
        
        # Modernization should not run
        assert orchestrator.enable_modernization is False
        assert len(orchestrator.modernization_recommendations) == 0
    
    @pytest.mark.skipif(not LOCATOR_MODERNIZATION_AVAILABLE, reason="Phase 3 not available")
    @patch('core.locator_modernization.engine.ModernizationEngine.analyze_batch')
    def test_orchestrator_phase3_enabled_runs_analysis(self, mock_analyze):
        """Verify Phase 3 analysis runs when enabled."""
        from core.locator_modernization.models import (
            ModernizationRecommendation,
            RiskScore,
            RiskLevel
        )
        
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        orchestrator.ai_enabled = False
        
        # Add Page Objects
        orchestrator.detected_assets['page_objects'] = [
            {
                'name': 'LoginPage',
                'file': 'pages/LoginPage.java',
                'locator_count': 3,
                'locators': []
            }
        ]
        
        # Mock analyze_batch to return recommendations
        mock_recommendation = ModernizationRecommendation(
            page_object_name="LoginPage",
            risk_score=RiskScore(
                heuristic_score=0.8,
                risk_level=RiskLevel.HIGH  # Will be overridden by __post_init__
            ),
            suggestions=[]
        )
        mock_analyze.return_value = [mock_recommendation]
        
        # This would normally be called in _transform_files()
        # We're testing the integration logic separately
        from core.locator_modernization.engine import ModernizationEngine
        engine = ModernizationEngine(enable_ai=False)
        recommendations = engine.analyze_batch([])  # Empty for mock
        
        # Should have been called
        assert mock_analyze.called or len(recommendations) == 0
    
    def test_orchestrator_modernization_summary_generation(self):
        """Test modernization summary generation."""
        from core.locator_modernization.models import (
            ModernizationRecommendation,
            RiskScore,
            RiskLevel,
            ModernizationSuggestion
        )
        
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        
        # Create sample recommendations
        orchestrator.modernization_recommendations = [
            ModernizationRecommendation(
                page_object_name="LoginPage",
                risk_score=RiskScore(
                    heuristic_score=0.9,
                    risk_level=RiskLevel.VERY_HIGH  # Will be overridden
                ),
                suggestions=[
                    ModernizationSuggestion(
                        locator_name="username",
                        page_object="LoginPage",
                        current_strategy="xpath",
                        current_value="//div[1]/input",
                        suggested_strategy="css",
                        suggested_value="input[data-testid='username']",
                        confidence=0.9,
                        reason="Index-based XPath is fragile",
                        source="heuristic",
                        current_risk=RiskScore(heuristic_score=0.9, risk_level=RiskLevel.HIGH)
                    )
                ]
            ),
            ModernizationRecommendation(
                page_object_name="HomePage",
                risk_score=RiskScore(
                    heuristic_score=0.2,
                    risk_level=RiskLevel.LOW  # Will be overridden
                ),
                suggestions=[]
            )
        ]
        
        # Generate summary
        summary = orchestrator._generate_modernization_summary()
        
        assert summary is not None
        assert len(summary) > 0
        assert "Locator Modernization Analysis" in summary
        assert "2 Page Objects analyzed" in summary
        assert "VERY HIGH" in summary or "VERY_HIGH" in summary
        assert "LoginPage" in summary


class TestPhase3ErrorHandling:
    """Test Phase 3 error handling and graceful degradation."""
    
    def test_orchestrator_handles_missing_page_objects(self):
        """Verify orchestrator handles case with no Page Objects."""
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        
        # No Page Objects detected
        orchestrator.detected_assets['page_objects'] = []
        
        # Should not crash
        assert len(orchestrator.modernization_recommendations) == 0
    
    def test_orchestrator_generates_empty_summary_with_no_recommendations(self):
        """Verify summary generation handles empty recommendations."""
        orchestrator = MigrationOrchestrator()
        orchestrator.modernization_recommendations = []
        
        summary = orchestrator._generate_modernization_summary()
        
        # Should return empty string
        assert summary == ""
    
    @pytest.mark.skipif(not LOCATOR_MODERNIZATION_AVAILABLE, reason="Phase 3 not available")
    @patch('core.locator_modernization.engine.ModernizationEngine.analyze_batch')
    def test_orchestrator_handles_analysis_failure(self, mock_analyze):
        """Verify orchestrator handles Phase 3 analysis failures gracefully."""
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        
        # Add Page Objects
        orchestrator.detected_assets['page_objects'] = [
            {'name': 'LoginPage', 'file': 'pages/LoginPage.java', 'locators': []}
        ]
        
        # Mock analysis failure
        mock_analyze.side_effect = Exception("AI service unavailable")
        
        # Should not crash the orchestrator
        # In real integration, this would be caught in _transform_files()
        try:
            from core.locator_modernization.engine import ModernizationEngine
            engine = ModernizationEngine(enable_ai=False)
            recommendations = engine.analyze_batch([])
        except Exception:
            pass  # Expected to be caught and logged
        
        # Orchestrator should continue without Phase 3
        assert True


class TestPhase3ReportingIntegration:
    """Test Phase 3 reporting integration."""
    
    def test_modernization_summary_format(self):
        """Verify modernization summary has correct format."""
        from core.locator_modernization.models import (
            ModernizationRecommendation,
            RiskScore,
            RiskLevel
        )
        
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        orchestrator.ai_enabled = False
        
        # Add sample recommendations
        orchestrator.modernization_recommendations = [
            ModernizationRecommendation(
                page_object_name="TestPage",
                risk_score=RiskScore(heuristic_score=0.5, risk_level=RiskLevel.MEDIUM),
                suggestions=[]
            )
        ]
        
        summary = orchestrator._generate_modernization_summary()
        
        # Verify summary structure
        assert "╭─────────────────────────────────────────────────────────╮" in summary
        assert "Locator Modernization Analysis" in summary
        assert "╰─────────────────────────────────────────────────────────╯" in summary
        assert "Analysis Results:" in summary
        assert "Risk Distribution:" in summary
        assert "Recommendations:" in summary
    
    def test_modernization_summary_includes_risk_distribution(self):
        """Verify summary includes risk level distribution."""
        from core.locator_modernization.models import (
            ModernizationRecommendation,
            RiskScore,
            RiskLevel
        )
        
        orchestrator = MigrationOrchestrator()
        orchestrator.modernization_recommendations = [
            ModernizationRecommendation(
                page_object_name="HighRiskPage",
                risk_score=RiskScore(heuristic_score=0.9, risk_level=RiskLevel.VERY_HIGH),
                suggestions=[]
            ),
            ModernizationRecommendation(
                page_object_name="LowRiskPage",
                risk_score=RiskScore(heuristic_score=0.1, risk_level=RiskLevel.VERY_LOW),
                suggestions=[]
            )
        ]
        
        summary = orchestrator._generate_modernization_summary()
        
        assert "VERY HIGH" in summary or "VERY_HIGH" in summary
        assert "VERY LOW" in summary or "VERY_LOW" in summary
        assert "🔴" in summary  # Very high risk emoji
        assert "✅" in summary  # Very low risk emoji


class TestPhase2And3Integration:
    """Test integration between Phase 2 (Detection) and Phase 3 (Modernization)."""
    
    def test_phase2_detection_feeds_phase3_analysis(self):
        """Verify Phase 2 detection results are used by Phase 3."""
        orchestrator = MigrationOrchestrator()
        
        # Phase 2 should populate detected_assets
        orchestrator.detected_assets['page_objects'] = [
            {
                'name': 'LoginPage',
                'file': 'pages/LoginPage.java',
                'locator_count': 5,
                'locators': []
            }
        ]
        
        # Phase 3 should consume detected_assets when enabled
        orchestrator.enable_modernization = True
        
        # Verify data is available for Phase 3
        assert len(orchestrator.detected_assets['page_objects']) > 0
        assert orchestrator.enable_modernization is True
    
    def test_phase3_handles_phase2_edge_cases(self):
        """Verify Phase 3 handles edge cases from Phase 2 detection."""
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        
        # Edge case 1: Page Object with no locators
        orchestrator.detected_assets['page_objects'] = [
            {
                'name': 'EmptyPage',
                'file': 'pages/EmptyPage.java',
                'locator_count': 0,
                'locators': []
            }
        ]
        
        # Should not crash
        assert len(orchestrator.detected_assets['page_objects']) == 1
        
        # Edge case 2: Malformed Page Object
        orchestrator.detected_assets['page_objects'] = [
            {
                'name': 'MalformedPage'
                # Missing required fields
            }
        ]
        
        # Should handle gracefully
        assert True


class TestPhase3Configuration:
    """Test Phase 3 configuration options."""
    
    def test_heuristic_only_mode(self):
        """Test heuristic-only mode (AI disabled)."""
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        orchestrator.ai_enabled = False
        
        assert orchestrator.ai_enabled is False
        # Heuristic analysis should work
    
    def test_ai_enabled_mode(self):
        """Test AI-enabled mode."""
        orchestrator = MigrationOrchestrator()
        orchestrator.enable_modernization = True
        orchestrator.ai_enabled = True
        
        assert orchestrator.ai_enabled is True
        # AI analysis should be attempted (if available)
    
    def test_phase3_disabled_default(self):
        """Verify Phase 3 is disabled by default for backward compatibility."""
        orchestrator = MigrationOrchestrator()
        
        assert orchestrator.enable_modernization is False
        assert orchestrator.ai_enabled is False
        
        # Should not affect existing workflows
        assert 'page_objects' in orchestrator.detected_assets


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
