"""
CrossBridge Authentication Commands

Manage repository and AI provider credentials for local testing.
Credentials are encrypted using AES-128 (Fernet) and stored securely.

⚠️  FOR TEST/DEVELOPMENT USE ONLY - NOT FOR PRODUCTION
"""

import typer
from typing import Optional

# Create auth app
auth_app = typer.Typer(help="Manage repository and AI credentials")


@auth_app.command("add")
def add_credentials(
    ai: bool = typer.Option(False, "--ai", help="Add AI provider credentials"),
    platform: Optional[str] = typer.Option(None, "--platform", help="Platform: bitbucket, github, openai, anthropic, selfhosted"),
    username: Optional[str] = typer.Option(None, "--username", help="Username/email"),
    token: Optional[str] = typer.Option(None, "--token", help="Access token/password"),
    repo_url: Optional[str] = typer.Option(None, "--repo-url", help="Repository URL")
):
    """
    Add and cache credentials for repository or AI providers.
    
    Credentials are encrypted using AES-128 (Fernet) and stored securely.
    
    Examples:
        crossbridge auth add                  # Interactive menu
        crossbridge auth add --platform bitbucket
        crossbridge auth add --ai --platform openai
    """
    # Reuse existing implementation from cli.app
    from cli.app import _handle_credential_action
    action = "cache-ai" if ai else "cache"
    _handle_credential_action(action=action, platform=platform, username=username, token=token, repo_url=repo_url)


@auth_app.command("list")
def list_credentials():
    """
    List all cached credentials.
    
    Shows repository and AI provider credentials with masked values.
    
    Example:
        crossbridge auth list
    """
    from cli.app import _handle_credential_action
    _handle_credential_action(action="list", platform=None, username=None, token=None, repo_url=None)


@auth_app.command("remove")
def remove_credentials(
    platform: Optional[str] = typer.Option(None, "--platform", help="Platform: bitbucket, github, openai, anthropic, selfhosted, all-ai, all"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """
    Remove cached credentials.
    
    Examples:
        crossbridge auth remove                      # Interactive selection
        crossbridge auth remove --platform openai
        crossbridge auth remove --platform all --yes
    """
    from cli.app import _handle_credential_action
    
    # Set environment variable to skip confirmation if --yes flag is used
    if yes:
        import os
        os.environ['CROSSBRIDGE_AUTH_SKIP_CONFIRM'] = '1'
    
    _handle_credential_action(action="clear", platform=platform, username=None, token=None, repo_url=None)


@auth_app.command("verify")
def verify_credentials(
    platform: Optional[str] = typer.Option(None, "--platform", help="Platform: bitbucket, github, openai, anthropic, selfhosted")
):
    """
    Test cached credentials to verify they still work.
    
    Examples:
        crossbridge auth verify                      # Interactive selection
        crossbridge auth verify --platform bitbucket
        crossbridge auth verify --platform openai
    """
    from cli.app import _handle_credential_action
    _handle_credential_action(action="test", platform=platform, username=None, token=None, repo_url=None)
