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


class TestTestNGDisplay:
    """Tests for TestNG results display functionality"""
    
    @pytest.fixture
    def testng_data_with_failures(self):
        """Sample TestNG data with failures"""
        return {
            "framework": "testng",
            "summary": {
                "total_tests": 10,
                "passed": 7,
                "failed": 3,
                "skipped": 0,
                "pass_rate": 70.0
            },
            "failed_tests": [
                {
                    "test_name": "com.example.LoginTest.testInvalidPassword",
                    "class_name": "com.example.LoginTest",
                    "method_name": "testInvalidPassword",
                    "status": "FAIL",
                    "error_message": "Expected error message not displayed",
                    "failure_type": "java.lang.AssertionError",
                    "category": "TEST_ASSERTION",
                    "duration_ms": 500,
                    "stack_trace": "at com.example.LoginTest.testInvalidPassword..."
                },
                {
                    "test_name": "com.example.TimeoutTest.testSlowOperation",
                    "class_name": "com.example.TimeoutTest",
                    "method_name": "testSlowOperation",
                    "status": "FAIL",
                    "error_message": "Timeout waiting for element",
                    "failure_type": "org.openqa.selenium.TimeoutException",
                    "category": "INFRASTRUCTURE",
                    "duration_ms": 30000,
                    "stack_trace": "at org.openqa.selenium..."
                },
                {
                    "test_name": "com.example.ApiTest.testEndpoint",
                    "class_name": "com.example.ApiTest",
                    "method_name": "testEndpoint",
                    "status": "FAIL",
                    "error_message": "Expected 200 but was 500",
                    "failure_type": "java.lang.AssertionError",
                    "category": "APPLICATION",
                    "duration_ms": 1200,
                    "stack_trace": "at com.example.ApiTest..."
                }
            ],
            "all_tests": [
                {"test_name": "test1", "duration_ms": 5000, "status": "PASS", "class_name": "Class1", "method_name": "test1"},
                {"test_name": "test2", "duration_ms": 3000, "status": "PASS", "class_name": "Class1", "method_name": "test2"},
                {"test_name": "test3", "duration_ms": 2000, "status": "PASS", "class_name": "Class1", "method_name": "test3"},
            ],
            "statistics": {
                "total": 10,
                "passed": 7,
                "failed": 3,
                "skipped": 0
            }
        }
    
    @pytest.fixture
    def testng_data_all_passed(self):
        """Sample TestNG data with all tests passed"""
        return {
            "framework": "testng",
            "summary": {
                "total_tests": 5,
                "passed": 5,
                "failed": 0,
                "skipped": 0,
                "pass_rate": 100.0
            },
            "failed_tests": [],
            "all_tests": [
                {"test_name": "test1", "duration_ms": 1000, "status": "PASS", "class_name": "Class1", "method_name": "test1"},
                {"test_name": "test2", "duration_ms": 2000, "status": "PASS", "class_name": "Class1", "method_name": "test2"},
            ],
            "statistics": {
                "total": 5,
                "passed": 5,
                "failed": 0,
                "skipped": 0
            }
        }
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_testng_results_with_failures(self, mock_print, testng_data_with_failures):
        """Test displaying TestNG results with failures"""
        parser = LogParser()
        
        # This should not raise any exceptions
        parser._display_testng_results(testng_data_with_failures)
        
        # Verify console.print was called (output was generated)
        assert mock_print.called
        assert mock_print.call_count > 0
        
        # Check that key sections were displayed
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "TestNG Test Results" in calls_str or "testng" in calls_str.lower()
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_testng_results_all_passed(self, mock_print, testng_data_all_passed):
        """Test displaying TestNG results when all tests passed"""
        parser = LogParser()
        
        # This should not raise any exceptions
        parser._display_testng_results(testng_data_all_passed)
        
        # Verify console.print was called
        assert mock_print.called
        
        # Should show PASS status
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "PASS" in calls_str
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_testng_with_clustering(self, mock_print, testng_data_with_failures):
        """Test that TestNG display uses clustering for failures"""
        parser = LogParser()
        
        # Add more similar failures to trigger clustering
        testng_data_with_failures["failed_tests"].extend([
            {
                "test_name": "com.example.Test2.method",
                "class_name": "com.example.Test2",
                "method_name": "method",
                "status": "FAIL",
                "error_message": "Expected error message not displayed",  # Similar error
                "failure_type": "java.lang.AssertionError",
                "category": "TEST_ASSERTION",
                "duration_ms": 500,
                "stack_trace": "..."
            }
        ])
        
        parser._display_testng_results(testng_data_with_failures)
        
        # Should mention clustering or deduplication
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        # The clustering module may deduplicate or show unique issues
        assert mock_print.called
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_testng_shows_slowest_tests(self, mock_print, testng_data_with_failures):
        """Test that slowest tests are displayed"""
        parser = LogParser()
        
        # Add tests with varying durations
        testng_data_with_failures["all_tests"] = [
            {"test_name": "slow1", "duration_ms": 50000, "status": "PASS", "class_name": "C1", "method_name": "slow1"},
            {"test_name": "slow2", "duration_ms": 40000, "status": "PASS", "class_name": "C1", "method_name": "slow2"},
            {"test_name": "slow3", "duration_ms": 30000, "status": "FAIL", "class_name": "C1", "method_name": "slow3"},
            {"test_name": "fast1", "duration_ms": 100, "status": "PASS", "class_name": "C1", "method_name": "fast1"},
        ]
        
        parser._display_testng_results(testng_data_with_failures)
        
        # Should show slowest tests section
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "Slowest" in calls_str or "Duration" in calls_str
    
    def test_display_results_routes_to_testng(self, testng_data_with_failures):
        """Test that display_results correctly routes TestNG data"""
        parser = LogParser()
        
        with patch.object(parser, '_display_testng_results') as mock_display:
            # Call display_results with testng framework
            parser.display_results(testng_data_with_failures, "testng")
            
            # Should have called _display_testng_results
            mock_display.assert_called_once()
            args = mock_display.call_args[0]
            assert args[0] == testng_data_with_failures


