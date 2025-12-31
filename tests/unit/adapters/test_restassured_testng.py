"""
Unit tests for RestAssured + TestNG adapter.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET

from adapters.restassured_testng.config import RestAssuredConfig
from adapters.restassured_testng.detector import RestAssuredDetector
from adapters.restassured_testng.extractor import RestAssuredExtractor
from adapters.restassured_testng.adapter import RestAssuredTestNGAdapter
from adapters.common.models import TestMetadata


class TestRestAssuredConfig:
    """Test RestAssured configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RestAssuredConfig(project_root="/test/project")
        
        assert config.project_root == "/test/project"
        assert config.src_root == "src/test/java"
        assert config.maven_command == "mvn"
        assert config.gradle_command == "gradle"
        assert config.parallel_threads == 1
        assert config.surefire_reports == "target/surefire-reports"
        assert config.testng_output == "test-output"
    
    def test_maven_detection(self, tmp_path):
        """Test Maven project detection."""
        project_dir = tmp_path / "maven_project"
        project_dir.mkdir()
        (project_dir / "pom.xml").write_text("<project></project>")
        
        config = RestAssuredConfig(project_root=str(project_dir))
        assert config.build_tool == "maven"
    
    def test_gradle_detection(self, tmp_path):
        """Test Gradle project detection."""
        project_dir = tmp_path / "gradle_project"
        project_dir.mkdir()
        (project_dir / "build.gradle").write_text("// Gradle build")
        
        config = RestAssuredConfig(project_root=str(project_dir))
        assert config.build_tool == "gradle"
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RestAssuredConfig(
            project_root="/custom",
            src_root="test/java",
            parallel_threads=4,
            groups=["smoke", "regression"]
        )
        
        assert config.src_root == "test/java"
        assert config.parallel_threads == 4
        assert "smoke" in config.groups
        assert "regression" in config.groups


class TestRestAssuredDetector:
    """Test RestAssured project detection."""
    
    def test_detect_maven_project(self, tmp_path):
        """Test detection of Maven + RestAssured project."""
        project_dir = tmp_path / "maven_ra"
        project_dir.mkdir()
        
        pom_content = """
        <project>
            <dependencies>
                <dependency>
                    <groupId>io.rest-assured</groupId>
                    <artifactId>rest-assured</artifactId>
                </dependency>
                <dependency>
                    <groupId>org.testng</groupId>
                    <artifactId>testng</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        (project_dir / "pom.xml").write_text(pom_content)
        
        detector = RestAssuredDetector()
        assert detector.detect(str(project_dir))
    
    def test_detect_gradle_project(self, tmp_path):
        """Test detection of Gradle + RestAssured project."""
        project_dir = tmp_path / "gradle_ra"
        project_dir.mkdir()
        
        build_content = """
        dependencies {
            testImplementation 'io.rest-assured:rest-assured:5.3.0'
            testImplementation 'org.testng:testng:7.7.0'
        }
        """
        (project_dir / "build.gradle").write_text(build_content)
        
        detector = RestAssuredDetector()
        assert detector.detect(str(project_dir))
    
    def test_detect_source_files(self, tmp_path):
        """Test detection from source files."""
        project_dir = tmp_path / "source_ra"
        project_dir.mkdir()
        src_dir = project_dir / "src" / "test" / "java"
        src_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test
            public void testApi() {
                RestAssured.given().get("/users");
            }
        }
        """
        (src_dir / "ApiTest.java").write_text(test_content)
        
        detector = RestAssuredDetector()
        assert detector.detect(str(project_dir))
    
    def test_no_detection(self, tmp_path):
        """Test no detection for non-RestAssured project."""
        project_dir = tmp_path / "no_ra"
        project_dir.mkdir()
        
        detector = RestAssuredDetector()
        assert not detector.detect(str(project_dir))


