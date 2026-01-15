"""
CLI Branding for CrossBridge by CrossStack AI.

Professional, clean branding following DevOps CLI patterns (Terraform, AWS CLI).
Subtle identity without overwhelming the user.

Branding Guidelines:
- CrossBridge = Product name
- CrossStack AI = Company name
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from typing import Optional
import sys
import os

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    try:
        # Try to set console to UTF-8 mode
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
        # Set console code page to UTF-8 on Windows
        if os.name == 'nt':
            os.system('chcp 65001 > nul 2>&1')
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)


def show_welcome():
    """Display welcome screen with CrossStack AI branding."""
    
    # CrossStack AI ASCII art logo
    logo = Text()
    logo.append("\n")
    logo.append("        ██╗  ██╗", style="cyan")
    logo.append("  ", style="")
    logo.append("███████╗", style="bright_magenta")
    logo.append("\n")
    
    logo.append("        ╚██╗██╔╝", style="cyan")
    logo.append("  ", style="")
    logo.append("╚══███╔╝", style="bright_magenta")
    logo.append("  ", style="")
    logo.append("◉━━◉", style="yellow")
    logo.append("\n")
    
    logo.append("         ╚███╔╝ ", style="bright_cyan")
    logo.append("  ", style="")
    logo.append("███╔╝ ", style="magenta")
    logo.append("  ", style="")
    logo.append("◉━━◉", style="green")
    logo.append("\n")
    
    logo.append("         ██╔██╗ ", style="green")
    logo.append("  ", style="")
    logo.append("███║  ", style="bright_blue")
    logo.append("  ", style="")
    logo.append("◉━━◉", style="bright_red")
    logo.append("\n")
    
    logo.append("        ██╔╝ ██╗", style="bright_green")
    logo.append("  ", style="")
    logo.append("███████╗", style="blue")
    logo.append("\n")
    
    logo.append("        ╚═╝  ╚═╝", style="dim")
    logo.append("  ", style="")
    logo.append("╚══════╝", style="dim")
    logo.append("\n\n")
    
    logo.append("      ", style="")
    logo.append("CrossStack ", style="bold white")
    logo.append("AI", style="bold bright_cyan")
    logo.append("\n")
    
    logo.append("  ", style="")
    logo.append("Bridging Legacy to AI-Powered Test Systems", style="dim cyan")
    logo.append("\n")
    
    console.print(logo)
    
    title = Text()
    title.append("CrossBridge", style="bold cyan")
    title.append(" by ", style="dim")
    title.append("CrossStack AI", style="bold magenta")
    
    welcome_panel = Panel(
        Text.from_markup(
            "[dim]Test Framework Migration • AI-Powered Modernization[/dim]"
        ),
        title=title,
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print()
    console.print(welcome_panel)
    console.print()


def show_migration_summary(
    migration_type: str,
    operation_type: str,
    transformation_mode: str,
    repo_url: str,
    branch: str,
    use_ai: bool,
    create_pr: bool = False,
    target_branch: Optional[str] = None,
    framework_config: Optional[dict] = None,
    force_retransform: bool = False,
    transformation_tier: Optional[str] = None,
    ai_provider: Optional[str] = None,
    ai_model: Optional[str] = None
):
    """Display migration configuration summary.
    
    Args:
        migration_type: Type of migration
        operation_type: Operation type (migration/transformation/both)
        transformation_mode: Transformation mode
        repo_url: Repository URL
        branch: Source branch
        use_ai: Whether AI is enabled
        create_pr: Whether to create PR
        target_branch: Target branch (for transformation)
        framework_config: Framework-specific configuration
        force_retransform: Whether to force re-transformation
        transformation_tier: Transformation depth tier (TIER_1/TIER_2/TIER_3)
        ai_provider: AI provider name (openai/anthropic)
        ai_model: AI model name (gpt-3.5-turbo, gpt-4, etc.)
    """
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="white")
    
    # Only show Migration Type if it's actually set (not for pure transformation)
    if migration_type and migration_type != "N/A":
        table.add_row("Migration Type", migration_type)
    
    # Enhanced Operation Type display for transformation
    if operation_type == "transformation":
        # Build multi-line display for transformation details
        operation_parts = ["Transformation"]
        
        # Add force on separate line if present
        if force_retransform:
            operation_parts.append("Force: Yes")
        
        # Add tier on separate line if present
        if transformation_tier:
            tier_map = {
                "tier_1": "Depth: Tier 1 (Quick Refresh)",
                "tier_2": "Depth: Tier 2 (Content Validation)",
                "tier_3": "Depth: Tier 3 (Deep Re-Generation)",
                "TIER_1": "Depth: Tier 1 (Quick Refresh)",
                "TIER_2": "Depth: Tier 2 (Content Validation)",
                "TIER_3": "Depth: Tier 3 (Deep Re-Generation)"
            }
            tier_display = tier_map.get(transformation_tier, f"Depth: {transformation_tier}")
            operation_parts.append(tier_display)
        
        operation_display = "\n".join(operation_parts)
        table.add_row("Operation Type", operation_display)
    else:
        table.add_row("Operation Type", operation_type)
    
    table.add_row("Transformation Mode", transformation_mode)
    table.add_row("Repository", repo_url)
    table.add_row("Branch", branch)
    
    # Show target branch only for transformation
    if target_branch and operation_type == "transformation":
        table.add_row("Target Branch", target_branch)
    
    # Show framework-specific config based on operation type
    if framework_config:
        if operation_type == "transformation":
            # For transformation, show Robot Framework configuration on multiple lines
            if "robot_tests_path" in framework_config:
                config_parts = [f"Tests: {framework_config['robot_tests_path']}"]
                
                if "page_objects_path" in framework_config:
                    config_parts.append(f"Page Objects: {framework_config['page_objects_path']}")
                
                if "locators_path" in framework_config:
                    config_parts.append(f"Locators: {framework_config['locators_path']}")
                
                config_display = "\n".join(config_parts)
                table.add_row("Robot Test Artifacts", config_display)
        elif operation_type in ["migration", "migration_and_transformation"]:
            if "java_source_path" in framework_config:
                table.add_row("Java Source Path", framework_config["java_source_path"])
            if "feature_files_path" in framework_config:
                table.add_row("Feature Files Path", framework_config["feature_files_path"])
    
    table.add_row("AI Assistance", "✓ Enabled" if use_ai else "○ Disabled")
    
    # Show AI provider and model if AI is enabled
    if use_ai and ai_provider and ai_model:
        # Format provider name for display
        provider_map = {
            "openai": "OpenAI",
            "anthropic": "Anthropic"
        }
        provider_display = provider_map.get(ai_provider.lower(), ai_provider.title()) if ai_provider else "Unknown"
        table.add_row("AI Provider", provider_display)
        table.add_row("AI Model", ai_model)
    
    table.add_row("Create PR", "✓ Yes" if create_pr else "○ No")
    
    panel = Panel(
        table,
        title="[bold]Configuration[/bold]",
        border_style="dim",
        padding=(0, 1)
    )
    
    console.print(panel)
    console.print()


def show_completion(
    pr_url: Optional[str] = None,
    log_file: Optional[str] = None,
    duration: Optional[float] = None,
    operation_type: str = "migration"
):
    """Display completion summary.
    
    Args:
        pr_url: Optional pull request URL
        log_file: Optional log file path
        duration: Optional duration in seconds
        operation_type: Type of operation - 'migration', 'transformation', or 'migration_and_transformation'
    """
    
    message = Text()
    message.append("✓ ", style="bold green")
    
    # Use appropriate message based on operation type
    if operation_type == "transformation":
        message.append("Transformation completed successfully", style="green")
    elif operation_type == "migration_and_transformation":
        message.append("Migration and transformation completed successfully", style="green")
    else:
        message.append("Migration completed successfully", style="green")
    
    details = []
    if pr_url:
        details.append(f"[cyan]Pull Request:[/cyan] {pr_url}")
    if log_file:
        details.append(f"[cyan]Logs:[/cyan] {log_file}")
    if duration:
        details.append(f"[cyan]Duration:[/cyan] {duration:.1f}s")
    
    content = message
    if details:
        content = Text.from_markup("\n".join([str(message)] + details))
    
    panel = Panel(
        content,
        border_style="green",
        padding=(1, 2)
    )
    
    console.print()
    console.print(panel)
    console.print()


def show_error(error_message: str, error_code: Optional[str] = None, suggestion: Optional[str] = None, log_file: Optional[str] = None):
    """Display error message with optional suggestion."""
    
    message = Text()
    message.append("✗ ", style="bold red")
    message.append("Migration failed", style="red")
    
    details = [f"\n[red]{error_message}[/red]"]
    
    if error_code:
        details.append(f"\n[dim]Error code: {error_code}[/dim]")
    
    if suggestion:
        details.append(f"\n[yellow]Suggestion:[/yellow] {suggestion}")
    
    if log_file:
        details.append(f"\n[dim]Log file:[/dim] [cyan]{log_file}[/cyan]")
    
    content = Text.from_markup("".join([str(message)] + details))
    
    panel = Panel(
        content,
        border_style="red",
        padding=(1, 2)
    )
    
    console.print()
    console.print(panel)
    console.print()


def show_info(message: str):
    """Display informational message."""
    console.print(f"[dim]ℹ {message}[/dim]")


def show_warning(message: str):
    """Display warning message."""
    console.print(f"[yellow]⚠ {message}[/yellow]")


def show_step(step: str):
    """Display current workflow step."""
    console.print(f"[cyan]→[/cyan] {step}")
