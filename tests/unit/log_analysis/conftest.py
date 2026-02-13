"""Shared test fixtures for log_analysis tests"""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_testng_xml(temp_workspace):
    """Create a sample TestNG XML file"""
    xml_file = temp_workspace / "testng-results.xml"
    xml_file.write_text("""
        <?xml version="1.0" encoding="UTF-8"?>
        <testng-results>
            <suite name="Test Suite">
                <test name="Unit Tests">
                    <class name="com.example.Test">
                        <test-method status="PASS" name="testPass" duration-ms="100"/>
                        <test-method status="FAIL" name="testFail" duration-ms="200">
                            <exception class="AssertionError">
                                <message>Test failed</message>
                            </exception>
                        </test-method>
                    </class>
                </test>
            </suite>
        </testng-results>
    """)
    return xml_file


@pytest.fixture
def sample_framework_log(temp_workspace):
    """Create a sample framework log file"""
    log_file = temp_workspace / "framework.log"
    log_file.write_text("""
        2024-01-15 10:00:00,000 INFO [Test] - Starting test
        2024-01-15 10:00:01,000 ERROR [Test] - Test failed
        java.lang.AssertionError: Test failed
            at Test.testFail(Test.java:10)
        2024-01-15 10:00:02,000 INFO [Test] - Test completed
    """)
    return log_file
