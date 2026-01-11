"""
Unit tests for enhanced Robot Framework configuration prompts.

Tests the prompt_robot_framework_config() function which collects:
- Robot test directory (required)
- Page Object classes path (optional)
- Locator files path (optional)

This validates Phase 2/3 integration via CLI menu.
"""

import pytest
from unittest.mock import patch, MagicMock
from cli.prompts import prompt_robot_framework_config


class TestRobotFrameworkConfig:
    """Test suite for Robot Framework configuration prompts."""
    
    def test_minimal_config_robot_only(self):
        """Test minimal configuration with only Robot test directory."""
        # Mock user inputs: robot path, skip page objects, skip locators
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot',  # robot_tests_path
                '',             # page_objects_path (skip)
                ''              # locators_path (skip)
            ]
            
            result = prompt_robot_framework_config()
            
            assert 'robot_tests_path' in result
            assert result['robot_tests_path'] == 'tests/robot'
            assert 'page_objects_path' not in result
            assert 'locators_path' not in result
    
    def test_full_config_all_paths(self):
        """Test full configuration with all paths provided."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'automation/robot',           # robot_tests_path
                'src/main/java/pages',        # page_objects_path
                'src/main/java/locators'      # locators_path
            ]
            
            result = prompt_robot_framework_config()
            
            assert result['robot_tests_path'] == 'automation/robot'
            assert result['page_objects_path'] == 'src/main/java/pages'
            assert result['locators_path'] == 'src/main/java/locators'
    
    def test_page_objects_only(self):
        """Test configuration with page objects but no locators."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'robot',                # robot_tests_path
                'tests/pages',          # page_objects_path
                ''                      # locators_path (skip)
            ]
            
            result = prompt_robot_framework_config()
            
            assert result['robot_tests_path'] == 'robot'
            assert result['page_objects_path'] == 'tests/pages'
            assert 'locators_path' not in result
    
    def test_locators_only(self):
        """Test configuration with locators but no page objects."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot',          # robot_tests_path
                '',                     # page_objects_path (skip)
                'tests/locators'        # locators_path
            ]
            
            result = prompt_robot_framework_config()
            
            assert result['robot_tests_path'] == 'tests/robot'
            assert 'page_objects_path' not in result
            assert result['locators_path'] == 'tests/locators'
    
    def test_whitespace_trimming(self):
        """Test that whitespace is properly trimmed from inputs."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                '  tests/robot  ',              # robot_tests_path with spaces
                '  src/main/java/pages  ',      # page_objects_path with spaces
                '  src/main/java/locators  '    # locators_path with spaces
            ]
            
            result = prompt_robot_framework_config()
            
            # All values should be trimmed
            assert result['robot_tests_path'] == 'tests/robot'
            assert result['page_objects_path'] == 'src/main/java/pages'
            assert result['locators_path'] == 'src/main/java/locators'
    
    def test_empty_robot_path_retry(self):
        """Test that empty robot path prompts retry until valid input."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            # First two attempts are empty/whitespace, third is valid
            mock_ask.side_effect = [
                '',                 # First attempt - empty
                '   ',              # Second attempt - whitespace only
                'tests/robot',      # Third attempt - valid
                '',                 # page_objects_path (skip)
                ''                  # locators_path (skip)
            ]
            
            result = prompt_robot_framework_config()
            
            # Should retry until valid input
            assert result['robot_tests_path'] == 'tests/robot'
            # Prompt should have been called 5 times (3 for robot, 2 for optional)
            assert mock_ask.call_count == 5
    
    def test_various_path_formats(self):
        """Test different path format conventions."""
        test_cases = [
            ('tests/robot', 'src/main/java/pages', 'src/main/java/locators'),
            ('robot-tests', 'pages', 'selectors'),
            ('automation/tests/robot', 'automation/src/pages', 'automation/src/locators'),
            ('test/robot', 'test/page_objects', 'test/locators')
        ]
        
        for robot_path, page_path, locator_path in test_cases:
            with patch('cli.prompts.Prompt.ask') as mock_ask:
                mock_ask.side_effect = [robot_path, page_path, locator_path]
                
                result = prompt_robot_framework_config()
                
                assert result['robot_tests_path'] == robot_path
                assert result['page_objects_path'] == page_path
                assert result['locators_path'] == locator_path
    
    def test_return_type(self):
        """Test that function returns a dictionary."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = ['tests/robot', '', '']
            
            result = prompt_robot_framework_config()
            
            assert isinstance(result, dict)
    
    def test_phase2_enabled_indicator(self):
        """Test that providing page objects path enables Phase 2."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot',
                'src/main/java/pages',  # This should enable Phase 2
                ''
            ]
            
            result = prompt_robot_framework_config()
            
            # When page_objects_path is present, Phase 2 should be enabled
            assert 'page_objects_path' in result
            # In actual usage, orchestrator will check this and enable Phase 2
    
    def test_phase3_enabled_indicator(self):
        """Test that providing locators path enables Phase 3."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot',
                '',
                'src/main/java/locators'  # This should enable Phase 3
            ]
            
            result = prompt_robot_framework_config()
            
            # When locators_path is present, Phase 3 should be enabled
            assert 'locators_path' in result
            # In actual usage, orchestrator will check this and enable Phase 3
    
    def test_both_phases_enabled(self):
        """Test that providing both paths enables Phase 2 & 3."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot',
                'src/pages',
                'src/locators'
            ]
            
            result = prompt_robot_framework_config()
            
            # Both Phase 2 and Phase 3 should be enabled
            assert 'page_objects_path' in result
            assert 'locators_path' in result
    
    def test_console_output_not_failing(self):
        """Test that Rich console output doesn't cause failures."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            with patch('cli.prompts.console') as mock_console:
                mock_ask.side_effect = ['tests/robot', '', '']
                
                result = prompt_robot_framework_config()
                
                # Function should complete successfully
                assert 'robot_tests_path' in result
                # Console.print should have been called for output
                assert mock_console.print.called


