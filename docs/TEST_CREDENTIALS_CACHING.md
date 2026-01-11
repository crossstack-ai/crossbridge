# Test Credentials Caching

## ⚠️ IMPORTANT: Test Mode Only

**This feature is designed exclusively for local development and unit testing. DO NOT use cached test credentials in production environments.**

## Overview

The test credentials caching system allows you to securely store and reuse repository credentials during local development and unit testing. This eliminates the need to repeatedly enter credentials or maintain them in environment variables.

## Key Characteristics

### 1. Test Mode Only ✅
- Credentials are explicitly marked as "test" credentials
- Stored with special marker `_cache_` to distinguish from production credentials
- Intended for local development, not live/production use
- For production, use proper CI/CD secret management (GitHub Secrets, Azure Key Vault, etc.)

### 2. Persistent Storage ✅
- Credentials stored on disk at `~/.crossbridge/credentials.enc`
- **Persist across VS Code restarts** ✅
- **Persist across machine reboots** ✅
- Remain cached until explicitly cleared or overwritten
- Encrypted with Fernet (AES-128) for security

### 3. CLI Menu Integration ✅
- Interactive CLI automatically detects cached credentials
- When you run `crossbridge-ai migrate`, if cached credentials exist:
  - Shows: "✓ Found cached test credentials for: your-email@example.com"
  - Prompts: "Use cached credentials? [y/n] (y):"
  - **Just hit Enter** to use cached values (default is Yes)
  - Type 'n' to enter new credentials
- Seamless workflow - cache once, use everywhere

## Features

✅ **Encrypted Storage**: Credentials encrypted using Fernet (symmetric encryption)  
✅ **Auto-Detection**: Automatically uses cached credentials in test files  
✅ **Environment Fallback**: Falls back to environment variables if no cache  
✅ **Secure Location**: Stored at `~/.crossbridge/credentials.enc`  
✅ **Multiple Providers**: Supports BitBucket, GitHub, GitLab  

## Quick Start

### 1. Install Dependencies

The caching system requires the `cryptography` package:

```bash
pip install cryptography
```

If not installed, the system will fall back to prompting for credentials each time.

### 2. Cache Your Credentials (One Time Setup)

**Option A: Interactive Setup (Recommended)**

```bash
python setup_test_creds.py
```

Follow the prompts to cache your BitBucket credentials:
- Username/email: `your-email@example.com`
- Token: `your-api-token`
- Repository (optional): `arcservedev/cc-ui-automation`

**Option B: Quick Python Script**

```python
from core.repo.test_credentials import cache_test_bitbucket_creds

# Cache credentials interactively
cache_test_bitbucket_creds(force_prompt=True)

# Or provide directly
cache_test_bitbucket_creds(
    username="your-email@example.com",
    token="your-api-token",
    repo_url="arcservedev/cc-ui-automation"
)
```

### 3. Use in CLI Menu (Just Hit Enter!)

```bash
$ crossbridge-ai migrate

Authentication for Bitbucket
✓ Found cached test credentials for: your-email@example.com
  Repository: arcservedev/cc-ui-automation
Use cached credentials? [y/n] (y): ← JUST HIT ENTER HERE!
Using cached test credentials
```

**That's it!** No need to re-enter credentials. Just hit Enter when prompted.

### 4. Use in Test Files (Automatic)

Once cached, your test files automatically use the credentials:

```python
from core.repo.test_credentials import get_test_bitbucket_creds

# Automatically uses cached credentials (no prompt in test code)
username, token, repo_url = get_test_bitbucket_creds()

# Use in your test code
bb = Bitbucket(url='https://bitbucket.org', username=username, password=token, cloud=True)
```

## Cache Persistence & Lifetime

### How Long Do Cached Credentials Last?

**Cached credentials persist indefinitely until explicitly cleared or overwritten.**

✅ **Persists across**:
- VS Code restarts
- Terminal/PowerShell sessions
- Machine reboots
- Git branch switches
- Workspace changes

❌ **Does NOT clear on**:
- Closing VS Code
- Restarting computer
- Opening new terminal windows
- Switching git branches

### Why So Persistent?

Credentials are stored in **encrypted files on disk**:
```
~/.crossbridge/
├── .key                    # Encryption key
└── credentials.enc         # Encrypted credentials
```

These files remain on your filesystem until you explicitly delete them.

