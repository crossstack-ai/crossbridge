"""
Python Coverage.py Parser for CrossBridge.

Parses coverage.py JSON reports to extract test-to-code mappings.
Supports pytest and other Python test frameworks.

Usage:
    parser = CoveragePyParser()
    mapping = parser.parse(json_path="coverage.json", test_name="test_login")
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Set
from dataclasses import dataclass

from core.logging import get_logger, LogCategory
from core.coverage.models import (
    CoveredCodeUnit,
    TestCoverageMapping,
    CoverageSource,
    ExecutionMode
)


@dataclass
class CoveragePyReport:
    """Represents a coverage.py JSON report structure."""
    files: Dict[str, 'FileCoverage']
    totals: Dict[str, float]
    
    @dataclass
    class FileCoverage:
        """Coverage for a single file."""
        executed_lines: List[int]
        missing_lines: List[int]
        excluded_lines: List[int]
        summary: Dict[str, int]


logger = get_logger(__name__, category=LogCategory.TESTING)


class CoveragePyParser:
    """
    Parser for coverage.py JSON reports.
    
    Converts coverage.py output into CrossBridge TestCoverageMapping.
    """
    
    def __init__(self):
        self.report_locator = CoveragePyReportLocator()
    
    def parse(
        self,
        json_path: Path,
        test_name: str,
        execution_mode: ExecutionMode = ExecutionMode.ISOLATED
    ) -> Optional[TestCoverageMapping]:
        """
        Parse coverage.py JSON report for a single test.
        
        Args:
            json_path: Path to coverage.json
            test_name: Name of the test (e.g., test_login)
            execution_mode: How coverage was collected
            
        Returns:
            TestCoverageMapping or None if parsing fails
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            covered_units = self._extract_covered_units(data)
            
            if not covered_units:
                return None
            
            return TestCoverageMapping(
                test_id=test_name,
                test_name=test_name,
                covered_code_units=covered_units,
                coverage_source=CoverageSource.COVERAGE_PY,
                execution_mode=execution_mode
            )
            
        except Exception as e:
            print(f"Error parsing coverage.py report: {e}")
            return None
    
    def parse_batch(
        self,
        json_path: Path,
        test_names: List[str],
        execution_mode: ExecutionMode = ExecutionMode.SMALL_BATCH
    ) -> Dict[str, TestCoverageMapping]:
        """
        Parse coverage.py report for multiple tests.
        
        Note: coverage.py aggregates coverage, so this has lower confidence
        than isolated execution. Use when performance matters more than precision.
        
        Args:
            json_path: Path to coverage.json
            test_names: List of test names
            execution_mode: How coverage was collected
            
        Returns:
            Dict mapping test_name -> TestCoverageMapping
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            covered_units = self._extract_covered_units(data)
            
            # Distribute coverage to all tests (approximation)
            mappings = {}
            for test_name in test_names:
                mappings[test_name] = TestCoverageMapping(
                    test_id=test_name,
                    test_name=test_name,
                    covered_code_units=covered_units,
                    coverage_source=CoverageSource.COVERAGE_PY,
                    execution_mode=execution_mode,
                    confidence=0.5  # Lower confidence for batch
                )
            
            return mappings
            
        except Exception as e:
            print(f"Error parsing coverage.py batch report: {e}")
            return {}
    
    def _extract_covered_units(self, data: Dict) -> List[CoveredCodeUnit]:
        """
        Extract covered code units from coverage.py JSON.
        
        Args:
            data: Parsed coverage.py JSON
            
        Returns:
            List of CoveredCodeUnit objects
        """
        units = []
        
        # coverage.py JSON structure:
        # {
        #   "files": {
        #     "path/to/file.py": {
        #       "executed_lines": [1, 2, 5, 10],
        #       "missing_lines": [3, 4],
        #       "summary": {
        #         "covered_lines": 4,
        #         "num_statements": 6,
        #         "percent_covered": 66.67,
        #         ...
        #       }
        #     }
        #   }
        # }
        
        files = data.get('files', {})
        
        for file_path, file_coverage in files.items():
            # Extract module/class name from file path
            module_name = self._path_to_module(file_path)
            
            executed_lines = file_coverage.get('executed_lines', [])
            summary = file_coverage.get('summary', {})
            
            covered_lines = summary.get('covered_lines', 0)
            total_lines = summary.get('num_statements', 0)
            
            line_coverage_pct = 0.0
            if total_lines > 0:
                line_coverage_pct = (covered_lines / total_lines) * 100
            
            # Create one unit per file (coverage.py doesn't break down by function)
            unit = CoveredCodeUnit(
                class_name=module_name,
                method_name=None,  # coverage.py doesn't track function-level
                file_path=file_path,
                line_numbers=executed_lines,
                line_coverage=line_coverage_pct
            )
            
            units.append(unit)
        
        return units
    
    def _path_to_module(self, file_path: str) -> str:
        """
        Convert file path to Python module name.
        
        Examples:
            src/app/services/auth.py -> app.services.auth
            tests/test_login.py -> tests.test_login
        """
        # Remove .py extension
        module = file_path.replace('.py', '')
        
        # Remove common prefixes
        for prefix in ['src/', 'app/', './']:
            if module.startswith(prefix):
                module = module[len(prefix):]
        
        # Convert slashes to dots
        module = module.replace('/', '.').replace('\\', '.')
        
        return module


class CoveragePyReportLocator:
    """
    Locates coverage.py reports in a project.
    
    Searches common locations:
    - coverage.json
    - .coverage (SQLite format - not supported yet)
    - htmlcov/coverage.json
    """
    
    def find_report(self, working_dir: Path) -> Optional[Path]:
        """
        Find coverage.py JSON report.
        
        Args:
            working_dir: Project directory
            
        Returns:
            Path to coverage.json or None
        """
        candidates = [
            working_dir / 'coverage.json',
            working_dir / '.coverage.json',
            working_dir / 'htmlcov' / 'coverage.json',
            working_dir / 'reports' / 'coverage.json',
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        return None


# ========================================
# Convenience Functions
# ========================================

def extract_coverage_from_pytest(
    working_dir: Path,
    test_name: str
) -> Optional[TestCoverageMapping]:
    """
    Quick helper to extract coverage from pytest run.
    
    Assumes coverage.json exists in working_dir.
    
    Args:
        working_dir: Directory with coverage.json
        test_name: Name of the test
        
    Returns:
        TestCoverageMapping or None
    """
    parser = CoveragePyParser()
    locator = CoveragePyReportLocator()
    
    json_path = locator.find_report(working_dir)
    if not json_path:
        return None
    
    return parser.parse(
        json_path=json_path,
        test_name=test_name,
        execution_mode=ExecutionMode.ISOLATED
    )
