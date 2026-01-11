# Using Bitbucket Repository Access Tokens

## Overview

Bitbucket Cloud now supports **Repository Access Tokens** - a more secure authentication method that doesn't require a username. These tokens are scoped to specific repositories and can be managed independently.

## Benefits of Repository Access Tokens

✅ **No username required** - Simpler authentication  
✅ **Repository-scoped** - Limited access for better security  
✅ **Independent management** - Create/revoke per repository  
✅ **CI/CD friendly** - Easier to manage in pipelines  
✅ **Granular permissions** - Fine-grained control  

## How to Create a Repository Access Token

### Step 1: Navigate to Repository Settings
1. Go to your Bitbucket repository
2. Click **Repository settings** (gear icon)
3. Under **Security**, click **Access tokens**

### Step 2: Create Token
1. Click **Create repository access token**
2. Give it a name (e.g., "CrossBridge Migration")
3. Select permissions:
   - ✅ **Repository read**
   - ✅ **Repository write**
   - ✅ **Pull requests read**
   - ✅ **Pull requests write**
4. Set expiration (optional)
5. Click **Create**

### Step 3: Copy Token
- **Important**: Copy the token immediately!
- You won't be able to see it again
- Store it securely (e.g., in environment variable)

## Usage

### Method 1: Environment Variable (Recommended)

```powershell
# Windows PowerShell
$env:BITBUCKET_REPO_TOKEN = "your_repository_access_token"

# Linux/Mac
export BITBUCKET_REPO_TOKEN=your_repository_access_token
```

### Method 2: Direct in Code

```python
from core.repo import create_connector

# With repository access token - no username needed!
connector = create_connector(
    "bitbucket:workspace/repo",
    token="your_repo_token",
    use_repo_token=True  # Key parameter!
)
```

## Example Usage

### Basic Connection

```python
from core.repo import create_connector

# Create connector with repo token
connector = create_connector(
    "bitbucket:myworkspace/myrepo",
    token="your_repository_token",
    use_repo_token=True
)

# List branches
branches = connector.list_branches()
for branch in branches:
    print(branch.name)

# Read file
content = connector.read_file("README.md")
print(content)
```

### Demo Script with Repository Token

```powershell
# Set the token
$env:BITBUCKET_REPO_TOKEN = "your_token"

# Run demo with repo token
python examples\bitbucket_migration_demo.py --use-repo-token

# Or specify directly
python examples\bitbucket_migration_demo.py --token your_token --use-repo-token
```

### Full Migration Example

```python
from core.repo import create_connector, RepoTranslator

# Connect with repository token
connector = create_connector(
    "bitbucket:myworkspace/myrepo",
    token="your_repo_token",
    use_repo_token=True
)

# Create translator
translator = RepoTranslator(
    connector,
    source_framework="selenium",
    target_framework="playwright"
)

# Discover tests
test_files = translator.discover_test_files()
print(f"Found {len(test_files)} test files")

# Transform
for file_path in test_files:
    translator.transform_file(file_path)

# Commit changes
translator.commit_changes(
    "feature/playwright-migration",
    "Migrate to Playwright"
)

# Create PR
pr = connector.create_pull_request(
    "Migrate to Playwright",
    "Automated migration from Selenium",
    "feature/playwright-migration",
    "main"
)
print(f"PR created: {pr.url}")
```

## Comparison: App Password vs Repository Token

| Feature | App Password | Repository Token |
|---------|--------------|------------------|
| Username Required | ✅ Yes | ❌ No |
| Scope | All repositories | Single repository |
| Permissions | Account-wide | Granular |
| Revocation | Affects all repos | Only one repo |
| CI/CD Setup | More complex | Simpler |
| Security | Account-level | Repository-level |

## Migration from App Password

### Before (App Password)

```python
# Requires username
connector = create_connector(
    "bitbucket:workspace/repo",
    token="app_password",
    username="your_username"  # Required!
)
```

### After (Repository Token)

```python
# No username needed!
connector = create_connector(
    "bitbucket:workspace/repo",
    token="repo_token",
    use_repo_token=True  # New parameter
)
```

## Testing Your Repository Token

Use the test script to verify your token works:

```powershell
# Set token
$env:BITBUCKET_REPO_TOKEN = "your_token"

# Run test
python test_repo_token.py
```

Expected output:
```
==================================================
🔐 Testing Bitbucket Repository Access Token
==================================================
Token: BBRAT0QP...a1b2
Auth Method: Repository Access Token (no username required)
==================================================

📡 Connecting to workspace/repo...
Using repository access token (no username needed)
✅ Connection successful!

📋 Testing API access - listing branches...
✅ Found 3 branches:
  1. main
  2. develop
  3. feature/test

==================================================
✅ Repository Token Test Complete!
==================================================
```

## Troubleshooting

### "Unauthorized (401)"
- Verify token is valid and not expired
- Check token has correct permissions
- Ensure you have access to the repository

### "Token not found"
- Set `BITBUCKET_REPO_TOKEN` environment variable
- Or pass `--token` with `--use-repo-token` flag

### "Username required"
- Add `--use-repo-token` flag
- Or set `use_repo_token=True` in code

### Permission Denied
- Check token permissions in repository settings
- Ensure token has:
  - Repository read/write
  - Pull request read/write (if needed)

## Environment Variables

The connector checks these variables in order:

1. `BITBUCKET_REPO_TOKEN` - Repository access token (preferred)
2. `BITBUCKET_TOKEN` - App password or repo token
3. `BITBUCKET_USERNAME` - Required only for app passwords

## Command Line Options

```bash
# With repository token
python examples\bitbucket_migration_demo.py \
  --workspace myworkspace \
  --repo myrepo \
  --token your_repo_token \
  --use-repo-token

# With app password (old method)
python examples\bitbucket_migration_demo.py \
  --workspace myworkspace \
  --repo myrepo \
  --username myuser \
  --token app_password
```

## Best Practices

1. **Use Repository Tokens for CI/CD**
   - Simpler setup
   - Better security isolation
   - Easier to rotate

2. **Create Separate Tokens per Environment**
   - Development token
   - Staging token
   - Production token

3. **Set Appropriate Permissions**
   - Only grant what's needed
   - Review periodically

4. **Set Expiration Dates**
   - Automatic cleanup
   - Forces regular rotation

5. **Store Securely**
   - Use secret management systems
   - Never commit to version control
   - Rotate if exposed

## Security Considerations

✅ **Do:**
- Use repository tokens when possible
- Store tokens in secret managers
- Set expiration dates
- Use minimum required permissions
- Rotate tokens regularly

❌ **Don't:**
- Commit tokens to git
- Share tokens across teams
- Use same token for all environments
- Grant excessive permissions
- Leave tokens active indefinitely

## See Also

- [Bitbucket Connector Documentation](../docs/REPO_NATIVE_TRANSFORMATION.md#4-bitbucket-connector)
- [Migration Demo Guide](BITBUCKET_DEMO_README.md)
- [Bitbucket Access Token Docs](https://support.atlassian.com/bitbucket-cloud/docs/repository-access-tokens/)

---

**Ready to try it?** Set your token and run:
```powershell
$env:BITBUCKET_REPO_TOKEN = "your_token"
python test_repo_token.py
```
