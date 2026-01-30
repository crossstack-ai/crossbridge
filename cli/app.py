"""
Interactive CLI for CrossBridge by CrossStack AI.

Main entry point using Typer for command routing and Rich for UI.
Follows Terraform/AWS CLI patterns: clean, conversational, professional.

Product: CrossBridge
Company: CrossStack AI
"""

import typer
import sys
import logging
from typing import Optional

from cli.branding import (
    show_welcome,
    show_migration_summary,
    show_completion,
    show_error,
    show_step
)
from cli.prompts import (
    prompt_migration_type,
    prompt_repository,
    prompt_ai_settings,
    confirm_migration,
    prompt_log_level,
    prompt_framework_config,
    prompt_robot_framework_config,
    prompt_migration_mode,
    prompt_transformation_mode,
    prompt_create_pr
)
from cli.progress import MigrationProgressTracker
from core.orchestration import MigrationOrchestrator, MigrationRequest
from services.logging_service import setup_logging

# Import coverage commands
from cli.commands.coverage_commands import coverage_group
from cli.commands.flaky import flaky_group
from cli.commands.memory import memory_app, search_app
from cli.commands.analyze import analyze_group

app = typer.Typer(
    name="crossbridge",
    help="CrossBridge by CrossStack AI - Test Framework Migration",
    add_completion=False,
    invoke_without_command=True
)

# Add coverage commands subgroup
app.add_typer(coverage_group, name="coverage")
# Add flaky detection commands
app.add_typer(flaky_group, name="flaky")
# Add memory and semantic search commands
app.add_typer(memory_app, name="memory")
app.add_typer(search_app, name="search")
# Add execution intelligence commands
app.add_typer(analyze_group, name="analyze")

# Install custom exception hook to suppress tracebacks in CLI
def _custom_exception_hook(exc_type, exc_value, exc_traceback):
    """Custom exception hook that logs exceptions but doesn't print tracebacks to console."""
    # Only log to file, don't print to console
    if exc_type is KeyboardInterrupt:
        # Let KeyboardInterrupt propagate normally
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Log to file only
    logger = logging.getLogger(__name__)
    logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = _custom_exception_hook


@app.callback(invoke_without_command=True)
def main_menu(ctx: typer.Context):
    """CrossBridge Main Menu - Interactive CLI for test framework operations."""
    # If a subcommand was invoked, don't show the menu
    if ctx.invoked_subcommand is not None:
        return
    
    from rich.console import Console
    from rich.prompt import Prompt
    
    console = Console()
    
    # Show welcome
    show_welcome()
    
    console.print("\n[cyan]═══ CrossBridge Main Menu ═══[/cyan]\n")
    console.print("[1] [green]Migration[/green] - Convert tests to Robot Framework")
    console.print("    • Migrate from existing frameworks")
    console.print("    • Convert to Robot Framework syntax\n")
    
    console.print("[2] [blue]Transformation[/blue] - Enhance Robot Framework tests")
    console.print("    • AI-powered improvements")
    console.print("    • Optimize existing Robot tests\n")
    
    console.print("[3] [magenta]Migration + Transformation[/magenta] - Complete workflow")
    console.print("    • Migrate AND transform in one operation")
    console.print("    • End-to-end conversion with enhancements\n")
    
    console.print("[4] [yellow]Test Credentials[/yellow] - Manage cached credentials")
    console.print("    • Cache repository credentials")
    console.print("    • View/Clear cached data\n")
    
    console.print("[5] [red]Exit[/red]\n")
    
    choice = Prompt.ask(
        "Enter choice [1–5] (default: 1)",
        choices=["1", "2", "3", "4", "5"],
        default="1",
        show_choices=False
    )
    
    if choice == "1":
        # Call migrate with explicit parameters for interactive mode
        ctx.invoke(migrate, repo_url=None, branch=None, dry_run=False, non_interactive=False)
    elif choice == "2":
        # Call transform with explicit parameters for interactive mode
        ctx.invoke(transform, repo_url=None, branch=None, target_branch=None, dry_run=False, non_interactive=False)
    elif choice == "3":
        # Call migrate_transform with explicit parameters for interactive mode
        ctx.invoke(migrate_transform, repo_url=None, branch=None, dry_run=False, non_interactive=False)
    elif choice == "4":
        # Call test_credentials with no action to show interactive menu
        ctx.invoke(test_credentials, action=None, platform=None, username=None, token=None, repo_url=None)
    elif choice == "5":
        console.print("\n[dim]Goodbye![/dim]")
        raise typer.Exit(0)


