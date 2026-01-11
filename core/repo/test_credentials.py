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
    
    if not test_creds:
        print("No cached test credentials")
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
    
    print("\n🔐 Cached Test Credentials:")
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


if __name__ == "__main__":
    """Interactive credential caching for test setup."""
    import sys
    
    print("\n🔐 CrossBridge Test Credential Manager")
    print("=" * 50)
    print("\nAvailable commands:")
    print("  1. Cache BitBucket credentials")
    print("  2. Cache GitHub credentials")
    print("  3. List cached credentials")
    print("  4. Clear BitBucket credentials")
    print("  5. Exit")
    
    while True:
        print("\n" + "=" * 50)
        choice = input("\nSelect option (1-5): ").strip()
        
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
            list_cached_test_creds()
            
        elif choice == "4":
            clear_test_bitbucket_creds()
            
        elif choice == "5" or choice.lower() == 'q':
            print("\n✅ Goodbye!")
            break
            
        else:
            print("❌ Invalid option. Please select 1-5.")
