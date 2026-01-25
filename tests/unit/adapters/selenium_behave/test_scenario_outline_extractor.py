"""
Tests for scenario outline extractor.
"""

import pytest
from pathlib import Path
from adapters.selenium_behave.scenario_outline_extractor import BehaveScenarioOutlineExtractor


@pytest.fixture
def extractor():
    return BehaveScenarioOutlineExtractor()


@pytest.fixture
def sample_feature_file(tmp_path):
    """Create a sample feature file with scenario outline."""
    feature_file = tmp_path / "login.feature"
    feature_file.write_text("""
Feature: User Login

  @smoke @regression
  Scenario Outline: Login with different credentials
    Given I am on the login page
    When I enter username "<username>"
    And I enter password "<password>"
    And I click the login button
    Then I should see "<result>"

    @valid
    Examples: Valid Credentials
      | username | password | result          |
      | admin    | admin123 | Welcome Admin   |
      | user1    | pass456  | Welcome User1   |

    @invalid
    Examples: Invalid Credentials
      | username | password | result               |
      | invalid  | wrong    | Invalid credentials  |
      | empty    |          | Password required    |
    """)
    return feature_file


def test_extract_scenario_outlines(extractor, sample_feature_file):
    """Test extraction of scenario outlines."""
    outlines = extractor.extract_scenario_outlines(sample_feature_file)
    
    assert len(outlines) == 1
    outline = outlines[0]
    
    assert outline.name == "Login with different credentials"
    assert len(outline.tags) >= 2  # @smoke @regression
    assert len(outline.steps) == 5
    assert len(outline.examples) == 2


def test_extract_examples_tables(extractor, sample_feature_file):
    """Test extraction of Examples tables."""
    outlines = extractor.extract_scenario_outlines(sample_feature_file)
    outline = outlines[0]
    
    # First examples table
    valid_examples = outline.examples[0]
    assert valid_examples.name == "Valid Credentials"
    assert valid_examples.headers == ['username', 'password', 'result']
    assert len(valid_examples.rows) == 2
    assert '@valid' in valid_examples.tags
    
    # Second examples table
    invalid_examples = outline.examples[1]
    assert invalid_examples.name == "Invalid Credentials"
    assert len(invalid_examples.rows) == 2
    assert '@invalid' in invalid_examples.tags


def test_extract_steps_with_placeholders(extractor, sample_feature_file):
    """Test extraction of steps with placeholders."""
    outlines = extractor.extract_scenario_outlines(sample_feature_file)
    outline = outlines[0]
    
    # Find step with placeholder
    username_step = next(
        (s for s in outline.steps if 'username' in s['text']),
        None
    )
    
    assert username_step is not None
    assert '<username>' in username_step['text']
    assert 'username' in username_step['placeholders']


def test_get_total_test_cases(extractor, sample_feature_file):
    """Test calculation of total test cases."""
    outlines = extractor.extract_scenario_outlines(sample_feature_file)
    outline = outlines[0]
    
    total = extractor.get_total_test_cases(outline)
    assert total == 4  # 2 valid + 2 invalid


def test_expand_outline(extractor, sample_feature_file):
    """Test expansion of outline into individual test cases."""
    outlines = extractor.extract_scenario_outlines(sample_feature_file)
    outline = outlines[0]
    
    test_cases = extractor.expand_outline(outline)
    
    assert len(test_cases) == 4
    
    # Check first test case
    first_case = test_cases[0]
    assert 'admin' in first_case['steps'][1]['text']  # Username step
    assert 'admin123' in first_case['steps'][2]['text']  # Password step
    assert first_case['parameters']['username'] == 'admin'


def test_scenario_outline_without_examples(extractor, tmp_path):
    """Test scenario outline without examples."""
    feature_file = tmp_path / "incomplete.feature"
    feature_file.write_text("""
Feature: Incomplete

  Scenario Outline: Test without examples
    Given I have <count> items
    When I add one more
    Then I should have <total> items
    """)
    
    outlines = extractor.extract_scenario_outlines(feature_file)
    
    assert len(outlines) == 1
    assert len(outlines[0].examples) == 0


def test_multiple_placeholders_in_step(extractor, tmp_path):
    """Test step with multiple placeholders."""
    feature_file = tmp_path / "multi_placeholder.feature"
    feature_file.write_text("""
Feature: Multiple Placeholders

  Scenario Outline: Test with multiple placeholders
    Given I have "<item1>" and "<item2>" and "<item3>"
    
    Examples:
      | item1 | item2 | item3 |
      | apple | banana | cherry |
    """)
    
    outlines = extractor.extract_scenario_outlines(feature_file)
    outline = outlines[0]
    
    step = outline.steps[0]
    assert len(step['placeholders']) == 3
    assert 'item1' in step['placeholders']
    assert 'item2' in step['placeholders']
    assert 'item3' in step['placeholders']
