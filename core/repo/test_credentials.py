"""
Test credential caching for local development and unit testing.

⚠️  FOR TEST/DEVELOPMENT USE ONLY - NOT FOR PRODUCTION ⚠️

This module provides convenient caching of BitBucket and other repository
credentials specifically for testing purposes. Credentials are stored
securely using the existing CredentialManager.

IMPORTANT NOTES:
1. TEST MODE ONLY: These cached credentials are intended for local development
   and unit testing. DO NOT use in production environments.

2. PERSISTENCE: Cached credentials are stored on disk at ~/.crossbridge/credentials.enc
   and persist across VS Code restarts and machine reboots until explicitly cleared
   or overwritten.

3. CLI INTEGRATION: When using the interactive CLI menu (crossbridge-ai migrate),
   if cached test credentials exist, you'll be prompted to use them. Simply hit
   Enter to accept the cached values, or type 'n' to enter new credentials.

Usage in test files:
    from core.repo.test_credentials import get_test_bitbucket_creds, cache_test_bitbucket_creds
    
    # Cache credentials (first time only)
    cache_test_bitbucket_creds()
    
    # Use cached credentials in tests
    username, token, repo_url, target_branch = get_test_bitbucket_creds()
"""

import os
from typing import Optional, Tuple
from pathlib import Path

try:
    from .credentials import CredentialManager, RepoCredential
    CREDS_AVAILABLE = True
except ImportError:
    CREDS_AVAILABLE = False


# Special marker for test credentials (not tied to specific repo)
TEST_CREDS_OWNER = "_test_"
TEST_CREDS_REPO = "_cache_"


def _get_test_creds_manager() -> Optional['CredentialManager']:
    """Get credential manager for test credentials."""
    if not CREDS_AVAILABLE:
        return None
    
    try:
        return CredentialManager()
    except ImportError:
        # cryptography not installed
        return None


