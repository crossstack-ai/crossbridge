# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");

"""
Comprehensive tests for new framework parsers.

Tests:
- .NET AST Extractor (NUnit, xUnit, MSTest, SpecFlow)
- Playwright Trace Parser
- Cypress Results Parser
- Behave Results Parser
- Selenium Log Parser
"""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

# Import parsers
from core.intelligence.dotnet_ast_extractor import (
    DotNetASTExtractor,
    extract_dotnet_signals,
    parse_dotnet_test_file,
)
from core.intelligence.playwright_trace_parser import (
    PlaywrightTraceParser,
    parse_playwright_trace,
    analyze_playwright_performance,
)
from core.intelligence.cypress_results_parser import (
    CypressResultsParser,
    parse_cypress_results,
    analyze_cypress_performance,
    find_flaky_tests,
)
from core.intelligence.behave_selenium_parsers import (
    BehaveResultsParser,
    SeleniumLogParser,
    parse_behave_results,
    parse_selenium_logs,
    analyze_behave_failures,
)


# ============================================================================
# .NET AST Extractor Tests
# ============================================================================

class TestDotNetASTExtractor:
    """Tests for .NET AST Extractor."""
    
    def test_parse_nunit_test(self, tmp_path):
        """Test parsing NUnit test file."""
        test_file = tmp_path / "LoginTests.cs"
        test_file.write_text("""
using NUnit.Framework;

namespace MyApp.Tests
{
    [TestFixture]
    public class LoginTests
    {
        [SetUp]
        public void Setup()
        {
            // Setup code
        }
        
        [Test]
        public void TestValidLogin()
        {
            var result = Login("admin", "password");
            Assert.That(result, Is.True);
            Assert.AreEqual("admin", result.Username);
        }
        
        [TearDown]
        public void Cleanup()
        {
            // Cleanup code
        }
    }
}
""")
        
        extractor = DotNetASTExtractor()
        signals = extractor.extract_signals(str(test_file), "TestValidLogin")
        
        assert signals is not None
        assert len(signals.assertions) >= 2
        assert signals.has_setup
        assert signals.has_teardown
    
    def test_parse_xunit_test(self, tmp_path):
        """Test parsing xUnit test file."""
        test_file = tmp_path / "ApiTests.cs"
        test_file.write_text("""
using Xunit;

public class ApiTests
{
    [Fact]
    public void TestGetUser()
    {
        var response = GetAsync("/api/users/1");
        Assert.Equal(200, response.StatusCode);
        Assert.NotNull(response.Body);
    }
    
    [Theory]
    [InlineData("admin")]
    [InlineData("user")]
    public void TestMultipleUsers(string username)
    {
        Assert.NotNull(username);
    }
}
""")
        
        extractor = DotNetASTExtractor()
        signals = extractor.extract_signals(str(test_file), "TestGetUser")
        
        assert signals is not None
        assert len(signals.assertions) >= 2
        assert len(signals.api_calls) >= 1
    
    def test_parse_specflow_binding(self, tmp_path):
        """Test parsing SpecFlow step binding."""
        test_file = tmp_path / "LoginSteps.cs"
        test_file.write_text("""
using TechTalk.SpecFlow;

[Binding]
public class LoginSteps
{
    [Given(@"the user is on the login page")]
    public void GivenUserOnLoginPage()
    {
        Navigate("/login");
    }
    
    [When(@"the user enters '(.*)' as username")]
    public void WhenUserEntersUsername(string username)
    {
        Fill("#username", username);
    }
    
    [Then(@"the user should be logged in")]
    public void ThenUserLoggedIn()
    {
        Assert.That(IsLoggedIn(), Is.True);
    }
}
""")
        
        extractor = DotNetASTExtractor()
        test_class = parse_dotnet_test_file(str(test_file))
        
        assert test_class.name == "LoginSteps"
        assert len(test_class.methods) >= 3
        assert any("Given" in m.attributes for m in test_class.methods)
    
    def test_detect_framework(self):
        """Test framework detection."""
        extractor = DotNetASTExtractor()
        
        nunit_code = "using NUnit.Framework;\n[Test]\npublic void Test() {}"
        assert extractor._detect_framework(nunit_code) == 'nunit'
        
        xunit_code = "using Xunit;\n[Fact]\npublic void Test() {}"
        assert extractor._detect_framework(xunit_code) == 'xunit'
        
        mstest_code = "using Microsoft.VisualStudio.TestTools;\n[TestMethod]\npublic void Test() {}"
        assert extractor._detect_framework(mstest_code) == 'mstest'


# ============================================================================
# Playwright Trace Parser Tests
# ============================================================================

