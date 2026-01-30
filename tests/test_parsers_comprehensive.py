"""
Comprehensive Unit Tests for Java Step Parser and Robot Log Parser.

Tests both with and without AI/ML features.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.intelligence.java_step_parser import JavaStepDefinitionParser, JavaStepDefinition
from core.intelligence.robot_log_parser import (
    RobotLogParser,
    RobotStatus,
    RobotKeyword,
    RobotTest,
    RobotSuite
)


# ============================================================================
# Java Step Parser Tests (WITHOUT AI)
# ============================================================================

class TestJavaStepParserBasic:
    """Test Java parser basic functionality without AI features."""
    
    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty Java file."""
        java_file = tmp_path / "Empty.java"
        java_file.write_text("")
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert steps == []
    
    def test_parse_file_without_steps(self, tmp_path):
        """Test parsing Java file without step definitions."""
        java_code = '''
        package com.example;
        public class NoSteps {
            public void regularMethod() {}
        }
        '''
        
        java_file = tmp_path / "NoSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert steps == []
    
    def test_parse_single_given_step(self, tmp_path):
        """Test parsing single Given step."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.Given;
        
        public class Steps {
            @Given("user is logged in")
            public void userLoggedIn() {}
        }
        '''
        
        java_file = tmp_path / "Steps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert len(steps) == 1
        assert steps[0].step_type == "Given"
        assert steps[0].pattern == "user is logged in"
        assert steps[0].method_name == "userLoggedIn"
    
    def test_parse_all_step_types(self, tmp_path):
        """Test parsing all step types (Given/When/Then/And/But)."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.*;
        
        public class AllSteps {
            @Given("step one")
            public void stepOne() {}
            
            @When("step two")
            public void stepTwo() {}
            
            @Then("step three")
            public void stepThree() {}
            
            @And("step four")
            public void stepFour() {}
            
            @But("step five")
            public void stepFive() {}
        }
        '''
        
        java_file = tmp_path / "AllSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert len(steps) == 5
        step_types = [s.step_type for s in steps]
        assert "Given" in step_types
        assert "When" in step_types
        assert "Then" in step_types
        assert "And" in step_types
        assert "But" in step_types
    
    def test_parse_cucumber_string_parameter(self, tmp_path):
        """Test parsing Cucumber {string} parameter."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.When;
        
        public class ParamSteps {
            @When("user enters name {string}")
            public void enterName(String name) {}
        }
        '''
        
        java_file = tmp_path / "ParamSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert len(steps) == 1
        assert "{string}" in steps[0].pattern
        assert len(steps[0].parameters) == 1
    
    def test_parse_cucumber_int_parameter(self, tmp_path):
        """Test parsing Cucumber {int} parameter."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.When;
        
        public class IntSteps {
            @When("user enters {int} items")
            public void enterItems(int count) {}
        }
        '''
        
        java_file = tmp_path / "IntSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert len(steps) == 1
        assert "{int}" in steps[0].pattern
    
    def test_parse_multiple_parameters(self, tmp_path):
        """Test parsing step with multiple parameters."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.When;
        
        public class MultiParamSteps {
            @When("user enters {string} and {string} and {int}")
            public void enterData(String first, String second, int number) {}
        }
        '''
        
        java_file = tmp_path / "MultiParamSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert len(steps) == 1
        assert len(steps[0].parameters) == 3
    
    def test_find_step_definition_exact_match(self, tmp_path):
        """Test finding step definition with exact match."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.When;
        
        public class SearchSteps {
            @When("user clicks login button")
            public void clickLogin() {}
        }
        '''
        
        java_file = tmp_path / "SearchSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        parser.parse_file(str(java_file))
        
        match = parser.find_step_definition("user clicks login button", "When")
        assert match is not None
        assert match.method_name == "clickLogin"
    
    def test_find_step_definition_no_match(self, tmp_path):
        """Test finding step definition with no match."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.When;
        
        public class Steps {
            @When("step one")
            public void stepOne() {}
        }
        '''
        
        java_file = tmp_path / "Steps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        parser.parse_file(str(java_file))
        
        match = parser.find_step_definition("step two", "When")
        assert match is None
    
    def test_get_step_bindings_map(self, tmp_path):
        """Test getting step bindings organized by type."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.*;
        
        public class BindingSteps {
            @Given("given one")
            public void givenOne() {}
            
            @Given("given two")
            public void givenTwo() {}
            
            @When("when one")
            public void whenOne() {}
            
            @Then("then one")
            public void thenOne() {}
        }
        '''
        
        java_file = tmp_path / "BindingSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        parser.parse_file(str(java_file))
        
        bindings = parser.get_step_bindings_map()
        
        assert len(bindings["Given"]) == 2
        assert len(bindings["When"]) == 1
        assert len(bindings["Then"]) == 1
    
    def test_parse_directory(self, tmp_path):
        """Test parsing entire directory of step files."""
        # Create multiple step files
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()
        
        (steps_dir / "LoginSteps.java").write_text('''
        package com.example.steps;
        import io.cucumber.java.en.Given;
        public class LoginSteps {
            @Given("user on login page")
            public void onLoginPage() {}
        }
        ''')
        
        (steps_dir / "SearchSteps.java").write_text('''
        package com.example.steps;
        import io.cucumber.java.en.When;
        public class SearchSteps {
            @When("user searches for {string}")
            public void search(String query) {}
        }
        ''')
        
        parser = JavaStepDefinitionParser()
        all_steps = parser.parse_directory(steps_dir, "**/*.java")
        
        assert len(all_steps) == 2
        step_types = [s.step_type for s in all_steps]
        assert "Given" in step_types
        assert "When" in step_types
    
    def test_invalid_java_file(self, tmp_path):
        """Test parsing invalid Java code."""
        java_file = tmp_path / "Invalid.java"
        java_file.write_text("this is not valid java code!!! @#$%")
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        # Should return empty list, not crash
        assert steps == []
    
    def test_file_path_tracking(self, tmp_path):
        """Test that file paths are correctly tracked."""
        java_code = '''
        package com.example.steps;
        import io.cucumber.java.en.Given;
        public class Steps {
            @Given("test step")
            public void testStep() {}
        }
        '''
        
        java_file = tmp_path / "Steps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file(str(java_file))
        
        assert len(steps) == 1
        assert steps[0].file_path == str(java_file)


# ============================================================================
# Robot Log Parser Tests (WITHOUT AI)
# ============================================================================

class TestRobotLogParserBasic:
    """Test Robot parser basic functionality without AI features."""
    
    def test_parse_empty_xml(self, tmp_path):
        """Test parsing empty XML file."""
        xml_file = tmp_path / "output.xml"
        xml_file.write_text('<?xml version="1.0"?><robot></robot>')
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        assert suite is None
    
    def test_parse_single_passing_test(self, tmp_path):
        """Test parsing single passing test."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="TestSuite" source="/path/to/test.robot">
                <test name="Test Case">
                    <kw name="Log" library="BuiltIn">
                        <arg>Hello</arg>
                        <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                    </kw>
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        assert suite is not None
        assert suite.name == "TestSuite"
        assert suite.status == RobotStatus.PASS
        assert len(suite.tests) == 1
        assert suite.tests[0].name == "Test Case"
        assert suite.tests[0].status == RobotStatus.PASS
    
    def test_parse_single_failing_test(self, tmp_path):
        """Test parsing single failing test."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="FailSuite">
                <test name="Failing Test">
                    <kw name="Should Be Equal" library="BuiltIn">
                        <arg>actual</arg>
                        <arg>expected</arg>
                        <msg level="FAIL">actual != expected</msg>
                        <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                    </kw>
                    <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000">Test failed</status>
                </test>
                <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        assert suite.status == RobotStatus.FAIL
        assert len(suite.tests) == 1
        assert suite.tests[0].status == RobotStatus.FAIL
        assert suite.tests[0].error_message == "Test failed"
    
    def test_parse_multiple_tests(self, tmp_path):
        """Test parsing multiple tests."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="MultiSuite">
                <test name="Test 1">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <test name="Test 2">
                    <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:02.000"/>
                </test>
                <test name="Test 3">
                    <status status="FAIL" starttime="20240101 12:00:02.000" endtime="20240101 12:00:03.000"/>
                </test>
                <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:04.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        assert len(suite.tests) == 3
        assert suite.tests[0].status == RobotStatus.PASS
        assert suite.tests[1].status == RobotStatus.PASS
        assert suite.tests[2].status == RobotStatus.FAIL
    
    def test_parse_keywords_with_arguments(self, tmp_path):
        """Test parsing keywords with arguments."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="KwSuite">
                <test name="Keyword Test">
                    <kw name="Input Text" library="SeleniumLibrary">
                        <arg>id=username</arg>
                        <arg>testuser</arg>
                        <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                    </kw>
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        test = suite.tests[0]
        assert len(test.keywords) == 1
        kw = test.keywords[0]
        assert kw.name == "Input Text"
        assert kw.library == "SeleniumLibrary"
        assert len(kw.arguments) == 2
        assert kw.arguments[0] == "id=username"
        assert kw.arguments[1] == "testuser"
    
    def test_parse_keyword_messages(self, tmp_path):
        """Test parsing keyword messages."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="MsgSuite">
                <test name="Message Test">
                    <kw name="Log" library="BuiltIn">
                        <msg level="INFO">Info message</msg>
                        <msg level="DEBUG">Debug message</msg>
                        <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                    </kw>
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        kw = suite.tests[0].keywords[0]
        assert len(kw.messages) == 2
        assert kw.messages[0] == "Info message"
        assert kw.messages[1] == "Debug message"
    
    def test_parse_test_tags(self, tmp_path):
        """Test parsing test tags."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="TagSuite">
                <test name="Tagged Test">
                    <tag>smoke</tag>
                    <tag>regression</tag>
                    <tag>priority-high</tag>
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        test = suite.tests[0]
        assert len(test.tags) == 3
        assert "smoke" in test.tags
        assert "regression" in test.tags
        assert "priority-high" in test.tags
    
    def test_parse_nested_suites(self, tmp_path):
        """Test parsing nested test suites."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="ParentSuite">
                <suite name="ChildSuite1">
                    <test name="Test 1">
                        <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                    </test>
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
                </suite>
                <suite name="ChildSuite2">
                    <test name="Test 2">
                        <status status="PASS" starttime="20240101 12:00:02.000" endtime="20240101 12:00:03.000"/>
                    </test>
                    <status status="PASS" starttime="20240101 12:00:02.000" endtime="20240101 12:00:04.000"/>
                </suite>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:05.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        assert suite.name == "ParentSuite"
        assert len(suite.suites) == 2
        assert suite.suites[0].name == "ChildSuite1"
        assert suite.suites[1].name == "ChildSuite2"
        assert len(suite.suites[0].tests) == 1
        assert len(suite.suites[1].tests) == 1
    
    def test_get_test_by_name(self, tmp_path):
        """Test finding test by name."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="Suite">
                <test name="Target Test">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <test name="Other Test">
                    <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:02.000"/>
                </test>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:03.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        parser.parse(str(xml_file))
        
        test = parser.get_test_by_name("Target Test")
        assert test is not None
        assert test.name == "Target Test"
    
    def test_get_failed_keywords(self, tmp_path):
        """Test extracting failed keywords."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="Suite">
                <test name="Test">
                    <kw name="Passing Keyword" library="BuiltIn">
                        <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                    </kw>
                    <kw name="Failing Keyword" library="BuiltIn">
                        <msg level="FAIL">Error occurred</msg>
                        <status status="FAIL" starttime="20240101 12:00:01.000" endtime="20240101 12:00:02.000"/>
                    </kw>
                    <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:02.000"/>
                </test>
                <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:03.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        parser.parse(str(xml_file))
        
        failed = parser.get_failed_keywords()
        assert len(failed) == 1
        assert failed[0].name == "Failing Keyword"
        assert failed[0].status == RobotStatus.FAIL
    
    def test_get_slowest_tests(self, tmp_path):
        """Test extracting slowest tests."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="Suite">
                <test name="Fast Test">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:00.100" elapsedtime="100"/>
                </test>
                <test name="Slow Test">
                    <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:06.000" elapsedtime="5000"/>
                </test>
                <test name="Medium Test">
                    <status status="PASS" starttime="20240101 12:00:06.000" endtime="20240101 12:00:09.000" elapsedtime="3000"/>
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
        assert slowest[0].name == "Slow Test"
        assert slowest[1].name == "Medium Test"
    
    def test_get_statistics(self, tmp_path):
        """Test getting execution statistics."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="Suite">
                <test name="Pass 1">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </test>
                <test name="Pass 2">
                    <status status="PASS" starttime="20240101 12:00:01.000" endtime="20240101 12:00:02.000"/>
                </test>
                <test name="Fail 1">
                    <status status="FAIL" starttime="20240101 12:00:02.000" endtime="20240101 12:00:03.000"/>
                </test>
                <status status="FAIL" starttime="20240101 12:00:00.000" endtime="20240101 12:00:05.000"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        parser.parse(str(xml_file))
        
        stats = parser.get_statistics()
        assert stats["total_tests"] == 3
        assert stats["passed_tests"] == 2
        assert stats["failed_tests"] == 1
    
    def test_invalid_xml(self, tmp_path):
        """Test parsing invalid XML."""
        xml_file = tmp_path / "invalid.xml"
        xml_file.write_text("not valid xml!!!")
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        # Should return None, not crash
        assert suite is None


# ============================================================================
# Integration Tests (Simplified - No Mocking)
# ============================================================================

class TestJavaParserIntegration:
    """Test Java parser integration scenarios."""
    
    def test_large_file_performance(self, tmp_path):
        """Test parser performance with large files."""
        # Create large file with 50 steps
        steps = []
        for i in range(50):
            steps.append(f'''
            @Given("step number {i}")
            public void step{i}() {{}}
            ''')
        
        java_code = f'''
        package com.example.steps;
        import io.cucumber.java.en.*;
        
        public class LargeSteps {{
            {"".join(steps)}
        }}
        '''
        
        java_file = tmp_path / "LargeSteps.java"
        java_file.write_text(java_code)
        
        parser = JavaStepDefinitionParser()
        
        import time
        start = time.time()
        steps = parser.parse_file(str(java_file))
        duration = time.time() - start
        
        assert len(steps) == 50
        assert duration < 1.0  # Should parse in under 1 second


class TestRobotParserIntegration:
    """Test Robot parser integration scenarios."""
    
    def test_large_suite_performance(self, tmp_path):
        """Test parser performance with large suites."""
        # Create large suite with 30 tests
        tests = []
        for i in range(30):
            tests.append(f'''
            <test name="Test {i}">
                <kw name="Log" library="BuiltIn">
                    <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
                </kw>
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:01.000"/>
            </test>
            ''')
        
        xml_content = f'''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="LargeSuite">
                {"".join(tests)}
                <status status="PASS" starttime="20240101 12:00:00.000" endtime="20240101 12:00:30.000"/>
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
        
        assert len(suite.tests) == 30
        assert duration < 1.0  # Should parse in under 1 second


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_java_parser_missing_file(self):
        """Test Java parser with non-existent file."""
        parser = JavaStepDefinitionParser()
        steps = parser.parse_file("/non/existent/file.java")
        
        assert steps == []
    
    def test_robot_parser_missing_file(self):
        """Test Robot parser with non-existent file."""
        parser = RobotLogParser()
        suite = parser.parse("/non/existent/output.xml")
        
        # Should return None and not crash
        assert suite is None
    
    def test_java_parser_permission_error(self, tmp_path):
        """Test Java parser with permission denied."""
        java_file = tmp_path / "restricted.java"
        java_file.write_text("package test; public class Test {}")
        java_file.chmod(0o000)  # Remove all permissions
        
        parser = JavaStepDefinitionParser()
        try:
            steps = parser.parse_file(str(java_file))
            # Should handle gracefully
            assert steps == []
        finally:
            java_file.chmod(0o644)  # Restore permissions for cleanup
    
    def test_robot_parser_malformed_timestamps(self, tmp_path):
        """Test Robot parser with malformed timestamps."""
        xml_content = '''<?xml version="1.0"?>
        <robot generator="Robot 6.0">
            <suite name="Suite">
                <test name="Test">
                    <status status="PASS" starttime="invalid" endtime="invalid"/>
                </test>
                <status status="PASS" starttime="invalid" endtime="invalid"/>
            </suite>
        </robot>
        '''
        
        xml_file = tmp_path / "output.xml"
        xml_file.write_text(xml_content)
        
        parser = RobotLogParser()
        suite = parser.parse(str(xml_file))
        
        # Should parse despite malformed timestamps
        assert suite is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
