"""
Unit tests for Java framework detection.

Tests all detection methods: build files, config files, source code, and metadata.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from adapters.selenium_java.build_detection import (
    detect_from_build_files,
    detect_from_config_files,
    detect_from_java_sources,
    detect_java_test_frameworks,
    get_primary_framework,
    detect_with_metadata,
    get_build_tool
)
from adapters.common.detection_models import (
    DetectionSource,
    DetectionConfidence
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def maven_junit_project(temp_project):
    """Create a Maven project with JUnit dependency."""
    pom_xml = temp_project / "pom.xml"
    pom_xml.write_text("""<?xml version="1.0"?>
<project>
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter-api</artifactId>
            <version>5.10.1</version>
        </dependency>
    </dependencies>
</project>
""")
    return temp_project


@pytest.fixture
def maven_testng_project(temp_project):
    """Create a Maven project with TestNG dependency."""
    pom_xml = temp_project / "pom.xml"
    pom_xml.write_text("""<?xml version="1.0"?>
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
    return temp_project


@pytest.fixture
def maven_mixed_project(temp_project):
    """Create a Maven project with both JUnit and TestNG."""
    pom_xml = temp_project / "pom.xml"
    pom_xml.write_text("""<?xml version="1.0"?>
<project>
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter-api</artifactId>
            <version>5.10.1</version>
        </dependency>
        <dependency>
            <groupId>org.testng</groupId>
            <artifactId>testng</artifactId>
            <version>7.8.0</version>
        </dependency>
    </dependencies>
</project>
""")
    return temp_project


@pytest.fixture
def gradle_junit_project(temp_project):
    """Create a Gradle project with JUnit dependency."""
    build_gradle = temp_project / "build.gradle"
    build_gradle.write_text("""
plugins {
    id 'java'
}

dependencies {
    testImplementation 'org.junit.jupiter:junit-jupiter-api:5.10.1'
}
""")
    return temp_project


@pytest.fixture
def testng_config_project(temp_project):
    """Create a project with testng.xml config file."""
    testng_xml = temp_project / "testng.xml"
    testng_xml.write_text("""<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="Test Suite">
    <test name="Sample Tests">
        <classes>
            <class name="com.example.Test"/>
        </classes>
    </test>
</suite>
""")
    return temp_project


@pytest.fixture
def source_only_junit_project(temp_project):
    """Create a project with JUnit source code but no build file."""
    source_dir = temp_project / "src" / "test" / "java" / "com" / "example"
    source_dir.mkdir(parents=True)
    
    test_file = source_dir / "SampleTest.java"
    test_file.write_text("""
package com.example;

import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class SampleTest {
    @Test
    void testSomething() {
        assertEquals(1, 1);
    }
}
""")
    return temp_project


@pytest.fixture
def source_only_testng_project(temp_project):
    """Create a project with TestNG source code but no build file."""
    source_dir = temp_project / "src" / "test" / "java" / "com" / "example"
    source_dir.mkdir(parents=True)
    
    test_file = source_dir / "SampleTest.java"
    test_file.write_text("""
package com.example;

import org.testng.annotations.*;
import static org.testng.Assert.*;

public class SampleTest {
    @Test
    public void testSomething() {
        assertEquals(1, 1);
    }
}
""")
    return temp_project


# Tests for detect_from_build_files()

def test_detect_junit_from_maven(maven_junit_project):
    """Test detecting JUnit from Maven pom.xml."""
    frameworks = detect_from_build_files(str(maven_junit_project))
    assert "junit" in frameworks
    assert "testng" not in frameworks


def test_detect_testng_from_maven(maven_testng_project):
    """Test detecting TestNG from Maven pom.xml."""
    frameworks = detect_from_build_files(str(maven_testng_project))
    assert "testng" in frameworks
    assert "junit" not in frameworks


def test_detect_mixed_from_maven(maven_mixed_project):
    """Test detecting both frameworks from Maven pom.xml."""
    frameworks = detect_from_build_files(str(maven_mixed_project))
    assert "junit" in frameworks
    assert "testng" in frameworks


def test_detect_junit_from_gradle(gradle_junit_project):
    """Test detecting JUnit from Gradle build.gradle."""
    frameworks = detect_from_build_files(str(gradle_junit_project))
    assert "junit" in frameworks


def test_no_build_files(temp_project):
    """Test detection when no build files exist."""
    frameworks = detect_from_build_files(str(temp_project))
    assert len(frameworks) == 0


# Tests for detect_from_config_files()

def test_detect_testng_from_config(testng_config_project):
    """Test detecting TestNG from testng.xml."""
    frameworks = detect_from_config_files(str(testng_config_project))
    assert "testng" in frameworks


def test_no_config_files(temp_project):
    """Test detection when no config files exist."""
    frameworks = detect_from_config_files(str(temp_project))
    assert len(frameworks) == 0


# Tests for detect_from_java_sources()

def test_detect_junit_from_source(source_only_junit_project):
    """Test detecting JUnit from source code imports."""
    source_dir = str(source_only_junit_project / "src" / "test" / "java")
    frameworks = detect_from_java_sources(source_dir)
    assert "junit" in frameworks


def test_detect_testng_from_source(source_only_testng_project):
    """Test detecting TestNG from source code imports."""
    source_dir = str(source_only_testng_project / "src" / "test" / "java")
    frameworks = detect_from_java_sources(source_dir)
    assert "testng" in frameworks


def test_no_source_files(temp_project):
    """Test detection when source directory doesn't exist."""
    frameworks = detect_from_java_sources(str(temp_project / "nonexistent"))
    assert len(frameworks) == 0


# Tests for detect_java_test_frameworks()

