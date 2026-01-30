"""
Demonstration: Unified Configuration in Action

This demonstrates how Crossbridge now loads framework rules directly from
crossbridge.yml instead of requiring separate YAML files.
"""

import logging
from core.execution.intelligence.rules.engine import load_rule_pack, RuleEngine
from pathlib import Path

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')


def demo_unified_configuration():
    """Demonstrate unified configuration loading"""
    
    print("=" * 80)
    print("Crossbridge Unified Configuration Demo")
    print("=" * 80)
    print()
    
    # Check if crossbridge.yml exists
    config_path = Path("crossbridge.yml")
    if not config_path.exists():
        print("[X] crossbridge.yml not found in current directory")
        return
    
    print(f"[OK] Found configuration: {config_path.absolute()}")
    print()
    
    # Demonstrate loading rules for different frameworks
    frameworks = ['selenium', 'pytest', 'robot']
    
    print("-" * 80)
    print("Loading Framework Rules from crossbridge.yml")
    print("-" * 80)
    print()
    
    for framework in frameworks:
        print(f"Framework: {framework}")
        print("-" * 40)
        
        try:
            # Load rule pack - automatically uses crossbridge.yml first
            rule_pack = load_rule_pack(framework)
            
            print(f"  [OK] Loaded {len(rule_pack.rules)} rules")
            print(f"  Source: crossbridge.yml -> execution.intelligence.rules.{framework}")
            
            # Show first 3 rules
            if rule_pack.rules:
                print(f"\n  Sample Rules:")
                for rule in rule_pack.rules[:3]:
                    print(f"    * {rule.id}: {rule.description}")
                    patterns = ', '.join(rule.match_any[:2])
                    if len(rule.match_any) > 2:
                        patterns += '...'
                    print(f"      Patterns: {patterns}")
                    print(f"      Type: {rule.failure_type} | Confidence: {rule.confidence}")
                if len(rule_pack.rules) > 3:
                    print(f"    ... and {len(rule_pack.rules) - 3} more rules")
            
            print()
            
        except Exception as e:
            print(f"  [ERROR] Error loading {framework}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    
    # Demonstrate rule matching
    print("─" * 80)
    print("Testing Rule Matching")
    print("─" * 80)
    print()
    
    # Create rule engine for Selenium
    engine = RuleEngine(framework='selenium')
    
    test_errors = [
        ("NoSuchElementException: Unable to locate element", "SEL_001"),
        ("TimeoutException: Timed out waiting for element", "SEL_002"),
        ("500 Internal Server Error from backend", "SEL_PROD_001"),
    ]
    
    for error_msg, expected_rule_id in test_errors:
        print(f"Error: {error_msg[:60]}...")
        
        # Create mock signal
        class MockSignal:
            def __init__(self, message):
                self.message = message
        
        signals = [MockSignal(error_msg)]
        matched_rules = engine.apply_rules(signals)
        
        if matched_rules:
            rule = matched_rules[0]
            match_indicator = "✓" if rule.id.startswith(expected_rule_id[:3]) else "?"
            print(f"  {match_indicator} Matched: {rule.id} - {rule.description}")
            print(f"    Classification: {rule.failure_type}")
            print(f"    Confidence: {rule.confidence * 100:.0f}%")
        else:
            print(f"  ⚠ No rule matched")
        
        print()
    
    # Show configuration benefits
    print("─" * 80)
    print("Benefits of Unified Configuration")
    print("─" * 80)
    print()
    print("Before (13 separate files):")
    print("  ├── rules/selenium.yaml")
    print("  ├── rules/pytest.yaml")
    print("  ├── rules/robot.yaml")
    print("  └── ... (10 more files)")
    print("  ❓ Users confused: 'Which file do I edit?'")
    print()
    print("After (single configuration):")
    print("  └── crossbridge.yml")
    print("      └── execution.intelligence.rules.<framework>")
    print("  ✓ Clear: 'Just edit crossbridge.yml'")
    print()
    print("Key Features:")
    print("  ✓ Single source of truth")
    print("  ✓ Automatic framework detection based on execution.framework")
    print("  ✓ Backward compatible with individual YAML files")
    print("  ✓ Easy to manage and version control")
    print()
    
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("  1. Edit crossbridge.yml to customize rules for your frameworks")
    print("  2. Run: crossbridge run --framework <your_framework>")
    print("  3. See: UNIFIED_CONFIGURATION_GUIDE.md for detailed documentation")
    print()


if __name__ == '__main__':
    demo_unified_configuration()
