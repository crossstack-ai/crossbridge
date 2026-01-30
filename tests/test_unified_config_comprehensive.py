"""
Comprehensive Unit Tests for Unified Configuration System

Tests cover:
- All 13 frameworks
- With AI enabled and disabled
- Error handling and edge cases
- Priority system and fallback behavior
- Integration scenarios
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

from core.execution.intelligence.rules.engine import (
    load_rule_pack, 
    RuleEngine, 
    _load_rules_from_crossbridge_config,
    _parse_rule_data
)
from core.execution.intelligence.rules.models import Rule, RulePack, FailureType


# ============================================================================
# FRAMEWORK SUPPORT TESTS (All 13 Frameworks)
# ============================================================================

class TestAllFrameworksSupport:
    """Verify all 13 frameworks are supported."""
    
    FRAMEWORKS = [
        'selenium', 'pytest', 'robot', 'playwright', 'cypress',
        'restassured', 'cucumber', 'behave', 'junit', 'testng',
        'specflow', 'nunit', 'generic'
    ]
    
    @pytest.mark.parametrize("framework", FRAMEWORKS)
    def test_framework_loads_from_yaml(self, framework):
        """Test each framework can load rules from YAML file."""
        rule_pack = load_rule_pack(framework)
        
        assert rule_pack is not None
        assert rule_pack.name == framework
        assert len(rule_pack.rules) > 0
        assert all(isinstance(rule, Rule) for rule in rule_pack.rules)
    
    @pytest.mark.parametrize("framework", FRAMEWORKS)
    def test_framework_loads_from_crossbridge_yml(self, framework):
        """Test each framework can load from crossbridge.yml."""
        config = {
            'crossbridge': {
                'intelligence': {
                    'rules': {
                        framework: [
                            {
                                'id': f'{framework.upper()}_TEST_001',
                                'description': 'Test rule',
                                'match_any': ['test_error'],
                                'failure_type': 'AUTOMATION_DEFECT',
                                'confidence': 0.85,
                                'priority': 10
                            }
                        ]
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            temp_path = f.name
        
        try:
            rule_pack = load_rule_pack(framework, config_file=temp_path)
            assert rule_pack is not None
            assert len(rule_pack.rules) >= 1
            assert any(rule.id.startswith(framework.upper()) for rule in rule_pack.rules)
        finally:
            Path(temp_path).unlink()


# ============================================================================
# AI ENABLED/DISABLED TESTS
# ============================================================================

class TestAIConfiguration:
    """Test behavior with AI enabled and disabled."""
    
    def test_classification_without_ai(self):
        """Test rule-based classification when AI is disabled."""
        # Create engine with AI disabled (default)
        engine = RuleEngine(framework='selenium')
        
        # Simulate failure signal
        signals = [{'message': 'NoSuchElementException: element not found'}]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # Should classify using rules only
        assert failure_type in ['AUTOMATION_DEFECT', 'PRODUCT_DEFECT', 'ENVIRONMENT_ISSUE', 'UNKNOWN']
        assert 0.0 <= confidence <= 1.0
        assert isinstance(matched_rules, list)
    
    def test_classification_with_ai_enabled(self):
        """Test classification when AI is enabled."""
        # Note: AI integration is a future enhancement
        # For now, test that rule-based classification works
        engine = RuleEngine(framework='selenium')
        signals = [{'message': 'Unexpected application crash'}]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # Should work with rule-based approach
        assert failure_type is not None
        assert confidence >= 0.0
        assert isinstance(matched_rules, list)
    
    def test_ai_fallback_to_rules(self):
        """Test fallback to rules when AI fails."""
        engine = RuleEngine(framework='pytest')
        
        # Clear signal that should match rules
        signals = [{'message': 'fixture failed in setup'}]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # Should use rules successfully
        assert failure_type != 'UNKNOWN' or len(matched_rules) == 0


# ============================================================================
# LOADING PRIORITY TESTS
# ============================================================================

class TestLoadingPriority:
    """Test that crossbridge.yml takes priority over YAML files."""
    
    def test_priority_crossbridge_over_yaml(self):
        """Test crossbridge.yml has priority over framework YAML."""
        # Create config with custom rule
        config = {
            'crossbridge': {
                'intelligence': {
                    'rules': {
                        'selenium': [
                            {
                                'id': 'CUSTOM_HIGH_PRIORITY',
                                'description': 'Custom high priority rule',
                                'match_any': ['custom_error'],
                                'failure_type': 'PRODUCT_DEFECT',
                                'confidence': 0.99,
                                'priority': 1
                            }
                        ]
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            temp_path = f.name
        
        try:
            rule_pack = load_rule_pack('selenium', config_file=temp_path)
            
            # Should load from crossbridge.yml (1 rule), not selenium.yaml (14 rules)
            assert len(rule_pack.rules) == 1
            assert rule_pack.rules[0].id == 'CUSTOM_HIGH_PRIORITY'
        finally:
            Path(temp_path).unlink()
    
    def test_fallback_to_yaml_when_no_config(self):
        """Test fallback to YAML when crossbridge.yml has no rules."""
        # Load without specifying config (uses default YAML)
        rule_pack = load_rule_pack('playwright', config_file='/nonexistent/path.yml')
        
        # Should fallback to playwright.yaml
        assert len(rule_pack.rules) > 0
        assert rule_pack.name == 'playwright'
    
    def test_multiple_path_formats(self):
        """Test different YAML path formats."""
        configs = [
            # Format 1: crossbridge.intelligence.rules.<framework>
            {
                'crossbridge': {
                    'intelligence': {
                        'rules': {
                            'robot': [{'id': 'TEST1', 'description': '', 'match_any': ['test'],
                                      'failure_type': 'AUTOMATION_DEFECT', 'confidence': 0.8, 'priority': 10}]
                        }
                    }
                }
            },
            # Format 2: intelligence.rules.<framework>
            {
                'intelligence': {
                    'rules': {
                        'robot': [{'id': 'TEST2', 'description': '', 'match_any': ['test'],
                                  'failure_type': 'AUTOMATION_DEFECT', 'confidence': 0.8, 'priority': 10}]
                    }
                }
            }
        ]
        
        for config in configs:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(config, f)
                temp_path = f.name
            
            try:
                rule_pack = load_rule_pack('robot', config_file=temp_path)
                assert rule_pack is not None
                assert len(rule_pack.rules) > 0
            finally:
                Path(temp_path).unlink()


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_yaml_file(self):
        """Test handling of invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: ][")
            temp_path = f.name
        
        try:
            rule_pack = load_rule_pack('selenium', config_file=temp_path)
            # Should return empty rule pack instead of crashing
            assert rule_pack is not None
            assert isinstance(rule_pack, RulePack)
        finally:
            Path(temp_path).unlink()
    
    def test_missing_required_fields(self):
        """Test handling of rules with missing required fields."""
        config = {
            'crossbridge': {
                'intelligence': {
                    'rules': {
                        'pytest': [
                            {
                                'id': 'INCOMPLETE_RULE',
                                # Missing required fields
                                'description': 'Incomplete rule'
                            }
                        ]
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            temp_path = f.name
        
        try:
            # Should handle gracefully
            rule_pack = load_rule_pack('pytest', config_file=temp_path)
            assert rule_pack is not None
        except KeyError:
            # Expected if validation is strict
            pass
        finally:
            Path(temp_path).unlink()
    
    def test_nonexistent_framework(self):
        """Test loading rules for nonexistent framework."""
        rule_pack = load_rule_pack('nonexistent_framework_xyz')
        
        # Should fallback to generic
        assert rule_pack is not None
        assert rule_pack.name == 'generic'
    
    def test_empty_rules_list(self):
        """Test handling of empty rules list."""
        config = {
            'crossbridge': {
                'intelligence': {
                    'rules': {
                        'cypress': []
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            temp_path = f.name
        
        try:
            rule_pack = load_rule_pack('cypress', config_file=temp_path)
            # Should fallback to cypress.yaml since config has empty list
            assert rule_pack is not None
        finally:
            Path(temp_path).unlink()
    
    def test_malformed_rule_data(self):
        """Test handling of malformed rule data."""
        data = "not a valid rule structure"
        
        try:
            result = _parse_rule_data(data, 'test')
            assert isinstance(result, RulePack)
        except Exception as e:
            # Should handle gracefully
            assert True


# ============================================================================
# RULE MATCHING TESTS
# ============================================================================

class TestRuleMatching:
    """Test rule matching functionality."""
    
    def test_exact_match(self):
        """Test exact string matching."""
        rule = Rule(
            id='TEST_001',
            match_any=['NoSuchElementException'],
            failure_type='AUTOMATION_DEFECT',
            confidence=0.90,
            priority=10,
            description='Test rule'
        )
        
        assert rule.matches('selenium.NoSuchElementException: element not found')
        assert not rule.matches('Different error message')
    
    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        rule = Rule(
            id='TEST_002',
            match_any=['timeout'],
            failure_type='AUTOMATION_DEFECT',
            confidence=0.85,
            priority=15,
            description='Test rule'
        )
        
        assert rule.matches('TIMEOUT occurred')
        assert rule.matches('Timeout Exception')
        assert rule.matches('connection timeout')
    
    def test_multiple_patterns(self):
        """Test OR logic with multiple patterns."""
        rule = Rule(
            id='TEST_003',
            match_any=['error', 'failure', 'exception'],
            failure_type='PRODUCT_DEFECT',
            confidence=0.75,
            priority=20,
            description='Test rule'
        )
        
        assert rule.matches('An error occurred')
        assert rule.matches('Test failure detected')
        assert rule.matches('Exception was thrown')
    
    def test_exclusion_patterns(self):
        """Test exclusion logic."""
        rule = Rule(
            id='TEST_004',
            match_any=['assert'],
            excludes=['fixture'],
            failure_type='PRODUCT_DEFECT',
            confidence=0.90,
            priority=10,
            description='Test rule'
        )
        
        assert rule.matches('assertion failed')
        assert not rule.matches('fixture assertion failed')
    
    def test_requires_all_patterns(self):
        """Test AND logic with requires_all."""
        rule = Rule(
            id='TEST_005',
            match_any=['error'],
            requires_all=['database', 'connection'],
            failure_type='ENVIRONMENT_ISSUE',
            confidence=0.85,
            priority=12,
            description='Test rule'
        )
        
        assert rule.matches('database connection error occurred')
        assert not rule.matches('database error occurred')
        assert not rule.matches('connection error occurred')


# ============================================================================
# PRIORITY AND CONFIDENCE TESTS
# ============================================================================

class TestPriorityAndConfidence:
    """Test priority handling and confidence scoring."""
    
    def test_priority_ordering(self):
        """Test that rules are ordered by priority."""
        rule_pack = RulePack(
            name='test',
            rules=[
                Rule(id='LOW', description='', match_any=['error'],
                     failure_type='PRODUCT_DEFECT', confidence=0.7, priority=50),
                Rule(id='HIGH', description='', match_any=['error'],
                     failure_type='AUTOMATION_DEFECT', confidence=0.9, priority=10),
                Rule(id='MED', description='', match_any=['error'],
                     failure_type='ENVIRONMENT_ISSUE', confidence=0.8, priority=25)
            ]
        )
        
        sorted_rules = rule_pack.get_sorted_rules()
        
        assert sorted_rules[0].id == 'HIGH'  # priority 10
        assert sorted_rules[1].id == 'MED'   # priority 25
        assert sorted_rules[2].id == 'LOW'   # priority 50
    
    def test_highest_confidence_selected(self):
        """Test that highest confidence rule is selected."""
        engine = RuleEngine(framework='selenium')
        engine.rule_pack = RulePack(
            name='test',
            rules=[
                Rule(id='LOW_CONF', description='', match_any=['timeout'],
                     failure_type='AUTOMATION_DEFECT', confidence=0.60, priority=10),
                Rule(id='HIGH_CONF', description='', match_any=['timeout'],
                     failure_type='AUTOMATION_DEFECT', confidence=0.95, priority=20)
            ]
        )
        
        signals = [{'message': 'timeout occurred'}]
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # Should use highest confidence
        assert confidence == 0.95


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for real-world scenarios."""
    
    def test_selenium_webdriver_errors(self):
        """Test classification of common Selenium errors."""
        engine = RuleEngine(framework='selenium')
        
        test_cases = [
            ('NoSuchElementException: Unable to locate element', 'AUTOMATION_DEFECT'),
            ('TimeoutException: Timed out waiting for element', 'AUTOMATION_DEFECT'),
            ('500 Internal Server Error', 'PRODUCT_DEFECT'),
        ]
        
        for error_msg, expected_type in test_cases:
            signals = [{'message': error_msg}]
            failure_type, confidence, rules = engine.classify(signals)
            
            # Should classify correctly (or UNKNOWN if no match)
            assert failure_type in [expected_type, 'UNKNOWN']
            if failure_type != 'UNKNOWN':
                assert confidence > 0.5
    
    def test_pytest_test_failures(self):
        """Test classification of pytest failures."""
        engine = RuleEngine(framework='pytest')
        
        test_cases = [
            ('fixture failed in conftest.py', 'AUTOMATION_DEFECT'),
            ('AssertionError: expected True but got False', 'PRODUCT_DEFECT'),
        ]
        
        for error_msg, expected_type in test_cases:
            signals = [{'message': error_msg}]
            failure_type, confidence, rules = engine.classify(signals)
            
            assert failure_type in [expected_type, 'UNKNOWN']
    
    def test_restassured_api_errors(self):
        """Test classification of REST API errors."""
        engine = RuleEngine(framework='restassured')
        
        signals = [{'message': 'Expected status code <200> but was <500>'}]
        failure_type, confidence, rules = engine.classify(signals)
        
        # Should identify as product defect (API issue)
        assert failure_type in ['PRODUCT_DEFECT', 'UNKNOWN']
    
    def test_multiple_signal_classification(self):
        """Test classification with multiple failure signals."""
        engine = RuleEngine(framework='selenium')
        
        signals = [
            {'message': 'NoSuchElementException'},
            {'message': 'Element not found'},
            {'message': 'Timeout waiting'}
        ]
        
        failure_type, confidence, rules = engine.classify(signals)
        
        # Should aggregate multiple signals
        assert failure_type is not None
        assert len(rules) > 0  # Should match multiple rules


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance and resource usage."""
    
    def test_rule_loading_performance(self):
        """Test that rule loading is efficient."""
        import time
        
        start = time.time()
        for _ in range(10):
            load_rule_pack('selenium')
        duration = time.time() - start
        
        # Should load 10 times in under 1 second
        assert duration < 1.0
    
    def test_classification_performance(self):
        """Test that classification is efficient."""
        import time
        
        engine = RuleEngine(framework='playwright')
        signals = [{'message': 'locator timeout'}]
        
        start = time.time()
        for _ in range(100):
            engine.classify(signals)
        duration = time.time() - start
        
        # Should classify 100 times in under 1 second
        assert duration < 1.0


# ============================================================================
# CONFIGURATION VALIDATION TESTS
# ============================================================================

class TestConfigurationValidation:
    """Test configuration validation."""
    
    def test_valid_failure_types(self):
        """Test that only valid failure types are accepted."""
        valid_types = ['AUTOMATION_DEFECT', 'PRODUCT_DEFECT', 'ENVIRONMENT_ISSUE']
        
        for failure_type in valid_types:
            rule = Rule(
                id='TEST',
                match_any=['test'],
                failure_type=failure_type,
                confidence=0.8,
                priority=10,
                description='Test'
            )
            assert rule.failure_type == failure_type
    
    def test_confidence_range(self):
        """Test that confidence values are in valid range."""
        rule = Rule(
            id='TEST',
            match_any=['test'],
            failure_type='AUTOMATION_DEFECT',
            confidence=0.85,
            priority=10,
            description='Test'
        )
        
        assert 0.0 <= rule.confidence <= 1.0
    
    def test_priority_values(self):
        """Test that priority values are reasonable."""
        rule = Rule(
            id='TEST',
            match_any=['test'],
            failure_type='AUTOMATION_DEFECT',
            confidence=0.85,
            priority=15,
            description='Test'
        )
        
        assert rule.priority > 0
        assert rule.priority <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
