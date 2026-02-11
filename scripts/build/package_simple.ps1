# Simple Packager
$sourceDir = Get-Location
$desktopPath = [Environment]::GetFolderPath("Desktop")
$distDir = "$sourceDir\K24_Installer_v1"

Write-Host "Packaging K24..."

# 1. Clean
if (Test-Path $distDir) { Remove-Item -Path $distDir -Recurse -Force }
New-Item -ItemType Directory -Path $distDir | Out-Null

# 2. Copy Backend
Write-Host "Copying Backend..."
New-Item -ItemType Directory -Path "$distDir\backend" | Out-Null
Copy-Item -Path "$sourceDir\backend\*" -Destination "$distDir\backend" -Recurse
Get-ChildItem -Path "$distDir\backend" -Include "__pycache__","*.pyc" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 3. Copy Frontend
Write-Host "Copying Frontend..."
New-Item -ItemType Directory -Path "$distDir\frontend" | Out-Null
Copy-Item -Path "$sourceDir\frontend\package.json" -Destination "$distDir\frontend"
Copy-Item -Path "$sourceDir\frontend\package-lock.json" -Destination "$distDir\frontend" -ErrorAction SilentlyContinue

$frontendDirs = @("src", "public")
foreach ($dir in $frontendDirs) {
    if (Test-Path "$sourceDir\frontend\$dir") {
        Copy-Item -Path "$sourceDir\frontend\$dir" -Destination "$distDir\frontend" -Recurse
    }
}

$configFiles = @("next.config.ts", "tsconfig.json", "tailwind.config.ts", "postcss.config.mjs", ".eslintrc.json")
foreach ($file in $configFiles) {
    if (Test-Path "$sourceDir\frontend\$file") {
        Copy-Item -Path "$sourceDir\frontend\$file" -Destination "$distDir\frontend"
    }
}

# 4. Copy Installer Files
Write-Host "Copying Installer Files..."
$filesToCopy = @("installer.ps1", "INSTALL_K24.bat", "requirements.txt", "INSTALL_FOR_USERS.md", "START_HERE.md", ".env.example")
foreach ($file in $filesToCopy) {
    if (Test-Path "$sourceDir\$file") {
        Copy-Item -Path "$sourceDir\$file" -Destination "$distDir"
    }
}

# 5. Create .env.example if missing
if (-not (Test-Path "$distDir\.env.example")) {
    "TALLY_URL=http://localhost:9000`nTALLY_COMPANY=YOUR_COMPANY_NAME`nTALLY_EDU_MODE=false`nTALLY_LIVE_UPDATE_ENABLED=true`nGOOGLE_API_KEY=" | Out-File "$distDir\.env.example" -Encoding UTF8
}

# 6. Create README
Write-Host "Creating README..."
"K24 INSTALLER`n`n1. Run INSTALL_K24.bat`n2. Follow instructions." | Out-File "$distDir\README.txt" -Encoding UTF8

Write-Host "Done! Package at $distDir"
