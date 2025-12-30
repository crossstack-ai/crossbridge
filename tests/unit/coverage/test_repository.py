"""
Unit tests for coverage repository.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime

from core.coverage.repository import CoverageRepository
from core.coverage.models import (
    TestCoverageMapping,
    ScenarioCoverageMapping,
    CoveredCodeUnit,
    CoverageType,
    CoverageSource,
    ExecutionMode
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test_coverage.db"
    return db_path


@pytest.fixture
def repository(test_db):
    """Create a coverage repository."""
    return CoverageRepository(test_db)


@pytest.fixture
def sample_test_mapping():
    """Create a sample test coverage mapping."""
    units = [
        CoveredCodeUnit(
            class_name="com.example.LoginService",
            method_name="authenticate",
            file_path="com/example/LoginService.java",
            line_numbers=[10, 11, 12, 15, 16],
            line_coverage=0.8,
            instruction_coverage=0.85
        ),
        CoveredCodeUnit(
            class_name="com.example.UserService",
            method_name="getUser",
            file_path="com/example/UserService.java",
            line_coverage=0.833
        )
    ]
    
    mapping = TestCoverageMapping(
        test_id="LoginTest.testSuccess",
        test_name="testSuccess",
        test_framework="junit",
        covered_classes={"com.example.LoginService", "com.example.UserService"},
        covered_methods={"com.example.LoginService.authenticate", "com.example.UserService.getUser"},
        covered_code_units=units,
        coverage_source=CoverageSource.JACOCO,
        execution_mode=ExecutionMode.ISOLATED,
        confidence=0.92
    )
    return mapping


class TestCoverageRepository:
    """Tests for CoverageRepository."""
    
    def test_create_repository(self, test_db):
        """Test creating a repository."""
        repo = CoverageRepository(test_db)
        assert repo is not None
        assert test_db.exists()
    
    def test_schema_creation(self, repository):
        """Test that schema is created."""
        # Check that tables exist
        with sqlite3.connect(repository.db_path) as conn:
            cursor = conn.cursor()
            
            # Check test_code_coverage table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='test_code_coverage'
            """)
            assert cursor.fetchone() is not None
            
            # Check scenario_code_coverage table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='scenario_code_coverage'
            """)
            assert cursor.fetchone() is not None
    
    def test_save_test_coverage(self, repository, sample_test_mapping):
        """Test saving test coverage mapping."""
        rows = repository.save_test_coverage(sample_test_mapping, "run-001")
        
        assert rows > 0
        assert rows == len(sample_test_mapping.covered_code_units)
    
    def test_get_tests_covering_class(self, repository, sample_test_mapping):
        """Test querying tests covering a class."""
        # Save mapping
        repository.save_test_coverage(sample_test_mapping, "run-001")
        
        # Query
        tests = repository.get_tests_covering_class("com.example.LoginService")
        
        assert len(tests) == 1
        assert tests[0]['test_id'] == "LoginTest.testSuccess"
        assert tests[0]['confidence'] == 0.92
    
    def test_get_tests_covering_method(self, repository, sample_test_mapping):
        """Test querying tests covering a specific method."""
        repository.save_test_coverage(sample_test_mapping, "run-001")
        
        tests = repository.get_tests_covering_method(
            "com.example.LoginService",
            "authenticate"
        )
        
        assert len(tests) == 1
        assert tests[0]['test_id'] == "LoginTest.testSuccess"
    
    def test_get_coverage_for_test(self, repository, sample_test_mapping):
        """Test getting coverage for a specific test."""
        repository.save_test_coverage(sample_test_mapping, "run-001")
        
        coverage = repository.get_coverage_for_test("LoginTest.testSuccess")
        
        assert len(coverage) == 2
        
        # Check first record
        assert coverage[0]['class_name'] in ["com.example.LoginService", "com.example.UserService"]
        assert coverage[0]['confidence'] == 0.92
    
    def test_get_impact_for_changed_classes(self, repository, sample_test_mapping):
        """Test impact analysis query."""
        repository.save_test_coverage(sample_test_mapping, "run-001")
        
        changed_classes = {"com.example.LoginService"}
        impact = repository.get_impact_for_changed_classes(changed_classes)
        
        assert len(impact) == 1
        assert impact[0]['test_id'] == "LoginTest.testSuccess"
        assert impact[0]['class_name'] == "com.example.LoginService"
    
    def test_impact_multiple_classes(self, repository, sample_test_mapping):
        """Test impact with multiple changed classes."""
        repository.save_test_coverage(sample_test_mapping, "run-001")
        
        changed_classes = {"com.example.LoginService", "com.example.UserService"}
        impact = repository.get_impact_for_changed_classes(changed_classes)
        
        assert len(impact) == 2
    
    def test_min_confidence_filter(self, repository, sample_test_mapping):
        """Test that min_confidence filters results."""
        repository.save_test_coverage(sample_test_mapping, "run-001")
        
        # Should return result with confidence 0.92
        tests = repository.get_tests_covering_class("com.example.LoginService", min_confidence=0.8)
        assert len(tests) == 1
        
        # Should not return result with min_confidence higher than 0.92
        tests = repository.get_tests_covering_class("com.example.LoginService", min_confidence=0.95)
        assert len(tests) == 0
    
    def test_create_discovery_run(self, repository):
        """Test creating a discovery run."""
        run_id = repository.create_discovery_run(
            run_type="isolated",
            test_framework="junit",
            coverage_source=CoverageSource.JACOCO,
            commit_hash="abc123"
        )
        
        assert run_id is not None
        assert len(run_id) > 0
        
        # Verify it's in database
        with sqlite3.connect(repository.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM coverage_discovery_run WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            assert row is not None
    
    def test_complete_discovery_run(self, repository):
        """Test completing a discovery run."""
        run_id = repository.create_discovery_run(
            run_type="batch",
            test_framework="junit",
            coverage_source=CoverageSource.JACOCO
        )
        
        repository.complete_discovery_run(
            run_id=run_id,
            test_count=10,
            classes_covered=50,
            methods_covered=200,
            duration_seconds=45.5
        )
        
        # Verify status is completed
        with sqlite3.connect(repository.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, test_count FROM coverage_discovery_run WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            assert row[0] == 'completed'
            assert row[1] == 10
    
    def test_fail_discovery_run(self, repository):
        """Test marking discovery run as failed."""
        run_id = repository.create_discovery_run(
            run_type="isolated",
            test_framework="junit",
            coverage_source=CoverageSource.JACOCO
        )
        
        repository.fail_discovery_run(run_id, "Test execution failed")
        
        # Verify status is failed
        with sqlite3.connect(repository.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, error_message FROM coverage_discovery_run WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            assert row[0] == 'failed'
            assert row[1] == "Test execution failed"
    
    def test_get_coverage_statistics(self, repository, sample_test_mapping):
        """Test getting coverage statistics."""
        repository.save_test_coverage(sample_test_mapping, "run-001")
        
        stats = repository.get_coverage_statistics()
        
        assert stats['total_tests'] == 1
        assert stats['total_classes'] == 2
        assert stats['total_methods'] == 2
        assert stats['average_confidence'] == 0.92
        assert 'junit' in stats['by_framework']
    
    def test_append_only_constraint(self, repository, sample_test_mapping):
        """Test that duplicate inserts are ignored (append-only)."""
        # Save once
        rows1 = repository.save_test_coverage(sample_test_mapping, "run-001")
        
        # Save again (should be ignored due to unique constraint)
        rows2 = repository.save_test_coverage(sample_test_mapping, "run-001")
        
        assert rows1 > 0
        assert rows2 == 0  # Should be ignored
    
    def test_save_scenario_coverage(self, repository):
        """Test saving scenario coverage."""
        # Create scenario mapping
        scenario = ScenarioCoverageMapping(
            scenario_id="scenario-1",
            scenario_name="Login scenario",
            feature_name="Login",
            feature_file="login.feature",
            step_coverage_mappings=[],
            coverage_source=CoverageSource.JACOCO,
            confidence=0.85
        )
        
        # Add aggregated coverage
        scenario.aggregated_classes = {"com.example.LoginService"}
        scenario.aggregated_methods = {"com.example.LoginService.authenticate"}
        scenario.aggregated_code_units = [
            CoveredCodeUnit(
                class_name="com.example.LoginService",
                method_name="authenticate",
                line_coverage=0.9
            )
        ]
        
        rows = repository.save_scenario_coverage(scenario, "run-001")
        
        assert rows > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
