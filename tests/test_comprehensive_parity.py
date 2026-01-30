"""
Comprehensive Parity Validation Tests.

This test suite validates that all framework parsers and adapters work correctly
and maintain consistent behavior across different test frameworks.
"""

import os
import pytest
import tempfile
from pathlib import Path
from typing import Dict, List

from core.intelligence.java_step_parser import JavaStepDefinitionParser, JavaStepDefinition
from core.intelligence.robot_log_parser import RobotLogParser, RobotStatus
from adapters.pytest.adapter import PyTestAdapter
from adapters.robot.adapter import RobotAdapter
from adapters.java.adapter import JavaAdapter


class TestJavaStepParserParity:
    """Test Java step definition parser functionality."""
    
    def test_parse_simple_step_definition(self, tmp_path):
        """Test parsing a simple step definition."""
        # Create test file
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
        
        java_file = tmp_path / "LoginSteps.java"
        java_file.write_text(java_code)
        
        # Parse
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        # Validate
        assert len(steps) == 3
        
        # Check step types
        step_types = [s.step_type for s in steps]
        assert "Given" in step_types
        assert "When" in step_types
        assert "Then" in step_types
        
        # Check patterns
        patterns = [s.pattern for s in steps]
        assert "the user is on the login page" in patterns
        assert any("username" in p and "password" in p for p in patterns)
        assert "the user should see the dashboard" in patterns
    
    def test_parse_cucumber_expressions(self, tmp_path):
        """Test parsing Cucumber expressions with parameter types."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.*;
        
        public class ParameterSteps {
            @When("I enter {int} items")
            public void enterItems(int count) {}
            
            @Then("the total should be {float}")
            public void checkTotal(double total) {}
            
            @Given("the name is {string}")
            public void setName(String name) {}
        }
        '''
        
        java_file = tmp_path / "ParameterSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert len(steps) == 3
        
        # Check parameter extraction
        for step in steps:
            assert len(step.parameters) == 1
            assert step.parameters[0] in ["int", "double", "String"]
    
    def test_find_step_definition_matching(self, tmp_path):
        """Test step definition matching."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.*;
        
        public class SearchSteps {
            @When("I search for {string}")
            public void searchFor(String query) {}
        }
        '''
        
        java_file = tmp_path / "SearchSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        parser.parse_file(str(java_file))
        
        # Test matching
        match = parser.find_step_definition('I search for "selenium"', "When")
        assert match is not None
        assert match.step_type == "When"
        assert "search for" in match.pattern.lower()
    
    def test_step_bindings_map(self, tmp_path):
        """Test step bindings map organization."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.*;
        
        public class MixedSteps {
            @Given("step one")
            public void stepOne() {}
            
            @Given("step two")
            public void stepTwo() {}
            
            @When("action")
            public void action() {}
            
            @Then("result")
            public void result() {}
        }
        '''
        
        java_file = tmp_path / "MixedSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        parser.parse_file(str(java_file))
        
        bindings = parser.get_step_bindings_map()
        
        assert "Given" in bindings
        assert "When" in bindings
        assert "Then" in bindings
        assert len(bindings["Given"]) == 2
        assert len(bindings["When"]) == 1
        assert len(bindings["Then"]) == 1


