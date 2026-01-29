#!/usr/bin/env python3
"""Test AI transformation summary generation."""

from core.orchestration.orchestrator import MigrationOrchestrator


def test_ai_summary_generation():
    """Test that AI summary is generated correctly."""
    print("\n=== Testing AI Summary Generation ===\n")
    
    # Create orchestrator
    orchestrator = MigrationOrchestrator()
    
    # Simulate AI transformations
    orchestrator.ai_metrics = {
        'enabled': True,
        'provider': 'openai',
        'model': 'gpt-3.5-turbo',
        'total_tokens': 15450,
        'total_cost': 0.0309,
        'files_transformed': 12,
        'step_definitions_transformed': 5,
        'page_objects_transformed': 4,
        'locators_transformed': 3,
        'transformations': [
            {
                'file': 'src/test/java/steps/LoginStepDefinitions.java',
                'type': 'step_definition',
                'tokens': 1850,
                'cost': 0.0037
            },
            {
                'file': 'src/test/java/steps/UserManagementSteps.java',
                'type': 'step_definition',
                'tokens': 2100,
                'cost': 0.0042
            },
            {
                'file': 'src/test/java/pages/LoginPage.java',
                'type': 'page_object',
                'tokens': 1200,
                'cost': 0.0024
            },
            {
                'file': 'src/test/java/pages/DashboardPage.java',
                'type': 'page_object',
                'tokens': 1450,
                'cost': 0.0029
            },
            {
                'file': 'src/test/java/locators/LoginLocators.java',
                'type': 'locator',
                'tokens': 850,
                'cost': 0.0017
            },
            {
                'file': 'src/test/java/steps/CheckoutSteps.java',
                'type': 'step_definition',
                'tokens': 2500,
                'cost': 0.0050
            },
            {
                'file': 'src/test/java/pages/ProductPage.java',
                'type': 'page_object',
                'tokens': 1100,
                'cost': 0.0022
            },
            {
                'file': 'src/test/java/steps/SearchSteps.java',
                'type': 'step_definition',
                'tokens': 1300,
                'cost': 0.0026
            },
            {
                'file': 'src/test/java/pages/CartPage.java',
                'type': 'page_object',
                'tokens': 950,
                'cost': 0.0019
            },
            {
                'file': 'src/test/java/locators/ProductLocators.java',
                'type': 'locator',
                'tokens': 750,
                'cost': 0.0015
            },
            {
                'file': 'src/test/java/steps/RegistrationSteps.java',
                'type': 'step_definition',
                'tokens': 1800,
                'cost': 0.0036
            },
            {
                'file': 'src/test/java/locators/CommonLocators.java',
                'type': 'locator',
                'tokens': 600,
                'cost': 0.0012
            }
        ]
    }
    
    # Generate AI summary
    summary = orchestrator._generate_ai_summary()
    
    # Display the summary
    print(summary)
    
    # Verify key components
    print("\n✅ Summary Tests:")
    assert "AI TRANSFORMATION SUMMARY" in summary, "Missing header"
    print("  ✓ Header present")
    
    assert "Provider: Openai" in summary, "Missing provider"
    print("  ✓ Provider shown")
    
    assert "Model: gpt-3.5-turbo" in summary, "Missing model"
    print("  ✓ Model shown")
    
    assert "Total Files Transformed: 12" in summary, "Missing file count"
    print("  ✓ File count correct")
    
    assert "Step Definitions: 5" in summary, "Missing step definition count"
    print("  ✓ Step definition count correct")
    
    assert "Page Objects: 4" in summary, "Missing page object count"
    print("  ✓ Page object count correct")
    
    assert "Locators: 3" in summary, "Missing locator count"
    print("  ✓ Locator count correct")
    
    assert "15,450" in summary, "Missing token count"
    print("  ✓ Token count shown")
    
    assert "$0.0309" in summary, "Missing total cost"
    print("  ✓ Total cost shown")
    
    assert "Avg Tokens/File" in summary, "Missing average tokens"
    print("  ✓ Average tokens shown")
    
    assert "Cost Breakdown by Type" in summary, "Missing cost breakdown"
    print("  ✓ Cost breakdown shown")
    
    assert "Top Cost Files" in summary, "Missing top files"
    print("  ✓ Top cost files shown")
    
    assert "Cost Savings" in summary or "Alternative Options" in summary, "Missing cost comparison"
    print("  ✓ Cost comparison shown")
    
    print("\n🎉 All AI summary tests passed!")


def test_ai_summary_with_gpt4():
    """Test AI summary with GPT-4 model."""
    print("\n=== Testing AI Summary with GPT-4 ===\n")
    
    # Create orchestrator
    orchestrator = MigrationOrchestrator()
    
    # Simulate AI transformations with GPT-4
    orchestrator.ai_metrics = {
        'enabled': True,
        'provider': 'openai',
        'model': 'gpt-4',
        'total_tokens': 8500,
        'total_cost': 0.2550,  # ~15x more expensive
        'files_transformed': 5,
        'step_definitions_transformed': 3,
        'page_objects_transformed': 2,
        'locators_transformed': 0,
        'transformations': [
            {
                'file': 'src/test/java/steps/LoginSteps.java',
                'type': 'step_definition',
                'tokens': 2000,
                'cost': 0.0600
            },
            {
                'file': 'src/test/java/steps/UserSteps.java',
                'type': 'step_definition',
                'tokens': 2200,
                'cost': 0.0660
            },
            {
                'file': 'src/test/java/pages/LoginPage.java',
                'type': 'page_object',
                'tokens': 1800,
                'cost': 0.0540
            },
            {
                'file': 'src/test/java/pages/DashboardPage.java',
                'type': 'page_object',
                'tokens': 1500,
                'cost': 0.0450
            },
            {
                'file': 'src/test/java/steps/CheckoutSteps.java',
                'type': 'step_definition',
                'tokens': 1000,
                'cost': 0.0300
            }
        ]
    }
    
    # Generate AI summary
    summary = orchestrator._generate_ai_summary()
    
    print(summary)
    
    print("\n✅ GPT-4 Summary Tests:")
    assert "Model: gpt-4" in summary, "Missing GPT-4 model"
    print("  ✓ GPT-4 model shown")
    
    assert "Alternative Options" in summary, "Missing alternative cost comparison"
    print("  ✓ Alternative cost comparison shown")
    
    assert "gpt-3.5-turbo" in summary, "Missing economical alternative"
    print("  ✓ Economical alternative mentioned")
    
    print("\n🎉 GPT-4 summary test passed!")


def test_empty_ai_summary():
    """Test that no summary is generated when AI not used."""
    print("\n=== Testing Empty AI Summary ===\n")
    
    # Create orchestrator
    orchestrator = MigrationOrchestrator()
    
    # AI not enabled
    summary = orchestrator._generate_ai_summary()
    
    assert summary == "", "Summary should be empty when AI not used"
    print("✓ No summary when AI disabled")
    
    # AI enabled but no files transformed
    orchestrator.ai_metrics['enabled'] = True
    orchestrator.ai_metrics['files_transformed'] = 0
    summary = orchestrator._generate_ai_summary()
    
    assert summary == "", "Summary should be empty when no files transformed"
    print("✓ No summary when no files transformed")
    
    print("\n🎉 Empty summary test passed!")


if __name__ == "__main__":
    test_ai_summary_generation()
    test_ai_summary_with_gpt4()
    test_empty_ai_summary()
    
    print("\n" + "="*60)
    print("🎊 All AI Summary Tests Passed Successfully!")
    print("="*60)
