# K24 Developer Notes & Directory Structure

## Repository Overview
This repository uses a structured layout to keep the root clean. Please follow these guidelines when adding new files.

### 📂 Directory Structure

*   `backend/` - Core Python API (FastAPI) and business logic.
*   `frontend/` - Next.js Web Application.
*   `baileys-listener/` - WhatsApp Node.js service.
*   `scripts/` - All maintenance and utility scripts.
    *   `ops/` - Operational tools (manual sync, specialized launchers).
    *   `db/` - Database migrations, fixes, and schema inspection tools.
    *   `debug/` - Diagnostic scripts for Tally, Gemini, and API probing.
    *   `tests/` - Manual test runners (one-off checks).
    *   `build/` - Deployment and packaging scripts.
*   `docs/`
    *   `reports/` - Historical progress reports, audit logs, and walkthroughs.
*   `archive/` - Obsolete files (logs, old dumps).

### 🚀 Running the App
*   **Startup:** Run `start_k24.bat` from the root directory.
*   **Development:** `uvicorn backend.api:app --reload`

### 🛠 Adding New Scripts
Do **NOT** add single-file scripts to the root directory.
*   If it's a test: put it in `scripts/tests/`.
*   If it's a fix: put it in `scripts/db/` or `scripts/ops/`.
*   If it's a probe: put it in `scripts/debug/`.

### ⚠️ Critical Files (Do Not Move)
*   `api.py` (Entry point)
*   `k24_config.json`
*   `.env`
