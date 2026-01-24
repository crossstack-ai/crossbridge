"""
Unit tests for console formatter.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime

from core.coverage.console_formatter import (
    print_functional_coverage_map,
    print_test_to_feature_coverage,
    print_change_impact_surface,
    print_coverage_gaps,
    export_to_csv,
    export_to_json
)
from core.coverage.functional_models import (
    FunctionalCoverageMapReport,
    TestToFeatureCoverageReport,
    ChangeImpactSurfaceReport,
    FunctionalCoverageMapEntry,
    TestToFeatureCoverageEntry,
    ChangeImpactSurfaceEntry,
    Feature, FeatureType, FeatureSource
)


class TestPrintFunctions:
    """Tests for print functions."""
    
    def test_print_functional_coverage_map(self, capsys):
        """Test printing functional coverage map."""
        entries = [
            FunctionalCoverageMapEntry(
                code_unit="LoginService.authenticate",
                test_count=14,
                testrail_tcs=["C12345", "C12401"]
            ),
            FunctionalCoverageMapEntry(
                code_unit="AuthController.login",
                test_count=9,
                testrail_tcs=["C12011"]
            )
        ]
        
        report = FunctionalCoverageMapReport(
            entries=entries,
            total_code_units=2,
            total_tests=23,
            total_external_tcs=3
        )
        
        print_functional_coverage_map(report)
        
        captured = capsys.readouterr()
        assert "Functional Coverage Map" in captured.out
        assert "LoginService.authenticate" in captured.out
        assert "14" in captured.out
        assert "C12345" in captured.out
    
    def test_print_test_to_feature_coverage(self, capsys):
        """Test printing test-to-feature coverage."""
        entries = [
            TestToFeatureCoverageEntry(
                feature="Login",
                feature_type="bdd",
                test_name="LoginTest.testValid",
                testrail_tc="C12345"
            ),
            TestToFeatureCoverageEntry(
                feature="Login",
                feature_type="bdd",
                test_name="LoginBDD.ValidLogin",
                testrail_tc="C12401"
            )
        ]
        
        report = TestToFeatureCoverageReport(
            entries=entries,
            total_features=1,
            total_tests=2,
            features_without_tests=0
        )
        
        print_test_to_feature_coverage(report)
        
        captured = capsys.readouterr()
        assert "Test-to-Feature Coverage" in captured.out
        assert "Login" in captured.out
        assert "LoginTest.testValid" in captured.out
    
    def test_print_change_impact_surface(self, capsys):
        """Test printing change impact surface."""
        entries = [
            ChangeImpactSurfaceEntry(
                impacted_test="LoginTest.testValid",
                feature="Login",
                testrail_tc="C12345"
            )
        ]
        
        report = ChangeImpactSurfaceReport(
            changed_file="LoginService.java",
            entries=entries,
            total_impacted_tests=1,
            total_impacted_features=1
        )
        
        print_change_impact_surface(report)
        
        captured = capsys.readouterr()
        assert "Change Impact Surface" in captured.out
        assert "LoginService.java" in captured.out
        assert "LoginTest.testValid" in captured.out
    
    def test_print_coverage_gaps(self, capsys):
        """Test printing coverage gaps."""
        features = [
            Feature(
                name="Payment Processing",
                type=FeatureType.SERVICE,
                source=FeatureSource.CODE
            ),
            Feature(
                name="Order Management",
                type=FeatureType.API,
                source=FeatureSource.API_SPEC
            )
        ]
        
        print_coverage_gaps(features)
        
        captured = capsys.readouterr()
        assert "Coverage Gaps" in captured.out
        assert "Payment Processing" in captured.out
        assert "Order Management" in captured.out
    
    def test_print_empty_coverage_gaps(self, capsys):
        """Test printing empty coverage gaps."""
        print_coverage_gaps([])
        
        captured = capsys.readouterr()
        assert "Coverage Gaps" in captured.out
        assert "All features have test coverage" in captured.out


class TestExportFunctions:
    """Tests for export functions."""
    
    def test_export_functional_coverage_to_csv(self):
        """Test exporting functional coverage map to CSV."""
        entries = [
            FunctionalCoverageMapEntry(
                code_unit="LoginService",
                test_count=14,
                testrail_tcs=["C12345", "C12401"]
            )
        ]
        
        report = FunctionalCoverageMapReport(
            entries=entries,
            total_code_units=1,
            total_tests=14,
            total_external_tcs=2
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
        
        try:
            export_to_csv(report, temp_file)
            
            # Verify file exists and has content
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "Code Unit" in content
                assert "LoginService" in content
                assert "14" in content
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_export_test_to_feature_coverage_to_csv(self):
        """Test exporting test-to-feature coverage to CSV."""
        entries = [
            TestToFeatureCoverageEntry(
                feature="Login",
                feature_type="bdd",
                test_name="LoginTest",
                testrail_tc="C12345"
            )
        ]
        
        report = TestToFeatureCoverageReport(
            entries=entries,
            total_features=1,
            total_tests=1,
            features_without_tests=0
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
        
        try:
            export_to_csv(report, temp_file)
            
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "Feature" in content
                assert "Login" in content
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_export_change_impact_to_csv(self):
        """Test exporting change impact surface to CSV."""
        entries = [
            ChangeImpactSurfaceEntry(
                impacted_test="LoginTest",
                feature="Login",
                testrail_tc="C12345",
                coverage_percentage=85.5
            )
        ]
        
        report = ChangeImpactSurfaceReport(
            changed_file="LoginService.java",
            entries=entries,
            total_impacted_tests=1,
            total_impacted_features=1
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
        
        try:
            export_to_csv(report, temp_file)
            
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "Impacted Test" in content
                assert "LoginTest" in content
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_export_to_json(self):
        """Test exporting report to JSON."""
        entries = [
            FunctionalCoverageMapEntry(
                code_unit="LoginService",
                test_count=14,
                testrail_tcs=["C12345"]
            )
        ]
        
        report = FunctionalCoverageMapReport(
            entries=entries,
            total_code_units=1,
            total_tests=14,
            total_external_tcs=1
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            export_to_json(report, temp_file)
            
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                data = json.load(f)
                assert 'entries' in data
                assert data['total_code_units'] == 1
                assert data['total_tests'] == 14
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_report(self, capsys):
        """Test printing empty report."""
        report = FunctionalCoverageMapReport(
            entries=[],
            total_code_units=0,
            total_tests=0,
            total_external_tcs=0
        )
        
        print_functional_coverage_map(report)
        
        captured = capsys.readouterr()
        assert "No coverage data found" in captured.out
    
    def test_entry_without_external_tcs(self):
        """Test entry without external test cases."""
        entry = FunctionalCoverageMapEntry(
            code_unit="Test",
            test_count=5,
            testrail_tcs=[]
        )
        
        row = entry.to_row()
        assert row[2] == "-"  # Should show dash when no TCs
    
    def test_entry_without_feature(self):
        """Test change impact entry without feature."""
        entry = ChangeImpactSurfaceEntry(
            impacted_test="Test",
            feature=None,
            testrail_tc=None
        )
        
        row = entry.to_row()
        assert row[1] == "-"  # Should show dash for missing feature
        assert row[2] == "-"  # Should show dash for missing TC
