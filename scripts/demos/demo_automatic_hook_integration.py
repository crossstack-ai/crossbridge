"""
Comprehensive Demo: Automatic Sidecar Hook Integration

Demonstrates automatic hook integration for all supported frameworks:
- Robot Framework
- pytest
- Playwright Python
- Playwright TypeScript
- Cypress

Shows:
1. Hook integration with default settings
2. Hook integration with custom settings
3. Disabled hook integration
4. Generated configuration files
"""

import tempfile
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from core.translation.migration_hooks import (
    MigrationHookConfig,
    MigrationHookIntegrator,
    integrate_hooks_after_migration
)

console = Console()


def print_section(title: str):
    """Print a section header"""
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")


def print_file_content(file_path: Path, language: str = "python"):
    """Print file content with syntax highlighting"""
    if file_path.exists():
        content = file_path.read_text()
        console.print(f"\n[bold green]📄 {file_path.name}:[/bold green]")
        syntax = Syntax(content, language, theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print(f"[red]❌ File not found: {file_path}[/red]")


def demo_robot_framework():
    """Demo Robot Framework hook integration"""
    print_section("🤖 Demo 1: Robot Framework Hook Integration")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir)
    
    try:
        # Create sample robot file
        robot_file = output_dir / "test_login.robot"
        robot_file.write_text("""*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Test Login Page
    Open Browser    https://example.com    chrome
    Input Text    id=username    admin
    Input Text    id=password    secret
    Click Button    id=login
    Close Browser
""")
        
        console.print("[bold]Scenario:[/bold] Migrating Selenium test to Robot Framework")
        console.print(f"Output directory: {output_dir}")
        console.print(f"Migrated files: {robot_file.name}\n")
        
        # Configure and integrate hooks
        config = MigrationHookConfig(
            enable_hooks=True,
            db_host="10.55.12.99",
            application_version="v1.5.0",
            product_name="RobotDemo"
        )
        
        integrator = MigrationHookIntegrator(config)
        result = integrator.integrate_hooks(
            target_framework="robot",
            output_dir=output_dir,
            migrated_files=[robot_file]
        )
        
        # Display results
        if result.get("enabled", False):
            console.print("✅ [bold green]Hook integration successful![/bold green]\n")
            
            table = Table(title="Integration Details")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Framework", result["framework"])
            table.add_row("Hook Type", result.get("type", "N/A"))
            table.add_row("Config File", result.get("config_file", "N/A"))
            table.add_row("Files Modified", str(len(result.get("updated_files", []))))
            
            console.print(table)
            
            # Show generated config file
            print_file_content(output_dir / "robot_config.py", "python")
            
            # Show updated robot file
            print_file_content(robot_file, "robotframework")
            
            # Show disable instructions
            console.print("\n[bold yellow]💡 To disable hooks:[/bold yellow]")
            console.print(integrator.generate_disable_instructions("robot"))
        else:
            console.print(f"❌ [red]Integration failed: {result.get('reason')}[/red]")
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def demo_pytest_integration():
    """Demo pytest hook integration"""
    print_section("🧪 Demo 2: pytest Hook Integration")
    
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir)
    
    try:
        # Create sample pytest file
        test_file = output_dir / "test_api.py"
        test_file.write_text("""import pytest
import requests

def test_api_endpoint():
    response = requests.get("https://api.example.com/users")
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_api_post():
    data = {"name": "Test User", "email": "test@example.com"}
    response = requests.post("https://api.example.com/users", json=data)
    assert response.status_code == 201
""")
        
        console.print("[bold]Scenario:[/bold] Migrating RestAssured test to pytest")
        console.print(f"Output directory: {output_dir}")
        console.print(f"Migrated files: {test_file.name}\n")
        
        # Configure with custom settings
        config = MigrationHookConfig(
            enable_hooks=True,
            db_host="pytest-db.company.com",
            db_port=5433,
            application_version="v2.0.0",
            product_name="PytestAPITests",
            environment="staging"
        )
        
        integrator = MigrationHookIntegrator(config)
        result = integrator.integrate_hooks(
            target_framework="pytest",
            output_dir=output_dir,
            migrated_files=[test_file]
        )
        
        # Display results
        if result["success"]:
            console.print("✅ [bold green]Hook integration successful![/bold green]\n")
            
            table = Table(title="Integration Details")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Framework", result["framework"])
            table.add_row("Hook Type", result["hook_type"])
            table.add_row("Config File", result["config_file"])
            
            console.print(table)
            
            # Show generated conftest.py
            print_file_content(output_dir / "conftest.py", "python")
            
            # Show generated pytest.ini
            print_file_content(output_dir / "pytest.ini", "ini")
            
            # Show disable instructions
            console.print("\n[bold yellow]💡 To disable hooks:[/bold yellow]")
            console.print(result["disable_instructions"])
        else:
            console.print(f"❌ [red]Integration failed: {result['message']}[/red]")
    
    finally:
        shutil.rmtree(temp_dir)


