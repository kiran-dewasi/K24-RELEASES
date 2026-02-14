# M4 - Windows Installer & Sidecar - COMPLETE ✅

**Date**: 2026-02-14
**Status**: SUCCESS
**Installer Output**: `frontend/src-tauri/target/release/bundle/msi/K24_1.0.3_x64_en-US.msi`

## Summary
Successfully integrated the Python backend as a standalone sidecar into the Tauri application and built a production-ready Windows installer.

## Components Built

1. **Backend Sidecar (`k24-backend.exe`)**
   - **Source**: Python FastAPI app (`backend/desktop_main.py`)
   - **Build Tool**: PyInstaller
   - **Size**: ~87 MB
   - **Location**: Bundled inside the installer.
   - **Config**: Automatically bundles `cloud.json`.

2. **Life-Cycle Management**
   - **Start**: Automatically spawned by Tauri when the app launches (random port assigned).
   - **Stop**: Automatically killed when the main window closes.
   - **Health**: App waits for backend health check on startup.

3. **Installer (MSI/NSIS)**
   - **Output**: `frontend/src-tauri/target/release/bundle/msi/`
   - **Features**: 
     - Installs to Program Files.
     - Creates Desktop & Start Menu shortcuts.
     - Manages dependencies (no Python install needed).

## Note on "Crash" Logs
If you see logs like:
`[WinError 10061] No connection could be made because the target machine actively refused it`
This is **NOT A CRASH**.
- It means the backend is running perfectly, but **Tally is offline/not found**.
- The backend retries connecting to Tally every few seconds.
- This is expected behavior on a machine without Tally running.

## How to Test
1. Grab the MSI file from `frontend/src-tauri/target/release/bundle/msi/K24_1.0.3_x64_en-US.msi`.
2. Copy it to a fresh Windows Sandbox or VM.
3. Run the installer.
4. Launch "K24" from desktop.
5. Verify app opens and login works.