def cache_test_bitbucket_creds(username: Optional[str] = None, 
                                token: Optional[str] = None,
                                repo_url: Optional[str] = None,
                                source_branch: Optional[str] = None,
                                target_branch: Optional[str] = None,
                                force_prompt: bool = False) -> Tuple[str, str, str, str, str]:
    """
    Cache BitBucket test credentials for reuse.
    
    If credentials are already cached and force_prompt=False, returns cached values.
    Otherwise, prompts for new credentials or uses provided values.
    
    Args:
        username: BitBucket username/email (optional, will prompt if not provided)
        token: BitBucket API token (optional, will prompt if not provided)
        repo_url: BitBucket repository URL (optional, e.g., 'arcservedev/cc-ui-automation')
        source_branch: Source branch to migrate from (optional, e.g., 'main', 'develop')
        target_branch: Target branch for transformations (optional, e.g., 'feature/crossbridge-test-migration')
        force_prompt: If True, always prompt even if credentials cached
        
    Returns:
        Tuple of (username, token, repo_url, source_branch, target_branch)
        
    Example:
        # First time setup (or update credentials)
        cache_test_bitbucket_creds(force_prompt=True)
        
        # Pass credentials directly
        cache_test_bitbucket_creds(username="user@example.com", token="mytoken", 
                                   source_branch="main", target_branch="feature/test")
    """
    manager = _get_test_creds_manager()
    
    # If no credential manager, use environment variables only
    if not manager:
        if username is None:
            username = os.getenv('BITBUCKET_USERNAME', '')
            if not username:
                username = input("BitBucket username/email: ").strip()
                
        if token is None:
            token = os.getenv('BITBUCKET_TOKEN', '')
            if not token:
                import getpass
                token = getpass.getpass("BitBucket API token: ").strip()
        
        if repo_url is None:
            repo_url = os.getenv('BITBUCKET_REPO_URL', '')
            if not repo_url:
                repo_url = input("BitBucket repo URL (optional, e.g., arcservedev/cc-ui-automation): ").strip()
        
        if source_branch is None:
            source_branch = os.getenv('BITBUCKET_SOURCE_BRANCH', '')
            if not source_branch:
                source_branch = input("Source branch (optional, e.g., main, develop): ").strip()
        
        if target_branch is None:
            target_branch = os.getenv('BITBUCKET_TARGET_BRANCH', '')
            if not target_branch:
                target_branch = input("Target branch (optional, e.g., feature/crossbridge-test-migration): ").strip()
        
        print(f"✅ Using credentials for: {username}")
        print("💡 Install 'cryptography' for secure credential caching: pip install cryptography")
        return username, token, repo_url or "", source_branch or "", target_branch or ""
    
    # Check if credentials already cached (unless forcing prompt)
    if not force_prompt:
        # Try to load all credentials to find our test cache
        manager._load_credentials()
        for key, cred in manager._credentials.items():
            if cred.provider == "bitbucket" and cred.repo == TEST_CREDS_REPO:
                # If new parameters provided, check if they differ from cached
                has_updates = False
                
                # Check each parameter - treat empty string same as None
                if username and username != cred.owner:
                    has_updates = True
                if repo_url and repo_url != (cred.url or ""):
                    has_updates = True
                if source_branch and source_branch != (cred.source_branch or ""):
                    has_updates = True
                if target_branch and target_branch != (cred.target_branch or ""):
                    has_updates = True
                if token:  # New token always means update
                    has_updates = True
                
                # If no updates, return cached
                if not has_updates:
                    print(f"✅ Using cached BitBucket credentials for: {cred.owner}")
                    if cred.url:
                        print(f"   Repository: {cred.url}")
                    if cred.source_branch:
                        print(f"   Source Branch: {cred.source_branch}")
                    if cred.target_branch:
                        print(f"   Target Branch: {cred.target_branch}")
                    return cred.owner, cred.token, cred.url or "", cred.source_branch or "", cred.target_branch or ""
                
                # Has updates - use cached values as defaults for missing parameters
                if not username:
                    username = cred.owner
                if not token:
                    token = cred.token
                if not repo_url and cred.url:
                    repo_url = cred.url
                if not source_branch and cred.source_branch:
                    source_branch = cred.source_branch
                if not target_branch and cred.target_branch:
                    target_branch = cred.target_branch
                break
    
    # Get credentials (prompt or use provided)
    if username is None:
        username = os.getenv('BITBUCKET_USERNAME', '')
        if not username:
            print("\n🔐 BitBucket Test Credentials Setup")
            print("=" * 50)
            username = input("BitBucket username/email: ").strip()
            
    if token is None:
        token = os.getenv('BITBUCKET_TOKEN', '')
        if not token:
            import getpass
            token = getpass.getpass("BitBucket API token: ").strip()
    
    if repo_url is None:
        repo_url = os.getenv('BITBUCKET_REPO_URL', '')
        if not repo_url:
            repo_url = input("BitBucket repo URL (optional, e.g., arcservedev/cc-ui-automation): ").strip()
    
    if source_branch is None:
        source_branch = os.getenv('BITBUCKET_SOURCE_BRANCH', '')
        if not source_branch:
            source_branch = input("Source branch (optional, e.g., main, develop): ").strip()
    
    if target_branch is None:
        target_branch = os.getenv('BITBUCKET_TARGET_BRANCH', '')
        if not target_branch:
            target_branch = input("Target branch (optional, e.g., feature/crossbridge-test-migration): ").strip()
    
    if not username or not token:
        raise ValueError("Both username and token are required")
    
    # First, clear ALL existing test credentials for this platform (regardless of username)
    # since we want only one cached credential per platform
    manager._load_credentials()
    keys_to_delete = []
    for key, cred in manager._credentials.items():
        # Match by provider and TEST_CREDS_REPO marker
        if cred.provider == "bitbucket" and cred.repo == TEST_CREDS_REPO:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del manager._credentials[key]
    
    # Save after deletion to ensure clean state
    if keys_to_delete:
        manager._save_credentials()
    
    # Store new credentials (using owner field for username)
    cred = RepoCredential(
        provider="bitbucket",
        owner=username,  # Store username in owner field
        repo=TEST_CREDS_REPO,
        token=token,
        url=repo_url or None,
        source_branch=source_branch or None,
        target_branch=target_branch or None
    )
    manager.store(cred)
    
    print(f"✅ Cached BitBucket test credentials for: {username}")
    if repo_url:
        print(f"   Repository: {repo_url}")
    if source_branch:
        print(f"   Source Branch: {source_branch}")
    if target_branch:
        print(f"   Target Branch: {target_branch}")
    print(f"📁 Stored at: {manager.credentials_file}")
    print("💡 Credentials are encrypted and secure")
    
    return username, token, repo_url or "", source_branch or "", target_branch or ""


