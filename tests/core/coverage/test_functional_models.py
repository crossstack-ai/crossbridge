"""
Unit tests for functional coverage models.
"""

import pytest
import uuid
from datetime import datetime

from core.coverage.functional_models import (
    Feature, CodeUnit, ExternalTestCase, ExternalTestRef,
    TestCaseExternalMap, TestFeatureMap, TestCodeCoverageMap,
    ChangeEvent, ChangeImpact,
    FunctionalCoverageMapEntry, TestToFeatureCoverageEntry,
    ChangeImpactSurfaceEntry, FunctionalCoverageMapReport,
    TestToFeatureCoverageReport, ChangeImpactSurfaceReport,
    FeatureType, FeatureSource, ExternalSystem, MappingSource,
    ChangeType, ImpactReason, parse_external_test_refs
)


class TestFeatureModel:
    """Tests for Feature model."""
    
    def test_feature_creation(self):
        """Test basic feature creation."""
        feature = Feature(
            name="Login",
            type=FeatureType.BDD,
            source=FeatureSource.CUCUMBER,
            description="Login functionality"
        )
        
        assert feature.name == "Login"
        assert feature.type == FeatureType.BDD
        assert feature.source == FeatureSource.CUCUMBER
        assert feature.description == "Login functionality"
        assert isinstance(feature.id, uuid.UUID)
        assert isinstance(feature.created_at, datetime)
    
    def test_feature_with_parent(self):
        """Test feature with parent relationship."""
        parent_id = uuid.uuid4()
        feature = Feature(
            name="Login Form",
            type=FeatureType.COMPONENT,
            source=FeatureSource.CODE,
            parent_feature_id=parent_id
        )
        
        assert feature.parent_feature_id == parent_id


class TestCodeUnitModel:
    """Tests for CodeUnit model."""
    
    def test_code_unit_creation(self):
        """Test basic code unit creation."""
        code_unit = CodeUnit(
            file_path="src/LoginService.java",
            class_name="LoginService",
            method_name="authenticate",
            package_name="com.example.auth"
        )
        
        assert code_unit.file_path == "src/LoginService.java"
        assert code_unit.class_name == "LoginService"
        assert code_unit.method_name == "authenticate"
        assert code_unit.package_name == "com.example.auth"
    
    def test_code_unit_full_name(self):
        """Test full name generation."""
        code_unit = CodeUnit(
            file_path="src/LoginService.java",
            class_name="LoginService",
            method_name="authenticate",
            package_name="com.example.auth"
        )
        
        expected = "com.example.auth.LoginService.authenticate"
        assert code_unit.full_name == expected
    
    def test_code_unit_full_name_without_package(self):
        """Test full name without package."""
        code_unit = CodeUnit(
            file_path="src/LoginService.java",
            class_name="LoginService",
            method_name="authenticate"
        )
        
        assert code_unit.full_name == "LoginService.authenticate"
    
    def test_code_unit_full_name_file_only(self):
        """Test full name with only file path."""
        code_unit = CodeUnit(
            file_path="src/utils.py"
        )
        
        assert code_unit.full_name == "src/utils.py"
    
    def test_code_unit_equality(self):
        """Test code unit equality."""
        cu1 = CodeUnit(
            file_path="src/test.java",
            class_name="Test",
            method_name="test"
        )
        cu2 = CodeUnit(
            file_path="src/test.java",
            class_name="Test",
            method_name="test"
        )
        cu3 = CodeUnit(
            file_path="src/test.java",
            class_name="Test",
            method_name="other"
        )
        
        assert cu1 == cu2
        assert cu1 != cu3
    
    def test_code_unit_hashable(self):
        """Test code unit can be used in sets."""
        cu1 = CodeUnit(file_path="test.py", class_name="Test")
        cu2 = CodeUnit(file_path="test.py", class_name="Test")
        
        code_units = {cu1, cu2}
        assert len(code_units) == 1  # Should be deduplicated