### How to Clear Cache

**Method 1: Interactive Tool**
```bash
python setup_test_creds.py
# Select option 4: Clear BitBucket credentials
```

**Method 2: Python Code**
```python
from core.repo.test_credentials import clear_test_bitbucket_creds
clear_test_bitbucket_creds()
```

**Method 3: Manual File Deletion**
```bash
# Windows PowerShell
Remove-Item -Recurse ~/.crossbridge

# Linux/Mac
rm -rf ~/.crossbridge
```

### When to Clear Cache

Clear cached credentials when:
- ✅ Rotating API tokens/passwords
- ✅ Switching to different test account
- ✅ Token has expired
- ✅ Decommissioning development machine
- ✅ Security policy requires it

You typically don't need to clear cache during normal development.

### Example 1: First-Time Setup

```bash
$ python setup_test_creds.py

============================================================
🔐 CrossBridge Test Credential Setup
============================================================

Available commands:
  1. Cache BitBucket credentials
  2. Cache GitHub credentials
  3. List cached credentials
  4. Clear BitBucket credentials
  5. Test BitBucket credentials
  6. Exit

Select option (1-6): 1

------------------------------------------------------------
🔐 BitBucket Test Credentials Setup
==================================================
BitBucket username/email: vverma_420@example.com
BitBucket API token: ••••••••••••••••

✅ Cached BitBucket test credentials for: vverma_420@example.com
📁 Stored at: C:\Users\YourName\.crossbridge\credentials.enc
💡 Credentials are encrypted and secure
```

### Example 2: Using in Test Files

**Before (manual entry each time):**

```python
import os
username = os.getenv('BITBUCKET_USERNAME', 'vverma_420')
password = os.getenv('BITBUCKET_TOKEN')  # Must be set!
```

**After (automatic from cache):**

```python
from core.repo.test_credentials import get_test_bitbucket_creds

# Automatically retrieves from cache, env, or prompts once
username, password = get_test_bitbucket_creds()
```

### Example 3: Updating Credentials

```python
from core.repo.test_credentials import cache_test_bitbucket_creds

# Force re-prompt and update
cache_test_bitbucket_creds(force_prompt=True)
```

### Example 4: Clearing Credentials

```python
from core.repo.test_credentials import clear_test_bitbucket_creds

# Remove cached credentials
clear_test_bitbucket_creds()
```

## Priority Order

The system checks credentials in this order:

1. **Environment Variables** (highest priority)
   - `BITBUCKET_USERNAME` / `BITBUCKET_TOKEN`
   - `GITHUB_USERNAME` / `GITHUB_TOKEN`

2. **Cached Credentials** (second priority)
   - Stored at `~/.crossbridge/credentials.enc`

3. **Interactive Prompt** (fallback)
   - Prompts user if nothing found
   - Auto-caches for future use

## Security

### Encryption

Credentials are encrypted using **Fernet (symmetric encryption)**:
- Industry-standard AES-128 encryption
- HMAC for authentication
- Timestamps for verification
- Key stored at `~/.crossbridge/.key` (0600 permissions)

### Storage

```
~/.crossbridge/
├── .key                    # Encryption key (read-only, owner only)
└── credentials.enc         # Encrypted credentials
```

### Best Practices

✅ **DO**:
- Use test credentials caching for local development
- Keep `~/.crossbridge/` directory private (0700 permissions)
- Rotate tokens periodically
- Use repository-specific tokens when possible

❌ **DON'T**:
- Commit `.crossbridge/` directory to git (already in .gitignore)
- Share encryption key with others
- Use production credentials in tests
- Store credentials in code or plaintext files

## API Reference

### `cache_test_bitbucket_creds()`

Cache BitBucket credentials for testing.

```python
cache_test_bitbucket_creds(
    username: Optional[str] = None,
    token: Optional[str] = None,
    force_prompt: bool = False
) -> Tuple[str, str]
```

**Parameters:**
- `username`: BitBucket email/username (prompts if None)
- `token`: BitBucket API token (prompts if None)
- `force_prompt`: Force re-prompt even if cached

**Returns:** `(username, token)` tuple

**Example:**
```python
# Interactive
username, token = cache_test_bitbucket_creds(force_prompt=True)

# Direct
username, token = cache_test_bitbucket_creds(
    username="user@example.com",
    token="abc123..."
)
```

### `get_test_bitbucket_creds()`

