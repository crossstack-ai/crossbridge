"""
Coverage Database Repository.

Handles persistence of test-to-code coverage mappings.
Append-only design: never UPDATE, only INSERT.
"""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional, Set, Dict
from datetime import datetime

from core.logging import get_logger, LogCategory
from core.coverage.models import (
    TestCoverageMapping,
    ScenarioCoverageMapping,
    CoveredCodeUnit,
    CoverageSource,
    ExecutionMode
)

logger = get_logger(__name__, category=LogCategory.PERSISTENCE)


class CoverageRepository:
    """Repository for test coverage mappings."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Create tables if they don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path) as f:
                conn.executescript(f.read())
    
    def save_test_coverage(
        self,
        mapping: TestCoverageMapping,
        discovery_run_id: Optional[str] = None
    ) -> int:
        """
        Save test coverage mapping to database.
        
        Args:
            mapping: Test coverage mapping
            discovery_run_id: ID of discovery run
            
        Returns:
            Number of rows inserted
        """
        if not discovery_run_id:
            discovery_run_id = str(uuid.uuid4())
        
        rows_inserted = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert coverage for each code unit
            for unit in mapping.covered_code_units:
                # Serialize line numbers to JSON
                line_numbers_json = json.dumps(unit.line_numbers) if unit.line_numbers else None
                
                # Calculate coverage percentage from available metrics
                coverage_pct = unit.line_coverage or unit.instruction_coverage or unit.branch_coverage or 0.0
                if coverage_pct and coverage_pct <= 1.0:
                    coverage_pct = coverage_pct * 100.0  # Convert to percentage
                
                # Determine coverage type based on available metrics
                if unit.instruction_coverage is not None:
                    cov_type = "instruction"
                    covered = int(unit.instruction_coverage * 100) if unit.instruction_coverage else 0
                    missed = 100 - covered
                elif unit.line_coverage is not None:
                    cov_type = "line"
                    covered = int(unit.line_coverage * 100) if unit.line_coverage else 0
                    missed = 100 - covered
                elif unit.branch_coverage is not None:
                    cov_type = "branch"
                    covered = unit.covered_branches
                    missed = unit.total_branches - unit.covered_branches
                else:
                    cov_type = "line"
                    covered = len(unit.line_numbers) if unit.line_numbers else 0
                    missed = 0
                
                cursor.execute("""
                    INSERT OR IGNORE INTO test_code_coverage (
                        test_id,
                        test_name,
                        test_framework,
                        class_name,
                        method_name,
                        coverage_type,
                        covered_count,
                        missed_count,
                        coverage_percentage,
                        line_numbers,
                        confidence,
                        execution_mode,
                        coverage_source,
                        discovery_run_id,
                        jacoco_report_path,
                        source_file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mapping.test_id,
                    mapping.test_name,
                    mapping.test_framework,
                    unit.class_name,
                    unit.method_name,
                    cov_type,
                    covered,
                    missed,
                    coverage_pct,
                    line_numbers_json,
                    mapping.confidence,
                    mapping.execution_mode.value if mapping.execution_mode else None,
                    mapping.coverage_source.value,
                    discovery_run_id,
                    None,  # jacoco_report_path - deprecated field
                    unit.file_path
                ))
                
                if cursor.rowcount > 0:
                    rows_inserted += 1
        
        return rows_inserted
    
    def save_scenario_coverage(
        self,
        mapping: ScenarioCoverageMapping,
        discovery_run_id: Optional[str] = None
    ) -> int:
        """
        Save scenario coverage mapping to database.
        
        Args:
            mapping: Scenario coverage mapping
            discovery_run_id: ID of discovery run
            
        Returns:
            Number of rows inserted
        """
        if not discovery_run_id:
            discovery_run_id = str(uuid.uuid4())
        
        rows_inserted = 0
        
        # Aggregate coverage if not done yet
        if not mapping.aggregated_code_units:
            mapping.aggregate_coverage()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert coverage for each aggregated code unit
            for unit in mapping.aggregated_code_units:
                # Calculate coverage percentage
                coverage_pct = unit.line_coverage or unit.instruction_coverage or unit.branch_coverage or 0.0
                if coverage_pct and coverage_pct <= 1.0:
                    coverage_pct = coverage_pct * 100.0
                
                # Determine coverage type and totals
                if unit.line_coverage is not None:
                    cov_type = "line"
                    covered = int(unit.line_coverage * 100) if unit.line_coverage else 0
                    total = 100
                elif unit.branch_coverage is not None:
                    cov_type = "branch"
                    covered = unit.covered_branches
                    total = unit.total_branches
                else:
                    cov_type = "instruction"
                    covered = int((unit.instruction_coverage or 0) * 100)
                    total = 100
                
                cursor.execute("""
                    INSERT OR IGNORE INTO scenario_code_coverage (
                        scenario_id,
                        scenario_name,
                        feature_name,
                        feature_file,
                        class_name,
                        method_name,
                        coverage_type,
                        covered_count,
                        total_count,
                        coverage_percentage,
                        confidence,
                        execution_mode,
                        coverage_source,
                        step_count,
                        discovery_run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mapping.scenario_id,
                    mapping.scenario_name,
                    mapping.feature_name,
                    mapping.feature_file,
                    unit.class_name,
                    unit.method_name,
                    cov_type,
                    covered,
                    total,
                    coverage_pct,
                    mapping.confidence,
                    None,  # execution_mode - not present in ScenarioCoverageMapping
                    mapping.coverage_source.value,
                    len(mapping.step_coverage_mappings),
                    discovery_run_id
                ))
                
                if cursor.rowcount > 0:
                    rows_inserted += 1
        
        return rows_inserted
    
    def get_tests_covering_class(
        self,
        class_name: str,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Find all tests that cover a given class.
        
        Args:
            class_name: Fully qualified class name
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of test info dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT
                    test_id,
                    test_name,
                    test_framework,
                    MAX(confidence) as confidence,
                    COUNT(DISTINCT method_name) as methods_covered,
                    MAX(discovery_timestamp) as latest_discovery
                FROM test_code_coverage
                WHERE class_name = ? AND confidence >= ?
                GROUP BY test_id
                ORDER BY confidence DESC, methods_covered DESC
            """, (class_name, min_confidence))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_tests_covering_method(
        self,
        class_name: str,
        method_name: str,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Find all tests that cover a given method.
        
        Args:
            class_name: Fully qualified class name
            method_name: Method name
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of test info dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT
                    test_id,
                    test_name,
                    test_framework,
                    MAX(confidence) as confidence,
                    MAX(discovery_timestamp) as latest_discovery
                FROM test_code_coverage
                WHERE class_name = ? AND method_name = ? AND confidence >= ?
                GROUP BY test_id
                ORDER BY confidence DESC
            """, (class_name, method_name, min_confidence))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_coverage_for_test(
        self,
        test_id: str
    ) -> List[Dict]:
        """
        Get all coverage for a given test.
        
        Args:
            test_id: Test identifier
            
        Returns:
            List of coverage records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    test_name,
                    test_framework,
                    class_name,
                    method_name,
                    coverage_type,
                    covered_count,
                    missed_count,
                    coverage_percentage,
                    confidence,
                    line_numbers
                FROM test_code_coverage
                WHERE test_id = ?
                ORDER BY class_name, method_name
            """, (test_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_impact_for_changed_classes(
        self,
        changed_classes: Set[str],
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Get all tests impacted by changed classes.
        
        Args:
            changed_classes: Set of changed class names
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of impacted test info
        """
        if not changed_classes:
            return []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            placeholders = ",".join("?" * len(changed_classes))
            query = f"""
                SELECT DISTINCT
                    test_id,
                    test_name,
                    test_framework,
                    class_name,
                    MAX(confidence) as confidence,
                    COUNT(DISTINCT method_name) as methods_covered
                FROM test_code_coverage
                WHERE class_name IN ({placeholders}) AND confidence >= ?
                GROUP BY test_id, class_name
                ORDER BY confidence DESC, test_id
            """
            
            cursor.execute(query, (*changed_classes, min_confidence))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def create_discovery_run(
        self,
        run_type: str,
        test_framework: str,
        coverage_source: CoverageSource,
        commit_hash: Optional[str] = None
    ) -> str:
        """
        Create a new coverage discovery run.
        
        Args:
            run_type: 'isolated', 'batch', 'full_suite'
            test_framework: Test framework name
            coverage_source: Coverage tool used
            commit_hash: Git commit hash
            
        Returns:
            Discovery run ID
        """
        run_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO coverage_discovery_run (
                    id,
                    run_type,
                    test_framework,
                    coverage_source,
                    commit_hash,
                    status
                ) VALUES (?, ?, ?, ?, ?, 'running')
            """, (
                run_id,
                run_type,
                test_framework,
                coverage_source.value,
                commit_hash
            ))
        
        return run_id
    
    def complete_discovery_run(
        self,
        run_id: str,
        test_count: int,
        classes_covered: int,
        methods_covered: int,
        duration_seconds: float
    ):
        """
        Mark discovery run as completed.
        
        Args:
            run_id: Discovery run ID
            test_count: Number of tests processed
            classes_covered: Number of unique classes covered
            methods_covered: Number of unique methods covered
            duration_seconds: Run duration
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Calculate average confidence
            cursor.execute("""
                SELECT AVG(confidence) FROM test_code_coverage
                WHERE discovery_run_id = ?
            """, (run_id,))
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            cursor.execute("""
                UPDATE coverage_discovery_run
                SET status = 'completed',
                    test_count = ?,
                    classes_covered = ?,
                    methods_covered = ?,
                    average_confidence = ?,
                    duration_seconds = ?
                WHERE id = ?
            """, (
                test_count,
                classes_covered,
                methods_covered,
                avg_confidence,
                duration_seconds,
                run_id
            ))
    
    def fail_discovery_run(self, run_id: str, error_message: str):
        """
        Mark discovery run as failed.
        
        Args:
            run_id: Discovery run ID
            error_message: Error message
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE coverage_discovery_run
                SET status = 'failed',
                    error_message = ?
                WHERE id = ?
            """, (error_message, run_id))
    
    def get_coverage_statistics(self) -> Dict:
        """
        Get overall coverage statistics.
        
        Returns:
            Statistics dictionary
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total tests with coverage
            cursor.execute("SELECT COUNT(DISTINCT test_id) FROM test_code_coverage")
            total_tests = cursor.fetchone()[0]
            
            # Total classes covered
            cursor.execute("SELECT COUNT(DISTINCT class_name) FROM test_code_coverage")
            total_classes = cursor.fetchone()[0]
            
            # Total methods covered
            cursor.execute("""
                SELECT COUNT(DISTINCT class_name || '.' || method_name) 
                FROM test_code_coverage 
                WHERE method_name IS NOT NULL
            """)
            total_methods = cursor.fetchone()[0]
            
            # Average confidence
            cursor.execute("SELECT AVG(confidence) FROM test_code_coverage")
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            # By framework
            cursor.execute("""
                SELECT test_framework, COUNT(DISTINCT test_id) as test_count
                FROM test_code_coverage
                GROUP BY test_framework
            """)
            by_framework = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "total_tests": total_tests,
                "total_classes": total_classes,
                "total_methods": total_methods,
                "average_confidence": avg_confidence,
                "by_framework": by_framework
            }
