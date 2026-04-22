use once_cell::sync::Lazy;
// std::sync::atomic::{AtomicBool, Ordering} removed — replaced by BackendLifecycle enum (B9)
use std::sync::Mutex;
use tauri::AppHandle;
use uuid::Uuid;
// ShellExt is only used in the production (release) code path.
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

// ── BackendLifecycle state machine ────────────────────────────────────────────
// Replaces both BACKEND_STATE (Option<BackendAuth>) and STARTUP_IN_PROGRESS
// (AtomicBool) as a single, authoritative source of truth.  The session_token
// lives only inside the Ready variant — it is NEVER emitted to the frontend.
#[derive(Debug, Clone)]
// Crashed is constructed only in the release (non-debug) code path.
#[allow(dead_code)]
pub enum BackendLifecycle {
    NotStarted,
    Starting,
    Ready { port: u16, session_token: String },
    Crashed { error: String },
}

// BackendAuth struct deleted — its fields now live inside Ready { port, session_token }.

static BACKEND_LIFECYCLE: Lazy<Mutex<BackendLifecycle>> =
    Lazy::new(|| Mutex::new(BackendLifecycle::NotStarted));

// BACKEND_PROCESS is unchanged — orthogonal OS handle used only for kill-on-shutdown.
static BACKEND_PROCESS: Lazy<Mutex<Option<CommandChild>>> = Lazy::new(|| Mutex::new(None));

// ── Internal helper — never exposed via Tauri command ─────────────────────────
fn get_session_token() -> Option<String> {
    let lifecycle = BACKEND_LIFECYCLE.lock().ok()?;
    match &*lifecycle {
        BackendLifecycle::Ready { session_token, .. } => Some(session_token.clone()),
        _ => None,
    }
}

