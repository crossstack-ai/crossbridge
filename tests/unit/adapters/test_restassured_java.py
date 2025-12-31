"""
Unit tests for RestAssured + Java adapter (TestNG and JUnit 5).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET

from adapters.restassured_java.config import RestAssuredConfig
from adapters.restassured_java.detector import RestAssuredDetector
from adapters.restassured_java.extractor import RestAssuredExtractor
from adapters.restassured_java.adapter import RestAssuredJavaAdapter
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
        assert config.test_framework is None  # Auto-detect
    
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
    
    def test_testng_framework_config(self):
        """Test TestNG framework configuration."""
        config = RestAssuredConfig(
            project_root="/custom",
            test_framework="testng",
            groups=["smoke", "regression"]
        )
        
        assert config.test_framework == "testng"
        assert "smoke" in config.groups
        assert "regression" in config.groups
    
    def test_junit5_framework_config(self):
        """Test JUnit 5 framework configuration."""
        config = RestAssuredConfig(
            project_root="/custom",
            test_framework="junit5",
            groups=["smoke", "api"]  # groups work as tags in JUnit 5
        )
        
        assert config.test_framework == "junit5"
        assert "smoke" in config.groups


class TestRestAssuredDetector:
    """Test RestAssured project detection for both frameworks."""
    
    def test_detect_maven_testng_project(self, tmp_path):
        """Test detection of Maven + RestAssured + TestNG project."""
        project_dir = tmp_path / "maven_testng"
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
        
        # Check config info
        config_info = detector.get_config_info(str(project_dir))
        assert config_info['test_framework'] == 'testng'
    
    def test_detect_maven_junit5_project(self, tmp_path):
        """Test detection of Maven + RestAssured + JUnit 5 project."""
        project_dir = tmp_path / "maven_junit5"
        project_dir.mkdir()
        
        pom_content = """
        <project>
            <dependencies>
                <dependency>
                    <groupId>io.rest-assured</groupId>
                    <artifactId>rest-assured</artifactId>
                </dependency>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        (project_dir / "pom.xml").write_text(pom_content)
        
        detector = RestAssuredDetector()
        assert detector.detect(str(project_dir))
        
        # Check config info
        config_info = detector.get_config_info(str(project_dir))
        assert config_info['test_framework'] == 'junit5'
    
    def test_detect_gradle_testng_project(self, tmp_path):
        """Test detection of Gradle + RestAssured + TestNG project."""
        project_dir = tmp_path / "gradle_testng"
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
    
    def test_detect_gradle_junit5_project(self, tmp_path):
        """Test detection of Gradle + RestAssured + JUnit 5 project."""
        project_dir = tmp_path / "gradle_junit5"
        project_dir.mkdir()
        
        build_content = """
        dependencies {
            testImplementation 'io.rest-assured:rest-assured:5.3.0'
            testImplementation 'org.junit.jupiter:junit-jupiter:5.10.0'
        }
        """
        (project_dir / "build.gradle").write_text(build_content)
        
        detector = RestAssuredDetector()
        assert detector.detect(str(project_dir))
        
        config_info = detector.get_config_info(str(project_dir))
        assert config_info['test_framework'] == 'junit5'
    
    def test_detect_both_frameworks(self, tmp_path):
        """Test detection when both TestNG and JUnit 5 are present."""
        project_dir = tmp_path / "both_frameworks"
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
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        (project_dir / "pom.xml").write_text(pom_content)
        
        detector = RestAssuredDetector()
        assert detector.detect(str(project_dir))
        
        config_info = detector.get_config_info(str(project_dir))
        assert config_info['test_framework'] == 'both'
    
    def test_detect_testng_source_files(self, tmp_path):
        """Test detection from TestNG source files."""
        project_dir = tmp_path / "source_testng"
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
    
    def test_detect_junit5_source_files(self, tmp_path):
        """Test detection from JUnit 5 source files."""
        project_dir = tmp_path / "source_junit5"
        project_dir.mkdir()
        src_dir = project_dir / "src" / "test" / "java"
        src_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.junit.jupiter.api.Test;
        
        public class ApiTest {
            @Test
            void testApi() {
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


class TestRestAssuredExtractorTestNG:
    """Test RestAssured test extraction for TestNG."""
    
    @pytest.fixture
    def testng_test_file(self, tmp_path):
        """Create sample TestNG test file."""
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
            }
            
            @Test(priority = 2, groups = {"regression"})
            public void testCreateUser() {
                RestAssured.given().body("{}").post("/users");
            }
            
            @Test(enabled = false, description = "Test for updating user")
            public void testUpdateUser() {
                RestAssured.put("/users/1");
            }
        }
        """
        test_file = test_dir / "UserApiTest.java"
        test_file.write_text(test_content)
        
        return tmp_path
    
    def test_extract_testng_tests(self, testng_test_file):
        """Test extracting TestNG tests."""
        config = RestAssuredConfig(project_root=str(testng_test_file))
        extractor = RestAssuredExtractor(config)
        
        tests = extractor.extract_tests(str(testng_test_file))
        
        # Should find tests (disabled one might be skipped)
        assert len(tests) >= 2
        
        # Check framework detection
        for test in tests:
            assert test.framework == "restassured-testng"
            assert test.test_type == "api"
        
        # Check class-level tags
        test1 = next((t for t in tests if "testGetUser" in t.test_name), None)
        assert test1 is not None
        assert "api" in test1.tags
        assert "smoke" in test1.tags


class TestRestAssuredExtractorJUnit5:
    """Test RestAssured test extraction for JUnit 5."""
    
    @pytest.fixture
    def junit5_test_file(self, tmp_path):
        """Create sample JUnit 5 test file."""
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        test_dir.mkdir(parents=True)
        
        test_content = """
        package com.example;
        
        import io.restassured.RestAssured;
        import io.restassured.response.Response;
        import org.junit.jupiter.api.Test;
        import org.junit.jupiter.api.DisplayName;
        import org.junit.jupiter.api.Tag;
        import org.junit.jupiter.api.Disabled;
        
        @Tag("api")
        public class UserApiTest {
            
            @Test
            @Tag("smoke")
            @DisplayName("Get user by ID")
            void testGetUser() {
                Response response = RestAssured.get("/users/1");
            }
            
            @Test
            @Tag("regression")
            @DisplayName("Create new user")
            void testCreateUser() {
                RestAssured.given().body("{}").post("/users");
            }
            
            @Test
            @Disabled
            void testUpdateUser() {
                RestAssured.put("/users/1");
            }
        }
        """
        test_file = test_dir / "UserApiTest.java"
        test_file.write_text(test_content)
        
        return tmp_path
    
    def test_extract_junit5_tests(self, junit5_test_file):
        """Test extracting JUnit 5 tests."""
        config = RestAssuredConfig(project_root=str(junit5_test_file))
        extractor = RestAssuredExtractor(config)
        
        tests = extractor.extract_tests(str(junit5_test_file))
        
        # Should find 2 enabled tests (disabled one skipped)
        assert len(tests) >= 2
        
        # Check framework detection
        for test in tests:
            assert test.framework == "restassured-junit5"
            assert test.test_type == "api"
        
        # Check class-level tags
        test1 = next((t for t in tests if "testGetUser" in t.test_name), None)
        assert test1 is not None
        assert "api" in test1.tags
        assert "smoke" in test1.tags
        
        # Check method-level tags
        test2 = next((t for t in tests if "testCreateUser" in t.test_name), None)
        assert test2 is not None
        assert "regression" in test2.tags


class TestRestAssuredAdapter:
    """Test RestAssured adapter with both frameworks."""
    
    def test_adapter_initialization_testng(self, tmp_path):
        """Test adapter initialization with TestNG."""
        project_dir = tmp_path / "testng_project"
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
        
        adapter = RestAssuredJavaAdapter(str(project_dir))
        assert adapter.config.test_framework == "testng"
    
    def test_adapter_initialization_junit5(self, tmp_path):
        """Test adapter initialization with JUnit 5."""
        project_dir = tmp_path / "junit5_project"
        project_dir.mkdir()
        
        pom_content = """
        <project>
            <dependencies>
                <dependency>
                    <groupId>io.rest-assured</groupId>
                    <artifactId>rest-assured</artifactId>
                </dependency>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        (project_dir / "pom.xml").write_text(pom_content)
        
        adapter = RestAssuredJavaAdapter(str(project_dir))
        assert adapter.config.test_framework == "junit5"
    
    def test_discover_testng_tests(self, tmp_path):
        """Test discovering TestNG tests."""
        project_dir = tmp_path / "testng_tests"
        project_dir.mkdir()
        
        # Create pom.xml
        pom = """<project>
            <dependencies>
                <dependency><groupId>io.rest-assured</groupId><artifactId>rest-assured</artifactId></dependency>
                <dependency><groupId>org.testng</groupId><artifactId>testng</artifactId></dependency>
            </dependencies>
        </project>"""
        (project_dir / "pom.xml").write_text(pom)
        
        # Create test file
        test_dir = project_dir / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test(groups = {"smoke"})
            public void test1() {
                RestAssured.get("/users");
            }
            
            @Test
            public void test2() {
                RestAssured.get("/posts");
            }
        }
        """
        (test_dir / "ApiTest.java").write_text(test_content)
        
        adapter = RestAssuredJavaAdapter(str(project_dir))
        tests = adapter.discover_tests()
        
        assert len(tests) == 2
        assert all(t.framework == "restassured-testng" for t in tests)
    
    def test_discover_junit5_tests(self, tmp_path):
        """Test discovering JUnit 5 tests."""
        project_dir = tmp_path / "junit5_tests"
        project_dir.mkdir()
        
        # Create pom.xml
        pom = """<project>
            <dependencies>
                <dependency><groupId>io.rest-assured</groupId><artifactId>rest-assured</artifactId></dependency>
                <dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId></dependency>
            </dependencies>
        </project>"""
        (project_dir / "pom.xml").write_text(pom)
        
        # Create test file
        test_dir = project_dir / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.junit.jupiter.api.Test;
        import org.junit.jupiter.api.Tag;
        
        public class ApiTest {
            @Test
            @Tag("smoke")
            void test1() {
                RestAssured.get("/users");
            }
            
            @Test
            void test2() {
                RestAssured.get("/posts");
            }
        }
        """
        (test_dir / "ApiTest.java").write_text(test_content)
        
        adapter = RestAssuredJavaAdapter(str(project_dir))
        tests = adapter.discover_tests()
        
        assert len(tests) == 2
        assert all(t.framework == "restassured-junit5" for t in tests)
    
    def test_filter_by_tags_testng(self, tmp_path):
        """Test filtering TestNG tests by groups."""
        project_dir = tmp_path / "testng_filter"
        project_dir.mkdir()
        
        pom = """<project>
            <dependencies>
                <dependency><groupId>io.rest-assured</groupId><artifactId>rest-assured</artifactId></dependency>
                <dependency><groupId>org.testng</groupId><artifactId>testng</artifactId></dependency>
            </dependencies>
        </project>"""
        (project_dir / "pom.xml").write_text(pom)
        
        test_dir = project_dir / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test(groups = {"smoke"})
            public void test1() { RestAssured.get("/users"); }
            
            @Test(groups = {"regression"})
            public void test2() { RestAssured.get("/posts"); }
        }
        """
        (test_dir / "ApiTest.java").write_text(test_content)
        
        adapter = RestAssuredJavaAdapter(str(project_dir))
        smoke_tests = adapter.discover_tests(tags=["smoke"])
        
        assert len(smoke_tests) == 1
        assert "smoke" in smoke_tests[0].tags
    
    def test_filter_by_tags_junit5(self, tmp_path):
        """Test filtering JUnit 5 tests by tags."""
        project_dir = tmp_path / "junit5_filter"
        project_dir.mkdir()
        
        pom = """<project>
            <dependencies>
                <dependency><groupId>io.rest-assured</groupId><artifactId>rest-assured</artifactId></dependency>
                <dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId></dependency>
            </dependencies>
        </project>"""
        (project_dir / "pom.xml").write_text(pom)
        
        test_dir = project_dir / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        test_content = """
        import io.restassured.RestAssured;
        import org.junit.jupiter.api.Test;
        import org.junit.jupiter.api.Tag;
        
        public class ApiTest {
            @Test
            @Tag("smoke")
            void test1() { RestAssured.get("/users"); }
            
            @Test
            @Tag("regression")
            void test2() { RestAssured.get("/posts"); }
        }
        """
        (test_dir / "ApiTest.java").write_text(test_content)
        
        adapter = RestAssuredJavaAdapter(str(project_dir))
        smoke_tests = adapter.discover_tests(tags=["smoke"])
        
        assert len(smoke_tests) == 1
        assert "smoke" in smoke_tests[0].tags
    
    def test_build_maven_command(self, tmp_path):
        """Test building Maven command."""
        config = RestAssuredConfig(project_root=str(tmp_path), build_tool="maven")
        adapter = RestAssuredJavaAdapter(str(tmp_path), config)
        
        cmd = adapter._build_maven_command(tests=None, tags=None)
        assert "mvn" in cmd
        assert "test" in cmd
    
    def test_build_gradle_command(self, tmp_path):
        """Test building Gradle command."""
        config = RestAssuredConfig(project_root=str(tmp_path), build_tool="gradle")
        adapter = RestAssuredJavaAdapter(str(tmp_path), config)
        
        cmd = adapter._build_gradle_command(tests=None, tags=None)
        assert "gradle" in cmd
        assert "test" in cmd
    
    def test_parse_surefire_reports(self, tmp_path):
        """Test parsing Maven Surefire reports."""
        reports_dir = tmp_path / "target" / "surefire-reports"
        reports_dir.mkdir(parents=True)
        
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="com.example.ApiTest" tests="2" failures="1" errors="0" skipped="0">
            <testcase classname="com.example.ApiTest" name="test1" time="0.123">
            </testcase>
            <testcase classname="com.example.ApiTest" name="test2" time="0.456">
                <failure message="Expected 200 but got 404">Stack trace</failure>
            </testcase>
        </testsuite>
        """
        (reports_dir / "TEST-com.example.ApiTest.xml").write_text(xml_content)
        
        config = RestAssuredConfig(project_root=str(tmp_path))
        adapter = RestAssuredJavaAdapter(str(tmp_path), config)
        results = adapter._parse_surefire_reports(reports_dir)
        
        assert len(results) == 2
        assert results[0].status == "pass"
        assert results[1].status == "fail"
    
    @patch('subprocess.run')
    def test_run_tests_maven(self, mock_run, tmp_path):
        """Test running tests with Maven."""
        config = RestAssuredConfig(project_root=str(tmp_path), build_tool="maven")
        adapter = RestAssuredJavaAdapter(str(tmp_path), config)
        
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        with patch.object(adapter, '_parse_results', return_value=[]):
            adapter.run_tests(tags=["smoke"])
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "mvn" in call_args
        assert "test" in call_args


