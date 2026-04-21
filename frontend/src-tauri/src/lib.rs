mod commands;

use tauri::Emitter;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_deep_link::init())
        .invoke_handler(tauri::generate_handler![
            commands::start_backend,
            commands::backend_request,
            commands::get_backend_status
        ])
        .setup(|app| {
            use tauri::Manager;
            if let Some(window) = app.get_webview_window("main") {
                #[cfg(debug_assertions)] // Only available if devtools feature is enabled
                window.open_devtools();
            }
            let handle = app.handle().clone();
            
            // Log startup
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Debug)
                        .build(),
                )?;
            } else {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            
            log::info!("K24 Desktop App starting...");
            
            // Auto-start backend on app launch
            tauri::async_runtime::spawn(async move {
                match commands::start_backend(handle.clone()).await {
                    Ok(result) => {
                        log::info!("Backend started: {:?}", result);
                        let _ = handle.emit("backend_ready", result);
                    }
                    Err(e) => {
                        log::error!("CRITICAL: Failed to start backend: {}", e);
                        let _ = handle.emit("backend_error", &e);

                        // Show a non-fatal error dialog. The user is informed but the process
                        // stays alive so they can dismiss and inspect logs. We do NOT call
                        // std::process::exit here — the startup budget (~90 s) is long enough
                        // that if we reach this branch the failure is genuine, but forcing an
                        // abrupt exit would destroy the log context and confuse users whose
                        // machine was merely slow to boot.
                        use tauri_plugin_dialog::DialogExt;
                        handle
                            .dialog()
                            .message(&format!(
                                "K24 backend failed to start after the full startup window.\n\n\
                                Details: {}\n\n\
                                Please restart the app. If the issue persists, check that your \
                                antivirus is not blocking k24-backend.exe, then reinstall K24.",
                                e
                            ))
                            .title("Startup Error")
                            .blocking_show();

                        // After the user dismisses the dialog, exit gracefully.
                        // This is only reached after the full ~90-second readiness budget
                        // has been exhausted, so it is a genuine failure — not a false positive.
                        std::process::exit(1);
                    }
                }
            });
            
            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                log::info!("Window close requested, stopping backend...");
                commands::stop_backend();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
