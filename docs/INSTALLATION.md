# CrossBridge Installation Guide

Complete guide for installing CrossBridge on client machines.

## Prerequisites

### Required
- **Python 3.8+** (Python 3.9+ recommended)
- **pip** (Python package installer)
- **Internet connection** (for PyPI or Git installation)

### Optional
- **Docker** (if using sidecar in container mode)
- **Git** (for installation from source)

### Verify Prerequisites

```bash
# Check Python version (must be 3.8+)
python --version
# or
python3 --version

# Check pip
pip --version
# or
python -m pip --version
```

---

## Installation Methods

### Method 1: Install from PyPI (Recommended)

**When to use:**
- Production deployments
- End users
- Stable, released versions

**Installation:**
```bash
# Install latest version
pip install crossbridge

# Install specific version
pip install crossbridge==0.2.1

# Upgrade to latest
pip install --upgrade crossbridge
```

**Verification:**
```bash
# Check version
crossbridge --version

# Test command availability
crossbridge --help
crossbridge run --help
crossbridge log --help
```

**Pros:**
✅ Simplest method  
✅ Automatic dependency resolution  
✅ Easy updates  
✅ Version control  

**Cons:**
⚠️ Requires internet connection  
⚠️ Package must be published to PyPI  

---

### Method 2: Install from Git Repository

**When to use:**
- Development and testing
- Latest unreleased features
- Contributing to the project

**Option A: Clone and Install (Editable)**
```bash
# Clone repository
git clone https://github.com/crossstack-ai/crossbridge.git
cd crossbridge

# Install in editable mode (for development)
pip install -e .

# Or install normally
pip install .
```

**Option B: Direct Install from Git URL**
```bash
# Install latest from main branch
pip install git+https://github.com/crossstack-ai/crossbridge.git

# Install from specific branch
pip install git+https://github.com/crossstack-ai/crossbridge.git@dev

# Install from specific tag
pip install git+https://github.com/crossstack-ai/crossbridge.git@v0.2.1
```

**Verification:**
```bash
crossbridge --version
python -c "import cli.commands.run_commands; print('✅ Installed successfully')"
```

**Pros:**
✅ Access to latest code  
✅ Can test unreleased features  
✅ Good for development  

**Cons:**
⚠️ Requires Git access  
⚠️ May have unstable features  

---

### Method 3: Install from Wheel Distribution (Enterprise)

**When to use:**
- Enterprise/corporate environments
- Offline installations
- Air-gapped systems
- Controlled software distribution

#### Step 1: Build the Wheel (On Build Machine)

```bash
# Navigate to CrossBridge source
cd /path/to/crossbridge

# Install build tools
pip install build

# Build wheel
python -m build

# Output will be in dist/
# dist/crossbridge-0.2.1-py3-none-any.whl
# dist/crossbridge-0.2.1.tar.gz
```

#### Step 2: Distribute the Wheel

**Option A: Network Share**
```bash
# Copy to network location
cp dist/crossbridge-0.2.1-py3-none-any.whl \\fileserver\share\packages\

# Or using scp
scp dist/crossbridge-0.2.1-py3-none-any.whl user@server:/packages/
```

**Option B: Internal Package Repository**
```bash
# Upload to internal PyPI server (e.g., devpi, artifactory)
twine upload --repository-url https://pypi.internal.company.com dist/*
```

**Option C: Version Control**
```bash
# Commit wheels to Git LFS or artifact storage
git lfs track "*.whl"
git add dist/crossbridge-0.2.1-py3-none-any.whl
git commit -m "Add wheel for v0.2.1"
```

#### Step 3: Install on Client Machines

**Direct Installation:**
```bash
# From local file
pip install /path/to/crossbridge-0.2.1-py3-none-any.whl

# From network share
pip install \\fileserver\share\packages\crossbridge-0.2.1-py3-none-any.whl

# From internal PyPI
pip install crossbridge --index-url https://pypi.internal.company.com
```

**With Dependencies:**
```bash
# Download all dependencies on internet-connected machine
pip download crossbridge -d packages/

# Transfer entire packages/ directory to offline machine

# Install on offline machine
pip install --no-index --find-links=packages/ crossbridge
```

**Verification:**
```bash
crossbridge --version
pip show crossbridge
```

**Pros:**
✅ Works offline  
✅ Controlled distribution  
✅ Corporate firewall friendly  
✅ Version locked  

**Cons:**
⚠️ Manual distribution process  
⚠️ Need to manage dependencies  

---

### Method 4: Install with Legacy Scripts (Backward Compatibility)

If you need the bash scripts as well:

```bash
# Install Python package
pip install crossbridge

# The bash scripts are in the source under bin/
# They are deprecated but available for compatibility
# No separate installation needed
```

---

## Installation Scenarios

### Scenario 1: Developer Workstation

