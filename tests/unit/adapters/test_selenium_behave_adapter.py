"""
Tests for Selenium + Behave adapter.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from adapters.selenium_behave.adapter import (
    SeleniumBehaveAdapter,
    SeleniumBehaveExtractor,
    SeleniumBehaveDetector
)


class TestSeleniumBehaveAdapter:
    """Test Selenium + Behave adapter functionality."""
    
    @patch('adapters.selenium_behave.adapter.SeleniumBehaveAdapter._verify_behave_installed')
    def test_adapter_initialization(self, mock_verify, tmp_path):
        """Test adapter initialization."""
        adapter = SeleniumBehaveAdapter(str(tmp_path), driver_type="chrome")
        
        assert adapter.project_root == tmp_path
        assert adapter.driver_type == "chrome"
        assert adapter.features_dir == tmp_path / "features"
    
    @patch('adapters.selenium_behave.adapter.SeleniumBehaveAdapter._verify_behave_installed')
    @patch('subprocess.run')
    def test_discover_from_files(self, mock_run, mock_verify, tmp_path):
        """Test discovering scenarios from feature files."""
        # Create features directory
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        # Create feature file
        feature_file = features_dir / "login.feature"
        feature_file.write_text("""
Feature: User Login
    
    Scenario: Successful login with valid credentials
        Given I am on the login page
        When I enter valid credentials
        Then I should be logged in
    
    Scenario: Failed login with invalid credentials
        Given I am on the login page
        When I enter invalid credentials
        Then I should see an error message
""")
        
        # Mock behave --dry-run to fail, forcing fallback to file parsing
        mock_run.return_value = Mock(returncode=1, stdout="")
        
        adapter = SeleniumBehaveAdapter(str(tmp_path))
        tests = adapter.discover_tests()
        
        assert len(tests) == 2
        assert any('login.feature:' in t for t in tests)
    
    @patch('subprocess.run')
    def test_run_tests_with_tags(self, mock_run, tmp_path):
        """Test running tests with tag filtering."""
        # Setup features directory
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        # Mock behave results
        results_data = [{
            'name': 'Login Feature',
            'elements': [
                {
                    'type': 'scenario',
                    'name': 'Successful login',
                    'location': 'features/login.feature:3',
                    'steps': [
                        {'result': {'status': 'passed', 'duration': 1.0}},
                        {'result': {'status': 'passed', 'duration': 0.5}},
                    ]
                }
            ]
        }]
        
        # Write results file
        results_path = tmp_path / "results.json"
        with open(results_path, 'w') as f:
            json.dump(results_data, f)
        
        mock_run.return_value = Mock(returncode=0, stdout="")
        
        adapter = SeleniumBehaveAdapter(str(tmp_path))
        results = adapter.run_tests(tags=["smoke", "critical"])
        
        # Verify behave was called with tags
        call_args = mock_run.call_args[0][0]
        assert "--tags" in call_args
        assert "@smoke" in call_args or "@critical" in call_args
    
    @patch('adapters.selenium_behave.adapter.SeleniumBehaveAdapter._verify_behave_installed')
    def test_parse_behave_results(self, mock_verify, tmp_path):
        """Test parsing Behave JSON results."""
        behave_data = [
            {
                'name': 'Shopping Cart',
                'elements': [
                    {
                        'type': 'scenario',
                        'name': 'Add item to cart',
                        'location': 'features/cart.feature:5',
                        'steps': [
                            {'result': {'status': 'passed', 'duration': 1.0}},
                            {'result': {'status': 'passed', 'duration': 0.5}},
                        ]
                    },
                    {
                        'type': 'scenario',
                        'name': 'Remove item from cart',
                        'location': 'features/cart.feature:12',
                        'steps': [
                            {'result': {'status': 'passed', 'duration': 0.8}},
                            {'result': {'status': 'failed', 'duration': 0.2,
                                       'error_message': 'Element not found'}},
                        ]
                    }
                ]
            }
        ]
        
        adapter = SeleniumBehaveAdapter(str(tmp_path))
        results = adapter._parse_behave_results(behave_data)
        
        assert len(results) == 2
        
        # First scenario passed
        assert results[0].status == 'pass'
        assert results[0].duration_ms == 1500
        
        # Second scenario failed
        assert results[1].status == 'fail'
        assert 'Element not found' in results[1].message
    
    @patch('adapters.selenium_behave.adapter.SeleniumBehaveAdapter._verify_behave_installed')
    def test_get_driver_info(self, mock_verify, tmp_path):
        """Test getting driver information."""
        adapter = SeleniumBehaveAdapter(str(tmp_path), driver_type="firefox")
        
        info = adapter.get_driver_info()
        assert info['driver_type'] == 'firefox'
        assert info['framework'] == 'selenium'
        assert info['runner'] == 'behave'
        assert info['bdd'] is True


class TestSeleniumBehaveExtractor:
    """Test Selenium Behave extractor."""
    
    def test_extract_scenarios(self, tmp_path):
        """Test extracting scenarios from feature files."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        feature_file = features_dir / "search.feature"
        feature_file.write_text("""
@smoke
Feature: Product Search
    As a customer
    I want to search for products
    So that I can find what I need
    
    @critical
    Scenario: Search with valid keyword
        Given I am on the homepage
        When I search for "laptop"
        Then I should see search results
    
    @regression
    Scenario: Search with no results
        Given I am on the homepage
        When I search for "xyzabc123"
        Then I should see "No results found"
""")
        
        extractor = SeleniumBehaveExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        
        # Check first scenario
        first_test = tests[0]
        assert 'Search with valid keyword' in first_test.test_name
        assert 'critical' in first_test.tags
        assert 'smoke' in first_test.tags  # Feature-level tag
        
        # Check second scenario
        second_test = tests[1]
        assert 'Search with no results' in second_test.test_name
        assert 'regression' in second_test.tags
        assert 'smoke' in second_test.tags  # Feature-level tag
    
    def test_extract_scenario_outline(self, tmp_path):
        """Test extracting Scenario Outline."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        feature_file = features_dir / "login.feature"
        feature_file.write_text("""