def get_test_bitbucket_creds(auto_cache: bool = True) -> Tuple[str, str, str, str, str]:
    """
    Get cached BitBucket test credentials.
    
    Args:
        auto_cache: If True and no cached credentials, prompt to cache them
        
    Returns:
        Tuple of (username, token, repo_url, source_branch, target_branch)
        
    Raises:
        ValueError: If no cached credentials and auto_cache=False
        
    Example:
        # In test file
        username, token, repo_url, source_branch, target_branch = get_test_bitbucket_creds()
    """
    manager = _get_test_creds_manager()
    
    # Try environment variables first
    env_username = os.getenv('BITBUCKET_USERNAME')
    env_token = os.getenv('BITBUCKET_TOKEN')
    env_repo_url = os.getenv('BITBUCKET_REPO_URL', '')
    env_source_branch = os.getenv('BITBUCKET_SOURCE_BRANCH', '')
    env_target_branch = os.getenv('BITBUCKET_TARGET_BRANCH', '')
    if env_username and env_token:
        return env_username, env_token, env_repo_url, env_source_branch, env_target_branch
    
    # Try cached credentials
    if manager:
        manager._load_credentials()
        for key, cred in manager._credentials.items():
            if cred.provider == "bitbucket" and cred.repo == TEST_CREDS_REPO:
                return cred.owner, cred.token, cred.url or "", cred.source_branch or "", cred.target_branch or ""  # owner field stores username
    
    # No cached credentials
    if not auto_cache:
        raise ValueError(
            "No cached BitBucket test credentials found. "
            "Run cache_test_bitbucket_creds() first or set BITBUCKET_USERNAME/BITBUCKET_TOKEN env vars"
        )
    
    # Auto-cache
    print("⚠️  No cached test credentials found")
    return cache_test_bitbucket_creds()



def clear_test_bitbucket_creds() -> bool:
    """
    Clear cached BitBucket test credentials.
    
    Returns:
        True if credentials were cleared, False if none existed
        
    Example:
        clear_test_bitbucket_creds()
    """
    manager = _get_test_creds_manager()
    if not manager:
        print("No credential manager available")
        return False
    
    # Find and delete bitbucket test credentials
    manager._load_credentials()
    deleted = False
    keys_to_delete = []
    
    for key, cred in manager._credentials.items():
        if cred.provider == "bitbucket" and cred.repo == TEST_CREDS_REPO:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del manager._credentials[key]
        deleted = True
    
    if deleted:
        manager._save_credentials()
        print("✅ Cleared cached BitBucket test credentials")
    else:
        print("ℹ️  No cached credentials to clear")
    
    return deleted