// ── start_backend ─────────────────────────────────────────────────────────────
#[tauri::command]
pub async fn start_backend(app_handle: AppHandle) -> Result<serde_json::Value, String> {
    #[cfg(debug_assertions)]
    let _ = &app_handle;

    // ── Early-exit guard (no state mutation) ──────────────────────────────────
    // Lock, inspect, release immediately — no await is held past this block.
    {
        let lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
        match &*lifecycle {
            BackendLifecycle::Starting => {
                return Ok(serde_json::json!({ "status": "starting" }));
            }
            BackendLifecycle::Ready { port, .. } => {
                return Ok(serde_json::json!({ "status": "ready", "port": port }));
            }
            // NotStarted and Crashed both allow a fresh start attempt.
            BackendLifecycle::NotStarted | BackendLifecycle::Crashed { .. } => {}
        }
    } // guard dropped here — no await held

    let port = portpicker::pick_unused_port()
        .ok_or("No available ports")?;

    let session_token = Uuid::new_v4().to_string();

    log::info!("Starting backend on port {} with session token", port);

    // ── Dev mode path ─────────────────────────────────────────────────────────
    // C6: must transition Starting → Ready so get_session_token() works in dev.
    #[cfg(debug_assertions)]
    {
        let port: u16 = std::env::var("DESKTOP_BACKEND_PORT")
            .unwrap_or("8001".to_string())
            .parse()
            .unwrap_or(8001);

        // Transition to Starting
        {
            let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
            *lifecycle = BackendLifecycle::Starting;
        }

        log::info!("Development mode: backend on port {}", port);

        // Transition to Ready
        {
            let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
            *lifecycle = BackendLifecycle::Ready {
                port,
                session_token: session_token.clone(),
            };
        }

        return Ok(serde_json::json!({
            "status": "ready",
            "port": port,
            "mode": "development"
        }));
    }

    // ── Production path ───────────────────────────────────────────────────────
    #[cfg(not(debug_assertions))]
    {
        // ── Transition: NotStarted/Crashed → Starting ─────────────────────────
        // Lock, mutate, release — no await held across this block.
        {
            let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
            *lifecycle = BackendLifecycle::Starting;
        }

        // SAFE MODE: Short initial delay so Tauri window is up and AV has cleared the process.
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

        let shell = app_handle.shell();
        log::info!("Attempting to spawn sidecar: k24-backend");

        let result = shell
            .sidecar("k24-backend")
            .map_err(|e| {
                // Transition to Crashed on sidecar-config failure
                if let Ok(mut lifecycle) = BACKEND_LIFECYCLE.lock() {
                    *lifecycle = BackendLifecycle::Crashed {
                        error: format!("Failed to configure sidecar: {}", e),
                    };
                }
                format!("Failed to configure sidecar: {}", e)
            })?
            .args(&[
                "--port", &port.to_string(),
                "--token", &session_token,
                "--desktop-mode", "true",
                "--app-version", &app_handle.package_info().version.to_string()
            ])
            .spawn();

        match result {
            Ok((mut rx, child)) => {
                // Change 2 — Store BACKEND_PROCESS before any await.
                // The lock is taken, mutated, and released synchronously here.
                // No .await is held across this block.
                {
                    let mut proc = BACKEND_PROCESS.lock().map_err(|e| e.to_string())?;
                    *proc = Some(child);
                }

                // === STARTUP READINESS WINDOW ===
                //
                // Total budget: 10 s warmup + 20 retries × 4 s = ~90 s
                // This covers cold disk, AV scan, OneDrive noise, slow Python/LangGraph init.
                //
                // BACKEND_LIFECYCLE remains Starting here.
                // It will only transition to Ready once health-check passes, so
                // get_backend_status() correctly reports "starting" until then.

                let health_url = format!("http://127.0.0.1:{}/health", port);

                // Change 3 — Monitored warmup: race sleep_until(deadline) against rx.recv().
                // Stdout/Stderr/Error are logged only — never trigger Crashed.
                // Terminated or None (channel closed) triggers immediate Crashed + Err return.
                log::info!("Waiting 10 s for backend initial warmup before first health-check…");
                {
                    let warmup_deadline =
                        tokio::time::Instant::now() + tokio::time::Duration::from_secs(10);
                    loop {
                        tokio::select! {
                            _ = tokio::time::sleep_until(warmup_deadline) => {
                                // Warmup window elapsed normally — proceed to health loop.
                                break;
                            }
                            event = rx.recv() => {
                                match event {
                                    Some(tauri_plugin_shell::process::CommandEvent::Stdout(line)) => {
                                        log::info!("[sidecar stdout] {}", String::from_utf8_lossy(&line));
                                        // continue monitoring
                                    }
                                    Some(tauri_plugin_shell::process::CommandEvent::Stderr(line)) => {
                                        log::warn!("[sidecar stderr] {}", String::from_utf8_lossy(&line));
                                        // continue monitoring
                                    }
                                    Some(tauri_plugin_shell::process::CommandEvent::Error(e)) => {
                                        log::warn!("[sidecar error] {}", e);
                                        // continue monitoring
                                    }
                                    Some(tauri_plugin_shell::process::CommandEvent::Terminated(payload)) => {
                                        log::error!(
                                            "Sidecar terminated during warmup — code={:?} signal={:?}",
                                            payload.code, payload.signal
                                        );
                                        {
                                            let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
                                            *lifecycle = BackendLifecycle::Crashed {
                                                error: format!(
                                                    "Sidecar exited during warmup (code={:?} signal={:?})",
                                                    payload.code, payload.signal
                                                ),
                                            };
                                        }
                                        return Err(format!(
                                            "Backend sidecar terminated during warmup (code={:?} signal={:?})",
                                            payload.code, payload.signal
                                        ));
                                    }
                                    Some(_) => {
                                        // Unknown variant — ignore and continue.
                                    }
                                    None => {
                                        // Channel closed — process gone.
                                        log::error!("Sidecar event channel closed during warmup");
                                        {
                                            let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
                                            *lifecycle = BackendLifecycle::Crashed {
                                                error: "Sidecar event channel closed during warmup".to_string(),
                                            };
                                        }
                                        return Err("Backend sidecar channel closed during warmup".to_string());
                                    }
                                }
                            }
                        }
                    }
                }

                log::info!("Starting readiness loop (max 20 retries × 4 s = 80 s)…");

                const MAX_ATTEMPTS: u32 = 20;
                const RETRY_SECS: u64 = 4;
                let mut backend_ok = false;
                // Change 4 — exit_detected drives the Phase-3 decision.
                let mut exit_detected = false;

                'health: for attempt in 1..=MAX_ATTEMPTS {
                    // Fresh client per attempt — avoids connection-pool stale-state.
                    let client = reqwest::Client::builder()
                        .timeout(std::time::Duration::from_secs(6))
                        .build()
                        .unwrap_or_default();

                    match client.get(&health_url).send().await {
                        Ok(response) if response.status().is_success() => {
                            log::info!(
                                "Backend readiness check PASSED ✓ (attempt {}/{})",
                                attempt, MAX_ATTEMPTS
                            );
                            backend_ok = true;
                            break 'health;
                        }
                        Ok(response) => {
                            log::warn!(
                                "Readiness check {}/{}: backend returned HTTP {}, waiting {} s…",
                                attempt, MAX_ATTEMPTS, response.status(), RETRY_SECS
                            );
                        }
                        Err(e) => {
                            log::warn!(
                                "Readiness check {}/{}: connection error ({}), waiting {} s…",
                                attempt, MAX_ATTEMPTS, e, RETRY_SECS
                            );
                        }
                    }

                    // Change 4 — Monitored inter-retry sleep: race sleep_until against rx.recv().
                    // Skip the sleep on the last attempt.
                    if attempt < MAX_ATTEMPTS {
                        let retry_deadline =
                            tokio::time::Instant::now() + tokio::time::Duration::from_secs(RETRY_SECS);
                        'drain: loop {
                            tokio::select! {
                                _ = tokio::time::sleep_until(retry_deadline) => {
                                    // Interval elapsed — do next health attempt.
                                    break 'drain;
                                }
                                event = rx.recv() => {
                                    match event {
                                        Some(tauri_plugin_shell::process::CommandEvent::Stdout(line)) => {
                                            log::info!("[sidecar stdout] {}", String::from_utf8_lossy(&line));
                                            // continue drain loop
                                        }
                                        Some(tauri_plugin_shell::process::CommandEvent::Stderr(line)) => {
                                            log::warn!("[sidecar stderr] {}", String::from_utf8_lossy(&line));
                                            // continue drain loop
                                        }
                                        Some(tauri_plugin_shell::process::CommandEvent::Error(e)) => {
                                            log::warn!("[sidecar error] {}", e);
                                            // continue drain loop
                                        }
                                        Some(tauri_plugin_shell::process::CommandEvent::Terminated(payload)) => {
                                            log::error!(
                                                "Sidecar terminated during health loop — code={:?} signal={:?}",
                                                payload.code, payload.signal
                                            );
                                            exit_detected = true;
                                            break 'drain;
                                        }
                                        Some(_) => {
                                            // Unknown variant — ignore and continue.
                                        }
                                        None => {
                                            // Channel closed — process gone.
                                            log::error!("Sidecar event channel closed during health loop");
                                            exit_detected = true;
                                            break 'drain;
                                        }
                                    }
                                }
                            }
                        }
                        if exit_detected {
                            break 'health;
                        }
                    }
                }

                // ── Change 5: Decision phase ──────────────────────────────────
                // All awaits are done. Locks are safe to take now.
                // Priority: exit_detected > backend_ok > timeout exhausted.
                if exit_detected {
                    let err_msg = "Backend sidecar exited unexpectedly during startup".to_string();
                    log::error!("CRITICAL: {}", err_msg);
                    {
                        let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
                        *lifecycle = BackendLifecycle::Crashed { error: err_msg.clone() };
                    }
                    Err(err_msg)
                } else if backend_ok {
                    {
                        let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
                        *lifecycle = BackendLifecycle::Ready {
                            port,
                            session_token: session_token.clone(),
                        };
                    }

                    log::info!("Backend started successfully on port {}", port);
                    Ok(serde_json::json!({
                        "status": "ready",
                        "port": port,
                        "mode": "production"
                        // session_token intentionally omitted — lives only in Ready variant
                    }))
                } else {
                    // Startup budget fully exhausted — genuine timeout failure.
                    let total_secs = 10 + MAX_ATTEMPTS as u64 * RETRY_SECS;
                    let err_msg = format!(
                        "Backend failed to start after ~{} s ({} health-check attempts). Check logs.",
                        total_secs, MAX_ATTEMPTS
                    );
                    log::error!(
                        "CRITICAL: Backend never became ready after {} attempts (~{} s total). Process did not respond.",
                        MAX_ATTEMPTS, total_secs
                    );
                    {
                        let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
                        *lifecycle = BackendLifecycle::Crashed { error: err_msg.clone() };
                    }
                    Err(err_msg)
                }
            }
            Err(e) => {
                let err_msg = format!(
                    "Backend failed to start. Antivirus may be blocking the executable. Error: {}",
                    e
                );
                log::error!("CRITICAL: Failed to spawn backend sidecar: {}", e);
                {
                    let mut lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
                    *lifecycle = BackendLifecycle::Crashed { error: err_msg.clone() };
                }
                Err(err_msg)
            }
        }
    }
}

