mod commands;

use tauri::Emitter;
use tauri::tray::{TrayIconBuilder, TrayIconEvent, MouseButton};
use tauri::image::Image;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            commands::start_backend,
            commands::backend_request,
            commands::get_backend_status
        ])
        .setup(|app| {
            use tauri::Manager;
            if let Some(_window) = app.get_webview_window("main") {
                #[cfg(debug_assertions)] // Only available if devtools feature is enabled
                _window.open_devtools();
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

            // ── Tray icon — Starting state ────────────────────────────────────────────
            let starting_icon = Image::from_bytes(include_bytes!("../icons/tray-starting.png"))
                .expect("tray-starting.png must exist at compile time");

            let _tray = TrayIconBuilder::with_id("main-tray")
                .icon(starting_icon)
                .tooltip("K24 — Starting…")
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { button: MouseButton::Left, .. } = event {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            // ── Auto-start backend on app launch ──────────────────────────────────────
            //
            // FRONTEND TEAM: Two breaking changes from BackendLifecycle migration:
            // (a) backend_ready event payload changed:
            //     OLD: { port, session_token, mode }
            //     NEW: { status: "ready", port, mode }   ← no session_token in payload
            //     Update every listener that destructures { port, session_token, mode }.
            // (b) get_backend_status return shape changed:
            //     OLD: { running: bool, port? }
            //     NEW: { status: "not_started"|"starting"|"ready"|"crashed", port?, error? }
            //     Replace `if (result.running)` with `if (result.status === "ready")`.
            // ─────────────────────────────────────────────────────────────────────────
            tauri::async_runtime::spawn(async move {
                match commands::start_backend(handle.clone()).await {
                    Ok(result) => {
                        log::info!("Backend started: {:?}", result);
                        // Payload shape: { status: "ready", port, mode } — no session_token
                        let _ = handle.emit("backend_ready", &result);

                        // Update tray to Ready state
                        if let Some(tray) = handle.tray_by_id("main-tray") {
                            let port = result["port"].as_u64().unwrap_or(0);
                            let _ = tray.set_tooltip(Some(
                                format!("K24 — Ready (port {})", port).as_str(),
                            ));
                            let ready_icon =
                                Image::from_bytes(include_bytes!("../icons/tray-ready.png"))
                                    .expect("tray-ready.png must exist at compile time");
                            let _ = tray.set_icon(Some(ready_icon));
                        }

                        // Fire native notification — production builds only
                        #[cfg(not(debug_assertions))]
                        {
                            use tauri_plugin_notification::NotificationExt;
                            let port = result["port"].as_u64().unwrap_or(0);
                            let _ = handle
                                .notification()
                                .builder()
                                .title("K24 is Ready")
                                .body(format!("Backend started on port {}.", port).as_str())
                                .show();
                        }
                    }
                    Err(e) => {
                        log::error!("CRITICAL: Failed to start backend: {}", e);
                        let _ = handle.emit("backend_error", &e);

                        // Update tray to Crashed state
                        if let Some(tray) = handle.tray_by_id("main-tray") {
                            let _ = tray.set_tooltip(Some("K24 — Crashed. Click to restart."));
                            let crashed_icon =
                                Image::from_bytes(include_bytes!("../icons/tray-crashed.png"))
                                    .expect("tray-crashed.png must exist at compile time");
                            let _ = tray.set_icon(Some(crashed_icon));
                        }

                        // Fire crash notification (all builds)
                        {
                            use tauri_plugin_notification::NotificationExt;
                            // Safe UTF-8 truncation — do not slice at raw byte boundary
                            let body: String = if e.chars().count() > 120 {
                                e.chars().take(120).collect::<String>() + "…"
                            } else {
                                e.clone()
                            };
                            let _ = handle
                                .notification()
                                .builder()
                                .title("K24 Backend Crashed")
                                .body(body.as_str())
                                .show();
                        }

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
