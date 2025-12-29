"""
Unit tests for Java framework detector (JUnit vs TestNG).

Tests cover:
- JUnit detection from pom.xml
- TestNG detection from pom.xml
- Mixed framework detection
- Gradle detection
- Source code detection
- Edge cases
"""

import pytest
from pathlib import Path
from adapters.selenium_java.config import SeleniumJavaConfig


class TestFrameworkDetectionFromPom:
    """Test framework detection from Maven pom.xml."""
    
    def test_detect_junit_jupiter_from_pom(self, tmp_path):
        """Test detecting JUnit 5 (Jupiter) from pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter-api</artifactId>
                    <version>5.9.0</version>
                </dependency>
            </dependencies>
        </project>
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        assert "junit5" in frameworks or "junit" in frameworks
        assert "testng" not in frameworks
    
    def test_detect_junit4_from_pom(self, tmp_path):
        """Test detecting JUnit 4 from pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""
        <project>
            <dependencies>
                <dependency>
                    <groupId>junit</groupId>
                    <artifactId>junit</artifactId>
                    <version>4.13.2</version>
                </dependency>
            </dependencies>
        </project>
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        assert "junit" in frameworks or "junit4" in frameworks
        assert "testng" not in frameworks
    
    def test_detect_testng_from_pom(self, tmp_path):
        """Test detecting TestNG from pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.testng</groupId>
                    <artifactId>testng</artifactId>
                    <version>7.8.0</version>
                </dependency>
            </dependencies>
        </project>
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        assert "testng" in frameworks
        assert "junit" not in frameworks
    
    def test_detect_mixed_frameworks_from_pom(self, tmp_path):
        """Test detecting both JUnit and TestNG in same project (REAL-WORLD)."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter-api</artifactId>
                </dependency>
                <dependency>
                    <groupId>org.testng</groupId>
                    <artifactId>testng</artifactId>
                </dependency>
            </dependencies>
        </project>
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        # Should detect both
        assert len(frameworks) >= 2
        assert any("junit" in f.lower() for f in frameworks)
        assert any("testng" in f.lower() for f in frameworks)


class TestFrameworkDetectionFromGradle:
    """Test framework detection from Gradle build files."""
    
    def test_detect_junit_from_gradle(self, tmp_path):
        """Test detecting JUnit from build.gradle."""
        build_gradle = tmp_path / "build.gradle"
        build_gradle.write_text("""
        dependencies {
            testImplementation 'org.junit.jupiter:junit-jupiter-api:5.9.0'
        }
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        assert "junit" in frameworks or "junit5" in frameworks
    
    def test_detect_testng_from_gradle(self, tmp_path):
        """Test detecting TestNG from build.gradle."""
        build_gradle = tmp_path / "build.gradle"
        build_gradle.write_text("""
        dependencies {
            testImplementation 'org.testng:testng:7.8.0'
        }
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        assert "testng" in frameworks


class TestFrameworkDetectionFromSource:
    """Test framework detection from Java source code."""
    
    def test_detect_junit_from_imports(self, tmp_path):
        """Test detecting JUnit from @Test annotation imports."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "LoginTest.java"
        test_file.write_text("""
        package com.example;
        
        import org.junit.jupiter.api.Test;
        
        public class LoginTest {
            @Test
            void testLogin() {}
        }
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        assert "junit" in frameworks or "junit5" in frameworks
    
    def test_detect_testng_from_imports(self, tmp_path):
        """Test detecting TestNG from @Test annotation imports."""
        src_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
        src_dir.mkdir(parents=True)
        
        test_file = src_dir / "LoginTest.java"
        test_file.write_text("""
        package com.example;
        
        import org.testng.annotations.Test;
        
        public class LoginTest {
            @Test
            public void testLogin() {}
        }
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        assert "testng" in frameworks


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_no_build_file(self, tmp_path):
        """Test when no pom.xml or build.gradle exists."""
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        # Should return empty set, not crash
        assert isinstance(frameworks, set)
    
    def test_empty_pom_xml(self, tmp_path):
        """Test with empty pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project></project>")
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        # Should not crash
        assert isinstance(frameworks, set)
    
    def test_malformed_pom_xml(self, tmp_path):
        """Test with malformed pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text("this is not xml")
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        # Should not crash
        assert isinstance(frameworks, set)
    
    def test_no_test_directory(self, tmp_path):
        """Test when src/test/java doesn't exist."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter-api</artifactId>
                </dependency>
            </dependencies>
        </project>
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path / "src" / "test" / "java")
        )
        
        # Should still detect from pom.xml
        assert "junit" in frameworks or "junit5" in frameworks
    
    def test_invalid_java_file_does_not_crash(self, tmp_path):
        """Test that invalid Java files don't crash detection."""
        src_dir = tmp_path / "src" / "test" / "java"
        src_dir.mkdir(parents=True)
        
        bad_file = src_dir / "BadTest.java"
        bad_file.write_text("this is not java @#$%^")
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(src_dir)
        )
        
        # Should not crash
        assert isinstance(frameworks, set)


class TestDetectionContract:
    """Test that detection contract remains stable."""
    
    def test_return_type_is_set(self, tmp_path):
        """Test that detect_all_frameworks returns a set."""
        result = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path)
        )
        
        assert isinstance(result, set)
    
    def test_framework_names_are_lowercase(self, tmp_path):
        """Test that framework names are normalized to lowercase."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter-api</artifactId>
                </dependency>
            </dependencies>
        </project>
        """)
        
        frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path)
        )
        
        # All framework names should be lowercase
        for framework in frameworks:
            assert framework == framework.lower()
    
    def test_empty_result_is_empty_set_not_none(self, tmp_path):
        """Test that no frameworks returns empty set, not None."""
        result = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(tmp_path),
            source_root=str(tmp_path)
        )
        
        assert result == set()
        assert result is not None
