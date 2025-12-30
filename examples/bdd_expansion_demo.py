"""
Demonstration of BDD Scenario Outline expansion.

Run this file to see the expansion in action:
    python examples/bdd_expansion_demo.py
"""
from adapters.common.bdd import (
    ScenarioOutline,
    ExamplesTable,
    ExpandedScenario,
    expand_scenario_outline,
    map_expanded_scenario_to_intent
)


def demo_basic_expansion():
    """Demonstrate basic scenario outline expansion."""
    print("=" * 80)
    print("DEMO: Basic Scenario Outline Expansion")
    print("=" * 80)
    print()
    
    # Define scenario outline
    outline = ScenarioOutline(
        name="User logs in",
        steps=(
            "Given user is on login page",
            "When user logs in with <username> and <password>",
            "Then login should be <result>"
        ),
        tags=("auth", "smoke")
    )
    
    # Define examples table
    examples = ExamplesTable(
        headers=("username", "password", "result"),
        rows=(
            ("admin", "admin123", "success"),
            ("user", "wrong123", "failure"),
            ("guest", "guest123", "success")
        )
    )
    
    print("📝 INPUT - Scenario Outline:")
    print(f"   Name: {outline.name}")
    print(f"   Tags: {', '.join(outline.tags)}")
    print(f"   Steps:")
    for step in outline.steps:
        print(f"      - {step}")
    print()
    
    print("📋 INPUT - Examples Table:")
    print(f"   Headers: {' | '.join(examples.headers)}")
    print(f"   Rows:")
    for row in examples.rows:
        print(f"      - {' | '.join(str(v) for v in row)}")
    print()
    
    # Expand
    print("🔄 EXPANDING...")
    scenarios = expand_scenario_outline(outline, examples)
    print()
    
    print(f"✅ OUTPUT - {len(scenarios)} Expanded Scenarios:")
    print()
    for i, scenario in enumerate(scenarios, 1):
        print(f"   [{i}] {scenario.name}")
        print(f"       Tags: {', '.join(scenario.tags)}")
        print(f"       Parameters: {scenario.parameters}")
        print(f"       Steps:")
        for step in scenario.steps:
            print(f"          - {step}")
        print()


def demo_intent_mapping():
    """Demonstrate conversion to IntentModel."""
    print("=" * 80)
    print("DEMO: Expanded Scenario → IntentModel Mapping")
    print("=" * 80)
    print()
    
    # Create expanded scenario
    scenario = ExpandedScenario(
        name="User logs in [admin123/admin]",
        steps=(
            "Given user is on login page",
            "When user logs in with admin and admin123",
            "Then login should be success"
        ),
        parameters={"username": "admin", "password": "admin123", "result": "success"},
        tags=("auth", "smoke"),
        original_outline_name="User logs in"
    )
    
    print("📝 INPUT - ExpandedScenario:")
    print(f"   Name: {scenario.name}")
    print(f"   Original Outline: {scenario.original_outline_name}")
    print(f"   Parameters: {scenario.parameters}")
    print(f"   Tags: {', '.join(scenario.tags)}")
    print(f"   Steps:")
    for step in scenario.steps:
        print(f"      - {step}")
    print()
    
    # Map to intent
    print("🔄 MAPPING TO INTENTMODEL...")
    intent = map_expanded_scenario_to_intent(scenario)
    print()
    
    print("✅ OUTPUT - IntentModel:")
    print(f"   Test Name: {intent.test_name}")
    print(f"   Intent: {intent.intent}")
    print(f"   Steps ({len(intent.steps)}):")
    for step in intent.steps:
        print(f"      - {step.action}: {step.description}")
        if step.target:
            print(f"        Target: {step.target}")
    print(f"   Assertions ({len(intent.assertions)}):")
    for assertion in intent.assertions:
        print(f"      - Type: {assertion.type.value}")
        print(f"        Expected: {assertion.expected}")
    print()


def demo_complex_scenario():
    """Demonstrate complex scenario with multiple placeholders."""
    print("=" * 80)
    print("DEMO: Complex Scenario with Multiple Parameters")
    print("=" * 80)
    print()
    
    outline = ScenarioOutline(
        name="Search products",
        steps=(
            "Given user is on <page> page",
            "When user searches for <query> in <category>",
            "Then <count> results should be displayed",
            "And results should contain <keyword>"
        ),
        tags=("search", "e2e")
    )
    
    examples = ExamplesTable(
        headers=("page", "query", "category", "count", "keyword"),
        rows=(
            ("home", "laptop", "electronics", "25", "Dell"),
            ("catalog", "book", "media", "100", "Python"),
            ("home", "chair", "furniture", "15", "Office")
        )
    )
    
    print("📝 Complex Scenario Outline with 5 parameters")
    print()
    
    scenarios = expand_scenario_outline(outline, examples)
    
    print(f"✅ Generated {len(scenarios)} test scenarios:")
    print()
    for i, scenario in enumerate(scenarios, 1):
        print(f"   [{i}] {scenario.name}")
        print(f"       First step: {scenario.steps[0]}")
        print(f"       Last step: {scenario.steps[-1]}")
        print()


def main():
    """Run all demos."""
    demo_basic_expansion()
    print("\n" * 2)
    
    demo_intent_mapping()
    print("\n" * 2)
    
    demo_complex_scenario()
    
    print("=" * 80)
    print("✅ All demos completed successfully!")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("  • Each example row becomes a separate test")
    print("  • Placeholders are replaced deterministically")
    print("  • Parameter names sorted alphabetically in test names")
    print("  • Tags inherited from outline")
    print("  • IntentModel ready for migration/AI processing")
    print()


if __name__ == "__main__":
    main()
