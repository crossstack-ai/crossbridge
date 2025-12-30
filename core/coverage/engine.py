"""
Coverage Mapping Engine.

Orchestrates test coverage collection and mapping:
1. Execute tests with coverage enabled
2. Parse coverage reports
3. Map tests to production code
4. Persist mappings to database
5. Query for impact analysis
"""

import subprocess
import time
from pathlib import Path
from typing import List, Optional, Set, Dict
from datetime import datetime

from core.coverage.models import (
    TestCoverageMapping,
    CoverageSource,
    ExecutionMode,
    CoverageImpactQuery
)
from core.coverage.jacoco_parser import JaCoCoXMLParser, JaCoCoReportLocator

# Optional Cucumber support
try:
    from core.coverage.cucumber_coverage import CucumberCoverageCollector
    CUCUMBER_SUPPORT = True
except ImportError:
    CucumberCoverageCollector = None
    CUCUMBER_SUPPORT = False

from core.coverage.repository import CoverageRepository


class CoverageMappingEngine:
    """
    Engine for collecting and mapping test coverage.
    
    Supports:
    - Isolated test execution (highest confidence)
    - Batch test execution (lower confidence, faster)
    - Cucumber scenario aggregation
    - Database persistence
    - Impact queries
    """
    
    def __init__(self, db_path: Path):
        self.repository = CoverageRepository(db_path)
        self.jacoco_parser = JaCoCoXMLParser()
        self.cucumber_collector = CucumberCoverageCollector() if CUCUMBER_SUPPORT else None
        self.report_locator = JaCoCoReportLocator()
    
    def collect_coverage_isolated(
        self,
        test_id: str,
        test_command: str,
        working_dir: Path,
        test_framework: str = "junit",
        timeout: int = 300
    ) -> Optional[TestCoverageMapping]:
        """
        Collect coverage for a single test (isolated execution).
        
        Highest confidence mapping (0.90-0.95).
        
        Args:
            test_id: Test identifier
            test_command: Command to run test (e.g., "mvn test -Dtest=LoginTest")
            working_dir: Working directory for test execution
            test_framework: Test framework name
            timeout: Execution timeout in seconds
            
        Returns:
            TestCoverageMapping or None if failed
        """
        print(f"Collecting isolated coverage for: {test_id}")
        start_time = time.time()
        
        try:
            # Execute test with coverage
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                print(f"Test execution failed: {result.stderr}")
                return None
            
            # Locate JaCoCo report
            jacoco_xml = self.report_locator.find_report(working_dir)
            if not jacoco_xml:
                print(f"JaCoCo report not found in {working_dir}")
                return None
            
            # Parse coverage
            mapping = self.jacoco_parser.parse(
                xml_path=jacoco_xml,
                test_id=test_id,
                test_name=test_id,
                execution_mode=ExecutionMode.ISOLATED
            )
            
            # Set test framework
            mapping.test_framework = test_framework
            
            # Create discovery run
            duration = time.time() - start_time
            run_id = self.repository.create_discovery_run(
                run_type="isolated",
                test_framework=test_framework,
                coverage_source=CoverageSource.JACOCO
            )
            
            # Save to database
            rows = self.repository.save_test_coverage(mapping, run_id)
            
            # Complete discovery run
            self.repository.complete_discovery_run(
                run_id=run_id,
                test_count=1,
                classes_covered=len(mapping.covered_classes),
                methods_covered=len(mapping.covered_methods),
                duration_seconds=duration
            )
            
            print(f"✓ Collected coverage: {len(mapping.covered_classes)} classes, "
                  f"{len(mapping.covered_methods)} methods (confidence: {mapping.confidence:.2f})")
            
            return mapping
            
        except subprocess.TimeoutExpired:
            print(f"Test execution timed out after {timeout}s")
            return None
        except Exception as e:
            print(f"Error collecting coverage: {e}")
            return None
    
    def collect_coverage_batch(
        self,
        test_ids: List[str],
        test_command: str,
        working_dir: Path,
        test_framework: str = "junit",
        timeout: int = 600
    ) -> List[TestCoverageMapping]:
        """
        Collect coverage for multiple tests (batch execution).
        
        Lower confidence (0.60-0.75), but faster than isolated.
        
        Args:
            test_ids: List of test identifiers
            test_command: Command to run tests (e.g., "mvn test")
            working_dir: Working directory
            test_framework: Test framework name
            timeout: Execution timeout
            
        Returns:
            List of TestCoverageMapping
        """
        print(f"Collecting batch coverage for {len(test_ids)} tests")
        start_time = time.time()
        
        try:
            # Execute tests with coverage
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                print(f"Test execution failed: {result.stderr}")
                return []
            
            # Locate JaCoCo report
            jacoco_xml = self.report_locator.find_report(working_dir)
            if not jacoco_xml:
                print(f"JaCoCo report not found")
                return []
            
            # Parse batch coverage
            mappings_dict = self.jacoco_parser.parse_batch(
                xml_path=jacoco_xml,
                test_ids=test_ids,
                execution_mode=ExecutionMode.SMALL_BATCH
            )
            
            # Convert dict to list
            mappings = list(mappings_dict.values())
            
            # Set test framework
            for mapping in mappings:
                mapping.test_framework = test_framework
            
            # Create discovery run
            duration = time.time() - start_time
            run_id = self.repository.create_discovery_run(
                run_type="batch",
                test_framework=test_framework,
                coverage_source=CoverageSource.JACOCO
            )
            
            # Save all mappings
            total_rows = 0
            all_classes = set()
            all_methods = set()
            
            for mapping in mappings:
                rows = self.repository.save_test_coverage(mapping, run_id)
                total_rows += rows
                all_classes.update(mapping.covered_classes)
                all_methods.update(mapping.covered_methods)
            
            # Complete discovery run
            self.repository.complete_discovery_run(
                run_id=run_id,
                test_count=len(mappings),
                classes_covered=len(all_classes),
                methods_covered=len(all_methods),
                duration_seconds=duration
            )
            
            print(f"✓ Collected coverage for {len(mappings)} tests: "
                  f"{len(all_classes)} classes, {len(all_methods)} methods")
            
            return mappings
            
        except subprocess.TimeoutExpired:
            print(f"Test execution timed out after {timeout}s")
            return []
        except Exception as e:
            print(f"Error collecting batch coverage: {e}")
            return []
    
    def collect_cucumber_coverage_isolated(
        self,
        scenario_id: str,
        test_command: str,
        working_dir: Path,
        cucumber_json: Path,
        timeout: int = 300
    ):
        """
        Collect coverage for a single Cucumber scenario.
        
        Args:
            scenario_id: Scenario identifier
            test_command: Command to run scenario
            working_dir: Working directory
            cucumber_json: Path to Cucumber JSON report
            timeout: Execution timeout
            
        Returns:
            ScenarioCoverageMapping or None
        """
        print(f"Collecting Cucumber coverage for: {scenario_id}")
        start_time = time.time()
        
        try:
            # Execute scenario with coverage
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                print(f"Scenario execution failed: {result.stderr}")
                return None
            
            # Locate JaCoCo report
            jacoco_xml = self.report_locator.find_report(working_dir)
            if not jacoco_xml:
                print(f"JaCoCo report not found")
                return None
            
            # Collect scenario coverage
            scenario_mapping = self.cucumber_collector.collect_isolated_scenario_coverage(
                scenario_id=scenario_id,
                cucumber_json=cucumber_json,
                jacoco_xml=jacoco_xml
            )
            
            if not scenario_mapping:
                print(f"Failed to collect scenario coverage")
                return None
            
            # Create discovery run
            duration = time.time() - start_time
            run_id = self.repository.create_discovery_run(
                run_type="isolated",
                test_framework="cucumber",
                coverage_source=CoverageSource.JACOCO
            )
            
            # Save to database
            rows = self.repository.save_scenario_coverage(scenario_mapping, run_id)
            
            # Complete discovery run
            self.repository.complete_discovery_run(
                run_id=run_id,
                test_count=1,
                classes_covered=len(scenario_mapping.aggregated_classes),
                methods_covered=len(scenario_mapping.aggregated_methods),
                duration_seconds=duration
            )
            
            print(f"✓ Collected scenario coverage: "
                  f"{len(scenario_mapping.aggregated_classes)} classes, "
                  f"{len(scenario_mapping.aggregated_methods)} methods")
            
            return scenario_mapping
            
        except subprocess.TimeoutExpired:
            print(f"Scenario execution timed out after {timeout}s")
            return None
        except Exception as e:
            print(f"Error collecting scenario coverage: {e}")
            return None
    
    def query_impact(
        self,
        changed_classes: Set[str],
        min_confidence: float = 0.5
    ) -> CoverageImpactQuery:
        """
        Query which tests are impacted by changed classes.
        
        Args:
            changed_classes: Set of changed class names
            min_confidence: Minimum confidence threshold
            
        Returns:
            CoverageImpactQuery with results
        """
        results = self.repository.get_impact_for_changed_classes(
            changed_classes,
            min_confidence
        )
        
        # Group by test
        affected_tests = {}
        for row in results:
            test_id = row['test_id']
            if test_id not in affected_tests:
                affected_tests[test_id] = {
                    'test_id': test_id,
                    'test_name': row['test_name'],
                    'test_framework': row['test_framework'],
                    'confidence': row['confidence'],
                    'covered_changed_classes': set()
                }
            affected_tests[test_id]['covered_changed_classes'].add(row['class_name'])
        
        # Create query result
        query = CoverageImpactQuery(
            changed_classes=changed_classes,
            changed_methods=set(),
            min_confidence=min_confidence
        )
        
        query.affected_tests = list(affected_tests.keys())
        
        # Store detailed results (as attribute for convenience)
        query.detailed_results = list(affected_tests.values())
        
        return query
    
    def get_test_coverage(self, test_id: str) -> Optional[TestCoverageMapping]:
        """
        Get coverage mapping for a specific test.
        
        Args:
            test_id: Test identifier
            
        Returns:
            TestCoverageMapping or None
        """
        coverage_records = self.repository.get_coverage_for_test(test_id)
        
        if not coverage_records:
            return None
        
        # Reconstruct mapping from records
        first_record = coverage_records[0]
        
        mapping = TestCoverageMapping(
            test_id=test_id,
            test_name=first_record['test_name'],
            test_framework=first_record.get('test_framework', 'unknown'),
            covered_classes=set(),
            covered_methods=set(),
            covered_code_units=[],
            coverage_source=CoverageSource.JACOCO,
            execution_mode=ExecutionMode.ISOLATED,
            confidence=first_record['confidence']
        )
        
        # Populate coverage data
        for record in coverage_records:
            mapping.covered_classes.add(record['class_name'])
            if record['method_name']:
                mapping.covered_methods.add(f"{record['class_name']}.{record['method_name']}")
        
        return mapping
    
    def get_statistics(self) -> Dict:
        """
        Get coverage statistics.
        
        Returns:
            Statistics dictionary
        """
        return self.repository.get_coverage_statistics()
