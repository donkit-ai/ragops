$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $ProjectRoot "frontend"
$StaticDir = Join-Path $ProjectRoot "src\donkit_ragops\web\static"

Write-Host "Building frontend..." -ForegroundColor Cyan

Set-Location $FrontendDir

# Install dependencies
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..."
    npm ci
}

# Build
Write-Host "Running build..."
npm run build

# Copy to static
Write-Host "Copying to static/..."
if (-not (Test-Path $StaticDir)) {
    New-Item -ItemType Directory -Path $StaticDir -Force | Out-Null
}
Remove-Item "$StaticDir\*" -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -Path "dist\*" -Destination $StaticDir -Recurse

# Add __init__.py for poetry to include it
New-Item -ItemType File -Path "$StaticDir\__init__.py" -Force | Out-Null

Write-Host "Done! Frontend built and copied to src\donkit_ragops\web\static\" -ForegroundColor Green
