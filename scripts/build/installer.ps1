# K24 - One-Click Installer for Windows
# This script installs K24 on a non-technical user's PC

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   K24 Intelligent ERP - Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run this installer as Administrator" -ForegroundColor Red
    Write-Host "Right-click this file and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit
}

Write-Host "[1/6] Checking system requirements..." -ForegroundColor Green

# Check Windows version
$osVersion = [System.Environment]::OSVersion.Version
if ($osVersion.Major -lt 10) {
    Write-Host "ERROR: Windows 10 or higher is required" -ForegroundColor Red
    pause
    exit
}

Write-Host "  ✓ Windows version OK" -ForegroundColor Gray

# Check if Tally is installed
$tallyPaths = @(
    "C:\Program Files (x86)\Tally.ERP 9",
    "C:\Program Files\Tally.ERP 9",
    "C:\Tally.ERP9"
)

$tallyFound = $false
foreach ($path in $tallyPaths) {
    if (Test-Path $path) {
        $tallyFound = $true
        Write-Host "  ✓ Tally found at: $path" -ForegroundColor Gray
        break
    }
}

if (-not $tallyFound) {
    Write-Host "  ⚠ Tally not found. Please install Tally first." -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit
    }
}

# Installation directory
$installDir = "C:\K24"
Write-Host ""
Write-Host "[2/6] Creating installation directory..." -ForegroundColor Green

if (Test-Path $installDir) {
    Write-Host "  ⚠ K24 is already installed at $installDir" -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite existing installation? (y/n)"
    if ($overwrite -ne "y") {
        exit
    }
    Remove-Item -Path $installDir -Recurse -Force
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Write-Host "  ✓ Created: $installDir" -ForegroundColor Gray

# Copy K24 files
Write-Host ""
Write-Host "[3/6] Installing K24 files..." -ForegroundColor Green

$sourceDir = $PSScriptRoot
Copy-Item -Path "$sourceDir\*" -Destination $installDir -Recurse -Force -Exclude @("installer.ps1", "*.md", ".git")
Write-Host "  ✓ Files copied" -ForegroundColor Gray

# Check for Python
Write-Host ""
Write-Host "[4/6] Checking Python installation..." -ForegroundColor Green

try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Python not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing Python..." -ForegroundColor Yellow
    
    # Download Python installer
    $pythonUrl = "https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe"
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    
    Write-Host "  Downloading Python..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
    
    Write-Host "  Installing Python (this may take a few minutes)..." -ForegroundColor Gray
    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    
    Remove-Item $pythonInstaller
    Write-Host "  ✓ Python installed" -ForegroundColor Gray
}

# Check for Node.js
Write-Host ""
Write-Host "[5/6] Checking Node.js installation..." -ForegroundColor Green

try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✓ Node.js found: $nodeVersion" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Node.js not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing Node.js..." -ForegroundColor Yellow
    
    # Download Node.js installer
    $nodeUrl = "https://nodejs.org/dist/v20.10.0/node-v20.10.0-x64.msi"
    $nodeInstaller = "$env:TEMP\node-installer.msi"
    
    Write-Host "  Downloading Node.js..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $nodeUrl -OutFile $nodeInstaller
    
    Write-Host "  Installing Node.js (this may take a few minutes)..." -ForegroundColor Gray
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$nodeInstaller`" /quiet /norestart" -Wait
    
    Remove-Item $nodeInstaller
    Write-Host "  ✓ Node.js installed" -ForegroundColor Gray
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Install Python dependencies
Write-Host ""
Write-Host "[6/6] Installing K24 dependencies..." -ForegroundColor Green
Write-Host "  This may take 5-10 minutes. Please wait..." -ForegroundColor Yellow

Set-Location $installDir

# Install Python packages
Write-Host "  Installing Python packages..." -ForegroundColor Gray
pip install -r requirements.txt --quiet 2>&1 | Out-Null
Write-Host "  ✓ Python packages installed" -ForegroundColor Gray

# Install Node packages
Write-Host "  Installing Node.js packages..." -ForegroundColor Gray
Set-Location "$installDir\frontend"
npm install --silent 2>&1 | Out-Null
Write-Host "  ✓ Node.js packages installed" -ForegroundColor Gray

# Create .env file if not exists
Set-Location $installDir
if (-not (Test-Path ".env")) {
    @"
TALLY_URL=http://localhost:9000
TALLY_COMPANY=YOUR_COMPANY_NAME
TALLY_EDU_MODE=false
TALLY_LIVE_UPDATE_ENABLED=true
GOOGLE_API_KEY=
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "  ✓ Configuration file created" -ForegroundColor Gray
}

# Create desktop shortcuts
Write-Host ""
Write-Host "Creating shortcuts..." -ForegroundColor Green

$WshShell = New-Object -comObject WScript.Shell

# Start K24 shortcut
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Start K24.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$installDir\start-k24.ps1`""
$Shortcut.WorkingDirectory = $installDir
# $Shortcut.IconLocation = "$installDir\k24-icon.ico"
$Shortcut.Description = "Start K24 Intelligent ERP"
$Shortcut.Save()

Write-Host "  ✓ Desktop shortcut created" -ForegroundColor Gray

# Create start script
@"
# K24 Startup Script
Write-Host "Starting K24 Intelligent ERP..." -ForegroundColor Cyan

# Start backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$installDir'; uvicorn backend.api:app --reload --port 8001" -WindowStyle Minimized

# Wait for backend to start
Start-Sleep -Seconds 5

# Start frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$installDir\frontend'; npm run dev" -WindowStyle Minimized

# Wait for frontend to start
Start-Sleep -Seconds 10

# Open browser
Start-Process "http://localhost:3000/onboarding"

Write-Host ""
Write-Host "K24 is now running!" -ForegroundColor Green
Write-Host "Browser should open automatically." -ForegroundColor Gray
Write-Host ""
Write-Host "To stop K24, close the PowerShell windows." -ForegroundColor Yellow
"@ | Out-File -FilePath "$installDir\start-k24.ps1" -Encoding UTF8

# Installation complete
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Installation Complete! 🎉" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "K24 has been installed to: $installDir" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Make sure Tally is running" -ForegroundColor Gray
Write-Host "  2. Double-click 'Start K24' on your desktop" -ForegroundColor Gray
Write-Host "  3. Follow the setup wizard" -ForegroundColor Gray
Write-Host ""
Write-Host "Need help? Email: support@k24.app" -ForegroundColor Cyan
Write-Host ""

# Ask to start now
$startNow = Read-Host "Start K24 now? (y/n)"
if ($startNow -eq "y") {
    & "$installDir\start-k24.ps1"
}

pause
