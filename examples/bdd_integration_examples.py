"""
Integration examples for BDD adapters with CrossBridge system.

This demonstrates how to integrate BDD framework adapters (Cucumber Java, Robot Framework, JBehave)
with the main CrossBridge intelligence and analytics pipeline.
"""
from pathlib import Path
from typing import List
from datetime import datetime

from core.bdd.registry import get_adapter
from core.bdd.models import BDDFeature, BDDScenario, BDDExecutionResult


class BDDAnalyticsPipeline:
    """
    Integration pipeline for BDD frameworks with CrossBridge analytics.
    
    Demonstrates:
    1. Feature discovery and parsing
    2. Step definition mapping
    3. Execution result ingestion
    4. Scenario-level intelligence
    5. Flaky test detection for BDD scenarios
    """
    
    def __init__(self, framework: str, project_root: Path):
        """
        Initialize BDD analytics pipeline.
        
        Args:
            framework: "cucumber-java", "robot-bdd", or "jbehave"
            project_root: Root directory of the test project
        """
        self.framework = framework
        self.project_root = project_root
        self.adapter = None
    
    def discover_and_analyze(self) -> dict:
        """
        Complete discovery and analysis workflow.
        
        Returns:
            Analytics summary with scenario metrics
        """
        # Step 1: Get adapter from registry
        self.adapter = self._get_adapter()
        
        if not self.adapter:
            return {"error": f"Adapter '{self.framework}' not available"}
        
        # Step 2: Discover features
        features = self._discover_features()
        
        # Step 3: Map step definitions
        step_coverage = self._analyze_step_coverage()
        
        # Step 4: Generate analytics summary
        summary = self._generate_summary(features, step_coverage)
        
        return summary
    
    def _get_adapter(self):
        """Get BDD adapter based on framework."""
        if self.framework == "cucumber-java":
            return get_adapter("cucumber-java",
                features_dir=self.project_root / "src/test/resources/features",
                step_definitions_dir=self.project_root / "src/test/java"
            )
        elif self.framework == "robot-bdd":
            return get_adapter("robot-bdd",
                robot_dir=self.project_root / "tests",
                resource_dir=self.project_root / "resources"
            )
        elif self.framework == "jbehave":
            return get_adapter("jbehave",
                stories_dir=self.project_root / "src/test/resources/stories",
                steps_dir=self.project_root / "src/test/java"
            )
        return None
    
    def _discover_features(self) -> List[BDDFeature]:
        """Discover all features in project."""
        features = []
        
        # Find feature files
        if self.framework == "cucumber-java":
            feature_dir = self.project_root / "src/test/resources/features"
        elif self.framework == "robot-bdd":
            feature_dir = self.project_root / "tests"
        else:  # jbehave
            feature_dir = self.project_root / "src/test/resources/stories"
        
        if not feature_dir.exists():
            return features
        
        feature_files = self.adapter.feature_parser.discover_feature_files(feature_dir)
        
        for file_path in feature_files:
            try:
                feature = self.adapter.feature_parser.parse_file(file_path)
                features.append(feature)
            except Exception as e:
                print(f"Failed to parse {file_path}: {e}")
        
        return features
    
    def _analyze_step_coverage(self) -> dict:
        """Analyze step definition coverage."""
        if hasattr(self.adapter, 'discover_and_map'):
            return self.adapter.discover_and_map()
        
        return {"coverage_percent": 0, "total_steps": 0, "mapped_steps": 0}
    
    def _generate_summary(self, features: List[BDDFeature], step_coverage: dict) -> dict:
        """Generate analytics summary."""
        total_scenarios = sum(f.total_scenarios for f in features)
        total_steps = sum(
            len(scenario.steps)
            for feature in features
            for scenario in feature.all_scenarios()
        )
        
        # Extract tags
        all_tags = set()
        for feature in features:
            all_tags.update(feature.tags)
            for scenario in feature.all_scenarios():
                all_tags.update(scenario.tags)
        
        return {
            "framework": self.framework,
            "project_root": str(self.project_root),
            "total_features": len(features),
            "total_scenarios": total_scenarios,
            "total_steps": total_steps,
            "unique_tags": len(all_tags),
            "tags": sorted(all_tags),
            "step_coverage_percent": step_coverage.get("coverage_percent", 0),
            "mapped_steps": step_coverage.get("mapped_steps", 0),
            "features": [
                {
                    "name": f.name,
                    "file": f.file_path,
                    "scenarios": f.total_scenarios,
                    "tags": f.tags
                }
                for f in features
            ]
        }


