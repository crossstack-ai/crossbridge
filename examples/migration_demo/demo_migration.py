"""
Demonstration of Java Selenium BDD → Python Playwright Migration

This script demonstrates the complete migration pipeline:
1. Parse Java step definitions
2. Extract semantic intent
3. Generate Playwright Page Objects and pytest-bdd steps
4. Write organized Python project
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from adapters.selenium_bdd_java.step_definition_parser import (
    JavaStepDefinitionParser,
    StepDefinitionIntent
)
from migration.generators.playwright_generator import MigrationOrchestrator


def main():
    """Run the migration demo"""
    
    print("=" * 70)
    print("Java Selenium BDD → Python Playwright Migration Demo")
    print("=" * 70)
    print()
    
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
    
    # 3. Show extracted Page Object calls
    print("📦 Extracted Page Object Calls:")
    for step in step_defs:
        if step.page_object_calls:
            print(f"   {step.method_name}:")
            for call in step.page_object_calls:
                print(f"      → {call.page_object_name}.{call.method_name}()")
    print()
    
    # 4. Generate Playwright code
    print("⚙️  Generating Playwright code...")
    orchestrator = MigrationOrchestrator()
    output_dir = Path(__file__).parent / "python_output"
    
    test_suite = orchestrator.migrate_step_definitions(
        step_defs,
        output_dir,
        mode="assistive"
    )
    
    print(f"   ✓ Generated {len(test_suite.page_objects)} Page Objects:")
    for po in test_suite.page_objects:
        print(f"      - {po.class_name}")
        print(f"         Methods: {', '.join(po.methods.keys())}")
    print()
    
    print(f"   ✓ Generated {len(test_suite.step_definitions)} Step Definitions")
    print()
    
    # 5. Write files
    print("💾 Writing migration output...")
    orchestrator.write_migration_output(test_suite, output_dir)
    
    print(f"   ✓ Files written to: {output_dir}")
    print(f"      📁 page_objects/")
    for po in test_suite.page_objects:
        filename = orchestrator._to_snake_case(po.class_name) + ".py"
        print(f"         - {filename}")
    print(f"      📁 step_definitions/")
    print(f"         - test_steps.py")
    print(f"      📄 conftest.py")
    print(f"      📄 README.md")
    print()
    
    # 6. Show sample generated code
    print("=" * 70)
    print("Sample Generated Code - LoginPage")
    print("=" * 70)
    print()
    
    login_page = next(po for po in test_suite.page_objects if po.class_name == "LoginPage")
    from migration.generators.playwright_generator import PlaywrightPageObjectGenerator
    
    generator = PlaywrightPageObjectGenerator()
    code = generator.render_page_object(login_page)
    
    # Show first 30 lines
    lines = code.split('\n')[:30]
    for line in lines:
        print(line)
    print("...")
    print()
    
    # 7. Success message
    print("=" * 70)
    print("✅ Migration Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review generated code in:", output_dir)
    print("2. Install dependencies: pip install pytest pytest-bdd playwright")
    print("3. Run tests: pytest", output_dir)
    print()
    print("Migration Statistics:")
    print(f"  - Step Definitions: {len(step_defs)}")
    print(f"  - Page Objects: {len(test_suite.page_objects)}")
    print(f"  - Total Methods: {sum(len(po.methods) for po in test_suite.page_objects)}")
    print()


if __name__ == "__main__":
    main()
