# K24 Crash Diagnosis Report (v1.0.3)

## 1. Primary Root Cause: Sidecar Identifier Mismatch
The application contains a mismatch between the **Identifier** defined in the build configuration and the **Identifier** called by the Rust execution engine.

- **Location:** `weare/frontend/src-tauri/src/commands.rs`
- **Error Line:** 67
- **Current Code:** `.sidecar("k24_backend")`
- **Required Code:** `.sidecar("k24-backend")`

**Observation:** Since the ID uses an underscore `_` but the configuration and binary use a dash `-`, the Tauri Shell plugin fails to locate the executable. In production builds, this failure in the `start_backend` flow leads to an unhandled promise rejection or a logger panic, causing the application to terminate (Exit 1).

## 2. Secondary Factor: Environment Sanitization
When the app is moved to another device, it lacks the Python environment present on the developer machine. If the sidecar fails to spawn (due to the mismatch above), the frontend cannot reach `localhost:8001`. 

## 3. Evidence of "The Game"
- **Symptom:** App window appears for 0.5 - 2 seconds and disappears.
- **Cause:** The `setup` block in `lib.rs` triggers `start_backend`. When `start_backend` hits the naming mismatch, it returns an `Err` which, depending on the thread state, results in an application-level panic.

## 4. Verification Step
To prove this diagnosis:
1. Open `frontend/src-tauri/src/commands.rs`.
2. Locate line 67.
3. Compare it to `tauri.conf.json` line 37.

## 5. Proposed Fix
1. Synchronize the sidecar ID to `k24-backend` (using a dash).
2. Re-run `scripts/build_sidecars.py` to ensure the binary name matches the triple exactly.
3. Execute a full clean build of the installer.
