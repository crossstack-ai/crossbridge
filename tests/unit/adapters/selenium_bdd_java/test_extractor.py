"""
Unit tests for Selenium BDD Java extractor.

Tests cover:
- Feature file parsing
- Scenario extraction
- Scenario Outline extraction
- Tag handling (feature-level and scenario-level)
- Multiple feature files
- Edge cases
"""

import pytest
from pathlib import Path
from adapters.selenium_bdd_java.extractor import SeleniumBDDJavaExtractor
from adapters.selenium_bdd_java.config import SeleniumBDDJavaConfig


@pytest.fixture
def temp_features_dir(tmp_path):
    """Create a temporary features directory."""
    features_dir = tmp_path / "features"
    features_dir.mkdir()
    return features_dir


class TestSeleniumBDDJavaExtractor:
    """Test the SeleniumBDDJavaExtractor class."""
    
    def test_extract_simple_feature(self, temp_features_dir):
        """Test extracting a simple feature with one scenario."""
        feature_file = temp_features_dir / "login.feature"
        feature_file.write_text("""
Feature: Login Feature

  Scenario: Valid login
    Given user is on login page
    When user enters valid credentials
    Then login should be successful
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].framework == "selenium-bdd-java"
        assert tests[0].test_name == "Login Feature::Valid login"
        assert tests[0].file_path == str(feature_file)
        assert tests[0].test_type == "ui"
        assert tests[0].language == "java"
    
    def test_extract_multiple_scenarios(self, temp_features_dir):
        """Test extracting multiple scenarios from one feature."""
        feature_file = temp_features_dir / "auth.feature"
        feature_file.write_text("""
Feature: Authentication

  Scenario: Valid login
    Given user is on login page
    When user enters valid credentials
    Then login should be successful

  Scenario: Invalid login
    Given user is on login page
    When user enters invalid credentials
    Then error message should be displayed
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        assert tests[0].test_name == "Authentication::Valid login"
        assert tests[1].test_name == "Authentication::Invalid login"
    
    def test_extract_scenario_outline(self, temp_features_dir):
        """Test extracting Scenario Outline."""
        feature_file = temp_features_dir / "search.feature"
        feature_file.write_text("""
Feature: Search Feature

  Scenario Outline: Search with different terms
    Given user is on search page
    When user searches for "<term>"
    Then results should contain "<term>"

    Examples:
      | term    |
      | python  |
      | java    |
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].test_name == "Search Feature::Search with different terms"
    
    def test_extract_feature_level_tags(self, temp_features_dir):
        """Test extracting feature-level tags."""
        feature_file = temp_features_dir / "tagged.feature"
        feature_file.write_text("""
@auth @smoke
Feature: Tagged Feature

  Scenario: Test scenario
    Given a test step
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert "auth" in tests[0].tags
        assert "smoke" in tests[0].tags
    
    def test_extract_scenario_level_tags(self, temp_features_dir):
        """Test extracting scenario-level tags."""
        feature_file = temp_features_dir / "scenario_tags.feature"
        feature_file.write_text("""
Feature: Scenario Tags

  @positive @critical
  Scenario: Tagged scenario
    Given a test step
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert "positive" in tests[0].tags
        assert "critical" in tests[0].tags
    
    def test_extract_combined_tags(self, temp_features_dir):
        """Test combining feature-level and scenario-level tags."""
        feature_file = temp_features_dir / "combined_tags.feature"
        feature_file.write_text("""
@auth
Feature: Combined Tags

  @smoke
  Scenario: Test with combined tags
    Given a test step
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert "auth" in tests[0].tags
        assert "smoke" in tests[0].tags
        assert len(tests[0].tags) == 2
    
    def test_extract_multiple_tags_same_line(self, temp_features_dir):
        """Test extracting multiple tags on the same line."""
        feature_file = temp_features_dir / "multi_tags.feature"
        feature_file.write_text("""
@auth @smoke @regression
Feature: Multiple Tags

  @positive @critical
  Scenario: Test with multiple tags
    Given a test step
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        # All tags should be present
        expected_tags = {"auth", "smoke", "regression", "positive", "critical"}
        assert set(tests[0].tags) == expected_tags
    
    def test_extract_multiple_feature_files(self, temp_features_dir):
        """Test extracting from multiple feature files."""
        # Create multiple feature files
        (temp_features_dir / "feature1.feature").write_text("""
Feature: Feature One
  Scenario: Scenario One
    Given step one
""")
        
        (temp_features_dir / "feature2.feature").write_text("""
Feature: Feature Two
  Scenario: Scenario Two
    Given step two
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        test_names = [t.test_name for t in tests]
        assert "Feature One::Scenario One" in test_names
        assert "Feature Two::Scenario Two" in test_names
    
    def test_extract_nested_feature_files(self, temp_features_dir):
        """Test extracting from nested directories."""
        # Create nested structure
        subdir = temp_features_dir / "auth"
        subdir.mkdir()
        
        (subdir / "login.feature").write_text("""
Feature: Login
  Scenario: Login test
    Given user logs in
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].test_name == "Login::Login test"
    
    def test_ignore_comments(self, temp_features_dir):
        """Test that comments are ignored."""
        feature_file = temp_features_dir / "comments.feature"
        feature_file.write_text("""
# This is a comment
Feature: Feature with comments

  # Another comment
  Scenario: Test scenario
    # Comment in steps
    Given a test step
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].test_name == "Feature with comments::Test scenario"
    
    def test_extract_with_background(self, temp_features_dir):
        """Test feature with Background section."""
        feature_file = temp_features_dir / "background.feature"
        feature_file.write_text("""
Feature: Feature with Background

  Background:
    Given common setup step

  Scenario: Test one
    When action one
    Then result one

  Scenario: Test two
    When action two
    Then result two
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Background is not extracted as test, only scenarios
        assert len(tests) == 2
        assert tests[0].test_name == "Feature with Background::Test one"
        assert tests[1].test_name == "Feature with Background::Test two"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_feature_file(self, temp_features_dir):
        """Test handling empty feature file."""
        feature_file = temp_features_dir / "empty.feature"
        feature_file.write_text("")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should not crash, returns empty or creates test with UnknownFeature
        assert isinstance(tests, list)
    
    def test_feature_without_scenarios(self, temp_features_dir):
        """Test feature file with no scenarios."""
        feature_file = temp_features_dir / "no_scenarios.feature"
        feature_file.write_text("""
Feature: Feature without scenarios

  This feature has no scenarios yet.
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 0
    
    def test_nonexistent_features_dir(self, tmp_path):
        """Test handling nonexistent features directory."""
        nonexistent = tmp_path / "nonexistent"
        
        config = SeleniumBDDJavaConfig(features_dir=str(nonexistent))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        # Should not crash, returns empty list
        assert tests == []
    
    def test_feature_with_special_characters(self, temp_features_dir):
        """Test feature names with special characters."""
        feature_file = temp_features_dir / "special.feature"
        feature_file.write_text("""
Feature: Login & Logout (E2E)

  Scenario: User can login/logout
    Given user is ready
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert "Login & Logout (E2E)" in tests[0].test_name
    
    def test_ignore_patterns(self, temp_features_dir):
        """Test ignore patterns functionality."""
        # Create files to ignore
        draft_dir = temp_features_dir / "draft"
        draft_dir.mkdir()
        
        (temp_features_dir / "valid.feature").write_text("""
Feature: Valid
  Scenario: Test
    Given step
""")
        
        (draft_dir / "ignored.feature").write_text("""
Feature: Ignored
  Scenario: Should be ignored
    Given step
""")
        
        config = SeleniumBDDJavaConfig(
            features_dir=str(temp_features_dir),
            ignore_patterns=["**/draft/**"]
        )
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].test_name == "Valid::Test"
    
    def test_scenario_without_tags(self, temp_features_dir):
        """Test scenario with no tags."""
        feature_file = temp_features_dir / "no_tags.feature"
        feature_file.write_text("""
Feature: No Tags

  Scenario: Untagged scenario
    Given a step
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].tags == []


class TestContractStability:
    """Test that API contracts remain stable."""
    
    def test_extracted_test_has_required_attributes(self, temp_features_dir):
        """Test that extracted TestMetadata has all required attributes."""
        feature_file = temp_features_dir / "test.feature"
        feature_file.write_text("""
Feature: Test
  Scenario: Test
    Given step
""")
        
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        test = tests[0]
        
        # Required attributes
        assert hasattr(test, "framework")
        assert hasattr(test, "test_name")
        assert hasattr(test, "file_path")
        assert hasattr(test, "tags")
        assert hasattr(test, "test_type")
        assert hasattr(test, "language")
        
        # Correct values
        assert test.framework == "selenium-bdd-java"
        assert test.test_type == "ui"
        assert test.language == "java"
        assert isinstance(test.tags, list)
    
    def test_extract_tests_returns_list(self, temp_features_dir):
        """Test that extract_tests always returns a list."""
        config = SeleniumBDDJavaConfig(features_dir=str(temp_features_dir))
        extractor = SeleniumBDDJavaExtractor(config)
        tests = extractor.extract_tests()
        
        assert isinstance(tests, list)
