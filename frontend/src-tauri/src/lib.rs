mod commands;

use tauri::Emitter;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_deep_link::init())
        .invoke_handler(tauri::generate_handler![
            commands::start_backend,
            commands::backend_request,
            commands::get_backend_status
        ])
        .setup(|app| {
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
                        log::error!("Failed to start backend: {}", e);
                        let _ = handle.emit("backend_error", e);
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
