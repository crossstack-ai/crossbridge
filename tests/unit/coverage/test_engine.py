"""
Unit tests for coverage mapping engine.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from core.coverage.engine import CoverageMappingEngine
from core.coverage.models import (
    TestCoverageMapping,
    CoveredCodeUnit,
    CoverageType,
    CoverageSource,
    ExecutionMode
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    return tmp_path / "test_engine.db"


@pytest.fixture
def engine(test_db):
    """Create a coverage mapping engine."""
    return CoverageMappingEngine(test_db)


@pytest.fixture
def sample_jacoco_xml(tmp_path):
    """Create a sample JaCoCo XML."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<report name="Test Coverage">
    <package name="com/example">
        <class name="com/example/TestClass">
            <method name="testMethod" desc="()V">
                <counter type="LINE" missed="0" covered="10"/>
            </method>
            <counter type="LINE" missed="0" covered="10"/>
        </class>
    </package>
</report>
"""
    
    # Create Maven structure
    report_dir = tmp_path / "target" / "site" / "jacoco"
    report_dir.mkdir(parents=True)
    xml_file = report_dir / "jacoco.xml"
    xml_file.write_text(xml_content)
    
    return xml_file


class TestCoverageMappingEngine:
    """Tests for CoverageMappingEngine."""
    
    def test_create_engine(self, test_db):
        """Test creating an engine."""
        engine = CoverageMappingEngine(test_db)
        assert engine is not None
        assert engine.repository is not None
        assert engine.jacoco_parser is not None
    
    @patch('core.coverage.engine.subprocess.run')
    def test_collect_coverage_isolated_success(self, mock_run, engine, tmp_path, sample_jacoco_xml):
        """Test collecting isolated coverage successfully."""
        # Mock successful test execution
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        mapping = engine.collect_coverage_isolated(
            test_id="TestClass.testMethod",
            test_command="mvn test -Dtest=TestClass#testMethod",
            working_dir=sample_jacoco_xml.parent.parent.parent.parent,
            test_framework="junit",
            timeout=300
        )
        
        assert mapping is not None
        assert mapping.test_id == "TestClass.testMethod"
        assert mapping.execution_mode == ExecutionMode.ISOLATED
        assert mapping.confidence >= 0.80  # Isolated execution should have high confidence
    
    @patch('core.coverage.engine.subprocess.run')
    def test_collect_coverage_isolated_failure(self, mock_run, engine, tmp_path):
        """Test collecting coverage when test fails."""
        # Mock failed test execution
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Test failed")
        
        mapping = engine.collect_coverage_isolated(
            test_id="TestClass.testMethod",
            test_command="mvn test -Dtest=TestClass#testMethod",
            working_dir=tmp_path,
            test_framework="junit"
        )
        
        assert mapping is None
    
    @patch('core.coverage.engine.subprocess.run')
    def test_collect_coverage_batch(self, mock_run, engine, tmp_path, sample_jacoco_xml):
        """Test collecting batch coverage."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        test_ids = ["Test1.test1", "Test2.test2", "Test3.test3"]
        
        mappings = engine.collect_coverage_batch(
            test_ids=test_ids,
            test_command="mvn test",
            working_dir=sample_jacoco_xml.parent.parent.parent.parent,
            test_framework="junit"
        )
        
        assert len(mappings) == 3
        
        for mapping in mappings:
            assert mapping.execution_mode == ExecutionMode.SMALL_BATCH
            assert mapping.confidence < 0.90  # Batch confidence lower than isolated
    
    @patch('core.coverage.engine.subprocess.run')
    def test_collect_coverage_timeout(self, mock_run, engine, tmp_path):
        """Test that timeout is handled."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("mvn test", 10)
        
        mapping = engine.collect_coverage_isolated(
            test_id="TestClass.testMethod",
            test_command="mvn test",
            working_dir=tmp_path,
            timeout=10
        )
        
        assert mapping is None
    
    def test_query_impact(self, engine):
        """Test querying impact."""
        # Add some test coverage
        mapping = TestCoverageMapping(
            test_id="LoginTest.test1",
            test_name="test1",
            test_framework="junit",
            covered_classes={"com.example.LoginService"},
            covered_methods={"com.example.LoginService.authenticate"},
            covered_code_units=[
                CoveredCodeUnit(
                    class_name="com.example.LoginService",
                    method_name="authenticate",
                    line_coverage=0.85
                )
            ],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED,
            confidence=0.92
        )
        
        engine.repository.save_test_coverage(mapping, "run-001")
        
        # Query impact
        impact = engine.query_impact(
            changed_classes={"com.example.LoginService"},
            min_confidence=0.8
        )
        
        assert len(impact.affected_tests) == 1
        assert "LoginTest.test1" in impact.affected_tests
    
    def test_query_impact_multiple_classes(self, engine):
        """Test impact query with multiple changed classes."""
        # Add test covering multiple classes
        mapping1 = TestCoverageMapping(
            test_id="Test1",
            test_name="test1",
            test_framework="junit",
            covered_classes={"com.example.ClassA"},
            covered_methods=set(),
            covered_code_units=[
                CoveredCodeUnit(
                    class_name="com.example.ClassA",
                    line_coverage=0.85
                )
            ],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED,
            confidence=0.9
        )
        
        mapping2 = TestCoverageMapping(
            test_id="Test2",
            test_name="test2",
            test_framework="junit",
            covered_classes={"com.example.ClassB"},
            covered_methods=set(),
            covered_code_units=[
                CoveredCodeUnit(
                    class_name="com.example.ClassB",
                    line_coverage=0.80
                )
            ],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED,
            confidence=0.85
        )
        
        engine.repository.save_test_coverage(mapping1, "run-001")
        engine.repository.save_test_coverage(mapping2, "run-001")
        
        # Query impact for both classes
        impact = engine.query_impact(
            changed_classes={"com.example.ClassA", "com.example.ClassB"}
        )
        
        assert len(impact.affected_tests) == 2
    
    def test_get_test_coverage(self, engine):
        """Test getting coverage for a test."""
        # Save coverage
        mapping = TestCoverageMapping(
            test_id="TestClass.test1",
            test_name="test1",
            test_framework="junit",
            covered_classes={"com.example.Service"},
            covered_methods={"com.example.Service.method"},
            covered_code_units=[
                CoveredCodeUnit(
                    class_name="com.example.Service",
                    method_name="method",
                    line_coverage=0.9
                )
            ],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED,
            confidence=0.9
        )
        
        engine.repository.save_test_coverage(mapping, "run-001")
        
        # Get coverage
        retrieved = engine.get_test_coverage("TestClass.test1")
        
        assert retrieved is not None
        assert retrieved.test_id == "TestClass.test1"
        assert "com.example.Service" in retrieved.covered_classes
    
    def test_get_test_coverage_not_found(self, engine):
        """Test getting coverage for nonexistent test."""
        coverage = engine.get_test_coverage("NonexistentTest")
        assert coverage is None
    
    def test_get_statistics(self, engine):
        """Test getting coverage statistics."""
        # Add some coverage
        mapping = TestCoverageMapping(
            test_id="Test1",
            test_name="test1",
            test_framework="junit",
            covered_classes={"com.example.Class1", "com.example.Class2"},
            covered_methods={"com.example.Class1.method1", "com.example.Class2.method2"},
            covered_code_units=[
                CoveredCodeUnit(
                    class_name="com.example.Class1",
                    method_name="method1",
                    line_coverage=0.85
                ),
                CoveredCodeUnit(
                    class_name="com.example.Class2",
                    method_name="method2",
                    line_coverage=0.90
                )
            ],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED,
            confidence=0.9
        )
        
        engine.repository.save_test_coverage(mapping, "run-001")
        
        stats = engine.get_statistics()
        
        assert stats['total_tests'] == 1
        assert stats['total_classes'] == 2
        assert stats['total_methods'] == 2
        assert stats['average_confidence'] == 0.9
    
    @patch('core.coverage.engine.subprocess.run')
    def test_report_locator_integration(self, mock_run, engine, tmp_path):
        """Test that report locator finds JaCoCo report."""
        # Create Maven structure
        report_dir = tmp_path / "target" / "site" / "jacoco"
        report_dir.mkdir(parents=True)
        xml_file = report_dir / "jacoco.xml"
        xml_file.write_text("<report></report>")
        
        mock_run.return_value = Mock(returncode=0)
        
        # Find report
        found = engine.report_locator.find_report(tmp_path)
        
        assert found is not None
        assert found == xml_file


class TestEngineIntegration:
    """Integration tests for coverage engine."""
    
    def test_end_to_end_coverage_collection(self, tmp_path):
        """Test end-to-end coverage collection flow."""
        # Create database
        db_path = tmp_path / "coverage.db"
        engine = CoverageMappingEngine(db_path)
        
        # Create fake JaCoCo report
        report_dir = tmp_path / "target" / "site" / "jacoco"
        report_dir.mkdir(parents=True)
        xml_file = report_dir / "jacoco.xml"
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<report name="Coverage">
    <package name="com/example">
        <class name="com/example/LoginService" sourcefilename="LoginService.java">
            <method name="authenticate" desc="()V" line="15">
                <counter type="INSTRUCTION" missed="0" covered="20"/>
                <counter type="LINE" missed="0" covered="20"/>
            </method>
            <counter type="INSTRUCTION" missed="0" covered="20"/>
            <counter type="LINE" missed="0" covered="20"/>
            <counter type="METHOD" missed="0" covered="1"/>
        </class>
    </package>
    <counter type="INSTRUCTION" missed="0" covered="20"/>
    <counter type="LINE" missed="0" covered="20"/>
    <counter type="METHOD" missed="0" covered="1"/>
    <counter type="CLASS" missed="0" covered="1"/>
</report>
"""
        xml_file.write_text(xml_content)
        
        # Mock subprocess to skip actual test execution
        with patch('core.coverage.engine.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            # Collect coverage
            mapping = engine.collect_coverage_isolated(
                test_id="LoginTest.test1",
                test_command="mvn test",
                working_dir=tmp_path,
                test_framework="junit"
            )
        
        # Verify mapping was created and saved
        assert mapping is not None
        
        # Query impact
        impact = engine.query_impact({"com.example.LoginService"})
        assert len(impact.affected_tests) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
