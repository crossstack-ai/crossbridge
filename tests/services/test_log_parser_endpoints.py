"""
Comprehensive Unit Tests for Log Parser Endpoints

Tests all framework parsers with and without AI assistance.
Covers Robot, Cypress, Playwright, Behave, and Java parsers.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from services.sidecar_api import SidecarAPIServer
from core.sidecar.observer import SidecarObserver
from core.intelligence.robot_log_parser import RobotLogParser, RobotStatus
from core.intelligence.cypress_results_parser import CypressResultsParser
from core.intelligence.playwright_trace_parser import PlaywrightTraceParser
from core.intelligence.behave_selenium_parsers import BehaveJSONParser
from core.intelligence.java_step_parser import JavaStepDefinitionParser


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_observer():
    """Mock SidecarObserver"""
    observer = Mock(spec=SidecarObserver)
    observer.get_stats.return_value = {
        'queue_size': 100,
        'queue_capacity': 5000,
        'events_processed': 1000,
        'events_dropped': 5
    }
    observer._max_queue_size = 5000
    return observer


@pytest.fixture
def api_server(mock_observer):
    """Create API server instance"""
    server = SidecarAPIServer(observer=mock_observer, host="0.0.0.0", port=8765)
    return server


@pytest.fixture
def client(api_server):
    """Create test client"""
    return TestClient(api_server.app)


@pytest.fixture
def sample_robot_xml():
    """Sample Robot Framework output.xml"""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 6.0">
  <suite id="s1" name="Tests" source="/tests">
    <status status="PASS" start="20260205 10:00:00.000" elapsed="5.234"/>
    <test id="s1-t1" name="Test Login">
      <kw name="Log" library="BuiltIn">
        <arg>Testing login</arg>
        <status status="PASS" start="20260205 10:00:01.000" elapsed="1.000"/>
      </kw>
      <status status="PASS" start="20260205 10:00:00.500" elapsed="2.500"/>
    </test>
    <test id="s1-t2" name="Test Logout">
      <kw name="Should Be Equal" library="BuiltIn">
        <arg>expected</arg>
        <arg>actual</arg>
        <msg level="FAIL">Expected 'expected' but got 'actual'</msg>
        <status status="FAIL" start="20260205 10:00:03.000" elapsed="0.500"/>
      </kw>
      <status status="FAIL" start="20260205 10:00:03.000" elapsed="0.734"/>
    </test>
  </suite>
</robot>
"""


@pytest.fixture
def sample_cypress_json():
    """Sample Cypress results JSON"""
    return json.dumps({
        "stats": {
            "tests": 10,
            "passes": 8,
            "failures": 2,
            "pending": 0,
            "skipped": 0,
            "duration": 12345
        },
        "tests": [
            {
                "title": "should login successfully",
                "state": "passed",
                "duration": 1234
            },
            {
                "title": "should handle errors",
                "state": "failed",
                "duration": 567,
                "err": {
                    "message": "Element not found",
                    "stack": "..."
                }
            }
        ]
    }).encode()


@pytest.fixture
def sample_playwright_trace():
    """Sample Playwright trace JSON"""
    return json.dumps({
        "actions": [
            {"type": "goto", "url": "https://example.com", "timestamp": 1000},
            {"type": "click", "selector": "#login", "timestamp": 2000}
        ],
        "network": [
            {"url": "https://api.example.com/login", "status": 200, "duration": 456}
        ],
        "console": [
            {"type": "log", "text": "Application loaded", "timestamp": 1500}
        ]
    }).encode()


@pytest.fixture
def sample_behave_json():
    """Sample Behave results JSON"""
    return json.dumps([
        {
            "keyword": "Feature",
            "name": "Login",
            "elements": [
                {
                    "keyword": "Scenario",
                    "name": "Valid login",
                    "steps": [
                        {"keyword": "Given", "name": "user on login page", "result": {"status": "passed"}},
                        {"keyword": "When", "name": "user enters credentials", "result": {"status": "passed"}},
                        {"keyword": "Then", "name": "user sees dashboard", "result": {"status": "passed"}}
                    ]
                }
            ]
        }
    ]).encode()


@pytest.fixture
def sample_java_steps():
    """Sample Java step definitions"""
    return b"""
package com.example.steps;

import io.cucumber.java.en.*;

public class LoginSteps {
    @Given("user is on the login page")
    public void userIsOnLoginPage() {
        // implementation
    }
    
    @When("user enters username {string} and password {string}")
    public void userEntersCredentials(String username, String password) {
        // implementation
    }
    
    @Then("user should see the dashboard")
    public void userShouldSeeDashboard() {
        // implementation
    }
}
"""


# ============================================================================
# Test Parse Robot Endpoint
# ============================================================================

