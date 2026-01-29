"""Quick test to verify AI summary generation."""

from core.orchestration.orchestrator import MigrationOrchestrator

def test_ai_summary_generation():
    """Test AI summary with enabled flag."""
    print("\n=== Testing AI Summary Generation ===\n")
    
    orchestrator = MigrationOrchestrator()
    
    # Test 1: AI enabled with no transformations
    print("Test 1: AI enabled, no transformations")
    orchestrator.ai_metrics['enabled'] = True
    orchestrator.ai_metrics['provider'] = 'openai'
    orchestrator.ai_metrics['model'] = 'gpt-3.5-turbo'
    orchestrator.ai_metrics['files_transformed'] = 0
    
    summary = orchestrator._generate_ai_summary()
    
    if summary:
        print("✓ Summary generated")
        print(f"  Length: {len(summary)} chars")
        print(f"  Has header: {'🤖 AI TRANSFORMATION SUMMARY' in summary}")
        print(f"  Has provider: {'OpenAI' in summary}")
        print(f"  Has model: {'gpt-3.5-turbo' in summary}")
        print(f"  Has status: {'AI Ready' in summary}")
    else:
        print("✗ No summary generated!")
    
    print("\n" + "="*60)
    print(summary)
    print("="*60)
    
    # Test 2: AI enabled with transformations
    print("\n\nTest 2: AI enabled, with transformations")
    orchestrator.ai_metrics['files_transformed'] = 3
    orchestrator.ai_metrics['step_definitions_transformed'] = 2
    orchestrator.ai_metrics['page_objects_transformed'] = 1
    orchestrator.ai_metrics['total_tokens'] = 3500
    orchestrator.ai_metrics['total_cost'] = 0.007
    orchestrator.ai_metrics['transformations'] = [
        {'file': 'LoginSteps.java', 'type': 'step_definition', 'tokens': 1200, 'cost': 0.0024},
        {'file': 'HomePage.java', 'type': 'page_object', 'tokens': 1500, 'cost': 0.003},
        {'file': 'UserSteps.java', 'type': 'step_definition', 'tokens': 800, 'cost': 0.0016}
    ]
    
    summary2 = orchestrator._generate_ai_summary()
    
    if summary2:
        print("✓ Summary generated")
        print(f"  Length: {len(summary2)} chars")
        print(f"  Has stats: {'Total Files Transformed: 3' in summary2}")
        print(f"  Has tokens: {'3,500' in summary2}")
        print(f"  Has cost: {'$0.0070' in summary2}")
    else:
        print("✗ No summary generated!")
    
    print("\n" + "="*60)
    print(summary2)
    print("="*60)
    
    # Test 3: AI disabled
    print("\n\nTest 3: AI disabled")
    orchestrator2 = MigrationOrchestrator()
    orchestrator2.ai_metrics['enabled'] = False
    
    summary3 = orchestrator2._generate_ai_summary()
    
    if not summary3:
        print("✓ No summary (as expected when disabled)")
    else:
        print(f"✗ Summary generated when it shouldn't: {len(summary3)} chars")

if __name__ == '__main__':
    test_ai_summary_generation()
    print("\n\n✓ All tests completed!")
