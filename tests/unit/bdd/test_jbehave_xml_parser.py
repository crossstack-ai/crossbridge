"""
Comprehensive test suite for JBehave XML execution parser.

Tests the newly implemented XML parser that promoted JBehave from Beta to Stable.
"""
import pytest
from pathlib import Path
from adapters.java.jbehave_adapter import JBehaveExecutionParser, JBehaveAdapter
from core.bdd.models import BDDFailure


class TestJBehaveXMLParser:
    """Test JBehave XML execution parser."""
    
    def test_parse_passing_scenarios(self, tmp_path):
        """Test parsing XML with passing scenarios."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="LoginStory" tests="2" failures="0" errors="0" skipped="0" time="2.5">
    <testcase classname="com.example.LoginStory" name="User logs in with valid credentials" time="1.2">
    </testcase>
    <testcase classname="com.example.LoginStory" name="User sees dashboard after login" time="1.3">
    </testcase>
</testsuite>
"""
        xml_file = tmp_path / "jbehave-results.xml"
        xml_file.write_text(xml_content)
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert len(results) == 2
        
        # First scenario
        assert results[0].scenario_name == "User logs in with valid credentials"
        assert results[0].feature_name == "LoginStory"
        assert results[0].status == "passed"
        assert results[0].duration_ns == 1_200_000_000  # 1.2 seconds
        assert results[0].failure is None
        
        # Second scenario
        assert results[1].scenario_name == "User sees dashboard after login"
        assert results[1].status == "passed"
        assert results[1].duration_ns == 1_300_000_000  # 1.3 seconds
    
    def test_parse_failing_scenarios(self, tmp_path):
        """Test parsing XML with failing scenarios."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="CheckoutStory" tests="2" failures="1" errors="0" skipped="0" time="3.0">
    <testcase classname="com.example.CheckoutStory" name="Add item to cart" time="1.0">
    </testcase>
    <testcase classname="com.example.CheckoutStory" name="Checkout with invalid card" time="2.0">
        <failure type="org.junit.ComparisonFailure" message="Expected error not displayed">
java.lang.AssertionError: Expected error message not found
    at com.example.CheckoutSteps.verifyError(CheckoutSteps.java:45)
    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
        </failure>
    </testcase>
</testsuite>
"""
        xml_file = tmp_path / "jbehave-results.xml"
        xml_file.write_text(xml_content)
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert len(results) == 2
        
        # Passing scenario
        assert results[0].status == "passed"
        assert results[0].failure is None
        
        # Failing scenario
        assert results[1].scenario_name == "Checkout with invalid card"
        assert results[1].status == "failed"
        assert results[1].failure is not None
        assert results[1].failure.error_type == "org.junit.ComparisonFailure"
        assert "Expected error not displayed" in results[1].failure.error_message
        assert "CheckoutSteps.java:45" in results[1].failure.stacktrace
    
    def test_parse_error_scenarios(self, tmp_path):
        """Test parsing XML with error scenarios."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="ApiStory" tests="1" failures="0" errors="1" skipped="0" time="1.5">
    <testcase classname="com.example.ApiStory" name="API returns data" time="1.5">
        <error type="java.net.ConnectException" message="Connection refused">
java.net.ConnectException: Connection refused
    at java.net.PlainSocketImpl.socketConnect(Native Method)
    at com.example.ApiClient.connect(ApiClient.java:23)
        </error>
    </testcase>
</testsuite>
"""
        xml_file = tmp_path / "jbehave-results.xml"
        xml_file.write_text(xml_content)
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert len(results) == 1
        assert results[0].status == "error"
        assert results[0].failure is not None
        assert results[0].failure.error_type == "java.net.ConnectException"
        assert "Connection refused" in results[0].failure.error_message
        assert "ApiClient.java:23" in results[0].failure.stacktrace
    
    def test_parse_skipped_scenarios(self, tmp_path):
        """Test parsing XML with skipped scenarios."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="FeatureStory" tests="2" failures="0" errors="0" skipped="1" time="1.0">
    <testcase classname="com.example.FeatureStory" name="Enabled scenario" time="1.0">
    </testcase>
    <testcase classname="com.example.FeatureStory" name="Disabled scenario" time="0">
        <skipped message="Test ignored" />
    </testcase>
</testsuite>
"""
        xml_file = tmp_path / "jbehave-results.xml"
        xml_file.write_text(xml_content)
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert len(results) == 2
        assert results[0].status == "passed"
        assert results[1].status == "skipped"
        assert results[1].failure is None
    
    def test_parse_testsuites_root(self, tmp_path):
        """Test parsing XML with <testsuites> root element."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite name="Story1" tests="1" failures="0" errors="0" skipped="0" time="1.0">
        <testcase classname="com.example.Story1" name="Scenario A" time="1.0">
        </testcase>
    </testsuite>
    <testsuite name="Story2" tests="1" failures="0" errors="0" skipped="0" time="1.5">
        <testcase classname="com.example.Story2" name="Scenario B" time="1.5">
        </testcase>
    </testsuite>
</testsuites>
"""
        xml_file = tmp_path / "jbehave-results.xml"
        xml_file.write_text(xml_content)
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert len(results) == 2
        assert results[0].feature_name == "Story1"
        assert results[0].scenario_name == "Scenario A"
        assert results[1].feature_name == "Story2"
        assert results[1].scenario_name == "Scenario B"
    
    def test_parse_invalid_xml(self, tmp_path):
        """Test parsing invalid XML returns empty list."""
        xml_file = tmp_path / "invalid.xml"
        xml_file.write_text("not valid xml </>")
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert results == []
    
    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing nonexistent file returns empty list."""
        xml_file = tmp_path / "nonexistent.xml"
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert results == []
    
    def test_scenario_id_generation(self, tmp_path):
        """Test scenario ID matches story parser format."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="LoginStory" tests="1" failures="0" errors="0" skipped="0" time="1.0">
    <testcase classname="com.example.LoginStory" name="Valid login" time="1.0">
    </testcase>
