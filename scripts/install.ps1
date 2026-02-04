# CrossBridge Universal Wrapper Installation Script (PowerShell)
# Installs crossbridge-run command for zero-touch test monitoring
#
# Usage:
#   iwr -useb https://crossbridge.io/install.ps1 | iex
#

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\CrossBridge\bin"
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[CrossBridge Install] $Message" -ForegroundColor Green
}

function Write-Warn-Custom {
    param([string]$Message)
    Write-Host "[CrossBridge Install] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[CrossBridge Install] $Message" -ForegroundColor Red
}

function Test-Prerequisites {
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-Error-Custom "PowerShell 5.0 or higher is required"
        exit 1
    }
    
    # Check tar availability (Windows 10+ has built-in tar)
    if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
        Write-Warn-Custom "tar command not found - some features may not work"
    }
    
    Write-Info "Prerequisites check passed"
}

function Get-Platform {
    $os = [System.Environment]::OSVersion.Platform
    $arch = [System.Environment]::GetEnvironmentVariable("PROCESSOR_ARCHITECTURE")
    
    Write-Info "Detected OS: Windows"
    Write-Info "Detected architecture: $arch"
}

function Install-Wrapper {
    $wrapperUrl = "https://raw.githubusercontent.com/crossbridge/crossbridge/main/bin/crossbridge-run.ps1"
    $wrapperPath = Join-Path $InstallDir "crossbridge-run.ps1"
    
    Write-Info "Creating installation directory..."
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    
    Write-Info "Downloading CrossBridge wrapper..."
    
    try {
        Invoke-WebRequest -Uri $wrapperUrl -OutFile $wrapperPath -UseBasicParsing
        Write-Info "✅ Installed crossbridge-run.ps1 to $InstallDir"
    } catch {
        Write-Error-Custom "Failed to download wrapper from $wrapperUrl"
        Write-Error-Custom $_.Exception.Message
        exit 1
    }
}

function Add-ToPath {
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    if ($currentPath -notlike "*$InstallDir*") {
        Write-Info "Adding $InstallDir to user PATH..."
        
        $newPath = "$currentPath;$InstallDir"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        
        # Update current session
        $env:Path = "$env:Path;$InstallDir"
        
        Write-Info "✅ Added to PATH"
    } else {
        Write-Info "Installation directory already in PATH"
    }
}

function Test-Installation {
    # Refresh environment
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    
    $wrapperPath = Join-Path $InstallDir "crossbridge-run.ps1"
    
    if (Test-Path $wrapperPath) {
        Write-Info "✅ Installation verified"
        Write-Host ""
        Write-Info "CrossBridge is ready to use!"
        Write-Host ""
        Write-Info "Usage examples:"
        Write-Host "  crossbridge-run robot tests/"
        Write-Host "  crossbridge-run pytest tests/"
        Write-Host "  crossbridge-run jest tests/"
        Write-Host ""
        Write-Info "Configuration (set before running tests):"
        Write-Host "  `$env:CROSSBRIDGE_API_HOST='your-sidecar-host'"
        Write-Host "  `$env:CROSSBRIDGE_API_PORT='8765'"
        Write-Host "  `$env:CROSSBRIDGE_ENABLED='true'"
        Write-Host ""
        Write-Warn-Custom "Note: You may need to restart your terminal for PATH changes to take effect"
        return $true
    } else {
        Write-Error-Custom "Installation verification failed"
        return $false
    }
}

function New-Alias {
    $profilePath = $PROFILE.CurrentUserAllHosts
    
    if (-not (Test-Path $profilePath)) {
        Write-Info "Creating PowerShell profile..."
        New-Item -ItemType File -Path $profilePath -Force | Out-Null
    }
    
    $aliasLine = "function crossbridge-run { & '$InstallDir\crossbridge-run.ps1' @args }"
    
    if (Select-String -Path $profilePath -Pattern "crossbridge-run" -Quiet) {
        Write-Info "Alias already exists in profile"
    } else {
        Write-Info "Adding crossbridge-run alias to PowerShell profile..."
        Add-Content -Path $profilePath -Value "`n$aliasLine"
        Write-Info "✅ Alias added to $profilePath"
    }
}

# Main installation
function Main {
    Write-Host ""
    Write-Info "CrossBridge Universal Wrapper Installation"
    Write-Host ""
    
    Test-Prerequisites
    Get-Platform
    
    Write-Info "Installation directory: $InstallDir"
    
    Install-Wrapper
    Add-ToPath
    New-Alias
    
    Write-Host ""
    Test-Installation
    Write-Host ""
}

Main