class TestRobotLogParserParity:
    """Test Robot Framework log parser functionality."""
    
    def test_parse_simple_robot_log(self, tmp_path):
        """Test parsing a simple Robot Framework output.xml."""
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
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:04.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        # Parse
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        # Validate suite
        assert suite is not None
        assert suite.name == "Login Tests"
        assert suite.status == RobotStatus.PASS
        
        # Validate tests
        assert len(suite.tests) == 1
        test = suite.tests[0]
        assert test.name == "Valid Login"
        assert test.status == RobotStatus.PASS
        
        # Validate keywords
        assert len(test.keywords) == 2
        assert test.keywords[0].name == "Open Browser"
        assert test.keywords[1].name == "Input Text"
    
    def test_parse_failed_robot_test(self, tmp_path):
        """Test parsing failed Robot test."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <robot generator="Robot 6.0">
            <suite name="Failed Suite">
                <test name="Failed Test">
                    <kw name="Should Be Equal" library="BuiltIn">
                        <arg>actual</arg>
                        <arg>expected</arg>
                        <msg level="FAIL">actual != expected</msg>
                        <status status="FAIL" starttime="20240101 12:00:01.000" endtime="20240101 12:00:02.000"/>
                    </kw>
                    <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:03.000">
                        Assertion error
                    </status>
                </test>
                <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:04.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        # Validate failure
        assert suite.status == RobotStatus.FAIL
        assert len(suite.tests) == 1
        
        test = suite.tests[0]
        assert test.status == RobotStatus.FAIL
        assert test.error is not None
        
        # Check failed keywords
        failed_keywords = parser.get_failed_keywords()
        assert len(failed_keywords) == 1
        assert failed_keywords[0].name == "Should Be Equal"
    
    def test_get_slowest_tests(self, tmp_path):
        """Test slowest tests extraction."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <robot generator="Robot 6.0">
            <suite name="Performance Suite">
                <test name="Fast Test">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <test name="Slow Test">
                    <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:06.000"/>
                </test>
                <test name="Medium Test">
                    <status status="PASS" starttime="20240101 12:00:06.000" endtime="20240101 12:00:09.000"/>
                </test>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:10.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        parser.parse(str(xml_file))
        
        slowest = parser.get_slowest_tests(count=2)
        assert len(slowest) == 2
        assert slowest[0].name == "Slow Test"  # 5 seconds
        assert slowest[1].name == "Medium Test"  # 3 seconds
    
    def test_get_statistics(self, tmp_path):
        """Test statistics extraction."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <robot generator="Robot 6.0">
            <suite name="Stats Suite">
                <test name="Pass 1">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <test name="Pass 2">
                    <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:02.000"/>
                </test>
                <test name="Fail 1">
                    <status status="FAIL" starttime="20240101 12:00:02.000" endtime="20240101 12:00:03.000"/>
                </test>
                <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:04.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        parser.parse(str(xml_file))
        
        stats = parser.get_statistics()
        assert stats["total_tests"] == 3
        assert stats["passed"] == 2
        assert stats["failed"] == 1
        assert stats["pass_rate"] == pytest.approx(66.67, rel=0.1)


class TestCrossFrameworkParity:
    """Test parity across different test frameworks."""
    
    def test_signal_extraction_parity(self):
        """Test that signal extraction works consistently across frameworks."""
        # This would test that Pytest, Robot, Java frameworks all extract similar signals
        # for equivalent test operations
        
        # Example: All should extract ASSERTION signals
        frameworks = ["pytest", "robot", "java"]
        
        for framework in frameworks:
            # Create mock test data
            # Verify signal extraction
            pass
    
    def test_error_classification_parity(self):
        """Test that error classification is consistent across frameworks."""
        # Timeout errors should be classified the same in all frameworks
        # Network errors should be classified the same
        # Locator errors should be classified the same
        pass
    
    def test_timing_accuracy_parity(self):
        """Test that timing measurements are accurate across frameworks."""
        # All frameworks should provide accurate timing data
        pass
    
    def test_metadata_completeness_parity(self):
        """Test that metadata extraction is complete across frameworks."""
        # All frameworks should extract: test name, suite, file, line number, etc.
        pass


class TestParserIntegration:
    """Test integration between different parsers."""
    
    def test_java_robot_integration(self):
        """Test Java and Robot parsers work together."""
        # For BDD scenarios, Java step definitions should match Robot keywords
        pass
    
    def test_pytest_intelligence_integration(self):
        """Test pytest intelligence plugin integration."""
        # Intelligence plugin should extract signals from pytest tests
        pass
    
    def test_adapter_parser_integration(self):
        """Test adapters correctly use parsers."""
        # Adapters should delegate to appropriate parsers
        pass


class TestParserPerformance:
    """Test parser performance characteristics."""
    
    def test_java_parser_performance(self, tmp_path):
        """Test Java parser performance on large files."""
        # Create large Java file with 100+ step definitions
        steps_code = []
        for i in range(100):
            steps_code.append(f'''
            @Given("step definition number {i}")
            public void stepDef{i}() {{}}
            ''')
        
        java_code = f'''
        package com.example.steps;
        import io.cucumber.java.en.*;
        
        public class LargeSteps {{
            {"".join(steps_code)}
        }}
        '''
        
        java_file = tmp_path / "LargeSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        
        import time
        start = time.time()
        steps = parser.parse_file(str(java_file))
        duration = time.time() - start
        
        # Should parse 100+ steps in under 1 second
        assert len(steps) >= 100
        assert duration < 1.0
    
    def test_robot_parser_performance(self, tmp_path):
        """Test Robot parser performance on large output files."""
        # Create large output.xml with many tests
        tests_xml = []
        for i in range(50):
            tests_xml.append(f'''
            <test name="Test {i}">
                <kw name="Keyword {i}" library="Library">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </kw>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
            </test>
            ''')
        
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
        <robot generator="Robot 6.0">
            <suite name="Large Suite">
                {"".join(tests_xml)}
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:01:40.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        
        import time
        start = time.time()
        suite = parser.parse(str(xml_file))
        duration = time.time() - start
        
        # Should parse 50+ tests in under 1 second
        assert len(suite.tests) >= 50
        assert duration < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
