"""
Enhanced Migration Demo - Multiple Target Frameworks

Demonstrates Java Selenium BDD migration to:
1. Python Playwright with pytest-bdd
2. Python Playwright with Robot Framework
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from adapters.selenium_bdd_java.step_definition_parser import JavaStepDefinitionParser
from migration.orchestrator import UnifiedMigrationOrchestrator


def print_section(title: str):
    """Print a formatted section header"""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


def main():
    """Run the enhanced migration demo"""
    
    print_section("Java Selenium BDD → Multiple Target Migration Demo")
    
    # 1. Read Java step definitions
    java_file = Path(__file__).parent / "java_source" / "LoginSteps.java"
    
    print(f"📂 Reading Java file: {java_file.name}")
    with open(java_file, "r") as f:
        java_code = f.read()
    
    print(f"   ✓ Read {len(java_code)} characters")
    print()
    
    # 2. Parse step definitions
    print("🔍 Parsing Java step definitions...")
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(java_code, str(java_file))
    step_defs = result.step_definitions
    
    print(f"   ✓ Found {len(step_defs)} step definitions:")
    for step in step_defs:
        print(f"      - @{step.step_type}: {step.pattern_text}")
    print()
    
    # 3. Show available targets
    orchestrator = UnifiedMigrationOrchestrator()
    targets = orchestrator.get_supported_targets()
    
    print("🎯 Available Migration Targets:")
    for i, target in enumerate(targets, 1):
        info = orchestrator.get_target_info(target)
        print(f"   {i}. {info['name']}")
        print(f"      Description: {info['description']}")
        print(f"      Framework: {info['framework']}")
        print(f"      Browser: {info['browser_library']}")
        print(f"      Install: {info['install_command']}")
        print()
    
    # 4. Migrate to pytest-bdd
    print_section("Migration Option 1: pytest-bdd")
    
    pytest_output = Path(__file__).parent / "output_pytest"
    
    print("⚙️  Migrating to pytest-bdd...")
    pytest_result = orchestrator.migrate(
        step_defs,
        pytest_output,
        target="pytest-bdd",
        mode="assistive"
    )
    
    print(f"   ✓ Migration complete!")
    print(f"   • Output: {pytest_result['output_dir']}")
    print(f"   • Step Definitions: {pytest_result['step_definitions']}")
    print(f"   • Page Objects: {pytest_result['page_objects']}")
    print()
    print("   📁 Generated Files:")
    for category, files in pytest_result['files'].items():
        print(f"      {category}:")
        for file in files:
            print(f"         - {file}")
    print()
    
    # Show sample pytest-bdd code
    print("   📄 Sample pytest-bdd Code:")
    print("   " + "-" * 60)
    sample_po = pytest_output / "page_objects" / "login_page.py"
    if sample_po.exists():
        with open(sample_po, "r") as f:
            lines = f.readlines()[:15]
            for line in lines:
                print(f"   {line.rstrip()}")
    print("   " + "-" * 60)
    print()
    
    # 5. Migrate to Robot Framework
    print_section("Migration Option 2: Robot Framework")
    
    robot_output = Path(__file__).parent / "output_robot"
    
    print("⚙️  Migrating to Robot Framework...")
    robot_result = orchestrator.migrate(
        step_defs,
        robot_output,
        target="robot-framework"
    )
    
    print(f"   ✓ Migration complete!")
    print(f"   • Output: {robot_result['output_dir']}")
    print(f"   • Test Cases: {robot_result['test_cases']}")
    print(f"   • Resources: {robot_result['resources']}")
    print()
    print("   📁 Generated Files:")
    for category, files in robot_result['files'].items():
        print(f"      {category}:")
        for file in files:
            print(f"         - {file}")
    print()
    
    # Show sample Robot Framework code
    print("   📄 Sample Robot Framework Code:")
    print("   " + "-" * 60)
    sample_resource = robot_output / "resources" / "LoginPage.robot"
    if sample_resource.exists():
        with open(sample_resource, "r") as f:
            lines = f.readlines()[:20]
            for line in lines:
                print(f"   {line.rstrip()}")
    print("   " + "-" * 60)
    print()
    
    # 6. Comparison
    print_section("Framework Comparison")
    
    print("pytest-bdd:")
    print("  ✓ Python-native, leverage pytest ecosystem")
    print("  ✓ Type hints and IDE support")
    print("  ✓ Familiar to Python developers")
    print("  ✓ Async/sync Playwright API")
    print()
    
    print("Robot Framework:")
    print("  ✓ Keyword-driven, non-programmer friendly")
    print("  ✓ Built-in reporting and logs")
    print("  ✓ Tag-based test execution")
    print("  ✓ Large ecosystem of libraries")
    print()
    
    # 7. Summary
    print_section("✅ Migration Complete!")
    
    print("Results:")
    print(f"  • Source: {len(step_defs)} Java Cucumber steps")
    print(f"  • Target 1 (pytest-bdd): {pytest_result['step_definitions']} steps, {pytest_result['page_objects']} Page Objects")
    print(f"  • Target 2 (Robot): {robot_result['test_cases']} test cases, {robot_result['resources']} resources")
    print()
    
    print("Next Steps:")
    print()
    print("For pytest-bdd:")
    print(f"  1. cd {pytest_output}")
    print("  2. pip install pytest pytest-bdd playwright")
    print("  3. playwright install")
    print("  4. pytest")
    print()
    
    print("For Robot Framework:")
    print(f"  1. cd {robot_output}")
    print("  2. pip install robotframework robotframework-browser")
    print("  3. rfbrowser init")
    print("  4. robot tests/")
    print()


if __name__ == "__main__":
    main()