Get cached BitBucket credentials.

```python
get_test_bitbucket_creds(
    auto_cache: bool = True
) -> Tuple[str, str]
```

**Parameters:**
- `auto_cache`: If True, prompt to cache if not found

**Returns:** `(username, token)` tuple

**Raises:** `ValueError` if no credentials and `auto_cache=False`

**Example:**
```python
# Auto-cache if needed (recommended)
username, token = get_test_bitbucket_creds()

# Require cached credentials
try:
    username, token = get_test_bitbucket_creds(auto_cache=False)
except ValueError:
    print("Please cache credentials first")
```

### `clear_test_bitbucket_creds()`

Clear cached BitBucket credentials.

```python
clear_test_bitbucket_creds() -> bool
```

**Returns:** `True` if cleared, `False` if none existed

**Example:**
```python
if clear_test_bitbucket_creds():
    print("Credentials cleared")
```

### `list_cached_test_creds()`

List all cached test credentials (without tokens).

```python
list_cached_test_creds() -> None
```

**Example:**
```python
list_cached_test_creds()
# Output:
# 🔐 Cached Test Credentials:
# ==================================================
#   bitbucket: user@example.com
#   github: myusername
```

## Troubleshooting

### Issue: "cryptography is required"

**Solution:**
```bash
pip install cryptography
```

### Issue: "No cached credentials found"

**Solutions:**
1. Run setup script: `python setup_test_creds.py`
2. Set environment variables: `$env:BITBUCKET_USERNAME = "..."`
3. Let it prompt on first use (auto-caches)

### Issue: "Authentication failed"

**Solutions:**
1. Verify token is valid in BitBucket settings
2. Check token has correct permissions (e.g., "Repositories: Read")
3. Ensure username is email (for BitBucket API tokens)
4. Clear and re-cache: `python setup_test_creds.py` → option 4, then option 1

### Issue: "Permission denied on .crossbridge"

**Solution (Linux/Mac):**
```bash
chmod 700 ~/.crossbridge
chmod 600 ~/.crossbridge/.key
chmod 600 ~/.crossbridge/credentials.enc
```

**Solution (Windows):**
Permissions are typically fine by default. If issues persist, check that only your user account has access to the `.crossbridge` folder.

## Integration with Existing Tests

### Updating Test Files

Change this:
```python
username = os.getenv('BITBUCKET_USERNAME', 'default_user')
token = os.getenv('BITBUCKET_TOKEN')
```

To this:
```python
from core.repo.test_credentials import get_test_bitbucket_creds
username, token = get_test_bitbucket_creds()
```

### Updated Test Files

The following test files now use credential caching:

- [test_bitbucket_access.py](../test_bitbucket_access.py) ✅
- Future: `test_bb_*.py` files
- Future: `tests/unit/test_bitbucket_*.py`

## Environment Variables

For CI/CD or temporary overrides, environment variables still work:

```bash
# Windows PowerShell
$env:BITBUCKET_USERNAME = "user@example.com"
$env:BITBUCKET_TOKEN = "abc123token"

# Linux/Mac
export BITBUCKET_USERNAME="user@example.com"
export BITBUCKET_TOKEN="abc123token"
```

Environment variables take **highest priority** and bypass the cache.

## FAQ

**Q: Where are credentials stored?**  
A: `~/.crossbridge/credentials.enc` (encrypted) with key at `~/.crossbridge/.key`

**Q: Can I use different credentials for different repos?**  
A: Currently, test credentials are shared across all tests. For repo-specific credentials, use the main `CredentialManager` class.

**Q: Is this secure?**  
A: Yes, credentials are encrypted using Fernet (AES-128). However, this is for **test credentials only**. Use proper secret management for production.

**Q: What if I don't want to cache credentials?**  
A: Just use environment variables - they still work and take priority over cache.

**Q: Can I share my .crossbridge directory?**  
A: No! This contains your encryption key and encrypted credentials. Never commit to git or share.

**Q: Do I need to cache credentials for CI/CD?**  
A: No, use environment variables in CI/CD. Caching is for local development convenience.

## See Also

- [core/repo/credentials.py](../core/repo/credentials.py) - Main credential manager
- [core/repo/test_credentials.py](../core/repo/test_credentials.py) - Test credential caching
- [setup_test_creds.py](../setup_test_creds.py) - Interactive setup script
