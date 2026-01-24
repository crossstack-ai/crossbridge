"""
Unit tests for external test case extractors.
"""

import pytest
import tempfile
import os

from core.coverage.external_extractors import (
    ExternalTestCaseExtractor,
    JavaExternalTestCaseExtractor,
    PytestExternalTestCaseExtractor,
    RobotFrameworkExternalTestCaseExtractor,
    CucumberExternalTestCaseExtractor,
    ExternalTestCaseExtractorFactory,
    extract_external_refs_from_test,
    extract_external_refs_from_file
)


class TestExternalTestCaseExtractor:
    """Tests for base ExternalTestCaseExtractor."""
    
    def test_extract_from_annotations(self):
        """Test extracting from annotations."""
        extractor = ExternalTestCaseExtractor()
        annotations = [
            '@TestRail(id = "C12345")',
            '@ExternalTestCase("C67890")'
        ]
        
        refs = extractor.extract_from_annotations(annotations)
        
        assert len(refs) == 2
        assert refs[0].system == "testrail"
        assert refs[0].external_id == "C12345"
        assert refs[1].external_id == "C67890"
    
    def test_extract_from_tags(self):
        """Test extracting from tags."""
        extractor = ExternalTestCaseExtractor()
        tags = [
            'testrail:C12345',
            'zephyr:T-1234',
            'smoke',
            'regression'
        ]
        
        refs = extractor.extract_from_tags(tags)
        
        assert len(refs) == 2
        assert refs[0].system == "testrail"
        assert refs[0].external_id == "C12345"
        assert refs[1].system == "zephyr"
        assert refs[1].external_id == "T-1234"
    
    def test_extract_from_test(self):
        """Test extracting from test source."""
        extractor = ExternalTestCaseExtractor()
        source = """
        @TestRail(id = "C12345")
        @Test
        public void testLogin() {
            // test code
        }
        """
        tags = ['testrail:C67890']
        
        refs = extractor.extract_from_test(source, tags)
        
        assert len(refs) == 2
        external_ids = [ref.external_id for ref in refs]
        assert "C12345" in external_ids
        assert "C67890" in external_ids


class TestJavaExternalTestCaseExtractor:
    """Tests for Java extractor."""
    
    def test_extract_from_java_file(self):
        """Test extracting from Java file."""
        extractor = JavaExternalTestCaseExtractor()
        
        # Create temporary Java file
        java_content = """
        package com.example.tests;
        
        import org.junit.jupiter.api.Test;
        
        /**
         * Login test
         * @testrail:C99999
         */
        public class LoginTest {
            
            @TestRail(id = "C12345")
            @Test
            public void testValidLogin() {
                // test
            }
            
            @TestRailCase(value = "C67890")
            @Test
            public void testInvalidLogin() {
                // test
            }
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(java_content)
            temp_file = f.name
        
        try:
            refs = extractor.extract_from_java_file(temp_file)
            
            assert len(refs) >= 2
            external_ids = [ref.external_id for ref in refs]
            assert "C12345" in external_ids
            assert "C67890" in external_ids
        finally:
            os.unlink(temp_file)
    
    def test_extract_javadoc_tags(self):
        """Test extracting from JavaDoc comments."""
        extractor = JavaExternalTestCaseExtractor()
        
        source = """
        /**
         * Test class
         * @testrail:C12345
         * @zephyr:T-999
         */
        public class Test {}
        """
        
        tags = extractor._extract_javadoc_tags(source)
        
        assert len(tags) >= 2
        assert "testrail:C12345" in tags
        assert "zephyr:T-999" in tags


class TestPytestExternalTestCaseExtractor:
    """Tests for pytest extractor."""
    
    def test_extract_from_pytest_file(self):
        """Test extracting from pytest file."""
        extractor = PytestExternalTestCaseExtractor()
        
        # Create temporary pytest file
        pytest_content = """
        import pytest
        
        @pytest.mark.testrail("C12345")
        @pytest.mark.smoke
        def test_login():
            assert True
        
        @pytest.mark.external_id("C67890")
        def test_logout():
            assert True
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(pytest_content)
            temp_file = f.name
        
        try:
            refs = extractor.extract_from_pytest_file(temp_file)
            
            assert len(refs) == 2
            external_ids = [ref.external_id for ref in refs]
            assert "C12345" in external_ids
            assert "C67890" in external_ids
        finally:
            os.unlink(temp_file)


class TestRobotFrameworkExternalTestCaseExtractor:
    """Tests for Robot Framework extractor."""
    
    def test_extract_from_robot_file(self):
        """Test extracting from Robot file."""
        extractor = RobotFrameworkExternalTestCaseExtractor()
        
        # Create temporary robot file
        robot_content = """
*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Valid Login
    [Tags]    testrail:C12345    smoke
    Open Browser    http://example.com
    Input Text    username    test
    
Invalid Login
    [Tags]    testrail:C67890    zephyr:T-1234
    Open Browser    http://example.com
    Input Text    username    invalid
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False) as f:
            f.write(robot_content)
            temp_file = f.name
        
        try:
            refs = extractor.extract_from_robot_file(temp_file)
            
            assert len(refs) >= 2
            external_ids = [ref.external_id for ref in refs]
            assert "C12345" in external_ids
            assert "C67890" in external_ids
        finally:
            os.unlink(temp_file)


class TestCucumberExternalTestCaseExtractor:
    """Tests for Cucumber extractor."""
    
    def test_extract_from_feature_file(self):
        """Test extracting from feature file."""
        extractor = CucumberExternalTestCaseExtractor()
        
        # Create temporary feature file
        feature_content = """
