"""
Interactive prompts for CrossBridge CLI.

Uses Typer and Rich for clean, conversational user interaction.
Password/token fields never echo to terminal.
"""

import typer
from rich.prompt import Prompt, Confirm
from rich.console import Console
from typing import Dict, Optional

from core.orchestration import (
    MigrationType,
    AuthType,
    AIMode,
    RepositoryAuth,
    AIConfig,
    MigrationMode,
    TransformationMode,
    TransformationTier,
    OperationType
)

console = Console()


def _mask_token(token: str) -> str:
    """
    Mask token showing only first and last 4 characters.
    
    Args:
        token: The token to mask
        
    Returns:
        Masked token string (e.g., "ATAT...2OeR" for short tokens, "ATAT...OeRP" for longer ones)
    """
    if len(token) <= 8:
        # Very short token - show first 2 and last 2
        return f"{token[:2]}...{token[-2:]}"
    elif len(token) <= 16:
        # Short token - show first 3 and last 3
        return f"{token[:3]}...{token[-3:]}"
    else:
        # Normal token - show first 4 and last 4
        return f"{token[:4]}...{token[-4:]}"


def _mask_username(username: str) -> str:
    """
    Mask username/email for display.
    
    Args:
        username: The username or email to mask
        
    Returns:
        Masked username (e.g., "vik***@arcserve.com" or "vik***ma")
    """
    if "@" in username:
        # Email format - mask the local part, keep domain visible
        local, domain = username.split("@", 1)
        if len(local) <= 3:
            masked_local = local[0] + "**"
        elif len(local) <= 6:
            masked_local = local[:2] + "***"
        else:
            masked_local = local[:3] + "***" + local[-2:]
        return f"{masked_local}@{domain}"
    else:
        # Regular username - mask middle part
        if len(username) <= 4:
            return username[0] + "***"
        elif len(username) <= 8:
            return username[:2] + "***" + username[-1]
        else:
            return username[:3] + "***" + username[-2:]


def prompt_migration_mode() -> MigrationMode:
    """Prompt user to select migration mode (Test or Live)."""
    
    console.print("\n[cyan]Select Execution Environment:[/cyan]")
    console.print("\n[1] [yellow]Sandbox (Test / Development)[/yellow]  [DEFAULT]")
    console.print("    • Allows overwriting previous runs")
    console.print("    • Faster iteration, fewer restrictions\n")
    console.print("[2] [green]Production (Live Migration)[/green]")
    console.print("    • Creates unique branches automatically")
    console.print("    • No overwriting or destructive actions")
    console.print("    • Enforced safety checks\n")
    
    choice = Prompt.ask(
        "Enter choice [1–2] (default: 1)",
        choices=["1", "2"],
        default="1",
        show_choices=False
    )
    
    return MigrationMode.TEST if choice == "1" else MigrationMode.LIVE


def prompt_operation_type() -> OperationType:
    """Prompt user to select operation type (Migration/Transformation/Both)."""
    
    console.print("\n[cyan]Select Operation Type:[/cyan]")
    console.print("\n[1] [blue]Migration[/blue]")
    console.print("    Move tests to a new framework without structural changes\n")
    console.print("[2] [yellow]Transformation[/yellow]")
    console.print("    Refactor tests within the same ecosystem\n")
    console.print("[3] [green]Migration + Transformation[/green]")
    console.print("    Move and modernize tests together [DEFAULT]\n")
    
    choice = Prompt.ask(
        "Enter choice [1–3] (default: 3)",
        choices=["1", "2", "3"],
        default="3",
        show_choices=False
    )
    
    if choice == "1":
        return OperationType.MIGRATION
    elif choice == "2":
        return OperationType.TRANSFORMATION
    else:
        return OperationType.MIGRATION_AND_TRANSFORMATION


def prompt_transformation_mode() -> TransformationMode:
    """Prompt user to select transformation mode (Manual/Enhanced/Hybrid)."""
    
    console.print("\n[cyan]Select transformation mode:[/cyan]")
    console.print("[1] [dim]Manual[/dim] - Create file structure only, manual test implementation needed")
    console.print("[2] [green]Enhanced[/green] - Automated Gherkin parsing with Robot Framework generation [DEFAULT]")
    console.print("[3] [yellow]Hybrid[/yellow] - Automated transformation with manual review checkpoints\n")
    
    choice = Prompt.ask(
        "Enter choice [1–3] (default: 2)",
        choices=["1", "2", "3"],
        default="2",
        show_choices=False
    )
    
    mode_map = {
        "1": TransformationMode.MANUAL,
        "2": TransformationMode.ENHANCED,
        "3": TransformationMode.HYBRID
    }
    
    return mode_map[choice]