```bash
# Clone for development
git clone https://github.com/crossstack-ai/crossbridge.git
cd crossbridge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Scenario 2: CI/CD Pipeline

**GitHub Actions:**
```yaml
steps:
  - uses: actions/setup-python@v4
    with:
      python-version: '3.9'
  
  - name: Install CrossBridge
    run: |
      pip install crossbridge
      crossbridge --version
```

**Jenkins:**
```groovy
stage('Setup') {
    steps {
        sh 'pip install crossbridge'
        sh 'crossbridge --version'
    }
}
```

**GitLab CI:**
```yaml
install:
  script:
    - pip install crossbridge
    - crossbridge --version
```

### Scenario 3: Docker Container

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

# Install CrossBridge
RUN pip install crossbridge

# Verify installation
RUN crossbridge --version

# Set working directory
WORKDIR /tests

# Command
CMD ["crossbridge", "run", "robot", "tests/"]
```

**Build and Use:**
```bash
# Build image
docker build -t crossbridge-runner .

# Run tests
docker run -v $(pwd)/tests:/tests crossbridge-runner
```

### Scenario 4: Corporate Environment (Offline)

```bash
# 1. On internet-connected build machine
pip download crossbridge -d packages/
tar -czf crossbridge-packages.tar.gz packages/

# 2. Transfer to offline machine
scp crossbridge-packages.tar.gz user@offline-machine:/tmp/

# 3. On offline machine
tar -xzf /tmp/crossbridge-packages.tar.gz
pip install --no-index --find-links=packages/ crossbridge
```

---

## Virtual Environment (Recommended)

### Why Use Virtual Environments?

✅ Isolate project dependencies  
✅ Avoid conflicts with system packages  
✅ Easy to recreate environments  
✅ Match production configurations  

### Create and Use

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv crossbridge-env

# Activate
source crossbridge-env/bin/activate

# Install CrossBridge
pip install crossbridge

# Use
crossbridge run pytest tests/

# Deactivate when done
deactivate
```

**Windows:**
```powershell
# Create virtual environment
python -m venv crossbridge-env

# Activate
crossbridge-env\Scripts\activate

# Install CrossBridge
pip install crossbridge

# Use
crossbridge run pytest tests/

# Deactivate when done
deactivate
```

---

## Installation Verification

### Basic Verification

```bash
# Check if command is available
which crossbridge  # Linux/macOS
where crossbridge  # Windows

# Check version
crossbridge --version

# Check help
crossbridge --help

# List all commands
crossbridge --help | grep "  "
```

### Detailed Verification

```bash
# Check Python package info
pip show crossbridge

# Verify imports
python -c "from cli.commands.run_commands import CrossBridgeRunner; print('✅ Run module OK')"
python -c "from cli.commands.log_commands import LogParser; print('✅ Log module OK')"

# Test framework detection
python -c "
from cli.commands.run_commands import CrossBridgeRunner
r = CrossBridgeRunner()
print('✅ Framework detection:', r.detect_framework('pytest'))
"

# Test log format detection
python -c "
from cli.commands.log_commands import LogParser
from pathlib import Path
p = LogParser()
print('✅ Log detection:', p.detect_framework(Path('output.xml')))
"
```

### Functional Test

```bash
# Test run command help
crossbridge run --help

# Test log command help
crossbridge log --help

# Test with actual execution (requires sidecar)
# crossbridge run pytest tests/
```

---

## Troubleshooting Installation

### Issue: "Command not found"

**Cause:** CrossBridge not in PATH

**Solution:**
```bash
# Check where pip installs packages
python -m site --user-base

# Add to PATH (Linux/macOS)
export PATH="$PATH:$(python -m site --user-base)/bin"

# Add to PATH (Windows)
set PATH=%PATH%;%USERPROFILE%\AppData\Roaming\Python\Python39\Scripts

# Or use Python module directly
python -m cli.app --help
```

### Issue: "ModuleNotFoundError"

**Cause:** Missing dependencies

**Solution:**
```bash
# Reinstall with dependencies
pip install --force-reinstall crossbridge

# Or install dependencies explicitly
pip install typer rich requests

# Check what's missing
pip check
```

### Issue: "Permission denied"

**Cause:** Installing to system Python without sudo

**Solution:**
```bash
# Option 1: Use user install
pip install --user crossbridge

# Option 2: Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install crossbridge

# Option 3: Use sudo (not recommended)
sudo pip install crossbridge
```

### Issue: "SSL/Certificate errors"

**Cause:** Corporate firewall or proxy

**Solution:**
```bash
# Set proxy
pip install --proxy http://proxy.company.com:8080 crossbridge

# Trust corporate CA
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org crossbridge

# Or use wheel distribution (see Method 3)
```

### Issue: "Wrong Python version"

**Cause:** Using Python < 3.8

**Solution:**
```bash
# Check version
python --version

# Use specific Python version
python3.9 -m pip install crossbridge