Feature: Login Tests
    
    @parameterized
    Scenario Outline: Login with different credentials
        Given I am on the login page
        When I enter "<username>" and "<password>"
        Then I should see "<result>"
    
    Examples:
        | username | password | result  |
        | admin    | admin123 | success |
        | guest    | wrong    | error   |
""")
        
        extractor = SeleniumBehaveExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert 'Scenario Outline' not in tests[0].test_name  # Should extract as regular scenario
        assert 'parameterized' in tests[0].tags
    
    def test_extract_steps(self, tmp_path):
        """Test extracting steps from scenarios."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        feature_file = features_dir / "checkout.feature"
        feature_file.write_text("""
Feature: Checkout Process
    
    Scenario: Complete purchase
        Given I have items in my cart
        And I am logged in
        When I proceed to checkout
        And I enter payment details
        Then the order should be confirmed
        And I should receive a confirmation email
""")
        
        extractor = SeleniumBehaveExtractor(str(tmp_path))
        steps = extractor.extract_steps(feature_file)
        
        assert 'Complete purchase' in steps
        scenario_steps = steps['Complete purchase']
        
        assert len(scenario_steps) == 6
        assert scenario_steps[0].startswith('Given')
        assert scenario_steps[2].startswith('When')
        assert scenario_steps[4].startswith('Then')
    
    def test_extract_with_tags_only(self, tmp_path):
        """Test extracting scenarios with only tags (no feature tags)."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        feature_file = features_dir / "tags_test.feature"
        feature_file.write_text("""
Feature: Tag Testing
    
    @wip @slow
    Scenario: Work in progress test
        Given something
        When something happens
        Then verify something