@app.command("migrate")
def migrate(
    repo_url: Optional[str] = typer.Option(None, "--repo", help="Repository URL"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Branch to migrate"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without committing"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Non-interactive mode for CI/CD")
):
    """
    Run test framework migration (convert to Robot Framework).
    
    Migrates your existing test framework to Robot Framework without transformation.
    
    Example:
        crossbridge migrate
        crossbridge migrate --repo https://github.com/org/repo --branch main
        crossbridge migrate --dry-run
    """
    from core.orchestration.models import OperationType
    _run_operation(
        operation_type=OperationType.MIGRATION,
        repo_url=repo_url,
        branch=branch,
        dry_run=dry_run,
        non_interactive=non_interactive
    )


@app.command("transform")
def transform(
    repo_url: Optional[str] = typer.Option(None, "--repo", help="Repository URL"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Branch with migrated tests"),
    target_branch: Optional[str] = typer.Option(None, "--target-branch", help="Branch containing migrated .robot files"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without committing"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Non-interactive mode for CI/CD")
):
    """
    Run transformation on already migrated Robot Framework tests.
    
    Enhances existing Robot Framework tests with AI-powered improvements.
    Requires tests to be already migrated to Robot Framework.
    
    Example:
        crossbridge transform
        crossbridge transform --repo https://github.com/org/repo --target-branch feature/migrated
        crossbridge transform --dry-run
    """
    from core.orchestration.models import OperationType
    _run_operation(
        operation_type=OperationType.TRANSFORMATION,
        repo_url=repo_url,
        branch=branch,
        target_branch=target_branch,
        dry_run=dry_run,
        non_interactive=non_interactive
    )


@app.command("migrate-transform")
def migrate_transform(
    repo_url: Optional[str] = typer.Option(None, "--repo", help="Repository URL"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Branch to migrate"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without committing"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Non-interactive mode for CI/CD")
):
    """
    Run migration and transformation together (full workflow).
    
    First migrates tests to Robot Framework, then applies AI-powered transformations.
    
    Example:
        crossbridge migrate-transform
        crossbridge migrate-transform --repo https://github.com/org/repo --branch main
        crossbridge migrate-transform --dry-run
    """
    from core.orchestration.models import OperationType
    _run_operation(
        operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
        repo_url=repo_url,
        branch=branch,
        dry_run=dry_run,
        non_interactive=non_interactive
    )


def _run_operation(
    operation_type,
    repo_url: Optional[str] = None,
    branch: Optional[str] = None,
    target_branch: Optional[str] = None,
    dry_run: bool = False,
    non_interactive: bool = False
):
    """
    Core operation runner for migration, transformation, or both.
    
    Args:
        operation_type: OperationType enum (MIGRATION, TRANSFORMATION, or MIGRATION_AND_TRANSFORMATION)
        repo_url: Repository URL (optional)
        branch: Source branch (optional)
        target_branch: Target branch for transformation (optional)
        dry_run: Preview mode flag
        non_interactive: Non-interactive mode flag
    """
    from core.orchestration.models import OperationType
    
    # Setup logging
    log_file = setup_logging()
    
    # Don't show welcome again if we came from main menu
    # (it's already shown in main_menu callback)
    # Only show it when commands are invoked directly
    import inspect
    caller_frame = inspect.currentframe().f_back
    if caller_frame and 'main_menu' not in str(caller_frame.f_code.co_name):
        show_welcome()
    
    try:
        # Interactive prompts (unless non-interactive)
        if not non_interactive:
            # 1. Environment (Test vs Live)
            migration_mode = prompt_migration_mode()
            
            # 2. Log level selection
            log_level = prompt_log_level()
            # Update logging level
            logging.getLogger().setLevel(getattr(logging, log_level))
            
            # 3. Migration type (only for MIGRATION and MIGRATION_AND_TRANSFORMATION)
            migration_type = None
            if operation_type in [OperationType.MIGRATION, OperationType.MIGRATION_AND_TRANSFORMATION]:
                migration_type = prompt_migration_type()
            # Note: For TRANSFORMATION only, migration_type remains None (not needed)
            
            # 4. Repository configuration (ask WHAT before asking HOW)
            # Determine if we need source branch based on operation type
            needs_migration = operation_type in [OperationType.MIGRATION, OperationType.MIGRATION_AND_TRANSFORMATION]
            migration_mode_for_prompt = "migration" if operation_type == OperationType.MIGRATION else (
                "both" if operation_type == OperationType.MIGRATION_AND_TRANSFORMATION else None
            )
            # Skip target branch prompt for TRANSFORMATION (will be asked separately)
            skip_target_branch = operation_type == OperationType.TRANSFORMATION
            repo_config = prompt_repository(
                repo_url, 
                branch, 
                migration_type=migration_mode_for_prompt,
                skip_target_branch=skip_target_branch,
                migration_mode=migration_mode  # Pass for auto-caching
            )
            
            # 5. For TRANSFORMATION, ask for target branch to use
            target_branch_for_transformation = target_branch
            if operation_type == OperationType.TRANSFORMATION:
                from rich.prompt import Prompt
                from rich.console import Console
                from core.repo.test_credentials import get_test_bitbucket_creds
                
                console = Console()
                
                # Try to get cached target branch
                cached_target_branch = None
                try:
                    _, _, _, _, cached_target_branch = get_test_bitbucket_creds(auto_cache=False)
                    if cached_target_branch:
                        console.print(f"\n[dim]💡 Using cached target branch: {cached_target_branch}[/dim]")
                except Exception as e:
                    logger.debug(f"Failed to retrieve cached credentials: {e}")
                
                console.print("\n[bold yellow]═══ Target Branch Selection ═══[/bold yellow]")
                console.print("[cyan]Specify the branch containing already migrated .robot files[/cyan]")
                console.print("[dim]This should be the branch where Migration was previously run[/dim]")
                console.print("[dim](e.g., feature/crossbridge-test-migration)[/dim]\n")
                
                # Use cached value as default if available
                default_branch = target_branch or cached_target_branch
                
                # Make this a required field - keep prompting until user provides a value
                while True:
                    if default_branch:
                        target_branch_for_transformation = Prompt.ask(
                            "[bold cyan]Target branch name[/bold cyan] [red]*required[/red]",
                            default=default_branch
                        )
                    else:
                        target_branch_for_transformation = Prompt.ask(
                            "[bold cyan]Target branch name[/bold cyan] [red]*required[/red]"
                        )
                    if target_branch_for_transformation and target_branch_for_transformation.strip():
                        target_branch_for_transformation = target_branch_for_transformation.strip()
                        break
                    console.print("[red]⚠ Target branch is required for Transformation operation[/red]")
                console.print()
            
            # 7. Framework-specific configuration
            # For TRANSFORMATION, only ask for Robot Framework location
            # For MIGRATION/MIGRATION_AND_TRANSFORMATION, ask for source framework paths
            if operation_type == OperationType.TRANSFORMATION:
                framework_config = prompt_robot_framework_config()
            else:
                framework_config = prompt_framework_config(migration_type)
            
            # 8. Transformation mode (ask AFTER we know WHAT to work on)
            # Only for TRANSFORMATION and MIGRATION_AND_TRANSFORMATION
            transformation_mode = None
            if operation_type in [OperationType.TRANSFORMATION, OperationType.MIGRATION_AND_TRANSFORMATION]:
                transformation_mode = prompt_transformation_mode()
            else:
                # For MIGRATION only, use default transformation mode
                from core.orchestration.models import TransformationMode
                transformation_mode = TransformationMode.MANUAL
            
            # 9. For TRANSFORMATION and MIGRATION_AND_TRANSFORMATION, ask about force retransform and tier selection
            force_retransform = False
            transformation_tier = None
            if operation_type in [OperationType.TRANSFORMATION, OperationType.MIGRATION_AND_TRANSFORMATION]:
                from cli.prompts import prompt_force_retransform, prompt_transformation_tier
                force_retransform = prompt_force_retransform(operation_type)
                # Always prompt for tier when transforming (not just on force_retransform)
                transformation_tier = prompt_transformation_tier(force_retransform, transformation_mode)
            
            # 10. AI settings
            ai_config = prompt_ai_settings()
            
            # 11. PR creation decision
            create_pr = prompt_create_pr(migration_mode)
            
            # Build request
            from core.orchestration import MigrationMode
            from core.orchestration.models import TransformationTier
            request = MigrationRequest(
                migration_mode=migration_mode,
                operation_type=operation_type,
                transformation_mode=transformation_mode,
                migration_type=migration_type,
                repo_url=repo_config["url"],
                branch=repo_config["branch"],
                auth=repo_config["auth"],
                use_ai=ai_config["enabled"],
                ai_config=ai_config.get("config"),
                dry_run=dry_run,
                create_pr=create_pr,
                framework_config=framework_config,
                force_retransform=force_retransform,
                transformation_tier=transformation_tier if transformation_tier else TransformationTier.TIER_1
            )
            
            # Set target branch based on operation type and mode
            if operation_type == OperationType.TRANSFORMATION:
                # For TRANSFORMATION, use the user-specified branch
                request.target_branch = target_branch_for_transformation
            elif migration_mode == MigrationMode.TEST:
                # In Test mode, use fixed branch name for overwriting
                request.target_branch = "feature/crossbridge-test-migration"
            
            # Show summary and confirm
            show_migration_summary(
                migration_type=migration_type.value if migration_type else "N/A",
                operation_type=operation_type.value,
                transformation_mode=transformation_mode.value if transformation_mode else "N/A",
                repo_url=request.repo_url,
                branch=request.branch,
                use_ai=request.use_ai,
                create_pr=create_pr,
                target_branch=target_branch_for_transformation,
                framework_config=framework_config,
                force_retransform=force_retransform,
                transformation_tier=transformation_tier.value if transformation_tier else None,
                ai_provider=ai_config.get("config").provider if request.use_ai and ai_config.get("config") else None,
                ai_model=ai_config.get("config").model if request.use_ai and ai_config.get("config") else None
            )
            
            if not confirm_migration(dry_run, operation_type):
                typer.echo("Operation cancelled.")
                raise typer.Exit(0)
        
        else:
            # Non-interactive mode - require all params
            if not repo_url:
                show_error("--repo is required in non-interactive mode", suggestion="Add --repo https://...")
                raise typer.Exit(1)
            
            # Build request from CLI params
            # (simplified - would need full auth config)
            raise NotImplementedError("Non-interactive mode coming soon")
        
        # Run migration with progress tracking
        # Use appropriate message based on operation type
        if operation_type == OperationType.TRANSFORMATION:
            show_step("Starting transformation")
        elif operation_type == OperationType.MIGRATION_AND_TRANSFORMATION:
            show_step("Starting migration and transformation")
        else:
            show_step("Starting migration")
        
        orchestrator = MigrationOrchestrator()
        progress_tracker = MigrationProgressTracker()
        
        response = orchestrator.run(
            request=request,
            progress_callback=progress_tracker.update
        )
        
        # Map operation_type enum to string for display
        if operation_type == OperationType.TRANSFORMATION:
            op_type_str = "transformation"
        elif operation_type == OperationType.MIGRATION_AND_TRANSFORMATION:
            op_type_str = "migration_and_transformation"
        else:
            op_type_str = "migration"
        
        # Show results
        if response.status.value == "completed":
            show_completion(
                pr_url=response.pr_url,
                log_file=str(log_file),
                duration=response.duration_seconds,
                operation_type=op_type_str
            )
        else:
            # Extract helpful suggestion from error message if present
            error_msg = response.error_message or "Unknown error"
            suggestion = None
            
            # Check if error message contains helpful suggestions (multi-line with bullet points)
            if "Possible causes:" in error_msg or "Please " in error_msg:
                # Extract only the first line for main error, rest for suggestion
                lines = error_msg.split('\n')
                if len(lines) > 1:
                    error_msg = lines[0]
                    suggestion = '\n'.join(lines[1:]).strip()
            
            # If no suggestion extracted, use default based on error code
            if not suggestion:
                suggestion = _get_error_suggestion(response.error_code)
            
            show_error(
                error_message=error_msg,
                error_code=response.error_code,
                suggestion=suggestion,
                log_file=str(log_file) if log_file else None
            )
            raise typer.Exit(1)
    
    except KeyboardInterrupt:
        show_error("Operation interrupted by user", log_file=str(log_file) if log_file else None)
        raise typer.Exit(130)
    
    except typer.Exit:
        # Let typer.Exit propagate without showing another error
        raise
    
    except Exception as e:
        show_error(str(e), suggestion="Check logs for details", log_file=str(log_file) if log_file else None)
        raise typer.Exit(1)


@app.command("version")
def version():
    """Display CrossBridge version."""
    typer.echo("CrossBridge 0.1.0 by CrossStack AI")
    typer.echo("Test Framework Migration Platform")


@app.command("test-creds")
def test_credentials(
    action: Optional[str] = typer.Option(None, "--action", help="Action: cache, list, clear, or test"),
    platform: Optional[str] = typer.Option(None, "--platform", help="Platform: bitbucket or github"),
    username: Optional[str] = typer.Option(None, "--username", help="Username/email"),
    token: Optional[str] = typer.Option(None, "--token", help="Access token/password"),
    repo_url: Optional[str] = typer.Option(None, "--repo-url", help="Repository URL")
):
    """
    Manage test mode credentials caching (BitBucket/GitHub).
    
    Cache credentials to avoid repeated entry during local testing.
    Credentials are encrypted using AES-128 (Fernet) and stored securely.
    
    ⚠️  FOR TEST/DEVELOPMENT USE ONLY - NOT FOR PRODUCTION
    
    Examples:
        crossbridge test-creds --action cache --platform bitbucket
        crossbridge test-creds --action list
        crossbridge test-creds --action clear --platform bitbucket
        crossbridge test-creds --action test --platform bitbucket
    """
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from core.repo.test_credentials import (
        cache_test_bitbucket_creds,
        cache_test_github_creds,
        get_test_bitbucket_creds,
        get_test_github_creds,
        clear_test_bitbucket_creds,
        clear_test_github_creds,
        list_cached_test_creds
    )
    
    console = Console()
    
    # Helper functions for masking
    def mask_username(username: str) -> str:
        """Mask username/email for display."""
        if '@' in username:
            local, domain = username.split('@', 1)
            if len(local) > 5:
                return f"{local[:3]}***{local[-2:]}@{domain}"
            return f"{local[:2]}***@{domain}"
        elif len(username) > 8:
            return f"{username[:4]}***{username[-2:]}"
        return f"{username[:2]}***"
    
    def mask_token(token: str) -> str:
        """Mask token for display."""
        if len(token) > 12:
            return f"{token[:4]}...{token[-4:]}"
        return "***"
    
    # Interactive menu if no action specified
    if not action:
        console.print("\n[cyan]═══ Test Credentials Management ═══[/cyan]")
        console.print("[yellow]⚠️  FOR TEST/DEVELOPMENT USE ONLY[/yellow]")
        console.print("[dim]Securely cache credentials to avoid repeated entry during local testing[/dim]\n")
        
        console.print("[cyan]Available Actions:[/cyan]")
        console.print("\n[1] [green]Cache[/green] - Store repository credentials")
        console.print("    • Securely encrypt and save credentials")
        console.print("    • Auto-fill in future test runs\n")
        console.print("[2] [cyan]List[/cyan] - View cached credentials")
        console.print("    • Display masked credentials")
        console.print("    • Show which repositories are cached\n")
        console.print("[3] [yellow]Clear[/yellow] - Remove cached credentials")
        console.print("    • Delete stored credentials")
        console.print("    • Select by platform\n")
        console.print("[4] [blue]Test[/blue] - Test cached credential connection")
        console.print("    • Verify credentials still work")
        console.print("    • Test repository access\n")
        console.print("[5] [red]Exit[/red]\n")
        
        choice = Prompt.ask(
            "Enter choice [1–5] (default: 1)",
            choices=["1", "2", "3", "4", "5"],
            default="1",
            show_choices=False
        )
        
        if choice == "1":
            action = "cache"
        elif choice == "2":
            action = "list"
        elif choice == "3":
            action = "clear"
        elif choice == "4":
            action = "test"
        else:
            console.print("[yellow]Exiting...[/yellow]")
            raise typer.Exit(0)
    
    # Execute action
    if action == "cache":
        # Ask for platform if not provided
        if not platform:
            console.print("\n[cyan]═══ Select Platform ═══[/cyan]")
            console.print("\n[1] BitBucket")
            console.print("[2] GitHub")
            console.print("[3] Azure DevOps")
            console.print("[4] GitLab")
            console.print("[5] TFS")
            console.print("[6] Other\n")
            
            choice = Prompt.ask(
                "Enter choice [1–6] (default: 1)",
                choices=["1", "2", "3", "4", "5", "6"],
                default="1",
                show_choices=False
            )
            platform_map = {
                "1": "bitbucket",
                "2": "github",
                "3": "azure",
                "4": "gitlab",
                "5": "tfs",
                "6": "other"
            }
            platform = platform_map[choice]
        
        # Try to get existing cached credentials for defaults
        existing_user = None
        existing_repo = None
        existing_source_branch = None
        existing_target_branch = None
        
        if platform == "bitbucket":
            try:
                existing_user, _, existing_repo, existing_source_branch, existing_target_branch = get_test_bitbucket_creds(auto_cache=False)
                console.print("[dim]Found existing cached credentials - showing as defaults[/dim]")
            except ValueError:
                # No cached credentials yet - that's fine
                pass
            except Exception as e:
                console.print(f"[dim yellow]Note: Could not load existing credentials: {e}[/dim yellow]")
        elif platform == "github":
            try:
                existing_user, _ = get_test_github_creds(auto_cache=False)
                console.print("[dim]Found existing cached credentials - showing as defaults[/dim]")
            except ValueError:
                # No cached credentials yet - that's fine
                pass
            except Exception as e:
                console.print(f"[dim yellow]Note: Could not load existing credentials: {e}[/dim yellow]")
        
        console.print(f"\n[cyan]═══ Cache {platform.title()} Credentials ═══[/cyan]")
        console.print("[yellow]⚠️  Credentials will be encrypted using AES-128 (Fernet)[/yellow]")
        console.print("[dim]Storage: ~/.crossbridge/credentials.enc[/dim]")
        if existing_user or existing_repo:
            console.print("[green]✓ Loading existing values as defaults[/green]")
        console.print()
        
        # Get credentials with defaults from cache if available
        if not username:
            if existing_user:
                console.print(f"[dim]Current cached: {mask_username(existing_user)}[/dim]")
                username = Prompt.ask("[bold]Username/Email[/bold] [dim](press Enter to keep current)[/dim]", default=existing_user)
            else:
                if platform == "bitbucket":
                    console.print("[dim]Example: user@example.com[/dim]")
                elif platform == "github":
                    console.print("[dim]Example: github-username[/dim]")
                username = Prompt.ask("[bold]Username/Email[/bold]")
        
        if not token:
            if existing_user:
                console.print("[dim]Enter new token or press Enter to keep existing[/dim]")
            token = Prompt.ask("[bold]Access Token/Password[/bold]", password=True)
        
        if not repo_url:
            if platform == "bitbucket":
                console.print("[dim]Example: https://bitbucket.org/yourorg/yourrepo[/dim]")
            elif platform == "github":
                console.print("[dim]Example: https://github.com/yourorg/yourrepo[/dim]")
            elif platform == "azure":
                console.print("[dim]Example: https://dev.azure.com/yourorg/yourproject[/dim]")
            elif platform == "gitlab":
                console.print("[dim]Example: https://gitlab.com/yourorg/yourrepo[/dim]")
            elif platform == "tfs":
                console.print("[dim]Example: http://tfs-server:8080/tfs/Collection[/dim]")
            
            if existing_repo:
                console.print(f"[dim]Current cached: {existing_repo}[/dim]")
                repo_url = Prompt.ask("[bold]Repository URL[/bold] [dim](press Enter to keep current)[/dim]", default=existing_repo)
            else:
                repo_url = Prompt.ask("[bold]Repository URL[/bold]")
        
        # Ask for source branch (for migration workflows)
        source_branch_input = None
        if platform == "bitbucket":
            console.print("\n[cyan]Source Branch (Optional)[/cyan]")
            console.print("[dim]Existing branch with code to migrate (e.g., main, develop)[/dim]")
            if existing_source_branch:
                console.print(f"[dim]Current cached: {existing_source_branch}[/dim]")
                source_branch_input = Prompt.ask(
                    "[bold]Source branch[/bold] [dim](press Enter to keep current or skip)[/dim]",
                    default=existing_source_branch
                )
            else:
                source_branch_input = Prompt.ask(
                    "[bold]Source branch[/bold] [dim](press Enter to skip)[/dim]",
                    default=""
                )
            if not source_branch_input or source_branch_input.strip() == "":
                source_branch_input = None
        
        # Ask for target branch (optional, for transformation workflows)
        target_branch_input = None
        if platform == "bitbucket":
            console.print("\n[cyan]Target Branch (Optional)[/cyan]")
            console.print("[dim]Branch containing migrated .robot files for transformation[/dim]")
            console.print("[dim]Example: feature/crossbridge-test-migration[/dim]")
            if existing_target_branch:
                console.print(f"[dim]Current cached: {existing_target_branch}[/dim]")
                target_branch_input = Prompt.ask(
                    "[bold]Target branch[/bold] [dim](press Enter to keep current or skip)[/dim]",
                    default=existing_target_branch
                )
            else:
                target_branch_input = Prompt.ask(
                    "[bold]Target branch[/bold] [dim](press Enter to skip)[/dim]",
                    default=""
                )
            if not target_branch_input or target_branch_input.strip() == "":
                target_branch_input = None
        
        # Cache based on platform
        try:
            if platform == "bitbucket":
                cached_user, cached_token, cached_repo, cached_source_branch, cached_target_branch = cache_test_bitbucket_creds(
                    username=username,
                    token=token,
                    repo_url=repo_url,
                    source_branch=source_branch_input,
                    target_branch=target_branch_input,
                    force_prompt=False
                )
            else:
                # GitHub cache returns (username, token) - no repo_url
                cached_user, cached_token = cache_test_github_creds(
                    username=username,
                    token=token,
                    force_prompt=False
                )
                cached_repo = repo_url  # Use the provided repo_url for display
                cached_branch = None  # GitHub doesn't cache branch
            
            console.print("\n[bold green]✓ Credentials cached successfully![/bold green]\n")
            console.print("[bold]Cached values:[/bold]")
            console.print(f"  Username: {mask_username(cached_user)}")
            console.print(f"  Token:    {mask_token(cached_token)}")
            if cached_repo:
                console.print(f"  📁 Repository: {cached_repo}")
            console.print("\n[dim]These credentials will be auto-offered during CLI prompts in test mode[/dim]")
            
        except Exception as e:
            console.print(f"\n[bold red]✗ Error caching credentials:[/bold red] {e}")
            raise typer.Exit(1)
    
    elif action == "list":
        console.print("\n[bold cyan]═══ Cached Test Credentials ═══[/bold cyan]\n")
        list_cached_test_creds()
        console.print()
    
    elif action == "clear":
        # Ask for platform if not provided
        if not platform:
            console.print("\n[bold cyan]═══ Select Platform ═══[/bold cyan]")
            platform = Prompt.ask(
                "[bold]Platform to clear[/bold]",
                choices=["bitbucket", "github", "all"],
                default="bitbucket"
            )
        
        # Confirm deletion
        if not Confirm.ask(f"\n[bold yellow]Clear cached {platform} credentials?[/bold yellow]", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
        
        try:
            if platform == "all":
                clear_test_bitbucket_creds()
                clear_test_github_creds()
                console.print("\n[bold green]✓ All cached credentials cleared[/bold green]")
            elif platform == "bitbucket":
                if clear_test_bitbucket_creds():
                    console.print("\n[bold green]✓ BitBucket credentials cleared[/bold green]")
                else:
                    console.print("\n[yellow]No BitBucket credentials found[/yellow]")
            else:
                if clear_test_github_creds():
                    console.print("\n[bold green]✓ GitHub credentials cleared[/bold green]")
                else:
                    console.print("\n[yellow]No GitHub credentials found[/yellow]")
        except Exception as e:
            console.print(f"\n[bold red]✗ Error clearing credentials:[/bold red] {e}")
            raise typer.Exit(1)
    
    elif action == "test":
        # Ask for platform if not provided
        if not platform:
            console.print("\n[bold cyan]═══ Select Platform ═══[/bold cyan]")
            platform = Prompt.ask(
                "[bold]Platform to test[/bold]",
                choices=["bitbucket", "github"],
                default="bitbucket"
            )
        
        console.print(f"\n[bold cyan]═══ Testing {platform.title()} Credentials ═══[/bold cyan]\n")
        
        try:
            if platform == "bitbucket":
                username, token, repo_url, source_branch, target_branch = get_test_bitbucket_creds(auto_cache=False)
            else:
                # GitHub returns (username, token) - no repo_url
                username, token = get_test_github_creds(auto_cache=False)
                repo_url = None
                source_branch = None
                target_branch = None
            
            if username and token:
                console.print("[bold green]✓ Cached credentials found:[/bold green]")
                console.print(f"  Username: {mask_username(username)}")
                console.print(f"  Token:    {mask_token(token)}")
                if repo_url:
                    console.print(f"  📁 Repository: {repo_url}")
                if source_branch:
                    console.print(f"  🌱 Source Branch: {source_branch}")
                if target_branch:
                    console.print(f"  🌿 Target Branch: {target_branch}")
                console.print("\n[dim]Note: Connection test not implemented (credentials retrieved successfully)[/dim]")
            else:
                console.print(f"[yellow]No cached {platform} credentials found[/yellow]")
                console.print(f"[dim]Use 'crossbridge test-creds --action cache --platform {platform}' to cache credentials[/dim]")
        except Exception as e:
            console.print(f"\n[bold red]✗ Error testing credentials:[/bold red] {e}")
            raise typer.Exit(1)
    
    else:
        console.print(f"[bold red]✗ Invalid action:[/bold red] {action}")
        console.print("[dim]Valid actions: cache, list, clear, test[/dim]")
        raise typer.Exit(1)


def _get_error_suggestion(error_code: Optional[str]) -> Optional[str]:
    """Get user-friendly suggestion for error code."""
    suggestions = {
        "CS-AUTH-001": "Check your credentials and repository permissions",
        "CS-REPO-001": "Verify repository URL and branch name",
        "CS-TRANSFORM-001": "Review source files for compatibility issues"
    }
    return suggestions.get(error_code) if error_code else None


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
