"""
Unit tests for AI summary generation.

Tests the AI transformation summary reporting to ensure it shows up correctly.
"""

import pytest
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import MigrationRequest, AIConfig


class TestAISummaryGeneration:
    """Test AI summary generation."""
    
    def test_ai_summary_with_enabled_flag(self):
        """Test that AI summary is generated when AI is enabled."""
        orchestrator = MigrationOrchestrator()
        
        # Simulate AI being enabled
        orchestrator.ai_metrics['enabled'] = True
        orchestrator.ai_metrics['provider'] = 'openai'
        orchestrator.ai_metrics['model'] = 'gpt-3.5-turbo'
        orchestrator.ai_metrics['files_transformed'] = 0
        
        summary = orchestrator._generate_ai_summary()
        
        assert summary != "", "AI summary should not be empty when enabled"
        assert "🤖 AI TRANSFORMATION SUMMARY" in summary
        assert "OpenAI" in summary
        assert "gpt-3.5-turbo" in summary
        assert "AI Ready (No Files Transformed)" in summary
    
    def test_ai_summary_without_enabled_flag(self):
        """Test that AI summary is NOT generated when AI is disabled."""
        orchestrator = MigrationOrchestrator()
        
        # AI not enabled (default state)
        orchestrator.ai_metrics['enabled'] = False
        
        summary = orchestrator._generate_ai_summary()
        
        assert summary == "", "AI summary should be empty when disabled"
    
    def test_ai_summary_with_transformations(self):
        """Test AI summary with actual transformation data."""
        orchestrator = MigrationOrchestrator()
        
        # Simulate AI transformations
        orchestrator.ai_metrics['enabled'] = True
        orchestrator.ai_metrics['provider'] = 'openai'
        orchestrator.ai_metrics['model'] = 'gpt-3.5-turbo'
        orchestrator.ai_metrics['files_transformed'] = 5
        orchestrator.ai_metrics['step_definitions_transformed'] = 3
        orchestrator.ai_metrics['page_objects_transformed'] = 2
        orchestrator.ai_metrics['locators_transformed'] = 0
        orchestrator.ai_metrics['total_tokens'] = 5000
        orchestrator.ai_metrics['total_cost'] = 0.01
        orchestrator.ai_metrics['transformations'] = [
            {
                'file': 'LoginSteps.java',
                'type': 'step_definition',
                'tokens': 1000,
                'cost': 0.002
            },
            {
                'file': 'HomePage.java',
                'type': 'page_object',
                'tokens': 1500,
                'cost': 0.003
            },
            {
                'file': 'UserSteps.java',
                'type': 'step_definition',
                'tokens': 2500,
                'cost': 0.005
            }
        ]
        
        summary = orchestrator._generate_ai_summary()
        
        assert summary != "", "AI summary should not be empty with transformations"
        assert "🤖 AI TRANSFORMATION SUMMARY" in summary
        assert "Total Files Transformed: 5" in summary
        assert "Step Definitions: 3" in summary
        assert "Page Objects: 2" in summary
        assert "Total Tokens: 5,000" in summary
        assert "Total Cost: $0.0100" in summary
        assert "Avg Tokens/File: 1000" in summary
        assert "Top Cost Files:" in summary
        assert "UserSteps.java" in summary  # Should be top cost file
    
    def test_ai_summary_with_no_provider(self):
        """Test AI summary handles missing provider gracefully."""
        orchestrator = MigrationOrchestrator()
        
        # AI enabled but no provider set
        orchestrator.ai_metrics['enabled'] = True
        orchestrator.ai_metrics['provider'] = None
        orchestrator.ai_metrics['model'] = None
        orchestrator.ai_metrics['files_transformed'] = 0
        
        summary = orchestrator._generate_ai_summary()
        
        assert summary != "", "AI summary should handle None provider"
        assert "Unknown" in summary  # Should show "Unknown" for provider/model
    
    def test_ai_metrics_initialization(self):
        """Test that AI metrics are properly initialized."""
        orchestrator = MigrationOrchestrator()
        
        assert orchestrator.ai_metrics['enabled'] == False
        assert orchestrator.ai_metrics['provider'] is None
        assert orchestrator.ai_metrics['model'] is None
        assert orchestrator.ai_metrics['total_tokens'] == 0
        assert orchestrator.ai_metrics['total_cost'] == 0.0
        assert orchestrator.ai_metrics['files_transformed'] == 0
        assert orchestrator.ai_metrics['step_definitions_transformed'] == 0
        assert orchestrator.ai_metrics['page_objects_transformed'] == 0
        assert orchestrator.ai_metrics['locators_transformed'] == 0
        assert orchestrator.ai_metrics['transformations'] == []
    
    def test_ai_summary_cost_breakdown(self):
        """Test AI summary shows cost breakdown by file type."""
        orchestrator = MigrationOrchestrator()
        
        orchestrator.ai_metrics['enabled'] = True
        orchestrator.ai_metrics['provider'] = 'anthropic'
        orchestrator.ai_metrics['model'] = 'claude-3-sonnet-20240229'
        orchestrator.ai_metrics['files_transformed'] = 6
        orchestrator.ai_metrics['step_definitions_transformed'] = 3
        orchestrator.ai_metrics['page_objects_transformed'] = 2
        orchestrator.ai_metrics['locators_transformed'] = 1
        orchestrator.ai_metrics['total_tokens'] = 10000
        orchestrator.ai_metrics['total_cost'] = 0.03
        orchestrator.ai_metrics['transformations'] = [
            {'file': 'Steps1.java', 'type': 'step_definition', 'tokens': 2000, 'cost': 0.006},
            {'file': 'Steps2.java', 'type': 'step_definition', 'tokens': 2000, 'cost': 0.006},
            {'file': 'Steps3.java', 'type': 'step_definition', 'tokens': 2000, 'cost': 0.006},
            {'file': 'Page1.java', 'type': 'page_object', 'tokens': 2000, 'cost': 0.006},
            {'file': 'Page2.java', 'type': 'page_object', 'tokens': 1000, 'cost': 0.003},
            {'file': 'Locators.java', 'type': 'locator', 'tokens': 1000, 'cost': 0.003}
        ]
        
        summary = orchestrator._generate_ai_summary()
        
        assert "Cost Breakdown by Type:" in summary
        assert "Step Definitions:" in summary
        assert "Page Objects:" in summary
        assert "Locators:" in summary
        assert "$0.0180" in summary  # Step definitions cost
        assert "$0.0090" in summary  # Page objects cost
        assert "$0.0030" in summary  # Locators cost


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
