@echo off
echo ========================================
echo    K24 Intelligent ERP - Installer
echo ========================================
echo.
echo This will install K24 on your computer.
echo Installation takes about 10 minutes.
echo.
echo Make sure you have:
echo   - Administrator access
echo   - Internet connection
echo   - Tally installed
echo.
pause

echo.
echo Starting installation...
echo.

PowerShell -ExecutionPolicy Bypass -File "%~dp0installer.ps1"

pause