def prompt_force_retransform(operation_type: OperationType) -> bool:
    """Prompt user if they want to force re-transformation of already-enhanced files.
    
    Only asked when operation_type is TRANSFORMATION (working on existing migrated files).
    
    Args:
        operation_type: The operation type selected by user
        
    Returns:
        True if user wants to force re-transformation, False otherwise
    """
    # Only prompt for TRANSFORMATION operations
    if operation_type != OperationType.TRANSFORMATION:
        return False
    
    console.print("\n[bold yellow]═══ Re-Transformation Options ═══[/bold yellow]")
    console.print("[cyan]Your target branch may contain already-enhanced Robot Framework files.[/cyan]")
    console.print("[dim]By default, CrossBridge skips files that are already enhanced to avoid redundant work.[/dim]\n")
    
    console.print("[bold cyan]Force Re-Transformation?[/bold cyan]")
    console.print("  [green]Yes[/green] - Re-process all files regardless of current state")
    console.print("  [blue]No[/blue]  - Skip already-enhanced files (faster, recommended) [DEFAULT]\n")
    
    choice = Confirm.ask(
        "Force re-transformation of already-enhanced files?",
        default=False
    )
    
    return choice


def prompt_transformation_tier(force_retransform: bool) -> TransformationTier:
    """Prompt user to select transformation tier (depth of transformation).
    
    Only asked when force_retransform is True.
    
    Args:
        force_retransform: Whether user chose to force re-transformation
        
    Returns:
        TransformationTier enum value
    """
    # Only prompt if force retransform is enabled
    if not force_retransform:
        return TransformationTier.TIER_1
    
    console.print("\n[bold cyan]═══ Transformation Depth Selection ═══[/bold cyan]")
    console.print("[dim]Choose how deep you want to transform the files:[/dim]\n")
    
    console.print("[1] [green]TIER 1 - Quick Header Refresh[/green] [DEFAULT]")
    console.print("    • Update timestamps and metadata")
    console.print("    • Refresh CrossStack platform integration headers")
    console.print("    • Fastest option (~1-2 seconds per file)")
    console.print("    • [dim]Best for: Updating documentation, timestamps, or minor enhancements[/dim]\n")
    
    console.print("[2] [yellow]TIER 2 - Content Validation & Optimization[/yellow]")
    console.print("    • Parse Robot Framework syntax")
    console.print("    • Validate keyword structures and detect anti-patterns")
    console.print("    • Fix common issues and optimize code")
    console.print("    • Medium speed (~5-10 seconds per file)")
    console.print("    • [dim]Best for: Quality validation, fixing issues, applying best practices[/dim]\n")
    
    console.print("[3] [red]TIER 3 - Deep Re-Generation[/red]")
    console.print("    • Complete re-transformation from original source files")
    console.print("    • Re-parse .feature (Gherkin) and .java (Step Definitions)")
    console.print("    • Apply latest Selenium → Playwright mappings")
    console.print("    • Generate production-ready tests from scratch")
    console.print("    • Slowest option (~30-60 seconds per file)")
    console.print("    • [dim]Best for: Major refactoring, fixing broken tests, applying new patterns[/dim]\n")
    
    choice = Prompt.ask(
        "Select transformation tier [1–3] (default: 1)",
        choices=["1", "2", "3"],
        default="1",
        show_choices=False
    )
    
    tier_map = {
        "1": TransformationTier.TIER_1,
        "2": TransformationTier.TIER_2,
        "3": TransformationTier.TIER_3
    }
    
    return tier_map[choice]


def prompt_create_pr(migration_mode: MigrationMode) -> bool:
    """Prompt user to decide if they want to create a PR.
    
    Args:
        migration_mode: Current migration mode (Test or Live)
        
    Returns:
        True if user wants to create a PR, False otherwise
    """
    # Default based on migration mode: Test=No, Live=Yes
    default = "n" if migration_mode == MigrationMode.TEST else "y"
    default_text = "No" if migration_mode == MigrationMode.TEST else "Yes"
    
    console.print(f"\n[cyan]Create Pull Request?[/cyan]")
    console.print("[dim]If No, changes will be pushed to the migration branch only[/dim]\n")
    
    choice = Prompt.ask(
        f"Create PR [y/n] (default: {default_text})",
        choices=["y", "n", "Y", "N"],
        default=default,
        show_choices=False
    )
    
    return choice.lower() == "y"


def prompt_log_level() -> str:
    """Prompt user to select logging level."""
    
    console.print("\n[cyan]Select logging level:[/cyan]")
    console.print("[1] INFO - Standard information")
    console.print("[2] DEBUG - Detailed debugging information")
    console.print("[3] WARNING - Warnings only")
    console.print("[4] ERROR - Errors only\n")
    
    choice = Prompt.ask(
        "Enter choice [1–4] (default: 1)",
        choices=["1", "2", "3", "4"],
        default="1",
        show_choices=False
    )
    
    mapping = {
        "1": "INFO",
        "2": "DEBUG",
        "3": "WARNING",
        "4": "ERROR"
    }
    
    return mapping[choice]


def prompt_migration_type() -> MigrationType:
    """Prompt user to select migration type."""
    
    typer.echo("\n[1] Selenium Java BDD → Robot Framework + Playwright")
    typer.echo("[2] Selenium Java → Playwright")
    typer.echo("[3] Selenium Java → Robot Framework")
    typer.echo("[4] Pytest → Robot Framework\n")
    
    choice = Prompt.ask(
        "Enter choice [1–4] (default: 1)",
        choices=["1", "2", "3", "4"],
        default="1",
        show_choices=False
    )
    
    mapping = {
        "1": MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
        "2": MigrationType.SELENIUM_JAVA_TO_PLAYWRIGHT,
        "3": MigrationType.SELENIUM_JAVA_TO_ROBOT,
        "4": MigrationType.PYTEST_TO_ROBOT
    }
    
    return mapping[choice]