def test_combined_detection_maven(maven_junit_project):
    """Test combined detection merges all signals."""
    frameworks = detect_java_test_frameworks(
        str(maven_junit_project),
        str(maven_junit_project / "src" / "test" / "java")
    )
    assert "junit" in frameworks


def test_combined_detection_fallback_to_source(source_only_junit_project):
    """Test combined detection falls back to source when no build files."""
    frameworks = detect_java_test_frameworks(
        str(source_only_junit_project),
        str(source_only_junit_project / "src" / "test" / "java")
    )
    assert "junit" in frameworks


# Tests for get_primary_framework()

def test_get_primary_framework_junit(maven_junit_project):
    """Test getting primary framework when only JUnit detected."""
    framework = get_primary_framework(str(maven_junit_project))
    assert framework == "junit"


def test_get_primary_framework_testng(maven_testng_project):
    """Test getting primary framework when only TestNG detected."""
    framework = get_primary_framework(str(maven_testng_project))
    assert framework == "testng"


def test_get_primary_framework_mixed_prefers_testng(maven_mixed_project):
    """Test that mixed projects prefer TestNG as primary."""
    framework = get_primary_framework(str(maven_mixed_project))
    assert framework == "testng"


def test_get_primary_framework_defaults_to_junit(temp_project):
    """Test default to JUnit when nothing detected."""
    framework = get_primary_framework(str(temp_project))
    assert framework == "junit"


# Tests for get_build_tool()

def test_get_build_tool_maven(maven_junit_project):
    """Test detecting Maven as build tool."""
    build_tool = get_build_tool(str(maven_junit_project))
    assert build_tool == "maven"


def test_get_build_tool_gradle(gradle_junit_project):
    """Test detecting Gradle as build tool."""
    build_tool = get_build_tool(str(gradle_junit_project))
    assert build_tool == "gradle"


def test_get_build_tool_unknown(temp_project):
    """Test unknown when no build tool detected."""
    build_tool = get_build_tool(str(temp_project))
    assert build_tool == "unknown"


# Tests for detect_with_metadata()

def test_metadata_detection_maven_high_confidence(maven_junit_project):
    """Test metadata detection returns high confidence for build files."""
    result = detect_with_metadata(str(maven_junit_project))
    
    assert len(result.detections) == 1
    assert result.detections[0].framework == "junit"
    assert result.detections[0].detection_source == DetectionSource.POM_XML
    assert result.detections[0].confidence == DetectionConfidence.HIGH
    assert "pom.xml" in result.detections[0].file_path


def test_metadata_detection_source_medium_confidence(source_only_junit_project):
    """Test metadata detection returns medium confidence for source code."""
    result = detect_with_metadata(
        str(source_only_junit_project),
        str(source_only_junit_project / "src" / "test" / "java")
    )
    
    assert len(result.detections) > 0
    junit_detection = [d for d in result.detections if d.framework == "junit"][0]
    assert junit_detection.detection_source == DetectionSource.SOURCE_IMPORTS
    assert junit_detection.confidence == DetectionConfidence.MEDIUM


def test_metadata_detection_mixed_frameworks(maven_mixed_project):
    """Test metadata detection for mixed frameworks."""
    result = detect_with_metadata(str(maven_mixed_project))
    
    frameworks = result.get_frameworks()
    assert "junit" in frameworks
    assert "testng" in frameworks
    
    # Both should be from pom.xml with high confidence
    for detection in result.detections:
        assert detection.detection_source == DetectionSource.POM_XML
        assert detection.confidence == DetectionConfidence.HIGH


def test_metadata_detection_testng_config_signal(testng_config_project):
    """Test metadata detection includes testng.xml as signal."""
    result = detect_with_metadata(str(testng_config_project))
    
    assert len(result.detections) == 1
    assert result.detections[0].framework == "testng"
    assert result.detections[0].detection_source == DetectionSource.TESTNG_XML
    assert result.detections[0].confidence == DetectionConfidence.HIGH


def test_metadata_to_dict_serialization(maven_junit_project):
    """Test metadata can be serialized to dict."""
    result = detect_with_metadata(str(maven_junit_project))
    data = result.to_dict()
    
    assert "project_root" in data
    assert "detections" in data
    assert isinstance(data["detections"], list)
    assert data["detections"][0]["framework"] == "junit"
    assert data["detections"][0]["detection_source"] == "pom.xml"
    assert data["detections"][0]["confidence"] == "high"


def test_metadata_from_dict_deserialization(maven_junit_project):
    """Test metadata can be deserialized from dict."""
    result = detect_with_metadata(str(maven_junit_project))
    data = result.to_dict()
    
    restored = type(result).from_dict(data)
    
    assert restored.project_root == result.project_root
    assert len(restored.detections) == len(result.detections)
    assert restored.detections[0].framework == result.detections[0].framework


# Edge cases

def test_empty_pom_xml(temp_project):
    """Test handling empty pom.xml."""
    pom_xml = temp_project / "pom.xml"
    pom_xml.write_text("")
    
    frameworks = detect_from_build_files(str(temp_project))
    assert len(frameworks) == 0


def test_malformed_pom_xml(temp_project):
    """Test handling malformed pom.xml."""
    pom_xml = temp_project / "pom.xml"
    pom_xml.write_text("not valid xml {{{")
    
    # Should not crash, just return empty
    frameworks = detect_from_build_files(str(temp_project))
    assert isinstance(frameworks, set)


def test_empty_java_file(temp_project):
    """Test handling empty Java source file."""
    source_dir = temp_project / "src" / "test" / "java"
    source_dir.mkdir(parents=True)
    
    test_file = source_dir / "Empty.java"
    test_file.write_text("")
    
    frameworks = detect_from_java_sources(str(source_dir))
    assert len(frameworks) == 0