class TestPlaywrightTraceParser:
    """Tests for Playwright Trace Parser."""
    
    def test_parse_trace_file(self, tmp_path):
        """Test parsing Playwright trace file."""
        trace_zip = tmp_path / "trace.zip"
        
        # Create mock trace data
        trace_data = {
            "name": "login_test",
            "events": [
                {
                    "type": "action",
                    "method": "goto",
                    "params": {"url": "https://example.com"},
                    "startTime": 1000,
                    "duration": 500,
                    "metadata": {}
                },
                {
                    "type": "action",
                    "method": "click",
                    "params": {"selector": "#login-button"},
                    "startTime": 1500,
                    "duration": 200,
                    "metadata": {}
                },
                {
                    "type": "console",
                    "messageType": "error",
                    "text": "Failed to load resource",
                    "timestamp": 1600
                }
            ]
        }
        
        # Create zip file with trace
        with zipfile.ZipFile(trace_zip, 'w') as zf:
            zf.writestr('trace.json', json.dumps(trace_data))
        
        parser = PlaywrightTraceParser()
        result = parser.parse_trace(trace_zip)
        
        assert result is not None
        assert result.test_name == "login_test"
        assert len(result.actions) >= 2
        assert len(result.console_messages) >= 1
        assert len(result.errors) >= 1
    
    def test_get_failed_actions(self, tmp_path):
        """Test extracting failed actions."""
        trace_zip = tmp_path / "trace.zip"
        
        trace_data = {
            "name": "test",
            "events": [
                {
                    "type": "action",
                    "method": "click",
                    "params": {"selector": "#btn"},
                    "startTime": 1000,
                    "duration": 100,
                    "metadata": {"error": "Element not found"}
                }
            ]
        }
        
        with zipfile.ZipFile(trace_zip, 'w') as zf:
            zf.writestr('trace.json', json.dumps(trace_data))
        
        result = parse_playwright_trace(trace_zip)
        
        assert result is not None
        failed = result.get_failed_actions()
        assert len(failed) == 1
        assert failed[0].error == "Element not found"


# ============================================================================
# Cypress Results Parser Tests
# ============================================================================