def prompt_repository(
    repo_url: Optional[str] = None,
    branch: Optional[str] = None,
    migration_type: Optional[str] = None,  # Add to determine if source branch is needed
    skip_target_branch: bool = False,  # Skip target branch prompt (asked separately for transformation)
    migration_mode: Optional['MigrationMode'] = None  # For auto-caching in TEST mode
) -> Dict:
    """Prompt for repository configuration."""
    
    platform = None
    cached_repo_url = None
    cached_username = None
    cached_token = None
    cached_source_branch = None
    cached_target_branch = None
    
    # Step 1: If repo_url not provided, ask for platform first
    if not repo_url:
        console.print("\n[bold yellow]═══ Repository Platform ═══[/bold yellow]")
        console.print("[cyan]Select your version control system:[/cyan]\n")
        
        console.print("[1] [bold]BitBucket[/bold]")
        console.print("[2] [bold]GitHub[/bold]")
        console.print("[3] [bold]Azure DevOps[/bold]")
        console.print("[4] [bold]GitLab[/bold]")
        console.print("[5] [bold]TFS[/bold]")
        console.print("[6] [bold]Other[/bold]\n")
        
        platform_choice = Prompt.ask(
            "Enter choice [1–6] (default: 1)",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1",
            show_choices=False
        )
        
        platform_map = {
            "1": ("bitbucket", "BitBucket"),
            "2": ("github", "GitHub"),
            "3": ("azure", "Azure DevOps"),
            "4": ("gitlab", "GitLab"),
            "5": ("tfs", "TFS"),
            "6": ("other", "Other")
        }
        
        platform, platform_name = platform_map.get(platform_choice, ("github", "GitHub"))
        console.print(f"[dim]Selected: {platform_name}[/dim]\n")
        
        # Step 2: Check for cached credentials for the selected platform
        try:
            from core.repo.test_credentials import get_test_bitbucket_creds, get_test_github_creds
            
            if platform == "bitbucket":
                try:
                    cached_username, cached_token, cached_repo_url, cached_source_branch, cached_target_branch = get_test_bitbucket_creds(auto_cache=False)
                except (ValueError, Exception):
                    pass
            elif platform == "github":
                try:
                    cached_username, cached_token = get_test_github_creds(auto_cache=False)
                    # GitHub cache doesn't store repo URL, so no cached_repo_url
                except (ValueError, Exception):
                    pass
        except ImportError:
            pass
        
        # Step 3: Show cached info if available
        if cached_repo_url or cached_username or cached_source_branch or cached_target_branch:
            console.print(f"[green]✓ Found cached {platform_name} credentials:[/green]")
            if cached_username:
                console.print(f"  [cyan]Username:[/cyan] {_mask_username(cached_username)}")
            if cached_token:
                console.print(f"  [cyan]Token:[/cyan] {_mask_token(cached_token)}")
            if cached_repo_url:
                console.print(f"  [yellow]📁 Repository:[/yellow] [bold]{cached_repo_url}[/bold]")
            if cached_source_branch:
                console.print(f"  [yellow]🌱 Source Branch:[/yellow] [bold]{cached_source_branch}[/bold]")
            if cached_target_branch:
                console.print(f"  [yellow]🌿 Target Branch:[/yellow] [bold]{cached_target_branch}[/bold]")
            console.print()
        
        # Step 4: Prompt for repository URL with cached value as default
        # Build platform-specific default URL
        if platform == "bitbucket":
            platform_url = "https://bitbucket.org"
        elif platform == "github":
            platform_url = "https://github.com"
        elif platform == "azure":
            platform_url = "https://dev.azure.com"
        elif platform == "gitlab":
            platform_url = "https://gitlab.com"
        else:
            platform_url = "https://your-git-server.com"
        
        default_url = cached_repo_url if cached_repo_url else f"{platform_url}/org/repo"
        
        repo_url_input = Prompt.ask(
            "Repository URL",
            default=default_url
        )
        
        # If user entered just the path (e.g., "org/repo"), construct full URL
        if repo_url_input and not repo_url_input.startswith(('http://', 'https://')):
            repo_url = f"{platform_url}/{repo_url_input}"
            console.print(f"[dim]→ Full URL: {repo_url}[/dim]")
        else:
            repo_url = repo_url_input
            
        # Clean up repository URL - remove common suffixes that shouldn't be there
        if repo_url:
            # Remove trailing slashes
            repo_url = repo_url.rstrip('/')
            # Remove /src/main or similar paths that are sometimes pasted
            common_suffixes = ['/src/main', '/src/test', '/blob', '/tree', '/src']
            for suffix in common_suffixes:
                if repo_url.endswith(suffix):
                    repo_url = repo_url[:-len(suffix)]
                    console.print(f"[dim]→ Cleaned URL: {repo_url}[/dim]")
                    break
    
    # If repo_url was provided as parameter, detect platform from URL
    if not platform:
        platform = _detect_platform(repo_url)
    
    # Source Branch (for migration and both modes)
    source_branch = None
    if migration_type in ("migration", "both"):
        console.print("\n[bold yellow]═══ Source Branch ═══[/bold yellow]")
        console.print("[cyan]Specify the branch to scan for existing code[/cyan]\n")
        
        default_source = cached_source_branch if cached_source_branch else "main"
        source_branch = Prompt.ask(
            "Source branch [bold red](required for migration)[/bold red]",
            default=default_source
        )
        
        if not source_branch:
            console.print("[bold red]❌ Source branch is required for migration[/bold red]")
            raise ValueError("Source branch is required for migration")
    
    # Target Branch (optional - for PR creation)
    # Skip if this will be asked separately (e.g., for transformation)
    target_branch = None
    if not skip_target_branch and not branch:
        console.print("\n[bold yellow]═══ Target Branch (Optional) ═══[/bold yellow]")
        console.print("[cyan]Branch for PR creation (leave empty to skip)[/cyan]\n")
        
        default_target = cached_target_branch if cached_target_branch else ""
        target_branch = Prompt.ask(
            "Target branch [dim](optional)[/dim]",
            default=default_target
        )
    elif branch:
        target_branch = branch
    
    # Authentication (pass details for auto-caching in TEST mode)
    auth = _prompt_authentication(
        platform, 
        repo_url=repo_url,
        source_branch=source_branch,
        target_branch=target_branch,
        migration_mode=migration_mode
    )
    
    result = {
        "url": repo_url,
        "auth": auth
    }
    
    # Add branches to result if they exist
    if source_branch:
        result["source_branch"] = source_branch
    if target_branch:
        result["target_branch"] = target_branch
    
    # For backward compatibility, set 'branch' to source_branch if it exists
    result["branch"] = source_branch if source_branch else (target_branch if target_branch else "main")
    
    return result


