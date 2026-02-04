# CrossBridge Universal Test Wrapper (PowerShell)
# Automatically injects CrossBridge monitoring into any supported test framework
#
# Usage:
#   crossbridge-run robot tests/
#   crossbridge-run pytest tests/
#   crossbridge-run jest tests/
#

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$TestCommand
)

# Configuration from environment
$CROSSBRIDGE_API_HOST = if ($env:CROSSBRIDGE_API_HOST) { $env:CROSSBRIDGE_API_HOST } else { "localhost" }
$CROSSBRIDGE_API_PORT = if ($env:CROSSBRIDGE_API_PORT) { $env:CROSSBRIDGE_API_PORT } else { "8765" }
$CROSSBRIDGE_ENABLED = if ($env:CROSSBRIDGE_ENABLED) { $env:CROSSBRIDGE_ENABLED } else { "true" }
$CROSSBRIDGE_ADAPTER_DIR = if ($env:CROSSBRIDGE_ADAPTER_DIR) { $env:CROSSBRIDGE_ADAPTER_DIR } else { "$env:USERPROFILE\.crossbridge\adapters" }

function Write-Info {
    param([string]$Message)
    Write-Host "[CrossBridge] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[CrossBridge] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[CrossBridge] $Message" -ForegroundColor Red
}

function Test-SidecarConnection {
    try {
        $response = Invoke-WebRequest -Uri "http://${CROSSBRIDGE_API_HOST}:${CROSSBRIDGE_API_PORT}/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Info "✅ Connected to CrossBridge sidecar at ${CROSSBRIDGE_API_HOST}:${CROSSBRIDGE_API_PORT}"
            return $true
        }
    } catch {
        Write-Warn "⚠️  Cannot reach CrossBridge sidecar at ${CROSSBRIDGE_API_HOST}:${CROSSBRIDGE_API_PORT}"
        Write-Warn "Tests will run without CrossBridge monitoring"
        $env:CROSSBRIDGE_ENABLED = "false"
        return $false
    }
}

function Get-Adapter {
    param([string]$Framework)
    
    $adapterPath = Join-Path $CROSSBRIDGE_ADAPTER_DIR $Framework
    
    # Skip if adapter already exists and is recent (< 24 hours)
    if (Test-Path $adapterPath) {
        $age = (Get-Date) - (Get-Item $adapterPath).LastWriteTime
        if ($age.TotalHours -lt 24) {
            Write-Info "Using cached ${Framework} adapter"
            return $true
        }
    }
    
    Write-Info "Downloading ${Framework} adapter from sidecar..."
    
    New-Item -ItemType Directory -Force -Path $CROSSBRIDGE_ADAPTER_DIR | Out-Null
    $tarFile = Join-Path $CROSSBRIDGE_ADAPTER_DIR "${Framework}.tar.gz"
    
    try {
        Invoke-WebRequest -Uri "http://${CROSSBRIDGE_API_HOST}:${CROSSBRIDGE_API_PORT}/adapters/${Framework}" -OutFile $tarFile -UseBasicParsing -ErrorAction Stop
        
        # Extract using tar (Windows 10+ has built-in tar)
        tar -xzf $tarFile -C $CROSSBRIDGE_ADAPTER_DIR
        Remove-Item $tarFile -ErrorAction SilentlyContinue
        
        Write-Info "✅ ${Framework} adapter downloaded"
        return $true
    } catch {
        Write-Error-Custom "Failed to download ${Framework} adapter"
        return $false
    }
}

function Get-Framework {
    param([string]$Command)
    
    switch -Regex ($Command) {
        "^(robot|pybot)" { return "robot" }
        "^(pytest|py\.test)" { return "pytest" }
        "^jest" { return "jest" }
        "^(mocha|_mocha)" { return "mocha" }
        "^(mvn|maven)" { return "junit" }
        "^(npm|yarn)" {
            if ($TestCommand -contains "test") {
                if (Test-Path "package.json") {
                    $packageJson = Get-Content "package.json" -Raw
                    if ($packageJson -match '"jest"') { return "jest" }
                    if ($packageJson -match '"mocha"') { return "mocha" }
                }
            }
            return "unknown"
        }
        default { return "unknown" }
    }
}

function Setup-Robot {
    $adapterPath = Join-Path $CROSSBRIDGE_ADAPTER_DIR "robot"
    
    if (-not (Test-Path $adapterPath)) {
        if (-not (Get-Adapter "robot")) { return $false }
    }
    
    $env:PYTHONPATH = "$adapterPath;$env:PYTHONPATH"
    $script:ExtraArgs += @("--listener", "crossbridge_listener.CrossBridgeListener")
    
    Write-Info "Robot Framework configured with CrossBridge listener"
    return $true
}

