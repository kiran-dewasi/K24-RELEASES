use once_cell::sync::Lazy;
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

fn get_session_token() -> Option<String> {
    let state = BACKEND_STATE.lock().ok()?;
    state.as_ref().map(|s| s.session_token.clone())
}

#[tauri::command]
pub async fn start_backend(app_handle: AppHandle) -> Result<serde_json::Value, String> {
    #[cfg(debug_assertions)]
    let _ = &app_handle;

    // Check if backend is already running
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
        let auth = BackendAuth {
            port: 8001,
            session_token: session_token.clone(),
        };
        *BACKEND_STATE.lock().map_err(|e| e.to_string())? = Some(auth);
        log::info!("Development mode: Using localhost:8001");
        return Ok(serde_json::json!({
            "port": 8001,
            "session_token": session_token,
            "mode": "development"
        }));
    }
    
    #[cfg(not(debug_assertions))]
    {
        // SAFE MODE: Delay startup to ensure window is ready and AV has scanned main process
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

        let shell = app_handle.shell();
        log::info!("Attempting to spawn sidecar: k24-backend");

        let result = shell
            .sidecar("k24-backend")
            .map_err(|e| format!("Failed to configure sidecar: {}", e))?
            .args(&[
                "--port", &port.to_string(),
                "--token", &session_token,
                "--desktop-mode", "true",
                "--app-version", &app_handle.package_info().version.to_string()
            ])
            .spawn();
        
        match result {
            Ok((_rx, child)) => {
                // Store the child process handle for cleanup on exit
                *BACKEND_PROCESS.lock().map_err(|e| e.to_string())? = Some(child);
                
                let auth = BackendAuth {
                    port,
                    session_token: session_token.clone(),
                };
                *BACKEND_STATE.lock().map_err(|e| e.to_string())? = Some(auth);
                
                // Allow backend time to warm up
                tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                
                // === ADD HEALTH CHECK ===
                log::info!("Attempting to verify backend health...");

                // Try to ping the backend
                let health_url = format!("http://127.0.0.1:{}/health", port);
                let mut attempts = 0;
                let max_attempts = 10;

                while attempts < max_attempts {
                    // Use a client with a timeout for the health check
                    let client = reqwest::Client::builder()
                        .timeout(std::time::Duration::from_secs(5))
                        .build()
                        .unwrap_or_default();

                    match client.get(&health_url).send().await {
                        Ok(response) => {
                            if response.status().is_success() {
                                log::info!("Backend health check PASSED ✓");
                                break;
                            }
                        }
                        Err(e) => {
                            log::warn!("Health check attempt {}/{} failed: {}", attempts + 1, max_attempts, e);
                            attempts += 1;
                            if attempts < max_attempts {
                                tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                            }
                        }
                    }
                }

                if attempts == max_attempts {
                    log::error!("CRITICAL: Backend health check failed after {} attempts. Process did not respond.", max_attempts);
                    return Err("Backend failed to start: process did not respond after 10 health-check attempts. Check logs.".into());
                }
                
                log::info!("Backend started successfully on port {}", port);
                Ok(serde_json::json!({
                    "port": port,
                    "session_token": session_token,
                    "mode": "production"
                }))
            }
            Err(e) => {
                log::error!("CRITICAL: Failed to spawn backend: {}", e);
                // Return generic error but DO NOT PANIC
                Err(format!("Backend failed to start. Antivirus might be blocking it. Error: {}", e))
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