def _detect_related_paths(provided_path: str, path_type: str) -> Dict[str, str]:
    """
    Detect related paths based on a provided path.
    
    Args:
        provided_path: The path that was provided by user
        path_type: Type of path ('java', 'feature', or 'step')
        
    Returns:
        Dictionary with detected paths
    """
    detected = {}
    
    # Common patterns
    if 'src/main/java' in provided_path or 'src/test/java' in provided_path:
        # Standard Maven structure
        base = provided_path.split('src/')[0] if 'src/' in provided_path else ''
        detected['java_src_path'] = f"{base}src/main/java".strip('/')
        detected['feature_files_path'] = f"{base}src/test/resources/features".strip('/')
        detected['step_definitions_path'] = f"{base}src/test/java".strip('/')
    
    elif 'src/main/resources' in provided_path:
        # Feature files in src/main/resources pattern
        base = provided_path.split('src/')[0] if 'src/' in provided_path else ''
        detected['java_src_path'] = f"{base}src/main/java".strip('/')
        detected['feature_files_path'] = provided_path
        # Try to detect step definitions nearby
        java_base = provided_path.replace('/resources/UIFeature', '').replace('/resources', '')
        # If it's in src/main, step definitions likely in src/main/java too
        if '/src/main/' in provided_path:
            detected['step_definitions_path'] = f"{base}src/main/java".strip('/')
        else:
            detected['step_definitions_path'] = f"{java_base}/java".strip('/')
    
    elif '/java/' in provided_path and 'stepdefinition' in provided_path.lower():
        # Step definitions path provided - keep it as is
        detected['step_definitions_path'] = provided_path
        # Extract base path before /java/
        parts = provided_path.split('/java/')
        if len(parts) > 1:
            base_with_src = parts[0]
            # Find if it's src/main or src/test
            if '/src/main/' in provided_path:
                base = base_with_src.split('/src/main/')[0]
                detected['java_src_path'] = f"{base}/src/main/java".strip('/')
                detected['feature_files_path'] = f"{base}/src/main/resources/UIFeature".strip('/') if base else "src/main/resources/UIFeature"
            elif '/src/test/' in provided_path:
                base = base_with_src.split('/src/test/')[0]
                detected['java_src_path'] = f"{base}/src/main/java".strip('/')
                detected['feature_files_path'] = f"{base}/src/test/resources/features".strip('/')
            else:
                # No standard src structure, try to guess
                base = base_with_src
                detected['java_src_path'] = f"{base}/java".strip('/')
                detected['feature_files_path'] = f"{base}/resources/features".strip('/')
    
    return detected


