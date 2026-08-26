@echo off
setlocal
title Tolly Web Preview
cd /d "%~dp0tally-win"

if not exist "package.json" (
  echo [Tolly] Cannot find tally-win\package.json.
  echo Please keep this file in the repository root.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [Tolly] Node.js is not available in PATH.
  echo Install Node.js 20 or newer, then run this file again.
  pause
  exit /b 1
)

if not exist "node_modules\.bin\vite.cmd" (
  echo [Tolly] Dependencies are not installed.
  where pnpm >nul 2>nul
  if errorlevel 1 (
    echo Install Node.js and pnpm, then run: pnpm install --frozen-lockfile
    pause
    exit /b 1
  )
  call pnpm install --frozen-lockfile
  if errorlevel 1 (
    echo [Tolly] Dependency installation failed.
    pause
    exit /b 1
  )
)

set "TOLLY_PORT_BUSY="
for /f "tokens=*" %%L in ('netstat -ano ^| findstr /R /C:":1420 .*LISTENING"') do set "TOLLY_PORT_BUSY=1"
if defined TOLLY_PORT_BUSY (
  echo [Tolly] Port 1420 is already occupied by another process.
  echo Close the old Tolly or WorkBuddy preview, then run this file again.
  pause
  exit /b 1
)

echo [Tolly] Starting the verified Vite preview at http://127.0.0.1:1420/
echo [Tolly] Keep this window open. Press Ctrl+C to stop.
if not defined TOLLY_NO_OPEN start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Milliseconds 900; Start-Process 'http://127.0.0.1:1420/?tolly-preview=vite'"
call "node_modules\.bin\vite.cmd" --host 127.0.0.1 --port 1420 --strictPort

if errorlevel 1 (
  echo.
  echo [Tolly] Port 1420 may already be used by an old process.
  echo Close the old Tolly or WorkBuddy preview, then run this file again.
  pause
)
