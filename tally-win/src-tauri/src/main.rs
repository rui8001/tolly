#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{fs, path::PathBuf};

#[cfg(debug_assertions)]
use std::process::Command;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    App, AppHandle, Emitter, Manager, PhysicalPosition, WebviewWindow, WindowEvent,
};
use tauri_plugin_positioner::{Position, WindowExt};

const PANEL_WORK_AREA_MARGIN: f64 = 8.0;

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(default)]
struct Settings {
    hidden_tools: Vec<String>,
    refresh_seconds: u64,
    qwenwork_quota_enabled: bool,
}

fn settings_path(app: &AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_config_dir()
        .map(|dir| dir.join("settings.json"))
        .map_err(|error| format!("无法定位设置目录：{error}"))
}

fn normalized_settings(mut settings: Settings) -> Settings {
    settings.hidden_tools.sort();
    settings.hidden_tools.dedup();
    settings.refresh_seconds = match settings.refresh_seconds {
        15 | 30 | 60 | 120 => settings.refresh_seconds,
        _ => 30,
    };
    settings
}

#[tauri::command]
fn get_settings(app: AppHandle) -> Result<Settings, String> {
    let path = settings_path(&app)?;
    if !path.exists() {
        return Ok(normalized_settings(Settings::default()));
    }
    let raw = fs::read_to_string(path).map_err(|error| format!("读取设置失败：{error}"))?;
    let settings = serde_json::from_str(&raw).map_err(|error| format!("设置格式无效：{error}"))?;
    Ok(normalized_settings(settings))
}

#[tauri::command]
fn save_settings(app: AppHandle, settings: Settings) -> Result<Settings, String> {
    let settings = normalized_settings(settings);
    let path = settings_path(&app)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| format!("创建设置目录失败：{error}"))?;
    }
    let data =
        serde_json::to_vec_pretty(&settings).map_err(|error| format!("序列化设置失败：{error}"))?;
    fs::write(path, data).map_err(|error| format!("保存设置失败：{error}"))?;
    Ok(settings)
}

#[cfg(debug_assertions)]
fn python_command() -> Result<(String, Vec<String>), String> {
    if let Ok(path) = std::env::var("TALLY_PYTHON") {
        if !path.trim().is_empty() {
            return Ok((path, Vec::new()));
        }
    }
    for (executable, prefix) in [("py", vec!["-3"]), ("python", vec![]), ("python3", vec![])] {
        if Command::new(executable)
            .args(&prefix)
            .arg("--version")
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false)
        {
            return Ok((
                executable.to_string(),
                prefix.into_iter().map(String::from).collect(),
            ));
        }
    }
    Err("未找到 Python 3；请安装 Python 3.10+ 或设置 TALLY_PYTHON。".into())
}

#[cfg(debug_assertions)]
fn source_engine_root() -> PathBuf {
    std::env::var("TALLY_ENGINE_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../tally-engine"))
}

#[cfg(debug_assertions)]
fn run_source_engine(qwenwork_quota_enabled: bool) -> Result<String, String> {
    let (python, mut args) = python_command()?;
    args.extend(["-m", "engine", "--json", "--no-sync-snapshot"].map(String::from));
    let mut command = Command::new(python);
    command
        .args(args)
        .current_dir(source_engine_root())
        .env("PYTHONIOENCODING", "utf-8");
    if qwenwork_quota_enabled {
        command.env("TALLY_QWENWORK_QUOTA", "1");
    }
    let output = command
        .output()
        .map_err(|error| format!("启动用量引擎失败：{error}"))?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
    }
    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

#[cfg(not(debug_assertions))]
async fn run_bundled_engine(
    app: &AppHandle,
    qwenwork_quota_enabled: bool,
) -> Result<String, String> {
    use tauri_plugin_shell::ShellExt;

    let mut command = app
        .shell()
        .sidecar("tally-engine")
        .map_err(|error| format!("无法定位内置用量引擎：{error}"))?
        .args(["--json", "--no-sync-snapshot"]);
    if qwenwork_quota_enabled {
        command = command.env("TALLY_QWENWORK_QUOTA", "1");
    }
    let output = command
        .output()
        .await
        .map_err(|error| format!("启动内置用量引擎失败：{error}"))?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
    }
    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

