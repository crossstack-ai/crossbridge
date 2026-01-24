"""
Unit tests for coverage.py parser.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from core.coverage.coverage_py_parser import (
    CoveragePyParser,
    CoveragePyReportLocator,
    extract_coverage_from_pytest
)
from core.coverage.models import CoverageSource, ExecutionMode


class TestCoveragePyParser:
    """Tests for CoveragePyParser class."""
    
    def test_parse_single_test(self):
        """Test parsing coverage.py JSON for a single test."""
        # Create sample coverage.json
        coverage_data = {
            "files": {
                "src/app/services/auth.py": {
                    "executed_lines": [1, 2, 5, 10, 15],
                    "missing_lines": [3, 4],
                    "excluded_lines": [],
                    "summary": {
                        "covered_lines": 5,
                        "num_statements": 7,
                        "percent_covered": 71.43
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = CoveragePyParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_login"
            )
            
            assert mapping is not None
            assert mapping.test_name == "test_login"
            assert mapping.coverage_source == CoverageSource.COVERAGE_PY
            assert len(mapping.covered_code_units) == 1
            
            unit = mapping.covered_code_units[0]
            assert unit.class_name == "services.auth"  # app/ prefix removed
            assert unit.file_path == "src/app/services/auth.py"
            assert len(unit.line_numbers) == 5
            assert unit.line_coverage > 0
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_multiple_files(self):
        """Test parsing coverage with multiple files."""
        coverage_data = {
            "files": {
                "app/services/user.py": {
                    "executed_lines": [1, 2, 3],
                    "missing_lines": [],
                    "summary": {
                        "covered_lines": 3,
                        "num_statements": 3,
                        "percent_covered": 100.0
                    }
                },
                "app/models/order.py": {
                    "executed_lines": [5, 10],
                    "missing_lines": [15],
                    "summary": {
                        "covered_lines": 2,
                        "num_statements": 3,
                        "percent_covered": 66.67
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = CoveragePyParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_checkout"
            )
            
            assert mapping is not None
            assert len(mapping.covered_code_units) == 2
            
            # Check module names
            module_names = [u.class_name for u in mapping.covered_code_units]
            assert "services.user" in module_names  # app/ prefix removed
            assert "models.order" in module_names  # app/ prefix removed
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_batch(self):
        """Test batch parsing for multiple tests."""
        coverage_data = {
            "files": {
                "app/auth.py": {
                    "executed_lines": [1, 2, 3],
                    "missing_lines": [],
                    "summary": {
                        "covered_lines": 3,
                        "num_statements": 3,
                        "percent_covered": 100.0
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = CoveragePyParser()
            test_names = ["test_login", "test_logout", "test_register"]
            mappings = parser.parse_batch(
                json_path=Path(temp_file),
                test_names=test_names
            )
            
            assert len(mappings) == 3
            assert all(name in mappings for name in test_names)
            
            # All tests should have same coverage (approximation)
            for name, mapping in mappings.items():
                assert mapping.test_name == name
                assert mapping.confidence == 0.5  # Lower confidence for batch
                
        finally:
            os.unlink(temp_file)
    
    def test_path_to_module_conversion(self):
        """Test file path to module name conversion."""
        parser = CoveragePyParser()
        
        assert parser._path_to_module("src/app/services/auth.py") == "services.auth"
        assert parser._path_to_module("app/models/user.py") == "models.user"
        assert parser._path_to_module("tests/test_login.py") == "tests.test_login"
        assert parser._path_to_module("./lib/utils.py") == "lib.utils"  # ./ removed, lib kept
    
    def test_parse_empty_coverage(self):
        """Test parsing empty coverage report."""
        coverage_data = {"files": {}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = CoveragePyParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_empty"
            )
            
            assert mapping is None
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_invalid_json(self):
        """Test handling of invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json{")
            temp_file = f.name
        
        try:
            parser = CoveragePyParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_invalid"
            )
            
            assert mapping is None
            
        finally:
            os.unlink(temp_file)


class TestCoveragePyReportLocator:
    """Tests for CoveragePyReportLocator class."""
    
    def test_find_report_in_root(self):
        """Test finding coverage.json in project root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            report_file = temp_path / "coverage.json"
            report_file.write_text("{}")
            
            locator = CoveragePyReportLocator()
            found = locator.find_report(temp_path)
            
            assert found is not None
            assert found == report_file
    
    def test_find_report_in_htmlcov(self):
        """Test finding coverage.json in htmlcov directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            htmlcov_dir = temp_path / "htmlcov"
            htmlcov_dir.mkdir()
            report_file = htmlcov_dir / "coverage.json"
            report_file.write_text("{}")
            
            locator = CoveragePyReportLocator()
            found = locator.find_report(temp_path)
            
            assert found is not None
            assert found == report_file
    
    def test_find_report_not_found(self):
        """Test when no report is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            locator = CoveragePyReportLocator()
            found = locator.find_report(temp_path)
            
            assert found is None


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_extract_coverage_from_pytest(self):
        """Test extract_coverage_from_pytest helper."""
        coverage_data = {
            "files": {
                "app/main.py": {
                    "executed_lines": [1, 2],
                    "missing_lines": [],
                    "summary": {
                        "covered_lines": 2,
                        "num_statements": 2,
                        "percent_covered": 100.0
                    }
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            report_file = temp_path / "coverage.json"
            report_file.write_text(json.dumps(coverage_data))
            
            mapping = extract_coverage_from_pytest(
                working_dir=temp_path,
                test_name="test_main"
            )
            
            assert mapping is not None
            assert mapping.test_name == "test_main"
            assert mapping.execution_mode == ExecutionMode.ISOLATED
    
    def test_extract_coverage_no_report(self):
        """Test when coverage report doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            mapping = extract_coverage_from_pytest(
                working_dir=temp_path,
                test_name="test_missing"
            )
            
            assert mapping is None
