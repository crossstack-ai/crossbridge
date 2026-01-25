"""
Cucumber Scenario Coverage Aggregation.

Bridges the gap between Cucumber scenarios and JaCoCo coverage:
1. Scenario → Steps (from Cucumber JSON)
2. Steps → Java step definitions (via mapping)
3. Step definitions → Production code (via JaCoCo)

Result: Scenario-level coverage mapping.
"""

from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime

from core.logging import get_logger, LogCategory
from core.coverage.models import (
    TestCoverageMapping,
    ScenarioCoverageMapping,
    CoverageSource,
    ExecutionMode
)
from core.coverage.jacoco_parser import JaCoCoXMLParser
from adapters.selenium_bdd_java import (
    parse_cucumber_json,
    ScenarioResult
)

logger = get_logger(__name__, category=LogCategory.TESTING)


class CucumberCoverageAggregator:
    """
    Aggregate JaCoCo coverage at Cucumber scenario level.
    
    Problem: JaCoCo knows about Java methods, not Cucumber scenarios.
    Solution: Map scenarios → steps → Java methods → coverage.
    """
    
    def __init__(self):
        self.jacoco_parser = JaCoCoXMLParser()
    
    def aggregate_scenario_coverage(
        self,
        scenario: ScenarioResult,
        jacoco_xml_path: Path,
        step_to_method_map: Optional[Dict[str, Set[str]]] = None,
        execution_mode: ExecutionMode = ExecutionMode.ISOLATED
    ) -> ScenarioCoverageMapping:
        """
        Create scenario-level coverage mapping.
        
        Args:
            scenario: Cucumber scenario result
            jacoco_xml_path: Path to jacoco.xml for this scenario
            step_to_method_map: Map of step text → Java method names
            execution_mode: How coverage was collected
            
        Returns:
            ScenarioCoverageMapping with aggregated coverage
        """
        # Parse JaCoCo coverage
        base_coverage = self.jacoco_parser.parse(
            xml_path=jacoco_xml_path,
            test_id=scenario.id,
            test_name=scenario.name,
            execution_mode=execution_mode
        )
        
        # Create per-step mappings (if we have step-to-method mapping)
        step_mappings = []
        
        if step_to_method_map:
            step_mappings = self._create_step_mappings(
                scenario=scenario,
                base_coverage=base_coverage,
                step_to_method_map=step_to_method_map
            )
        
        # Create scenario mapping
        scenario_mapping = ScenarioCoverageMapping(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            feature_name=getattr(scenario, 'feature_name', None),
            feature_file=getattr(scenario, 'feature_file', None),
            step_coverage_mappings=step_mappings,
            coverage_source=CoverageSource.JACOCO,
            confidence=base_coverage.confidence,
            execution_time=datetime.now()
        )
        
        # If no step mappings, use base coverage directly
        if not step_mappings:
            scenario_mapping.aggregated_classes = base_coverage.covered_classes
            scenario_mapping.aggregated_methods = base_coverage.covered_methods
            scenario_mapping.aggregated_code_units = base_coverage.covered_code_units
        else:
            # Aggregate from steps
            scenario_mapping.aggregate_coverage()
        
        return scenario_mapping
    
    def aggregate_feature_coverage(
        self,
        cucumber_json_path: Path,
        jacoco_xml_path: Path,
        step_to_method_map: Optional[Dict[str, Set[str]]] = None,
        execution_mode: ExecutionMode = ExecutionMode.SMALL_BATCH
    ) -> List[ScenarioCoverageMapping]:
        """
        Aggregate coverage for all scenarios in a feature.
        
        Args:
            cucumber_json_path: Path to Cucumber JSON report
            jacoco_xml_path: Path to JaCoCo XML (batch coverage)
            step_to_method_map: Optional step-to-method mapping
            execution_mode: Batch execution mode
            
        Returns:
            List of scenario coverage mappings
        """
        # Parse Cucumber JSON
        feature_results = parse_cucumber_json(cucumber_json_path)
        
        # Parse JaCoCo coverage (batch)
        batch_coverage = self.jacoco_parser.parse(
            xml_path=jacoco_xml_path,
            test_id="batch",
            execution_mode=execution_mode
        )
        
        # Create scenario mappings
        scenario_mappings = []
        
        for feature in feature_results:
            for scenario in feature.scenarios:
                # Create scenario mapping with batch coverage
                scenario_mapping = ScenarioCoverageMapping(
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    feature_name=feature.name,
                    feature_file=feature.uri,
                    coverage_source=CoverageSource.JACOCO,
                    confidence=batch_coverage.confidence,
                    execution_time=datetime.now()
                )
                
                # Use batch coverage (lower confidence)
                scenario_mapping.aggregated_classes = batch_coverage.covered_classes.copy()
                scenario_mapping.aggregated_methods = batch_coverage.covered_methods.copy()
                scenario_mapping.aggregated_code_units = batch_coverage.covered_code_units.copy()
                
                scenario_mappings.append(scenario_mapping)
        
        return scenario_mappings
    
    def _create_step_mappings(
        self,
        scenario: ScenarioResult,
        base_coverage: TestCoverageMapping,
        step_to_method_map: Dict[str, Set[str]]
    ) -> List[TestCoverageMapping]:
        """
        Create per-step coverage mappings.
        
        This requires knowing which Java methods implement each step.
        """
        step_mappings = []
        
        for step in scenario.steps:
            # Get Java methods for this step
            step_key = self._normalize_step_text(step.keyword + " " + step.name)
            java_methods = step_to_method_map.get(step_key, set())
            
            if not java_methods:
                continue
            
            # Filter base coverage to this step's methods
            step_units = [
                unit for unit in base_coverage.covered_code_units
                if f"{unit.class_name}.{unit.method_name}" in java_methods
            ]
            
            step_classes = {unit.class_name for unit in step_units}
            step_methods = {f"{unit.class_name}.{unit.method_name}" for unit in step_units}
            
            # Create step mapping
            step_mapping = TestCoverageMapping(
                test_id=f"{scenario.id}::{step.keyword}::{step.name}",
                test_name=f"{step.keyword} {step.name}",
                test_framework="cucumber",
                covered_classes=step_classes,
                covered_methods=step_methods,
                covered_code_units=step_units,
                coverage_source=CoverageSource.JACOCO,
                execution_mode=base_coverage.execution_mode,
                confidence=base_coverage.confidence
            )
            
            step_mappings.append(step_mapping)
        
        return step_mappings
    
    def _normalize_step_text(self, step_text: str) -> str:
        """
        Normalize step text for matching.
        
        Example:
        "Given user is on login page" → "given user is on login page"
        """
        return step_text.strip().lower()