class TestRestAssuredExtractor:
    """Test RestAssured test extraction."""
    
    @pytest.fixture
    def sample_test_file(self, tmp_path):
        """Create sample test file."""
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        test_dir.mkdir(parents=True)
        
        test_content = """
        package com.example;
        
        import io.restassured.RestAssured;
        import io.restassured.response.Response;
        import org.testng.annotations.Test;
        
        @Test(groups = {"api", "smoke"})
        public class UserApiTest {
            
            @Test(priority = 1)
            public void testGetUser() {
                Response response = RestAssured.get("/users/1");
                assertEquals(200, response.statusCode());
            }
            
            @Test(priority = 2, groups = {"regression"})
            public void testCreateUser() {
                RestAssured.given()
                    .body("{}")
                    .post("/users");
            }
            
            @Test(enabled = false, description = "Test for updating user")
            public void testUpdateUser() {
                RestAssured.put("/users/1");
            }
        }
        """
        test_file = test_dir / "UserApiTest.java"
        test_file.write_text(test_content)
        
        return test_file
    
    def test_extract_tests(self, sample_test_file, tmp_path):
        """Test extracting tests from file."""
        config = RestAssuredConfig(project_root=str(tmp_path))
        extractor = RestAssuredExtractor(config)
        
        tests = extractor.extract_tests(str(tmp_path))
        
        assert len(tests) == 3
        
        # Check first test
        test1 = next(t for t in tests if "testGetUser" in t.test_name)
        assert test1.framework == "restassured-testng"
        assert test1.test_type == "api"
        assert "api" in test1.tags
        assert "smoke" in test1.tags
        
        # Check second test
        test2 = next(t for t in tests if "testCreateUser" in t.test_name)
        assert "regression" in test2.tags
        
        # Check third test
        test3 = next(t for t in tests if "testUpdateUser" in t.test_name)
        # Note: metadata attributes like enabled, priority, description are not stored in TestMetadata
    
    def test_skip_non_restassured_files(self, tmp_path):
        """Test skipping files without RestAssured imports."""
        test_dir = tmp_path / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        non_ra_content = """
        import org.testng.annotations.Test;
        
        public class NonApiTest {
            @Test
            public void testSomething() {}
        }
        """
        (test_dir / "NonApiTest.java").write_text(non_ra_content)
        
        config = RestAssuredConfig(project_root=str(tmp_path))
        extractor = RestAssuredExtractor(config)
        
        tests = extractor.extract_tests(str(tmp_path))
        assert len(tests) == 0


