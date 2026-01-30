"""
Test unified rule configuration loading from crossbridge.yml

Tests that rules can be loaded from:
1. crossbridge.yml (execution.intelligence.rules.<framework>)
2. Framework-specific YAML files (fallback)
3. Generic rules (final fallback)
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from core.execution.intelligence.rules.engine import load_rule_pack, _load_rules_from_crossbridge_config


def test_load_rules_from_crossbridge_yml():
    """Test loading rules from crossbridge.yml"""
    
    # Create temporary crossbridge.yml with rules
    config_content = {
        'execution': {
            'framework': 'selenium',
            'intelligence': {
                'rules': {
                    'selenium': [
                        {
                            'id': 'TEST_001',
                            'description': 'Test rule',
                            'match_any': ['NoSuchElementException'],
                            'failure_type': 'AUTOMATION_DEFECT',
                            'confidence': 0.90,
                            'priority': 10
                        },
                        {
                            'id': 'TEST_002',
                            'description': 'Another test rule',
                            'match_any': ['TimeoutException'],
                            'failure_type': 'AUTOMATION_DEFECT',
                            'confidence': 0.85,
                            'priority': 15
                        }
                    ]
                }
            }
        }
    }
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_content, f)
        temp_path = f.name
    
    try:
        # Load rules
        rule_pack = _load_rules_from_crossbridge_config('selenium', temp_path)
        
        # Assertions
        assert rule_pack is not None, "Rule pack should be loaded"
        assert rule_pack.name == 'selenium', f"Expected framework 'selenium', got '{rule_pack.name}'"
        assert len(rule_pack.rules) == 2, f"Expected 2 rules, got {len(rule_pack.rules)}"
        
        # Check first rule
        rule1 = rule_pack.rules[0]
        assert rule1.id == 'TEST_001'
        assert rule1.description == 'Test rule'
        assert 'NoSuchElementException' in rule1.match_any
        assert rule1.failure_type == 'AUTOMATION_DEFECT'
        assert rule1.confidence == 0.90
        assert rule1.priority == 10
        
        # Check second rule
        rule2 = rule_pack.rules[1]
        assert rule2.id == 'TEST_002'
        assert 'TimeoutException' in rule2.match_any
        
        print("✓ Successfully loaded rules from crossbridge.yml")
        return True
        
    finally:
        # Cleanup
        Path(temp_path).unlink()


def test_load_rules_priority_system():
    """Test that crossbridge.yml has priority over YAML files"""
    
    # Create temporary crossbridge.yml with custom rules
    config_content = {
        'execution': {
            'intelligence': {
                'rules': {
                    'selenium': [
                        {
                            'id': 'CUSTOM_001',
                            'description': 'Custom rule from config',
                            'match_any': ['CustomException'],
                            'failure_type': 'AUTOMATION_DEFECT',
                            'confidence': 0.95,
                            'priority': 5
                        }
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_content, f)
        temp_path = f.name
    
    try:
        # Load rules with config file specified
        rule_pack = load_rule_pack('selenium', config_file=temp_path)
        
        # Should load from crossbridge.yml (custom rule)
        assert rule_pack is not None
        assert len(rule_pack.rules) >= 1
        
        # Check if custom rule is loaded
        custom_rule = next((r for r in rule_pack.rules if r.id == 'CUSTOM_001'), None)
        assert custom_rule is not None, "Custom rule should be loaded from crossbridge.yml"
        assert custom_rule.description == 'Custom rule from config'
        
        print("✓ Priority system working: crossbridge.yml takes precedence")
        return True
        
    finally:
        Path(temp_path).unlink()


def test_fallback_to_yaml_file():
    """Test fallback to framework-specific YAML when crossbridge.yml has no rules"""
    
    # Load without config file (should fallback to selenium.yaml if it exists)
    rule_pack = load_rule_pack('selenium', config_file='/nonexistent/path.yml')
    
    # Should fallback to selenium.yaml or generic.yaml
    assert rule_pack is not None
    assert rule_pack.name in ['selenium', 'generic']
    
    print(f"✓ Fallback working: loaded rules from {rule_pack.name}")
    return True


def test_multiple_frameworks():
    """Test loading rules for different frameworks from same config"""
    
    config_content = {
        'execution': {
            'intelligence': {
                'rules': {
                    'selenium': [
                        {
                            'id': 'SEL_001',
                            'description': 'Selenium rule',
                            'match_any': ['NoSuchElementException'],
                            'failure_type': 'AUTOMATION_DEFECT',
                            'confidence': 0.90,
                            'priority': 10
                        }
                    ],
                    'pytest': [
                        {
                            'id': 'PYT_001',
                            'description': 'Pytest rule',
                            'match_any': ['fixture'],
                            'failure_type': 'AUTOMATION_DEFECT',
                            'confidence': 0.85,
                            'priority': 15
                        }
                    ],
                    'robot': [
                        {
                            'id': 'ROB_001',
                            'description': 'Robot rule',
                            'match_any': ['Keyword'],
                            'failure_type': 'AUTOMATION_DEFECT',
                            'confidence': 0.88,
                            'priority': 12
                        }
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_content, f)
        temp_path = f.name
    
    try:
        # Load rules for different frameworks
        selenium_pack = load_rule_pack('selenium', config_file=temp_path)
        pytest_pack = load_rule_pack('pytest', config_file=temp_path)
        robot_pack = load_rule_pack('robot', config_file=temp_path)
        
        # Verify each framework loads its own rules
        assert selenium_pack.rules[0].id == 'SEL_001'
        assert pytest_pack.rules[0].id == 'PYT_001'
        assert robot_pack.rules[0].id == 'ROB_001'
        
        print("✓ Multiple frameworks: Each framework loads its own rules")
        return True
        
    finally:
        Path(temp_path).unlink()


def test_rule_matching():
    """Test that loaded rules can match error messages"""
    
    config_content = {
        'execution': {
            'intelligence': {
                'rules': {
                    'selenium': [
                        {
                            'id': 'SEL_ELEMENT',
                            'description': 'Element not found',
                            'match_any': ['NoSuchElementException', 'element not found'],
                            'failure_type': 'AUTOMATION_DEFECT',
                            'confidence': 0.90,
                            'priority': 10
                        }
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_content, f)
        temp_path = f.name
    
    try:
        rule_pack = load_rule_pack('selenium', config_file=temp_path)
        
        # Test matching
        test_messages = [
            "selenium.common.exceptions.NoSuchElementException: Unable to locate element",
            "Error: element not found on page",
            "Timeout waiting for element"  # Should not match
        ]
        
        rule = rule_pack.rules[0]
        
        # Should match first two messages
        assert rule.matches(test_messages[0]), "Should match NoSuchElementException"
        assert rule.matches(test_messages[1]), "Should match 'element not found'"
        assert not rule.matches(test_messages[2]), "Should not match timeout message"
        
        print("✓ Rule matching: Rules correctly identify error patterns")
        return True
        
    finally:
        Path(temp_path).unlink()


if __name__ == '__main__':
    """Run tests directly"""
    print("\n" + "=" * 70)
    print("Testing Unified Configuration - Rule Loading from crossbridge.yml")
    print("=" * 70 + "\n")
    
    tests = [
        ("Load rules from crossbridge.yml", test_load_rules_from_crossbridge_yml),
        ("Priority system (config > YAML)", test_load_rules_priority_system),
        ("Fallback to YAML files", test_fallback_to_yaml_file),
        ("Multiple frameworks support", test_multiple_frameworks),
        ("Rule matching functionality", test_rule_matching)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 70)
        try:
            success = test_func()
            results.append((test_name, "✓ PASSED" if success else "✗ FAILED"))
        except Exception as e:
            print(f"✗ FAILED: {e}")
            results.append((test_name, f"✗ FAILED: {str(e)}"))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    for test_name, result in results:
        print(f"{result:12} {test_name}")
    
    passed = sum(1 for _, r in results if "PASSED" in r)
    total = len(results)
    print(f"\nResults: {passed}/{total} tests passed")
    print("=" * 70 + "\n")