class TestCypressDisplay:
    """Tests for Cypress results display functionality."""
    
    @pytest.fixture
    def cypress_data_with_failures(self):
        """Cypress data with some failures for testing clustering."""
        return {
            "framework": "cypress",
            "total_tests": 15,
            "passed": 10,
            "failed": 5,
            "skipped": 0,
            "pass_rate": 66.7,
            "duration_ms": 45000,
            "failed_tests": [
                {
                    "test_name": "Login Test > should handle invalid credentials",
                    "title": "should handle invalid credentials",
                    "status": "failed",
                    "error_message": "Timed out retrying after 4000ms: Expected to find element: #login-btn",
                    "stack_trace": "at Object.cypressErr...",
                    "duration_ms": 4500,
                },
                {
                    "test_name": "Profile Test > should load user profile",
                    "title": "should load user profile",
                    "status": "failed",
                    "error_message": "Timed out retrying after 4000ms: Expected to find element: #profile",
                    "stack_trace": "at Object.cypressErr...",
                    "duration_ms": 4200,
                },
                {
                    "test_name": "API Test > should return 200",
                    "title": "should return 200",
                    "status": "failed",
                    "error_message": "expected 200 to equal 500",
                    "stack_trace": "AssertionError...",
                    "duration_ms": 1000,
                },
            ],
            "all_tests": [
                {"test_name": "test1", "status": "passed", "duration_ms": 5000},
                {"test_name": "test2", "status": "passed", "duration_ms": 3000},
                {"test_name": "test3", "status": "failed", "duration_ms": 4500},
            ],
        }
    
    @pytest.fixture
    def cypress_data_all_passed(self):
        """Cypress data with all tests passing."""
        return {
            "framework": "cypress",
            "total_tests": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "pass_rate": 100.0,
            "duration_ms": 25000,
            "failed_tests": [],
            "all_tests": [
                {"test_name": "test1", "status": "passed", "duration_ms": 2500},
                {"test_name": "test2", "status": "passed", "duration_ms": 2400},
            ],
        }
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_cypress_results_with_failures(self, mock_print, cypress_data_with_failures):
        """Test displaying Cypress results with failures"""
        parser = LogParser()
        
        # This should not raise any exceptions
        parser._display_cypress_results(cypress_data_with_failures)
        
        # Verify console.print was called
        assert mock_print.called
        
        # Should show FAIL status and clustering info
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "FAIL" in calls_str or "Failed" in calls_str
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_cypress_results_all_passed(self, mock_print, cypress_data_all_passed):
        """Test displaying Cypress results when all tests passed"""
        parser = LogParser()
        
        parser._display_cypress_results(cypress_data_all_passed)
        
        # Verify console.print was called
        assert mock_print.called
        
        # Should show PASS status
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "PASS" in calls_str
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_cypress_with_clustering(self, mock_print, cypress_data_with_failures):
        """Test that Cypress display uses clustering for failures"""
        parser = LogParser()
        
        # Add more similar failures to trigger clustering
        cypress_data_with_failures["failed_tests"].append({
            "test_name": "Settings Test > should update settings",
            "title": "should update settings",
            "status": "failed",
            "error_message": "Timed out retrying after 4000ms: Expected to find element: #settings",
            "stack_trace": "at Object.cypressErr...",
            "duration_ms": 4100,
        })
        
        parser._display_cypress_results(cypress_data_with_failures)
        
        # Should mention clustering or show root cause analysis
        assert mock_print.called
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_cypress_shows_slowest_tests(self, mock_print, cypress_data_with_failures):
        """Test that slowest tests are displayed"""
        parser = LogParser()
        
        # Add tests with varying durations
        cypress_data_with_failures["all_tests"] = [
            {"test_name": "slow_test_1", "duration_ms": 8000, "status": "passed"},
            {"test_name": "slow_test_2", "duration_ms": 7000, "status": "passed"},
            {"test_name": "fast_test", "duration_ms": 100, "status": "passed"},
        ]
        
        parser._display_cypress_results(cypress_data_with_failures)
        
        # Should show slowest tests section
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "Slowest" in calls_str or "Duration" in calls_str
    
    def test_display_results_routes_to_cypress(self, cypress_data_with_failures):
        """Test that display_results correctly routes Cypress data"""
        parser = LogParser()
        
        with patch.object(parser, '_display_cypress_results') as mock_display:
            parser.display_results(cypress_data_with_failures, "cypress")
            
            mock_display.assert_called_once()
            args = mock_display.call_args[0]
            assert args[0] == cypress_data_with_failures


