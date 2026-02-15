"""
Unit Tests for TestNG Parser

Tests structured parsing of testng-results.xml files.
"""

import pytest
from pathlib import Path
from textwrap import dedent
import tempfile
import xml.etree.ElementTree as ET

from core.log_analysis.ingestion import TestNGParser, StructuredFailure, FailureCategory


class TestTestNGParser:
    """Test TestNG XML parsing functionality"""
    
    @pytest.fixture
    def sample_testng_xml(self, tmp_path):
        """Create a sample TestNG XML file"""
        xml_content = dedent('''
            <?xml version="1.0" encoding="UTF-8"?>
            <testng-results>
                <suite name="Test Suite" duration-ms="5000">
                    <test name="Smoke Tests" duration-ms="3000">
                        <class name="com.example.LoginTest">
                            <test-method status="PASS" name="testValidLogin" 
                                        duration-ms="1000" started-at="2024-01-15T10:00:00">
                            </test-method>
                            <test-method status="FAIL" name="testInvalidPassword" 
                                        duration-ms="500" started-at="2024-01-15T10:00:01">
                                <exception class="java.lang.AssertionError">
                                    <message>Expected error message not displayed</message>
                                    <full-stacktrace>
                                        at com.example.LoginTest.testInvalidPassword(LoginTest.java:45)
                                        at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
                                    </full-stacktrace>
                                </exception>
                            </test-method>
                        </class>
                        <class name="com.example.TimeoutTest">
                            <test-method status="FAIL" name="testSlowOperation" 
                                        duration-ms="30000" started-at="2024-01-15T10:00:02">
                                <exception class="org.openqa.selenium.TimeoutException">
                                    <message>Timeout waiting for element</message>
                                    <full-stacktrace>
                                        at org.openqa.selenium.support.ui.WebDriverWait.timeoutException
                                    </full-stacktrace>
                                </exception>
                            </test-method>
                        </class>
                    </test>
                    <test name="Regression Tests" duration-ms="2000">
                        <class name="com.example.DataTest">
                            <test-method status="SKIP" name="testDataImport" 
                                        duration-ms="0" started-at="2024-01-15T10:00:03">
                            </test-method>
                        </class>
                    </test>
                </suite>
            </testng-results>
        ''').strip()
        
        xml_file = tmp_path / "testng-results.xml"
        xml_file.write_text(xml_content)
        return xml_file
    
    def test_parse_basic_structure(self, sample_testng_xml):
        """Test parsing basic TestNG structure"""
        parser = TestNGParser()
        failures = parser.parse(sample_testng_xml)
        
        # Should parse all test methods (PASS, FAIL, SKIP)
        assert len(failures) == 4
        
        # Check summary statistics
        summary = parser.get_summary()
        assert summary['total_tests'] == 4
        assert summary['passed'] == 1
        assert summary['failed'] == 2
        assert summary['skipped'] == 1
        assert summary['pass_rate'] == 25.0
    
    def test_parse_passed_test(self, sample_testng_xml):
        """Test parsing passed test"""
        parser = TestNGParser()
        parser.parse(sample_testng_xml)
        
        passed_tests = parser.get_passed()
        assert len(passed_tests) == 1
        
        test = passed_tests[0]
        assert test.test_name == "com.example.LoginTest.testValidLogin"
        assert test.class_name == "com.example.LoginTest"
        assert test.method_name == "testValidLogin"
        assert test.status == "PASS"
        assert test.duration_ms == 1000
        assert test.is_passed()
    
    def test_parse_failed_test_with_assertion(self, sample_testng_xml):
        """Test parsing failed test with assertion error"""
        parser = TestNGParser()
        parser.parse(sample_testng_xml)
        
        failed_tests = parser.get_failures()
        assertion_failure = [
            f for f in failed_tests 
            if f.method_name == "testInvalidPassword"
        ][0]
        
        assert assertion_failure.status == "FAIL"
        assert assertion_failure.failure_type == "java.lang.AssertionError"
        assert "Expected error message" in assertion_failure.error_message
        assert assertion_failure.stack_trace is not None
        assert "LoginTest.java:45" in assertion_failure.stack_trace
        assert assertion_failure.category == FailureCategory.TEST_ASSERTION
        assert not assertion_failure.infra_related
    
    def test_parse_failed_test_with_timeout(self, sample_testng_xml):
        """Test parsing failed test with timeout"""
        parser = TestNGParser()
        parser.parse(sample_testng_xml)
        
        failed_tests = parser.get_failures()
        timeout_failure = [
            f for f in failed_tests 
            if f.method_name == "testSlowOperation"
        ][0]
        
        assert timeout_failure.status == "FAIL"
        assert timeout_failure.failure_type == "org.openqa.selenium.TimeoutException"
        assert "Timeout" in timeout_failure.error_message
        assert timeout_failure.category == FailureCategory.INFRASTRUCTURE
        assert timeout_failure.duration_ms == 30000
    
    def test_parse_skipped_test(self, sample_testng_xml):
        """Test parsing skipped test"""
        parser = TestNGParser()
        failures = parser.parse(sample_testng_xml)
        
        skipped = [f for f in failures if f.is_skipped()]
        assert len(skipped) == 1
        
        test = skipped[0]
        assert test.method_name == "testDataImport"
        assert test.status == "SKIP"
        assert test.duration_ms == 0
    
    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing nonexistent file"""
        parser = TestNGParser()
        nonexistent = tmp_path / "does-not-exist.xml"
        
        failures = parser.parse(nonexistent)
        assert len(failures) == 0
    
    def test_parse_malformed_xml(self, tmp_path):
        """Test parsing malformed XML"""
        malformed_file = tmp_path / "malformed.xml"
        malformed_file.write_text("<testng-results><unclosed>")
        
        parser = TestNGParser()
        # Should raise ValueError on malformed XML
        with pytest.raises(ValueError) as exc_info:
            parser.parse(malformed_file)
        assert "Invalid TestNG XML format" in str(exc_info.value)
    
    def test_categorization_infrastructure(self):
        """Test infrastructure failure categorization"""
        parser = TestNGParser()
        
        # Timeout
        category = parser._categorize_failure(
            "java.util.concurrent.TimeoutException",
            "Operation timed out after 30s",
            None
        )
        assert category == FailureCategory.INFRASTRUCTURE
        
        # Connection
        category = parser._categorize_failure(
            "java.net.ConnectException",
            "Connection refused",
            None
        )
        assert category == FailureCategory.INFRASTRUCTURE
        
        # WebDriver
        category = parser._categorize_failure(
            "org.openqa.selenium.SessionNotCreatedException",
            "Session not created",
            None
        )
        assert category == FailureCategory.INFRASTRUCTURE
    
    def test_categorization_test_assertion(self):
        """Test assertion failure categorization"""
        parser = TestNGParser()
        
        # AssertionError
        category = parser._categorize_failure(
            "java.lang.AssertionError",
            "Expected true but was false",
            None
        )
        assert category == FailureCategory.TEST_ASSERTION
        
        # AssertionFailedError
        category = parser._categorize_failure(
            "org.junit.AssertionFailedError",
            "Values did not match",
            None
        )
        assert category == FailureCategory.TEST_ASSERTION
    
    def test_categorization_environment(self):
        """Test environment failure categorization"""
        parser = TestNGParser()
        
        # FileNotFound
        category = parser._categorize_failure(
            "java.io.FileNotFoundException",
            "Config file not found",
            None
        )
        assert category == FailureCategory.ENVIRONMENT
        
        # NullPointer
        category = parser._categorize_failure(
            "java.lang.NullPointerException",
            "Unexpected null value",
            None
        )
        assert category == FailureCategory.ENVIRONMENT
    
    def test_categorization_application(self):
        """Test application failure categorization"""
        parser = TestNGParser()
        
        category = parser._categorize_failure(
            "java.lang.RuntimeException",
            "Server returned 500 Internal Server Error",
            None
        )
        assert category == FailureCategory.APPLICATION
    
    def test_short_error_extraction(self):
        """Test short error message extraction"""
        failure = StructuredFailure(
            test_name="test",
            class_name="TestClass",
            error_message="First line\nSecond line\nThird line"
        )
        
        short = failure.short_error()
        assert short == "First line"
        assert len(short) <= 100
    
    def test_empty_test_suite(self, tmp_path):
        """Test parsing empty test suite"""
        xml_content = dedent('''
            <?xml version="1.0" encoding="UTF-8"?>
            <testng-results>
                <suite name="Empty Suite" duration-ms="0">
                </suite>
            </testng-results>
        ''').strip()
        
        xml_file = tmp_path / "empty.xml"
        xml_file.write_text(xml_content)
        
        parser = TestNGParser()
        failures = parser.parse(xml_file)
        
        assert len(failures) == 0
        summary = parser.get_summary()
        assert summary['total_tests'] == 0
        assert summary['pass_rate'] == 0.0


class TestTestNGParserGetAll:
    """Test get_all() method that returns all tests"""
    
    @pytest.fixture
    def mixed_results_xml(self, tmp_path):
        """Create TestNG XML with passed, failed, and skipped tests"""
        xml_content = dedent('''
            <?xml version="1.0" encoding="UTF-8"?>
            <testng-results>
                <suite name="Mixed Results Suite" duration-ms="10000">
                    <test name="All States Test" duration-ms="10000">
                        <class name="com.example.MixedTest">
                            <test-method status="PASS" name="testPassed1" 
                                        duration-ms="1000" started-at="2024-01-15T10:00:00">
                            </test-method>
                            <test-method status="PASS" name="testPassed2" 
                                        duration-ms="2000" started-at="2024-01-15T10:00:01">
                            </test-method>
                            <test-method status="FAIL" name="testFailed1" 
                                        duration-ms="500" started-at="2024-01-15T10:00:02">
                                <exception class="java.lang.AssertionError">
                                    <message>Test failed</message>
                                </exception>
                            </test-method>
                            <test-method status="SKIP" name="testSkipped1" 
                                        duration-ms="0" started-at="2024-01-15T10:00:03">
                            </test-method>
                            <test-method status="FAIL" name="testFailed2" 
                                        duration-ms="1500" started-at="2024-01-15T10:00:04">
                                <exception class="java.lang.NullPointerException">
                                    <message>NPE occurred</message>
                                </exception>
                            </test-method>
                        </class>
                    </test>
                </suite>
            </testng-results>
        ''').strip()
        
        xml_file = tmp_path / "mixed.xml"
        xml_file.write_text(xml_content)
        return xml_file
    
    def test_get_all_returns_all_tests(self, mixed_results_xml):
        """Test that get_all() returns all tests regardless of status"""
        parser = TestNGParser()
        parser.parse(mixed_results_xml)
        
        all_tests = parser.get_all()
        
        # Should return all 5 tests
        assert len(all_tests) == 5
        
        # Verify we have each status
        statuses = [t.status for t in all_tests]
        assert statuses.count("PASS") == 2
        assert statuses.count("FAIL") == 2
        assert statuses.count("SKIP") == 1
    
    def test_get_all_vs_get_failures(self, mixed_results_xml):
        """Test that get_all() returns more than just failures"""
        parser = TestNGParser()
        parser.parse(mixed_results_xml)
        
        all_tests = parser.get_all()
        failures = parser.get_failures()
        passed = parser.get_passed()
        
        # get_all() should return all tests
        assert len(all_tests) == 5
        
        # get_failures() should only return failed tests
        assert len(failures) == 2
        
        # get_passed() should only return passed tests
        assert len(passed) == 2
        
        # Combined failures + passed should be less than all (missing skipped)
        assert len(failures) + len(passed) < len(all_tests)
    
    def test_get_all_includes_duration(self, mixed_results_xml):
        """Test that all tests include duration information"""
        parser = TestNGParser()
        parser.parse(mixed_results_xml)
        
        all_tests = parser.get_all()
        
        # Check that all tests have duration
        for test in all_tests:
            assert hasattr(test, 'duration_ms')
            assert isinstance(test.duration_ms, int)
        
        # Verify durations are correct
        durations = sorted([t.duration_ms for t in all_tests])
        assert durations == [0, 500, 1000, 1500, 2000]
    
    def test_get_all_preserves_test_details(self, mixed_results_xml):
        """Test that get_all() preserves all test details"""
        parser = TestNGParser()
        parser.parse(mixed_results_xml)
        
        all_tests = parser.get_all()
        
        # Check first passed test
        passed_test = [t for t in all_tests if t.status == "PASS"][0]
        assert passed_test.class_name == "com.example.MixedTest"
        assert passed_test.method_name in ["testPassed1", "testPassed2"]
        assert passed_test.test_name.startswith("com.example.MixedTest.")
        
        # Check failed test has error details
        failed_test = [t for t in all_tests if t.status == "FAIL"][0]
        assert failed_test.error_message is not None
        assert failed_test.failure_type is not None