def prompt_framework_config(migration_type: MigrationType) -> Dict:
    """Prompt for framework-specific repository configuration."""
    
    console.print("\n[cyan]Framework-specific configuration:[/cyan]")
    console.print("[yellow]Note: Provide paths from the repository root (e.g., 'TetonUIAutomation/src/main/java')[/yellow]\n")
    
    config = {}
    
    if migration_type in [
        MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
        MigrationType.SELENIUM_JAVA_TO_PLAYWRIGHT,
        MigrationType.SELENIUM_JAVA_TO_ROBOT
    ]:
        # Java Selenium projects
        console.print("[dim]Configure paths for Java Selenium project[/dim]")
        console.print("[yellow]Tip: You can provide just one path, and we'll try to detect the others[/yellow]\n")
        
        # Ask for feature files first (most specific)
        feature_path = ""
        if migration_type == MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT:
            feature_path = Prompt.ask(
                "Feature files path (from repository root) [or press Enter to skip]",
                default="src/test/resources/features"
            )
        
        # Try to detect other paths
        detected = {}
        if feature_path:
            detected = _detect_related_paths(feature_path, 'feature')
            config["feature_files_path"] = feature_path
        
        # Java source path
        java_default = detected.get('java_src_path', 'src/main/java')
        java_path = Prompt.ask(
            "Java source path (from repository root) [or press Enter to use detected]",
            default=java_default
        )
        
        # If user provided Java path and we don't have detections yet
        if java_path and not detected:
            detected = _detect_related_paths(java_path, 'java')
        
        if java_path:
            config["java_src_path"] = java_path
        
        # Step definitions path
        if migration_type == MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT:
            # First check if user wants to provide step definitions to auto-detect others
            if not detected:
                step_hint = Prompt.ask(
                    "Step definitions path (from repository root) [or press Enter to skip]",
                    default="src/test/java"
                )
                if step_hint and 'stepdefinition' in step_hint.lower():
                    detected = _detect_related_paths(step_hint, 'step')
                    config["step_definitions_path"] = step_hint
                    # Update Java path if detected
                    if not java_path and detected.get('java_src_path'):
                        config["java_src_path"] = detected['java_src_path']
                    # Update feature path if detected
                    if not feature_path and detected.get('feature_files_path'):
                        config["feature_files_path"] = detected['feature_files_path']
                elif step_hint:
                    config["step_definitions_path"] = step_hint
            else:
                # Use detected step definitions path
                step_default = detected.get('step_definitions_path', 'src/test/java')
                step_path = Prompt.ask(
                    "Step definitions path (from repository root) [or press Enter to use detected]",
                    default=step_default
                )
                
                if step_path:
                    config["step_definitions_path"] = step_path
        
        # Show detected paths if any were auto-filled
        if detected:
            console.print("\n[dim]Detected related paths:[/dim]")
            for key, value in config.items():
                console.print(f"[dim]  {key}: {value}[/dim]")
            console.print()
    
    elif migration_type == MigrationType.PYTEST_TO_ROBOT:
        # Pytest projects
        console.print("[dim]Configure paths for Pytest project[/dim]")
        
        config["project_root"] = Prompt.ask(
            "Project root directory",
            default="."
        )
        
        config["tests_path"] = Prompt.ask(
            "Tests directory path",
            default="tests"
        )
        
        config["fixtures_path"] = Prompt.ask(
            "Fixtures/conftest path",
            default="tests"
        )
    
    # Common: Ask for Page Objects and Locators for all migration types
    console.print("\n[bold cyan]═══ Page Objects & Locators (Optional) ═══[/bold cyan]")
    console.print("[dim]Migrate your Page Object classes and locator definitions to Robot Framework resources.[/dim]")
    console.print("[dim]These will maintain their original folder structure under the robot base folder.[/dim]\n")
    
    # Page Objects
    console.print("[bold cyan]📦 Page Object Classes Path[/bold cyan] [dim](optional - recommended)[/dim]")
    console.print("[dim]Path to Page Object pattern classes (Java/Python).[/dim]")
    console.print("[dim]Examples: src/main/java/com/company/pages, src/main/java/com/company/pagefactory[/dim]\n")
    
    page_objects_path = Prompt.ask(
        "[yellow]Enter path[/yellow] [dim](press Enter to skip)[/dim]",
        default=""
    )
    
    if page_objects_path and page_objects_path.strip():
        config["page_objects_path"] = page_objects_path.strip()
        console.print(f"[green]✓[/green] Page Objects: [cyan]{page_objects_path.strip()}[/cyan]")
        console.print("[dim]  → Will be migrated to Robot Framework resources[/dim]")
        console.print("[dim]  → Original folder structure will be preserved[/dim]\n")
    else:
        console.print("[dim]  → Page objects migration skipped[/dim]\n")
    
    # Locators
    console.print("[bold cyan]🎯 Locator Files Path[/bold cyan] [dim](optional)[/dim]")
    console.print("[dim]Path to standalone locator definition files.[/dim]")
    console.print("[dim]Examples: src/main/java/locators, tests/locators, automation/selectors[/dim]\n")
    
    locators_path = Prompt.ask(
        "[yellow]Enter path[/yellow] [dim](press Enter to skip)[/dim]",
        default=""
    )
    
    if locators_path and locators_path.strip():
        config["locators_path"] = locators_path.strip()
        console.print(f"[green]✓[/green] Locators: [cyan]{locators_path.strip()}[/cyan]")
        console.print("[dim]  → Will be migrated to Robot Framework variables[/dim]\n")
    else:
        console.print("[dim]  → Locators migration skipped[/dim]\n")
    
    # Show summary
    console.print("[green]✓ Configuration Complete[/green]\n")
    console.print("[bold]Summary:[/bold]")
    for key, value in config.items():
        key_display = key.replace('_', ' ').title()
        console.print(f"  [cyan]{key_display}:[/cyan] {value}")
    console.print()
    
    return config


