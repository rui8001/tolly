@echo off
setlocal
title Tolly Desktop Development
cd /d "%~dp0"

set "VSWHERE=C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
  echo [Tolly] Visual Studio Build Tools were not found.
  echo Install the Desktop development with C++ workload first.
  pause
  exit /b 1
)

set "VS_PATH="
for /f "usebackq tokens=*" %%I in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VS_PATH=%%I"
if not defined VS_PATH (
  echo [Tolly] The Visual C++ x64 tools are missing.
  echo Modify Visual Studio Build Tools and add Desktop development with C++.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [Tolly] Node.js 20 or newer is required in PATH.
  pause
  exit /b 1
)
where cargo >nul 2>nul
if errorlevel 1 (
  echo [Tolly] Rust stable is required in PATH.
  pause
  exit /b 1
)

if not defined TALLY_PYTHON if exist "%~dp0tally-engine\.venv\Scripts\python.exe" set "TALLY_PYTHON=%~dp0tally-engine\.venv\Scripts\python.exe"
if not defined TALLY_PYTHON (
  echo [Tolly] Python was not found. Set TALLY_PYTHON to Python 3.10 or newer.
  pause
  exit /b 1
)

if not exist "%~dp0tally-win\node_modules\@tauri-apps\cli\tauri.js" (
  echo [Tolly] Dependencies are missing. Run pnpm install --frozen-lockfile in tally-win first.
  pause
  exit /b 1
)

call "%VS_PATH%\Common7\Tools\VsDevCmd.bat" -arch=amd64
if errorlevel 1 exit /b 1

cd /d "%~dp0tally-win"
echo [Tolly] Starting the real Windows desktop app with local usage data.
echo [Tolly] Keep this window open. Press Ctrl+C to stop development mode.
node node_modules\@tauri-apps\cli\tauri.js dev