// ── backend_request ───────────────────────────────────────────────────────────
// C2: Silent port-8001 fallback is REMOVED. If lifecycle is not Ready,
// this returns Err("Backend not ready") — a hard error, not a silent fallback.
#[tauri::command]
pub async fn backend_request(
    endpoint: String,
    method: String,
    body: Option<String>,
    auth_token: Option<String>,
) -> Result<String, String> {
    let port = {
        let lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
        match &*lifecycle {
            BackendLifecycle::Ready { port, .. } => *port,
            _ => return Err("Backend not ready".to_string()),
        }
    };

    let is_local_endpoint = endpoint.starts_with("/api/tally") ||
                            endpoint.starts_with("/api/vouchers") ||
                            endpoint.starts_with("/api/ledgers") ||
                            endpoint.starts_with("/api/reports") ||
                            endpoint.starts_with("/api/sync") ||
                            endpoint.starts_with("/api/setup") ||
                            endpoint.starts_with("/api/health") ||
                            endpoint.starts_with("/api/contacts") ||
                            endpoint.starts_with("/api/customers") ||
                            endpoint.starts_with("/api/dashboard") ||
                            endpoint.starts_with("/api/inventory") ||
                            endpoint.starts_with("/api/items") ||
                            endpoint.starts_with("/api/search");

    let base_url = if is_local_endpoint {
        format!("http://127.0.0.1:{}", port)
    } else {
        "https://weare-production.up.railway.app".to_string()
    };

    let url = format!("{}{}", base_url, endpoint);
    let client = reqwest::Client::builder()
        .danger_accept_invalid_certs(false)
        .use_rustls_tls()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("Failed to build client: {}", e))?;
    let method_parsed: reqwest::Method = method.parse()
        .map_err(|_| format!("Invalid HTTP method: {}", method))?;

    let mut request = client.request(method_parsed, &url)
        .header("Content-Type", "application/json")
        .header("x-api-key", "k24-secret-key-123");

    if let Some(session_token) = get_session_token() {
        request = request.header("X-Desktop-Token", &session_token);
    }

    if let Some(token) = auth_token {
        request = request.header("Authorization", format!("Bearer {}", token));
    }
    if let Some(body_content) = body {
        request = request.body(body_content);
    }

    let response = request.send().await.map_err(|e| format!("Request failed: {}", e))?;
    let status = response.status();
    let text = response.text().await.map_err(|e| format!("Failed to read response: {}", e))?;

    if !status.is_success() {
        log::warn!("Backend returned error {}: {}", status, text);
    }
    Ok(text)
}

