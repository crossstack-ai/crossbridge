"""
Unit tests for Istanbul/NYC parser.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from core.coverage.istanbul_parser import (
    IstanbulParser,
    IstanbulReportLocator,
    extract_coverage_from_jest
)
from core.coverage.models import CoverageSource, ExecutionMode


class TestIstanbulParser:
    """Tests for IstanbulParser class."""
    
    def test_parse_single_test(self):
        """Test parsing Istanbul coverage for a single test."""
        # Create sample Istanbul report
        coverage_data = {
            "src/services/auth.js": {
                "statementMap": {
                    "0": {"start": {"line": 1}, "end": {"line": 1}},
                    "1": {"start": {"line": 2}, "end": {"line": 2}}
                },
                "fnMap": {
                    "0": {"name": "login", "line": 5}
                },
                "branchMap": {},
                "s": {"0": 5, "1": 3},
                "f": {"0": 2},
                "b": {}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = IstanbulParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_login"
            )
            
            assert mapping is not None
            assert mapping.test_name == "test_login"
            assert mapping.coverage_source == CoverageSource.ISTANBUL
            assert len(mapping.covered_code_units) == 1
            
            unit = mapping.covered_code_units[0]
            assert unit.class_name == "services.auth"
            assert unit.method_name == "login"
            assert unit.file_path == "src/services/auth.js"
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_multiple_functions(self):
        """Test parsing coverage with multiple functions."""
        coverage_data = {
            "src/utils/helpers.ts": {
                "statementMap": {
                    "0": {"start": {"line": 1}, "end": {"line": 1}}
                },
                "fnMap": {
                    "0": {"name": "formatDate", "line": 5},
                    "1": {"name": "parseDate", "line": 10},
                    "2": {"name": "validateDate", "line": 15}
                },
                "branchMap": {},
                "s": {"0": 10},
                "f": {"0": 5, "1": 3, "2": 2},
                "b": {}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = IstanbulParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_date_utils"
            )
            
            assert mapping is not None
            assert len(mapping.covered_code_units) == 3
            
            # Check function names
            function_names = [u.method_name for u in mapping.covered_code_units]
            assert "formatDate" in function_names
            assert "parseDate" in function_names
            assert "validateDate" in function_names
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_with_branches(self):
        """Test parsing coverage with branch information."""
        coverage_data = {
            "src/validator.js": {
                "statementMap": {
                    "0": {"start": {"line": 1}, "end": {"line": 1}}
                },
                "fnMap": {
                    "0": {"name": "validate", "line": 5}
                },
                "branchMap": {
                    "0": {"line": 10, "locations": [{"start": {"line": 10}}, {"start": {"line": 12}}]}
                },
                "s": {"0": 5},
                "f": {"0": 5},
                "b": {"0": [3, 2]}  # 3 times took first branch, 2 times second
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = IstanbulParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_validation"
            )
            
            assert mapping is not None
            unit = mapping.covered_code_units[0]
            assert unit.method_name == "validate"
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_batch(self):
        """Test batch parsing for multiple tests."""
        coverage_data = {
            "src/auth.js": {
                "statementMap": {"0": {"start": {"line": 1}, "end": {"line": 1}}},
                "fnMap": {"0": {"name": "login", "line": 5}},
                "branchMap": {},
                "s": {"0": 5},
                "f": {"0": 2},
                "b": {}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = IstanbulParser()
            test_names = ["test_login", "test_logout"]
            mappings = parser.parse_batch(
                json_path=Path(temp_file),
                test_names=test_names
            )
            
            assert len(mappings) == 2
            assert all(name in mappings for name in test_names)
            
            # Check lower confidence for batch
            for mapping in mappings.values():
                assert mapping.confidence == 0.5
                
        finally:
            os.unlink(temp_file)
    
    def test_path_to_module_conversion(self):
        """Test file path to module name conversion."""
        parser = IstanbulParser()
        
        assert parser._path_to_module("src/app/services/auth.js") == "services.auth"  # src/ and app/ removed
        assert parser._path_to_module("lib/utils/helpers.ts") == "utils.helpers"  # lib/ removed
        assert parser._path_to_module("dist/bundle.mjs") == "bundle"  # dist/ removed
        assert parser._path_to_module("./app/main.cjs") == "main"  # ./ and app/ removed
    
    def test_parse_file_level_coverage(self):
        """Test parsing when no functions are covered but statements are."""
        coverage_data = {
            "src/config.js": {
                "statementMap": {
                    "0": {"start": {"line": 1}, "end": {"line": 1}},
                    "1": {"start": {"line": 2}, "end": {"line": 2}}
                },
                "fnMap": {},  # No functions
                "branchMap": {},
                "s": {"0": 1, "1": 1},
                "f": {},
                "b": {}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = IstanbulParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_config"
            )
            
            assert mapping is not None
            assert len(mapping.covered_code_units) == 1
            
            unit = mapping.covered_code_units[0]
            assert unit.method_name is None  # File-level coverage
            assert unit.line_coverage == 100.0
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_empty_coverage(self):
        """Test parsing empty coverage report."""
        coverage_data = {}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coverage_data, f)
            temp_file = f.name
        
        try:
            parser = IstanbulParser()
            mapping = parser.parse(
                json_path=Path(temp_file),
                test_name="test_empty"
            )
            
            assert mapping is None
            
        finally:
            os.unlink(temp_file)


class TestIstanbulReportLocator:
    """Tests for IstanbulReportLocator class."""
    
    def test_find_report_in_coverage_dir(self):
        """Test finding coverage-final.json in coverage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            coverage_dir = temp_path / "coverage"
            coverage_dir.mkdir()
            report_file = coverage_dir / "coverage-final.json"
            report_file.write_text("{}")
            
            locator = IstanbulReportLocator()
            found = locator.find_report(temp_path)
            
            assert found is not None
            assert found == report_file
    
    def test_find_report_in_nyc_output(self):
        """Test finding report in .nyc_output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nyc_dir = temp_path / ".nyc_output"
            nyc_dir.mkdir()
            report_file = nyc_dir / "coverage.json"
            report_file.write_text("{}")
            
            locator = IstanbulReportLocator()
            found = locator.find_report(temp_path)
            
            assert found is not None
            assert found == report_file
    
    def test_find_report_not_found(self):
        """Test when no report is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            locator = IstanbulReportLocator()
            found = locator.find_report(temp_path)
            
            assert found is None


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_extract_coverage_from_jest(self):
        """Test extract_coverage_from_jest helper."""
        coverage_data = {
            "src/app.js": {
                "statementMap": {"0": {"start": {"line": 1}, "end": {"line": 1}}},
                "fnMap": {"0": {"name": "main", "line": 5}},
                "branchMap": {},
                "s": {"0": 1},
                "f": {"0": 1},
                "b": {}
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            coverage_dir = temp_path / "coverage"
            coverage_dir.mkdir()
            report_file = coverage_dir / "coverage-final.json"
            report_file.write_text(json.dumps(coverage_data))
            
            mapping = extract_coverage_from_jest(
                working_dir=temp_path,
                test_name="test_app"
            )
            
            assert mapping is not None
            assert mapping.test_name == "test_app"
            assert mapping.execution_mode == ExecutionMode.ISOLATED
    
    def test_extract_coverage_no_report(self):
        """Test when coverage report doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            mapping = extract_coverage_from_jest(
                working_dir=temp_path,
                test_name="test_missing"
            )
            
            assert mapping is None