class TestRestAssuredAdapter:
    """Test RestAssured adapter."""
    
    @pytest.fixture
    def mock_adapter(self, tmp_path):
        """Create adapter with mocked dependencies."""
        config = RestAssuredConfig(project_root=str(tmp_path))
        adapter = RestAssuredTestNGAdapter(str(tmp_path), config)
        return adapter
    
    def test_adapter_initialization(self, mock_adapter):
        """Test adapter initialization."""
        assert mock_adapter.project_root
        assert mock_adapter.config is not None
        assert mock_adapter.extractor is not None
        assert mock_adapter.detector is not None
    
    def test_discover_tests_no_filter(self, mock_adapter, tmp_path):
        """Test discovering all tests."""
        # Create test file
        test_dir = tmp_path / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test
            public void test1() {}
            
            @Test
            public void test2() {}
        }
        """
        (test_dir / "ApiTest.java").write_text(test_content)
        
        tests = mock_adapter.discover_tests()
        assert len(tests) == 2
    
    def test_discover_tests_with_tags(self, mock_adapter, tmp_path):
        """Test discovering tests filtered by tags."""
        test_dir = tmp_path / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test(groups = {"smoke"})
            public void test1() {}
            
            @Test(groups = {"regression"})
            public void test2() {}
        }
        """
        (test_dir / "ApiTest.java").write_text(test_content)
        
        tests = mock_adapter.discover_tests(tags=["smoke"])
        assert len(tests) == 1
        assert "smoke" in tests[0].tags
    
    def test_build_maven_command_basic(self, mock_adapter):
        """Test building Maven command."""
        mock_adapter.config.build_tool = "maven"
        
        cmd = mock_adapter._build_maven_command(tests=None, tags=None)
        
        assert "mvn" in cmd
        assert "test" in cmd
    
    def test_build_maven_command_with_groups(self, mock_adapter):
        """Test Maven command with groups."""
        mock_adapter.config.build_tool = "maven"
        
        cmd = mock_adapter._build_maven_command(tests=None, tags=["smoke", "api"])
        
        assert any("-Dgroups=smoke,api" in arg for arg in cmd)
    
    def test_build_maven_command_with_tests(self, mock_adapter):
        """Test Maven command with specific tests."""
        mock_adapter.config.build_tool = "maven"
        
        cmd = mock_adapter._build_maven_command(
            tests=["com.example.ApiTest#test1", "com.example.ApiTest#test2"],
            tags=None
        )
        
        assert any("-Dtest=com.example.ApiTest" in arg for arg in cmd)
    
    def test_build_gradle_command_basic(self, mock_adapter):
        """Test building Gradle command."""
        mock_adapter.config.build_tool = "gradle"
        
        cmd = mock_adapter._build_gradle_command(tests=None, tags=None)
        
        assert "gradle" in cmd
        assert "test" in cmd
    
    def test_build_gradle_command_with_tests(self, mock_adapter):
        """Test Gradle command with specific tests."""
        mock_adapter.config.build_tool = "gradle"
        
        cmd = mock_adapter._build_gradle_command(
            tests=["com.example.ApiTest#test1"],
            tags=None
        )
        
        assert "--tests" in cmd
        assert "com.example.ApiTest.test1" in cmd
    
    def test_parse_surefire_reports(self, mock_adapter, tmp_path):
        """Test parsing Maven Surefire reports."""
        reports_dir = tmp_path / "target" / "surefire-reports"
        reports_dir.mkdir(parents=True)
        
        # Create sample XML report
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="com.example.ApiTest" tests="3" failures="1" errors="0" skipped="1">
            <testcase classname="com.example.ApiTest" name="test1" time="0.123">
            </testcase>
            <testcase classname="com.example.ApiTest" name="test2" time="0.456">
                <failure message="Expected 200 but got 404" type="AssertionError">
                    Stack trace here
                </failure>
            </testcase>
            <testcase classname="com.example.ApiTest" name="test3" time="0.001">
                <skipped message="Test disabled"/>
            </testcase>
        </testsuite>
        """
        (reports_dir / "TEST-com.example.ApiTest.xml").write_text(xml_content)
        
        mock_adapter.config.surefire_reports = "target/surefire-reports"
        results = mock_adapter._parse_surefire_reports(reports_dir)
        
        assert len(results) == 3
        
        # Check passed test
        pass_result = next(r for r in results if r.name == "com.example.ApiTest#test1")
        assert pass_result.status == "pass"
        assert pass_result.duration_ms == 123.0
        
        # Check failed test
        fail_result = next(r for r in results if r.name == "com.example.ApiTest#test2")
        assert fail_result.status == "fail"
        assert "Expected 200 but got 404" in fail_result.message
        
        # Check skipped test
        skip_result = next(r for r in results if r.name == "com.example.ApiTest#test3")
        assert skip_result.status == "skip"
    
    def test_parse_testng_results(self, mock_adapter, tmp_path):
        """Test parsing TestNG XML results."""
        testng_dir = tmp_path / "test-output"
        testng_dir.mkdir()
        
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testng-results>
            <suite name="API Test Suite">
                <test name="API Tests">
                    <class name="com.example.ApiTest">
                        <test-method status="PASS" name="test1" duration-ms="150" 
                                     signature="com.example.ApiTest.test1()">
                        </test-method>
                        <test-method status="FAIL" name="test2" duration-ms="200"
                                     signature="com.example.ApiTest.test2()">
                            <exception class="java.lang.AssertionError">
                                <message>Test failed</message>
                            </exception>
                        </test-method>
                        <test-method status="SKIP" name="test3" duration-ms="0"
                                     signature="com.example.ApiTest.test3()">
                        </test-method>
                    </class>
                </test>
            </suite>
        </testng-results>
        """
        (testng_dir / "testng-results.xml").write_text(xml_content)
        
        mock_adapter.config.testng_output = "test-output"
        results = mock_adapter._parse_testng_results(testng_dir)
        
        assert len(results) == 3
        
        # Check passed test
        pass_result = next(r for r in results if "test1" in r.name)
        assert pass_result.status == "pass"
        assert pass_result.duration_ms == 150.0
        
        # Check failed test
        fail_result = next(r for r in results if "test2" in r.name)
        assert fail_result.status == "fail"
        assert "Test failed" in fail_result.message
        
        # Check skipped test
        skip_result = next(r for r in results if "test3" in r.name)
        assert skip_result.status == "skip"
    
    @patch('subprocess.run')
    def test_run_tests_maven(self, mock_run, mock_adapter):
        """Test running tests with Maven."""
        mock_adapter.config.build_tool = "maven"
        
        # Mock successful execution
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Mock parsing results
        with patch.object(mock_adapter, '_parse_results', return_value=[]):
            results = mock_adapter.run_tests(tags=["smoke"])
        
        # Verify Maven was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "mvn" in call_args[0][0]
        assert "test" in call_args[0][0]
    
    @patch('subprocess.run')
    def test_run_tests_gradle(self, mock_run, mock_adapter):
        """Test running tests with Gradle."""
        mock_adapter.config.build_tool = "gradle"
        
        # Mock successful execution
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Mock parsing results
        with patch.object(mock_adapter, '_parse_results', return_value=[]):
            results = mock_adapter.run_tests()
        
        # Verify Gradle was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "gradle" in call_args[0][0]
        assert "test" in call_args[0][0]
    
    def test_detect_project(self, tmp_path):
        """Test static project detection method."""
        project_dir = tmp_path / "ra_project"
        project_dir.mkdir()
        
        # Create pom.xml with dependencies
        pom_content = """
        <project>
            <dependencies>
                <dependency>
                    <groupId>io.rest-assured</groupId>
                    <artifactId>rest-assured</artifactId>
                </dependency>
                <dependency>
                    <groupId>org.testng</groupId>
                    <artifactId>testng</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        (project_dir / "pom.xml").write_text(pom_content)
        
        detected = RestAssuredTestNGAdapter.detect_project(str(project_dir))
        assert detected


class TestIntegration:
    """Integration tests for RestAssured adapter."""
    
    def test_full_workflow(self, tmp_path):
        """Test complete workflow from detection to extraction."""
        # Setup project
        project_dir = tmp_path / "integration_test"
        project_dir.mkdir()
        
        # Create pom.xml
        pom_content = """
        <project>
            <dependencies>
                <dependency>
                    <groupId>io.rest-assured</groupId>
                    <artifactId>rest-assured</artifactId>
                </dependency>
                <dependency>
                    <groupId>org.testng</groupId>
                    <artifactId>testng</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        (project_dir / "pom.xml").write_text(pom_content)
        
        # Create test file
        test_dir = project_dir / "src" / "test" / "java" / "com" / "example"
        test_dir.mkdir(parents=True)
        
        test_content = """
        package com.example;
        
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        @Test(groups = {"api"})
        public class UserApiTest {
            
            @Test(priority = 1, groups = {"smoke"})
            public void testGetAllUsers() {
                RestAssured.get("/users");
            }
            
            @Test(priority = 2)
            public void testGetUser() {
                RestAssured.get("/users/1");
            }
        }
        """
        (test_dir / "UserApiTest.java").write_text(test_content)
        
        # 1. Detect project
        assert RestAssuredTestNGAdapter.detect_project(str(project_dir))
        
        # 2. Create adapter
        adapter = RestAssuredTestNGAdapter(str(project_dir))
        assert adapter.config.build_tool == "maven"
        
        # 3. Discover tests
        all_tests = adapter.discover_tests()
        assert len(all_tests) == 2
        
        # 4. Filter by tags
        smoke_tests = adapter.discover_tests(tags=["smoke"])
        assert len(smoke_tests) == 1
        assert "smoke" in smoke_tests[0].tags
        
        # 5. Verify test metadata
        test1 = next(t for t in all_tests if "testGetAllUsers" in t.test_name)
        assert test1.framework == "restassured-testng"
        assert test1.test_type == "api"
        assert "api" in test1.tags
        assert "smoke" in test1.tags
