# TFS Migration Demo - Setup and Usage Guide

## Overview

The TFS Migration Demo demonstrates migrating a Selenium Java BDD framework to Python Robot Framework + Playwright using a TFS/Azure DevOps Server repository.

## Implementation Status

✅ **Completed**:
- TFS/Azure DevOps Server connector with username/password support
- Full migration demo workflow script
- Repository analysis and test discovery
- Sample code transformation
- Branch and PR workflow
- All 13 Azure DevOps connector tests passing

## Files Created/Modified

### New Files
1. **`examples/tfs_migration_demo.py`** (520 lines)
   - Complete TFS migration workflow demonstration
   - Repository connection and analysis
   - Java test discovery
   - Code transformation examples
   - Branch and PR creation

2. **`test_tfs_connection.py`** - Connection test script
3. **`test_tfs_direct.py`** - Direct HTTP connectivity test
4. **`debug_tfs_url.py`** - URL parsing verification

### Modified Files
1. **`core/repo/azuredevops.py`**
   - Added `username` parameter for TFS authentication
   - Support for username/password (not just PAT)
   - Updated to use BasicAuthentication with username

2. **`core/repo/repo_translator.py`**
   - Enhanced TFS URL parsing
   - Pass username to AzureDevOpsConnector
   - Improved server URL extraction for TFS

## Authentication Methods

### For TFS Server (On-Premises):

1. **Personal Access Token (Recommended)**
   ```powershell
   $env:TFS_USERNAME='vikas.verma'
   $env:TFS_PASSWORD='<your_PAT_token>'
   python examples\tfs_migration_demo.py
   ```

2. **Username/Password** (if enabled on server)
   ```powershell
   $env:TFS_USERNAME='vikas.verma'
   $env:TFS_PASSWORD='Vipresg@1238'
   python examples\tfs_migration_demo.py
   ```

3. **Domain Authentication** (for NTLM)
   ```powershell
   $env:TFS_USERNAME='DOMAIN\vikas.verma'
   $env:TFS_PASSWORD='password'
   python examples\tfs_migration_demo.py
   ```

## Usage

### Basic Usage

```powershell
# Set environment variables
$env:TFS_URL='http://msptfsapp01:8080/tfs'
$env:TFS_PROJECT='UDP/UDPAuto'
$env:TFS_REPO='Tungsten_Automation'
$env:TFS_USERNAME='vikas.verma'
$env:TFS_PASSWORD='Vipresg@1238'

# Run demo (dry-run by default)
python examples\tfs_migration_demo.py
```

### Command-Line Options

```powershell
# With inline parameters
python examples\tfs_migration_demo.py \
  --server-url 'http://msptfsapp01:8080/tfs' \
  --project 'UDP/UDPAuto' \
  --repo 'Tungsten_Automation' \
  --username 'vikas.verma' \
  --password 'Vipresg@1238'

# Enable AI transformation
python examples\tfs_migration_demo.py --use-ai

# Execute changes (disable dry-run)
python examples\tfs_migration_demo.py --execute
```

### Testing Connection

```powershell
# Simple connection test
python test_tfs_connection.py

# Direct HTTP test
python test_tfs_direct.py
```

## Current Network Issue

### Problem
The TFS server at `http://msptfsapp01:8080` is not accessible, resulting in:
- Connection timeouts
- "Resource not available for anonymous access" errors

### Possible Causes
1. **Server on internal network** - Requires VPN connection
2. **Firewall blocking port 8080**
3. **Hostname not resolving** - DNS issue
4. **Server offline or wrong URL**

### Troubleshooting Steps

1. **Check server accessibility**:
   ```powershell
   # Test ping
   ping msptfsapp01
   
   # Test port
   Test-NetConnection -ComputerName msptfsapp01 -Port 8080
   ```

2. **Verify URL in browser**:
   - Open: `http://msptfsapp01:8080/tfs/UDP/UDPAuto/_git/Tungsten_Automation`
   - If you can't access it in browser, Python won't work either

3. **Check VPN**:
   - Connect to corporate VPN if required
   - Verify you can access internal resources

4. **Verify credentials**:
   - Try logging into TFS web interface
   - Confirm username/password are correct
   - Check if domain is required: `DOMAIN\vikas.verma`

5. **Check TFS configuration**:
   - Verify Basic Authentication is enabled
   - Confirm your user has repository read access
   - Check if PAT is required instead of password

## Expected Output

When the demo runs successfully, you'll see:

```
================================================================================
🚀 TFS/Azure DevOps Server Migration Demo
================================================================================

Repository: http://msptfsapp01:8080/tfs/UDP/UDPAuto/_git/Tungsten_Automation
Target Framework: Robot Framework + Playwright
Mode: DRY RUN (no changes will be made)

======================================================================
🔌 Connecting to TFS/Azure DevOps Server
======================================================================
Server: http://msptfsapp01:8080/tfs
Project: UDP/UDPAuto
Repository: Tungsten_Automation
Username: vikas.verma
Auth: Username + Password

✅ Connected successfully to UDP/UDPAuto/Tungsten_Automation
📋 Found 5 branches

======================================================================
📊 Analyzing Repository Structure
======================================================================

📋 Available Branches: 5
  - main
  - develop
  - feature/login-tests
  - feature/dashboard-tests
  - bugfix/timeout-fix

📁 Repository Structure:
  📂 src/
     - test/java/LoginTests.java
     - test/java/DashboardTests.java
     ... and 15 more files

======================================================================
🔍 Discovering Java Test Files
======================================================================

✅ Found 12 Java test files:
  - src/test/java/steps/LoginSteps.java
  - src/test/java/steps/DashboardSteps.java
  - src/test/java/steps/ReportSteps.java
  ... and 9 more

📝 Found 8 Gherkin feature files:
  - src/test/resources/features/login.feature
  - src/test/resources/features/dashboard.feature
  ... and 6 more

[... migration plan, transformations, branch/PR creation ...]

================================================================================
✅ Demo completed successfully!
================================================================================
```

## Migration Workflow

The demo demonstrates this complete workflow:

1. **Connect** to TFS repository
2. **Analyze** repository structure (branches, files)
3. **Discover** Java test files and Gherkin features
4. **Preview** test file contents
5. **Generate** migration plan (Selenium → Playwright)
6. **Transform** sample code (Java → Robot Framework)
7. **Show** syntax comparison (Selenium vs Playwright)
8. **Create** migration branch (dry-run)
9. **Create** pull request (dry-run)

## Next Steps

Once you have network access to the TFS server:

1. **Verify connectivity**:
   ```powershell
   python test_tfs_connection.py
   ```

2. **Run demo in dry-run mode**:
   ```powershell
   python examples\tfs_migration_demo.py
   ```

3. **Execute actual migration** (when ready):
   ```powershell
   python examples\tfs_migration_demo.py --execute
   ```

4. **Use with AI enhancement**:
   ```powershell
   $env:OPENAI_API_KEY='your_key'
   python examples\tfs_migration_demo.py --use-ai --execute
   ```

## Support

For issues or questions:
1. Verify network connectivity to TFS server
2. Confirm authentication credentials
3. Check TFS server configuration
4. Review error messages in test scripts
5. Contact TFS administrator if needed

## Architecture

The implementation uses:
- **azure-devops** Python SDK for TFS API access
- **BasicAuthentication** for username/password
- **Repository pattern** for consistent API across platforms
- **Test discovery** to find Java and Gherkin files
- **AI integration** (optional) for enhanced transformation