// ── get_backend_status ────────────────────────────────────────────────────────
// B3: New 4-arm return shape. Key "running" is RETIRED; "status" is the new
// discriminator. session_token is NEVER included in this response.
//
// FRONTEND TEAM NOTE (D18 / C3):
//   Replace all `if (result.running)` checks with `if (result.status === "ready")`.
//   Replace all `result.port` reads with a guard on `result.status === "ready"`.
#[tauri::command]
pub fn get_backend_status() -> Result<serde_json::Value, String> {
    let lifecycle = BACKEND_LIFECYCLE.lock().map_err(|e| e.to_string())?;
    match &*lifecycle {
        BackendLifecycle::NotStarted => Ok(serde_json::json!({ "status": "not_started" })),
        BackendLifecycle::Starting   => Ok(serde_json::json!({ "status": "starting" })),
        BackendLifecycle::Ready { port, .. } => Ok(serde_json::json!({
            "status": "ready",
            "port": port
            // session_token intentionally omitted
        })),
        BackendLifecycle::Crashed { error } => Ok(serde_json::json!({
            "status": "crashed",
            "error": error
        })),
    }
}

// ── stop_backend ──────────────────────────────────────────────────────────────
// B7: Reset lifecycle to NotStarted (allows restart if process is ever re-spawned).
/// Stops the backend sidecar process (used on app shutdown)
pub fn stop_backend() {
    log::info!("Stopping backend sidecar...");
    if let Ok(mut process) = BACKEND_PROCESS.lock() {
        if let Some(child) = process.take() {
            match child.kill() {
                Ok(_) => log::info!("Backend process terminated successfully"),
                Err(e) => log::error!("Failed to kill backend process: {}", e),
            }
        }
    }

    // Reset lifecycle to NotStarted
    if let Ok(mut lifecycle) = BACKEND_LIFECYCLE.lock() {
        *lifecycle = BackendLifecycle::NotStarted;
    }
}
