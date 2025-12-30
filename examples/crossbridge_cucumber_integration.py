"""
CrossBridge Platform Integration Example for Cucumber JSON Parser.

This example demonstrates how the Cucumber JSON parser integrates with
the CrossBridge platform for end-to-end test execution and analysis.
"""

import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adapters.selenium_bdd_java import (
    parse_cucumber_json,
    FeatureResult,
    ScenarioResult,
)


class CrossBridgeCucumberIntegration:
    """
    Integration layer between Cucumber test execution and CrossBridge platform.
    
    This class demonstrates the complete workflow:
    1. Execute Cucumber tests
    2. Parse results
    3. Normalize to CrossBridge models
    4. Persist to database (placeholder)
    5. Enable impact analysis (placeholder)
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cucumber_report_path = project_root / "target" / "cucumber-report.json"
    
    def execute_and_analyze(self) -> Dict:
        """
        Complete workflow: Execute tests, parse results, and analyze.
        
        Returns:
            Dictionary with execution summary and analysis results
        """
        print("=" * 70)
        print("CrossBridge Cucumber Integration - Full Workflow")
        print("=" * 70)
        
        # Step 1: Execute Cucumber tests (simulated - would run Maven/Gradle)
        print("\n[Step 1] Executing Cucumber tests...")
        self._execute_cucumber_tests()
        
        # Step 2: Parse Cucumber JSON report
        print("\n[Step 2] Parsing Cucumber JSON report...")
        features = self._parse_results()
        
        # Step 3: Normalize to CrossBridge models
        print("\n[Step 3] Normalizing to CrossBridge models...")
        normalized_data = self._normalize_results(features)
        
        # Step 4: Persist to database
        print("\n[Step 4] Persisting to database...")
        self._persist_results(normalized_data)
        
        # Step 5: Perform impact analysis
        print("\n[Step 5] Performing impact analysis...")
        impact_data = self._analyze_impact(features)
        
        # Step 6: Generate summary
        summary = self._generate_summary(features, impact_data)
        
        print("\n" + "=" * 70)
        print("Workflow Complete!")
        print("=" * 70)
        
        return summary
    
    def _execute_cucumber_tests(self):
        """
        Execute Cucumber tests via Maven/Gradle.
        
        In real implementation:
        - Run: mvn test -Dcucumber.plugin=json:target/cucumber-report.json
        - Or: gradle test -Dcucumber.plugin=json:build/cucumber-report.json
        """
        print("   → Running Maven/Gradle test execution...")
        print("   → Command: mvn test -Dcucumber.plugin=json:target/cucumber-report.json")
        print("   ✅ Tests executed (simulated)")
    
    def _parse_results(self) -> List[FeatureResult]:
        """Parse Cucumber JSON report using our parser."""
        if not self.cucumber_report_path.exists():
            print(f"   ⚠️  Report not found at {self.cucumber_report_path}")
            print("   → Using example report for demonstration")
            
            # Use example report for demo
            example_report = self.project_root / "examples" / "sample-cucumber-report.json"
            if example_report.exists():
                features = parse_cucumber_json(example_report)
            else:
                raise FileNotFoundError("No report available for parsing")
        else:
            features = parse_cucumber_json(self.cucumber_report_path)
        
        print(f"   ✅ Parsed {len(features)} feature(s)")
        return features
    
    def _normalize_results(self, features: List[FeatureResult]) -> Dict:
        """
        Normalize parsed results to CrossBridge database models.
        
        This is where FeatureResult/ScenarioResult would be converted to
        database entities for persistence.
        """
        normalized = {
            "test_run_id": "run_20250330_143022",  # Generated test run ID
            "features": [],
            "scenarios": [],
            "steps": []
        }
        
        for feature in features:
            # Normalize feature
            feature_record = {
                "name": feature.name,
                "uri": feature.uri,
                "description": feature.description,
                "tags": feature.tags,
                "overall_status": feature.overall_status,
                "total_scenarios": feature.total_scenarios,
                "passed_scenarios": feature.passed_scenarios,
                "failed_scenarios": feature.failed_scenarios,
                "skipped_scenarios": feature.skipped_scenarios,
            }
            normalized["features"].append(feature_record)
            
            # Normalize scenarios
            for scenario in feature.scenarios:
                scenario_record = {
                    "feature_uri": feature.uri,
                    "feature_name": feature.name,
                    "scenario_name": scenario.scenario,
                    "scenario_type": scenario.scenario_type,
                    "line": scenario.line,
                    "tags": scenario.tags,
                    "status": scenario.status,
                    "duration_ns": scenario.total_duration_ns,
                    "step_count": len(scenario.steps),
                    "failed_step_count": len(scenario.failed_steps),
                }
                normalized["scenarios"].append(scenario_record)
                
                # Normalize steps
                for step in scenario.steps:
                    step_record = {
                        "scenario_name": scenario.scenario,
                        "step_name": step.name,
                        "status": step.status,
                        "duration_ns": step.duration_ns,
                        "error_message": step.error_message,
                    }
                    normalized["steps"].append(step_record)
        
        print(f"   ✅ Normalized {len(normalized['features'])} features, "
              f"{len(normalized['scenarios'])} scenarios, "
              f"{len(normalized['steps'])} steps")
        
        return normalized
    
    def _persist_results(self, normalized_data: Dict):
        """
        Persist normalized results to CrossBridge database.
        
        In real implementation:
        - Use ORM (SQLAlchemy) to insert records
        - Link to test run, build ID, git commit
        - Enable historical trend analysis
        """
        print("   → Inserting feature records...")
        print(f"   → Inserted {len(normalized_data['features'])} feature records")
        
        print("   → Inserting scenario records...")
        print(f"   → Inserted {len(normalized_data['scenarios'])} scenario records")
        
        print("   → Inserting step records...")
        print(f"   → Inserted {len(normalized_data['steps'])} step records")
        
        print("   ✅ All results persisted to database (simulated)")
    
    def _analyze_impact(self, features: List[FeatureResult]) -> Dict:
        """
        Perform impact analysis using file/line references.
        
        In real implementation:
        - Map scenarios to source code files
        - Detect changed files in git
        - Identify impacted tests
        - Enable intelligent test selection
        """
        impact_data = {
            "total_tests": 0,
            "tests_by_tag": {},
            "tests_by_file": {},
            "failed_test_locations": []
        }
        
        for feature in features:
            # Map tests by file
            if feature.uri not in impact_data["tests_by_file"]:
                impact_data["tests_by_file"][feature.uri] = []
            
            for scenario in feature.scenarios:
                impact_data["total_tests"] += 1
                
                # Collect test locations
                test_location = {
                    "file": feature.uri,
                    "line": scenario.line,
                    "scenario": scenario.scenario,
                    "status": scenario.status
                }
                impact_data["tests_by_file"][feature.uri].append(test_location)
                
                # Track failed test locations for impact analysis
                if scenario.status == "failed":
                    impact_data["failed_test_locations"].append(test_location)
                
                # Aggregate by tags
                for tag in scenario.tags:
                    if tag not in impact_data["tests_by_tag"]:
                        impact_data["tests_by_tag"][tag] = {"total": 0, "passed": 0, "failed": 0}
                    
                    impact_data["tests_by_tag"][tag]["total"] += 1
                    if scenario.status == "passed":
                        impact_data["tests_by_tag"][tag]["passed"] += 1
                    elif scenario.status == "failed":
                        impact_data["tests_by_tag"][tag]["failed"] += 1
        
        print(f"   ✅ Impact analysis complete")
        print(f"   → Mapped {impact_data['total_tests']} tests")
        print(f"   → Identified {len(impact_data['failed_test_locations'])} failed tests")
        print(f"   → Analyzed {len(impact_data['tests_by_tag'])} unique tags")
        
        return impact_data
    
    def _generate_summary(self, features: List[FeatureResult], impact_data: Dict) -> Dict:
        """Generate execution summary and recommendations."""
        total_scenarios = sum(f.total_scenarios for f in features)
        total_passed = sum(f.passed_scenarios for f in features)
        total_failed = sum(f.failed_scenarios for f in features)
        total_skipped = sum(f.skipped_scenarios for f in features)
        
        pass_rate = (total_passed / total_scenarios * 100) if total_scenarios > 0 else 0
        
        summary = {
            "execution": {
                "total_features": len(features),
                "total_scenarios": total_scenarios,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "pass_rate": pass_rate
            },
            "impact": impact_data,
            "recommendations": self._generate_recommendations(features, impact_data)
        }
        
        # Print summary
        print("\n" + "-" * 70)
        print("Execution Summary")
        print("-" * 70)
        print(f"Features:   {len(features)}")
        print(f"Scenarios:  {total_scenarios} total")
        print(f"  ✅ Passed:   {total_passed}")
        print(f"  ❌ Failed:   {total_failed}")
        print(f"  ⏭️  Skipped:  {total_skipped}")
        print(f"Pass Rate:  {pass_rate:.1f}%")
        
        print("\n" + "-" * 70)
        print("Tag Analysis")
        print("-" * 70)
        for tag, stats in impact_data["tests_by_tag"].items():
            tag_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"{tag:20} {stats['total']:3} tests  ({tag_pass_rate:.0f}% pass rate)")
        
        if summary["recommendations"]:
            print("\n" + "-" * 70)
            print("Recommendations")
            print("-" * 70)
            for i, rec in enumerate(summary["recommendations"], 1):
                print(f"{i}. {rec}")
        
        return summary
    
    def _generate_recommendations(self, features: List[FeatureResult], impact_data: Dict) -> List[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []
        
        # Check for failed critical tests
        critical_tag_stats = impact_data["tests_by_tag"].get("@critical", {})
        if critical_tag_stats.get("failed", 0) > 0:
            recommendations.append(
                f"⚠️  {critical_tag_stats['failed']} critical test(s) failed - requires immediate attention"
            )
        
        # Check for consistent failures in specific features
        failed_features = [f for f in features if f.failed_scenarios > 0]
        if failed_features:
            recommendations.append(
                f"🔍 Investigate {len(failed_features)} feature(s) with failures"
            )
        
        # Suggest running smoke tests on next commit
        smoke_tag_stats = impact_data["tests_by_tag"].get("@smoke", {})
        if smoke_tag_stats and smoke_tag_stats["passed"] == smoke_tag_stats["total"]:
            recommendations.append(
                "✅ All smoke tests passed - safe to run full regression suite"
            )
        
        return recommendations


def main():
    """Run the integration example."""
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create integration instance
    integration = CrossBridgeCucumberIntegration(project_root)
    
    # Run full workflow
    summary = integration.execute_and_analyze()
    
    print("\n" + "=" * 70)
    print("Integration Example Complete")
    print("=" * 70)
    print("\nThis demonstrates how the Cucumber JSON parser integrates with")
    print("the CrossBridge platform to enable:")
    print("  • Test execution tracking")
    print("  • Result persistence")
    print("  • Impact analysis")
    print("  • Intelligent test selection")
    print("  • Historical trend analysis")


if __name__ == "__main__":
    main()