def demo_playwright_python():
    """Demo Playwright Python hook integration"""
    print_section("🎭 Demo 3: Playwright Python Hook Integration")
    
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir)
    
    try:
        # Create sample Playwright test
        test_file = output_dir / "test_e2e.py"
        test_file.write_text("""import pytest
from playwright.sync_api import Page, expect

def test_homepage(page: Page):
    page.goto("https://example.com")
    expect(page).to_have_title("Example Domain")
    
def test_navigation(page: Page):
    page.goto("https://example.com")
    page.click("text=More information")
    expect(page).to_have_url("https://www.iana.org/domains/reserved")
""")
        
        console.print("[bold]Scenario:[/bold] Migrating Cypress test to Playwright Python")
        console.print(f"Output directory: {output_dir}")
        console.print(f"Migrated files: {test_file.name}\n")
        
        # Use convenience function
        result = integrate_hooks_after_migration(
            target_framework="playwright-python",
            output_dir=output_dir,
            migrated_files=[test_file],
            enable_hooks=True,
            db_host="10.55.12.99",
            application_version="v3.0.0",
            product_name="PlaywrightE2E"
        )
        
        # Display results
        if result.get("enabled", False):
            console.print("✅ [bold green]Hook integration successful![/bold green]\n")
            
            table = Table(title="Integration Details")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Framework", result["framework"])
            table.add_row("Hook Type", result.get("type", "N/A"))
            table.add_row("Config File", result.get("config_file", "N/A"))
            
            console.print(table)
            
            # Show generated conftest.py (Playwright Python uses pytest)
            print_file_content(output_dir / "conftest.py", "python")
            
            # Show disable instructions
            console.print("\n[bold yellow]💡 To disable hooks:[/bold yellow]")
            console.print(integrator.generate_disable_instructions("playwright-python"))
        else:
            console.print(f"❌ [red]Integration failed: {result['message']}[/red]")
    
    finally:
        shutil.rmtree(temp_dir)


def demo_playwright_typescript():
    """Demo Playwright TypeScript hook integration"""
    print_section("🎭 Demo 4: Playwright TypeScript Hook Integration")
    
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir)
    
    try:
        # Create sample Playwright TypeScript test
        test_file = output_dir / "example.spec.ts"
        test_file.write_text("""import { test, expect } from '@playwright/test';

test('homepage has title', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example Domain/);
});

test('navigate to more info', async ({ page }) => {
  await page.goto('https://example.com');
  await page.click('text=More information');
  await expect(page).toHaveURL('https://www.iana.org/domains/reserved');
});
""")
        
        console.print("[bold]Scenario:[/bold] Migrating Selenium test to Playwright TypeScript")
        console.print(f"Output directory: {output_dir}")
        console.print(f"Migrated files: {test_file.name}\n")
        
        # Configure and integrate
        config = MigrationHookConfig(
            enable_hooks=True,
            db_host="playwright-ts.company.com",
            application_version="v3.5.0",
            product_name="PlaywrightTS"
        )
        
        integrator = MigrationHookIntegrator(config)
        result = integrator.integrate_hooks(
            target_framework="playwright-typescript",
            output_dir=output_dir,
            migrated_files=[test_file]
        )
        
        # Display results
        if result.get("enabled", False):
            console.print("✅ [bold green]Hook integration successful![/bold green]\n")
            
            table = Table(title="Integration Details")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Framework", result["framework"])
            table.add_row("Hook Type", result.get("type", "N/A"))
            table.add_row("Config File", result.get("config_file", "N/A"))
            
            console.print(table)
            
            # Show generated playwright.config.ts
            print_file_content(output_dir / "playwright.config.ts", "typescript")
            
            # Show disable instructions
            console.print("\n[bold yellow]💡 To disable hooks:[/bold yellow]")
            console.print(integrator.generate_disable_instructions("playwright-typescript"))
        else:
            console.print(f"❌ [red]Integration failed: {result.get('reason')}[/red]")
    
    finally:
        shutil.rmtree(temp_dir)