#[tauri::command]
async fn get_usage(_app: AppHandle) -> Result<Value, String> {
    let qwenwork_quota_enabled = get_settings(_app.clone())
        .map(|settings| settings.qwenwork_quota_enabled)
        .unwrap_or(false);
    #[cfg(debug_assertions)]
    let raw =
        tauri::async_runtime::spawn_blocking(move || run_source_engine(qwenwork_quota_enabled))
            .await
            .map_err(|error| format!("用量引擎任务失败：{error}"))??;

    #[cfg(not(debug_assertions))]
    let raw = run_bundled_engine(&_app, qwenwork_quota_enabled).await?;

    serde_json::from_str(&raw).map_err(|error| format!("用量引擎返回了无效 JSON：{error}"))
}

#[tauri::command]
fn quit_app(app: AppHandle) {
    app.exit(0);
}

fn clamp_axis(
    position: i32,
    window_size: u32,
    work_start: i32,
    work_size: u32,
    margin: i32,
) -> i32 {
    let minimum = work_start.saturating_add(margin);
    let maximum = work_start
        .saturating_add(work_size as i32)
        .saturating_sub(window_size as i32)
        .saturating_sub(margin);

    if maximum < minimum {
        work_start
    } else {
        position.clamp(minimum, maximum)
    }
}

fn constrain_panel_to_work_area(window: &WebviewWindow) -> tauri::Result<()> {
    let Some(monitor) = window.current_monitor()? else {
        return Ok(());
    };
    let work_area = monitor.work_area();
    let window_size = window.outer_size()?;
    let position = window.outer_position()?;
    let margin = (PANEL_WORK_AREA_MARGIN * monitor.scale_factor()).round() as i32;

    let x = clamp_axis(
        position.x,
        window_size.width,
        work_area.position.x,
        work_area.size.width,
        margin,
    );
    let y = clamp_axis(
        position.y,
        window_size.height,
        work_area.position.y,
        work_area.size.height,
        margin,
    );

    if x != position.x || y != position.y {
        window.set_position(PhysicalPosition::new(x, y))?;
    }
    Ok(())
}

fn show_panel(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if window.move_window_constrained(Position::TrayLeft).is_ok() {
            let _ = constrain_panel_to_work_area(&window);
        }
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[cfg(test)]
mod tests {
    use super::clamp_axis;

    #[test]
    fn keeps_panel_inside_the_right_work_area_edge() {
        assert_eq!(clamp_axis(1700, 420, 0, 1920, 8), 1492);
    }

    #[test]
    fn supports_monitors_with_negative_coordinates() {
        assert_eq!(clamp_axis(-2100, 420, -1920, 1920, 8), -1912);
    }

    #[test]
    fn falls_back_to_work_area_start_when_panel_is_too_large() {
        assert_eq!(clamp_axis(200, 1200, 0, 1000, 8), 0);
    }
}

fn toggle_panel(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_visible().unwrap_or(false) {
            let _ = window.hide();
        } else {
            show_panel(app);
        }
    }
}

fn setup_tray(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let show = MenuItem::with_id(app, "show", "显示面板", true, None::<&str>)?;
    let refresh = MenuItem::with_id(app, "refresh", "刷新", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&show, &refresh, &quit])?;
    let icon = app
        .default_window_icon()
        .cloned()
        .ok_or_else(|| std::io::Error::other("缺少应用图标"))?;

    TrayIconBuilder::with_id("tolly-tray")
        .icon(icon)
        .tooltip("Tolly · AI 编程用量")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "quit" => app.exit(0),
            "show" => show_panel(app),
            "refresh" => {
                show_panel(app);
                let _ = app.emit("request-refresh", ());
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            tauri_plugin_positioner::on_tray_event(tray.app_handle(), &event);
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                toggle_panel(tray.app_handle());
            }
        })
        .build(app)?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_positioner::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            show_panel(app)
        }))
        .setup(|app| {
            setup_tray(app)?;
            if let Some(window) = app.get_webview_window("main") {
                let window_for_events = window.clone();
                window.on_window_event(move |event| match event {
                    WindowEvent::Focused(false) => {
                        if !cfg!(debug_assertions) {
                            let _ = window_for_events.hide();
                        }
                    }
                    WindowEvent::CloseRequested { api, .. } => {
                        api.prevent_close();
                        let _ = window_for_events.hide();
                    }
                    _ => {}
                });
            }
            show_panel(app.handle());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_usage,
            get_settings,
            save_settings,
            quit_app
        ])
        .run(tauri::generate_context!())
        .expect("Tolly failed to start");
}
