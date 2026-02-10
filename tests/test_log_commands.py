"""
Unit tests for CrossBridge Log Commands
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import json
import requests

from cli.commands.log_commands import LogParser


class TestLogParser:
    """Tests for LogParser class."""
    
    def test_init_default_values(self):
        """Test initialization with default env values."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            parser = LogParser()
            
            assert parser.sidecar_host == "localhost"
            assert parser.sidecar_port == "8765"
            assert parser.sidecar_url == "http://localhost:8765"
    
    def test_init_custom_values(self):
        """Test initialization with custom env values."""
        import os
        custom_env = {
            "CROSSBRIDGE_SIDECAR_HOST": "remote.host",
            "CROSSBRIDGE_SIDECAR_PORT": "9000"
        }
        
        with patch.dict(os.environ, custom_env):
            parser = LogParser()
            
            assert parser.sidecar_host == "remote.host"
            assert parser.sidecar_port == "9000"
            assert parser.sidecar_url == "http://remote.host:9000"
    
    @patch("requests.get")
    def test_check_sidecar_success(self, mock_get):
        """Test sidecar health check when successful."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        parser = LogParser()
        result = parser.check_sidecar()
        
        assert result == True
    
    @patch("requests.get")
    def test_check_sidecar_failure(self, mock_get):
        """Test sidecar health check when unreachable."""
        mock_get.side_effect = Exception("Connection refused")
        
        parser = LogParser()
        result = parser.check_sidecar()
        
        assert result == False
    
    def test_detect_framework_robot(self):
        """Test framework detection for Robot Framework."""
        parser = LogParser()
        
        assert parser.detect_framework(Path("output.xml")) == "robot"
        assert parser.detect_framework(Path("robot-results.xml")) == "robot"
    
    def test_detect_framework_cypress(self):
        """Test framework detection for Cypress."""
        parser = LogParser()
        
        assert parser.detect_framework(Path("cypress-results.json")) == "cypress"
        assert parser.detect_framework(Path("results-cypress.json")) == "cypress"
    
    def test_detect_framework_playwright(self):
        """Test framework detection for Playwright."""
        parser = LogParser()
        
        assert parser.detect_framework(Path("playwright-trace.json")) == "playwright"
        assert parser.detect_framework(Path("trace-results.json")) == "playwright"
    
    def test_detect_framework_behave(self):
        """Test framework detection for Behave."""
        parser = LogParser()
        
        # Test with file content check
        mock_file_content = '{"feature": "test"}'
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            assert parser.detect_framework(Path("behave-results.json")) == "behave"
    
    def test_detect_framework_java(self):
        """Test framework detection for Java Cucumber."""
        parser = LogParser()
        
        assert parser.detect_framework(Path("LoginSteps.java")) == "java"
        assert parser.detect_framework(Path("UserStepDefinitions.java")) == "java"
    
    def test_detect_framework_by_content_robot(self):
        """Test framework detection by file content for Robot."""
        parser = LogParser()
        
        mock_file_content = '<?xml version="1.0"?>\n<robot generator="Robot 5.0">'
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            assert parser.detect_framework(Path("test.xml")) == "robot"
    
    def test_detect_framework_by_content_cypress(self):
        """Test framework detection by file content for Cypress."""
        parser = LogParser()
        
        mock_file_content = '{"suites": []}'
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            assert parser.detect_framework(Path("results.json")) == "cypress"
    
    def test_detect_framework_unknown(self):
        """Test framework detection for unknown format."""
        parser = LogParser()
        
        with patch("builtins.open", mock_open(read_data="random content")):
            assert parser.detect_framework(Path("unknown.txt")) == "unknown"
    
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake log data")
    def test_parse_log_success(self, mock_file, mock_post):
        """Test successful log parsing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"suite": {"name": "Test Suite"}}
        mock_post.return_value = mock_response
        
        parser = LogParser()
        result = parser.parse_log(Path("output.xml"), "robot")
        
        assert result == {"suite": {"name": "Test Suite"}}
        mock_post.assert_called_once()
    
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake log data")
    def test_parse_log_failure(self, mock_file, mock_post):
        """Test log parsing failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Parse error"}
        mock_post.return_value = mock_response
        
        parser = LogParser()
        result = parser.parse_log(Path("output.xml"), "robot")
        
        assert result == {}
    
    @patch("requests.post")
    def test_enrich_with_intelligence_no_ai(self, mock_post):
        """Test intelligence enrichment without AI."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "analyzed": True,
            "data": {"tests": []},
            "intelligence_summary": {}
        }
        mock_post.return_value = mock_response
        
        parser = LogParser()
        data = {"tests": []}
        result = parser.enrich_with_intelligence(data, "robot", enable_ai=False)
        
        assert "analyzed" in result
        mock_post.assert_called_once()
    
    @patch("requests.get")
    @patch("requests.post")
    def test_enrich_with_intelligence_with_ai(self, mock_post, mock_get):
        """Test intelligence enrichment with AI enabled."""
        # Mock AI provider info
        mock_provider_response = Mock()
        mock_provider_response.status_code = 200
        mock_provider_response.json.return_value = {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "cost_per_1k_tokens": 0.002
        }
        mock_get.return_value = mock_provider_response
        
        # Mock analysis response
        mock_analysis_response = Mock()
        mock_analysis_response.status_code = 200
        mock_analysis_response.json.return_value = {
            "analyzed": True,
            "data": {"tests": []},
            "ai_usage": {"total_tokens": 1000}
        }
        mock_post.return_value = mock_analysis_response
        
        parser = LogParser()
        data = {"tests": []}
        result = parser.enrich_with_intelligence(data, "robot", enable_ai=True)
        
        assert "ai_usage" in result
    
    def test_apply_filters_empty(self):
        """Test applying empty filters."""
        parser = LogParser()
        data = {"tests": [{"name": "test1"}, {"name": "test2"}]}
        
        result = parser.apply_filters(data, {})
        
        # Should return data unchanged when no filters
        assert result == data
    
    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        parser = LogParser()
        
        assert parser.format_duration(30) == "30s"
        assert parser.format_duration(59) == "59s"
    
    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        parser = LogParser()
        
        assert parser.format_duration(60) == "1m"
        assert parser.format_duration(90) == "1m 30s"
        assert parser.format_duration(120) == "2m"
    
    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        parser = LogParser()
        
        assert parser.format_duration(3600) == "1h"
        assert parser.format_duration(3660) == "1h 1m"
        assert parser.format_duration(7200) == "2h"
    
    def test_format_duration_days(self):
        """Test duration formatting for days."""
        parser = LogParser()
        
        assert parser.format_duration(86400) == "1d"
        assert parser.format_duration(90000) == "1d 1h"
        assert parser.format_duration(172800) == "2d"
    
    def test_display_robot_results(self):
        """Test displaying Robot Framework results."""
        parser = LogParser()
        
        data = {
            "suite": {
                "name": "Test Suite",
                "status": "PASS",
                "total_tests": 10,
                "passed_tests": 9,
                "failed_tests": 1,
                "elapsed_ms": 5000
            },
            "failed_keywords": [
                {
                    "name": "Click Button",
                    "library": "SeleniumLibrary",
                    "error": "Element not found"
                }
            ]
        }
        
        # Just test that it doesn't raise an exception
        parser._display_robot_results(data)
    
    def test_display_cypress_results(self):
        """Test displaying Cypress results."""
        parser = LogParser()
        
        data = {
            "statistics": {
                "total_tests": 5,
                "passed_tests": 4,
                "failed_tests": 1
            },
            "failures": [
                {
                    "title": "Login test",
                    "error_message": "Assertion failed"
                }
            ]
        }
        
        # Just test that it doesn't raise an exception
        parser._display_cypress_results(data)
    
    def test_display_playwright_results(self):
        """Test displaying Playwright results."""
        parser = LogParser()
        
        data = {
            "actions": [
                {"action": "click", "selector": "#button"},
                {"action": "type", "selector": "#input"}
            ],
            "network_calls": []
        }
        
        # Just test that it doesn't raise an exception
        parser._display_playwright_results(data)
    
    def test_display_intelligence_summary(self):
        """Test displaying intelligence summary."""
        parser = LogParser()
        
        data = {
            "intelligence_summary": {
                "classifications": {
                    "PRODUCT_DEFECT": 2,
                    "AUTOMATION_DEFECT": 1
                },
                "signals": {
                    "timeout": 1,
                    "assertion_error": 2
                }
            }
        }
        
        # Just test that it doesn't raise an exception
        parser._display_intelligence_summary(data)
    
    def test_display_ai_usage(self):
        """Test displaying AI usage summary."""
        parser = LogParser()
        
        data = {
            "ai_usage": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "total_tokens": 1500,
                "cost": 0.003
            }
        }
        
        # Just test that it doesn't raise an exception
        parser._display_ai_usage(data)
    
    def test_display_ai_usage_selfhosted(self):
        """Test displaying AI usage for self-hosted."""
        parser = LogParser()
        
        data = {
            "ai_usage": {
                "provider": "selfhosted",
                "model": "llama-2-7b",
                "total_tokens": 1500,
                "cost": 0
            }
        }
        
        # Just test that it doesn't raise an exception
        parser._display_ai_usage(data)


class TestLogCommandIntegration:
    """Integration tests for log command."""
    
    @patch("requests.get")
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b'<?xml version="1.0"?><robot>')
    def test_full_parse_workflow(self, mock_file, mock_post, mock_get):
        """Test complete log parsing workflow."""
        # Mock sidecar health check
        mock_health_response = Mock()
        mock_health_response.status_code = 200
        
        # Mock parse response
        mock_parse_response = Mock()
        mock_parse_response.status_code = 200
        mock_parse_response.json.return_value = {
            "suite": {"name": "Test", "status": "PASS"}
        }
        
        # Set up the mocks
        mock_get.return_value = mock_health_response
        mock_post.return_value = mock_parse_response
        
        parser = LogParser()
        
        # Check sidecar
        assert parser.check_sidecar() == True
        
        # Detect framework
        framework = parser.detect_framework(Path("output.xml"))
        assert framework == "robot"
        
        # Parse log
        result = parser.parse_log(Path("output.xml"), framework)
        assert "suite" in result