</testsuite>
"""
        xml_file = tmp_path / "jbehave-results.xml"
        xml_file.write_text(xml_content)
        
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        assert len(results) == 1
        assert results[0].scenario_id == "LoginStory::Valid login"


class TestJBehaveAdapterCompleteness:
    """Test JBehave adapter completeness after XML parser implementation."""
    
    def test_adapter_is_now_stable(self):
        """Test that JBehave adapter meets all 10 completeness criteria."""
        adapter = JBehaveAdapter()
        completeness = adapter.validate_completeness()
        
        # Verify all 10 criteria are True
        assert completeness["discovery"] is True
        assert completeness["feature_parsing"] is True
        assert completeness["scenario_extraction"] is True
        assert completeness["step_extraction"] is True
        assert completeness["tag_extraction"] is True
        assert completeness["step_definition_mapping"] is True
        assert completeness["execution_parsing"] is True  # ✅ Now True
        assert completeness["failure_mapping"] is True
        assert completeness["embedding_compatibility"] is True
        assert completeness["graph_compatibility"] is True
        
        # All criteria met - STABLE status
        assert all(completeness.values())
    
    def test_execution_parser_available(self):
        """Test that execution parser is properly initialized."""
        adapter = JBehaveAdapter()
        
        assert adapter.execution_parser is not None
        assert hasattr(adapter.execution_parser, 'parse_execution_report')
        assert "xml" in adapter.execution_parser.supported_report_formats


class TestJBehaveExecutionIntegration:
    """Integration tests for JBehave execution parsing."""
    
    def test_full_execution_workflow(self, tmp_path):
        """Test complete workflow: parse XML, link failures, verify results."""
        # Create sample XML report
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="UserManagementStory" tests="3" failures="1" errors="0" skipped="0" time="5.0">
    <testcase classname="com.example.UserManagementStory" name="Create new user" time="2.0">
    </testcase>
    <testcase classname="com.example.UserManagementStory" name="Update user email" time="1.5">
        <failure type="AssertionError" message="Email not updated">
Expected: new@example.com
Actual: old@example.com
        </failure>
    </testcase>
    <testcase classname="com.example.UserManagementStory" name="Delete user" time="1.5">
    </testcase>
</testsuite>
"""
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)
        
        # Parse execution results
        parser = JBehaveExecutionParser()
        results = parser.parse_execution_report(xml_file)
        
        # Verify parsing
        assert len(results) == 3
        
        # Check passed scenarios
        passed = [r for r in results if r.status == "passed"]
        assert len(passed) == 2
        
        # Check failed scenarios
        failed = [r for r in results if r.status == "failed"]
        assert len(failed) == 1
        assert failed[0].scenario_name == "Update user email"
        assert failed[0].failure is not None
        assert "Email not updated" in failed[0].failure.error_message
        
        # Verify total duration
        total_duration_seconds = sum(r.duration_ns for r in results) / 1_000_000_000
        assert abs(total_duration_seconds - 5.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