def cache_test_github_creds(username: Optional[str] = None,
                            token: Optional[str] = None,
                            force_prompt: bool = False) -> Tuple[str, str]:
    """
    Cache GitHub test credentials for reuse.
    
    Similar to cache_test_bitbucket_creds() but for GitHub.
    
    Args:
        username: GitHub username (optional)
        token: GitHub PAT (optional)
        force_prompt: If True, always prompt
        
    Returns:
        Tuple of (username, token)
    """
    manager = _get_test_creds_manager()
    
    if not manager:
        if username is None:
            username = os.getenv('GITHUB_USERNAME', '')
            if not username:
                username = input("GitHub username: ").strip()
                
        if token is None:
            token = os.getenv('GITHUB_TOKEN', '')
            if not token:
                import getpass
                token = getpass.getpass("GitHub PAT: ").strip()
        
        print(f"✅ Using credentials for: {username}")
        return username, token
    
    if not force_prompt:
        # Try to load all credentials to find our test cache
        manager._load_credentials()
        for key, cred in manager._credentials.items():
            if cred.provider == "github" and cred.repo == TEST_CREDS_REPO:
                print(f"✅ Using cached GitHub credentials for: {cred.owner}")
                return cred.owner, cred.token
    
    if username is None:
        username = os.getenv('GITHUB_USERNAME', '')
        if not username:
            print("\n🔐 GitHub Test Credentials Setup")
            username = input("GitHub username: ").strip()
            
    if token is None:
        token = os.getenv('GITHUB_TOKEN', '')
        if not token:
            import getpass
            token = getpass.getpass("GitHub PAT: ").strip()
    
    if not username or not token:
        raise ValueError("Both username and token are required")
    
    # First, clear ALL existing test credentials for this platform (regardless of username)
    # since we want only one cached credential per platform
    manager._load_credentials()
    keys_to_delete = []
    for key, cred in manager._credentials.items():
        # Match by provider and TEST_CREDS_REPO marker
        if cred.provider == "github" and cred.repo == TEST_CREDS_REPO:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del manager._credentials[key]
    
    # Save after deletion to ensure clean state
    if keys_to_delete:
        manager._save_credentials()
    
    # Store new credentials
    cred = RepoCredential(
        provider="github",
        owner=username,
        repo=TEST_CREDS_REPO,
        token=token
    )
    manager.store(cred)
    
    print(f"✅ Cached GitHub test credentials for: {username}")
    print(f"📁 Stored at: {manager.credentials_file}")
    
    return username, token


def get_test_github_creds(auto_cache: bool = True) -> Tuple[str, str]:
    """Get cached GitHub test credentials."""
    manager = _get_test_creds_manager()
    
    env_username = os.getenv('GITHUB_USERNAME')
    env_token = os.getenv('GITHUB_TOKEN')
    if env_username and env_token:
        return env_username, env_token
    
    if manager:
        manager._load_credentials()
        for key, cred in manager._credentials.items():
            if cred.provider == "github" and cred.repo == TEST_CREDS_REPO:
                return cred.owner, cred.token
    
    if not auto_cache:
        raise ValueError("No cached GitHub test credentials found")
    
    print("⚠️  No cached test credentials found")
    return cache_test_github_creds()


def clear_test_github_creds() -> bool:
    """
    Clear cached GitHub test credentials.
    
    Returns:
        True if credentials were cleared, False if none existed
        
    Example:
        clear_test_github_creds()
    """
    manager = _get_test_creds_manager()
    if not manager:
        print("No credential manager available")
        return False
    
    # Find and delete github test credentials
    manager._load_credentials()
    deleted = False
    keys_to_delete = []
    
    for key, cred in manager._credentials.items():
        if cred.provider == "github" and cred.repo == TEST_CREDS_REPO:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del manager._credentials[key]
        deleted = True
    
    if deleted:
        manager._save_credentials()
        print("✅ Cleared cached GitHub test credentials")
    else:
        print("ℹ️  No cached credentials to clear")
    
    return deleted


