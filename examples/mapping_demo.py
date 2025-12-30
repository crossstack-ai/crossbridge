#!/usr/bin/env python3
"""
Interactive demonstration of the step-to-code-path mapping system.

This demo shows how adapters register signals and how the resolver
maps BDD steps to page objects, methods, and code paths.

Usage:
    python examples/mapping_demo.py
"""

from adapters.common.mapping import (
    StepSignal,
    CodeReference,
    StepMapping,
    SignalType,
    StepSignalRegistry,
    StepMappingResolver,
)


def demo_basic_registration():
    """Demo: Register signals and resolve a step."""
    print("=" * 80)
    print("DEMO 1: Basic Signal Registration and Resolution")
    print("=" * 80)
    print()

    # Create registry
    registry = StepSignalRegistry()
    
    # Adapter registers signals during test discovery
    registry.register_signal(
        "user logs in with {username} and {password}",
        StepSignal(
            type=SignalType.PAGE_OBJECT,
            value="LoginPage",
            metadata={"file": "pages/login_page.py"}
        )
    )
    
    registry.register_signal(
        "user logs in",
        StepSignal(
            type=SignalType.METHOD,
            value="LoginPage.login",
            metadata={"parameters": ["username", "password"]}
        )
    )
    
    registry.register_signal(
        "user logs in",
        StepSignal(
            type=SignalType.CODE_PATH,
            value="pages/login_page.py::LoginPage.login",
            metadata={"line": 42}
        )
    )
    
    print(f"✅ Registered {registry.count()} signal patterns\n")
    
    # Resolve a step
    resolver = StepMappingResolver(registry)
    mapping = resolver.resolve_step("Given user logs in with admin and password123")
    
    print(f"Step: {mapping.step}")
    print(f"Page Objects: {mapping.page_objects}")
    print(f"Methods: {mapping.methods}")
    print(f"Code Paths: {mapping.code_paths}")
    print(f"Signals: {len(mapping.signals)} matched")
    print()


def demo_multi_signal_resolution():
    """Demo: Multiple signals for complex steps."""
    print("=" * 80)
    print("DEMO 2: Multi-Signal Resolution (UI + API)")
    print("=" * 80)
    print()

    registry = StepSignalRegistry()
    
    # Complex step with multiple signals
    registry.register_signal(
        "user creates an order",
        StepSignal(
            type=SignalType.PAGE_OBJECT,
            value="OrderPage",
            metadata={"type": "ui"}
        )
    )
    
    registry.register_signal(
        "user creates an order",
        StepSignal(
            type=SignalType.PAGE_OBJECT,
            value="OrderAPI",
            metadata={"type": "api"}
        )
    )
    
    registry.register_signal(
        "user creates an order",
        StepSignal(
            type=SignalType.METHOD,
            value="OrderPage.createOrder",
            metadata={}
        )
    )
    
    registry.register_signal(
        "user creates an order",
        StepSignal(
            type=SignalType.CODE_PATH,
            value="pages/order_page.py::OrderPage.createOrder",
            metadata={"line": 87}
        )
    )
    
    registry.register_signal(
        "user creates an order",
        StepSignal(
            type=SignalType.CODE_PATH,
            value="api/order_api.py::OrderAPI.post_order",
            metadata={"line": 120}
        )
    )
    
    resolver = StepMappingResolver(registry)
    mapping = resolver.resolve_step("When user creates an order for laptop")
    
    print(f"Step: {mapping.step}")
    print(f"\nPage Objects: {mapping.page_objects}")
    print(f"Methods: {mapping.methods}")
    print(f"Code Paths:")
    for path in mapping.code_paths:
        print(f"  • {path}")
    print(f"\nTotal Signals: {len(mapping.signals)}")
    print()


