"""
Example usage of Cucumber JSON Parser.

This demonstrates how to parse Cucumber JSON reports and extract test results.
"""

from pathlib import Path
from adapters.selenium_bdd_java import (
    parse_cucumber_json,
    parse_multiple_cucumber_reports,
)


def demo_basic_parsing():
    """Demo: Parse a single Cucumber JSON report."""
    print("=" * 60)
    print("Demo: Basic Cucumber JSON Parsing")
    print("=" * 60)
    
    # Example: Parse a report file
    report_path = "target/cucumber-report.json"
    
    # Check if file exists (for demo purposes)
    if not Path(report_path).exists():
        print(f"Note: {report_path} not found. This is a demonstration.")
        print("In real usage, provide path to actual cucumber-report.json\n")
        return
    
    # Parse the report
    features = parse_cucumber_json(report_path)
    
    # Display results
    print(f"\nParsed {len(features)} feature(s):\n")
    
    for feature in features:
        print(f"📋 Feature: {feature.name}")
        print(f"   File: {feature.uri}")
        print(f"   Status: {feature.overall_status}")
        print(f"   Scenarios: {feature.total_scenarios} total, "
              f"{feature.passed_scenarios} passed, "
              f"{feature.failed_scenarios} failed, "
              f"{feature.skipped_scenarios} skipped")
        
        if feature.tags:
            print(f"   Tags: {', '.join(feature.tags)}")
        
        print()
        
        # Show scenarios
        for scenario in feature.scenarios:
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(scenario.status, "❓")
            
            print(f"   {status_emoji} Scenario: {scenario.scenario}")
            print(f"      Type: {scenario.scenario_type}")
            print(f"      Line: {scenario.line}")
            print(f"      Status: {scenario.status}")
            print(f"      Duration: {scenario.total_duration_ns / 1_000_000:.2f}ms")
            
            if scenario.tags:
                print(f"      Tags: {', '.join(scenario.tags)}")
            
            # Show failed steps if any
            if scenario.failed_steps:
                print(f"      Failed steps:")
                for step in scenario.failed_steps:
                    print(f"         - {step.name}")
                    if step.error_message:
                        print(f"           Error: {step.error_message}")
            
            print()


def demo_multiple_reports():
    """Demo: Parse multiple Cucumber reports."""
    print("=" * 60)
    print("Demo: Parsing Multiple Reports")
    print("=" * 60)
    
    # Example: Parse reports from multiple modules
    report_paths = [
        "module-a/target/cucumber.json",
        "module-b/target/cucumber.json",
        "module-c/target/cucumber.json",
    ]
    
    print(f"\nParsing {len(report_paths)} report(s)...\n")
    
    # Parse all reports (skips missing files automatically)
    all_features = parse_multiple_cucumber_reports(report_paths)
    
    print(f"Total features parsed: {len(all_features)}")
    
    # Aggregate statistics
    total_scenarios = sum(f.total_scenarios for f in all_features)
    total_passed = sum(f.passed_scenarios for f in all_features)
    total_failed = sum(f.failed_scenarios for f in all_features)
    total_skipped = sum(f.skipped_scenarios for f in all_features)
    
    print("\nAggregate Statistics:")
    print(f"  Total scenarios: {total_scenarios}")
    print(f"  ✅ Passed: {total_passed}")
    print(f"  ❌ Failed: {total_failed}")
    print(f"  ⏭️  Skipped: {total_skipped}")
    
    if total_scenarios > 0:
        pass_rate = (total_passed / total_scenarios) * 100
        print(f"  Pass rate: {pass_rate:.1f}%")


def demo_scenario_analysis():
    """Demo: Analyze specific scenarios."""
    print("=" * 60)
    print("Demo: Scenario Analysis")
    print("=" * 60)
    
    report_path = "target/cucumber-report.json"
    
    if not Path(report_path).exists():
        print(f"Note: {report_path} not found. This is a demonstration.\n")
        return
    
    features = parse_cucumber_json(report_path)
    
    print("\nScenarios with @smoke tag:\n")
    
    for feature in features:
        for scenario in feature.scenarios:
            if "@smoke" in scenario.tags:
                print(f"  {scenario.feature} > {scenario.scenario}")
                print(f"    Status: {scenario.status}")
                print(f"    Steps: {len(scenario.steps)}")
                print()
    
    print("\nFailed Scenarios:\n")
    
    for feature in features:
        for scenario in feature.scenarios:
            if scenario.status == "failed":
                print(f"  ❌ {feature.name} > {scenario.scenario}")
                print(f"     Location: {scenario.uri}:{scenario.line}")
                
                # Show which steps failed
                for step in scenario.failed_steps:
                    print(f"     Failed: {step.name}")
                    if step.error_message:
                        # Show first line of error
                        error_line = step.error_message.split('\n')[0]
                        print(f"     Error: {error_line}")
                
                print()


def demo_integration_example():
    """Demo: Integration with CrossBridge platform."""
    print("=" * 60)
    print("Demo: CrossBridge Platform Integration")
    print("=" * 60)
    
    print("\nTypical workflow:\n")
    print("1. Execute Cucumber tests via Maven/Gradle")
    print("2. Generate cucumber-report.json")
    print("3. Parse report using this adapter")
    print("4. Normalize results to framework-neutral models")
    print("5. Persist to database (next phase)")
    print("6. Enable impact analysis & intelligent test selection")
    
    print("\nExample code:")
    print("""
    from adapters.selenium_bdd_java import parse_cucumber_json
    
    # After test execution
    features = parse_cucumber_json("target/cucumber-report.json")
    
    # Features are now in neutral format
    for feature in features:
        for scenario in feature.scenarios:
            # Ready for database persistence
            db.save_scenario_result(
                feature_uri=feature.uri,
                scenario_name=scenario.scenario,
                status=scenario.status,
                tags=scenario.tags,
                duration_ns=scenario.total_duration_ns
            )
    """)


def main():
    """Run all demos."""
    demo_basic_parsing()
    print("\n")
    demo_multiple_reports()
    print("\n")
    demo_scenario_analysis()
    print("\n")
    demo_integration_example()


if __name__ == "__main__":
    main()
