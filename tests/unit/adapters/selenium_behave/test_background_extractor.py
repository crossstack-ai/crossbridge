"""
Comprehensive unit tests for Behave Background Extractor.
"""

import pytest
from pathlib import Path
from adapters.selenium_behave.background_extractor import BehaveBackgroundExtractor


@pytest.fixture
def extractor():
    return BehaveBackgroundExtractor()


@pytest.fixture
def feature_with_background(tmp_path):
    """Create a feature file with Background section."""
    feature_file = tmp_path / "login.feature"
    feature_file.write_text("""Feature: User Authentication

Background:
  Given the application is running
  And I am on the login page
  And the database is clean

Scenario: Valid Login
  When I enter username "admin"
  And I enter password "pass123"
  And I click login button
  Then I should see dashboard

Scenario: Invalid Login
  When I enter username "invalid"
  And I enter password "wrong"
  And I click login button
  Then I should see error message
""")
    return feature_file


@pytest.fixture
def multiple_features(tmp_path):
    """Create multiple feature files with different backgrounds."""
    features_dir = tmp_path / "features"
    features_dir.mkdir()
    
    # Feature 1 with background
    f1 = features_dir / "login.feature"
    f1.write_text("""
Feature: Login
  Background:
    Given I am on login page
  Scenario: Login test
    When I login
    """)
    
    # Feature 2 without background
    f2 = features_dir / "search.feature"
    f2.write_text("""
Feature: Search
  Scenario: Search test
    Given I search for "test"
    """)
    
    # Feature 3 with background
    f3 = features_dir / "checkout.feature"
    f3.write_text("""
Feature: Checkout
  Background:
    Given I have items in cart
    And I am logged in
  Scenario: Checkout test
    When I proceed to checkout
    """)
    
    return features_dir


class TestBackgroundExtraction:
    """Test background extraction from feature files."""
    
    def test_extract_background_basic(self, extractor, feature_with_background):
        """Test basic background extraction."""
        background = extractor.extract_background(feature_with_background)
        
        assert background is not None
        assert len(background['steps']) == 3
    
    def test_background_steps_content(self, extractor, feature_with_background):
        """Test that background steps are correctly extracted."""
        background = extractor.extract_background(feature_with_background)
        
        steps = [step['text'] for step in background.steps]
        assert "the application is running" in steps[0]
        assert "I am on the login page" in steps[1]
        assert "the database is clean" in steps[2]
    
    def test_background_step_types(self, extractor, feature_with_background):
        """Test that step types are correctly identified."""
        background = extractor.extract_background(feature_with_background)
        
        assert background.steps[0]['keyword'] == 'Given'
        assert background.steps[1]['keyword'] == 'And'
        assert background.steps[2]['keyword'] == 'And'
    
    def test_feature_without_background(self, extractor, tmp_path):
        """Test handling of feature without background."""
        feature_file = tmp_path / "no_background.feature"
        feature_file.write_text("""
Feature: Simple Feature
  Scenario: Simple Test
    Given something
    When something else
    Then result
        """)
        
        background = extractor.extract_background(feature_file)
        assert background is None
    
    def test_has_background_true(self, extractor, feature_with_background):
        """Test has_background returns True for feature with background."""
        assert extractor.has_background(feature_with_background) is True
    
    def test_has_background_false(self, extractor, tmp_path):
        """Test has_background returns False for feature without background."""
        feature_file = tmp_path / "no_bg.feature"
        feature_file.write_text("""
Feature: No Background
  Scenario: Test
    Given step
        """)
        
        assert extractor.has_background(feature_file) is False