class TestExternalTestCaseModel:
    """Tests for ExternalTestCase model."""
    
    def test_external_test_case_creation(self):
        """Test external test case creation."""
        tc = ExternalTestCase(
            system=ExternalSystem.TESTRAIL,
            external_id="C12345",
            title="Valid Login Test",
            priority="high"
        )
        
        assert tc.system == ExternalSystem.TESTRAIL
        assert tc.external_id == "C12345"
        assert tc.title == "Valid Login Test"
        assert tc.priority == "high"
    
    def test_external_test_case_full_id(self):
        """Test full ID property."""
        tc = ExternalTestCase(
            system=ExternalSystem.TESTRAIL,
            external_id="C12345"
        )
        
        assert tc.full_id == "testrail:C12345"


class TestExternalTestRefModel:
    """Tests for ExternalTestRef model."""
    
    def test_external_test_ref_creation(self):
        """Test external test ref creation."""
        ref = ExternalTestRef(
            system="testrail",
            external_id="C12345",
            source="annotation"
        )
        
        assert ref.system == "testrail"
        assert ref.external_id == "C12345"
        assert ref.source == "annotation"
        assert ref.confidence == 1.0


class TestConsoleOutputModels:
    """Tests for console output models."""
    
    def test_functional_coverage_map_entry(self):
        """Test functional coverage map entry."""
        entry = FunctionalCoverageMapEntry(
            code_unit="LoginService.authenticate",
            test_count=14,
            testrail_tcs=["C12345", "C12401"],
            avg_coverage=85.5
        )
        
        row = entry.to_row()
        assert row[0] == "LoginService.authenticate"
        assert row[1] == 14
        assert "C12345" in row[2]
        assert "C12401" in row[2]
    
    def test_functional_coverage_map_entry_many_tcs(self):
        """Test entry with many TestRail TCs."""
        entry = FunctionalCoverageMapEntry(
            code_unit="Test",
            test_count=5,
            testrail_tcs=["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
        )
        
        row = entry.to_row()
        assert "+2 more" in row[2]  # Should truncate
    
    def test_test_to_feature_coverage_entry(self):
        """Test test-to-feature coverage entry."""
        entry = TestToFeatureCoverageEntry(
            feature="Login",
            feature_type="bdd",
            test_name="LoginTest.testValid",
            testrail_tc="C12345",
            confidence=0.95
        )
        
        row = entry.to_row()
        assert row[0] == "Login"
        assert row[1] == "LoginTest.testValid"
        assert row[2] == "C12345"
    
    def test_change_impact_surface_entry(self):
        """Test change impact surface entry."""
        entry = ChangeImpactSurfaceEntry(
            impacted_test="LoginTest.testValid",
            feature="Login",
            testrail_tc="C12345",
            coverage_percentage=85.5
        )
        
        row = entry.to_row()
        assert row[0] == "LoginTest.testValid"
        assert row[1] == "Login"
        assert row[2] == "C12345"


class TestReportModels:
    """Tests for report models."""
    
    def test_functional_coverage_map_report(self):
        """Test functional coverage map report."""
        entries = [
            FunctionalCoverageMapEntry("Test1", 5, ["C1"]),
            FunctionalCoverageMapEntry("Test2", 3, ["C2"])
        ]
        
        report = FunctionalCoverageMapReport(
            entries=entries,
            total_code_units=2,
            total_tests=8,
            total_external_tcs=2
        )
        
        assert len(report.entries) == 2
        assert report.total_code_units == 2
        assert report.total_tests == 8
        assert report.total_external_tcs == 2
        assert isinstance(report.generated_at, datetime)
    
    def test_test_to_feature_coverage_report(self):
        """Test test-to-feature coverage report."""
        entries = [
            TestToFeatureCoverageEntry("Login", "bdd", "Test1"),
            TestToFeatureCoverageEntry("Logout", "bdd", "Test2")
        ]
        
        report = TestToFeatureCoverageReport(
            entries=entries,
            total_features=2,
            total_tests=2,
            features_without_tests=1
        )
        
        assert len(report.entries) == 2
        assert report.total_features == 2
        assert report.features_without_tests == 1
    
    def test_change_impact_surface_report(self):
        """Test change impact surface report."""
        entries = [
            ChangeImpactSurfaceEntry("Test1", "Login", "C1"),
            ChangeImpactSurfaceEntry("Test2", "Login", "C2")
        ]
        
        report = ChangeImpactSurfaceReport(
            changed_file="LoginService.java",
            entries=entries,
            total_impacted_tests=2,
            total_impacted_features=1
        )
        
        assert report.changed_file == "LoginService.java"
        assert len(report.entries) == 2
        assert report.total_impacted_tests == 2
        assert report.total_impacted_features == 1


class TestParseExternalTestRefs:
    """Tests for parse_external_test_refs function."""
    
    def test_parse_testrail_annotation(self):
        """Test parsing TestRail annotation."""
        annotations = ['@TestRail(id = "C12345")']
        tags = []
        
        refs = parse_external_test_refs(annotations, tags)
        
        assert len(refs) == 1
        assert refs[0].system == "testrail"
        assert refs[0].external_id == "C12345"
        assert refs[0].source == "annotation"
    
    def test_parse_external_test_case_annotation(self):
        """Test parsing ExternalTestCase annotation."""
        annotations = ['@ExternalTestCase("C12345")']
        tags = []
        
        refs = parse_external_test_refs(annotations, tags)
        
        assert len(refs) == 1
        assert refs[0].system == "testrail"
        assert refs[0].external_id == "C12345"
    
    def test_parse_testrail_tag(self):
        """Test parsing TestRail tag."""
        annotations = []
        tags = ['testrail:C12345', 'smoke']
        
        refs = parse_external_test_refs(annotations, tags)
        
        assert len(refs) == 1
        assert refs[0].system == "testrail"
        assert refs[0].external_id == "C12345"
        assert refs[0].source == "tag"
    
    def test_parse_zephyr_tag(self):
        """Test parsing Zephyr tag."""
        annotations = []
        tags = ['zephyr:T-1234']
        
        refs = parse_external_test_refs(annotations, tags)
        
        assert len(refs) == 1
        assert refs[0].system == "zephyr"
        assert refs[0].external_id == "T-1234"
    
    def test_parse_multiple_refs(self):
        """Test parsing multiple references."""
        annotations = ['@TestRail(id = "C12345")']
        tags = ['zephyr:T-1234', 'qtest:TC-999']
        
        refs = parse_external_test_refs(annotations, tags)
        
        assert len(refs) == 3
        systems = [ref.system for ref in refs]
        assert "testrail" in systems
        assert "zephyr" in systems
        assert "qtest" in systems
    
    def test_parse_at_prefix_tag(self):
        """Test parsing tag with @ prefix."""
        annotations = []
        tags = ['@testrail:C12345']
        
        refs = parse_external_test_refs(annotations, tags)
        
        assert len(refs) == 1
        assert refs[0].external_id == "C12345"
    
    def test_parse_no_refs(self):
        """Test parsing when no refs present."""
        annotations = ['@Test', '@Before']
        tags = ['smoke', 'regression']
        
        refs = parse_external_test_refs(annotations, tags)
        
        assert len(refs) == 0


class TestEnums:
    """Tests for enum types."""
    
    def test_feature_type_enum(self):
        """Test FeatureType enum."""
        assert FeatureType.API.value == "api"
        assert FeatureType.SERVICE.value == "service"
        assert FeatureType.BDD.value == "bdd"
    
    def test_feature_source_enum(self):
        """Test FeatureSource enum."""
        assert FeatureSource.CUCUMBER.value == "cucumber"
        assert FeatureSource.JIRA.value == "jira"
        assert FeatureSource.CODE.value == "code"
    
    def test_external_system_enum(self):
        """Test ExternalSystem enum."""
        assert ExternalSystem.TESTRAIL.value == "testrail"
        assert ExternalSystem.ZEPHYR.value == "zephyr"
        assert ExternalSystem.QTEST.value == "qtest"
    
    def test_mapping_source_enum(self):
        """Test MappingSource enum."""
        assert MappingSource.ANNOTATION.value == "annotation"
        assert MappingSource.TAG.value == "tag"
        assert MappingSource.COVERAGE.value == "coverage"
