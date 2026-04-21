use once_cell::sync::Lazy;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use tauri::AppHandle;
use uuid::Uuid;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

/// Backend Authentication State
#[derive(Debug, Clone)]
pub struct BackendAuth {
    pub port: u16,
    pub session_token: String,
}

static BACKEND_STATE: Lazy<Mutex<Option<BackendAuth>>> = Lazy::new(|| Mutex::new(None));
static BACKEND_PROCESS: Lazy<Mutex<Option<CommandChild>>> = Lazy::new(|| Mutex::new(None));
// True while start_backend is still running its readiness loop (prevents re-entrant calls
// from the frontend returning a false already_running=true before health-check passes).
static STARTUP_IN_PROGRESS: AtomicBool = AtomicBool::new(false);

fn get_session_token() -> Option<String> {
    let state = BACKEND_STATE.lock().ok()?;
    state.as_ref().map(|s| s.session_token.clone())
}

#[tauri::command]
pub async fn start_backend(app_handle: AppHandle) -> Result<serde_json::Value, String> {
    #[cfg(debug_assertions)]
    let _ = &app_handle;

    // If a startup attempt is already in progress, tell the caller to wait rather than
    // returning a false "already_running" that might race against an incomplete readiness loop.
    if STARTUP_IN_PROGRESS.load(Ordering::SeqCst) {
        return Ok(serde_json::json!({
            "startup_in_progress": true
        }));
    }

    // Check if backend has fully started (readiness loop has passed)
    {
        let state = BACKEND_STATE.lock().map_err(|e| e.to_string())?;
        if state.is_some() {
            let auth = state.as_ref().unwrap();
            return Ok(serde_json::json!({
                "port": auth.port,
                "already_running": true
            }));
        }
    }

    let port = portpicker::pick_unused_port()
        .ok_or("No available ports")?;
    
    let session_token = Uuid::new_v4().to_string();
    
    log::info!("Starting backend on port {} with session token", port);
    
    #[cfg(debug_assertions)]
    {
        let port: u16 = std::env::var("DESKTOP_BACKEND_PORT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(8001);
        let auth = BackendAuth {
            port,
            session_token: session_token.clone(),
        };
        *BACKEND_STATE.lock().map_err(|e| e.to_string())? = Some(auth);
        log::info!("Development mode: backend on port {}", port);
        return Ok(serde_json::json!({
            "port": port,
            "session_token": session_token,
            "mode": "development"
        }));
    }
    
    #[cfg(not(debug_assertions))]
    {
        // Mark startup as in-progress so concurrent start_backend calls don't race.
        STARTUP_IN_PROGRESS.store(true, Ordering::SeqCst);

        // SAFE MODE: Short initial delay so Tauri window is up and AV has cleared the process.
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

        let shell = app_handle.shell();
        log::info!("Attempting to spawn sidecar: k24-backend");

        let result = shell
            .sidecar("k24-backend")
            .map_err(|e| {
                STARTUP_IN_PROGRESS.store(false, Ordering::SeqCst);
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
            Ok((_rx, child)) => {
                // Store the child process handle for cleanup on exit.
                *BACKEND_PROCESS.lock().map_err(|e| e.to_string())? = Some(child);

                // === STARTUP READINESS WINDOW ===
                //
                // Total budget: 10 s warmup + 20 retries × 4 s = ~90 s
                // This covers cold disk, AV scan, OneDrive noise, slow Python/LangGraph init.
                //
                // BACKEND_STATE is intentionally NOT set here yet.
                // It will only be set once health-check passes, so get_backend_status()
                // returns running=false (correctly) until the backend is genuinely ready.

                let health_url = format!("http://127.0.0.1:{}/health", port);

                // Generous initial warmup before first probe — Python + uvicorn cold start.
                log::info!("Waiting 10 s for backend initial warmup before first health-check…");
                tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;

                log::info!("Starting readiness loop (max 20 retries × 4 s = 80 s)…");

                const MAX_ATTEMPTS: u32 = 20;
                const RETRY_SECS: u64 = 4;
                let retry_interval = tokio::time::Duration::from_secs(RETRY_SECS);
                let mut backend_ok = false;

                for attempt in 1..=MAX_ATTEMPTS {
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
                            break;
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

                    // Sleep after every attempt, including the last one, to ensure
                    // we give a final window before declaring failure.
                    if attempt < MAX_ATTEMPTS {
                        tokio::time::sleep(retry_interval).await;
                    }
                }

                // Clear the in-progress flag regardless of outcome.
                STARTUP_IN_PROGRESS.store(false, Ordering::SeqCst);

                if backend_ok {
                    // Only NOW write BACKEND_STATE — prevents stale ready-state from leaking
                    // if the readiness loop fails.
                    let auth = BackendAuth {
                        port,
                        session_token: session_token.clone(),
                    };
                    *BACKEND_STATE.lock().map_err(|e| e.to_string())? = Some(auth);

                    log::info!("Backend started successfully on port {}", port);
                    Ok(serde_json::json!({
                        "port": port,
                        "session_token": session_token,
                        "mode": "production"
                    }))
                } else {
                    // Startup budget fully exhausted — genuine failure.
                    let total_secs = 10 + MAX_ATTEMPTS as u64 * RETRY_SECS;
                    log::error!(
                        "CRITICAL: Backend never became ready after {} attempts (~{} s total). Process did not respond.",
                        MAX_ATTEMPTS, total_secs
                    );
                    Err(format!(
                        "Backend failed to start after ~{} s ({} health-check attempts). Check logs.",
                        total_secs, MAX_ATTEMPTS
                    ))
                }
            }
            Err(e) => {
                STARTUP_IN_PROGRESS.store(false, Ordering::SeqCst);
                log::error!("CRITICAL: Failed to spawn backend sidecar: {}", e);
                Err(format!(
                    "Backend failed to start. Antivirus may be blocking the executable. Error: {}",
                    e
                ))
            }
        }
    }
}

#[tauri::command]
pub async fn backend_request(
    endpoint: String,
    method: String,
    body: Option<String>,
    auth_token: Option<String>,
) -> Result<String, String> {
    let port = {
        let state = BACKEND_STATE.lock().map_err(|e| e.to_string())?;
        state.as_ref().map(|s| s.port).unwrap_or(8001)
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

#[tauri::command]
pub fn get_backend_status() -> Result<serde_json::Value, String> {
    let state = BACKEND_STATE.lock().map_err(|e| e.to_string())?;
    match state.as_ref() {
        Some(auth) => Ok(serde_json::json!({
            "running": true,
            "port": auth.port
        })),
        None => Ok(serde_json::json!({
            "running": false
        }))
    }
}

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
    
    // Clear backend state
    if let Ok(mut state) = BACKEND_STATE.lock() {
        *state = None;
    }
}