def demo_contains_matching():
    """Demo: Exact vs contains matching."""
    print("=" * 80)
    print("DEMO 3: Deterministic Matching (Exact First, Then Contains)")
    print("=" * 80)
    print()

    registry = StepSignalRegistry()
    
    # Exact match signal
    registry.register_signal(
        "user clicks login button",
        StepSignal(
            type=SignalType.CODE_PATH,
            value="pages/login_page.py::LoginPage.click_login",
            metadata={"match_type": "exact"}
        )
    )
    
    # Contains match signals (broader patterns)
    registry.register_signal(
        "clicks",
        StepSignal(
            type=SignalType.METHOD,
            value="BasePage.click",
            metadata={"match_type": "contains"}
        )
    )
    
    registry.register_signal(
        "button",
        StepSignal(
            type=SignalType.PAGE_OBJECT,
            value="ButtonHelper",
            metadata={"match_type": "contains"}
        )
    )
    
    resolver = StepMappingResolver(registry)
    
    # Test exact match
    mapping_exact = resolver.resolve_step("Given user clicks login button")
    print("Exact Match:")
    print(f"  Step: {mapping_exact.step}")
    print(f"  Signals: {len(mapping_exact.signals)}")
    for signal in mapping_exact.signals:
        print(f"    • {signal.type.value}: {signal.value} (match: {signal.metadata.get('match_type', 'N/A')})")
    
    # Test contains match
    mapping_contains = resolver.resolve_step("When user clicks submit")
    print("\nContains Match:")
    print(f"  Step: {mapping_contains.step}")
    print(f"  Signals: {len(mapping_contains.signals)}")
    for signal in mapping_contains.signals:
        print(f"    • {signal.type.value}: {signal.value} (match: {signal.metadata.get('match_type', 'N/A')})")
    print()


def demo_bdd_keyword_removal():
    """Demo: BDD keyword normalization."""
    print("=" * 80)
    print("DEMO 4: BDD Keyword Removal (Given/When/Then/And/But)")
    print("=" * 80)
    print()

    registry = StepSignalRegistry()
    
    # Register without BDD keyword
    registry.register_signal(
        "dashboard is visible",
        StepSignal(
            type=SignalType.CODE_PATH,
            value="pages/dashboard_page.py::DashboardPage.is_visible",
            metadata={}
        )
    )
    
    resolver = StepMappingResolver(registry)
    
    # All these variations match the same signal
    variations = [
        "Then dashboard is visible",
        "And dashboard is visible",
        "But dashboard is visible",
        "dashboard is visible"
    ]
    
    print("Signal Registered: 'dashboard is visible'\n")
    print("Step Variations (all match):")
    for step_text in variations:
        mapping = resolver.resolve_step(step_text)
        match_indicator = "✅" if mapping.code_paths else "❌"
        print(f"  {match_indicator} {step_text:40} → {len(mapping.signals)} signal(s)")
    print()


def demo_integration_with_bdd_expansion():
    """Demo: Integration with BDD Scenario Outline expansion."""
    print("=" * 80)
    print("DEMO 5: Integration with BDD Expansion")
    print("=" * 80)
    print()

    from adapters.common.bdd import ScenarioOutline, ExamplesTable, expand_scenario_outline
    from adapters.common.bdd import map_expanded_scenario_to_intent
    
    # Create registry with signals
    registry = StepSignalRegistry()
    registry.register_signal(
        "user logs in with {username} and {password}",
        StepSignal(type=SignalType.CODE_PATH, value="pages/login_page.py::LoginPage.login", metadata={})
    )
    registry.register_signal(
        "user logs in",
        StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage", metadata={})
    )
    registry.register_signal(
        "user navigates to {page}",
        StepSignal(type=SignalType.CODE_PATH, value="pages/navigation.py::Navigation.goto", metadata={})
    )
    registry.register_signal(
        "navigates",
        StepSignal(type=SignalType.METHOD, value="Navigation.goto", metadata={})
    )
    
    # Expand scenario outline
    outline = ScenarioOutline(
        name="User Login Test",
        steps=[
            "Given user logs in with <username> and <password>",
            "When user navigates to <page>",
            "Then dashboard should display welcome message"
        ],
        tags=["@login"]
    )
    
    examples = ExamplesTable(
        headers=["username", "password", "page"],
        rows=[
            ["admin", "admin123", "dashboard"],
            ["user1", "pass456", "profile"]
        ]
    )
    
    expanded_scenarios = expand_scenario_outline(outline, examples)
    print(f"✅ Expanded {len(expanded_scenarios)} scenarios\n")
    
    # Map to intents and resolve code paths
    resolver = StepMappingResolver(registry)
    
    for i, scenario in enumerate(expanded_scenarios, 1):
        intent = map_expanded_scenario_to_intent(scenario)
        print(f"Scenario {i}: {intent.test_name}")
        
        # Resolve code paths for each step
        all_code_paths = []
        for step in intent.steps:
            mapping = resolver.resolve_step(step.action)
            all_code_paths.extend(mapping.code_paths)
        
        intent.code_paths = list(dict.fromkeys(all_code_paths))  # Deduplicate
        
        print(f"  Steps: {len(intent.steps)}")
        print(f"  Code Paths:")
        for path in intent.code_paths:
            print(f"    • {path}")
        print()