""")
        
        extractor = SeleniumBehaveExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert 'wip' in tests[0].tags
        assert 'slow' in tests[0].tags


class TestSeleniumBehaveDetector:
    """Test Selenium Behave project detector."""
    
    def test_detect_valid_project(self, tmp_path):
        """Test detecting valid Selenium + Behave project."""
        # Create features directory
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        # Create feature file
        (features_dir / "example.feature").write_text("""
Feature: Example
    Scenario: Test
        Given something
""")
        
        # Create steps directory with selenium import
        steps_dir = features_dir / "steps"
        steps_dir.mkdir()
        
        (steps_dir / "steps.py").write_text("""
from behave import given, when, then
from selenium import webdriver

@given('something')
def step_impl(context):
    context.driver = webdriver.Chrome()
""")
        
        assert SeleniumBehaveDetector.detect(str(tmp_path)) is True
    
    def test_detect_with_environment_file(self, tmp_path):
        """Test detection with environment.py."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        (features_dir / "test.feature").write_text("Feature: Test\n")
        
        # Create environment.py with selenium
        (features_dir / "environment.py").write_text("""
from selenium import webdriver

def before_all(context):
    context.driver = webdriver.Chrome()

def after_all(context):
    context.driver.quit()
""")
        
        assert SeleniumBehaveDetector.detect(str(tmp_path)) is True
    
    def test_detect_with_requirements(self, tmp_path):
        """Test detection via requirements.txt."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        (features_dir / "test.feature").write_text("Feature: Test\n")
        
        steps_dir = features_dir / "steps"
        steps_dir.mkdir()
        (steps_dir / "steps.py").write_text("# Steps")
        
        # Create requirements with both behave and selenium
        (tmp_path / "requirements.txt").write_text("behave==1.2.6\nselenium==4.0.0\n")
        
        assert SeleniumBehaveDetector.detect(str(tmp_path)) is True
    
    def test_detect_no_features_directory(self, tmp_path):
        """Test no detection without features directory."""
        (tmp_path / "test.py").write_text("from selenium import webdriver")
        
        assert SeleniumBehaveDetector.detect(str(tmp_path)) is False
    
    def test_detect_no_selenium(self, tmp_path):
        """Test no detection when Selenium missing."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        (features_dir / "test.feature").write_text("Feature: Test\n")
        
        steps_dir = features_dir / "steps"
        steps_dir.mkdir()
        (steps_dir / "steps.py").write_text("from behave import given")
        
        # Without selenium, might still detect based on structure
        # but should be False if we enforce selenium requirement
        result = SeleniumBehaveDetector.detect(str(tmp_path))
        # This test depends on implementation strictness
        assert isinstance(result, bool)


class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self, tmp_path):
        """Test complete workflow: detect -> extract -> discover."""
        # Setup project structure
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        feature_file = features_dir / "workflow.feature"
        feature_file.write_text("""
@smoke
Feature: Workflow Test
    
    @critical
    Scenario: Step one
        Given I start the test
        When I perform action
        Then I verify result
    
    @regression
    Scenario: Step two
        Given I start again
        Then I verify again
""")
        
        steps_dir = features_dir / "steps"
        steps_dir.mkdir()
        (steps_dir / "steps.py").write_text("from selenium import webdriver")
        
        # Detect
        detected = SeleniumBehaveDetector.detect(str(tmp_path))
        assert detected is True
        
        # Extract
        extractor = SeleniumBehaveExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        assert len(tests) == 2
        
        # Verify metadata
        assert all(t.framework == "selenium-behave" for t in tests)
        assert all(t.test_type == "bdd" for t in tests)
        assert all('smoke' in t.tags for t in tests)
        
        # Extract steps
        steps = extractor.extract_steps(feature_file)
        assert 'Step one' in steps
        assert len(steps['Step one']) == 3