class TestRobotConfigIntegration:
    """Integration tests for Robot config with orchestrator."""
    
    def test_config_structure_matches_orchestrator_expectations(self):
        """Test that config structure matches what orchestrator expects."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot',
                'src/pages',
                'src/locators'
            ]
            
            config = prompt_robot_framework_config()
            
            # Orchestrator expects these keys in framework_config dict
            assert isinstance(config, dict)
            assert 'robot_tests_path' in config
            
            # Optional paths should be present when provided
            if 'page_objects_path' in config:
                assert isinstance(config['page_objects_path'], str)
            if 'locators_path' in config:
                assert isinstance(config['locators_path'], str)
    
    def test_config_values_are_strings(self):
        """Test that all config values are strings (not None or other types)."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot',
                'src/pages',
                'src/locators'
            ]
            
            config = prompt_robot_framework_config()
            
            # All values should be strings
            for key, value in config.items():
                assert isinstance(value, str), f"{key} should be string, got {type(value)}"
                assert value.strip() != '', f"{key} should not be empty"
    
    def test_no_none_values_in_config(self):
        """Test that config never contains None values."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            # Test with various input combinations
            test_cases = [
                ['tests/robot', '', ''],
                ['tests/robot', 'pages', ''],
                ['tests/robot', '', 'locators'],
                ['tests/robot', 'pages', 'locators']
            ]
            
            for inputs in test_cases:
                mock_ask.side_effect = inputs
                config = prompt_robot_framework_config()
                
                # No None values should exist
                for key, value in config.items():
                    assert value is not None, f"{key} should not be None"
                
                # Only present keys should have values
                if not inputs[1].strip():
                    assert 'page_objects_path' not in config
                if not inputs[2].strip():
                    assert 'locators_path' not in config


class TestRobotConfigEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_special_characters_in_paths(self):
        """Test paths with special characters."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'tests/robot-framework',
                'src/main/java/page_objects',
                'src/main/java/locators_v2'
            ]
            
            result = prompt_robot_framework_config()
            
            # Paths with hyphens and underscores should work
            assert result['robot_tests_path'] == 'tests/robot-framework'
            assert result['page_objects_path'] == 'src/main/java/page_objects'
            assert result['locators_path'] == 'src/main/java/locators_v2'
    
    def test_nested_directory_paths(self):
        """Test deeply nested directory paths."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'a/b/c/d/robot',
                'src/main/java/automation/pages',
                'src/main/java/automation/locators/v1'
            ]
            
            result = prompt_robot_framework_config()
            
            assert result['robot_tests_path'] == 'a/b/c/d/robot'
            assert result['page_objects_path'] == 'src/main/java/automation/pages'
            assert result['locators_path'] == 'src/main/java/automation/locators/v1'
    
    def test_single_directory_names(self):
        """Test single directory names without paths."""
        with patch('cli.prompts.Prompt.ask') as mock_ask:
            mock_ask.side_effect = [
                'robot',
                'pages',
                'locators'
            ]
            
            result = prompt_robot_framework_config()
            
            assert result['robot_tests_path'] == 'robot'
            assert result['page_objects_path'] == 'pages'
            assert result['locators_path'] == 'locators'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