class TestCypressResultsParser:
    """Tests for Cypress Results Parser."""
    
    def test_parse_mochawesome_format(self, tmp_path):
        """Test parsing Mochawesome JSON."""
        results_file = tmp_path / "results.json"
        
        mochawesome_data = {
            "stats": {
                "tests": 2,
                "passes": 1,
                "failures": 1,
                "duration": 3000,
                "start": "2026-01-30T10:00:00.000Z",
                "end": "2026-01-30T10:00:03.000Z"
            },
            "results": [
                {
                    "suites": [
                        {
                            "title": "Login Tests",
                            "tests": [
                                {
                                    "title": "should login with valid credentials",
                                    "fullTitle": "Login Tests should login with valid credentials",
                                    "state": "passed",
                                    "duration": 1500
                                },
                                {
                                    "title": "should reject invalid credentials",
                                    "fullTitle": "Login Tests should reject invalid credentials",
                                    "state": "failed",
                                    "duration": 1500,
                                    "err": {
                                        "message": "AssertionError: expected false to be true"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        results_file.write_text(json.dumps(mochawesome_data))
        
        parser = CypressResultsParser()
        result = parser.parse_results(results_file)
        
        assert result is not None
        assert len(result.suites) >= 1
        all_tests = result.get_all_tests()
        assert len(all_tests) == 2
        failed = result.get_failed_tests()
        assert len(failed) == 1
    
    def test_parse_cypress_native_format(self, tmp_path):
        """Test parsing Cypress native format."""
        results_file = tmp_path / "results.json"
        
        cypress_data = {
            "cypressVersion": "12.0.0",
            "browserName": "chrome",
            "totalTests": 3,
            "totalPassed": 2,
            "totalFailed": 1,
            "runs": [
                {
                    "spec": {"name": "login.cy.js"},
                    "tests": [
                        {
                            "title": ["Login", "should work"],
                            "state": "passed",
                            "duration": 2000
                        }
                    ],
                    "stats": {"duration": 2000}
                }
            ]
        }
        
        results_file.write_text(json.dumps(cypress_data))
        
        result = parse_cypress_results(results_file)
        
        assert result is not None
        assert result.cypress_version == "12.0.0"
        assert result.browser == "chrome"
    
    def test_find_flaky_tests(self, tmp_path):
        """Test flaky test detection."""
        # Create multiple result files
        result_files = []
        
        for i in range(3):
            file_path = tmp_path / f"run_{i}.json"
            data = {
                "tests": [
                    {"title": "stable test", "state": "passed", "duration": 1000},
                    {"title": "flaky test", "state": "passed" if i % 2 == 0 else "failed", "duration": 1000}
                ]
            }
            file_path.write_text(json.dumps(data))
            result_files.append(file_path)
        
        flaky = find_flaky_tests(result_files)
        
        assert "flaky test" in flaky
        assert "stable test" not in flaky


# ============================================================================
# Behave Results Parser Tests
# ============================================================================

class TestBehaveResultsParser:
    """Tests for Behave Results Parser."""
    
    def test_parse_behave_json(self, tmp_path):
        """Test parsing Behave JSON output."""
        results_file = tmp_path / "behave_results.json"
        
        behave_data = [
            {
                "keyword": "Feature",
                "name": "Login Feature",
                "description": "",
                "line": 1,
                "tags": [{"name": "@smoke", "line": 1}],
                "elements": [
                    {
                        "type": "scenario",
                        "keyword": "Scenario",
                        "name": "Valid login",
                        "line": 5,
                        "tags": [],
                        "steps": [
                            {
                                "keyword": "Given ",
                                "name": "the user is on the login page",
                                "step_type": "given",
                                "line": 6,
                                "result": {
                                    "status": "passed",
                                    "duration": 0.5
                                }
                            },
                            {
                                "keyword": "When ",
                                "name": "the user enters valid credentials",
                                "step_type": "when",
                                "line": 7,
                                "result": {
                                    "status": "passed",
                                    "duration": 1.0
                                }
                            },
                            {
                                "keyword": "Then ",
                                "name": "the user should be logged in",
                                "step_type": "then",
                                "line": 8,
                                "result": {
                                    "status": "passed",
                                    "duration": 0.3
                                }
                            }
                        ]
                    }
                ]
            }
        ]
        
        results_file.write_text(json.dumps(behave_data))
        
        parser = BehaveResultsParser()
        result = parser.parse_json(results_file)
        
        assert result is not None
        assert len(result.features) == 1
        assert result.features[0].name == "Login Feature"
        scenarios = result.get_all_scenarios()
        assert len(scenarios) == 1
        assert scenarios[0].name == "Valid login"
        assert len(scenarios[0].steps) == 3
    
    def test_analyze_behave_failures(self, tmp_path):
        """Test analyzing Behave failures."""
        results_file = tmp_path / "behave_results.json"
        
        behave_data = [
            {
                "name": "Feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Failed scenario",
                        "steps": [
                            {
                                "keyword": "When ",
                                "name": "step fails",
                                "step_type": "when",
                                "result": {
                                    "status": "failed",
                                    "duration": 0.1,
                                    "error_message": "AssertionError: expected True"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
        
        results_file.write_text(json.dumps(behave_data))
        
        analysis = analyze_behave_failures(results_file)
        
        assert analysis['total_failures'] >= 1
        assert analysis['failed_when_steps'] >= 1


# ============================================================================
# Selenium Log Parser Tests
# ============================================================================

class TestSeleniumLogParser:
    """Tests for Selenium Log Parser."""
    
    def test_parse_selenium_logs(self, tmp_path):
        """Test parsing Selenium browser logs."""
        log_file = tmp_path / "selenium_logs.json"
        
        log_data = [
            {
                "timestamp": "2026-01-30T10:00:00.000Z",
                "level": "INFO",
                "source": "browser",
                "message": "Page loaded"
            },
            {
                "timestamp": "2026-01-30T10:00:01.000Z",
                "level": "ERROR",
                "source": "network",
                "message": "Failed to load resource: net::ERR_CONNECTION_REFUSED"
            },
            {
                "timestamp": "2026-01-30T10:00:02.000Z",
                "level": "WARNING",
                "source": "browser",
                "message": "Cookie SameSite attribute missing"
            }
        ]
        
        log_file.write_text(json.dumps(log_data))
        
        parser = SeleniumLogParser()
        result = parser.parse_json_logs(log_file)
        
        assert result is not None
        assert len(result.entries) == 3
        errors = result.get_errors()
        assert len(errors) == 1
        assert "ERR_CONNECTION_REFUSED" in errors[0].message
        warnings = result.get_warnings()
        assert len(warnings) == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestParserIntegration:
    """Integration tests for multiple parsers."""
    
    def test_all_parsers_available(self):
        """Test that all parsers can be instantiated."""
        dotnet_parser = DotNetASTExtractor()
        playwright_parser = PlaywrightTraceParser()
        cypress_parser = CypressResultsParser()
        behave_parser = BehaveResultsParser()
        selenium_parser = SeleniumLogParser()
        
        assert dotnet_parser is not None
        assert playwright_parser is not None
        assert cypress_parser is not None
        assert behave_parser is not None
        assert selenium_parser is not None
    
    def test_parser_error_handling(self, tmp_path):
        """Test parsers handle errors gracefully."""
        missing_file = tmp_path / "missing.json"
        
        # All parsers should return None for missing files
        assert parse_playwright_trace(missing_file) is None
        assert parse_cypress_results(missing_file) is None
        assert parse_behave_results(missing_file) is None
        assert parse_selenium_logs(missing_file) is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