class TestIntegrationTestNG:
    """Integration tests for TestNG workflow."""
    
    def test_full_testng_workflow(self, tmp_path):
        """Test complete TestNG workflow."""
        project_dir = tmp_path / "integration_testng"
        project_dir.mkdir()
        
        # Create pom.xml
        pom = """<project>
            <dependencies>
                <dependency><groupId>io.rest-assured</groupId><artifactId>rest-assured</artifactId></dependency>
                <dependency><groupId>org.testng</groupId><artifactId>testng</artifactId></dependency>
            </dependencies>
        </project>"""
        (project_dir / "pom.xml").write_text(pom)
        
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
            public void testGetAllUsers() { RestAssured.get("/users"); }
            
            @Test(priority = 2)
            public void testGetUser() { RestAssured.get("/users/1"); }
        }
        """
        (test_dir / "UserApiTest.java").write_text(test_content)
        
        # 1. Detect project
        assert RestAssuredJavaAdapter.detect_project(str(project_dir))
        
        # 2. Create adapter
        adapter = RestAssuredJavaAdapter(str(project_dir))
        assert adapter.config.build_tool == "maven"
        assert adapter.config.test_framework == "testng"
        
        # 3. Discover tests
        all_tests = adapter.discover_tests()
        assert len(all_tests) == 2
        
        # 4. Filter by tags
        smoke_tests = adapter.discover_tests(tags=["smoke"])
        assert len(smoke_tests) == 1
        assert "smoke" in smoke_tests[0].tags
        
        # 5. Verify test metadata
        test1 = next((t for t in all_tests if "testGetAllUsers" in t.test_name), None)
        assert test1 is not None
        assert test1.framework == "restassured-testng"
        assert test1.test_type == "api"
        assert "api" in test1.tags
        assert "smoke" in test1.tags


class TestIntegrationJUnit5:
    """Integration tests for JUnit 5 workflow."""
    
    def test_full_junit5_workflow(self, tmp_path):
        """Test complete JUnit 5 workflow."""
        project_dir = tmp_path / "integration_junit5"
        project_dir.mkdir()
        
        # Create pom.xml
        pom = """<project>
            <dependencies>
                <dependency><groupId>io.rest-assured</groupId><artifactId>rest-assured</artifactId></dependency>
                <dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId></dependency>
            </dependencies>
        </project>"""
        (project_dir / "pom.xml").write_text(pom)
        
        # Create test file
        test_dir = project_dir / "src" / "test" / "java" / "com" / "example"
        test_dir.mkdir(parents=True)
        
        test_content = """
        package com.example;
        import io.restassured.RestAssured;
        import org.junit.jupiter.api.Test;
        import org.junit.jupiter.api.Tag;
        
        @Tag("api")
        public class UserApiTest {
            @Test
            @Tag("smoke")
            void testGetAllUsers() { RestAssured.get("/users"); }
            
            @Test
            void testGetUser() { RestAssured.get("/users/1"); }
        }
        """
        (test_dir / "UserApiTest.java").write_text(test_content)
        
        # 1. Detect project
        assert RestAssuredJavaAdapter.detect_project(str(project_dir))
        
        # 2. Create adapter
        adapter = RestAssuredJavaAdapter(str(project_dir))
        assert adapter.config.build_tool == "maven"
        assert adapter.config.test_framework == "junit5"
        
        # 3. Discover tests
        all_tests = adapter.discover_tests()
        assert len(all_tests) == 2
        
        # 4. Filter by tags
        smoke_tests = adapter.discover_tests(tags=["smoke"])
        assert len(smoke_tests) == 1
        assert "smoke" in smoke_tests[0].tags
        
        # 5. Verify test metadata
        test1 = next((t for t in all_tests if "testGetAllUsers" in t.test_name), None)
        assert test1 is not None
        assert test1.framework == "restassured-junit5"
        assert test1.test_type == "api"
        assert "api" in test1.tags
        assert "smoke" in test1.tags