def demo_cypress():
    """Demo Cypress hook integration"""
    print_section("🌲 Demo 5: Cypress Hook Integration")
    
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir)
    
    try:
        # Create sample Cypress test
        cypress_dir = output_dir / "cypress" / "e2e"
        cypress_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = cypress_dir / "login.cy.js"
        test_file.write_text("""describe('Login Tests', () => {
  beforeEach(() => {
    cy.visit('https://example.com/login');
  });

  it('should display login form', () => {
    cy.get('#username').should('be.visible');
    cy.get('#password').should('be.visible');
    cy.get('#login-button').should('be.visible');
  });

  it('should login successfully', () => {
    cy.get('#username').type('testuser');
    cy.get('#password').type('testpass');
    cy.get('#login-button').click();
    cy.url().should('include', '/dashboard');
  });
});
""")
        
        console.print("[bold]Scenario:[/bold] Migrating Selenium test to Cypress")
        console.print(f"Output directory: {output_dir}")
        console.print(f"Migrated files: {test_file.relative_to(output_dir)}\n")
        
        # Configure and integrate
        config = MigrationHookConfig(
            enable_hooks=True,
            db_host="10.55.12.99",
            application_version="v4.0.0",
            product_name="CypressTests",
            environment="test"
        )
        
        integrator = MigrationHookIntegrator(config)
        result = integrator.integrate_hooks(
            target_framework="cypress",
            output_dir=output_dir,
            migrated_files=[test_file]
        )
        
        # Display results
        if result.get("enabled", False):
            console.print("✅ [bold green]Hook integration successful![/bold green]\n")
            
            table = Table(title="Integration Details")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Framework", result["framework"])
            table.add_row("Hook Type", result.get("type", "N/A"))
            table.add_row("Config File", result.get("config_file", "N/A"))
            table.add_row("Support File", str(output_dir / "cypress" / "support" / "e2e.js"))
            
            console.print(table)
            
            # Show generated cypress.config.js
            print_file_content(output_dir / "cypress.config.js", "javascript")
            
            # Show generated support file
            print_file_content(output_dir / "cypress" / "support" / "e2e.js", "javascript")
            
            # Show disable instructions
            console.print("\n[bold yellow]💡 To disable hooks:[/bold yellow]")
            console.print(integrator.generate_disable_instructions("cypress"))
        else:
            console.print(f"❌ [red]Integration failed: {result.get('reason')}[/red]")
    
    finally:
        shutil.rmtree(temp_dir)


def demo_disabled_hooks():
    """Demo with hooks disabled"""
    print_section("🚫 Demo 6: Disabled Hook Integration")
    
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir)
    
    try:
        console.print("[bold]Scenario:[/bold] Migration with --disable-sidecar flag")
        console.print(f"Output directory: {output_dir}\n")
        
        # Configure with hooks disabled
        config = MigrationHookConfig(enable_hooks=False)
        
        integrator = MigrationHookIntegrator(config)
        result = integrator.integrate_hooks(
            target_framework="robot",
            output_dir=output_dir,
            migrated_files=[]
        )
        
        # Display results
        if not result.get("enabled", True):
            console.print("ℹ️  [bold yellow]Hook integration skipped (disabled)[/bold yellow]\n")
            console.print(f"Reason: {result.get('reason')}\n")
            
            # Check that no files were created
            config_file = output_dir / "robot_config.py"
            if not config_file.exists():
                console.print("✅ [green]Verified: No configuration files created[/green]")
            else:
                console.print("❌ [red]Error: Configuration files were created despite disabled flag[/red]")
        else:
            console.print("❌ [red]Error: Integration should have been skipped[/red]")
    
    finally:
        shutil.rmtree(temp_dir)


def demo_all_frameworks_summary():
    """Demo summary of all frameworks"""
    print_section("📊 Demo 7: All Frameworks Summary")
    
    frameworks = [
        ("robot", "Robot Framework", "robot_listener", "robot_config.py"),
        ("pytest", "pytest", "pytest_plugin", "conftest.py"),
        ("playwright-python", "Playwright Python", "pytest_plugin", "conftest.py"),
        ("playwright-typescript", "Playwright TypeScript", "playwright_reporter", "playwright.config.ts"),
        ("cypress", "Cypress", "cypress_plugin", "cypress.config.js"),
    ]
    
    table = Table(title="Automatic Hook Integration - Supported Frameworks")
    table.add_column("Framework ID", style="cyan")
    table.add_column("Display Name", style="green")
    table.add_column("Hook Type", style="yellow")
    table.add_column("Config File", style="magenta")
    table.add_column("Status", style="bold green")
    
    for fw_id, display_name, hook_type, config_file in frameworks:
        table.add_row(fw_id, display_name, hook_type, config_file, "✅ Supported")
    
    console.print(table)
    
    # Show usage examples
    console.print("\n[bold cyan]Usage Examples:[/bold cyan]\n")
    
    examples = [
        ("Enable hooks (default)", "crossbridge translate --source selenium-java --target robot ..."),
        ("Disable hooks", "crossbridge translate --source selenium-java --target robot --disable-sidecar ..."),
        ("Custom database", "crossbridge translate ... --sidecar-db-host my-db.com --sidecar-app-version v2.0.0"),
    ]
    
    for title, command in examples:
        console.print(f"[bold]{title}:[/bold]")
        console.print(f"  [dim]{command}[/dim]\n")


def main():
    """Run all demos"""
    console.print(Panel.fit(
        "[bold cyan]Automatic Sidecar Hook Integration - Comprehensive Demo[/bold cyan]\n"
        "[dim]Demonstrates automatic hook integration for all supported frameworks[/dim]",
        border_style="cyan"
    ))
    
    try:
        # Run demos
        demo_robot_framework()
        demo_pytest_integration()
        demo_playwright_python()
        demo_playwright_typescript()
        demo_cypress()
        demo_disabled_hooks()
        demo_all_frameworks_summary()
        
        # Final summary
        print_section("✅ Demo Complete")
        console.print("[bold green]All demos completed successfully![/bold green]\n")
        console.print("[dim]Automatic hook integration is ready for production use.[/dim]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Demo failed with error:[/bold red]")
        console.print(f"[red]{str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    main()