class TestParseRobotEndpoint:
    """Tests for POST /parse/robot endpoint"""
    
    def test_parse_robot_success(self, client, sample_robot_xml):
        """Test successful Robot log parsing"""
        response = client.post(
            "/parse/robot",
            content=sample_robot_xml,
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["framework"] == "robot"
        assert "suite" in data
        assert data["suite"]["total_tests"] == 2
        assert data["suite"]["passed_tests"] == 1
        assert data["suite"]["failed_tests"] == 1
        assert "statistics" in data
        assert "failed_keywords" in data
        assert len(data["failed_keywords"]) > 0
    
    def test_parse_robot_empty_content(self, client):
        """Test Robot parsing with empty content"""
        response = client.post(
            "/parse/robot",
            content=b"",
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 400
        assert "No content provided" in response.json()["detail"]
    
    def test_parse_robot_invalid_xml(self, client):
        """Test Robot parsing with invalid XML"""
        response = client.post(
            "/parse/robot",
            content=b"<invalid>xml",
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 400 or response.status_code == 500
    
    def test_parse_robot_with_ai_disabled(self, client, sample_robot_xml, monkeypatch):
        """Test Robot parsing with AI disabled"""
        # Disable AI by setting environment variable
        monkeypatch.setenv("CROSSBRIDGE_AI_ENABLED", "false")
        
        response = client.post(
            "/parse/robot",
            content=sample_robot_xml,
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["framework"] == "robot"
        # Should work without AI


# ============================================================================
# Test Parse Cypress Endpoint
# ============================================================================

class TestParseCypressEndpoint:
    """Tests for POST /parse/cypress endpoint"""
    
    def test_parse_cypress_success(self, client, sample_cypress_json):
        """Test successful Cypress results parsing"""
        response = client.post(
            "/parse/cypress",
            content=sample_cypress_json,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["framework"] == "cypress"
        assert "statistics" in data
        assert data["statistics"]["total"] == 10
        assert data["statistics"]["passed"] == 8
        assert data["statistics"]["failed"] == 2
    
    def test_parse_cypress_invalid_json(self, client):
        """Test Cypress parsing with invalid JSON"""
        response = client.post(
            "/parse/cypress",
            content=b"{invalid json}",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 500


# ============================================================================
# Test Parse Playwright Endpoint
# ============================================================================

class TestParsePlaywrightEndpoint:
    """Tests for POST /parse/playwright endpoint"""
    
    def test_parse_playwright_success(self, client, sample_playwright_trace):
        """Test successful Playwright trace parsing"""
        response = client.post(
            "/parse/playwright",
            content=sample_playwright_trace,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["framework"] == "playwright"
        assert "actions" in data or "statistics" in data


# ============================================================================
# Test Parse Behave Endpoint
# ============================================================================

class TestParseBehaveEndpoint:
    """Tests for POST /parse/behave endpoint"""
    
    def test_parse_behave_success(self, client, sample_behave_json):
        """Test successful Behave results parsing"""
        response = client.post(
            "/parse/behave",
            content=sample_behave_json,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["framework"] == "behave"
        assert "statistics" in data


# ============================================================================
# Test Parse Java Endpoint
# ============================================================================

class TestParseJavaEndpoint:
    """Tests for POST /parse/java endpoint"""
    
    def test_parse_java_success(self, client, sample_java_steps):
        """Test successful Java step definitions parsing"""
        response = client.post(
            "/parse/java",
            content=sample_java_steps,
            headers={"Content-Type": text/plain"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["framework"] == "java"
        assert data["total_steps"] == 3
        assert "step_types" in data


# ============================================================================
# Test Error Handling
# ============================================================================

class TestParserErrorHandling:
    """Tests for error handling across all parsers"""
    
    def test_unsupported_framework(self, client):
        """Test parsing with unsupported framework"""
        response = client.post(
            "/parse/unsupported",
            content=b"test content",
            headers={"Content-Type": "text/plain"}
        )
        
        assert response.status_code == 400
        assert "Unsupported framework" in response.json()["detail"]
    
    def test_empty_content_all_frameworks(self, client):
        """Test all frameworks with empty content"""
        frameworks = ["robot", "cypress", "playwright", "behave", "java"]
        
        for framework in frameworks:
            response = client.post(
                f"/parse/{framework}",
                content=b"",
                headers={"Content-Type": "application/xml"}
            )
            
            assert response.status_code == 400


# ============================================================================
# Test Integration with AI
# ============================================================================

class TestParserWithAI:
    """Tests for parser integration with AI"""
    
    @patch('core.intelligence.ai_analyzer.AIAnalyzer')
    def test_robot_parser_with_ai_analysis(self, mock_ai, client, sample_robot_xml):
        """Test Robot parser with AI failure analysis"""
        # Mock AI analyzer
        mock_ai.return_value.analyze_failure.return_value = {
            "category": "assertion_error",
            "confidence": 0.95,
            "suggestions": ["Check expected value"]
        }
        
        response = client.post(
            "/parse/robot",
            content=sample_robot_xml,
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["framework"] == "robot"


# ============================================================================
# Test Performance
# ============================================================================

class TestParserPerformance:
    """Tests for parser performance"""
    
    def test_large_robot_log_parsing(self, client):
        """Test parsing large Robot output.xml files"""
        # Generate large XML with many tests
        large_xml = b'<?xml version="1.0"?><robot generator="Robot 6.0">'
        large_xml += b'<suite id="s1" name="Tests">'
        
        for i in range(100):
            large_xml += f"""
            <test id="s1-t{i}" name="Test {i}">
                <kw name="Log" library="BuiltIn">
                    <status status="PASS" start="20260205 10:00:00.000" elapsed="0.1"/>
                </kw>
                <status status="PASS" start="20260205 10:00:00.000" elapsed="0.2"/>
            </test>
            """.encode()
        
        large_xml += b'<status status="PASS" start="20260205 10:00:00.000" elapsed="20.0"/>'
        large_xml += b'</suite></robot>'
        
        import time
        start = time.time()
        
        response = client.post(
            "/parse/robot",
            content=large_xml,
            headers={"Content-Type": "application/xml"}
        )
        
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0  # Should parse in under 5 seconds


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