def prompt_robot_framework_config() -> Dict:
    """
    Prompt for Robot Framework test location and Page Object/Locator paths.
    
    Enhanced to support Phase 2 (Detection) and Phase 3 (Modernization) by collecting:
    - Robot test directory (required)
    - Page Object classes path (optional - for detection and transformation)
    - Locator files path (optional - for modernization analysis)
    
    Returns:
        Dict with configuration including robot_tests_path, page_objects_path, locators_path
    """
    
    console.print("\n[bold yellow]═══ Robot Framework Configuration ═══[/bold yellow]")
    console.print("[cyan]Configure your Robot Framework test structure.[/cyan]")
    console.print("[dim]All paths should be relative to the repository root.[/dim]\n")
    
    config = {}
    
    # 1. Robot test directory (REQUIRED)
    console.print("[bold cyan]📁 Robot Test Directory[/bold cyan] [red]*required[/red]")
    console.print("[dim]This is where your .robot test files are located.[/dim]")
    console.print("[dim]Examples: tests/robot, automation/robot, robot-tests[/dim]\n")
    
    while True:
        robot_path = Prompt.ask(
            "[yellow]Enter path[/yellow]",
            default=""
        )
        if robot_path and robot_path.strip():
            config["robot_tests_path"] = robot_path.strip()
            console.print(f"[green]✓[/green] Robot tests: [cyan]{robot_path.strip()}[/cyan]\n")
            break
        console.print("[red]⚠ Robot test directory is required[/red]\n")
    
    # 2. Page Object classes (OPTIONAL - Phase 2 Detection)
    console.print("[bold cyan]📦 Page Object Classes[/bold cyan] [dim](optional - recommended)[/dim]")
    console.print("[dim]Path to Page Object pattern classes (Java/Python).[/dim]")
    console.print("[dim]If provided, CrossBridge will:[/dim]")
    console.print("[dim]  • Detect Page Object patterns (Phase 2)[/dim]")
    console.print("[dim]  • Extract locator definitions[/dim]")
    console.print("[dim]  • Transform to Robot Framework resources[/dim]")
    console.print("[dim]  • Preserve locator semantics[/dim]")
    console.print("[dim]Examples: src/main/java/pages, tests/pages, automation/page_objects[/dim]\n")
    
    page_objects_path = Prompt.ask(
        "[yellow]Enter path[/yellow] [dim](press Enter to skip)[/dim]",
        default=""
    )
    
    if page_objects_path and page_objects_path.strip():
        config["page_objects_path"] = page_objects_path.strip()
        console.print(f"[green]✓[/green] Page Objects: [cyan]{page_objects_path.strip()}[/cyan]")
        console.print("[green]  → Phase 2 detection enabled[/green]\n")
    else:
        console.print("[dim]  → Page Object detection skipped[/dim]\n")
    
    # 3. Locator files (OPTIONAL - Phase 3 Modernization)
    console.print("[bold cyan]🎯 Locator Files[/bold cyan] [dim](optional - for quality analysis)[/dim]")
    console.print("[dim]Path to standalone locator definition files.[/dim]")
    console.print("[dim]If provided, CrossBridge will:[/dim]")
    console.print("[dim]  • Analyze locator quality (Phase 3)[/dim]")
    console.print("[dim]  • Detect brittle XPath patterns[/dim]")
    console.print("[dim]  • Suggest modern alternatives (CSS, data-testid)[/dim]")
    console.print("[dim]  • Generate quality reports[/dim]")
    console.print("[dim]Examples: src/main/java/locators, tests/locators, automation/selectors[/dim]\n")
    
    locators_path = Prompt.ask(
        "[yellow]Enter path[/yellow] [dim](press Enter to skip)[/dim]",
        default=""
    )
    
    if locators_path and locators_path.strip():
        config["locators_path"] = locators_path.strip()
        console.print(f"[green]✓[/green] Locators: [cyan]{locators_path.strip()}[/cyan]")
        console.print("[green]  → Phase 3 modernization analysis enabled[/green]\n")
    else:
        console.print("[dim]  → Locator analysis skipped[/dim]\n")
    
    # Show summary
    console.print("[bold green]✓ Configuration Complete[/bold green]")
    console.print("\n[dim]Summary:[/dim]")
    console.print(f"  [cyan]Robot Tests:[/cyan] {config['robot_tests_path']}")
    if "page_objects_path" in config:
        console.print(f"  [cyan]Page Objects:[/cyan] {config['page_objects_path']} [green](Phase 2 enabled)[/green]")
    else:
        console.print("  [dim]Page Objects: Not specified[/dim]")
    if "locators_path" in config:
        console.print(f"  [cyan]Locators:[/cyan] {config['locators_path']} [green](Phase 3 enabled)[/green]")
    else:
        console.print("  [dim]Locators: Not specified[/dim]")
    
    console.print()
    return config


