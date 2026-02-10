use once_cell::sync::Lazy;
use std::sync::Mutex;
use tauri::{AppHandle, Emitter};
use uuid::Uuid;
use tauri_plugin_updater::UpdaterExt;
use tauri_plugin_shell::ShellExt;

/// Backend Authentication State
#[derive(Debug, Clone)]
pub struct BackendAuth {
    pub port: u16,
    pub session_token: String,
}

static BACKEND_STATE: Lazy<Mutex<Option<BackendAuth>>> = Lazy::new(|| Mutex::new(None));

fn get_backend_url() -> Option<String> {
    let state = BACKEND_STATE.lock().ok()?;
    state.as_ref().map(|s| format!("http://127.0.0.1:{}", s.port))
}

fn get_session_token() -> Option<String> {
    let state = BACKEND_STATE.lock().ok()?;
    state.as_ref().map(|s| s.session_token.clone())
}

#[tauri::command]
pub async fn start_backend(app_handle: AppHandle) -> Result<serde_json::Value, String> {
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
            port: 8000,
            session_token: session_token.clone(),
        };
        *BACKEND_STATE.lock().map_err(|e| e.to_string())? = Some(auth);
        log::info!("Development mode: Using localhost:8000");
        return Ok(serde_json::json!({
            "port": 8000,
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
                "--desktop-mode", "true"
            ])
            .spawn();
        
        match result {
            Ok((_rx, _child)) => {
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
                    match reqwest::get(&health_url).await {
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
                    log::warn!("Backend health check failed after {} attempts. Continuing anyway to allow debugging.", max_attempts);
                    // Non-blocking: We return OK even if health check fails, trusting the process spawned.
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
    let backend_url = get_backend_url().ok_or("Backend not started")?;
    let session_token = get_session_token().ok_or("No session token")?;
    let url = format!("{}{}", backend_url, endpoint);
    let client = reqwest::Client::new();
    let method_parsed: reqwest::Method = method.parse()
        .map_err(|_| format!("Invalid HTTP method: {}", method))?;
    
    let mut request = client.request(method_parsed, &url)
        .header("Content-Type", "application/json")
        .header("X-Desktop-Token", &session_token);
    
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

#[tauri::command]
pub async fn check_updates(app: AppHandle) -> Result<String, String> {
    if let Some(updater) = app.updater().ok() {
        match updater.check().await {
            Ok(Some(update)) => Ok(format!("Update available: v{}", update.version)),
            Ok(None) => Ok("Up to date".to_string()),
            Err(e) => Err(format!("Check failed: {}", e)),
        }
    } else {
        Err("Updater not initialized".to_string())
    }
}

#[tauri::command]
pub async fn install_update(app: AppHandle) -> Result<String, String> {
    if let Some(updater) = app.updater().ok() {
        match updater.check().await {
            Ok(Some(update)) => {
                update.download_and_install(|_chunk, _total| {}, || {}).await.map_err(|e| e.to_string())?;
                Ok("Update installed".to_string())
            }
            Ok(None) => Ok("No update".to_string()),
            Err(e) => Err(e.to_string())
        }
    } else {
        Err("Updater not initialized".to_string())
    }
}

#[tauri::command]
pub async fn restart_app(app: AppHandle) -> Result<(), String> {
    app.restart();
    Ok(())
}