def list_cached_test_creds():
    """List all cached test credentials (with masked display)."""
    manager = _get_test_creds_manager()
    if not manager:
        print("Credential manager not available")
        return
    
    manager._load_credentials()
    test_creds = [
        cred for cred in manager._credentials.values()
        if cred.repo == TEST_CREDS_REPO
    ]
    
    ai_creds = [
        cred for cred in manager._credentials.values()
        if cred.repo == "_ai_cache_"
    ]
    
    if not test_creds and not ai_creds:
        print("No cached credentials")
        return
    
    def mask_username(username: str) -> str:
        """Mask username for display."""
        if "@" in username:
            local, domain = username.split("@", 1)
            if len(local) <= 3:
                masked_local = local[0] + "**"
            elif len(local) <= 6:
                masked_local = local[:2] + "***"
            else:
                masked_local = local[:3] + "***" + local[-2:]
            return f"{masked_local}@{domain}"
        else:
            if len(username) <= 4:
                return username[0] + "***"
            elif len(username) <= 8:
                return username[:2] + "***" + username[-1]
            else:
                return username[:3] + "***" + username[-2:]
    
    def mask_token(token: str) -> str:
        """Mask token for display."""
        if len(token) <= 8:
            return f"{token[:2]}...{token[-2:]}"
        elif len(token) <= 16:
            return f"{token[:3]}...{token[-3:]}"
        else:
            return f"{token[:4]}...{token[-4:]}"
    
    if test_creds:
        print("\n🔐 Cached Repository Credentials:")
        print("=" * 50)
        for cred in test_creds:
            print(f"  {cred.provider}:")
            print(f"    Username: {mask_username(cred.owner)}")
            print(f"    Token:    {mask_token(cred.token)}")
            if cred.url:
                print(f"    📁 Repository: {cred.url}")
            if cred.source_branch:
                print(f"    🌱 Source Branch: {cred.source_branch}")
            if cred.target_branch:
                print(f"    🌿 Target Branch: {cred.target_branch}")
    
    if ai_creds:
        print("\n🤖 Cached AI Provider Credentials:")
        print("=" * 50)
        for cred in ai_creds:
            print(f"  {cred.provider.upper()}:")
            print(f"    API Key: {mask_token(cred.token)}")


def cache_ai_credentials(provider: Optional[str] = None,
                        api_key: Optional[str] = None,
                        force_prompt: bool = False) -> Tuple[str, str]:
    """
    Cache AI provider credentials (OpenAI/Anthropic) for reuse.
    
    Args:
        provider: AI provider ('openai' or 'anthropic')
        api_key: API key for the provider
        force_prompt: If True, always prompt even if credentials cached
        
    Returns:
        Tuple of (provider, api_key)
        
    Example:
        cache_ai_credentials(provider="openai", api_key="sk-...")
        cache_ai_credentials(force_prompt=True)  # Interactive
    """
    manager = _get_test_creds_manager()
    
    # If no credential manager, use environment variables only
    if not manager:
        if provider is None:
            provider = input("AI Provider (openai/anthropic): ").strip().lower()
        
        if api_key is None:
            import getpass
            api_key = getpass.getpass(f"{provider.title()} API key: ").strip()
        
        # Set environment variable
        env_var = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        os.environ[env_var] = api_key
        
        print(f"✅ Using {provider} credentials")
        print("💡 Install 'cryptography' for secure credential caching: pip install cryptography")
        return provider, api_key
    
    # Check if credentials already cached (unless forcing prompt)
    if not force_prompt:
        manager._load_credentials()
        for key, cred in manager._credentials.items():
            if cred.provider == provider and cred.repo == "_ai_cache_":
                if api_key and api_key != cred.token:
                    # New API key provided - update it
                    break
                print(f"✅ Using cached {provider} credentials")
                return provider, cred.token
    
    # Prompt for credentials if needed
    if provider is None:
        print("\n🤖 Select AI Provider:")
        print("  1. OpenAI (GPT-4, GPT-3.5)")
        print("  2. Anthropic (Claude)")
        choice = input("Choice (1/2): ").strip()
        provider = "openai" if choice == "1" else "anthropic"
    
    if api_key is None:
        import getpass
        print(f"\n🔑 Enter {provider.title()} API Key:")
        if provider == "openai":
            print("  Get your key at: https://platform.openai.com/api-keys")
        else:
            print("  Get your key at: https://console.anthropic.com/")
        api_key = getpass.getpass("API Key: ").strip()
    
    # Store credentials
    cred = RepoCredential(
        provider=provider,
        owner="_ai_",
        repo="_ai_cache_",
        token=api_key
    )
    
    manager.store(cred)
    
    # Also set environment variable for immediate use
    env_var = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    os.environ[env_var] = api_key
    
    print(f"✅ {provider.title()} credentials cached successfully!")
    print(f"   Stored securely in: {manager.credentials_file}")
    
    return provider, api_key