class TestBehaveDisplay:
    """Tests for Behave BDD results display functionality."""
    
    @pytest.fixture
    def behave_data_with_failures(self):
        """Behave data with some failures for testing clustering."""
        return {
            "framework": "behave",
            "total_features": 3,
            "total_scenarios": 20,
            "passed_scenarios": 15,
            "failed_scenarios": 5,
            "skipped_scenarios": 0,
            "pass_rate": 75.0,
            "duration_ms": 60000,
            "failed_scenarios_list": [
                {
                    "test_name": "User Authentication: Login with valid credentials",
                    "scenario_name": "Login with valid credentials",
                    "feature_name": "User Authentication",
                    "status": "failed",
                    "error_message": "Element not found: #login-button",
                    "failed_steps": 1,
                    "duration_ms": 5000,
                    "tags": ["smoke", "auth"],
                },
                {
                    "test_name": "User Authentication: Login with invalid credentials",
                    "scenario_name": "Login with invalid credentials",
                    "feature_name": "User Authentication",
                    "status": "failed",
                    "error_message": "Element not found: #error-message",
                    "failed_steps": 1,
                    "duration_ms": 4500,
                    "tags": ["smoke", "auth"],
                },
                {
                    "test_name": "API Testing: Get user profile",
                    "scenario_name": "Get user profile",
                    "feature_name": "API Testing",
                    "status": "failed",
                    "error_message": "AssertionError: expected 200 but got 500",
                    "failed_steps": 1,
                    "duration_ms": 2000,
                    "tags": ["api"],
                },
            ],
            "all_scenarios": [
                {
                    "test_name": "Feature1: Scenario1",
                    "scenario_name": "Scenario1",
                    "feature_name": "Feature1",
                    "status": "passed",
                    "error_message": "",
                    "duration_ms": 3000,
                    "tags": [],
                },
                {
                    "test_name": "Feature1: Scenario2",
                    "scenario_name": "Scenario2",
                    "feature_name": "Feature1",
                    "status": "passed",
                    "duration_ms": 2500,
                    "tags": [],
                },
            ],
        }
    
    @pytest.fixture
    def behave_data_all_passed(self):
        """Behave data with all scenarios passing."""
        return {
            "framework": "behave",
            "total_features": 2,
            "total_scenarios": 12,
            "passed_scenarios": 12,
            "failed_scenarios": 0,
            "skipped_scenarios": 0,
            "pass_rate": 100.0,
            "duration_ms": 35000,
            "failed_scenarios_list": [],
            "all_scenarios": [
                {
                    "test_name": "Feature1: Scenario1",
                    "scenario_name": "Scenario1",
                    "feature_name": "Feature1",
                    "status": "passed",
                    "error_message": "",
                    "duration_ms": 2900,
                    "tags": [],
                },
            ],
        }
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_behave_results_with_failures(self, mock_print, behave_data_with_failures):
        """Test displaying Behave results with failures"""
        parser = LogParser()
        
        # This should not raise any exceptions
        parser._display_behave_results(behave_data_with_failures)
        
        # Verify console.print was called
        assert mock_print.called
        
        # Should show FAIL status and scenario info
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "FAIL" in calls_str or "Failed" in calls_str
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_behave_results_all_passed(self, mock_print, behave_data_all_passed):
        """Test displaying Behave results when all scenarios passed"""
        parser = LogParser()
        
        parser._display_behave_results(behave_data_all_passed)
        
        # Verify console.print was called
        assert mock_print.called
        
        # Should show PASS status
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "PASS" in calls_str
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_behave_with_clustering(self, mock_print, behave_data_with_failures):
        """Test that Behave display uses clustering for failures"""
        parser = LogParser()
        
        # Add more similar failures
        behave_data_with_failures["failed_scenarios_list"].append({
            "test_name": "User Authentication: Logout",
            "scenario_name": "Logout",
            "feature_name": "User Authentication",
            "status": "failed",
            "error_message": "Element not found: #logout-button",
            "failed_steps": 1,
            "duration_ms": 4800,
            "tags": ["auth"],
        })
        
        parser._display_behave_results(behave_data_with_failures)
        
        # Should mention clustering or root cause analysis
        assert mock_print.called
    
    @patch("cli.commands.log_commands.console.print")
    def test_display_behave_shows_slowest_scenarios(self, mock_print, behave_data_with_failures):
        """Test that slowest scenarios are displayed"""
        parser = LogParser()
        
        # Add scenarios with varying durations
        behave_data_with_failures["all_scenarios"] = [
            {
                "test_name": "Feature1: Slow Scenario 1",
                "scenario_name": "Slow Scenario 1",
                "feature_name": "Feature1",
                "status": "passed",
                "error_message": "",
                "duration_ms": 10000,
                "tags": [],
            },
            {
                "test_name": "Feature1: Slow Scenario 2",
                "scenario_name": "Slow Scenario 2",
                "feature_name": "Feature1",
                "status": "passed",
                "error_message": "",
                "duration_ms": 9000,
                "tags": [],
            },
            {
                "test_name": "Feature1: Fast Scenario",
                "scenario_name": "Fast Scenario",
                "feature_name": "Feature1",
                "status": "passed",
                "error_message": "",
                "duration_ms": 500,
                "tags": [],
            },
        ]
        
        parser._display_behave_results(behave_data_with_failures)
        
        # Should show slowest scenarios section
        calls_str = " ".join([str(call) for call in mock_print.call_args_list])
        assert "Slowest" in calls_str or "Duration" in calls_str
    
    def test_display_results_routes_to_behave(self, behave_data_with_failures):
        """Test that display_results correctly routes Behave data"""
        parser = LogParser()
        
        with patch.object(parser, '_display_behave_results') as mock_display:
            parser.display_results(behave_data_with_failures, "behave")
            
            mock_display.assert_called_once()
            args = mock_display.call_args[0]
            assert args[0] == behave_data_with_failures

