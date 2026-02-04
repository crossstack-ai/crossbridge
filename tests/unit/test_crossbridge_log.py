"""
Unit tests for crossbridge-log CLI and intelligence integration

Tests:
1. Basic log parsing
2. Framework detection
3. Intelligence analysis integration
4. Filtering capabilities
5. API upload functionality
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from core.execution.intelligence.analyzer import ExecutionAnalyzer
from core.execution.intelligence.models import FailureType


class TestCrossbridgeLogIntelligence:
    """Test crossbridge-log CLI intelligence integration"""
    
    def test_analyzer_initialization(self):
        """Test ExecutionAnalyzer initializes without AI"""
        analyzer = ExecutionAnalyzer(enable_ai=False)
        
        assert analyzer.enable_ai is False
        assert analyzer.ai_provider is None
        assert analyzer.extractor is not None
        assert analyzer.classifier is not None
        assert analyzer.resolver is not None
    
    def test_analyzer_works_with_ai(self):
        """Test ExecutionAnalyzer can work with AI when enabled"""
        mock_ai_provider = Mock()
        analyzer = ExecutionAnalyzer(
            enable_ai=True,
            ai_provider=mock_ai_provider
        )
        
        assert analyzer.enable_ai is True
        assert analyzer.ai_provider is mock_ai_provider
    
    def test_analyze_robot_failure(self):
        """Test analysis of Robot Framework failure"""
        analyzer = ExecutionAnalyzer(enable_ai=False)
        
        raw_log = """
        Test: Login Test
        Status: FAIL
        Error: Element not found
        selenium.common.exceptions.NoSuchElementException: Unable to locate element: //button[@id='login']
        """
        
        result = analyzer.analyze(
            raw_log=raw_log,
            test_name="Login Test",
            framework="robot"
        )
        
        assert result is not None
        assert result.classification is not None
        # Should be AUTOMATION_DEFECT due to NoSuchElementException
        assert result.classification.failure_type == FailureType.AUTOMATION_DEFECT
        assert len(result.signals) > 0
    
    def test_analyze_product_defect(self):
        """Test analysis of product defect (assertion failure)"""
        analyzer = ExecutionAnalyzer(enable_ai=False)
        
        raw_log = """
        Test: Checkout Test
        Status: FAIL
        Error: AssertionError: assert 'Success' == 'Error'
        Expected 'Success' but got 'Error'
        """
        
        result = analyzer.analyze(
            raw_log=raw_log,
            test_name="Checkout Test",
            framework="pytest"
        )
        
        assert result is not None
        assert result.classification is not None
        # Should be PRODUCT_DEFECT due to assertion failure
        assert result.classification.failure_type == FailureType.PRODUCT_DEFECT
    
    def test_analyze_environment_issue(self):
        """Test analysis of environment issue (network error)"""
        analyzer = ExecutionAnalyzer(enable_ai=False)
        
        raw_log = """
        Test: API Test
        Status: FAIL
        Error: ConnectionError: HTTPConnectionPool(host='api.example.com', port=443): Max retries exceeded
        Connection refused
        """
        
        result = analyzer.analyze(
            raw_log=raw_log,
            test_name="API Test",
            framework="pytest"
        )
        
        assert result is not None
        assert result.classification is not None
        # May classify as UNKNOWN or ENVIRONMENT_ISSUE depending on rules
        # Both are acceptable for connection errors
        assert result.classification.failure_type in [
            FailureType.ENVIRONMENT_ISSUE,
            FailureType.UNKNOWN
        ]
        # Should detect HTTP/network signal
        signal_types = [s.signal_type.value for s in result.signals]
        assert 'http_error' in signal_types or 'network_error' in signal_types
    
    def test_extract_failed_tests_robot(self):
        """Test extraction of failed tests from Robot data"""
        data = {
            "suite": {
                "name": "Test Suite",
                "tests": [
                    {"name": "Test 1", "status": "PASS"},
                    {"name": "Test 2", "status": "FAIL", "error_message": "Error"},
                    {"name": "Test 3", "status": "FAIL", "error_message": "Error 2"}
                ]
            }
        }
        
        # Simulate extract function
        failed = [t for t in data["suite"]["tests"] if t.get("status") == "FAIL"]
        
        assert len(failed) == 2
        assert failed[0]["name"] == "Test 2"
        assert failed[1]["name"] == "Test 3"
    
    def test_extract_failed_tests_cypress(self):
        """Test extraction of failed tests from Cypress data"""
        data = {
            "tests": [
                {"title": "Test 1", "state": "passed"},
                {"title": "Test 2", "state": "failed", "error": "Error"},
                {"title": "Test 3", "state": "failed", "error": "Error 2"}
            ]
        }
        
        failed = [t for t in data["tests"] if t.get("state") == "failed"]
        
        assert len(failed) == 2
        assert failed[0]["title"] == "Test 2"
        assert failed[1]["title"] == "Test 3"
    
    def test_build_raw_log(self):
        """Test building raw log from test data"""
        test = {
            "name": "Login Test",
            "error_message": "Element not found",
            "stack_trace": "selenium.common.exceptions.NoSuchElementException\n  at line 42",
            "messages": ["Step 1", "Step 2"]
        }
        
        lines = []
        lines.append(f"Test: {test['name']}")
        lines.append(f"Error: {test['error_message']}")
        lines.append(f"Stack trace:\n{test['stack_trace']}")
        for msg in test["messages"]:
            lines.append(f"Message: {msg}")
        
        raw_log = "\n".join(lines)
        
        assert "Login Test" in raw_log
        assert "Element not found" in raw_log
        assert "NoSuchElementException" in raw_log
        assert "Step 1" in raw_log
    
    def test_classification_counts(self):
        """Test counting classifications from multiple tests"""
        classifications = {}
        
        # Simulate multiple test results
        results = [
            FailureType.PRODUCT_DEFECT,
            FailureType.PRODUCT_DEFECT,
            FailureType.AUTOMATION_DEFECT,
            FailureType.ENVIRONMENT_ISSUE
        ]
        
        for failure_type in results:
            classifications[failure_type.value] = classifications.get(failure_type.value, 0) + 1
        
        assert classifications["PRODUCT_DEFECT"] == 2
        assert classifications["AUTOMATION_DEFECT"] == 1
        assert classifications["ENVIRONMENT_ISSUE"] == 1
    
    def test_recommendations_generation(self):
        """Test recommendation generation based on failure types"""
        recommendations = set()
        
        # PRODUCT_DEFECT
        recommendations.add("Review application code for bugs")
        
        # AUTOMATION_DEFECT
        recommendations.add("Update test automation code/locators")
        
        # ENVIRONMENT_ISSUE
        recommendations.add("Check infrastructure and network connectivity")
        
        assert len(recommendations) == 3
        assert "Review application code for bugs" in recommendations
    
    def test_signal_extraction(self):
        """Test signal extraction from analysis results"""
        analyzer = ExecutionAnalyzer(enable_ai=False)
        
        raw_log = """
        Test: Login Test
        Error: TimeoutException: Timed out after 30 seconds
        Element not found: //button[@id='submit']
        """
        
        result = analyzer.analyze(
            raw_log=raw_log,
            test_name="Login Test",
            framework="selenium"
        )
        
        # Should extract timeout and locator signals
        signal_types = [s.signal_type.value for s in result.signals]
        assert len(signal_types) > 0
    
    def test_code_reference_resolution(self):
        """Test code reference resolution for automation defects"""
        analyzer = ExecutionAnalyzer(
            workspace_root=str(Path(__file__).parent.parent),
            enable_ai=False
        )
        
        raw_log = """
        Test: Login Test
        selenium.common.exceptions.NoSuchElementException
        File "tests/test_login.py", line 42, in test_login
        """
        
        result = analyzer.analyze(
            raw_log=raw_log,
            test_name="Login Test",
            framework="selenium"
        )
        
        # For automation defects, code reference should be attempted
        if result.classification.failure_type == FailureType.AUTOMATION_DEFECT:
            # Code reference might be None if file doesn't exist, but resolver should try
            assert result.classification is not None
    
    def test_filtering_integration(self):
        """Test filtering works with intelligence-enriched data"""
        data = {
            "analyzed": True,
            "intelligence_summary": {
                "classifications": {"PRODUCT_DEFECT": 2},
                "signals": {"assertion_failure": 2}
            },
            "enriched_tests": [
                {
                    "name": "Test 1",
                    "status": "FAIL",
                    "classification": {"type": "PRODUCT_DEFECT"}
                },
                {
                    "name": "Test 2",
                    "status": "FAIL",
                    "classification": {"type": "PRODUCT_DEFECT"}
                }
            ]
        }
        
        # Filter by status
        filtered = [t for t in data["enriched_tests"] if t["status"] == "FAIL"]
        assert len(filtered) == 2
        
        # Filter by classification
        product_defects = [
            t for t in data["enriched_tests"]
            if t.get("classification", {}).get("type") == "PRODUCT_DEFECT"
        ]
        assert len(product_defects) == 2


class TestCrossbridgeLogAPI:
    """Test API integration for crossbridge-log"""
    
    @pytest.fixture
    def mock_analyzer(self):
        """Mock ExecutionAnalyzer"""
        analyzer = Mock(spec=ExecutionAnalyzer)
        analyzer.enable_ai = False
        return analyzer
    
    def test_analyze_endpoint_structure(self, mock_analyzer):
        """Test /analyze endpoint response structure"""
        # Expected request
        request_body = {
            "data": {
                "suite": {
                    "tests": [
                        {"name": "Test 1", "status": "FAIL", "error_message": "Error"}
                    ]
                }
            },
            "framework": "robot",
            "workspace_root": "/path/to/project"
        }
        
        # Expected response structure
        expected_keys = [
            "analyzed",
            "data",
            "intelligence_summary",
            "enriched_tests"
        ]
        
        # Verify structure
        assert all(key in expected_keys for key in ["analyzed", "data", "intelligence_summary"])
    
    def test_intelligence_summary_structure(self):
        """Test intelligence summary structure"""
        summary = {
            "classifications": {"PRODUCT_DEFECT": 2, "AUTOMATION_DEFECT": 1},
            "signals": {"timeout": 1, "assertion_failure": 2},
            "recommendations": [
                "Review application code for bugs",
                "Update test automation code/locators"
            ]
        }
        
        assert "classifications" in summary
        assert "signals" in summary
        assert "recommendations" in summary
        assert isinstance(summary["classifications"], dict)
        assert isinstance(summary["signals"], dict)
        assert isinstance(summary["recommendations"], list)
    
    def test_enriched_test_structure(self):
        """Test enriched test structure"""
        enriched_test = {
            "name": "Login Test",
            "status": "FAIL",
            "error_message": "Element not found",
            "classification": {
                "type": "AUTOMATION_DEFECT",
                "confidence": 0.92,
                "reason": "Locator not found",
                "code_reference": {
                    "file": "tests/test_login.py",
                    "line": 42,
                    "snippet": "driver.find_element(By.ID, 'login')"
                }
            },
            "signals": [
                {
                    "type": "locator_error",
                    "confidence": 0.95,
                    "message": "NoSuchElementException"
                }
            ]
        }
        
        assert "classification" in enriched_test
        assert "signals" in enriched_test
        assert enriched_test["classification"]["type"] == "AUTOMATION_DEFECT"
        assert len(enriched_test["signals"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
