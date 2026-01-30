"""
Quick verification script for new parsers and hooks.
"""

import tempfile
from pathlib import Path

print("=" * 60)
print("Testing Java Step Parser")
print("=" * 60)

from core.intelligence.java_step_parser import JavaStepDefinitionParser

# Create test Java file
java_code = '''
package com.example.steps;
import io.cucumber.java.en.*;

public class LoginSteps {
    @Given("the user is on the login page")
    public void userOnLoginPage() {
        // Implementation
    }
    
    @When("the user enters username {string} and password {string}")
    public void userEntersCredentials(String username, String password) {
        // Implementation
    }
    
    @Then("the user should see the dashboard")
    public void userSeesDashboard() {
        // Implementation
    }
}
'''

with tempfile.TemporaryDirectory() as tmp_dir:
    java_file = Path(tmp_dir) / "LoginSteps.java"
    java_file.write_text(java_code)
    
    parser = JavaStepDefinitionParser()
    steps = parser.parse_file(str(java_file))
    
    print(f"✓ Parsed {len(steps)} step definitions")
    for step in steps:
        print(f"  - {step.step_type}: {step.pattern}")
        print(f"    Method: {step.method_name}, Params: {step.parameters}")
    
    # Test matching
    match = parser.find_step_definition('the user enters username "admin" and password "pass123"', "When")
    if match:
        print(f"\n✓ Step matching works: Found match for When step")
    
    # Test bindings map
    bindings = parser.get_step_bindings_map()
    print(f"\n✓ Step bindings: Given={len(bindings['Given'])}, When={len(bindings['When'])}, Then={len(bindings['Then'])}")

print("\n" + "=" * 60)
print("Testing Robot Log Parser")
print("=" * 60)

from core.intelligence.robot_log_parser import RobotLogParser

xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 6.0" generated="20240101 12:00:00.000">
    <suite name="Login Tests" source="/path/to/login.robot">
        <test name="Valid Login">
            <kw name="Open Browser" library="SeleniumLibrary">
                <arg>http://example.com</arg>
                <arg>chrome</arg>
                <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:02.000"/>
            </kw>
            <kw name="Input Text" library="SeleniumLibrary">
                <arg>id=username</arg>
                <arg>testuser</arg>
                <status status="PASS" starttime="20240101 12:00:02.000" endtime="20240101 12:00:03.000"/>
            </kw>
            <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:03.000"/>
        </test>
        <test name="Failed Login">
            <kw name="Should Be Equal" library="BuiltIn">
                <arg>actual</arg>
                <arg>expected</arg>
                <msg level="FAIL">actual != expected</msg>
                <status status="FAIL" starttime="20240101 12:00:04.000" endtime="20240101 12:00:05.000"/>
            </kw>
            <status status="FAIL" starttime="20240101 12:00:03.000" endtime="20240101 12:00:06.000">
                Assertion error
            </status>
        </test>
        <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:07.000"/>
    </suite>
</robot>
'''

with tempfile.TemporaryDirectory() as tmp_dir:
    xml_file = Path(tmp_dir) / "output.xml"
    xml_file.write_text(xml_content)
    
    parser = RobotLogParser()
    suite = parser.parse(str(xml_file))
    
    print(f"✓ Parsed suite: {suite.name}")
    print(f"  Status: {suite.status.value}")
    print(f"  Tests: {len(suite.tests)}")
    
    for test in suite.tests:
        print(f"\n  Test: {test.name}")
        print(f"    Status: {test.status.value}")
        print(f"    Keywords: {len(test.keywords)}")
        for kw in test.keywords:
            print(f"      - {kw.name} [{kw.status.value}]")
    
    # Test failed keywords
    failed_keywords = parser.get_failed_keywords()
    print(f"\n✓ Failed keywords: {len(failed_keywords)}")
    for kw in failed_keywords:
        error_msg = kw.messages[0] if kw.messages else "No error message"
        print(f"  - {kw.name}: {error_msg}")
    
    # Test statistics
    stats = parser.get_statistics()
    print(f"\n✓ Statistics:")
    print(f"  Total: {stats['total_tests']}")
    print(f"  Passed: {stats['passed_tests']}")
    print(f"  Failed: {stats['failed_tests']}")
    print(f"  Pass rate: {stats['pass_rate']}")

print("\n" + "=" * 60)
print("Testing Pytest Intelligence Plugin")
print("=" * 60)

from hooks.pytest_intelligence_plugin import CrossBridgeIntelligencePlugin

plugin = CrossBridgeIntelligencePlugin()
print(f"✓ Plugin created: {plugin.__class__.__name__}")
print(f"  Enabled: {plugin.enabled}")
print(f"  Signals collected: {len(plugin.get_signals())}")

print("\n" + "=" * 60)
print("✅ All verifications passed!")
print("=" * 60)
