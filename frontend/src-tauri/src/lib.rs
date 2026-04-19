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

                        // Show a blocking error dialog so the user knows what happened
                        use tauri_plugin_dialog::DialogExt;
                        handle
                            .dialog()
                            .message("K24 backend failed to start. Please restart the app. If the issue persists, reinstall K24.")
                            .title("Startup Error")
                            .blocking_show();

                        // Exit cleanly — do NOT silently load the dashboard with a dead backend
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
