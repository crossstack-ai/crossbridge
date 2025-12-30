"""
Unit tests for JaCoCo XML parser.
"""

import pytest
from pathlib import Path
from xml.etree import ElementTree as ET

from core.coverage.jacoco_parser import JaCoCoXMLParser, JaCoCoReportLocator
from core.coverage.models import ExecutionMode, CoverageType


@pytest.fixture
def sample_jacoco_xml(tmp_path):
    """Create a sample JaCoCo XML report."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<report name="Test Coverage">
    <package name="com/example/service">
        <class name="com/example/service/LoginService" sourcefilename="LoginService.java">
            <method name="authenticate" desc="(Ljava/lang/String;Ljava/lang/String;)Z" line="15">
                <counter type="INSTRUCTION" missed="5" covered="45"/>
                <counter type="LINE" missed="2" covered="18"/>
                <counter type="BRANCH" missed="1" covered="3"/>
            </method>
            <method name="logout" desc="()V" line="35">
                <counter type="INSTRUCTION" missed="0" covered="10"/>
                <counter type="LINE" missed="0" covered="5"/>
            </method>
            <counter type="INSTRUCTION" missed="5" covered="55"/>
            <counter type="LINE" missed="2" covered="23"/>
            <counter type="METHOD" missed="0" covered="2"/>
        </class>
        <class name="com/example/service/UserService" sourcefilename="UserService.java">
            <method name="getUser" desc="(I)Lcom/example/User;" line="20">
                <counter type="INSTRUCTION" missed="2" covered="28"/>
                <counter type="LINE" missed="1" covered="12"/>
            </method>
            <counter type="INSTRUCTION" missed="2" covered="28"/>
            <counter type="LINE" missed="1" covered="12"/>
            <counter type="METHOD" missed="0" covered="1"/>
        </class>
    </package>
    <package name="com/example/page">
        <class name="com/example/page/LoginPage" sourcefilename="LoginPage.java">
            <method name="open" desc="()V" line="10">
                <counter type="INSTRUCTION" missed="0" covered="15"/>
                <counter type="LINE" missed="0" covered="7"/>
            </method>
            <counter type="INSTRUCTION" missed="0" covered="15"/>
            <counter type="LINE" missed="0" covered="7"/>
            <counter type="METHOD" missed="0" covered="1"/>
        </class>
    </package>
    <counter type="INSTRUCTION" missed="7" covered="98"/>
    <counter type="LINE" missed="3" covered="42"/>
    <counter type="METHOD" missed="0" covered="4"/>
    <counter type="CLASS" missed="0" covered="3"/>
</report>
"""
    
    xml_file = tmp_path / "jacoco.xml"
    xml_file.write_text(xml_content)
    return xml_file


@pytest.fixture
def minimal_jacoco_xml(tmp_path):
    """Create a minimal JaCoCo XML report."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<report name="Minimal Coverage">
    <package name="com/example">
        <class name="com/example/SimpleClass">
            <method name="simpleMethod" desc="()V">
                <counter type="INSTRUCTION" missed="0" covered="10"/>
            </method>
            <counter type="INSTRUCTION" missed="0" covered="10"/>
        </class>
    </package>
</report>
"""
    
    xml_file = tmp_path / "jacoco-minimal.xml"
    xml_file.write_text(xml_content)
    return xml_file


