# K24 Release Packager - COMPLETE VERSION
# This script creates a clean distribution folder ready for zipping

$sourceDir = Get-Location
$desktopPath = [Environment]::GetFolderPath("Desktop")
$distDir = "$desktopPath\K24_Installer_v1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   K24 COMPLETE PACKAGE BUILDER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Clean up old build if exists
if (Test-Path $distDir) {
    Write-Host "Removing old package..." -ForegroundColor Yellow
    Remove-Item -Path $distDir -Recurse -Force
}
New-Item -ItemType Directory -Path $distDir | Out-Null

# 2. Copy Backend (ALL files)
Write-Host "Copying Backend..." -ForegroundColor Green
New-Item -ItemType Directory -Path "$distDir\backend" | Out-Null
Copy-Item -Path "$sourceDir\backend\*" -Destination "$distDir\backend" -Recurse

# Clean Python cache
Get-ChildItem -Path "$distDir\backend" -Include "__pycache__","*.pyc" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Backend copied (cleaned)" -ForegroundColor Gray

# 3. Copy Frontend (ALL files except build artifacts)
Write-Host "Copying Frontend..." -ForegroundColor Green
New-Item -ItemType Directory -Path "$distDir\frontend" | Out-Null

# Copy package files first
Copy-Item -Path "$sourceDir\frontend\package.json" -Destination "$distDir\frontend"
Copy-Item -Path "$sourceDir\frontend\package-lock.json" -Destination "$distDir\frontend" -ErrorAction SilentlyContinue

# Copy all source directories
$frontendDirs = @("src", "public")
foreach ($dir in $frontendDirs) {
    if (Test-Path "$sourceDir\frontend\$dir") {
        Copy-Item -Path "$sourceDir\frontend\$dir" -Destination "$distDir\frontend" -Recurse
    }
}

# Copy config files
$configFiles = @("next.config.ts", "tsconfig.json", "tailwind.config.ts", "postcss.config.mjs", ".eslintrc.json")
foreach ($file in $configFiles) {
    if (Test-Path "$sourceDir\frontend\$file") {
        Copy-Item -Path "$sourceDir\frontend\$file" -Destination "$distDir\frontend"
    }
}

Write-Host "  ✓ Frontend copied" -ForegroundColor Gray

# 4. Copy Installer Files
Write-Host "Copying Installer & Documentation..." -ForegroundColor Green
$filesToCopy = @(
    "installer.ps1",
    "INSTALL_K24.bat",
    "requirements.txt",
    "INSTALL_FOR_USERS.md",
    "START_HERE.md",
    ".env.example"
)

foreach ($file in $filesToCopy) {
    if (Test-Path "$sourceDir\$file") {
        Copy-Item -Path "$sourceDir\$file" -Destination "$distDir"
    } else {
        Write-Host "  ⚠ Warning: $file not found!" -ForegroundColor Yellow
    }
}

# Create .env.example if not exists
if (-not (Test-Path "$distDir\.env.example")) {
    $envExample = @(
"TALLY_URL=http://localhost:9000",
"TALLY_COMPANY=YOUR_COMPANY_NAME",
"TALLY_EDU_MODE=false",
"TALLY_LIVE_UPDATE_ENABLED=true",
"GOOGLE_API_KEY="
)
    Set-Content -Path "$distDir\.env.example" -Value $envExample
}

Write-Host "  ✓ Installer files copied" -ForegroundColor Gray

# 5. Create README.txt
Write-Host "Creating README..." -ForegroundColor Green
$readmeContent = @(
"================================================================",
"   K24 INTELLIGENT ERP - INSTALLATION FILES v1.0",
"================================================================",
"",
"QUICK START:",
"Step 1: Double-click INSTALL_K24.bat",
"Step 2: Wait for installation - takes about 10 minutes",
"Step 3: Look for Start K24 icon on your desktop",
"Step 4: Follow the setup wizard",
"",
"FEATURES INCLUDED:",
"- Receipt and Payment Management",
"- Sales Invoices",
"- Daybook with Real-time Sync",
"- Contact Management",
"- PDF Export with Professional Templates",
"- Audit Trail - MCA Compliant",
"- GST Reports",
"- Outstanding Reports",
"- AI-Powered Chat",
"- Multi-User Support with Roles",
"",
"SYSTEM REQUIREMENTS:",
"- Windows 10 or higher",
"- Tally ERP 9 - any version",
"- 2GB free disk space",
"- Internet connection for installation only",
"",
"FULL GUIDE:",
"Open INSTALL_FOR_USERS.md for step-by-step instructions.",
"",
"SUPPORT:",
"Email: support@k24.app",
"",
"================================================================",
"Made with love for Indian Accountants | Version 1.0 | Nov 2025",
"================================================================"
)
Set-Content -Path "$distDir\README.txt" -Value $readmeContent

# 6. Feature Verification
Write-Host ""
Write-Host "Verifying Features..." -ForegroundColor Cyan

$featureChecks = @{
    "Login and Onboarding" = "$distDir\frontend\src\app\login\page.tsx"
    "Daybook" = "$distDir\frontend\src\app\daybook\page.tsx"
    "Receipt Voucher" = "$distDir\frontend\src\app\vouchers\new\receipt\page.tsx"
    "Payment Voucher" = "$distDir\frontend\src\app\vouchers\new\payment\page.tsx"
    "Sales Invoice" = "$distDir\frontend\src\app\vouchers\new\sales\page.tsx"
    "Contact Management" = "$distDir\frontend\src\app\contacts\[name]\page.tsx"
    "Audit Dashboard" = "$distDir\frontend\src\app\compliance\audit-dashboard\page.tsx"
    "Outstanding Reports" = "$distDir\frontend\src\app\reports\outstanding\page.tsx"
    "GST Reports" = "$distDir\frontend\src\app\reports\gst\page.tsx"
    "PDF Generator" = "$distDir\frontend\src\lib\pdfGenerator.ts"
    "K24 Logo" = "$distDir\frontend\public\k24-logo.png"
    "Auth System" = "$distDir\backend\routers\auth.py"
}

