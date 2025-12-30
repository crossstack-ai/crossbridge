"""
Quick verification script for Cucumber JSON Parser.

This script tests the parser with sample data to verify the implementation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adapters.selenium_bdd_java import (
    parse_cucumber_json,
    FeatureResult,
    ScenarioResult,
    StepResult
)


def verify_parser():
    """Verify the Cucumber JSON parser works correctly."""
    print("=" * 70)
    print("Cucumber JSON Parser Verification")
    print("=" * 70)
    
    # Parse the sample report
    sample_report = project_root / "examples" / "sample-cucumber-report.json"
    
    if not sample_report.exists():
        print(f"❌ Sample report not found: {sample_report}")
        return False
    
    print(f"\n📄 Parsing: {sample_report.name}\n")
    
    try:
        features = parse_cucumber_json(sample_report)
        print(f"✅ Successfully parsed {len(features)} feature(s)\n")
    except Exception as e:
        print(f"❌ Parser failed: {e}")
        return False
    
    # Verify the results
    print("-" * 70)
    print("Verification Results:")
    print("-" * 70)
    
    all_checks_passed = True
    
    # Check 1: Number of features
    expected_features = 2
    if len(features) == expected_features:
        print(f"✅ Feature count: {len(features)} (expected: {expected_features})")
    else:
        print(f"❌ Feature count: {len(features)} (expected: {expected_features})")
        all_checks_passed = False
    
    # Check 2: Login Feature
    login_feature = features[0]
    if login_feature.name == "Login Feature":
        print(f"✅ First feature name: '{login_feature.name}'")
    else:
        print(f"❌ First feature name: '{login_feature.name}' (expected: 'Login Feature')")
        all_checks_passed = False
    
    # Check 3: Login Feature scenarios
    expected_scenarios = 2
    if len(login_feature.scenarios) == expected_scenarios:
        print(f"✅ Login feature scenarios: {len(login_feature.scenarios)} (expected: {expected_scenarios})")
    else:
        print(f"❌ Login feature scenarios: {len(login_feature.scenarios)} (expected: {expected_scenarios})")
        all_checks_passed = False
    
    # Check 4: Feature tags
    if "@smoke" in login_feature.tags:
        print(f"✅ Feature tags contain: @smoke")
    else:
        print(f"❌ Feature tags missing: @smoke (got: {login_feature.tags})")
        all_checks_passed = False
    
    # Check 5: First scenario status (should be passed)
    first_scenario = login_feature.scenarios[0]
    if first_scenario.status == "passed":
        print(f"✅ First scenario status: {first_scenario.status}")
    else:
        print(f"❌ First scenario status: {first_scenario.status} (expected: passed)")
        all_checks_passed = False
    
    # Check 6: Second scenario status (should be failed)
    second_scenario = login_feature.scenarios[1]
    if second_scenario.status == "failed":
        print(f"✅ Second scenario status: {second_scenario.status}")
    else:
        print(f"❌ Second scenario status: {second_scenario.status} (expected: failed)")
        all_checks_passed = False
    
    # Check 7: Failed steps detection
    failed_steps = second_scenario.failed_steps
    if len(failed_steps) == 1:
        print(f"✅ Failed steps detected: {len(failed_steps)}")
    else:
        print(f"❌ Failed steps detected: {len(failed_steps)} (expected: 1)")
        all_checks_passed = False
    
    # Check 8: Error message captured
    if failed_steps and failed_steps[0].error_message:
        print(f"✅ Error message captured: '{failed_steps[0].error_message[:50]}...'")
    else:
        print(f"❌ Error message not captured")
        all_checks_passed = False
    
    # Check 9: Scenario outline type
    checkout_feature = features[1]
    outline_scenario = checkout_feature.scenarios[0]
    if outline_scenario.scenario_type == "scenario_outline":
        print(f"✅ Scenario outline type detected")
    else:
        print(f"❌ Scenario type: {outline_scenario.scenario_type} (expected: scenario_outline)")
        all_checks_passed = False
    
    # Check 10: Duration calculation
    total_duration = first_scenario.total_duration_ns
    expected_duration = 100000000 + 120000000 + 80000000
    if total_duration == expected_duration:
        print(f"✅ Duration calculation: {total_duration}ns")
    else:
        print(f"❌ Duration calculation: {total_duration}ns (expected: {expected_duration}ns)")
        all_checks_passed = False
    
    # Check 11: Feature statistics
    if login_feature.passed_scenarios == 1 and login_feature.failed_scenarios == 1:
        print(f"✅ Feature statistics: {login_feature.passed_scenarios} passed, {login_feature.failed_scenarios} failed")
    else:
        print(f"❌ Feature statistics incorrect")
        all_checks_passed = False
    
    # Check 12: Overall feature status
    if login_feature.overall_status == "failed":
        print(f"✅ Feature overall status: {login_feature.overall_status}")
    else:
        print(f"❌ Feature overall status: {login_feature.overall_status} (expected: failed)")
        all_checks_passed = False
    
    print("\n" + "-" * 70)
    print("Detailed Feature Report:")
    print("-" * 70)
    
    for i, feature in enumerate(features, 1):
        print(f"\n{i}. 📋 Feature: {feature.name}")
        print(f"   📁 File: {feature.uri}")
        print(f"   🏷️  Tags: {', '.join(feature.tags) if feature.tags else 'None'}")
        print(f"   📊 Status: {feature.overall_status}")
        print(f"   📈 Scenarios: {feature.total_scenarios} total, "
              f"{feature.passed_scenarios} ✅, "
              f"{feature.failed_scenarios} ❌, "
              f"{feature.skipped_scenarios} ⏭️")
        
        for j, scenario in enumerate(feature.scenarios, 1):
            status_symbol = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(scenario.status, "❓")
            
            print(f"\n   {i}.{j} {status_symbol} Scenario: {scenario.scenario}")
            print(f"        Type: {scenario.scenario_type}")
            print(f"        Line: {scenario.line}")
            print(f"        Tags: {', '.join(scenario.tags) if scenario.tags else 'None'}")
            print(f"        Steps: {len(scenario.steps)}")
            print(f"        Duration: {scenario.total_duration_ns / 1_000_000:.2f}ms")
            
            if scenario.failed_steps:
                print(f"        Failed steps:")
                for step in scenario.failed_steps:
                    print(f"          - {step.name}")
                    if step.error_message:
                        error_preview = step.error_message[:60]
                        print(f"            Error: {error_preview}...")
    
    print("\n" + "=" * 70)
    
    if all_checks_passed:
        print("✅ All verification checks PASSED!")
        print("=" * 70)
        return True
    else:
        print("❌ Some verification checks FAILED!")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = verify_parser()
    sys.exit(0 if success else 1)