class TestJaCoCoXMLParser:
    """Tests for JaCoCoXMLParser."""
    
    def test_parse_basic_report(self, sample_jacoco_xml):
        """Test parsing a basic JaCoCo report."""
        parser = JaCoCoXMLParser()
        
        mapping = parser.parse(
            xml_path=sample_jacoco_xml,
            test_id="LoginTest.testAuthenticate",
            test_name="testAuthenticate",
            execution_mode=ExecutionMode.ISOLATED
        )
        
        assert mapping.test_id == "LoginTest.testAuthenticate"
        assert mapping.test_name == "testAuthenticate"
        assert mapping.execution_mode == ExecutionMode.ISOLATED
        
        # Should cover 3 classes
        assert len(mapping.covered_classes) == 3
        assert "com.example.service.LoginService" in mapping.covered_classes
        assert "com.example.service.UserService" in mapping.covered_classes
        assert "com.example.page.LoginPage" in mapping.covered_classes
        
        # Should cover 4 methods
        assert len(mapping.covered_methods) == 4
    
    def test_parse_with_high_confidence(self, sample_jacoco_xml):
        """Test that isolated execution gets high confidence."""
        parser = JaCoCoXMLParser()
        
        mapping = parser.parse(
            xml_path=sample_jacoco_xml,
            test_id="test1",
            execution_mode=ExecutionMode.ISOLATED
        )
        
        assert mapping.confidence >= 0.90
    
    def test_parse_minimal_report(self, minimal_jacoco_xml):
        """Test parsing a minimal report."""
        parser = JaCoCoXMLParser()
        
        mapping = parser.parse(
            xml_path=minimal_jacoco_xml,
            test_id="test1",
            execution_mode=ExecutionMode.ISOLATED
        )
        
        assert len(mapping.covered_classes) == 1
        assert "com.example.SimpleClass" in mapping.covered_classes
        assert len(mapping.covered_methods) == 1
    
    def test_parse_batch(self, sample_jacoco_xml):
        """Test parsing batch coverage."""
        parser = JaCoCoXMLParser()
        
        test_ids = ["Test1", "Test2", "Test3"]
        
        mappings_dict = parser.parse_batch(
            xml_path=sample_jacoco_xml,
            test_ids=test_ids,
            execution_mode=ExecutionMode.SMALL_BATCH
        )
        
        assert len(mappings_dict) == 3
        
        # All should have same coverage (batch correlation)
        for mapping in mappings_dict.values():
            assert len(mapping.covered_classes) == 3
            assert mapping.execution_mode == ExecutionMode.SMALL_BATCH
            # Batch confidence should be lower
            assert mapping.confidence < 0.90
    
    def test_extract_covered_classes_only(self, sample_jacoco_xml):
        """Test extracting only class names."""
        parser = JaCoCoXMLParser()
        
        classes = parser.extract_covered_classes_only(sample_jacoco_xml)
        
        assert len(classes) == 3
        assert "com.example.service.LoginService" in classes
        assert "com.example.service.UserService" in classes
        assert "com.example.page.LoginPage" in classes
    
    def test_extract_covered_methods_only(self, sample_jacoco_xml):
        """Test extracting only method names."""
        parser = JaCoCoXMLParser()
        
        methods = parser.extract_covered_methods_only(sample_jacoco_xml)
        
        assert len(methods) == 4
        assert "com.example.service.LoginService.authenticate" in methods
        assert "com.example.service.LoginService.logout" in methods
        assert "com.example.service.UserService.getUser" in methods
        assert "com.example.page.LoginPage.open" in methods
    
    def test_parse_coverage_types(self, sample_jacoco_xml):
        """Test that different coverage types are parsed."""
        parser = JaCoCoXMLParser()
        
        mapping = parser.parse(
            xml_path=sample_jacoco_xml,
            test_id="test1",
            execution_mode=ExecutionMode.ISOLATED
        )
        
        # Should have different coverage types based on which fields are populated
        has_instruction = any(unit.instruction_coverage is not None for unit in mapping.covered_code_units)
        has_line = any(unit.line_coverage is not None for unit in mapping.covered_code_units)
        has_branch = any(unit.branch_coverage is not None for unit in mapping.covered_code_units)
        
        # At least one coverage type should be present
        assert has_instruction or has_line or has_branch
    
    def test_parse_nonexistent_file(self):
        """Test parsing a nonexistent file."""
        parser = JaCoCoXMLParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse(
                xml_path=Path("/nonexistent/jacoco.xml"),
                test_id="test1",
                execution_mode=ExecutionMode.ISOLATED
            )
    
    def test_class_name_conversion(self, sample_jacoco_xml):
        """Test that class names are converted from path to dotted notation."""
        parser = JaCoCoXMLParser()
        
        classes = parser.extract_covered_classes_only(sample_jacoco_xml)
        
        # Should have dots, not slashes
        for class_name in classes:
            assert "/" not in class_name
            assert "." in class_name


class TestJaCoCoReportLocator:
    """Tests for JaCoCoReportLocator."""
    
    def test_find_maven_report(self, tmp_path):
        """Test finding JaCoCo report in Maven project."""
        # Create Maven structure
        report_dir = tmp_path / "target" / "site" / "jacoco"
        report_dir.mkdir(parents=True)
        report_file = report_dir / "jacoco.xml"
        report_file.write_text("<report></report>")
        
        locator = JaCoCoReportLocator()
        found = locator.find_report(tmp_path)
        
        assert found is not None
        assert found == report_file
    
    def test_find_gradle_report(self, tmp_path):
        """Test finding JaCoCo report in Gradle project."""
        # Create Gradle structure
        report_dir = tmp_path / "build" / "reports" / "jacoco" / "test"
        report_dir.mkdir(parents=True)
        report_file = report_dir / "jacocoTestReport.xml"
        report_file.write_text("<report></report>")
        
        locator = JaCoCoReportLocator()
        found = locator.find_report(tmp_path)
        
        assert found is not None
        assert found == report_file
    
    def test_find_report_not_found(self, tmp_path):
        """Test when report is not found."""
        locator = JaCoCoReportLocator()
        found = locator.find_report(tmp_path)
        
        assert found is None
    
    def test_find_multiple_reports_prefers_maven(self, tmp_path):
        """Test that Maven report is preferred when multiple exist."""
        # Create both Maven and Gradle reports
        maven_dir = tmp_path / "target" / "site" / "jacoco"
        maven_dir.mkdir(parents=True)
        maven_file = maven_dir / "jacoco.xml"
        maven_file.write_text("<report>Maven</report>")
        
        gradle_dir = tmp_path / "build" / "reports" / "jacoco" / "test"
        gradle_dir.mkdir(parents=True)
        gradle_file = gradle_dir / "jacocoTestReport.xml"
        gradle_file.write_text("<report>Gradle</report>")
        
        locator = JaCoCoReportLocator()
        found = locator.find_report(tmp_path)
        
        # Should prefer Maven
        assert found == maven_file
    
    def test_get_common_locations(self):
        """Test getting common report locations."""
        locator = JaCoCoReportLocator()
        locations = locator.get_common_locations(Path("/project"))
        
        assert len(locations) > 0
        assert any("target" in str(loc) for loc in locations)
        assert any("build" in str(loc) for loc in locations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