def _detect_platform(repo_url: str) -> str:
    """Detect repository platform from URL."""
    url_lower = repo_url.lower()
    
    if "github.com" in url_lower:
        return "github"
    elif "bitbucket.org" in url_lower or "bitbucket.com" in url_lower:
        return "bitbucket"
    elif "dev.azure.com" in url_lower or "visualstudio.com" in url_lower:
        return "azure"
    elif "gitlab.com" in url_lower:
        return "gitlab"
    else:
        return "unknown"


def _prompt_authentication(platform: str, repo_url: Optional[str] = None, source_branch: Optional[str] = None, target_branch: Optional[str] = None, migration_mode: Optional['MigrationMode'] = None) -> RepositoryAuth:
    """Prompt for repository authentication.
    
    Args:
        platform: Platform name (bitbucket, github, etc.)
        repo_url: Repository URL for caching
        source_branch: Source branch for caching
        target_branch: Target branch for caching
        migration_mode: Migration mode (TEST mode enables auto-caching)
    """
    
    console.print(f"\n[cyan]Authentication for {platform.title()}[/cyan]")
    
    # Check for cached test credentials (test mode only)
    try:
        from core.repo.test_credentials import get_test_bitbucket_creds, get_test_github_creds
        
        if platform == "bitbucket":
            try:
                cached_username, cached_token, cached_repo, cached_source_branch, cached_target_branch = get_test_bitbucket_creds(auto_cache=False)
                
                # Display cached credentials in user-friendly, masked format
                console.print("[green]✓ Found cached test credentials[/green]")
                console.print(f"  [cyan]Username:[/cyan] {_mask_username(cached_username)}")
                console.print(f"  [cyan]Token:[/cyan]    {_mask_token(cached_token)}")
                if cached_repo:
                    console.print(f"  [yellow]📁 Repository:[/yellow] [bold]{cached_repo}[/bold]")
                if cached_source_branch:
                    console.print(f"  [yellow]🌱 Source Branch:[/yellow] [bold]{cached_source_branch}[/bold]")
                if cached_target_branch:
                    console.print(f"  [yellow]🌿 Target Branch:[/yellow] [bold]{cached_target_branch}[/bold]")
                
                if Confirm.ask("\n[bold]Use these cached credentials?[/bold]", default=True):
                    console.print("[dim]✓ Using cached test credentials[/dim]")
                    return RepositoryAuth(
                        auth_type=AuthType.BITBUCKET_TOKEN,
                        username=cached_username,
                        token=cached_token
                    )
                else:
                    console.print("[yellow]Prompting for new credentials...[/yellow]")
            except ValueError:
                # No cached credentials, continue to prompt
                console.print("[dim]No cached credentials found[/dim]")
            except Exception as e:
                # Other errors (decryption, file corruption, etc.)
                console.print(f"[yellow]⚠ Could not load cached credentials: {str(e)}[/yellow]")
                console.print("[dim]Prompting for new credentials...[/dim]")
        
        elif platform == "github":
            try:
                cached_username, cached_token = get_test_github_creds(auto_cache=False)
                
                # Display cached credentials in user-friendly, masked format
                console.print("[green]✓ Found cached test credentials[/green]")
                console.print(f"  [cyan]Username:[/cyan] {_mask_username(cached_username)}")
                console.print(f"  [cyan]Token:[/cyan]    {_mask_token(cached_token)}")
                
                if Confirm.ask("\n[bold]Use these cached credentials?[/bold]", default=True):
                    console.print("[dim]✓ Using cached test credentials[/dim]")
                    return RepositoryAuth(
                        auth_type=AuthType.GITHUB_TOKEN,
                        token=cached_token
                    )
                else:
                    console.print("[yellow]Prompting for new credentials...[/yellow]")
            except ValueError:
                # No cached credentials, continue to prompt
                pass
    except ImportError:
        # test_credentials module not available
        pass
    
    if platform == "github":
        token = None
        while not token:
            console.print("[dim](Paste your token - first/last 4 chars will be shown)[/dim]")
            token_input = Prompt.ask(
                "GitHub personal access token (PAT)",
                password=True
            )
            if token_input and token_input.strip():
                token = token_input.strip()
                # Show masked token for confirmation
                masked = _mask_token(token)
                console.print(f"[dim]Token received: {masked}[/dim]")
            else:
                console.print("[red]Token is required. Please paste your GitHub PAT.[/red]")
        
        # Auto-cache credentials in TEST mode
        if migration_mode and migration_mode == MigrationMode.TEST:
            try:
                from core.repo.test_credentials import cache_test_github_creds
                cache_test_github_creds(
                    username=None,  # GitHub only needs token
                    token=token
                )
                console.print("[dim]✓ Credentials cached for future use[/dim]")
            except Exception as e:
                # Non-fatal - just log and continue
                console.print(f"[dim]Could not cache credentials: {e}[/dim]")
        
        return RepositoryAuth(
            auth_type=AuthType.GITHUB_TOKEN,
            token=token
        )
    
    elif platform == "bitbucket":
        console.print("[yellow]Note: Bitbucket API tokens require your account EMAIL address (not username)[/yellow]")
        username = ""
        while not username:
            username = Prompt.ask("Bitbucket email address")
            if not username:
                console.print("[red]Email address is required. Please enter your Bitbucket account email.[/red]")
            elif "@" not in username:
                console.print("[yellow]Warning: This doesn't look like an email address. Bitbucket API tokens require email.[/yellow]")
                if not Confirm.ask("Continue anyway?", default=False):
                    username = ""
        
        token = None
        while not token:
            console.print("[dim](Paste your token - first/last 4 chars will be shown)[/dim]")
            token_input = Prompt.ask(
                "Bitbucket API token (not app password)",
                password=True
            )
            if token_input and token_input.strip():
                token = token_input.strip()
                # Show masked token for confirmation
                masked = _mask_token(token)
                console.print(f"[dim]Token received: {masked}[/dim]")
            else:
                console.print("[red]Token is required. Please paste your Bitbucket API token.[/red]")
        
        # Auto-cache credentials in TEST mode
        if migration_mode and migration_mode == MigrationMode.TEST:
            try:
                from core.repo.test_credentials import cache_test_bitbucket_creds
                cache_test_bitbucket_creds(
                    username=username,
                    token=token,
                    repo_url=repo_url,
                    source_branch=source_branch,
                    target_branch=target_branch
                )
                console.print("[dim]✓ Credentials cached for future use[/dim]")
            except Exception as e:
                # Non-fatal - just log and continue
                console.print(f"[dim]Could not cache credentials: {e}[/dim]")
        
        return RepositoryAuth(
            auth_type=AuthType.BITBUCKET_TOKEN,
            username=username,
            token=token
        )
    
    elif platform == "azure":
        token = None
        while not token:
            console.print("[dim](Paste your token - first/last 4 chars will be shown)[/dim]")
            token_input = Prompt.ask(
                "Azure DevOps PAT",
                password=True
            )
            if token_input and token_input.strip():
                token = token_input.strip()
                # Show masked token for confirmation
                masked = _mask_token(token)
                console.print(f"[dim]Token received: {masked}[/dim]")
            else:
                console.print("[red]Token is required. Please enter a valid PAT.[/red]")
        return RepositoryAuth(
            auth_type=AuthType.AZURE_PAT,
            token=token
        )
    
    else:
        # Generic token
        token = None
        while not token:
            console.print("[dim](Paste your token - first/last 4 chars will be shown)[/dim]")
            token_input = Prompt.ask(
                "API token / Personal access token",
                password=True
            )
            if token_input and token_input.strip():
                token = token_input.strip()
                # Show masked token for confirmation
                masked = _mask_token(token)
                console.print(f"[dim]Token received: {masked}[/dim]")
            else:
                console.print("[red]Token is required. Please enter a valid token.[/red]")
        return RepositoryAuth(
            auth_type=AuthType.BITBUCKET_TOKEN,  # Default
            token=token
        )


