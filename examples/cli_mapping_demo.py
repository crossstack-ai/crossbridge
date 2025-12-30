"""
Demo script to test CLI mapping commands end-to-end.

This script creates sample mappings and demonstrates:
- Saving mappings with persistence layer
- show-mappings command
- analyze-impact command
- validate-coverage command
"""
from adapters.common.mapping import (
    StepMapping,
    StepSignal,
    SignalType,
    save_mapping,
)

def create_sample_mappings():
    """Create sample test mappings for demonstration."""
    print("Creating sample test mappings...")
    
    # Sample test run ID
    run_id = "demo_run_20250101"
    
    # Test 1: Login test with full mapping
    mapping1 = StepMapping(
        step="Given user is on login page",
        page_objects=["LoginPage"],
        methods=["open", "navigateTo"],
        code_paths=[
            "pages/login_page.py::LoginPage.open",
            "pages/base_page.py::BasePage.navigateTo"
        ],
        signals=[]
    )
    save_mapping(mapping1, test_id="test_login_001", run_id=run_id)
    
    # Test 2: Login step with auth
    mapping2 = StepMapping(
        step="When user logs in with admin and password123",
        page_objects=["LoginPage"],
        methods=["login", "enterCredentials"],
        code_paths=[
            "pages/login_page.py::LoginPage.login",
            "pages/login_page.py::LoginPage.enterCredentials"
        ],
        signals=[]
    )
    save_mapping(mapping2, test_id="test_login_002", run_id=run_id)
    
    # Test 3: Dashboard verification
    mapping3 = StepMapping(
        step="Then user should see dashboard",
        page_objects=["DashboardPage"],
        methods=["isVisible", "waitForElement"],
        code_paths=[
            "pages/dashboard_page.py::DashboardPage.isVisible",
            "pages/base_page.py::BasePage.waitForElement"
        ],
        signals=[]
    )
    save_mapping(mapping3, test_id="test_dashboard_001", run_id=run_id)
    
    # Test 4: Order creation (UI + API)
    mapping4 = StepMapping(
        step="When user creates order for product",
        page_objects=["OrderPage", "OrderAPI"],
        methods=["createOrder", "post_order"],
        code_paths=[
            "pages/order_page.py::OrderPage.createOrder",
            "api/order_api.py::OrderAPI.post_order"
        ],
        signals=[]
    )
    save_mapping(mapping4, test_id="test_order_001", run_id=run_id)
    
    # Test 5: Unmapped step (for coverage demo)
    mapping5 = StepMapping(
        step="When user receives email notification",
        page_objects=[],
        methods=[],
        code_paths=[],
        signals=[]
    )
    save_mapping(mapping5, test_id="test_email_001", run_id=run_id)
    
    print(f"✅ Created 5 sample mappings for run_id={run_id}\n")
    return run_id

def demo_cli_commands(run_id: str):
    """Demonstrate CLI commands with sample data."""
    import subprocess
    
    print("=" * 80)
    print("DEMO: CLI Mapping Commands")
    print("=" * 80)
    print()
    
    # Demo 1: Show single mapping
    print("1️⃣  Show single mapping (JSON format):")
    print("   Command: python cli/main.py show-mappings --test-id test_login_001 --run-id " + run_id + " --format json")
    print()
    result = subprocess.run(
        ["python", "cli/main.py", "show-mappings", 
         "--test-id", "test_login_001", 
         "--run-id", run_id,
         "--format", "json"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print()
    
    # Demo 2: Show all mappings (summary)
    print("2️⃣  Show all mappings for run (summary):")
    print("   Command: python cli/main.py show-mappings --run-id " + run_id + " --format summary")
    print()
    result = subprocess.run(
        ["python", "cli/main.py", "show-mappings",
         "--run-id", run_id,
         "--format", "summary"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print()
    
    # Demo 3: Show all mappings (table)
    print("3️⃣  Show all mappings (table format):")
    print("   Command: python cli/main.py show-mappings --run-id " + run_id + " --format table")
    print()
    result = subprocess.run(
        ["python", "cli/main.py", "show-mappings",
         "--run-id", run_id,
         "--format", "table"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print()
    
    # Demo 4: Analyze impact
    print("4️⃣  Analyze impact of code change:")
    print("   Command: python cli/main.py analyze-impact --changed 'pages/login_page.py::LoginPage.login,pages/base_page.py::BasePage.waitForElement' --run-id " + run_id)
    print()
    result = subprocess.run(
        ["python", "cli/main.py", "analyze-impact",
         "--changed", "pages/login_page.py::LoginPage.login,pages/base_page.py::BasePage.waitForElement",
         "--run-id", run_id],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print()
    
    # Demo 5: Analyze impact (detailed)
    print("5️⃣  Analyze impact (detailed format):")
    print("   Command: python cli/main.py analyze-impact --changed 'pages/base_page.py::BasePage.navigateTo' --run-id " + run_id + " --format detailed")
    print()
    result = subprocess.run(
        ["python", "cli/main.py", "analyze-impact",
         "--changed", "pages/base_page.py::BasePage.navigateTo",
         "--run-id", run_id,
         "--format", "detailed"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print()
    
    # Demo 6: Validate coverage
    print("6️⃣  Validate mapping coverage:")
    print("   Command: python cli/main.py validate-coverage --run-id " + run_id)
    print()
    result = subprocess.run(
        ["python", "cli/main.py", "validate-coverage",
         "--run-id", run_id],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print()
    
    # Demo 7: Validate coverage (detailed with unmapped)
    print("7️⃣  Validate coverage (detailed with unmapped steps):")
    print("   Command: python cli/main.py validate-coverage --run-id " + run_id + " --format detailed --show-unmapped")
    print()
    result = subprocess.run(
        ["python", "cli/main.py", "validate-coverage",
         "--run-id", run_id,
         "--format", "detailed",
         "--show-unmapped"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print()
    
    print("=" * 80)
    print("All CLI demos completed! ✅")
    print("=" * 80)

if __name__ == "__main__":
    # Create sample data
    run_id = create_sample_mappings()
    
    # Run CLI demos
    demo_cli_commands(run_id)
    
    print()
    print("💡 Tip: You can now run these commands manually:")
    print(f"   python cli/main.py show-mappings --run-id {run_id}")
    print(f"   python cli/main.py analyze-impact --changed pages/login_page.py::LoginPage.login --run-id {run_id}")
    print(f"   python cli/main.py validate-coverage --run-id {run_id} --show-unmapped")