def get_ai_credentials(provider: str, auto_cache: bool = True) -> Optional[str]:
    """
    Get AI provider credentials from cache or environment.
    
    Args:
        provider: AI provider ('openai' or 'anthropic')
        auto_cache: If True and not cached, prompt to cache
        
    Returns:
        API key or None if not found
        
    Example:
        api_key = get_ai_credentials('openai')
    """
    manager = _get_test_creds_manager()
    
    # Try environment variable first
    env_var = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    env_key = os.getenv(env_var)
    if env_key:
        return env_key
    
    if not manager:
        return None
    
    # Try cached credentials
    manager._load_credentials()
    for key, cred in manager._credentials.items():
        if cred.provider == provider and cred.repo == "_ai_cache_":
            # Set environment variable for compatibility
            os.environ[env_var] = cred.token
            return cred.token
    
    # Not found - prompt to cache if auto_cache enabled
    if auto_cache:
        print(f"\n⚠️  No cached {provider} credentials found")
        response = input(f"Cache {provider} credentials now? (y/n): ").strip().lower()
        if response == 'y':
            _, api_key = cache_ai_credentials(provider=provider, force_prompt=True)
            return api_key
    
    return None


def clear_ai_credentials(provider: Optional[str] = None) -> bool:
    """
    Clear cached AI credentials.
    
    Args:
        provider: Specific provider to clear ('openai'/'anthropic'), or None for all
        
    Returns:
        True if credentials were cleared, False if none found
    """
    manager = _get_test_creds_manager()
    if not manager:
        return False
    
    manager._load_credentials()
    cleared = False
    
    # Find and remove AI credentials
    keys_to_remove = []
    for key, cred in manager._credentials.items():
        if cred.repo == "_ai_cache_":
            if provider is None or cred.provider == provider:
                keys_to_remove.append(key)
                cleared = True
    
    for key in keys_to_remove:
        del manager._credentials[key]
    
    if cleared:
        manager._save_credentials()
        print(f"✅ Cleared {provider or 'all'} AI credentials")
    
    return cleared


if __name__ == "__main__":
    """Interactive credential caching for test setup."""
    import sys
    
    print("\n🔐 CrossBridge Test Credential Manager")
    print("=" * 50)
    print("\nAvailable commands:")
    print("  1. Cache BitBucket credentials")
    print("  2. Cache GitHub credentials")
    print("  3. Cache AI credentials (OpenAI/Anthropic)")
    print("  4. List cached credentials")
    print("  5. Clear BitBucket credentials")
    print("  6. Clear AI credentials")
    print("  7. Exit")
    
    while True:
        print("\n" + "=" * 50)
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == "1":
            try:
                cache_test_bitbucket_creds(force_prompt=True)
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == "2":
            try:
                cache_test_github_creds(force_prompt=True)
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "3":
            try:
                cache_ai_credentials(force_prompt=True)
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == "4":
            list_cached_test_creds()
            
        elif choice == "5":
            clear_test_bitbucket_creds()
        
        elif choice == "6":
            provider = input("Clear which provider? (openai/anthropic/all): ").strip().lower()
            if provider == "all":
                clear_ai_credentials()
            else:
                clear_ai_credentials(provider)
            
        elif choice == "7" or choice.lower() == 'q':
            print("\n✅ Goodbye!")
            break
            
        else:
            print("❌ Invalid option. Please select 1-7.")