def prompt_ai_settings() -> Dict:
    """Prompt for AI configuration."""
    
    use_ai = Confirm.ask(
        "\nEnable AI-assisted migration?",
        default=True
    )
    
    if not use_ai:
        return {"enabled": False}
    
    # AI Mode
    console.print("\n[1] Public Cloud (OpenAI/Anthropic)")
    console.print("[2] On-Premises / Self-Hosted")
    console.print("[3] Disabled\n")
    
    mode_choice = Prompt.ask(
        "AI mode",
        choices=["1", "2", "3"],
        default="1"
    )
    
    mode_mapping = {
        "1": AIMode.PUBLIC_CLOUD,
        "2": AIMode.ON_PREM,
        "3": AIMode.DISABLED
    }
    
    ai_mode = mode_mapping[mode_choice]
    
    if ai_mode == AIMode.DISABLED:
        return {"enabled": False}
    
    # Provider and API key
    if ai_mode == AIMode.PUBLIC_CLOUD:
        console.print("\n[1] OpenAI")
        console.print("[2] Anthropic (Claude)\n")
        
        provider_choice = Prompt.ask(
            "AI Provider",
            choices=["1", "2"],
            default="1"
        )
        
        provider = "openai" if provider_choice == "1" else "anthropic"
        
        api_key = Prompt.ask(
            f"{provider.title()} API Key",
            password=True
        )
        
        return {
            "enabled": True,
            "config": AIConfig(
                mode=ai_mode,
                provider=provider,
                api_key=api_key
            )
        }
    
    else:  # On-prem
        endpoint = Prompt.ask("AI endpoint URL")
        api_key = Prompt.ask("API Key", password=True)
        
        return {
            "enabled": True,
            "config": AIConfig(
                mode=ai_mode,
                provider="custom",
                api_endpoint=endpoint,
                api_key=api_key
            )
        }


def confirm_migration(dry_run: bool = False, operation_type: OperationType = OperationType.MIGRATION_AND_TRANSFORMATION) -> bool:
    """Confirm before starting migration."""
    
    if operation_type == OperationType.TRANSFORMATION:
        action = "Preview transformation" if dry_run else "Start transformation"
    elif operation_type == OperationType.MIGRATION:
        action = "Preview migration" if dry_run else "Start migration"
    else:  # MIGRATION_AND_TRANSFORMATION
        action = "Preview migration" if dry_run else "Start migration"
    
    return Confirm.ask(
        f"\n{action}?",
        default=True
    )