# Update Python
# Linux: apt-get install python3.9
# macOS: brew install python@3.9
# Windows: Download from python.org
```

---

## Uninstallation

```bash
# Uninstall CrossBridge
pip uninstall crossbridge

# Verify removal
crossbridge --version  # Should fail

# Clean up cache
rm -rf ~/.crossbridge
```

---

## Updates and Upgrades

### Check for Updates

```bash
# Check current version
pip show crossbridge

# Check available versions
pip index versions crossbridge

# Check what would be upgraded
pip list --outdated | grep crossbridge
```

### Upgrade

```bash
# Upgrade to latest
pip install --upgrade crossbridge

# Upgrade to specific version
pip install --upgrade crossbridge==0.3.0

# Force reinstall
pip install --force-reinstall crossbridge
```

---

## Dependencies

CrossBridge requires these Python packages (automatically installed):

**Core Dependencies:**
- `typer >= 0.9.0` - CLI framework
- `rich >= 13.0.0` - Rich terminal output
- `requests >= 2.31.0` - HTTP client for sidecar API
- `pydantic >= 2.0.0` - Data validation

**Optional Dependencies:**
- `pytest >= 7.0.0` - For running tests (dev)
- `black >= 23.0.0` - Code formatting (dev)
- `mypy >= 1.0.0` - Type checking (dev)

**Install with development dependencies:**
```bash
pip install crossbridge[dev]
```

---

## Platform-Specific Notes

### Windows

```powershell
# Recommended: Use Python from Microsoft Store or python.org
# NOT: Windows Store Python (has PATH issues)

# Verify installation location
python -c "import sys; print(sys.executable)"

# May need to add Scripts to PATH
$env:PATH += ";$env:USERPROFILE\AppData\Local\Programs\Python\Python39\Scripts"
```

### macOS

```bash
# Use Homebrew Python (recommended)
brew install python@3.9

# Or use system Python with virtual environment
python3 -m venv venv
source venv/bin/activate
pip install crossbridge
```

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 -m pip install crossbridge

# RHEL/CentOS
sudo yum install python3 python3-pip
python3 -m pip install crossbridge

# Arch
sudo pacman -S python python-pip
pip install crossbridge
```

---

## Enterprise Distribution Guide

### Option 1: Internal PyPI Server

**Setup (devpi example):**
```bash
# Install devpi on server
pip install devpi-server devpi-web

# Initialize
devpi-init

# Start server
devpi-server --start

# Upload CrossBridge
devpi use http://pypi.internal.company.com
devpi login root --password=''
devpi upload dist/*
```

**Client Configuration:**
```bash
# Install from internal PyPI
pip install crossbridge --index-url http://pypi.internal.company.com/simple
```

### Option 2: Artifactory/Nexus

**Upload to Artifactory:**
```bash
# Build wheel
python -m build

# Upload using twine
twine upload --repository-url https://artifactory.company.com/pypi dist/*
```

**Install from Artifactory:**
```bash
pip install crossbridge --index-url https://artifactory.company.com/api/pypi/pypi/simple
```

### Option 3: Configuration Management

**Ansible Playbook:**
```yaml
- name: Install CrossBridge
  hosts: test_servers
  tasks:
    - name: Install CrossBridge
      pip:
        name: crossbridge
        state: present
```

**Puppet Manifest:**
```puppet
package { 'crossbridge':
  ensure   => 'present',
  provider => 'pip3',
}
```

---

## Support

### Getting Help

```bash
# Built-in help
crossbridge --help
crossbridge run --help
crossbridge log --help

# Version info
crossbridge --version

# Check installation
pip show crossbridge
pip check
```

### Report Installation Issues

If you encounter installation problems:

1. **Check Prerequisites:**
   - Python version >= 3.8
   - pip is up to date: `pip install --upgrade pip`

2. **Try clean install:**
   ```bash
   pip uninstall crossbridge
   pip cache purge
   pip install crossbridge
   ```

3. **Collect diagnostic info:**
   ```bash
   python --version
   pip --version
   pip show crossbridge
   which crossbridge
   ```

4. **Report issue:**
   - GitHub: https://github.com/crossstack-ai/crossbridge/issues
   - Include: OS, Python version, error messages, diagnostic output

---

## Quick Reference

| Task | Command |
|------|---------|
| **Install from PyPI** | `pip install crossbridge` |
| **Install from Git** | `pip install git+https://github.com/crossstack-ai/crossbridge.git` |
| **Install from wheel** | `pip install crossbridge-0.2.1-py3-none-any.whl` |
| **Upgrade** | `pip install --upgrade crossbridge` |
| **Uninstall** | `pip uninstall crossbridge` |
| **Verify** | `crossbridge --version` |
| **Help** | `crossbridge --help` |

---

**Last Updated:** February 10, 2026  
**Version:** 0.2.1  
**Maintained by:** CrossStack AI