def demo_impact_analysis():
    """Demo: Impact analysis - find tests affected by code changes."""
    print("=" * 80)
    print("DEMO 6: Impact Analysis (Find Affected Tests)")
    print("=" * 80)
    print()

    # Simulate a test suite with code path mappings
    test_suite = {
        "LoginTest": ["pages/login_page.py::LoginPage.login", "pages/base_page.py::BasePage.wait"],
        "DashboardTest": ["pages/dashboard_page.py::DashboardPage.load", "pages/base_page.py::BasePage.wait"],
        "ProfileTest": ["pages/profile_page.py::ProfilePage.edit", "pages/base_page.py::BasePage.save"],
        "OrderTest": ["pages/order_page.py::OrderPage.create", "api/order_api.py::OrderAPI.post_order"]
    }
    
    # Simulate code changes
    changed_files = [
        "pages/base_page.py::BasePage.wait",
        "api/order_api.py::OrderAPI.post_order"
    ]
    
    print(f"Changed Code Paths: {len(changed_files)}")
    for path in changed_files:
        print(f"  • {path}")
    print()
    
    # Find affected tests
    affected_tests = []
    for test_name, code_paths in test_suite.items():
        if any(changed_path in code_paths for changed_path in changed_files):
            affected_tests.append(test_name)
    
    print(f"Affected Tests: {len(affected_tests)}")
    for test_name in affected_tests:
        print(f"  ⚠️  {test_name}")
        matching_paths = [path for path in test_suite[test_name] if path in changed_files]
        for path in matching_paths:
            print(f"       └─ {path}")
    print()


def demo_serialization():
    """Demo: Serialize/deserialize StepMapping for persistence."""
    print("=" * 80)
    print("DEMO 7: StepMapping Serialization (Database/File Storage)")
    print("=" * 80)
    print()

    registry = StepSignalRegistry()
    registry.register_signal(
        "user creates order",
        StepSignal(type=SignalType.CODE_PATH, value="pages/order_page.py::OrderPage.create", metadata={})
    )
    registry.register_signal(
        "user creates order",
        StepSignal(type=SignalType.PAGE_OBJECT, value="OrderPage", metadata={})
    )
    
    resolver = StepMappingResolver(registry)
    mapping = resolver.resolve_step("When user creates order for product")
    
    # Serialize to dict (for JSON/database)
    mapping_dict = mapping.to_dict()
    print("Serialized StepMapping:")
    import json
    print(json.dumps(mapping_dict, indent=2))
    print()
    
    # Deserialize back
    restored_mapping = StepMapping.from_dict(mapping_dict)
    print("Restored StepMapping:")
    print(f"  Step: {restored_mapping.step}")
    print(f"  Page Objects: {restored_mapping.page_objects}")
    print(f"  Code Paths: {restored_mapping.code_paths}")
    print()


def main():
    """Run all demonstrations."""
    print("\n")
    print("=" * 80)
    print(" " * 20 + "Step-to-Code-Path Mapping Demo")
    print("=" * 80)
    print("  Demonstrates signal-driven step-to-code-path mapping system")
    print("  for impact analysis, migration parity, and test intelligence")
    print("=" * 80)
    print()
    
    demos = [
        demo_basic_registration,
        demo_multi_signal_resolution,
        demo_contains_matching,
        demo_bdd_keyword_removal,
        demo_integration_with_bdd_expansion,
        demo_impact_analysis,
        demo_serialization
    ]
    
    for demo_func in demos:
        demo_func()
        input("Press Enter to continue...")
        print("\n")
    
    print("=" * 80)
    print("All demos completed! ✅")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("  1. Integrate mapping into your test adapters")
    print("  2. Register signals during test discovery")
    print("  3. Use StepMappingResolver to populate IntentModel.code_paths")
    print("  4. Enable impact analysis and migration parity checks")
    print()


if __name__ == "__main__":
    main()