class StepDefinitionMapper:
    """
    Map Cucumber steps to Java step definition methods.
    
    This can be done via:
    1. Static analysis (parse @Given, @When, @Then annotations)
    2. Runtime instrumentation (log step executions)
    3. Naming conventions (step text → method name heuristics)
    """
    
    def __init__(self):
        self.step_map: Dict[str, Set[str]] = {}
    
    def build_from_source(self, step_definitions_dir: Path) -> Dict[str, Set[str]]:
        """
        Build step-to-method map from Java source files.
        
        Parses @Given/@When/@Then annotations.
        
        Args:
            step_definitions_dir: Directory containing step definition classes
            
        Returns:
            Map of step pattern → Java method names
        """
        # TODO: Implement static analysis
        # For now, return empty map
        return {}
    
    def build_from_execution_log(self, log_path: Path) -> Dict[str, Set[str]]:
        """
        Build step-to-method map from execution logs.
        
        Requires instrumentation to log step→method mappings.
        
        Args:
            log_path: Path to execution log
            
        Returns:
            Map of step text → Java method names
        """
        # TODO: Implement log parsing
        return {}
    
    def add_mapping(self, step_pattern: str, java_method: str):
        """
        Manually add a step-to-method mapping.
        
        Args:
            step_pattern: Cucumber step pattern (e.g., "Given user logs in")
            java_method: Fully qualified Java method (e.g., "LoginSteps.userLogsIn")
        """
        if step_pattern not in self.step_map:
            self.step_map[step_pattern] = set()
        self.step_map[step_pattern].add(java_method)
    
    def get_mapping(self) -> Dict[str, Set[str]]:
        """Get current step-to-method mapping."""
        return self.step_map


class CucumberCoverageCollector:
    """
    Orchestrate Cucumber coverage collection.
    
    Workflow:
    1. Run Cucumber tests
    2. Collect JaCoCo coverage
    3. Parse Cucumber JSON
    4. Aggregate scenario-level coverage
    5. Persist to database
    """
    
    def __init__(self):
        self.aggregator = CucumberCoverageAggregator()
        self.step_mapper = StepDefinitionMapper()
    
    def collect_isolated_scenario_coverage(
        self,
        scenario_id: str,
        cucumber_json: Path,
        jacoco_xml: Path
    ) -> Optional[ScenarioCoverageMapping]:
        """
        Collect coverage for a single scenario (isolated execution).
        
        Highest confidence mapping.
        """
        # Parse Cucumber JSON
        features = parse_cucumber_json(cucumber_json)
        
        # Find scenario
        target_scenario = None
        for feature in features:
            for scenario in feature.scenarios:
                if scenario.id == scenario_id:
                    target_scenario = scenario
                    break
        
        if not target_scenario:
            return None
        
        # Aggregate coverage
        return self.aggregator.aggregate_scenario_coverage(
            scenario=target_scenario,
            jacoco_xml_path=jacoco_xml,
            step_to_method_map=self.step_mapper.get_mapping(),
            execution_mode=ExecutionMode.ISOLATED
        )
    
    def collect_feature_coverage(
        self,
        cucumber_json: Path,
        jacoco_xml: Path
    ) -> List[ScenarioCoverageMapping]:
        """
        Collect coverage for all scenarios in a feature (batch execution).
        
        Lower confidence, but faster.
        """
        return self.aggregator.aggregate_feature_coverage(
            cucumber_json_path=cucumber_json,
            jacoco_xml_path=jacoco_xml,
            step_to_method_map=self.step_mapper.get_mapping(),
            execution_mode=ExecutionMode.SMALL_BATCH
        )