function Setup-Pytest {
    $adapterPath = Join-Path $CROSSBRIDGE_ADAPTER_DIR "pytest"
    
    if (-not (Test-Path $adapterPath)) {
        if (-not (Get-Adapter "pytest")) { return $false }
    }
    
    $env:PYTHONPATH = "$adapterPath;$env:PYTHONPATH"
    $env:PYTEST_PLUGINS = "crossbridge_plugin"
    
    Write-Info "Pytest configured with CrossBridge plugin"
    return $true
}

function Setup-Jest {
    $adapterPath = Join-Path $CROSSBRIDGE_ADAPTER_DIR "jest"
    
    if (-not (Test-Path $adapterPath)) {
        if (-not (Get-Adapter "jest")) { return $false }
    }
    
    $reporterPath = Join-Path $adapterPath "crossbridge_reporter.js"
    if (-not ($TestCommand -match "--reporters")) {
        $script:ExtraArgs += @("--reporters=default", "--reporters=$reporterPath")
    }
    
    Write-Info "Jest configured with CrossBridge reporter"
    return $true
}

function Setup-Mocha {
    $adapterPath = Join-Path $CROSSBRIDGE_ADAPTER_DIR "mocha"
    
    if (-not (Test-Path $adapterPath)) {
        if (-not (Get-Adapter "mocha")) { return $false }
    }
    
    $reporterPath = Join-Path $adapterPath "crossbridge_reporter.js"
    if (-not ($TestCommand -match "--reporter")) {
        $script:ExtraArgs += @("--reporter", $reporterPath)
    }
    
    Write-Info "Mocha configured with CrossBridge reporter"
    return $true
}

function Setup-JUnit {
    $adapterPath = Join-Path $CROSSBRIDGE_ADAPTER_DIR "junit"
    
    if (-not (Test-Path $adapterPath)) {
        if (-not (Get-Adapter "junit")) { return $false }
    }
    
    Write-Warn "JUnit adapter downloaded to ${adapterPath}"
    Write-Warn "Please add CrossBridgeListener to your test configuration"
    Write-Warn "See: ${adapterPath}\README.md for instructions"
    return $true
}

# Main execution
if ($TestCommand.Count -eq 0) {
    Write-Host "Usage: crossbridge-run <test-command> [args...]"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  crossbridge-run robot tests/"
    Write-Host "  crossbridge-run pytest tests/"
    Write-Host "  crossbridge-run jest tests/"
    Write-Host "  crossbridge-run mocha tests/"
    Write-Host "  crossbridge-run mvn test"
    exit 1
}

# Export configuration
$env:CROSSBRIDGE_ENABLED = $CROSSBRIDGE_ENABLED
$env:CROSSBRIDGE_API_HOST = $CROSSBRIDGE_API_HOST
$env:CROSSBRIDGE_API_PORT = $CROSSBRIDGE_API_PORT

# Check sidecar connection
$connected = Test-SidecarConnection

if ($env:CROSSBRIDGE_ENABLED -ne "true") {
    Write-Warn "Running tests without CrossBridge monitoring"
    & $TestCommand[0] $TestCommand[1..($TestCommand.Length-1)]
    exit $LASTEXITCODE
}

# Detect framework
$framework = Get-Framework $TestCommand[0]

if ($framework -eq "unknown") {
    Write-Warn "Unknown test framework: $($TestCommand[0])"
    Write-Warn "Running tests without CrossBridge monitoring"
    & $TestCommand[0] $TestCommand[1..($TestCommand.Length-1)]
    exit $LASTEXITCODE
}

Write-Info "Detected framework: ${framework}"

# Setup framework-specific integration
$script:ExtraArgs = @()
$success = $false

switch ($framework) {
    "robot" { $success = Setup-Robot }
    "pytest" { $success = Setup-Pytest }
    "jest" { $success = Setup-Jest }
    "mocha" { $success = Setup-Mocha }
    "junit" { $success = Setup-JUnit }
    default {
        Write-Error-Custom "Framework setup not implemented: ${framework}"
        & $TestCommand[0] $TestCommand[1..($TestCommand.Length-1)]
        exit $LASTEXITCODE
    }
}

# Execute the test command with extra args
$allArgs = $TestCommand[1..($TestCommand.Length-1)] + $script:ExtraArgs
& $TestCommand[0] $allArgs
exit $LASTEXITCODE