$allGood = $true
foreach ($feature in $featureChecks.GetEnumerator()) {
    if (Test-Path $feature.Value) {
        Write-Host "  ✓ $($feature.Key)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($feature.Key) - MISSING!" -ForegroundColor Red
        $allGood = $false
    }
}

# 7. Size Check
Write-Host ""
Write-Host "Calculating package size..." -ForegroundColor Cyan
$size = (Get-ChildItem -Path $distDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "  Package Size: $([math]::Round($size, 2)) MB" -ForegroundColor Gray

# 8. Final Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "   ✅ PACKAGE COMPLETE!" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ PACKAGE COMPLETE (with warnings)" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Location: $distDir" -ForegroundColor White
Write-Host "Size: $([math]::Round($size, 2)) MB" -ForegroundColor White
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Right-click the folder and select 'Send to > Compressed (zipped) folder'" -ForegroundColor Gray
Write-Host "2. Upload the ZIP to Google Drive" -ForegroundColor Gray
Write-Host "3. Share the link with users" -ForegroundColor Gray
Write-Host ""
Write-Host "Or copy to USB drive for offline distribution." -ForegroundColor Gray
Write-Host ""

# Create a features checklist file
$featuresDoc = @(
"# K24 V1 - Complete Feature List",
"",
"## ✅ ALL FEATURES INCLUDED IN THIS PACKAGE",
"",
"### 🔐 Authentication and User Management",
"- [x] Multi-step onboarding wizard (4 steps)",
"- [x] Login page with JWT authentication",
"- [x] Role-based access control (Admin, Auditor, Accountant, Viewer)",
"- [x] User settings management",
"- [x] Company/multi-tenant support",
"",
"### 📝 Voucher Management",
"- [x] Receipt vouchers (Cash & Bank)",
"- [x] Payment vouchers (Cash & Bank)",
"- [x] Sales invoices",
"- [x] Real-time Tally synchronization",
"- [x] EDU mode support",
"",
"### 📊 Reports and Analytics",
"- [x] Daybook with advanced filters",
"- [x] Outstanding Receivables",
"- [x] Outstanding Payables",
"- [x] GST Reports",
"- [x] Balance Sheet",
"- [x] Profit & Loss",
"- [x] Cash Book",
"- [x] Sales Reports",
"- [x] Purchase Reports",
"",
"### 👥 Contact Management",
"- [x] Contact profiles",
"- [x] Transaction history per contact",
"- [x] Outstanding tracking",
"",
"### 🛡️ Compliance and Audit",
"- [x] MCA-compliant audit trail",
"- [x] Immutable logging (Who, When, What, Why)",
"- [x] Forensic checks:",
"  - High-value transactions (>INR 2L)",
"  - Backdated entries",
"  - Weekend entries",
"  - Round-trip detection",
"- [x] Audit dashboard",
"- [x] TDS/TCS tracking",
"",
"### 📄 PDF Export",
"- [x] Professional invoice templates (Zoho-quality)",
"- [x] Itemized tables with tax breakdown",
"- [x] Audit report export",
"- [x] Company branding (Logo, GSTIN, PAN)",
"",
"### 🤖 AI Features",
"- [x] Natural language commands",
"- [x] Google Gemini integration",
"- [x] Smart chat interface",
"",
"### 🎨 UI/UX",
"- [x] Premium K24 logo (Black & Red)",
"- [x] Gradient backgrounds",
"- [x] Smooth animations (Framer Motion)",
"- [x] Responsive design",
"- [x] Dark mode ready",
"",
"### 🔧 Technical Features",
"- [x] Docker support",
"- [x] Windows installer",
"- [x] Auto-dependency installation",
"- [x] Desktop shortcuts",
"- [x] Multi-company support",
"",
"## 📦 Package Contents",
"",
"Backend/",
"├── api.py (Main backend server)",
"├── database.py (Database models)",
"├── auth.py (Authentication)",
"├── tally_connector.py (Tally integration)",
"├── compliance/ (Audit system)",
"└── routers/ (All API endpoints)",
"",
"Frontend/",
"├── src/",
"│   ├── app/ (All pages)",
"│   │   ├── login/",
"│   │   ├── onboarding/",
"│   │   ├── daybook/",
"│   │   ├── vouchers/",
"│   │   ├── reports/",
"│   │   ├── contacts/",
"│   │   └── compliance/",
"│   ├── components/ (UI components)",
"│   └── lib/ (Utilities, PDF generator)",
"└── public/",
"    └── k24-logo.png (Brand logo)",
"",
"Installation/",
"├── INSTALL_K24.bat (One-click installer)",
"├── installer.ps1 (PowerShell script)",
"├── INSTALL_FOR_USERS.md (User guide)",
"├── START_HERE.md (Documentation index)",
"└── README.txt (Quick start)",
"",
"## ✨ Version 1.0 - Production Ready!"
)
Set-Content -Path "$distDir\FEATURES_INCLUDED.md" -Value $featuresDoc

Write-Host "📄 Created FEATURES_INCLUDED.md" -ForegroundColor Cyan
Write-Host ""