class BDDExecutionIngestion:
    """
    Ingest BDD execution results into CrossBridge intelligence system.
    
    Demonstrates:
    1. Parse execution reports (JSON/XML)
    2. Link failures to scenarios
    3. Extract flakiness patterns
    4. Store in CrossBridge database
    """
    
    def __init__(self, framework: str):
        self.framework = framework
        self.adapter = get_adapter(framework)
    
    def ingest_execution_report(self, report_path: Path) -> dict:
        """
        Ingest execution report and analyze results.
        
        Args:
            report_path: Path to execution report (cucumber.json, output.xml, etc.)
        
        Returns:
            Ingestion summary with metrics
        """
        if not self.adapter:
            return {"error": f"Adapter '{self.framework}' not available"}
        
        # Parse execution results
        results = self.adapter.execution_parser.parse_execution_report(report_path)
        
        # Analyze results
        summary = self._analyze_results(results)
        
        # Store in database (integration point)
        self._store_results(results)
        
        return summary
    
    def _analyze_results(self, results: List[BDDExecutionResult]) -> dict:
        """Analyze execution results."""
        passed = [r for r in results if r.status == "passed"]
        failed = [r for r in results if r.status == "failed"]
        skipped = [r for r in results if r.status == "skipped"]
        
        total_duration_ms = sum(r.duration_ms for r in results)
        
        failure_types = {}
        for result in failed:
            if result.failure:
                error_type = result.failure.error_type
                failure_types[error_type] = failure_types.get(error_type, 0) + 1
        
        return {
            "framework": self.framework,
            "total_scenarios": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "skipped": len(skipped),
            "pass_rate": len(passed) / len(results) * 100 if results else 0,
            "total_duration_ms": total_duration_ms,
            "avg_duration_ms": total_duration_ms / len(results) if results else 0,
            "failure_types": failure_types,
            "failed_scenarios": [
                {
                    "scenario_id": r.scenario_id,
                    "scenario_name": r.scenario_name,
                    "feature_name": r.feature_name,
                    "error_type": r.failure.error_type if r.failure else None,
                    "error_message": r.failure.error_message if r.failure else None
                }
                for r in failed
            ]
        }
    
    def _store_results(self, results: List[BDDExecutionResult]):
        """Store results in CrossBridge database."""
        # Integration point: Store in persistence layer
        # from persistence.db_manager import DbManager
        # db = DbManager()
        # for result in results:
        #     db.store_scenario_execution(result)
        pass


class BDDFlakinessDetector:
    """
    Detect flaky BDD scenarios across test runs.
    
    Integrates with CrossBridge flaky detection system.
    """
    
    def __init__(self, framework: str):
        self.framework = framework
        self.execution_history = []
    
    def add_execution(self, report_path: Path):
        """Add execution report to history."""
        adapter = get_adapter(self.framework)
        if not adapter:
            return
        
        results = adapter.execution_parser.parse_execution_report(report_path)
        self.execution_history.append({
            "timestamp": datetime.now(),
            "results": results
        })
    
    def detect_flaky_scenarios(self, min_runs: int = 3) -> List[dict]:
        """
        Detect scenarios with inconsistent results.
        
        Args:
            min_runs: Minimum number of runs to consider
        
        Returns:
            List of flaky scenarios with statistics
        """
        if len(self.execution_history) < min_runs:
            return []
        
        # Group results by scenario ID
        scenario_results = {}
        for execution in self.execution_history:
            for result in execution["results"]:
                scenario_id = result.scenario_id
                if scenario_id not in scenario_results:
                    scenario_results[scenario_id] = []
                scenario_results[scenario_id].append(result.status)
        
        # Detect flakiness
        flaky_scenarios = []
        for scenario_id, statuses in scenario_results.items():
            if len(statuses) < min_runs:
                continue
            
            # Flaky if both passed and failed in recent runs
            passed_count = statuses.count("passed")
            failed_count = statuses.count("failed")
            
            if passed_count > 0 and failed_count > 0:
                flaky_scenarios.append({
                    "scenario_id": scenario_id,
                    "total_runs": len(statuses),
                    "passed": passed_count,
                    "failed": failed_count,
                    "flaky_rate": failed_count / len(statuses) * 100,
                    "recent_statuses": statuses[-5:]  # Last 5 runs
                })
        
        return sorted(flaky_scenarios, key=lambda x: x["flaky_rate"], reverse=True)