class TestMultipleFeatures:
    """Test extraction from multiple feature files."""
    
    def test_extract_from_multiple_features(self, extractor, multiple_features):
        """Test extracting backgrounds from multiple features."""
        backgrounds = extractor.extract_from_multiple_features(multiple_features)
        
        # Should find 2 backgrounds (login and checkout)
        assert len(backgrounds) == 2
    
    def test_multiple_features_content(self, extractor, multiple_features):
        """Test content of backgrounds from multiple features."""
        backgrounds = extractor.extract_from_multiple_features(multiple_features)
        
        feature_names = [bg.feature_name for bg in backgrounds]
        assert "Login" in feature_names
        assert "Checkout" in feature_names
        assert "Search" not in feature_names  # No background
    
    def test_empty_directory(self, extractor, tmp_path):
        """Test handling of empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        backgrounds = extractor.extract_from_multiple_features(empty_dir)
        assert len(backgrounds) == 0


class TestRobotFrameworkConversion:
    """Test conversion to Robot Framework format."""
    
    def test_convert_to_robot_setup(self, extractor, feature_with_background):
        """Test conversion to Robot Framework Setup keyword."""
        background = extractor.extract_background(feature_with_background)
        robot_code = extractor.convert_to_robot_setup(background)
        
        assert "*** Keywords ***" in robot_code
        assert "Suite Setup" in robot_code or "Test Setup" in robot_code
        assert "the application is running" in robot_code
        assert "I am on the login page" in robot_code
    
    def test_robot_conversion_structure(self, extractor, feature_with_background):
        """Test Robot Framework conversion has proper structure."""
        background = extractor.extract_background(feature_with_background)
        robot_code = extractor.convert_to_robot_setup(background)
        
        # Should have keywords section
        assert "*** Keywords ***" in robot_code
        # Should have proper indentation
        assert "    " in robot_code


class TestPytestConversion:
    """Test conversion to pytest fixtures."""
    
    def test_convert_to_pytest_fixture(self, extractor, feature_with_background):
        """Test conversion to pytest fixture."""
        background = extractor.extract_background(feature_with_background)
        pytest_code = extractor.convert_to_pytest_fixture(background)
        
        assert "@pytest.fixture" in pytest_code
        assert "def setup_" in pytest_code or "def background_" in pytest_code
        assert "yield" in pytest_code or "return" in pytest_code
    
    def test_pytest_fixture_autouse(self, extractor, feature_with_background):
        """Test pytest fixture with autouse option."""
        background = extractor.extract_background(feature_with_background)
        pytest_code = extractor.convert_to_pytest_fixture(background, autouse=True)
        
        assert "autouse=True" in pytest_code
    
    def test_pytest_fixture_scope(self, extractor, feature_with_background):
        """Test pytest fixture with different scopes."""
        background = extractor.extract_background(feature_with_background)
        
        # Test function scope
        pytest_code = extractor.convert_to_pytest_fixture(background, scope="function")
        assert 'scope="function"' in pytest_code or "scope='function'" in pytest_code
        
        # Test module scope
        pytest_code = extractor.convert_to_pytest_fixture(background, scope="module")
        assert 'scope="module"' in pytest_code or "scope='module'" in pytest_code


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_background_with_docstring(self, extractor, tmp_path):
        """Test background with docstring."""
        feature_file = tmp_path / "with_docstring.feature"
        feature_file.write_text('''
Feature: Feature with Docstring
  Background:
    Given I have config
      """
      {
        "key": "value"
      }
      """
  Scenario: Test
    When I do something
        ''')
        
        background = extractor.extract_background(feature_file)
        assert background is not None
        assert len(background.steps) >= 1
    
    def test_background_with_table(self, extractor, tmp_path):
        """Test background with data table."""
        feature_file = tmp_path / "with_table.feature"
        feature_file.write_text("""
Feature: Feature with Table
  Background:
    Given I have users
      | name  | role  |
      | Alice | Admin |
      | Bob   | User  |
  Scenario: Test
    When I check users
        """)
        
        background = extractor.extract_background(feature_file)
        assert background is not None
    
    def test_nonexistent_file(self, extractor, tmp_path):
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / "doesnt_exist.feature"
        
        background = extractor.extract_background(nonexistent)
        assert background is None
    
    def test_invalid_feature_file(self, extractor, tmp_path):
        """Test handling of invalid feature file."""
        invalid_file = tmp_path / "invalid.feature"
        invalid_file.write_text("This is not a valid feature file")
        
        background = extractor.extract_background(invalid_file)
        assert background is None
    
    def test_background_only_no_scenarios(self, extractor, tmp_path):
        """Test feature with only background and no scenarios."""
        feature_file = tmp_path / "bg_only.feature"
        feature_file.write_text("""
Feature: Background Only
  Background:
    Given setup step
        """)
        
        background = extractor.extract_background(feature_file)
        assert background is not None
        assert len(background.steps) == 1


class TestBackgroundStatistics:
    """Test background statistics and analysis."""
    
    def test_get_background_statistics(self, extractor, multiple_features):
        """Test getting statistics about backgrounds."""
        backgrounds = extractor.extract_from_multiple_features(multiple_features)
        stats = extractor.get_background_statistics(backgrounds)
        
        assert stats['total_backgrounds'] == 2
        assert stats['total_steps'] > 0
        assert 'features_with_background' in stats
    
    def test_average_steps_per_background(self, extractor, multiple_features):
        """Test calculating average steps per background."""
        backgrounds = extractor.extract_from_multiple_features(multiple_features)
        stats = extractor.get_background_statistics(backgrounds)
        
        assert 'average_steps_per_background' in stats
        assert stats['average_steps_per_background'] > 0


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_background_with_parameters(self, extractor, tmp_path):
        """Test background with parameterized steps."""
        feature_file = tmp_path / "params.feature"
        feature_file.write_text("""
Feature: Parameterized Background
  Background:
    Given I am logged in as "admin"
    And I have "5" items in cart
    And I am on page "checkout"
  Scenario: Test
    When I proceed
        """)
        
        background = extractor.extract_background(feature_file)
        assert background is not None
        assert len(background.steps) == 3
        
        # Check parameters are captured
        step_texts = [s['text'] for s in background.steps]
        assert any('"admin"' in text for text in step_texts)
        assert any('"5"' in text for text in step_texts)
    
    def test_background_with_tags(self, extractor, tmp_path):
        """Test feature with tags and background."""
        feature_file = tmp_path / "tagged.feature"
        feature_file.write_text("""
@smoke @regression
Feature: Tagged Feature
  Background:
    Given common setup
  
  @critical
  Scenario: Important test
    When something happens
        """)
        
        background = extractor.extract_background(feature_file)
        assert background is not None
    
    def test_multiple_backgrounds_same_content(self, extractor, tmp_path):
        """Test multiple features with identical backgrounds."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        
        for i in range(3):
            f = features_dir / f"feature{i}.feature"
            f.write_text("""
Feature: Feature {}
  Background:
    Given common setup
    And another setup
  Scenario: Test
    When test
            """.format(i))
        
        backgrounds = extractor.extract_from_multiple_features(features_dir)
        assert len(backgrounds) == 3
        
        # All should have same step count
        step_counts = [len(bg.steps) for bg in backgrounds]
        assert all(count == 2 for count in step_counts)
