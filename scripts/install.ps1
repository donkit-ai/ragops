#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$PYTHON_VERSION = "3.12.8"
$PYTHON_URL = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-amd64.exe"
$PACKAGE_NAME = "donkit-ragops"

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "   Installing Donkit RAGOps" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python 3.12+ is available
function Test-Python {
    # Check common Python commands
    $pythonCmds = @("python", "python3", "py -3.12", "py")

    foreach ($cmd in $pythonCmds) {
        try {
            $parts = $cmd -split " "
            $exe = $parts[0]
            $args = if ($parts.Count -gt 1) { $parts[1..($parts.Count-1)] } else { @() }

            $versionOutput = if ($args) {
                & $exe $args --version 2>&1
            } else {
                & $exe --version 2>&1
            }

            if ($versionOutput -match "Python 3\.1[2-9]|Python 3\.[2-9]\d") {
                $script:PYTHON_CMD = $cmd
                Write-Host "[+] $versionOutput found" -ForegroundColor Green
                return $true
            }
        } catch {
            continue
        }
    }
    return $false
}

# Execute Python command
function Invoke-Python {
    param([string[]]$Arguments)

    $parts = $script:PYTHON_CMD -split " "
    $exe = $parts[0]

    if ($parts.Count -gt 1) {
        $allArgs = $parts[1..($parts.Count-1)] + $Arguments
        & $exe $allArgs
    } else {
        & $exe $Arguments
    }
}

# Install Python
function Install-Python {
    Write-Host "[*] Installing Python $PYTHON_VERSION..." -ForegroundColor Yellow

    $installer = "$env:TEMP\python-$PYTHON_VERSION-amd64.exe"

    # Download
    Write-Host "    Downloading..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $PYTHON_URL -OutFile $installer -UseBasicParsing

    # Install silently with PATH
    Write-Host "    Installing..."
    $installArgs = @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_pip=1",
        "Include_launcher=1",
        "Include_test=0"
    )

    Start-Process -Wait -FilePath $installer -ArgumentList $installArgs

    # Clean up
    Remove-Item $installer -Force

    # Refresh PATH in current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + `
                [System.Environment]::GetEnvironmentVariable("Path", "Machine")

    # Set Python command for subsequent use
    $script:PYTHON_CMD = "python"

    Write-Host "[+] Python installed" -ForegroundColor Green
}

# Install pipx
function Install-Pipx {
    # Check if pipx already exists
    try {
        $null = Get-Command pipx -ErrorAction Stop
        Write-Host "[+] pipx already installed" -ForegroundColor Green
        return
    } catch {
        # Continue with installation
    }

    Write-Host "[*] Installing pipx..." -ForegroundColor Yellow

    # Install pipx using pip
    Invoke-Python @("-m", "pip", "install", "--user", "pipx", "--quiet")

    # Ensure pipx is in PATH
    Invoke-Python @("-m", "pipx", "ensurepath", "--force")

    # Add pipx bin to current session PATH
    $pipxBinPath = "$env:USERPROFILE\.local\bin"
    if ($env:Path -notlike "*$pipxBinPath*") {
        $env:Path = "$pipxBinPath;$env:Path"
    }

    # Also check AppData location (Windows default)
    $pipxAppDataPath = "$env:USERPROFILE\AppData\Roaming\Python\Python312\Scripts"
    if (Test-Path $pipxAppDataPath) {
        if ($env:Path -notlike "*$pipxAppDataPath*") {
            $env:Path = "$pipxAppDataPath;$env:Path"
        }
    }

    Write-Host "[+] pipx installed" -ForegroundColor Green
}

# Install donkit-ragops
function Install-Ragops {
    Write-Host "[*] Installing $PACKAGE_NAME..." -ForegroundColor Yellow

    # Try using pipx command first
    try {
        $null = Get-Command pipx -ErrorAction Stop
        & pipx install $PACKAGE_NAME --force
    } catch {
        # Fall back to python -m pipx
        Invoke-Python @("-m", "pipx", "install", $PACKAGE_NAME, "--force")
    }

    Write-Host "[+] $PACKAGE_NAME installed" -ForegroundColor Green
}

# Check if Docker is available
function Test-Docker {
    try {
        $null = Get-Command docker -ErrorAction Stop
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[+] Docker found and running" -ForegroundColor Green
        } else {
            Write-Host "[!] Docker found but not running (start Docker Desktop for full functionality)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host ""
        Write-Host "[!] Docker not found (optional but recommended)" -ForegroundColor Yellow
        Write-Host "    Install from: https://docker.com/products/docker-desktop"
    }
}

# Print completion message
function Show-Completion {
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "   Installation Complete!" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands available:"
    Write-Host "  donkit-ragops       - Start CLI agent"
    Write-Host "  donkit-ragops-web   - Start Web UI (http://localhost:8067)"
    Write-Host ""

    # Check if restart is needed
    $needsRestart = $false

    try {
        $null = Get-Command donkit-ragops -ErrorAction Stop
    } catch {
        $needsRestart = $true
    }

    if ($needsRestart) {
        Write-Host "====================================" -ForegroundColor Yellow
        Write-Host "   IMPORTANT: Restart Required" -ForegroundColor Yellow
        Write-Host "====================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Close this PowerShell window and open a new one," -ForegroundColor Yellow
        Write-Host "then run: donkit-ragops" -ForegroundColor Yellow
        Write-Host ""
    } else {
        Write-Host "Get started:"
        Write-Host "  PS> donkit-ragops"
        Write-Host ""
    }
}

# Main installation flow
function Main {
    if (-not (Test-Python)) {
        Write-Host ""
        Write-Host "[!] Python 3.12+ not found" -ForegroundColor Yellow
        Write-Host ""

        $response = Read-Host "    Install Python automatically? [Y/n]"
        if ($response -match "^[Nn]") {
            Write-Host "Please install Python 3.12+ from https://python.org/downloads/"
            exit 1
        }

        Install-Python

        # Verify installation
        if (-not (Test-Python)) {
            Write-Host ""
            Write-Host "Error: Failed to install Python. Please install manually from https://python.org/downloads/" -ForegroundColor Red
            exit 1
        }
    }

    Install-Pipx
    Install-Ragops
    Test-Docker
    Show-Completion
}

# Run main
Main