# Example usage
def example_cucumber_java_integration():
    """Example: Integrate Cucumber Java project with CrossBridge."""
    project_root = Path("/path/to/cucumber-project")
    
    # Discovery and analysis
    pipeline = BDDAnalyticsPipeline("cucumber-java", project_root)
    summary = pipeline.discover_and_analyze()
    
    print(f"Discovered {summary['total_features']} features")
    print(f"Total scenarios: {summary['total_scenarios']}")
    print(f"Step coverage: {summary['step_coverage_percent']:.1f}%")
    print(f"Tags: {summary['tags']}")
    
    # Execution ingestion
    report_path = project_root / "target/cucumber-reports/cucumber.json"
    ingestion = BDDExecutionIngestion("cucumber-java")
    execution_summary = ingestion.ingest_execution_report(report_path)
    
    print(f"Pass rate: {execution_summary['pass_rate']:.1f}%")
    print(f"Failed scenarios: {execution_summary['failed']}")
    
    # Flaky detection
    detector = BDDFlakinessDetector("cucumber-java")
    for report in [report_path]:  # Add multiple reports in real usage
        detector.add_execution(report)
    
    flaky = detector.detect_flaky_scenarios()
    print(f"Detected {len(flaky)} flaky scenarios")


def example_robot_bdd_integration():
    """Example: Integrate Robot Framework BDD with CrossBridge."""
    project_root = Path("/path/to/robot-project")
    
    pipeline = BDDAnalyticsPipeline("robot-bdd", project_root)
    summary = pipeline.discover_and_analyze()
    
    print(f"Robot BDD - {summary['total_features']} test suites")
    print(f"Total test cases: {summary['total_scenarios']}")
    
    # Parse execution
    report_path = project_root / "results/output.xml"
    ingestion = BDDExecutionIngestion("robot-bdd")
    execution_summary = ingestion.ingest_execution_report(report_path)
    
    print(f"Pass rate: {execution_summary['pass_rate']:.1f}%")


def example_jbehave_integration():
    """Example: Integrate JBehave with CrossBridge."""
    project_root = Path("/path/to/jbehave-project")
    
    pipeline = BDDAnalyticsPipeline("jbehave", project_root)
    summary = pipeline.discover_and_analyze()
    
    print(f"JBehave - {summary['total_features']} stories")
    print(f"Total scenarios: {summary['total_scenarios']}")
    
    # Parse execution (XML report)
    report_path = project_root / "target/jbehave-reports/TEST-Stories.xml"
    ingestion = BDDExecutionIngestion("jbehave")
    execution_summary = ingestion.ingest_execution_report(report_path)
    
    print(f"Pass rate: {execution_summary['pass_rate']:.1f}%")
    print(f"Failure types: {execution_summary['failure_types']}")


if __name__ == "__main__":
    # Run examples (update paths to real projects)
    print("=== Cucumber Java Integration ===")
    example_cucumber_java_integration()
    
    print("\n=== Robot Framework BDD Integration ===")
    example_robot_bdd_integration()
    
    print("\n=== JBehave Integration ===")
    example_jbehave_integration()
