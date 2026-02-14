# M4 – Tauri Installer & Startup Experience

**Status**: 60% complete | **Priority**: HIGH
**Owner**: Builder + Tester/Reviewer

## Goal
Create a distributable Windows installer (.msi/.exe) that bundles the Python backend as a standalone executable (sidecar), ensures it starts automatically with the GUI, and handles configuration correctly on fresh installations.

## Current State
- ✅ **Done**: Tauri config (MSI/NSIS targets)
- ✅ **Done**: Installer scripts (`installer.ps1`)
- ✅ **Done**: Config service (`backend/services/config_service.py`) and Cloud URL configuration (Task 0 / Task 5)
- ❌ **Pending**: Backend sidecar (`k24-backend.exe`) not built/bundled
- ❌ **Pending**: Backend auto-start in Tauri (`main.rs`)
- ❌ **Pending**: Installer logic to create initial config files in `%APPDATA%`

---

## Remaining Tasks

### 1. Create PyInstaller Spec for Backend Sidecar
- **File**: Create `backend/k24_backend.spec`
- **Goal**: Bundle FastAPI app, all dependencies (uvicorn, requests, etc.), and Tally connectors into a single `.exe`.
- **Requirements**:
  - Standalone (no Python installation required on target machine).
  - Must include hidden imports for libraries that PyInstaller might miss (e.g., `uvicorn.loops.auto`, `uvicorn.protocols.http.auto`).
  - **Output**: `k24-backend.exe`

### 2. Build Backend Sidecar Binary
- **Command**: Run `pyinstaller backend/k24_backend.spec --noconfirm`
- **Output**: `backend/dist/k24-backend.exe`
- **Constraints**:
  - Verify size is reasonable (< 100MB preferred).
  - Test the `.exe` independently to ensure it launches the helper API securely.

### 3. Integrate Sidecar into Tauri
- **Action**: Copy the built binary to the specific path Tauri expects for sidecars.
- **Path (Windows)**: `frontend/src-tauri/binaries/k24-backend-x86_64-pc-windows-msvc.exe`
- **Tauri Config**: Ensure `tauri.conf.json` defines this in the `bundle` -> `externalBin` section (should be just `k24-backend`).

### 4. Implement Backend Auto-Start in Tauri
- **File**: `frontend/src-tauri/src/main.rs`
- **Logic**:
  - Use Tauri's `Command` API (or `Sidecar` API) to spawn the backend process when the app starts.
  - **Important**: Pass configuration (like port, tokens) if needed via environment variables or CLI args.
  - Monitor the child process; if it dies, the app should likely handle it (restart it or show an error).
  - Ensure the backend process is killed when the main window/app closes (Graceful Shutdown).

### 5. Update Installer Script (Final Polish)
- **File**: `installer.ps1` (or NSIS config)
- **Goal**:
  - Create the `%APPDATA%/K24` folder if it doesn't exist.
  - Write a default `config.json` with sensible defaults (e.g., Tally URL).
  - Create the desktop shortcut pointing to the main Tauri executable.

---

## Testing Plan

1.  **Unit Test (Sidecar)**:
    *   Run `backend/dist/k24-backend.exe` in a terminal.
    *   Verify it starts the server (e.g., `http://127.0.0.1:8000/docs` is accessible).
    *   Ctrl+C to stop it.

2.  **Integration Test (Tauri + Sidecar)**:
    *   Run `npm run tauri dev` (or build in debug mode).
    *   Verify that launching the frontend *automatically* launches the backend process.
    *   Verify that closing the frontend kills the backend process.

3.  **Full Installation Test (Fresh Machine/VM)**:
    *   Build the MSI/Setup.exe.
    *   Run installer on a fresh Windows environment (Sandbox).
    *   Verify app launches, connects to backend, and Tally status is correct.

## Definition of Done
- [ ] `backend/k24_backend.spec` created.
- [ ] `k24-backend.exe` successfully built and runnable standalone.
- [ ] Sidecar binary placed in `frontend/src-tauri/binaries/`.
- [ ] `main.rs` updated to spawn/kill the sidecar process.
- [ ] Installer builds successfully.
- [ ] Manual smoke test passes.
