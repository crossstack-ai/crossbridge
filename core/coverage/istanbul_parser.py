"""
Istanbul/NYC Coverage Parser for CrossBridge.

Parses Istanbul/NYC JSON reports to extract test-to-code mappings.
Supports JavaScript/TypeScript test frameworks (Jest, Mocha, etc.).

Usage:
    parser = IstanbulParser()
    mapping = parser.parse(json_path="coverage/coverage-final.json", test_name="test_login")
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

from core.logging import get_logger, LogCategory
from core.coverage.models import (
    CoveredCodeUnit,
    TestCoverageMapping,
    CoverageSource,
    ExecutionMode
)


@dataclass
class IstanbulFileCoverage:
    """Coverage data for a single file from Istanbul report."""
    path: str
    statement_map: Dict
    fn_map: Dict
    branch_map: Dict
    s: Dict[str, int]  # Statement counts
    f: Dict[str, int]  # Function counts
    b: Dict[str, List[int]]  # Branch counts


logger = get_logger(__name__, category=LogCategory.TESTING)


class IstanbulParser:
    """
    Parser for Istanbul/NYC coverage reports.
    
    Converts Istanbul JSON output into CrossBridge TestCoverageMapping.
    
    Istanbul report format:
    {
      "path/to/file.js": {
        "statementMap": {...},
        "fnMap": {...},
        "branchMap": {...},
        "s": {"1": 5, "2": 3, ...},  # Statement execution counts
        "f": {"1": 2, "2": 1, ...},  # Function execution counts
        "b": {"1": [2, 1], ...}      # Branch execution counts
      }
    }
    """
    
    def __init__(self):
        self.report_locator = IstanbulReportLocator()
    
    def parse(
        self,
        json_path: Path,
        test_name: str,
        execution_mode: ExecutionMode = ExecutionMode.ISOLATED
    ) -> Optional[TestCoverageMapping]:
        """
        Parse Istanbul coverage report for a single test.
        
        Args:
            json_path: Path to coverage JSON (e.g., coverage-final.json)
            test_name: Name of the test
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
                coverage_source=CoverageSource.ISTANBUL,
                execution_mode=execution_mode
            )
            
        except Exception as e:
            print(f"Error parsing Istanbul report: {e}")
            return None
    
    def parse_batch(
        self,
        json_path: Path,
        test_names: List[str],
        execution_mode: ExecutionMode = ExecutionMode.SMALL_BATCH
    ) -> Dict[str, TestCoverageMapping]:
        """
        Parse Istanbul report for multiple tests.
        
        Note: Istanbul aggregates coverage, so this has lower confidence.
        
        Args:
            json_path: Path to coverage JSON
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
                    coverage_source=CoverageSource.ISTANBUL,
                    execution_mode=execution_mode,
                    confidence=0.5  # Lower confidence for batch
                )
            
            return mappings
            
        except Exception as e:
            print(f"Error parsing Istanbul batch report: {e}")
            return {}
    
    def _extract_covered_units(self, data: Dict) -> List[CoveredCodeUnit]:
        """
        Extract covered code units from Istanbul JSON.
        
        Args:
            data: Parsed Istanbul coverage JSON
            
        Returns:
            List of CoveredCodeUnit objects
        """
        units = []
        
        # Iterate over all files in the coverage report
        for file_path, file_coverage in data.items():
            # Skip if not a coverage object (e.g., metadata keys)
            if not isinstance(file_coverage, dict):
                continue
            
            # Extract function coverage
            fn_map = file_coverage.get('fnMap', {})
            f_counts = file_coverage.get('f', {})
            
            for fn_id, fn_data in fn_map.items():
                fn_name = fn_data.get('name', f'anonymous_{fn_id}')
                fn_line = fn_data.get('line', 0)
                executed_count = f_counts.get(fn_id, 0)
                
                if executed_count > 0:
                    # Extract module name from file path
                    module_name = self._path_to_module(file_path)
                    
                    unit = CoveredCodeUnit(
                        class_name=module_name,
                        method_name=fn_name,
                        file_path=file_path,
                        line_numbers=[fn_line]
                    )
                    units.append(unit)
            
            # Calculate file-level coverage metrics
            statements = file_coverage.get('s', {})
            branches = file_coverage.get('b', {})
            
            total_statements = len(statements)
            covered_statements = sum(1 for count in statements.values() if count > 0)
            
            total_branches = sum(len(branch_counts) for branch_counts in branches.values())
            covered_branches = sum(
                sum(1 for count in branch_counts if count > 0)
                for branch_counts in branches.values()
            )
            
            # If no functions were covered, create a file-level unit
            if not fn_map or all(f_counts.get(fn_id, 0) == 0 for fn_id in fn_map):
                if covered_statements > 0:
                    module_name = self._path_to_module(file_path)
                    
                    line_coverage = 0.0
                    if total_statements > 0:
                        line_coverage = (covered_statements / total_statements) * 100
                    
                    branch_coverage = 0.0
                    if total_branches > 0:
                        branch_coverage = (covered_branches / total_branches) * 100
                    
                    unit = CoveredCodeUnit(
                        class_name=module_name,
                        method_name=None,
                        file_path=file_path,
                        line_coverage=line_coverage,
                        branch_coverage=branch_coverage,
                        covered_branches=covered_branches,
                        total_branches=total_branches
                    )
                    units.append(unit)
        
        return units
    
    def _path_to_module(self, file_path: str) -> str:
        """
        Convert file path to module name.
        
        Examples:
            src/app/services/auth.js -> app.services.auth
            lib/utils/helpers.ts -> utils.helpers
        """
        # Remove file extension
        module = file_path
        for ext in ['.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs']:
            if module.endswith(ext):
                module = module[:-len(ext)]
                break
        
        # Remove common prefixes (iteratively until no more matches)
        prefixes = ['src/', 'lib/', 'app/', 'dist/', 'build/', './']
        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                if module.startswith(prefix):
                    module = module[len(prefix):]
                    changed = True
                    break
        
        # Convert slashes to dots
        module = module.replace('/', '.').replace('\\', '.')
        
        return module


class IstanbulReportLocator:
    """
    Locates Istanbul/NYC coverage reports.
    
    Searches common locations:
    - coverage/coverage-final.json
    - coverage/coverage.json
    - .nyc_output/coverage.json
    """
    
    def find_report(self, working_dir: Path) -> Optional[Path]:
        """
        Find Istanbul coverage JSON report.
        
        Args:
            working_dir: Project directory
            
        Returns:
            Path to coverage JSON or None
        """
        candidates = [
            working_dir / 'coverage' / 'coverage-final.json',
            working_dir / 'coverage' / 'coverage.json',
            working_dir / '.nyc_output' / 'coverage.json',
            working_dir / 'reports' / 'coverage' / 'coverage.json',
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        return None


# ========================================
# Convenience Functions
# ========================================

def extract_coverage_from_jest(
    working_dir: Path,
    test_name: str
) -> Optional[TestCoverageMapping]:
    """
    Quick helper to extract coverage from Jest run.
    
    Assumes coverage/coverage-final.json exists in working_dir.
    
    Args:
        working_dir: Directory with coverage report
        test_name: Name of the test
        
    Returns:
        TestCoverageMapping or None
    """
    parser = IstanbulParser()
    locator = IstanbulReportLocator()
    
    json_path = locator.find_report(working_dir)
    if not json_path:
        return None
    
    return parser.parse(
        json_path=json_path,
        test_name=test_name,
        execution_mode=ExecutionMode.ISOLATED
    )