Feature: Login functionality

  @testrail:C12345 @smoke
  Scenario: Valid login
    Given I am on the login page
    When I enter valid credentials
    Then I should be logged in
  
  @testrail:C67890 @zephyr:T-1234
  Scenario: Invalid login
    Given I am on the login page
    When I enter invalid credentials
    Then I should see an error
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(feature_content)
            temp_file = f.name
        
        try:
            refs = extractor.extract_from_feature_file(temp_file)
            
            assert len(refs) >= 2
            external_ids = [ref.external_id for ref in refs]
            assert "C12345" in external_ids
            assert "C67890" in external_ids
        finally:
            os.unlink(temp_file)


class TestExternalTestCaseExtractorFactory:
    """Tests for extractor factory."""
    
    def test_get_java_extractor(self):
        """Test getting Java extractor."""
        extractor = ExternalTestCaseExtractorFactory.get_extractor('java')
        assert isinstance(extractor, JavaExternalTestCaseExtractor)
    
    def test_get_junit_extractor(self):
        """Test getting JUnit extractor."""
        extractor = ExternalTestCaseExtractorFactory.get_extractor('junit')
        assert isinstance(extractor, JavaExternalTestCaseExtractor)
    
    def test_get_pytest_extractor(self):
        """Test getting pytest extractor."""
        extractor = ExternalTestCaseExtractorFactory.get_extractor('pytest')
        assert isinstance(extractor, PytestExternalTestCaseExtractor)
    
    def test_get_robot_extractor(self):
        """Test getting Robot extractor."""
        extractor = ExternalTestCaseExtractorFactory.get_extractor('robot')
        assert isinstance(extractor, RobotFrameworkExternalTestCaseExtractor)
    
    def test_get_cucumber_extractor(self):
        """Test getting Cucumber extractor."""
        extractor = ExternalTestCaseExtractorFactory.get_extractor('cucumber')
        assert isinstance(extractor, CucumberExternalTestCaseExtractor)
    
    def test_get_unknown_extractor(self):
        """Test getting extractor for unknown framework."""
        extractor = ExternalTestCaseExtractorFactory.get_extractor('unknown')
        assert isinstance(extractor, ExternalTestCaseExtractor)


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_extract_external_refs_from_test(self):
        """Test extract_external_refs_from_test function."""
        source = '@TestRail(id = "C12345")\n@Test\npublic void test() {}'
        tags = ['testrail:C67890']
        
        refs = extract_external_refs_from_test(source, tags, framework='java')
        
        assert len(refs) == 2
        external_ids = [ref.external_id for ref in refs]
        assert "C12345" in external_ids
        assert "C67890" in external_ids
    
    def test_extract_external_refs_from_file_java(self):
        """Test extract_external_refs_from_file for Java."""
        java_content = """
        @TestRail(id = "C12345")
        @Test
        public void test() {}
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(java_content)
            temp_file = f.name
        
        try:
            refs = extract_external_refs_from_file(temp_file, framework='java')
            
            assert len(refs) >= 1
            assert any(ref.external_id == "C12345" for ref in refs)
        finally:
            os.unlink(temp_file)
    
    def test_extract_external_refs_from_file_pytest(self):
        """Test extract_external_refs_from_file for pytest."""
        pytest_content = """
        import pytest
        
        @pytest.mark.testrail("C12345")
        def test_something():
            pass
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(pytest_content)
            temp_file = f.name
        
        try:
            refs = extract_external_refs_from_file(temp_file, framework='pytest')
            
            assert len(refs) >= 1
            assert any(ref.external_id == "C12345" for ref in refs)
        finally:
            os.unlink(temp_file)


class TestPatternMatching:
    """Tests for pattern matching edge cases."""
    
    def test_testrail_with_single_quotes(self):
        """Test TestRail annotation with single quotes."""
        extractor = ExternalTestCaseExtractor()
        annotations = ["@TestRail(id = 'C12345')"]
        
        refs = extractor.extract_from_annotations(annotations)
        
        assert len(refs) == 1
        assert refs[0].external_id == "C12345"
    
    def test_testrail_with_spaces(self):
        """Test TestRail annotation with various spacing."""
        extractor = ExternalTestCaseExtractor()
        annotations = ['@TestRail(  id  =  "C12345"  )']
        
        refs = extractor.extract_from_annotations(annotations)
        
        assert len(refs) == 1
        assert refs[0].external_id == "C12345"
    
    def test_tag_with_at_prefix(self):
        """Test tag with @ prefix."""
        extractor = ExternalTestCaseExtractor()
        tags = ['@testrail:C12345']
        
        refs = extractor.extract_from_tags(tags)
        
        assert len(refs) == 1
        assert refs[0].external_id == "C12345"
    
    def test_multiple_systems_in_tags(self):
        """Test multiple systems in tags."""
        extractor = ExternalTestCaseExtractor()
        tags = [
            'testrail:C12345',
            'zephyr:T-1234',
            'qtest:TC-999',
            'jira:TEST-123'
        ]
        
        refs = extractor.extract_from_tags(tags)
        
        assert len(refs) == 4
        systems = [ref.system for ref in refs]
        assert 'testrail' in systems
        assert 'zephyr' in systems
        assert 'qtest' in systems
        assert 'jira' in systems
